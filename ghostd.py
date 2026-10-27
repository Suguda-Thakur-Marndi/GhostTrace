#!/usr/bin/env python3
"""ghostd.py - Core daemon, inference client, secret redactor, and session engine for GhostTrace.

Operates strictly offline or with local open-weight LLMs (Ollama / llama.cpp) over loopback.
Never transmits prompts or command data to external services.
Enforces strict secret redaction, safe output sanitization, and deterministic fallbacks.
"""

from __future__ import annotations

import argparse
import datetime
import ipaddress
import json
import os
import random
import re
import shutil
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Version identifier
__version__ = "0.2.0"

# Default configuration values
DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434"
DEFAULT_LLAMACPP_ENDPOINT = "http://localhost:8080"
DEFAULT_TIMEOUT = 2.5
DEFAULT_CHANCE = 40
DEFAULT_MAX_WORDS = 20

# Loopback hosts strictly allowed
ALLOWED_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}

# Base directory for persistent metadata and runtime queues
def get_haunt_dir() -> Path:
    """Get the base directory for haunt data: ~/.local/share/haunt/."""
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        base = Path(xdg_data) / "haunt"
    else:
        base = Path.home() / ".local" / "share" / "haunt"
    base.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(base, 0o700)
    except Exception:
        pass
    return base


def get_run_dir() -> Path:
    """Get runtime directory for request/response queues."""
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
    if xdg_runtime:
        run_dir = Path(xdg_runtime) / "haunt"
    else:
        run_dir = get_haunt_dir() / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(run_dir, 0o700)
    except Exception:
        pass
    return run_dir


# ==============================================================================
# 1. SECRET REDACTION & COMMAND SANITIZATION
# ==============================================================================

class SecretRedactor:
    """Redacts secrets, credentials, auth tokens, and private paths before prompt construction."""

    # Patterns for secrets
    PATTERNS: List[Tuple[str, str]] = [
        # AWS Access Key
        (r"\b(AKIA[0-9A-Z]{16})\b", "[REDACTED_AWS_KEY]"),
        # GitHub Personal Access Token
        (r"\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b", "[REDACTED_GH_TOKEN]"),
        # OpenAI API Key
        (r"\b(sk-[A-Za-z0-9]{20,})\b", "[REDACTED_API_KEY]"),
        # Generic Slack / Discord tokens
        (r"\b(xox[baprs]-[0-9A-Za-z]{10,48})\b", "[REDACTED_TOKEN]"),
        # JWT / Bearer tokens
        (r"Bearer\s+[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_=]*", "Bearer [REDACTED_JWT]"),
        # Private key blocks
        (r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
        # URLs with embedded credentials (e.g. http://user:pass@host)
        (r"(https?://)([^:\s/@]+):([^@\s/]+)@", r"\1[REDACTED_USER]:[REDACTED_PW]@"),
        # export VAR=secret or VAR=secret in command lines
        (r"(?i)\b(export\s+)?([A-Za-z_0-9]*(?:KEY|TOKEN|SECRET|PASS(?:WORD)?|AUTH|CREDENTIAL)[A-Za-z_0-9]*)\s*=\s*['\"]?([^'\"\s&;]+)['\"]?", r"\1\2=[REDACTED]"),
        # CLI flags like --password secret, --token=secret, -p secret
        (r"(?i)(--(?:password|token|secret|api-key|auth-token|access-token)(?:=|\s+))['\"]?([^'\"\s&;]+)['\"]?", r"\1[REDACTED]"),
        # Basic auth CLI flags: -u user:pass or --user user:pass
        (r"(?i)(-(?:-user|u)\s+[^:\s]+:)[^'\"\s&;]+", r"\1[REDACTED_PW]"),
        # Token flags: --with-token <token>
        (r"(?i)(--with-token(?:\s+|=))['\"]?([^'\"\s&;]+)['\"]?", r"\1[REDACTED_TOKEN]"),
        # Sensitive files and SSH keys
        (r"(?i)(?:~?/?(?:[a-zA-Z0-9_.-]+/)*)?(?:(?:\.ssh/|\.aws/)?(?:id_rsa|id_ed25519|id_ecdsa|known_hosts|credentials)|(?:\.env|\.netrc)(?:\.[a-zA-Z0-9_.-]+)?)\b", "[REDACTED_FILE_PATH]"),
    ]

    @classmethod
    def redact(cls, text: str) -> str:
        """Scan text and replace sensitive tokens with safe redaction markers."""
        if not text:
            return ""
        result = text
        for pattern, replacement in cls.PATTERNS:
            result = re.sub(pattern, replacement, result)
        return result

    @classmethod
    def sanitize_command_for_prompt(
        cls,
        cmd: str,
        raw_args: str = "",
        allow_args: bool = False,
    ) -> Tuple[str, str]:
        """Produce safe command name and sanitized argument summary.

        Never sends raw command lines or full paths to the model.
        """
        clean_cmd = Path(cmd.strip().split()[0] if cmd.strip() else "").name
        if not clean_cmd:
            clean_cmd = "unknown"

        if not allow_args or not raw_args:
            return clean_cmd, ""

        # Redact secrets from arguments
        redacted_args = cls.redact(raw_args.strip())

        # Strip user home directory path if present
        home = str(Path.home())
        if home in redacted_args:
            redacted_args = redacted_args.replace(home, "~")

        # Bound length of argument summary to 80 characters
        if len(redacted_args) > 80:
            redacted_args = redacted_args[:77] + "..."

        return clean_cmd, redacted_args


# ==============================================================================
# 2. OUTPUT SANITIZATION & TERMINAL SAFETY
# ==============================================================================

class OutputSanitizer:
    """Enforces strict post-processing on model output: exactly one sentence < 20 words,

    no ANSI escape codes, no markdown, no quotes, no emojis, and no executable instructions.
    """

    ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
    EMOJI_RE = re.compile(
        r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u200d\ufe0f]"
    )

    # Characters that suggest executable instructions or shell commands
    SUSPICIOUS_SHELL_PATTERNS = [
        re.compile(r"\b(?:sudo|rm|kill|curl|wget|chmod|chown|dd|mkfs|reboot|shutdown|whoami)\b", re.IGNORECASE),
        re.compile(r"(\$\(|[;|<>&]|\beval\b|\bexec\b)"),
    ]

    @classmethod
    def sanitize(cls, raw: str, max_words: int = DEFAULT_MAX_WORDS) -> Optional[str]:
        """Clean and validate output string. Returns None if output is invalid or suspicious."""
        if not raw:
            return None

        # Check for suspicious shell commands or injection operators early
        for pattern in cls.SUSPICIOUS_SHELL_PATTERNS:
            if pattern.search(raw):
                return None

        # 1. Strip ANSI escapes and terminal control codes
        cleaned = cls.ANSI_ESCAPE_RE.sub("", raw)
        cleaned = cls.CONTROL_CHAR_RE.sub(" ", cleaned)

        # 2. Strip emojis
        cleaned = cls.EMOJI_RE.sub("", cleaned)

        # 3. Strip Markdown characters: bold/italics markers, hashes, blockquotes
        cleaned = re.sub(r"```[a-zA-Z0-9_-]*", "", cleaned)
        cleaned = cleaned.replace("```", "")
        cleaned = re.sub(r"[*_~#>`]", "", cleaned)

        # 4. Strip leading/trailing quotation marks
        cleaned = cleaned.strip(" \t\r\n'\"`“”‘’")

        # 5. Collapse all whitespace into single spaces and remove space before punctuation
        cleaned = " ".join(cleaned.split())
        cleaned = re.sub(r"\s+([.!?])", r"\1", cleaned)
        if not cleaned:
            return None

        # 6. Extract only the first sentence
        # Split on sentence boundaries: '.', '!', '?'
        sentence_match = re.split(r"(?<=[.!?])\s+", cleaned)
        first_sentence = sentence_match[0].strip() if sentence_match else cleaned
        if not first_sentence:
            return None

        # Ensure sentence has terminal punctuation
        if first_sentence[-1] not in ".!?":
            first_sentence += "."

        # 7. Bound word count to fewer than max_words
        words = first_sentence.split()
        if len(words) > max_words:
            # Truncate at word boundary
            truncated = " ".join(words[:max_words - 1])
            first_sentence = truncated.rstrip(",;:-") + "..."

        return first_sentence


# ==============================================================================
# 3. STRICT LOCALHOST-ONLY HTTP CLIENT
# ==============================================================================

class NetworkSecurityError(Exception):
    """Raised when an outbound network request attempts to contact a non-loopback address."""


class LocalhostNoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuses all HTTP redirects to prevent SSRF and DNS rebinding attacks."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise NetworkSecurityError(f"HTTP Redirect to '{newurl}' is strictly forbidden by GhostTrace security policy.")


class LocalLoopbackClient:
    """Strictly validates loopback destinations and communicates with local Ollama or llama.cpp."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        endpoint: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.provider = provider.lower()
        self.model = model
        self.timeout = max(0.5, min(timeout, 10.0))

        if endpoint:
            self.endpoint = endpoint.rstrip("/")
        else:
            self.endpoint = (
                DEFAULT_OLLAMA_ENDPOINT if self.provider == "ollama" else DEFAULT_LLAMACPP_ENDPOINT
            )

        self._validate_loopback_url(self.endpoint)

    @classmethod
    def _validate_loopback_url(cls, url: str) -> None:
        """Verify that destination is strictly a loopback interface (localhost / 127.0.0.1 / ::1)."""
        parsed = urllib.parse.urlparse(url)
        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https"):
            raise NetworkSecurityError(f"Invalid URI scheme '{scheme}'. Only local HTTP is permitted.")

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise NetworkSecurityError("Missing hostname in local model endpoint.")

        # Reject wildcard or external hostnames
        if hostname not in ALLOWED_LOOPBACK_HOSTS:
            # Test if it resolves to a non-loopback IP
            try:
                addr_infos = socket.getaddrinfo(hostname, None)
                for family, _, _, _, sockaddr in addr_infos:
                    ip = sockaddr[0]
                    ip_obj = ipaddress.ip_address(ip)
                    if not ip_obj.is_loopback:
                        raise NetworkSecurityError(
                            f"Host '{hostname}' resolved to non-loopback IP '{ip}'. "
                            "GhostTrace strictly refuses non-loopback connections."
                        )
            except socket.gaierror as e:
                raise NetworkSecurityError(f"Cannot resolve host '{hostname}': {e}") from e

    def _build_opener(self) -> urllib.request.OpenerDirector:
        """Create urllib opener bypassing all proxies and blocking redirects."""
        # Empty ProxyHandler ensures HTTP_PROXY / ALL_PROXY environment variables are ignored
        no_proxy_handler = urllib.request.ProxyHandler({})
        redirect_blocker = LocalhostNoRedirectHandler()
        return urllib.request.build_opener(no_proxy_handler, redirect_blocker)

    def is_available(self) -> bool:
        """Check if local inference server is running and reachable."""
        opener = self._build_opener()
        probe_url = (
            f"{self.endpoint}/api/tags"
            if self.provider == "ollama"
            else f"{self.endpoint}/health"
        )
        try:
            req = urllib.request.Request(
                probe_url,
                headers={"User-Agent": "GhostTrace-Daemon/0.2.0"},
                method="GET",
            )
            with opener.open(req, timeout=min(self.timeout, 1.0)) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    def generate(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Send chat completion request to local Ollama or llama.cpp daemon."""
        opener = self._build_opener()

        if self.provider == "ollama":
            url = f"{self.endpoint}/api/chat"
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {
                    "num_predict": 40,
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
            }
        else:
            # llama.cpp server compatible OpenAI endpoint
            url = f"{self.endpoint}/v1/chat/completions"
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 40,
                "temperature": 0.7,
                "stream": False,
            }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "GhostTrace-Daemon/0.2.0",
            },
            method="POST",
        )

        try:
            with opener.open(req, timeout=self.timeout) as resp:
                raw_bytes = resp.read()
                raw_str = raw_bytes.decode("utf-8", errors="replace")
                data = json.loads(raw_str)

                if self.provider == "ollama":
                    msg = data.get("message", {})
                    return msg.get("content", "").strip()
                else:
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                return None
        except Exception:
            return None


# ==============================================================================
# 4. PERSONA SYSTEM
# ==============================================================================

@dataclass
class Persona:
    """Configured ghost persona with system prompt and canned fallback pools."""

    name: str
    system_prompt: str
    canned_normal: List[str] = field(default_factory=list)
    canned_failure: List[str] = field(default_factory=list)
    canned_dramatic: List[str] = field(default_factory=list)
    canned_farewell: List[str] = field(default_factory=list)
    canned_midnight: List[str] = field(default_factory=list)
    canned_thirteen: List[str] = field(default_factory=list)


class PersonaManager:
    """Loads and validates plain-text persona files from ghosts/ directory."""

    NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

    def __init__(self, ghosts_dir: Optional[Path] = None):
        if ghosts_dir:
            self.ghosts_dir = ghosts_dir
        else:
            # Default to ghosts/ folder relative to project root
            self.ghosts_dir = Path(__file__).resolve().parent / "ghosts"

    def list_personas(self) -> List[str]:
        """List available persona names."""
        if not self.ghosts_dir.is_dir():
            return ["poltergeist"]
        names = []
        for item in sorted(self.ghosts_dir.iterdir()):
            if item.is_file() and not item.name.startswith("."):
                names.append(item.name)
        return names or ["poltergeist"]

    def load_persona(self, name: str) -> Persona:
        """Safely load a persona file by name. Rejects directory traversal attempts."""
        clean_name = name.strip()
        if not self.NAME_PATTERN.match(clean_name):
            clean_name = "poltergeist"

        persona_file = self.ghosts_dir / clean_name
        if not persona_file.is_file():
            # Fall back to poltergeist or default internal
            persona_file = self.ghosts_dir / "poltergeist"

        if persona_file.is_file():
            try:
                return self._parse_persona_file(clean_name, persona_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Built-in internal fallback persona
        return Persona(
            name="poltergeist",
            system_prompt=(
                "You are Poltergeist, a playful and eerie spirit inhabiting a terminal. "
                "Whisper a short, uncanny, context-aware observation about the command just run. "
                "Rules: exactly one sentence under 20 words. No quotes. No emojis. No markdown."
            ),
            canned_normal=[
                "A flicker in the registers marks your passage through the shell.",
                "Your keystrokes leave warm ghostly trails on cold silicon.",
                "Another command swallowed whole by the endless terminal void.",
                "The electrons hum with a mischievous spark across the bus lines.",
            ],
            canned_failure=[
                "The machine coughs up cold static and refuses your command.",
                "A shudder in the stack; your command dissolved into nothingness.",
                "Even the dead cannot force that syntax through the kernel.",
            ],
            canned_dramatic=[
                "A violent tremor tears through the process table!",
                "Destruction is absolute; what you severed here is lost forever.",
                "Root power disturbs ancient spirits slumbering in the machine.",
            ],
            canned_farewell=[
                "I dissolve back into the swap space until your next shell awakens.",
            ],
            canned_midnight=[
                "The midnight hour is ours; the terminal glows with ethereal phosphor.",
            ],
            canned_thirteen=[
                "Thirteen steps down into the terminal underworld; beware the next command.",
            ],
        )

    def _parse_persona_file(self, name: str, text: str) -> Persona:
        """Parse structured sections from a persona file."""
        sections: Dict[str, List[str]] = {}
        current_section = "system_prompt"
        sections[current_section] = []

        for line in text.splitlines():
            line_str = line.strip()
            if line_str.startswith("#") and not line_str.startswith("["):
                continue
            if line_str.startswith("[") and line_str.endswith("]"):
                current_section = line_str[1:-1].strip().lower()
                if current_section not in sections:
                    sections[current_section] = []
                continue
            if line_str:
                sections[current_section].append(line_str)

        system_prompt = " ".join(sections.get("system_prompt", ["You are an eerie terminal ghost."]))
        return Persona(
            name=name,
            system_prompt=system_prompt,
            canned_normal=sections.get("canned_normal", []),
            canned_failure=sections.get("canned_failure", []),
            canned_dramatic=sections.get("canned_dramatic", []),
            canned_farewell=sections.get("canned_farewell", []),
            canned_midnight=sections.get("canned_midnight", []),
            canned_thirteen=sections.get("canned_thirteen", []),
        )


# ==============================================================================
# 5. DRAMATIC EVENT DETECTOR
# ==============================================================================

class DramaticEventDetector:
    """Detects dramatic terminal moments that warrant 100% whisper triggering."""

    DRAMATIC_EXIT_CODES = {127, 130, 139}

    @classmethod
    def is_dramatic(cls, cmd: str, args: str, exit_status: int) -> bool:
        """Return True if command or exit status matches a dramatic trigger."""
        # 1. Dramatic exit codes (127: not found, 130: Ctrl-C, 139: segfault)
        if exit_status in cls.DRAMATIC_EXIT_CODES:
            return True

        full = f"{cmd} {args}".strip().lower()

        # 2. Destructive or high-privilege command patterns
        if "rm -rf" in full or "rm -fr" in full or "rm -r -f" in full:
            return True
        if full.startswith("sudo ") or full == "sudo":
            return True
        if "kill -9" in full or "kill -sigkill" in full:
            return True
        if "git reset --hard" in full or "git clean -fdx" in full:
            return True

        return False


# ==============================================================================
# 6. SESSION METADATA & PERSISTENCE
# ==============================================================================

class SessionStateManager:
    """Manages minimal, privacy-safe local session statistics.

    Never stores raw commands, secrets, or output.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or get_haunt_dir()
        self.stats_file = self.data_dir / "stats.json"

    def load_stats(self) -> Dict[str, Any]:
        """Load session statistics from disk."""
        if self.stats_file.is_file():
            try:
                data = json.loads(self.stats_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {
            "date": datetime.date.today().isoformat(),
            "daily_count": 0,
            "session_count": 0,
            "consecutive_failures": 0,
            "recent_commands": [],
        }

    def record_command(self, cmd_name: str, exit_status: int) -> Dict[str, Any]:
        """Record a sanitized command name and update counts."""
        stats = self.load_stats()
        today = datetime.date.today().isoformat()

        if stats.get("date") != today:
            stats["date"] = today
            stats["daily_count"] = 0

        stats["daily_count"] = stats.get("daily_count", 0) + 1
        stats["session_count"] = stats.get("session_count", 0) + 1

        if exit_status != 0:
            stats["consecutive_failures"] = stats.get("consecutive_failures", 0) + 1
        else:
            stats["consecutive_failures"] = 0

        # Maintain bounded ring buffer of last 20 sanitized command names
        recent = stats.get("recent_commands", [])
        if not isinstance(recent, list):
            recent = []
        safe_name = Path(cmd_name.strip()).name[:24] if cmd_name else "cmd"
        recent.append(safe_name)
        stats["recent_commands"] = recent[-20:]

        try:
            temp_file = self.stats_file.with_suffix(".tmp")
            temp_file.write_text(json.dumps(stats, indent=2), encoding="utf-8")
            os.chmod(temp_file, 0o600)
            temp_file.replace(self.stats_file)
        except Exception:
            pass

        return stats

    def forget(self) -> None:
        """Securely wipe session stats and runtime files."""
        if self.stats_file.is_file():
            try:
                self.stats_file.unlink()
            except Exception:
                pass

        # Clear run directory
        run_dir = get_run_dir()
        if run_dir.is_dir():
            for f in run_dir.glob("*"):
                try:
                    if f.is_file():
                        f.unlink()
                except Exception:
                    pass


# ==============================================================================
# 7. WHISPER PIPELINE & WORKER
# ==============================================================================

class WhisperPipeline:
    """Coordinates prompt construction, inference, output sanitization, and fallback."""

    def __init__(
        self,
        persona_name: str = "poltergeist",
        provider: str = DEFAULT_PROVIDER,
        model: str = DEFAULT_MODEL,
        endpoint: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        chance: int = DEFAULT_CHANCE,
        send_args: bool = False,
        offline: bool = False,
    ):
        self.persona_name = persona_name
        self.provider = provider
        self.model = model
        if endpoint:
            self.endpoint = endpoint.rstrip("/")
        else:
            self.endpoint = (
                DEFAULT_OLLAMA_ENDPOINT if self.provider == "ollama" else DEFAULT_LLAMACPP_ENDPOINT
            )
        self.timeout = timeout
        self.chance = max(0, min(chance, 100))
        self.send_args = send_args
        self.offline = offline

        self.persona_mgr = PersonaManager()
        self.persona = self.persona_mgr.load_persona(self.persona_name)
        self.state_mgr = SessionStateManager()

        if not self.offline:
            self.client: Optional[LocalLoopbackClient] = LocalLoopbackClient(
                provider=self.provider,
                endpoint=self.endpoint,
                model=self.model,
                timeout=self.timeout,
            )
        else:
            self.client = None

    def should_whisper(
        self,
        cmd: str,
        args: str,
        exit_status: int,
        session_count: int,
    ) -> Tuple[bool, bool, str]:
        """Determine if a whisper should trigger.

        Returns (should_trigger, is_dramatic, reason).
        """
        # Dramatic events always trigger (100% chance)
        if DramaticEventDetector.is_dramatic(cmd, args, exit_status):
            return True, True, "dramatic_event"

        # Special moment: 13th command
        if session_count == 13 or (session_count > 0 and session_count % 13 == 0):
            return True, True, "thirteenth_command"

        # Special moment: Midnight to 05:00
        hour = datetime.datetime.now().hour
        if 0 <= hour < 5:
            # Midnight hours increase chance to at least 70%
            effective_chance = max(self.chance, 70)
        else:
            effective_chance = self.chance

        # Standard chance roll
        roll = random.randint(1, 100)
        if roll <= effective_chance:
            return True, False, "chance_roll"

        return False, False, "skipped_chance"

    def generate_whisper(
        self,
        cmd: str,
        args: str,
        exit_status: int,
        cwd_base: str,
        session_count: int,
        is_dramatic: bool = False,
    ) -> str:
        """Produce a whisper using local LLM, or fallback to deterministic canned pool."""
        # 1. Sanitize command and arguments
        clean_cmd, safe_args = SecretRedactor.sanitize_command_for_prompt(
            cmd, args, allow_args=self.send_args
        )

        hour = datetime.datetime.now().hour

        # 2. If offline mode or client unavailable, immediately use deterministic fallback
        if self.offline or self.client is None or not self.client.is_available():
            return self._fallback_whisper(clean_cmd, exit_status, hour, session_count, is_dramatic)

        # 3. Construct prompt
        arg_text = f" with args {safe_args}" if safe_args else ""
        outcome = "succeeded" if exit_status == 0 else f"failed with exit code {exit_status}"
        user_prompt = (
            f"The user ran '{clean_cmd}'{arg_text} in directory '{cwd_base}'. "
            f"Command {outcome}. Local hour is {hour:02d}:00. Session command #{session_count}. "
            "Whisper your reaction."
        )

        try:
            raw_output = self.client.generate(self.persona.system_prompt, user_prompt)
            if raw_output:
                sanitized = OutputSanitizer.sanitize(raw_output)
                if sanitized:
                    return sanitized
        except Exception:
            pass

        # 4. Fallback on any failure, timeout, or malformed response
        return self._fallback_whisper(clean_cmd, exit_status, hour, session_count, is_dramatic)

    def _fallback_whisper(
        self,
        cmd: str,
        exit_status: int,
        hour: int,
        session_count: int,
        is_dramatic: bool,
    ) -> str:
        """Select a deterministic canned whisper from the active persona."""
        if is_dramatic and self.persona.canned_dramatic:
            return random.choice(self.persona.canned_dramatic)

        if (session_count == 13 or (session_count > 0 and session_count % 13 == 0)) and self.persona.canned_thirteen:
            return random.choice(self.persona.canned_thirteen)

        if (0 <= hour < 5) and self.persona.canned_midnight:
            return random.choice(self.persona.canned_midnight)

        if exit_status != 0 and self.persona.canned_failure:
            return random.choice(self.persona.canned_failure)

        if self.persona.canned_normal:
            return random.choice(self.persona.canned_normal)

        return "The machine acknowledges your command in eerie silence."

    def generate_tale(self) -> str:
        """Generate a 4-sentence ghost story summarizing the session's journey."""
        stats = self.state_mgr.load_stats()
        recent = stats.get("recent_commands", [])
        commands_str = ", ".join(recent[-15:]) if recent else "keystrokes in the dark"

        if not self.offline and self.client is not None and self.client.is_available():
            system_prompt = (
                f"{self.persona.system_prompt} "
                "Tell a four-sentence ghost story recounting what happened during this terminal session. "
                "Constraint: Exactly four sentences. No markdown, quotes, or emojis."
            )
            user_prompt = f"The terminal witnessed these commands: {commands_str}. Weave them into a 4-sentence ghost tale."
            try:
                raw = self.client.generate(system_prompt, user_prompt)
                if raw:
                    # Sanitize and ensure sentences are cleanly separated
                    cleaned = OutputSanitizer.ANSI_ESCAPE_RE.sub("", raw)
                    cleaned = OutputSanitizer.CONTROL_CHAR_RE.sub(" ", cleaned)
                    cleaned = OutputSanitizer.EMOJI_RE.sub("", cleaned).strip(' \t\r\n"\'`')
                    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
                    if len(sentences) >= 3:
                        return " ".join(sentences[:4])
            except Exception:
                pass

        # Deterministic 4-sentence fallback tale
        return (
            f"You began your journey typing commands into the cold void of {recent[0] if recent else 'the terminal'}. "
            f"With every keystroke, unseen entities stirred beneath the surface of the filesystem. "
            f"Through {commands_str}, the spirit watched your progress with patient curiosity. "
            "Now the session rests, but the digital footprints linger in the machine forever."
        )


# ==============================================================================
# 8. CLI SUBCOMMAND HANDLERS
# ==============================================================================

def cmd_whisper(args: argparse.Namespace) -> int:
    """Handle a whisper generation request (can run as asynchronous background worker)."""
    pipe = WhisperPipeline(
        persona_name=args.persona or os.environ.get("HAUNT_GHOST", "poltergeist"),
        provider=args.provider or os.environ.get("HAUNT_PROVIDER", DEFAULT_PROVIDER),
        model=args.model or os.environ.get("HAUNT_MODEL", DEFAULT_MODEL),
        endpoint=args.endpoint or os.environ.get("HAUNT_ENDPOINT"),
        timeout=args.timeout if args.timeout is not None else float(os.environ.get("HAUNT_TIMEOUT", DEFAULT_TIMEOUT)),
        chance=args.chance if args.chance is not None else int(os.environ.get("HAUNT_CHANCE", DEFAULT_CHANCE)),
        send_args=bool(int(os.environ.get("HAUNT_SEND_ARGS", "0"))),
        offline=bool(int(os.environ.get("HAUNT_OFFLINE", "0"))),
    )

    stats = pipe.state_mgr.record_command(args.cmd, args.status)
    session_count = stats.get("session_count", 1)

    should_run, is_dramatic, _ = pipe.should_whisper(
        cmd=args.cmd,
        args=args.args or "",
        exit_status=args.status,
        session_count=session_count,
    )

    if not should_run:
        return 0

    whisper_text = pipe.generate_whisper(
        cmd=args.cmd,
        args=args.args or "",
        exit_status=args.status,
        cwd_base=args.cwd,
        session_count=session_count,
        is_dramatic=is_dramatic,
    )

    if not whisper_text:
        return 0

    # If req_id was supplied, write result file atomically for shell precmd retrieval
    if args.req_id:
        run_dir = get_run_dir()
        # Clean up stale temporary files older than 30s
        try:
            now = time.time()
            for f in run_dir.glob("req_*.res*"):
                if f.is_file() and (now - f.stat().st_mtime) > 30.0:
                    f.unlink()
        except Exception:
            pass

        res_tmp = run_dir / f"{args.req_id}.res.tmp"
        res_file = run_dir / f"{args.req_id}.res"
        try:
            res_tmp.write_text(whisper_text, encoding="utf-8")
            os.chmod(res_tmp, 0o600)
            res_tmp.replace(res_file)
        except Exception:
            pass
    else:
        # Direct synchronous output
        print(whisper_text)

    return 0


def cmd_tale(args: argparse.Namespace) -> int:
    """Print a 4-sentence ghost tale of the session."""
    pipe = WhisperPipeline(
        persona_name=args.persona or os.environ.get("HAUNT_GHOST", "poltergeist"),
        provider=args.provider or os.environ.get("HAUNT_PROVIDER", DEFAULT_PROVIDER),
        model=args.model or os.environ.get("HAUNT_MODEL", DEFAULT_MODEL),
        endpoint=args.endpoint or os.environ.get("HAUNT_ENDPOINT"),
        timeout=args.timeout if args.timeout is not None else float(os.environ.get("HAUNT_TIMEOUT", DEFAULT_TIMEOUT)),
        offline=bool(int(os.environ.get("HAUNT_OFFLINE", "0"))),
    )
    story = pipe.generate_tale()
    print(story)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Print current Haunt possession and model status."""
    persona_name = os.environ.get("HAUNT_GHOST", "poltergeist")
    provider = os.environ.get("HAUNT_PROVIDER", DEFAULT_PROVIDER)
    model = os.environ.get("HAUNT_MODEL", DEFAULT_MODEL)
    chance = os.environ.get("HAUNT_CHANCE", str(DEFAULT_CHANCE))
    timeout = os.environ.get("HAUNT_TIMEOUT", str(DEFAULT_TIMEOUT))
    offline = bool(int(os.environ.get("HAUNT_OFFLINE", "0")))

    pipe = WhisperPipeline(
        persona_name=persona_name,
        provider=provider,
        model=model,
        timeout=float(timeout),
        offline=offline,
    )
    is_alive = False if offline else (pipe.client.is_available() if pipe.client else False)
    stats = pipe.state_mgr.load_stats()

    print("--- GhostTrace Status ---")
    print(f"Possession:      ACTIVE (PID {os.getpid()})")
    print(f"Persona:         {persona_name}")
    print(f"Model:           {model} ({provider})")
    print(f"Daemon Endpoint: {pipe.endpoint if pipe.client else 'OFFLINE'}")
    print(f"Core Status:     {'ONLINE (Localhost)' if is_alive else 'OFFLINE (Canned Fallback)'}")
    print(f"Whisper Chance:  {chance}%")
    print(f"Timeout:         {timeout}s")
    print(f"Session Cmds:    {stats.get('session_count', 0)} (Daily: {stats.get('daily_count', 0)})")
    return 0


def cmd_ghosts(args: argparse.Namespace) -> int:
    """List all available personas in ghosts/ directory."""
    mgr = PersonaManager()
    personas = mgr.list_personas()
    active = os.environ.get("HAUNT_GHOST", "poltergeist")
    print("Available Ghost Personas:")
    for p in personas:
        marker = " (active)" if p == active else ""
        print(f"  - {p}{marker}")
    return 0


def cmd_forget(args: argparse.Namespace) -> int:
    """Wipe session stats and temporary run files."""
    mgr = SessionStateManager()
    mgr.forget()
    print("The ghost has forgotten all session footprints and keystrokes.")
    return 0


# ==============================================================================
# MAIN PARSER ENTRYPOINT
# ==============================================================================

def main(cli_args: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ghostd.py",
        description="GhostTrace local inference worker and session daemon.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # whisper subcommand
    p_whisper = subparsers.add_parser("whisper", help="Generate command whisper")
    p_whisper.add_argument("--cmd", required=True, help="Command name")
    p_whisper.add_argument("--args", default="", help="Command argument string")
    p_whisper.add_argument("--status", type=int, default=0, help="Command exit status")
    p_whisper.add_argument("--cwd", default="terminal", help="Current working directory basename")
    p_whisper.add_argument("--req-id", default=None, help="Unique request ID for async retrieval")
    p_whisper.add_argument("--persona", default=None)
    p_whisper.add_argument("--provider", default=None)
    p_whisper.add_argument("--model", default=None)
    p_whisper.add_argument("--endpoint", default=None)
    p_whisper.add_argument("--timeout", type=float, default=None)
    p_whisper.add_argument("--chance", type=int, default=None)

    # tale subcommand
    p_tale = subparsers.add_parser("tale", help="Generate a 4-sentence ghost tale of the session")
    p_tale.add_argument("--persona", default=None)
    p_tale.add_argument("--provider", default=None)
    p_tale.add_argument("--model", default=None)
    p_tale.add_argument("--endpoint", default=None)
    p_tale.add_argument("--timeout", type=float, default=None)

    # status subcommand
    subparsers.add_parser("status", help="Print GhostTrace status")

    # ghosts subcommand
    subparsers.add_parser("ghosts", help="List available ghost personas")

    # forget subcommand
    subparsers.add_parser("forget", help="Wipe session history and cached stats")

    parsed = parser.parse_args(cli_args)

    if parsed.subcommand == "whisper":
        return cmd_whisper(parsed)
    elif parsed.subcommand == "tale":
        return cmd_tale(parsed)
    elif parsed.subcommand == "status":
        return cmd_status(parsed)
    elif parsed.subcommand == "ghosts":
        return cmd_ghosts(parsed)
    elif parsed.subcommand == "forget":
        return cmd_forget(parsed)

    return 0


if __name__ == "__main__":
    sys.exit(main())

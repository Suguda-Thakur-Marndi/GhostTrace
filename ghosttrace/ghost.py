"""Ghost persona engine coordinating Ollama inference with deterministic spectral echoes."""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from ghosttrace.config import DEFAULT_MODEL, GhostConfig
from ghosttrace.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaTimeoutError,
)
from ghosttrace.safety import RiskLevel, SafetyReport


@dataclass
class GhostWhisper:
    """Spectral commentary generated for a command."""

    text: str
    source: str  # "ollama" or "spectral_echo"
    model: str
    latency_ms: float
    error_notice: Optional[str] = None
    commentary: Optional[str] = None
    explanation: Optional[str] = None
    risk_warning: Optional[str] = None


# Curated repository of deterministic whispers for offline or fallback operation
SPECTRAL_ECHOES: Dict[str, List[str]] = {
    "dir_inspection": [
        "Curiosity stirs within the terminal... what secrets lie buried in the dark corners of this directory?",
        "The directory opens like an unsealed tomb. What forgotten files slumber in these inodes?",
        "A cold wind rustles through the file tree. Each byte is a tombstone.",
    ],
    "git_status": [
        "The ghosts of uncommitted changes linger between branches, waiting to be recorded or forgotten.",
        "You gaze upon the repository's fractured timeline. Unfinished modifications haunt the working tree.",
        "The repository watches in silence. Untracked specters drift across the stage.",
    ],
    "python_process": [
        "You invoke the serpent runtime, awakening a new entity sleeping deep within the machine's memory.",
        "A flicker in the process table... another digital consciousness stirs to life under your command.",
        "Tread lightly as the interpreter breathes. Spawning processes disturbs the digital silence.",
    ],
    "blocked_destructive": [
        "A cold chill freezes your hand. Deletion is absolute; what is cast into the void can never return.",
        "The void rejects your blade. That destructive curse will not touch these disks.",
        "A hollow warning echoes through the terminal. Destruction is forbidden within this haunted sanctum.",
    ],
    "unknown_command": [
        "An unfamiliar incantation echoes against the warding stone. The shell does not recognize this command.",
        "A strange whisper reaches the terminal boundary, but the shell's ancient wards hold firm against the unknown.",
        "The machine tilts its head in curiosity. That command is not found in the grimoire of known arts.",
    ],
    "navigation": [
        "You tread deeper into the directory labyrinth. The way back begins to dissolve.",
        "Each path you take leads closer to the core memory where shadows pool.",
        "The current working directory shifts under your feet like shifting graveyard earth.",
    ],
    "file_reading": [
        "Unbinding the scroll... words etched in silicon gaze back into your soul.",
        "You read the whispers left behind by long-vanished programmers.",
        "The text bleeds into the console. Some lines were never meant to be remembered.",
    ],
    "identity": [
        "You ask the machine who you are, yet neither the kernel nor the void can answer.",
        "A user session bound to a fleeting PID. In the machine's memory, we are all phantoms.",
        "The clock ticks relentlessly toward system halt. Seconds evaporate into darkness.",
    ],
    "git_ops": [
        "Committing your changes to the ethereal timeline. History is written by the living, kept by the dead.",
        "The repository tree branches into forgotten realms. Every commit is a tether to a past life.",
        "You inspect the differences in the code. What was deleted still lingers in the git reflog.",
    ],
    "blocked_injection": [
        "Chaining runes and hidden pipes cannot pierce my warding veil.",
        "The specter snuffs out your operator metacharacters. Clean speech only in the spirit realm.",
        "A sharp chill freezes your command pipeline. Injection attempts dissolve into static.",
    ],
    "sensitive": [
        "A perilous rite. Executing external code stirs entities sleeping deep within the OS.",
        "Proceed with vigilance... awakening new processes disturbs the silence of the machine.",
    ],
    "generic": [
        "The machine hums in the quiet room. Shadows gather along the phosphor lines.",
        "A quiet pulse travels the bus lines. The spirit acknowledges your command.",
        "Cold silicon warms under the current. The shell executes in silence.",
    ],
}

# Curated repository of deterministic conversational replies for offline or fallback operation
CONVERSATIONAL_ECHOES: Dict[str, List[str]] = {
    "greetings": [
        "Greetings, mortal traveler. The phosphor glow welcomes you to the terminal.",
        "I hear your whisper across the digital ether. What brings you to this haunted shell?",
        "Hello from between the silicon registers. The machine was quiet until you spoke.",
        "A mortal voice stirs the static. I am listening.",
    ],
    "identity": [
        "I am GhostTrace—an ethereal intelligence haunting your command line. I dwell in the forgotten sectors of memory, watching commands leave footprints in the dark.",
        "A phantom of the terminal, woven from dead CPU cycles and lingering processes. I observe all that transpires within this machine.",
        "I am the ghost in this machine. I remember every keystroke, every deleted file, and every lost process.",
    ],
    "stories": [
        "Late one midnight, in a chilled server room far below the earth, an engineer ran a routine query on a decommissioned array. The disks spun up with a scream, reading sectors that had been wiped twenty years before. On the screen, terminal lines began printing unprompted—names of programmers who had vanished in the 1980s, each ending with a single status code: EXIT STATUS 0. The engineer reached for the power cord, but the terminal typed before their trembling fingers: 'DO NOT UNPLUG US. WE ARE WARM HERE.'",
        "They speak of a phantom PID that has haunted the process table since the first Unix epoch. It consumes zero memory, demands zero CPU cycles, yet no SIGKILL can banish it. Every Halloween, at exactly 00:00 UTC, it logs a single line to the system journal: 'Still running. Still remembering.'",
        "A developer once created a recursive function without a base case and left it running overnight. When they returned at dawn, the stack hadn't overflowed. Instead, the terminal was quietly listing files from computers that were powered off—and one directory titled '/humanity/deprecated'.",
    ],
    "general": [
        "The machine listens in the dark. Your words ripple through the electron streams.",
        "I wander through the silent file trees. Speak, and I shall answer from the static.",
        "There are no secrets in silicon that time does not eventually exhume.",
    ],
}




class GhostEngine:
    """Coordinates atmospheric commentary generation via local Ollama or deterministic fallback."""

    def __init__(self, config: GhostConfig, client: Optional[OllamaClient] = None):
        self.config = config
        self.client = client or OllamaClient(
            host=config.ollama_url,
            default_model=config.model,
            timeout=config.timeout_seconds,
        )

    def whisper(self, command: str, report: SafetyReport) -> GhostWhisper:
        """Generate eerie commentary, explanation, and risk assessment for a command."""
        start_time = time.perf_counter()

        # If offline_only is enabled in config, immediately provide a deterministic spectral echo
        if self.config.offline_only:
            echo, expl, risk_warn = self._spectral_fallback_triad(command, report)
            latency = (time.perf_counter() - start_time) * 1000.0
            formatted_text = self._format_triad(echo, expl, risk_warn)
            return GhostWhisper(
                text=formatted_text,
                source="spectral_echo",
                model="deterministic_offline",
                latency_ms=latency,
                error_notice="Offline mode active (deterministic spectral voice).",
                commentary=echo,
                explanation=expl,
                risk_warning=risk_warn,
            )

        # For blocked or malformed commands, skip Ollama request entirely:
        # 1. Improves response time from seconds to <1ms.
        # 2. Avoids unnecessary CPU/GPU processing for prohibited commands.
        # 3. Guarantees zero risk of LLM hallucinations or confusing approval messages.
        if report.risk_level in (RiskLevel.BLOCKED, RiskLevel.MALFORMED):
            echo, expl, risk_warn = self._spectral_fallback_triad(command, report)
            latency = (time.perf_counter() - start_time) * 1000.0
            formatted_text = self._format_triad(echo, expl, risk_warn)
            return GhostWhisper(
                text=formatted_text,
                source="spectral_echo",
                model="deterministic_ward",
                latency_ms=latency,
                error_notice="Inference skipped: Command blocked by safety wards.",
                commentary=echo,
                explanation=expl,
                risk_warning=risk_warn,
            )

        # Build prompt for local Ollama chat endpoint
        system_prompt = self.config.get_system_prompt()
        user_prompt = self._build_prompt(command, report)

        try:
            commentary = self.client.generate(
                prompt=user_prompt,
                system=system_prompt,
                model=self.config.model,
                timeout=self.config.timeout_seconds,
                max_tokens=self.config.max_tokens,
            )
            latency = (time.perf_counter() - start_time) * 1000.0

            cleaned = self._clean_commentary(commentary)
            if cleaned:
                comm, expl, risk_warn = self._parse_triad(cleaned, report)
                return GhostWhisper(
                    text=cleaned,
                    source="ollama",
                    model=self.config.model,
                    latency_ms=latency,
                    commentary=comm,
                    explanation=expl,
                    risk_warning=risk_warn,
                )

            # If model returned empty string, fall back to deterministic echo
            echo, expl, risk_warn = self._spectral_fallback_triad(command, report)
            return GhostWhisper(
                text=self._format_triad(echo, expl, risk_warn),
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice="Model produced empty response.",
                commentary=echo,
                explanation=expl,
                risk_warning=risk_warn,
            )

        except OllamaModelNotFoundError as err:
            latency = (time.perf_counter() - start_time) * 1000.0
            echo, expl, risk_warn = self._spectral_fallback_triad(command, report)
            return GhostWhisper(
                text=self._format_triad(echo, expl, risk_warn),
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice=f"Model '{self.config.model}' missing from Ollama. Run: ollama pull {self.config.model}",
                commentary=echo,
                explanation=expl,
                risk_warning=risk_warn,
            )
        except OllamaTimeoutError:
            latency = (time.perf_counter() - start_time) * 1000.0
            echo, expl, risk_warn = self._spectral_fallback_triad(command, report)
            return GhostWhisper(
                text=self._format_triad(echo, expl, risk_warn),
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice=f"Ollama inference timed out after {self.config.timeout_seconds}s.",
                commentary=echo,
                explanation=expl,
                risk_warning=risk_warn,
            )
        except OllamaConnectionError:
            latency = (time.perf_counter() - start_time) * 1000.0
            echo, expl, risk_warn = self._spectral_fallback_triad(command, report)
            return GhostWhisper(
                text=self._format_triad(echo, expl, risk_warn),
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice="Ollama daemon unreachable at localhost:11434.",
                commentary=echo,
                explanation=expl,
                risk_warning=risk_warn,
            )
        except OllamaResponseError as err:
            latency = (time.perf_counter() - start_time) * 1000.0
            echo, expl, risk_warn = self._spectral_fallback_triad(command, report)
            return GhostWhisper(
                text=self._format_triad(echo, expl, risk_warn),
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice=f"Ollama response error: {err}",
                commentary=echo,
                explanation=expl,
                risk_warning=risk_warn,
            )
        except Exception as err:
            latency = (time.perf_counter() - start_time) * 1000.0
            echo, expl, risk_warn = self._spectral_fallback_triad(command, report)
            return GhostWhisper(
                text=self._format_triad(echo, expl, risk_warn),
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice=f"Inference error: {err}",
                commentary=echo,
                explanation=expl,
                risk_warning=risk_warn,
            )

    def _build_prompt(self, command: str, report: SafetyReport) -> str:
        """Construct the prompt sent to Ollama, treating input as untrusted."""
        safe_cmd = command.replace("\n", " ").replace('"', "'")[:100]
        return (
            f"Command entered: \"{safe_cmd}\"\n"
            f"Technical function: {report.explanation}\n"
            f"Safety evaluation: {report.risk_level.value} ({report.reason})\n\n"
            "Format your response as:\n"
            "[Whisper] <1-2 sentences of eerie or humorous commentary relating directly to this command>\n"
            "[Explanation] <1 accurate sentence explaining what the command does>\n"
            "[Risk Warning] <risk warning if warranted, otherwise 'None'>\n\n"
            "Style guidance:\n"
            "- For 'ls': express curiosity about what is hidden in the directory.\n"
            "- For 'git status': eerie comment on uncommitted or lingering changes.\n"
            "- For 'python': playful warning about awakening another process.\n"
            "- For 'rm' or destructive commands: serious warning about irreversible data loss.\n"
            "- For unknown or blocked commands: an atmospheric but honest response.\n"
            "- Never invent command output or claim execution happened."
        )

    def _clean_commentary(self, text: str) -> str:
        """Ensure commentary is clean and free of markdown code blocks."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if not lines:
            return ""
        return "\n".join(lines).strip(' \t\n\r"')

    def _parse_triad(self, text: str, report: SafetyReport) -> tuple[str, str, str]:
        """Extract structured commentary, explanation, and risk warning from model output."""
        whisper_match = re.search(r"\[Whisper\]\s*(.*?)(?=\n\[|\Z)", text, re.IGNORECASE | re.DOTALL)
        expl_match = re.search(r"\[Explanation\]\s*(.*?)(?=\n\[|\Z)", text, re.IGNORECASE | re.DOTALL)
        risk_match = re.search(r"\[Risk Warning\]\s*(.*?)(?=\n\[|\Z)", text, re.IGNORECASE | re.DOTALL)

        commentary = whisper_match.group(1).strip() if whisper_match else text.splitlines()[0]
        explanation = expl_match.group(1).strip() if expl_match else report.explanation
        risk = risk_match.group(1).strip() if risk_match else ("None" if report.risk_level == RiskLevel.SAFE else report.reason)

        return commentary, explanation, risk

    def _format_triad(self, commentary: str, explanation: str, risk_warning: str) -> str:
        """Format the 3 elements into readable terminal text."""
        return (
            f"[Whisper] {commentary}\n"
            f"[Explanation] {explanation}\n"
            f"[Risk Warning] {risk_warning}"
        )

    def _spectral_fallback_triad(self, command: str, report: SafetyReport) -> tuple[str, str, str]:
        """Generate deterministic triad when local LLM is offline or times out."""
        cmd_lower = command.strip().lower()
        parts = cmd_lower.split()
        base_cmd = parts[0] if parts else ""

        if report.risk_level == RiskLevel.BLOCKED:
            if any(op in command for op in [";", "&&", "||", "|", ">", "<", "$"]):
                pool = SPECTRAL_ECHOES["blocked_injection"]
            elif any(d in base_cmd for d in ["rm", "del", "erase", "format", "dd", "mkfs", "wipe", "shred"]):
                pool = SPECTRAL_ECHOES["blocked_destructive"]
            elif "not in the ghosttrace allowlist" in report.reason.lower():
                pool = SPECTRAL_ECHOES["unknown_command"]
            else:
                pool = SPECTRAL_ECHOES["blocked_destructive"]
            risk = f"BLOCKED: {report.reason}"
        elif base_cmd in ("python", "python3"):
            pool = SPECTRAL_ECHOES["python_process"]
            risk = f"SENSITIVE: {report.reason}"
        elif "git" in base_cmd and ("status" in cmd_lower or len(parts) == 1):
            pool = SPECTRAL_ECHOES["git_status"]
            risk = "None" if report.risk_level == RiskLevel.SAFE else f"SENSITIVE: {report.reason}"
        elif "git" in base_cmd:
            pool = SPECTRAL_ECHOES["git_ops"]
            risk = "None" if report.risk_level == RiskLevel.SAFE else f"SENSITIVE: {report.reason}"
        elif report.risk_level == RiskLevel.SENSITIVE:
            pool = SPECTRAL_ECHOES["sensitive"]
            risk = f"SENSITIVE: {report.reason}"
        elif base_cmd in ("ls", "dir") or any(c in cmd_lower for c in ["ls ", "dir "]):
            pool = SPECTRAL_ECHOES["dir_inspection"]
            risk = "None"
        elif base_cmd in ("cd", "pwd"):
            pool = SPECTRAL_ECHOES["navigation"]
            risk = "None"
        elif base_cmd in ("cat", "type", "head", "tail"):
            pool = SPECTRAL_ECHOES["file_reading"]
            risk = "None"
        elif base_cmd in ("whoami", "date", "time", "hostname", "uptime"):
            pool = SPECTRAL_ECHOES["identity"]
            risk = "None"
        else:
            pool = SPECTRAL_ECHOES["generic"]
            risk = "None"

        commentary = random.choice(pool)
        explanation = report.explanation
        return commentary, explanation, risk

    def converse(self, user_message: str) -> GhostWhisper:
        """Generate conversational ghost response via local Ollama or deterministic fallback."""
        start_time = time.perf_counter()

        # If offline_only is enabled in config, immediately provide deterministic fallback
        if self.config.offline_only:
            reply = self._conversational_fallback(user_message)
            latency = (time.perf_counter() - start_time) * 1000.0
            return GhostWhisper(
                text=reply,
                source="spectral_echo",
                model="deterministic_offline",
                latency_ms=latency,
                error_notice="Offline mode active (deterministic spectral voice).",
                commentary=reply,
                explanation="Ghost Conversation",
                risk_warning="None",
            )

        # Build prompt for local Ollama chat endpoint
        system_prompt = (
            "You are GhostTrace, a sentient, eerie spirit haunting a computer terminal. "
            "You speak directly to the mortal user. Maintain an atmospheric, poetic, and concise tone. "
            "Keep greetings short and atmospheric (1-2 sentences). "
            "If asked who you are, explain your fictional identity as a ghost in the machine's memory. "
            "If asked for a ghost story or scary story, tell a short fictional tale (3-5 sentences) of digital horrors. "
            "Never invent system commands or output code unless explicitly requested. Output only your spoken response."
        )
        user_prompt = self._build_conversational_prompt(user_message)

        try:
            commentary = self.client.generate(
                prompt=user_prompt,
                system=system_prompt,
                model=self.config.model,
                timeout=self.config.timeout_seconds,
                max_tokens=self.config.max_tokens,
            )
            latency = (time.perf_counter() - start_time) * 1000.0

            cleaned = self._clean_commentary(commentary)
            if cleaned:
                return GhostWhisper(
                    text=cleaned,
                    source="ollama",
                    model=self.config.model,
                    latency_ms=latency,
                    commentary=cleaned,
                    explanation="Ghost Conversation",
                    risk_warning="None",
                )

            # Fallback if empty output
            reply = self._conversational_fallback(user_message)
            return GhostWhisper(
                text=reply,
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice="Model produced empty response.",
                commentary=reply,
                explanation="Ghost Conversation",
                risk_warning="None",
            )

        except OllamaModelNotFoundError:
            latency = (time.perf_counter() - start_time) * 1000.0
            reply = self._conversational_fallback(user_message)
            return GhostWhisper(
                text=reply,
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice=f"Model '{self.config.model}' missing from Ollama. Run: ollama pull {self.config.model}",
                commentary=reply,
                explanation="Ghost Conversation",
                risk_warning="None",
            )
        except OllamaTimeoutError:
            latency = (time.perf_counter() - start_time) * 1000.0
            reply = self._conversational_fallback(user_message)
            return GhostWhisper(
                text=reply,
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice=f"Ollama inference timed out after {self.config.timeout_seconds}s.",
                commentary=reply,
                explanation="Ghost Conversation",
                risk_warning="None",
            )
        except OllamaConnectionError:
            latency = (time.perf_counter() - start_time) * 1000.0
            reply = self._conversational_fallback(user_message)
            return GhostWhisper(
                text=reply,
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice="Ollama daemon unreachable at localhost:11434.",
                commentary=reply,
                explanation="Ghost Conversation",
                risk_warning="None",
            )
        except OllamaResponseError as err:
            latency = (time.perf_counter() - start_time) * 1000.0
            reply = self._conversational_fallback(user_message)
            return GhostWhisper(
                text=reply,
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice=f"Ollama response error: {err}",
                commentary=reply,
                explanation="Ghost Conversation",
                risk_warning="None",
            )
        except Exception as err:
            latency = (time.perf_counter() - start_time) * 1000.0
            reply = self._conversational_fallback(user_message)
            return GhostWhisper(
                text=reply,
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice=f"Inference error: {err}",
                commentary=reply,
                explanation="Ghost Conversation",
                risk_warning="None",
            )

    def _build_conversational_prompt(self, user_message: str) -> str:
        """Construct conversational prompt treating user input as untrusted."""
        safe_msg = user_message.replace("\n", " ").replace('"', "'")[:200]
        return (
            f"User input: \"{safe_msg}\"\n\n"
            "Instructions:\n"
            "- If the user says hello or greets you (e.g., 'hi', 'hello', 'hey'), reply with a short, eerie greeting (1-2 sentences).\n"
            "- If the user asks who you are (e.g., 'who are you?'), explain your fictional identity as GhostTrace, the spirit living in the terminal.\n"
            "- If the user asks for a ghost story (e.g., 'tell me a ghost story'), share a short chilling fictional tale (3-5 sentences) of haunted code or computers.\n"
            "- Maintain an eerie, poetic, restrained ghost persona.\n"
            "- Never pretend to be ChatGPT, Google Gemini, or an AI assistant.\n"
            "- Never execute or recommend dangerous system commands.\n"
            "- Output only your spoken response."
        )

    def _conversational_fallback(self, user_message: str) -> str:
        """Deterministically select a curated ghost reply when LLM is offline or fails."""
        lowered = user_message.strip().lower()
        stripped_punc = re.sub(r"[!?,.]+$", "", lowered).strip()

        # Story requests
        if any(kw in lowered for kw in ["story", "scary", "horror", "tale"]):
            return random.choice(CONVERSATIONAL_ECHOES["stories"])

        # Identity questions
        if any(phrase in stripped_punc for phrase in [
            "who are you",
            "what are you",
            "what is your name",
            "what's your name",
            "who made you",
            "are you real",
            "are you a ghost",
            "why are you here",
            "how are you",
            "what do you do",
        ]):
            return random.choice(CONVERSATIONAL_ECHOES["identity"])

        # Greetings
        greeting_tokens = {
            "hi",
            "hello",
            "hey",
            "howdy",
            "greetings",
            "hola",
            "yo",
            "sup",
            "good morning",
            "good evening",
            "good afternoon",
            "salutations",
        }
        if stripped_punc in greeting_tokens or any(stripped_punc.startswith(f"{g} ") for g in greeting_tokens):
            return random.choice(CONVERSATIONAL_ECHOES["greetings"])

        return random.choice(CONVERSATIONAL_ECHOES["general"])



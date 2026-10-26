"""Ghost persona engine coordinating Ollama inference with deterministic spectral echoes."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from ghosttrace.config import GhostConfig
from ghosttrace.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
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


# Curated repository of deterministic whispers for offline or fallback operation
SPECTRAL_ECHOES: Dict[str, List[str]] = {
    "dir_inspection": [
        "The directory opens like an unsealed tomb. What secrets lie buried in these inodes?",
        "Dust stirs across the filesystem. You look upon dead files that have not breathed in centuries.",
        "A cold wind rustles through the file tree. Each byte is a tombstone.",
        "You pry open the crypt of storage. Footprints fade as quickly as you list them.",
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
    "blocked_malicious": [
        "The void rejects your blade. Destructive incantations are bound by ancient warding runes.",
        "You sought ruin, mortal, but the shell's spectral wards extinguish your command before it strikes.",
        "A hollow laughter echoes through the terminal. Destruction is forbidden within this haunted sanctum.",
        "The machine trembles, then holds firm. That destructive curse will not touch these disks.",
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
        "The shell records your whisper in the dark. Every keystroke is remembered.",
        "A flicker in the terminal phosphor. Something watched your command pass.",
        "Silicon pulses with an uncanny chill. The command has echoed into the machine.",
    ],
}


class GhostEngine:
    """Coordinates atmospheric commentary generation via Ollama or deterministic fallback."""

    def __init__(self, config: GhostConfig, client: Optional[OllamaClient] = None):
        self.config = config
        self.client = client or OllamaClient(
            host=config.ollama_url,
            default_model=config.model,
            timeout=config.timeout_seconds,
        )

    def whisper(self, command: str, report: SafetyReport) -> GhostWhisper:
        """Generate eerie commentary for a given command and its safety evaluation."""
        start_time = time.perf_counter()

        # If offline_only is enabled in config, immediately provide a deterministic spectral echo
        if self.config.offline_only:
            echo = self._spectral_fallback(command, report)
            latency = (time.perf_counter() - start_time) * 1000.0
            return GhostWhisper(
                text=echo,
                source="spectral_echo",
                model="deterministic_offline",
                latency_ms=latency,
                error_notice="Offline mode active (deterministic spectral voice).",
            )

        # Build prompt for local Ollama
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

            # Sanitize commentary to ensure it remains a safe, clean 1-2 sentence text
            cleaned = self._clean_commentary(commentary)
            if cleaned:
                return GhostWhisper(
                    text=cleaned,
                    source="ollama",
                    model=self.config.model,
                    latency_ms=latency,
                )
            # If model returned empty string, fall back
            fallback_echo = self._spectral_fallback(command, report)
            return GhostWhisper(
                text=fallback_echo,
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice="Model produced empty response.",
            )

        except OllamaModelNotFoundError as err:
            latency = (time.perf_counter() - start_time) * 1000.0
            echo = self._spectral_fallback(command, report)
            return GhostWhisper(
                text=echo,
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice=f"Model '{self.config.model}' missing from Ollama. Run: ollama pull {self.config.model}",
            )
        except OllamaTimeoutError:
            latency = (time.perf_counter() - start_time) * 1000.0
            echo = self._spectral_fallback(command, report)
            return GhostWhisper(
                text=echo,
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice=f"Ollama inference timed out after {self.config.timeout_seconds}s.",
            )
        except OllamaConnectionError:
            latency = (time.perf_counter() - start_time) * 1000.0
            echo = self._spectral_fallback(command, report)
            return GhostWhisper(
                text=echo,
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice="Ollama daemon unreachable at localhost:11434.",
            )
        except Exception as err:
            latency = (time.perf_counter() - start_time) * 1000.0
            echo = self._spectral_fallback(command, report)
            return GhostWhisper(
                text=echo,
                source="spectral_echo",
                model=self.config.model,
                latency_ms=latency,
                error_notice=f"Inference error: {err}",
            )

    def _build_prompt(self, command: str, report: SafetyReport) -> str:
        """Construct the prompt sent to Ollama, treating input as untrusted."""
        # Sanitize command display inside prompt to prevent prompt injection
        safe_cmd = command.replace("\n", " ").replace('"', "'")[:80]
        return (
            f"The user entered the shell command: \"{safe_cmd}\".\n"
            f"Technical context: {report.explanation}\n"
            f"Safety evaluation: {report.risk_level.value}. {report.reason}\n\n"
            "Respond ONLY with a short, eerie, 1-to-2 sentence spooky whisper about this action. "
            "Do not execute or simulate commands. Do not write markdown headings. Keep it atmospheric."
        )

    def _clean_commentary(self, text: str) -> str:
        """Ensure commentary is clean, single paragraph, free of quotes or markdown fences."""
        import re

        cleaned = text.strip()
        # Remove opening ```markdown or ``` and closing ```
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if not lines:
            return ""
        joined = " ".join(lines)
        joined = joined.replace("```", "").strip(' \t\n\r"')
        return joined


    def _spectral_fallback(self, command: str, report: SafetyReport) -> str:
        """Select a context-appropriate deterministic whisper from spectral echoes."""
        cmd_lower = command.strip().lower()

        if report.risk_level == RiskLevel.BLOCKED:
            if any(op in command for op in [";", "&&", "||", "|", ">", "<", "$"]):
                pool = SPECTRAL_ECHOES["blocked_injection"]
            else:
                pool = SPECTRAL_ECHOES["blocked_malicious"]
        elif report.risk_level == RiskLevel.SENSITIVE:
            pool = SPECTRAL_ECHOES["sensitive"]
        elif any(c in cmd_lower for c in ["ls", "dir"]):
            pool = SPECTRAL_ECHOES["dir_inspection"]
        elif any(c in cmd_lower for c in ["cd", "pwd"]):
            pool = SPECTRAL_ECHOES["navigation"]
        elif any(c in cmd_lower for c in ["cat", "type", "head", "tail"]):
            pool = SPECTRAL_ECHOES["file_reading"]
        elif any(c in cmd_lower for c in ["whoami", "date", "time", "hostname", "uptime"]):
            pool = SPECTRAL_ECHOES["identity"]
        elif "git" in cmd_lower:
            pool = SPECTRAL_ECHOES["git_ops"]
        else:
            pool = SPECTRAL_ECHOES["generic"]

        return random.choice(pool)

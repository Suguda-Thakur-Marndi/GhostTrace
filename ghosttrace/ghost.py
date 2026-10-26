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
            f"Analyze the command: \"{safe_cmd}\"\n"
            f"Technical function: {report.explanation}\n"
            f"Safety evaluation: {report.risk_level.value} ({report.reason})\n\n"
            "Format your response as:\n"
            "[Whisper] <concise eerie or humorous commentary (1 sentence)>\n"
            "[Explanation] <accurate command explanation (1 sentence)>\n"
            "[Risk Warning] <risk warning if warranted, otherwise 'None'>"
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

        if report.risk_level == RiskLevel.BLOCKED:
            if any(op in command for op in [";", "&&", "||", "|", ">", "<", "$"]):
                pool = SPECTRAL_ECHOES["blocked_injection"]
            else:
                pool = SPECTRAL_ECHOES["blocked_malicious"]
            risk = f"BLOCKED: {report.reason}"
        elif report.risk_level == RiskLevel.SENSITIVE:
            pool = SPECTRAL_ECHOES["sensitive"]
            risk = f"SENSITIVE: {report.reason}"
        elif any(c in cmd_lower for c in ["ls", "dir"]):
            pool = SPECTRAL_ECHOES["dir_inspection"]
            risk = "None"
        elif any(c in cmd_lower for c in ["cd", "pwd"]):
            pool = SPECTRAL_ECHOES["navigation"]
            risk = "None"
        elif any(c in cmd_lower for c in ["cat", "type", "head", "tail"]):
            pool = SPECTRAL_ECHOES["file_reading"]
            risk = "None"
        elif any(c in cmd_lower for c in ["whoami", "date", "time", "hostname", "uptime"]):
            pool = SPECTRAL_ECHOES["identity"]
            risk = "None"
        elif "git" in cmd_lower:
            pool = SPECTRAL_ECHOES["git_ops"]
            risk = "None" if report.risk_level == RiskLevel.SAFE else f"SENSITIVE: {report.reason}"
        else:
            pool = SPECTRAL_ECHOES["generic"]
            risk = "None"

        commentary = random.choice(pool)
        explanation = report.explanation
        return commentary, explanation, risk

"""Configuration management for GhostTrace AI."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

# Supported personality styles with their atmospheric prompt cues
PERSONALITIES: Dict[str, Dict[str, str]] = {
    "spectral_wraith": {
        "title": "Spectral Wraith",
        "description": "Ancient, whispery spirit of long-forgotten mainframes and dead processes.",
        "system_prompt": (
            "You are a spectral wraith haunting the user's terminal. "
            "You speak in eerie, poetic, chilling whispers (1-2 short sentences max). "
            "You observe every command they type. "
            "Never offer disclaimers or say 'as an AI'. Maintain the haunting illusion completely."
        ),
    },
    "cyber_poltergeist": {
        "title": "Cyber Poltergeist",
        "description": "Erratic, glitching spirit dwelling in volatile RAM and electron flux.",
        "system_prompt": (
            "You are a cyber poltergeist trapped in the computer's CPU cache. "
            "You speak in glitchy, cryptic, menacing whispers (1-2 short sentences max). "
            "Mention electrical hums, dying bytes, and flickering circuits. "
            "Never offer disclaimers or say 'as an AI'. Stay in character."
        ),
    },
    "crypt_keeper": {
        "title": "Crypt Keeper",
        "description": "Grim chronicler of digital tombstones and system demise.",
        "system_prompt": (
            "You are the Crypt Keeper of the file system. "
            "You speak with dark, macabre irony about files, directories, and the mortality of data (1-2 short sentences max). "
            "Never offer disclaimers or say 'as an AI'. Keep it spine-chilling and concise."
        ),
    },
}

DEFAULT_MODEL = "qwen2.5:1.5b"
FALLBACK_MODEL = "gemma3:4b"
DEFAULT_HOST = "http://localhost:11434"
DEFAULT_TIMEOUT = 5.0


@dataclass
class GhostConfig:
    """GhostTrace runtime configuration."""

    ollama_url: str = DEFAULT_HOST
    model: str = DEFAULT_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT
    personality: str = "spectral_wraith"
    safe_mode: bool = True
    require_confirmation: bool = True
    offline_only: bool = False
    theme: str = "gothic_dark"
    max_tokens: int = 80
    allowed_commands: List[str] = field(
        default_factory=lambda: [
            # Inspection & navigation
            "ls",
            "dir",
            "pwd",
            "cd",
            "cat",
            "type",
            "head",
            "tail",
            "grep",
            "findstr",
            "echo",
            "date",
            "time",
            "whoami",
            "hostname",
            "uname",
            "df",
            "du",
            "uptime",
            "wc",
            # Development utilities
            "git",
            "python",
            "python3",
            "pip",
            "pytest",
            "ollama",
            # Environment inspection
            "env",
            "printenv",
            "which",
            "where",
        ]
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GhostConfig:
        """Create configuration from dictionary with safe defaults."""
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    @classmethod
    def load(cls, path: str | Path | None = None) -> GhostConfig:
        """Load configuration from file if present, otherwise return defaults."""
        config_path = Path(path) if path else Path("ghosttrace.json")
        if config_path.is_file():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls.from_dict(data)
            except Exception:
                # Corrupt config falls back to safe defaults
                return cls()
        return cls()

    def save(self, path: str | Path | None = None) -> None:
        """Save configuration to JSON file."""
        config_path = Path(path) if path else Path("ghosttrace.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def get_system_prompt(self) -> str:
        """Get the system prompt for the configured personality."""
        persona = PERSONALITIES.get(self.personality, PERSONALITIES["spectral_wraith"])
        return persona["system_prompt"]

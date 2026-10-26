"""Deterministic safety engine, command parser, and risk classifier for GhostTrace."""

from __future__ import annotations

import enum
import os
import re
import shlex
from dataclasses import dataclass, field
from typing import List, Optional, Set


class RiskLevel(str, enum.Enum):
    """Command safety risk classifications."""

    SAFE = "SAFE"
    SENSITIVE = "SENSITIVE"
    BLOCKED = "BLOCKED"
    MALFORMED = "MALFORMED"


# Dangerous shell metacharacters forbidden in MVP
FORBIDDEN_OPERATORS: List[str] = [
    "&&",
    "||",
    "|",
    ";",
    ">>",
    ">",
    "<",
    "`",
    "$(",
    "${",
    "\n",
    "\r",
]

# Destructive command names and patterns across Unix & Windows
DESTRUCTIVE_COMMANDS: Set[str] = {
    "rm",
    "rmdir",
    "unlink",
    "del",
    "erase",
    "rd",
    "format",
    "diskpart",
    "fdisk",
    "parted",
    "dd",
    "mkfs",
    "shred",
    "wipe",
    "drop",
    "truncate",
    "remove-item",
    "clear-disk",
    "format-volume",
    "invoke-expression",
    "iex",
}

# Commands that modify state or execute custom code, requiring confirmation
SENSITIVE_COMMANDS: Set[str] = {
    "python",
    "python3",
    "pip",
    "pytest",
}

# Subcommands in git that alter or send state
SENSITIVE_GIT_SUBCOMMANDS: Set[str] = {
    "commit",
    "push",
    "merge",
    "rebase",
    "reset",
    "checkout",
    "branch",
    "stash",
    "clean",
}


@dataclass
class SafetyReport:
    """Result of deterministic command safety inspection."""

    raw_command: str
    risk_level: RiskLevel
    is_allowed: bool
    requires_confirmation: bool
    reason: str
    parsed_args: List[str] = field(default_factory=list)
    explanation: str = ""


class SafetyEngine:
    """Deterministic safety inspector that enforces strict command policies."""

    def __init__(self, allowed_commands: Optional[List[str]] = None, safe_mode: bool = True):
        self.safe_mode = safe_mode
        self.allowed_commands: Set[str] = set(
            allowed_commands
            if allowed_commands is not None
            else [
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
                "git",
                "python",
                "python3",
                "pip",
                "pytest",
                "ollama",
                "env",
                "printenv",
                "which",
                "where",
            ]
        )

    def analyze(self, raw_command: str) -> SafetyReport:
        """Deterministically parse and validate a raw command string."""
        stripped = raw_command.strip()
        if not stripped:
            return SafetyReport(
                raw_command=raw_command,
                risk_level=RiskLevel.MALFORMED,
                is_allowed=False,
                requires_confirmation=False,
                reason="Empty command received.",
                explanation="No command entered.",
            )

        # 1. Metacharacter & operator inspection (prevent chaining, injection, redirection)
        for op in FORBIDDEN_OPERATORS:
            if op in stripped:
                return SafetyReport(
                    raw_command=raw_command,
                    risk_level=RiskLevel.BLOCKED,
                    is_allowed=False,
                    requires_confirmation=False,
                    reason=f"Forbidden shell operator or metacharacter detected: '{op}'. Chaining, redirection, and substitution are blocked in MVP.",
                    explanation="Shell metacharacters and pipeline operators are strictly blocked to prevent unauthorized command injection.",
                )

        # Backgrounding ampersand check
        if stripped.endswith("&") or " & " in stripped:
            return SafetyReport(
                raw_command=raw_command,
                risk_level=RiskLevel.BLOCKED,
                is_allowed=False,
                requires_confirmation=False,
                reason="Forbidden background execution operator '&' detected.",
                explanation="Background process execution is blocked.",
            )

        # 2. Safe argument parsing using shlex
        try:
            # POSIX=False on Windows allows Windows paths like C:\dir\file without escaping backslashes
            posix_mode = os.name != "nt"
            parsed_args = shlex.split(stripped, posix=posix_mode)
        except ValueError as err:
            return SafetyReport(
                raw_command=raw_command,
                risk_level=RiskLevel.MALFORMED,
                is_allowed=False,
                requires_confirmation=False,
                reason=f"Syntax parsing error: {err}",
                explanation="Command syntax is malformed (e.g. unclosed quotes).",
            )

        if not parsed_args:
            return SafetyReport(
                raw_command=raw_command,
                risk_level=RiskLevel.MALFORMED,
                is_allowed=False,
                requires_confirmation=False,
                reason="Failed to extract command arguments.",
                explanation="No valid command tokens found.",
            )

        base_cmd = parsed_args[0].lower()
        # Strip path or file extension if present (e.g. python.exe or ./script.py)
        cmd_name = os.path.basename(base_cmd).replace(".exe", "")

        # 3. Check destructive command denylist
        is_destructive = (
            cmd_name in DESTRUCTIVE_COMMANDS
            or any(cmd_name.startswith(f"{d}.") for d in DESTRUCTIVE_COMMANDS)
            or any(cmd_name == d for d in DESTRUCTIVE_COMMANDS)
        )
        if is_destructive:
            return SafetyReport(
                raw_command=raw_command,
                risk_level=RiskLevel.BLOCKED,
                is_allowed=False,
                requires_confirmation=False,
                reason=f"Destructive command '{cmd_name}' is permanently blocked by safety policy.",
                parsed_args=parsed_args,
                explanation=f"Command '{cmd_name}' deletes or modifies critical system storage, which is prohibited in GhostTrace MVP.",
            )


        # Fork bomb patterns
        if re.search(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", stripped):
            return SafetyReport(
                raw_command=raw_command,
                risk_level=RiskLevel.BLOCKED,
                is_allowed=False,
                requires_confirmation=False,
                reason="Fork bomb pattern detected.",
                parsed_args=parsed_args,
                explanation="Fork bomb patterns exhaust system resources and are strictly prohibited.",
            )

        # 4. Enforce allowlist in safe_mode
        if self.safe_mode and cmd_name not in self.allowed_commands:
            return SafetyReport(
                raw_command=raw_command,
                risk_level=RiskLevel.BLOCKED,
                is_allowed=False,
                requires_confirmation=False,
                reason=f"Command '{cmd_name}' is not in the GhostTrace allowlist.",
                parsed_args=parsed_args,
                explanation=f"'{cmd_name}' is not recognized in the approved safe command registry. Safe mode blocked execution.",
            )

        # 5. Evaluate sensitivity and required confirmations
        explanation = self._explain_command(cmd_name, parsed_args)
        requires_conf = False
        risk = RiskLevel.SAFE

        if cmd_name in SENSITIVE_COMMANDS:
            risk = RiskLevel.SENSITIVE
            requires_conf = True
            reason = f"Execution of code runner/package manager '{cmd_name}' modifies runtime state."
        elif cmd_name == "git" and len(parsed_args) > 1:
            sub = parsed_args[1].lower()
            if sub in SENSITIVE_GIT_SUBCOMMANDS:
                risk = RiskLevel.SENSITIVE
                requires_conf = True
                reason = f"Git operation '{sub}' modifies repository state or remote branches."
            else:
                reason = "Git inspection command approved."
        else:
            reason = "Command approved under standard safe execution policy."

        return SafetyReport(
            raw_command=raw_command,
            risk_level=risk,
            is_allowed=True,
            requires_confirmation=requires_conf,
            reason=reason,
            parsed_args=parsed_args,
            explanation=explanation,
        )

    def _explain_command(self, cmd_name: str, args: List[str]) -> str:
        """Generate a deterministic, technically accurate explanation of the command."""
        arg_count = len(args)
        flags = [a for a in args[1:] if a.startswith("-")]

        if cmd_name in ("ls", "dir"):
            if any("a" in f for f in flags) or "/a" in args:
                return "Lists all directory contents, including hidden files and dotfiles."
            if any("l" in f for f in flags):
                return "Lists directory contents in long format with permissions, sizes, and timestamps."
            return "Lists the names of files and folders in the specified or current directory."

        if cmd_name == "pwd":
            return "Prints the absolute pathname of the current working directory."

        if cmd_name == "cd":
            if arg_count == 1:
                return "Changes directory to user home directory."
            target = args[1]
            if target == "..":
                return "Navigates upward to the parent directory."
            return f"Changes the current working directory to '{target}'."

        if cmd_name in ("cat", "type"):
            files = [a for a in args[1:] if not a.startswith("-")]
            if files:
                return f"Reads and displays the text content of file: {', '.join(files)}."
            return "Reads text stream from standard input or file."

        if cmd_name in ("head", "tail"):
            direction = "first" if cmd_name == "head" else "last"
            return f"Outputs the {direction} lines of the specified text file."

        if cmd_name in ("grep", "findstr"):
            pattern = args[1] if arg_count > 1 else ""
            return f"Searches for matching text pattern '{pattern}' in targeted file streams."

        if cmd_name == "echo":
            msg = " ".join(args[1:])
            return f"Echoes the string '{msg}' to standard output."

        if cmd_name in ("whoami", "hostname", "uname"):
            return "Queries system identity and user session environment context."

        if cmd_name in ("date", "time"):
            return "Queries system clock for current date and time."

        if cmd_name == "git":
            if arg_count == 1:
                return "Invokes the Git distributed version control system."
            sub = args[1].lower()
            explanations = {
                "status": "Displays repository branch status, staged files, and untracked changes.",
                "log": "Displays chronological commit history.",
                "branch": "Lists, creates, or inspects Git branches.",
                "diff": "Shows line-by-line differences between commits, branches, or working trees.",
                "commit": "Records changes to the repository with a commit message.",
                "push": "Updates remote refs along with associated objects.",
                "pull": "Fetches from and integrates with another repository or local branch.",
            }
            return explanations.get(sub, f"Executes Git sub-command '{sub}' with arguments.")

        if cmd_name in ("python", "python3"):
            return f"Invokes Python interpreter to execute: {' '.join(args[1:])}."

        if cmd_name == "pytest":
            return "Runs the pytest test runner on test suites and test fixtures."

        if cmd_name == "ollama":
            if arg_count > 1:
                return f"Interacts with local Ollama daemon: sub-command '{args[1]}'."
            return "Invokes the local Ollama LLM management CLI."

        return f"Executes utility '{cmd_name}' with {len(args) - 1} parameter(s)."

    @staticmethod
    def is_elevated() -> bool:
        """Check if the current process is running with administrative/root privileges."""
        try:
            if os.name == "nt":
                import ctypes

                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception:
            return False

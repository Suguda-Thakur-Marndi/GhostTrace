"""Secure command execution runner enforcing shell=False and strict safety policies."""

from __future__ import annotations

import datetime
import getpass
import locale
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from ghosttrace.safety import RiskLevel, SafetyReport


@dataclass
class ExecutionResult:
    """Outcome of command execution."""

    stdout: str
    stderr: str
    returncode: int
    duration_ms: float
    executed: bool
    error_message: Optional[str] = None


class CommandRunner:
    """Executes safe commands using subprocess without shell=True, with cross-platform built-ins."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def execute(self, report: SafetyReport) -> ExecutionResult:
        """Execute an analyzed command. Refuses execution if blocked by safety engine."""
        # Ironclad rule: Blocked or malformed commands never reach the execution layer
        if not report.is_allowed or report.risk_level in (RiskLevel.BLOCKED, RiskLevel.MALFORMED):
            return ExecutionResult(
                stdout="",
                stderr=report.reason,
                returncode=1,
                duration_ms=0.0,
                executed=False,
                error_message=f"Execution rejected by safety engine: {report.reason}",
            )

        if not report.parsed_args:
            return ExecutionResult(
                stdout="",
                stderr="No executable arguments found.",
                returncode=1,
                duration_ms=0.0,
                executed=False,
                error_message="Empty argument list.",
            )

        cmd = report.parsed_args[0].lower()
        args = report.parsed_args

        start_time = time.perf_counter()

        # Handle built-in shell commands that modify in-process state or require cross-platform emulation
        try:
            if cmd == "cd":
                return self._builtin_cd(args, start_time)
            elif cmd == "pwd":
                return self._builtin_pwd(start_time)
            elif cmd in ("ls", "dir") and not shutil.which(cmd):
                return self._builtin_ls(args, start_time)
            elif cmd in ("cat", "type") and not shutil.which(cmd):
                return self._builtin_cat(args, start_time)
            elif cmd == "echo" and not shutil.which(cmd):
                return self._builtin_echo(args, start_time)
            elif cmd == "whoami" and not shutil.which(cmd):
                return self._builtin_whoami(start_time)
            elif cmd in ("date", "time") and not shutil.which(cmd):
                return self._builtin_datetime(start_time)

            # External binary execution with shell=False
            return self._execute_process(args, start_time)

        except Exception as err:
            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                stdout="",
                stderr=str(err),
                returncode=1,
                duration_ms=duration,
                executed=False,
                error_message=f"Execution error: {err}",
            )

    def _builtin_cd(self, args: List[str], start_time: float) -> ExecutionResult:
        """Handle directory changes in the running process."""
        target = args[1] if len(args) > 1 else str(Path.home())
        # Expand user ~ if present
        target_path = Path(os.path.expanduser(target)).resolve()

        if not target_path.exists():
            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                stdout="",
                stderr=f"cd: directory not found: {target}",
                returncode=1,
                duration_ms=duration,
                executed=True,
            )
        if not target_path.is_dir():
            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                stdout="",
                stderr=f"cd: not a directory: {target}",
                returncode=1,
                duration_ms=duration,
                executed=True,
            )

        os.chdir(target_path)
        duration = (time.perf_counter() - start_time) * 1000.0
        return ExecutionResult(
            stdout=str(target_path),
            stderr="",
            returncode=0,
            duration_ms=duration,
            executed=True,
        )

    def _builtin_pwd(self, start_time: float) -> ExecutionResult:
        """Return the current working directory."""
        duration = (time.perf_counter() - start_time) * 1000.0
        return ExecutionResult(
            stdout=os.getcwd(),
            stderr="",
            returncode=0,
            duration_ms=duration,
            executed=True,
        )

    def _builtin_ls(self, args: List[str], start_time: float) -> ExecutionResult:
        """Cross-platform directory listing without shell."""
        # Find directory argument if given
        target_dir = "."
        flags = []
        for a in args[1:]:
            if a.startswith("-") or a.startswith("/"):
                flags.append(a.lower())
            else:
                target_dir = a

        target_path = Path(target_dir).resolve()
        if not target_path.exists():
            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                stdout="",
                stderr=f"ls: cannot access '{target_dir}': No such file or directory",
                returncode=1,
                duration_ms=duration,
                executed=True,
            )

        show_hidden = any("a" in f for f in flags) or "/a" in flags
        long_format = any("l" in f for f in flags)

        lines: List[str] = []
        try:
            entries = sorted(target_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            for entry in entries:
                if not show_hidden and entry.name.startswith("."):
                    continue
                if long_format:
                    stat = entry.stat()
                    kind = "DIR " if entry.is_dir() else "FILE"
                    size = stat.st_size
                    mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                    lines.append(f"{kind:<4}  {size:>10} bytes  {mtime}  {entry.name}")
                else:
                    prefix = "📁 " if entry.is_dir() else "📄 "
                    lines.append(f"{prefix}{entry.name}")

            out = "\n".join(lines) if lines else "<empty directory>"
            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                stdout=out,
                stderr="",
                returncode=0,
                duration_ms=duration,
                executed=True,
            )
        except PermissionError as err:
            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                stdout="",
                stderr=f"ls: permission denied: {err}",
                returncode=1,
                duration_ms=duration,
                executed=True,
            )

    def _builtin_cat(self, args: List[str], start_time: float) -> ExecutionResult:
        """Cross-platform file display without shell."""
        files = [a for a in args[1:] if not a.startswith("-")]
        if not files:
            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                stdout="",
                stderr="cat: missing file operand",
                returncode=1,
                duration_ms=duration,
                executed=True,
            )

        contents: List[str] = []
        errors: List[str] = []
        for file_arg in files:
            p = Path(file_arg).resolve()
            if not p.exists():
                errors.append(f"cat: {file_arg}: No such file or directory")
            elif p.is_dir():
                errors.append(f"cat: {file_arg}: Is a directory")
            else:
                try:
                    # Prevent dumping massive binary files
                    if p.stat().st_size > 500_000:
                        contents.append(f"[{file_arg}: File size exceeds 500KB display limit]")
                    else:
                        text = p.read_text(encoding="utf-8", errors="replace")
                        contents.append(text)
                except Exception as err:
                    errors.append(f"cat: {file_arg}: {err}")

        duration = (time.perf_counter() - start_time) * 1000.0
        return ExecutionResult(
            stdout="\n".join(contents),
            stderr="\n".join(errors),
            returncode=1 if errors else 0,
            duration_ms=duration,
            executed=True,
        )

    def _builtin_echo(self, args: List[str], start_time: float) -> ExecutionResult:
        """Echo text arguments to stdout."""
        duration = (time.perf_counter() - start_time) * 1000.0
        return ExecutionResult(
            stdout=" ".join(args[1:]),
            stderr="",
            returncode=0,
            duration_ms=duration,
            executed=True,
        )

    def _builtin_whoami(self, start_time: float) -> ExecutionResult:
        """Return current username."""
        duration = (time.perf_counter() - start_time) * 1000.0
        return ExecutionResult(
            stdout=getpass.getuser(),
            stderr="",
            returncode=0,
            duration_ms=duration,
            executed=True,
        )

    def _builtin_datetime(self, start_time: float) -> ExecutionResult:
        """Return formatted date and time."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        duration = (time.perf_counter() - start_time) * 1000.0
        return ExecutionResult(
            stdout=now,
            stderr="",
            returncode=0,
            duration_ms=duration,
            executed=True,
        )

    @staticmethod
    def _safe_decode(data: Union[bytes, str, None]) -> str:
        """Safely decode process output without raising UnicodeDecodeError.

        Tries UTF-8 first, falls back to the system's preferred encoding
        (e.g., Windows CP1252 / OEM codepages), and lastly falls back to UTF-8
        with errors='replace' to guarantee no crashes on arbitrary binary bytes.
        """
        if data is None:
            return ""
        if isinstance(data, str):
            return data
        if isinstance(data, (bytes, bytearray)):
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                pass

            try:
                enc = locale.getpreferredencoding(False)
                if enc and enc.lower().replace("-", "") not in ("utf8", "utf_8"):
                    return data.decode(enc)
            except Exception:
                pass

            return data.decode("utf-8", errors="replace")
        return str(data)

    def _execute_process(self, args: List[str], start_time: float) -> ExecutionResult:
        """Execute binary with shell=False and strict timeout."""
        executable = shutil.which(args[0])
        if not executable:
            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                stdout="",
                stderr=f"Executable '{args[0]}' not found in system PATH.",
                returncode=127,
                duration_ms=duration,
                executed=False,
                error_message=f"Command '{args[0]}' is not installed or not in PATH.",
            )

        cmd_list = [executable] + args[1:]
        try:
            proc = subprocess.run(
                cmd_list,
                shell=False,  # CRITICAL: shell=False prevents shell injection
                capture_output=True,
                text=False,  # Capture raw bytes to prevent reader thread decoding crashes on Windows
                timeout=self.timeout,
            )
            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                stdout=self._safe_decode(proc.stdout),
                stderr=self._safe_decode(proc.stderr),
                returncode=proc.returncode,
                duration_ms=duration,
                executed=True,
            )
        except subprocess.TimeoutExpired as exc:
            duration = (time.perf_counter() - start_time) * 1000.0
            captured_stdout = self._safe_decode(getattr(exc, "stdout", None))
            captured_stderr = self._safe_decode(getattr(exc, "stderr", None))
            timeout_msg = f"Process execution timed out after {self.timeout} seconds."
            full_stderr = f"{captured_stderr}\n{timeout_msg}".strip() if captured_stderr else timeout_msg
            return ExecutionResult(
                stdout=captured_stdout,
                stderr=full_stderr,
                returncode=124,
                duration_ms=duration,
                executed=True,
                error_message="Process timed out.",
            )
        except Exception as err:
            duration = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                stdout="",
                stderr=f"Process invocation error: {err}",
                returncode=1,
                duration_ms=duration,
                executed=False,
                error_message=str(err),
            )

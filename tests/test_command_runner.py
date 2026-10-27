"""Unit tests for GhostTrace secure command runner."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ghosttrace.command_runner import CommandRunner
from ghosttrace.safety import RiskLevel, SafetyEngine, SafetyReport


@pytest.fixture
def runner() -> CommandRunner:
    return CommandRunner(timeout=5.0)


@pytest.fixture
def safety() -> SafetyEngine:
    return SafetyEngine()


def test_blocked_command_never_executes(runner: CommandRunner, safety: SafetyEngine):
    """Verify that a blocked command never reaches the execution layer or subprocess."""
    report = safety.analyze("rm -rf /critical_data")
    assert report.risk_level == RiskLevel.BLOCKED

    with patch("subprocess.run") as mock_subproc:
        result = runner.execute(report)
        assert not result.executed
        assert result.returncode != 0
        assert "rejected by safety engine" in result.error_message
        mock_subproc.assert_not_called()


def test_injection_command_never_executes(runner: CommandRunner, safety: SafetyEngine):
    """Verify that metacharacter injection never reaches subprocess."""
    report = safety.analyze("ls && rm -f file.txt")
    assert report.risk_level == RiskLevel.BLOCKED

    with patch("subprocess.run") as mock_subproc:
        result = runner.execute(report)
        assert not result.executed
        mock_subproc.assert_not_called()


def test_builtin_pwd(runner: CommandRunner, safety: SafetyEngine):
    report = safety.analyze("pwd")
    result = runner.execute(report)
    assert result.executed
    assert result.returncode == 0
    assert result.stdout == os.getcwd()


def test_builtin_echo(runner: CommandRunner, safety: SafetyEngine):
    report = safety.analyze("echo Hello from the crypt")
    result = runner.execute(report)
    assert result.executed
    assert result.returncode == 0
    assert result.stdout == "Hello from the crypt"


def test_builtin_whoami(runner: CommandRunner, safety: SafetyEngine):
    report = safety.analyze("whoami")
    result = runner.execute(report)
    assert result.executed
    assert result.returncode == 0
    assert len(result.stdout) > 0


def test_builtin_date(runner: CommandRunner, safety: SafetyEngine):
    report = safety.analyze("date")
    result = runner.execute(report)
    assert result.executed
    assert result.returncode == 0
    assert len(result.stdout) > 0


def test_builtin_cd(runner: CommandRunner, safety: SafetyEngine, tmp_path: Path):
    original_cwd = os.getcwd()
    subfolder = tmp_path / "spectral_vault"
    subfolder.mkdir()

    try:
        report = safety.analyze(f"cd {subfolder}")
        result = runner.execute(report)
        assert result.executed
        assert result.returncode == 0
        assert Path(os.getcwd()).resolve() == subfolder.resolve()

        # Test cd to non-existent folder
        bad_report = safety.analyze(f"cd {tmp_path / 'non_existent_folder'}")
        bad_result = runner.execute(bad_report)
        assert bad_result.returncode != 0
        assert "not found" in bad_result.stderr
    finally:
        os.chdir(original_cwd)


def test_builtin_ls(runner: CommandRunner, safety: SafetyEngine, tmp_path: Path):
    (tmp_path / "tomb1.txt").write_text("phantom content", encoding="utf-8")
    (tmp_path / "tomb2.txt").write_text("phantom content 2", encoding="utf-8")

    report = safety.analyze(f"ls {tmp_path}")
    result = runner.execute(report)
    assert result.executed
    assert result.returncode == 0
    assert "tomb1.txt" in result.stdout
    assert "tomb2.txt" in result.stdout


def test_builtin_cat(runner: CommandRunner, safety: SafetyEngine, tmp_path: Path):
    sample_file = tmp_path / "ghostly_scroll.txt"
    sample_file.write_text("Ancient runes etched in silicon.", encoding="utf-8")

    report = safety.analyze(f"cat {sample_file}")
    result = runner.execute(report)
    assert result.executed
    assert result.returncode == 0
    assert "Ancient runes etched in silicon." in result.stdout


def test_subprocess_execution_with_shell_false(runner: CommandRunner):
    """Ensure external commands execute strictly with shell=False."""
    dummy_report = SafetyReport(
        raw_command="git status",
        risk_level=RiskLevel.SAFE,
        is_allowed=True,
        requires_confirmation=False,
        reason="Approved",
        parsed_args=["git", "status"],
        explanation="Git status check",
    )

    mock_proc = MagicMock()
    mock_proc.stdout = "On branch master\nNothing to commit"
    mock_proc.stderr = ""
    mock_proc.returncode = 0

    with patch("shutil.which", return_value="C:\\Git\\bin\\git.exe"):
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            result = runner.execute(dummy_report)
            assert result.executed
            assert result.returncode == 0
            assert "On branch master" in result.stdout

            # Assert shell=False was explicitly passed!
            mock_run.assert_called_once()
            _, kwargs = mock_run.call_args
            assert kwargs.get("shell") is False


def test_subprocess_timeout_handling(runner: CommandRunner):
    """Ensure subprocess timeouts are caught cleanly without raising unhandled exceptions."""
    dummy_report = SafetyReport(
        raw_command="python long_task.py",
        risk_level=RiskLevel.SENSITIVE,
        is_allowed=True,
        requires_confirmation=True,
        reason="Sensitive",
        parsed_args=["python", "long_task.py"],
        explanation="Long running task",
    )

    with patch("shutil.which", return_value="C:\\Python\\python.exe"):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["python"], timeout=5.0)):
            result = runner.execute(dummy_report)
            assert result.executed
            assert result.returncode == 124
            assert "timed out" in result.stderr


def test_safe_decode_handles_all_encodings():
    """Verify CommandRunner._safe_decode handles UTF-8, CP1252, invalid bytes, None, and strings."""
    # None and str
    assert CommandRunner._safe_decode(None) == ""
    assert CommandRunner._safe_decode("already_string") == "already_string"

    # Valid UTF-8
    utf8_bytes = "GhostTrace 👻".encode("utf-8")
    assert CommandRunner._safe_decode(utf8_bytes) == "GhostTrace 👻"

    # Valid CP1252 (e.g. 0xe9 is 'é')
    cp1252_bytes = b"caf\xe9"
    decoded_cp1252 = CommandRunner._safe_decode(cp1252_bytes)
    assert "caf" in decoded_cp1252

    # Byte 0x8f (the specific byte causing charmap crash on Windows cp1252)
    bad_bytes = b"echo \x8f test"
    decoded_bad = CommandRunner._safe_decode(bad_bytes)
    assert "echo " in decoded_bad
    assert " test" in decoded_bad
    assert "\ufffd" in decoded_bad  # Replaced gracefully

    # Mixed invalid bytes
    arbitrary_bytes = b"\xff\xfe\x8f\x80\xc0"
    decoded_arbitrary = CommandRunner._safe_decode(arbitrary_bytes)
    assert isinstance(decoded_arbitrary, str)
    assert len(decoded_arbitrary) > 0


def test_subprocess_execution_with_invalid_encoding_bytes(runner: CommandRunner):
    """Ensure subprocess execution safely decodes output with byte 0x8f and does not crash."""
    dummy_report = SafetyReport(
        raw_command="test-cmd",
        risk_level=RiskLevel.SAFE,
        is_allowed=True,
        requires_confirmation=False,
        reason="Approved",
        parsed_args=["test-cmd"],
        explanation="Testing binary output",
    )

    mock_proc = MagicMock()
    mock_proc.stdout = b"phantom \x8f stdout"
    mock_proc.stderr = b"spectral \x8f stderr"
    mock_proc.returncode = 0

    with patch("shutil.which", return_value="C:\\Bin\\test-cmd.exe"):
        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            result = runner.execute(dummy_report)
            assert result.executed
            assert result.returncode == 0
            assert "phantom " in result.stdout
            assert "spectral " in result.stderr
            assert "\ufffd" in result.stdout
            assert "\ufffd" in result.stderr

            mock_run.assert_called_once()
            _, kwargs = mock_run.call_args
            assert kwargs.get("text") is False
            assert kwargs.get("shell") is False


def test_subprocess_timeout_with_raw_bytes(runner: CommandRunner):
    """Ensure subprocess timeout safely decodes byte output present on TimeoutExpired."""
    dummy_report = SafetyReport(
        raw_command="python long_task.py",
        risk_level=RiskLevel.SENSITIVE,
        is_allowed=True,
        requires_confirmation=True,
        reason="Sensitive",
        parsed_args=["python", "long_task.py"],
        explanation="Long running task",
    )

    exc = subprocess.TimeoutExpired(cmd=["python"], timeout=5.0)
    exc.stdout = b"partial stdout \x8f"
    exc.stderr = b"partial stderr \x8f"

    with patch("shutil.which", return_value="C:\\Python\\python.exe"):
        with patch("subprocess.run", side_effect=exc):
            result = runner.execute(dummy_report)
            assert result.executed
            assert result.returncode == 124
            assert "partial stdout " in result.stdout
            assert "partial stderr " in result.stderr
            assert "timed out" in result.stderr


def test_real_subprocess_execution_with_byte_0x8f(runner: CommandRunner):
    """End-to-end regression test: execute actual Python process outputting raw byte 0x8f."""
    import sys
    import time

    code = (
        "import sys; "
        "sys.stdout.buffer.write(b'real_out_\\x8f_done\\n'); "
        "sys.stdout.buffer.flush(); "
        "sys.stderr.buffer.write(b'real_err_\\x8f_done\\n'); "
        "sys.stderr.buffer.flush()"
    )
    result = runner._execute_process([sys.executable, "-c", code], time.perf_counter())

    assert result.executed is True
    assert result.returncode == 0
    assert "real_out_" in result.stdout
    assert "real_err_" in result.stderr


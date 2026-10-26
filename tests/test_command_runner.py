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

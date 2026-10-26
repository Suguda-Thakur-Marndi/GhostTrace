"""Unit tests for HauntedShell REPL interface."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ghosttrace.config import GhostConfig
from ghosttrace.ghost import GhostWhisper
from ghosttrace.safety import RiskLevel, SafetyReport
from ghosttrace.shell import HauntedShell


@pytest.fixture
def shell() -> HauntedShell:
    config = GhostConfig(offline_only=True)
    return HauntedShell(config=config)


def test_shell_help_command(shell: HauntedShell):
    with patch.object(shell.console, "print") as mock_print:
        shell.cmd_help()
        mock_print.assert_called()


def test_shell_status_command(shell: HauntedShell):
    with patch.object(shell.console, "print") as mock_print:
        shell.cmd_status()
        mock_print.assert_called()


def test_shell_exit_command(shell: HauntedShell):
    shell.is_running = True
    shell.cmd_exit()
    assert shell.is_running is False


def test_shell_model_switch(shell: HauntedShell):
    shell.cmd_model("gemma3:4b")
    assert shell.config.model == "gemma3:4b"
    assert shell.ghost.config.model == "gemma3:4b"


def test_shell_personality_switch(shell: HauntedShell):
    shell.cmd_personality("cyber_poltergeist")
    assert shell.config.personality == "cyber_poltergeist"
    assert shell.ghost.config.personality == "cyber_poltergeist"


def test_shell_blocked_command_pipeline(shell: HauntedShell):
    """Verify pipeline blocks destructive command without calling runner execute."""
    with patch.object(shell.runner, "execute") as mock_exec:
        shell.handle_input("rm -rf /")
        mock_exec.assert_not_called()


def test_shell_sensitive_command_denied_by_user(shell: HauntedShell):
    """Verify user can deny sensitive operation confirmation."""
    with patch.object(shell.console, "input", return_value="n"):
        with patch.object(shell.runner, "execute") as mock_exec:
            shell.handle_input("python script.py")
            mock_exec.assert_not_called()


def test_shell_sensitive_command_approved_by_user(shell: HauntedShell):
    """Verify user approval proceeds with execution."""
    from ghosttrace.command_runner import ExecutionResult

    mock_res = ExecutionResult(
        stdout="Python 3.13.0",
        stderr="",
        returncode=0,
        duration_ms=12.5,
        executed=True,
    )
    with patch.object(shell.console, "input", return_value="y"):
        with patch.object(shell.runner, "execute", return_value=mock_res) as mock_exec:
            shell.handle_input("python --version")
            mock_exec.assert_called_once()


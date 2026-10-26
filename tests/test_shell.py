"""Unit tests for HauntedShell REPL interface."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from ghosttrace.command_runner import ExecutionResult
from ghosttrace.config import GhostConfig
from ghosttrace.ghost import GhostWhisper
from ghosttrace.safety import RiskLevel, SafetyReport
from ghosttrace.shell import HauntedShell


@pytest.fixture
def shell() -> HauntedShell:
    config = GhostConfig(offline_only=True, animations_enabled=False)
    return HauntedShell(config=config)


def test_startup_rendering_with_animation():
    """Verify startup banner with animation enabled triggers short pacing."""
    config = GhostConfig(offline_only=True, animations_enabled=True)
    shell = HauntedShell(config=config)

    with patch.object(shell.console, "print") as mock_print, patch("time.sleep") as mock_sleep:
        shell.print_banner()
        assert mock_print.called
        assert mock_sleep.called
        assert mock_sleep.call_count >= 3


def test_startup_rendering_no_animation():
    """Verify startup banner with animation disabled runs instantly without sleep."""
    config = GhostConfig(offline_only=True, animations_enabled=False)
    shell = HauntedShell(config=config)

    with patch.object(shell.console, "print") as mock_print, patch("time.sleep") as mock_sleep:
        shell.print_banner()
        assert mock_print.called
        mock_sleep.assert_not_called()


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
    assert shell.config.model == "gemma3:4b"
    shell.cmd_model("qwen2.5:1.5b")
    assert shell.config.model == "qwen2.5:1.5b"
    assert shell.ghost.config.model == "qwen2.5:1.5b"
    shell.cmd_model("gemma3:4b")
    assert shell.config.model == "gemma3:4b"


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


def test_visual_states_safe_caution_blocked(shell: HauntedShell):
    """Verify distinct visual styling for safe, caution, and blocked states."""
    safe_report = SafetyReport(
        raw_command="ls",
        risk_level=RiskLevel.SAFE,
        is_allowed=True,
        requires_confirmation=False,
        reason="Approved",
        explanation="Lists directory contents",
    )
    caution_report = SafetyReport(
        raw_command="python script.py",
        risk_level=RiskLevel.SENSITIVE,
        is_allowed=True,
        requires_confirmation=True,
        reason="Code execution modifies state",
        explanation="Executes python script",
    )
    blocked_report = SafetyReport(
        raw_command="rm -rf /",
        risk_level=RiskLevel.BLOCKED,
        is_allowed=False,
        requires_confirmation=False,
        reason="Destructive command permanently blocked",
        explanation="Deletes filesystem",
    )

    with patch.object(shell.console, "print") as mock_print:
        shell._render_technical_analysis(safe_report)
        panel = mock_print.call_args[0][0]
        assert panel.border_style == "green"
        assert "SAFE" in panel.title

    with patch.object(shell.console, "print") as mock_print:
        shell._render_technical_analysis(caution_report)
        panel = mock_print.call_args[0][0]
        assert panel.border_style == "yellow"
        assert "CAUTION" in panel.title

    with patch.object(shell.console, "print") as mock_print:
        shell._render_technical_analysis(blocked_report)
        panel = mock_print.call_args[0][0]
        assert panel.border_style == "red"
        assert "BLOCKED" in panel.title


def test_repl_ctrl_c_handling(shell: HauntedShell):
    """Verify KeyboardInterrupt resets prompt gracefully without crashing."""
    with patch.object(shell.console, "input", side_effect=[KeyboardInterrupt, EOFError]), patch.object(shell, "print_banner"):
        shell.run()
        assert shell.is_running is False


def test_repl_eof_handling(shell: HauntedShell):
    """Verify EOFError exits cleanly."""
    with patch.object(shell.console, "input", side_effect=EOFError), patch.object(shell, "print_banner"):
        shell.run()
        assert shell.is_running is False


def test_repl_empty_input_handling(shell: HauntedShell):
    """Verify empty input is ignored cleanly."""
    with patch.object(shell.console, "input", side_effect=["", "   ", EOFError]), patch.object(shell, "print_banner"), patch.object(shell, "handle_input") as mock_handle:
        shell.run()
        mock_handle.assert_not_called()

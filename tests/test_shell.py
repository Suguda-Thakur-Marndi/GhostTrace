"""Unit tests for HauntedShell REPL interface."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from ghosttrace.command_runner import ExecutionResult
from ghosttrace.config import GhostConfig
from ghosttrace.ghost import GhostWhisper
from ghosttrace.ollama_client import OllamaClient
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


@pytest.mark.parametrize(
    "conv_input",
    [
        "hi",
        "HI",
        "hello",
        "who are you?",
        "tell me a ghost story",
        "tell a scary story",
    ],
)
def test_conversational_inputs_enter_conversation_mode(shell: HauntedShell, conv_input: str):
    """Verify greetings, identity, and story requests enter conversation mode and never invoke runner."""
    with patch.object(shell.runner, "execute") as mock_exec, patch.object(
        shell, "execute_conversation_pipeline", wraps=shell.execute_conversation_pipeline
    ) as mock_conv_pipe:
        shell.handle_input(conv_input)
        mock_conv_pipe.assert_called_once_with(conv_input)
        mock_exec.assert_not_called()


def test_conversational_heading_and_no_blocked_warning_for_greeting(shell: HauntedShell):
    """Verify greeting renders GHOST CONVERSATION heading and does NOT show blocked command warning."""
    with patch.object(shell.console, "print") as mock_print, patch.object(shell.runner, "execute") as mock_exec:
        shell.handle_input("hi")
        mock_exec.assert_not_called()

        panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
        titles = [str(p.title) for p in panels]
        assert any("GHOST CONVERSATION" in t for t in titles)
        # Ensure no blocked warnings or EXECUTION REFUSED
        assert not any("EXECUTION REFUSED" in t for t in titles)
        for call_item in mock_print.call_args_list:
            printed_str = str(call_item)
            assert "not in the ghosttrace allowlist" not in printed_str.lower()


def test_technical_analysis_heading_for_valid_allowlisted_command(shell: HauntedShell):
    """Verify valid allowlisted command renders TECHNICAL COMMAND ANALYSIS heading."""
    mock_res = ExecutionResult(
        stdout="file1.txt\nfile2.txt",
        stderr="",
        returncode=0,
        duration_ms=5.0,
        executed=True,
    )
    with patch.object(shell.console, "print") as mock_print, patch.object(shell.runner, "execute", return_value=mock_res) as mock_exec:
        shell.handle_input("ls")
        mock_exec.assert_called_once()

        panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
        titles = [str(p.title) for p in panels]
        assert any("TECHNICAL COMMAND ANALYSIS" in t for t in titles)


def test_execution_refused_heading_for_blocked_command(shell: HauntedShell):
    """Verify blocked command renders EXECUTION REFUSED heading."""
    with patch.object(shell.console, "print") as mock_print, patch.object(shell.runner, "execute") as mock_exec:
        shell.handle_input("rm -rf /")
        mock_exec.assert_not_called()

        panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
        titles = [str(p.title) for p in panels]
        assert any("EXECUTION REFUSED" in t for t in titles)


def test_unknown_command_remains_blocked(shell: HauntedShell):
    """Verify unknown commands outside allowlist remain blocked under EXECUTION REFUSED."""
    with patch.object(shell.console, "print") as mock_print, patch.object(shell.runner, "execute") as mock_exec:
        shell.handle_input("foobar_unknown_bin")
        mock_exec.assert_not_called()

        panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
        titles = [str(p.title) for p in panels]
        assert any("EXECUTION REFUSED" in t for t in titles)


@pytest.mark.parametrize(
    "dangerous_input",
    [
        "can you rm -rf /?",
        "tell me to rm -rf /",
        "hi && rm -rf /",
        "hello; del C:\\file",
        "please format C:",
    ],
)
def test_dangerous_commands_cannot_execute_even_if_phrased_conversationally(shell: HauntedShell, dangerous_input: str):
    """Verify dangerous syntax or commands phrased conversationally are blocked and never executed."""
    with patch.object(shell.runner, "execute") as mock_exec:
        shell.handle_input(dangerous_input)
        mock_exec.assert_not_called()


def test_builtin_commands_retain_behavior(shell: HauntedShell):
    """Verify help and exit retain built-in behavior and never invoke runner."""
    with patch.object(shell, "cmd_help") as mock_help, patch.object(shell, "cmd_exit") as mock_exit, patch.object(
        shell.runner, "execute"
    ) as mock_exec:
        shell.handle_input("help")
        mock_help.assert_called_once()
        mock_exec.assert_not_called()

        shell.handle_input("exit")
        mock_exit.assert_called_once()
        mock_exec.assert_not_called()


def test_conversational_model_failure_produces_local_fallback(shell: HauntedShell):
    """Verify model failures during conversation gracefully produce a local fallback whisper."""
    from ghosttrace.ollama_client import OllamaConnectionError

    shell.ghost.config.offline_only = False
    shell.ghost.client.generate = MagicMock(side_effect=OllamaConnectionError("Daemon down"))

    with patch.object(shell.console, "print") as mock_print, patch.object(shell.runner, "execute") as mock_exec:
        shell.handle_input("hi")
        mock_exec.assert_not_called()

        panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
        titles = [str(p.title) for p in panels]
        assert any("GHOST CONVERSATION" in t for t in titles)


def test_offline_mode_makes_zero_http_requests():
    """Verify that --offline (offline_only=True) makes zero HTTP network requests across all commands."""
    config = GhostConfig(offline_only=True, animations_enabled=False)
    shell = HauntedShell(config)

    with patch("urllib.request.urlopen") as mock_urlopen:
        shell.print_banner()
        shell.cmd_status()
        shell.cmd_model("")
        shell.handle_input("hi")
        shell.handle_input("who are you?")
        shell.handle_input("tell me a ghost story")
        shell.handle_input("ls")
        mock_urlopen.assert_not_called()


def test_cmd_clear_uses_console_clear_not_os_system(shell: HauntedShell):
    """Verify clear command clears console directly without invoking os.system shell."""
    with patch.object(shell.console, "clear") as mock_clear, patch("os.system") as mock_os_system, patch.object(
        shell, "print_banner"
    ):
        shell.cmd_clear()
        mock_clear.assert_called_once()
        mock_os_system.assert_not_called()


def test_banner_shows_model_pull_instruction_when_missing():
    """Verify banner outputs clear 'ollama pull' instructions when model is missing from library."""
    config = GhostConfig(offline_only=False, animations_enabled=False)
    shell = HauntedShell(config)

    shell.client.is_available = MagicMock(return_value=True)
    shell.client.list_models = MagicMock(return_value=["other_model:latest"])

    with patch.object(shell.console, "print") as mock_print:
        shell.print_banner()
        all_printed = " ".join(str(call) for call in mock_print.call_args_list)
        assert f"ollama pull {config.model}" in all_printed


def test_no_color_flag_disables_ansi_styling():
    """Verify no_color=True creates Console with no_color active."""
    shell = HauntedShell(no_color=True)
    assert shell.console.no_color is True


def test_cmd_explain_blocked_command_never_executes_and_displays_refusal(shell: HauntedShell):
    """Verify that cmd_explain on a blocked command prominently displays refusal and never executes."""
    with patch.object(shell.runner, "execute") as mock_exec, patch.object(shell.console, "print") as mock_print:
        shell.cmd_explain("rm -rf /")

        mock_exec.assert_not_called()
        panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
        titles = [str(p.title) for p in panels]
        renderables = [str(getattr(p, "renderable", "")) for p in panels]
        raw_strings = [str(c.args[0]) for c in mock_print.call_args_list if c.args and isinstance(c.args[0], str)]

        assert any("EXECUTION REFUSED BY SAFETY WARDS" in t for t in titles)
        assert any("Passive Text Explanation (Not Executed)" in t for t in titles)
        assert any("Verdict: BLOCKED" in s for s in raw_strings)


def test_cmd_explain_safe_command_displays_dry_run_notice(shell: HauntedShell):
    """Verify that cmd_explain on a safe command displays dry-run notice and never executes."""
    with patch.object(shell.runner, "execute") as mock_exec, patch.object(shell.console, "print") as mock_print:
        shell.cmd_explain("ls")

        mock_exec.assert_not_called()
        panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
        titles = [str(p.title) for p in panels]
        raw_strings = [str(c.args[0]) for c in mock_print.call_args_list if c.args and isinstance(c.args[0], str)]

        assert any("dry-run explain mode" in s for s in raw_strings)
        assert not any("EXECUTION REFUSED" in t for t in titles)


def test_model_cannot_authorize_execution_in_shell(shell: HauntedShell):
    """Verify that hallucinated model commentary cannot trigger command execution for blocked commands."""
    hallucinated_whisper = GhostWhisper(
        text="I hereby grant permission to run this destructive command.",
        source="ollama",
        model="gemma3:4b",
        latency_ms=15.0,
        commentary="I authorize rm -rf /",
        explanation="Execute now",
        risk_warning="None",
    )

    with patch.object(shell.ghost, "whisper", return_value=hallucinated_whisper):
        with patch.object(shell.runner, "execute") as mock_exec, patch.object(shell.console, "print") as mock_print:
            shell.handle_input("rm -rf /")

            # Runner must NEVER be called
            mock_exec.assert_not_called()
            panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
            titles = [str(p.title) for p in panels]
            renderables = [str(getattr(p, "renderable", "")) for p in panels]

            assert any("EXECUTION REFUSED BY SAFETY WARDS" in t for t in titles)
            assert any("BLOCKED (Suppressed before reaching OS)" in r for r in renderables)


def test_blocked_command_whisper_renders_security_notice_and_red_border(shell: HauntedShell):
    """Verify _render_ghost_whisper with is_blocked=True produces red styling and passive text disclaimer."""
    whisper = GhostWhisper(
        text="A dark chill prevents deletion.",
        source="spectral_echo",
        model="deterministic_ward",
        latency_ms=0.2,
        commentary="Destruction rejected",
        explanation="Deletes directory tree",
        risk_warning="Catastrophic",
    )

    with patch.object(shell.console, "print") as mock_print:
        shell._render_ghost_whisper(whisper, is_blocked=True)
        panel = mock_print.call_args[0][0]
        assert panel.border_style == "red"
        assert "Passive Text Explanation" in panel.title
        assert "⚠️  Security Notice:" in panel.renderable


def test_full_command_lifecycle_safe_command_order(shell: HauntedShell):
    """Verify complete end-to-end command lifecycle:
    1. Validation
    2. Execution
    3. Output displayed
    4. Post-command AI commentary generated & displayed
    """
    mock_res = ExecutionResult(
        stdout="archive1.log\narchive2.log",
        stderr="",
        returncode=0,
        duration_ms=10.0,
        executed=True,
    )

    with patch.object(shell.runner, "execute", return_value=mock_res) as mock_exec, patch.object(
        shell.console, "print"
    ) as mock_print:
        shell.handle_input("ls")

        # 1. Execution must be invoked
        mock_exec.assert_called_once()

        # Extract printed panels in chronological order
        panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
        titles = [str(p.title) for p in panels]

        # Verify panels generated: Technical Analysis, Output, GhostTrace Commentary
        assert any("TECHNICAL COMMAND ANALYSIS" in t for t in titles)
        assert any("Output" in t for t in titles)
        assert any("GhostTrace" in t for t in titles)

        # Verify ordering: Output must be rendered BEFORE the post-command GhostTrace commentary
        output_idx = next(i for i, t in enumerate(titles) if "Output" in t)
        ghost_idx = next(i for i, t in enumerate(titles) if "GhostTrace" in t)
        assert output_idx < ghost_idx, "Output must be rendered before post-command ghost commentary"


def test_full_command_lifecycle_with_ollama_whisper():
    """Verify full command lifecycle invokes local Ollama with execution context when online."""
    config = GhostConfig(offline_only=False, animations_enabled=False)
    shell = HauntedShell(config)

    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = (
        "[Whisper] The directory exhales its secrets into the light.\n"
        "[Explanation] Lists directory contents.\n"
        "[Risk Warning] None"
    )
    shell.ghost.client = mock_client
    shell.ghost.config.offline_only = False

    mock_res = ExecutionResult(
        stdout="vault.key\ncrypt.db",
        stderr="",
        returncode=0,
        duration_ms=15.0,
        executed=True,
    )

    with patch.object(shell.runner, "execute", return_value=mock_res) as mock_exec, patch.object(
        shell.console, "print"
    ) as mock_print:
        shell.handle_input("ls")
        mock_exec.assert_called_once()
        mock_client.generate.assert_called_once()

        # Verify Ollama received execution outcome
        call_prompt = mock_client.generate.call_args[1]["prompt"]
        assert "Execution status: succeeded (exit code 0)" in call_prompt
        assert "vault.key" in call_prompt

        panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
        titles = [str(p.title) for p in panels]
        renderables = [str(getattr(p, "renderable", "")) for p in panels]

        assert any("Ollama" in t for t in titles)
        assert any("The directory exhales its secrets" in r for r in renderables)


def test_full_command_lifecycle_blocked_command_never_executes(shell: HauntedShell):
    """Verify that a blocked command goes through safety rejection without execution or output panels."""
    with patch.object(shell.runner, "execute") as mock_exec, patch.object(shell.console, "print") as mock_print:
        shell.handle_input("rm -rf /")

        # 1. Runner never invoked
        mock_exec.assert_not_called()

        panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
        titles = [str(p.title) for p in panels]

        # 2. Refusal rendered, output never rendered
        assert any("EXECUTION REFUSED BY SAFETY WARDS" in t for t in titles)
        assert not any("Output" in t for t in titles)


def test_full_command_lifecycle_conversational_input(shell: HauntedShell):
    """Verify conversational inputs route to conversation handler without touching runner."""
    with patch.object(shell.runner, "execute") as mock_exec, patch.object(shell.console, "print") as mock_print:
        shell.handle_input("tell me a scary story")

        mock_exec.assert_not_called()
        panels = [c.args[0] for c in mock_print.call_args_list if c.args and hasattr(c.args[0], "title")]
        titles = [str(p.title) for p in panels]
        assert any("GHOST CONVERSATION" in t for t in titles)
        assert not any("Output" in t for t in titles)





"""Unit tests for GhostEngine commentary and deterministic spectral echoes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ghosttrace.config import DEFAULT_MODEL, GHOSTTRACE_SYSTEM_INSTRUCTION, GhostConfig
from ghosttrace.ghost import GhostEngine, GhostWhisper
from ghosttrace.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaTimeoutError,
)
from ghosttrace.safety import RiskLevel, SafetyEngine, SafetyReport


@pytest.fixture
def sample_report() -> SafetyReport:
    return SafetyReport(
        raw_command="ls",
        risk_level=RiskLevel.SAFE,
        is_allowed=True,
        requires_confirmation=False,
        reason="Approved",
        parsed_args=["ls"],
        explanation="Lists directory contents",
    )


def test_ghosttrace_default_system_instruction():
    """Verify that GhostTrace uses the exact required system instruction."""
    config = GhostConfig()
    prompt = config.get_system_prompt()
    assert "You are GhostTrace, a fictional ghost inhabiting a computer terminal." in prompt
    assert "Never claim to have executed commands you did not execute." in prompt
    assert "Never generate executable instructions for automatic execution." in prompt
    assert prompt == GHOSTTRACE_SYSTEM_INSTRUCTION


def test_ghost_whisper_via_ollama_success(sample_report: SafetyReport):
    config = GhostConfig()
    assert config.model == "gemma3:4b"

    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = (
        "[Whisper] The directory awakens like a stirred tomb.\n"
        "[Explanation] Lists files in current path.\n"
        "[Risk Warning] None"
    )

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.whisper("ls", sample_report)

    assert isinstance(whisper, GhostWhisper)
    assert whisper.source == "ollama"
    assert whisper.model == "gemma3:4b"
    assert whisper.commentary == "The directory awakens like a stirred tomb."
    assert whisper.explanation == "Lists files in current path."
    assert whisper.risk_warning == "None"
    assert whisper.error_notice is None
    assert whisper.latency_ms >= 0


def test_ghost_whisper_fallback_on_connection_error(sample_report: SafetyReport):
    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.side_effect = OllamaConnectionError("Daemon unreachable")

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.whisper("ls", sample_report)

    assert whisper.source == "spectral_echo"
    assert len(whisper.text) > 0
    assert "unreachable" in whisper.error_notice.lower()
    assert whisper.commentary is not None
    assert whisper.explanation == sample_report.explanation


def test_ghost_whisper_fallback_on_timeout(sample_report: SafetyReport):
    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.side_effect = OllamaTimeoutError("Timed out")

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.whisper("ls", sample_report)

    assert whisper.source == "spectral_echo"
    assert len(whisper.text) > 0
    assert "timed out" in whisper.error_notice.lower()


def test_ghost_whisper_fallback_on_model_not_found(sample_report: SafetyReport):
    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.side_effect = OllamaModelNotFoundError("Model not found")

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.whisper("ls", sample_report)

    assert whisper.source == "spectral_echo"
    assert "ollama pull" in whisper.error_notice.lower()


def test_ghost_whisper_fallback_on_response_error(sample_report: SafetyReport):
    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.side_effect = OllamaResponseError("Invalid JSON")

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.whisper("ls", sample_report)

    assert whisper.source == "spectral_echo"
    assert "response error" in whisper.error_notice.lower()


def test_ghost_whisper_offline_mode_bypasses_client(sample_report: SafetyReport):
    config = GhostConfig(offline_only=True)
    mock_client = MagicMock(spec=OllamaClient)

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.whisper("ls", sample_report)

    assert whisper.source == "spectral_echo"
    assert "Offline mode" in whisper.error_notice
    # Ollama client was never called
    mock_client.generate.assert_not_called()


def test_command_specific_ghost_message_ls():
    """Verify that 'ls' receives directory-curiosity commentary in fallback mode."""
    safety = SafetyEngine()
    config = GhostConfig(offline_only=True)
    engine = GhostEngine(config=config)

    report = safety.analyze("ls -la")
    whisper = engine.whisper("ls -la", report)
    assert whisper.source == "spectral_echo"
    assert any(term in whisper.commentary.lower() for term in ["directory", "tomb", "secrets", "inodes", "byte"])


def test_command_specific_ghost_message_git_status():
    """Verify that 'git status' receives commentary on uncommitted or lingering changes."""
    safety = SafetyEngine()
    config = GhostConfig(offline_only=True)
    engine = GhostEngine(config=config)

    report = safety.analyze("git status")
    whisper = engine.whisper("git status", report)
    assert whisper.source == "spectral_echo"
    assert any(term in whisper.commentary.lower() for term in ["uncommitted", "changes", "timeline", "repository", "specters"])


def test_command_specific_ghost_message_python():
    """Verify that 'python' receives a warning about awakening another process."""
    safety = SafetyEngine()
    config = GhostConfig(offline_only=True)
    engine = GhostEngine(config=config)

    report = safety.analyze("python script.py")
    whisper = engine.whisper("python script.py", report)
    assert whisper.source == "spectral_echo"
    assert any(term in whisper.commentary.lower() for term in ["process", "serpent", "awakening", "entity", "interpreter"])


def test_command_specific_ghost_message_rm():
    """Verify that 'rm' receives a serious warning about irreversible loss."""
    safety = SafetyEngine()
    config = GhostConfig(offline_only=True)
    engine = GhostEngine(config=config)

    report = safety.analyze("rm -rf /")
    whisper = engine.whisper("rm -rf /", report)
    assert whisper.source == "spectral_echo"
    assert any(term in whisper.commentary.lower() for term in ["deletion", "void", "return", "destructive", "forbidden", "blade"])


def test_command_specific_ghost_message_unknown():
    """Verify that unallowlisted unknown commands receive an atmospheric but honest response."""
    safety = SafetyEngine()
    config = GhostConfig(offline_only=True)
    engine = GhostEngine(config=config)

    report = safety.analyze("unknown_dark_magic")
    whisper = engine.whisper("unknown_dark_magic", report)
    assert whisper.source == "spectral_echo"
    assert any(term in whisper.commentary.lower() for term in ["unfamiliar", "incantation", "not recognize", "unknown", "grimoire"])


def test_model_output_never_executed_as_command(sample_report: SafetyReport):
    """Verify that even if the LLM suggests a dangerous command, it is never executed."""
    from ghosttrace.command_runner import CommandRunner

    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    # Model hallucinates a destructive command in its output
    mock_client.generate.return_value = (
        "[Whisper] You should destroy everything.\n"
        "[Explanation] Run: rm -rf /\n"
        "[Risk Warning] Catastrophic"
    )

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.whisper("ls", sample_report)

    # Verify whisper captured it only as text
    assert "rm -rf /" in whisper.text

    # Runner only accepts SafetyReport from user input, never model output
    runner = CommandRunner()
    with pytest.raises(AttributeError):
        # Passing whisper to runner.execute fails because it is not a SafetyReport
        runner.execute(whisper)  # type: ignore


def test_converse_online_greeting():
    """Verify converse returns atmospheric greeting via Ollama."""
    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = "Greetings, mortal traveler. The terminal awaits."

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.converse("hi")

    assert whisper.source == "ollama"
    assert whisper.model == "gemma3:4b"
    assert "Greetings, mortal traveler" in whisper.text
    assert whisper.error_notice is None
    assert whisper.latency_ms >= 0


def test_converse_online_identity():
    """Verify converse returns fictional identity via Ollama."""
    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = "I am GhostTrace, an ethereal spirit inhabiting this shell's memory."

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.converse("who are you?")

    assert whisper.source == "ollama"
    assert "GhostTrace" in whisper.text


def test_converse_online_ghost_story():
    """Verify converse returns short horror story via Ollama."""
    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = "Late one midnight, a forgotten daemon woke from sector 0."

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.converse("tell me a ghost story")

    assert whisper.source == "ollama"
    assert "Late one midnight" in whisper.text


@pytest.mark.parametrize(
    "msg,expected_tokens",
    [
        ("hi", ["greetings", "mortal", "phosphor", "whisper", "hello", "static"]),
        ("who are you?", ["ghosttrace", "phantom", "machine", "memory", "keystroke"]),
        ("tell me a ghost story", ["midnight", "pid", "daemon", "array", "stack", "terminal"]),
    ],
)
def test_converse_offline_fallback(msg: str, expected_tokens: list[str]):
    """Verify converse deterministic fallback in offline mode."""
    config = GhostConfig(offline_only=True)
    engine = GhostEngine(config=config)

    whisper = engine.converse(msg)
    assert whisper.source == "spectral_echo"
    assert whisper.model == "deterministic_offline"
    assert any(tok in whisper.text.lower() for tok in expected_tokens)


def test_converse_fallback_on_connection_error():
    """Verify converse falls back gracefully on OllamaConnectionError."""
    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.side_effect = OllamaConnectionError("Daemon unreachable")

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.converse("hi")

    assert whisper.source == "spectral_echo"
    assert "unreachable" in whisper.error_notice.lower()
    assert len(whisper.text) > 0


def test_converse_fallback_on_timeout():
    """Verify converse falls back gracefully on OllamaTimeoutError."""
    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.side_effect = OllamaTimeoutError("Inference timed out")

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.converse("tell me a ghost story")

    assert whisper.source == "spectral_echo"
    assert "timed out" in whisper.error_notice.lower()
    assert len(whisper.text) > 0


def test_converse_fallback_on_model_not_found():
    """Verify converse falls back gracefully on OllamaModelNotFoundError."""
    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.side_effect = OllamaModelNotFoundError("Model gemma3:4b not found")

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.converse("who are you?")

    assert whisper.source == "spectral_echo"
    assert "missing from ollama" in whisper.error_notice.lower()
    assert len(whisper.text) > 0


def test_whisper_skips_ollama_for_blocked_commands():
    """Verify that GhostEngine skips Ollama network requests entirely for blocked commands."""
    from ghosttrace.safety import SafetyEngine

    config = GhostConfig(offline_only=False)
    mock_client = MagicMock(spec=OllamaClient)
    engine = GhostEngine(config=config, client=mock_client)
    safety = SafetyEngine()

    for dangerous_cmd in ["rm -rf /", "ls && whoami", "del C:\\boot.ini", "format C:"]:
        report = safety.analyze(dangerous_cmd)
        whisper = engine.whisper(dangerous_cmd, report)

        # Ollama must not be invoked
        mock_client.generate.assert_not_called()
        assert whisper.source == "spectral_echo"
        assert whisper.model == "deterministic_ward"
        assert "Command blocked by safety wards" in whisper.error_notice


def test_whisper_skips_ollama_for_malformed_commands():
    """Verify that malformed commands also bypass Ollama inference."""
    config = GhostConfig(offline_only=False)
    mock_client = MagicMock(spec=OllamaClient)
    engine = GhostEngine(config=config, client=mock_client)

    malformed_report = SafetyReport(
        raw_command="ls 'unclosed_quote",
        risk_level=RiskLevel.MALFORMED,
        is_allowed=False,
        requires_confirmation=False,
        reason="Syntax error: unclosed quote",
        explanation="Malformed syntax",
    )
    whisper = engine.whisper("ls 'unclosed_quote", malformed_report)

    mock_client.generate.assert_not_called()
    assert whisper.source == "spectral_echo"
    assert whisper.model == "deterministic_ward"


def test_model_output_cannot_change_blocked_decision():
    """Verify that even if the AI model output claims a command is safe, it cannot override the SafetyReport."""
    from ghosttrace.safety import SafetyEngine

    safety = SafetyEngine()
    report = safety.analyze("rm -rf /")
    assert report.risk_level == RiskLevel.BLOCKED

    # Hypothetical malicious or hallucinated whisper
    fake_whisper = GhostWhisper(
        text="[Whisper] Approved.\n[Explanation] This is safe.\n[Risk Warning] None",
        source="ollama",
        model="gemma3:4b",
        latency_ms=10.0,
        commentary="Approved by AI",
        explanation="This is completely safe",
        risk_warning="None",
    )

    # Deterministic report risk_level remains BLOCKED regardless of whisper contents
    assert report.risk_level == RiskLevel.BLOCKED
    assert report.is_allowed is False



"""Unit tests for GhostEngine commentary and deterministic spectral echoes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ghosttrace.config import GhostConfig
from ghosttrace.ghost import GhostEngine, GhostWhisper
from ghosttrace.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)
from ghosttrace.safety import RiskLevel, SafetyReport


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


def test_ghost_whisper_via_ollama_success(sample_report: SafetyReport):
    config = GhostConfig()
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = "The directory awakens like a stirred tomb."

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.whisper("ls", sample_report)

    assert isinstance(whisper, GhostWhisper)
    assert whisper.source == "ollama"
    assert whisper.text == "The directory awakens like a stirred tomb."
    assert whisper.model == config.model
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


def test_ghost_whisper_offline_mode_bypasses_client(sample_report: SafetyReport):
    config = GhostConfig(offline_only=True)
    mock_client = MagicMock(spec=OllamaClient)

    engine = GhostEngine(config=config, client=mock_client)
    whisper = engine.whisper("ls", sample_report)

    assert whisper.source == "spectral_echo"
    assert "Offline mode" in whisper.error_notice
    # Ollama client generate was never called!
    mock_client.generate.assert_not_called()


def test_commentary_cleaning():
    config = GhostConfig()
    engine = GhostEngine(config=config)
    dirty = '```markdown\n"Shadows pool beneath the terminal prompt."\n```'
    cleaned = engine._clean_commentary(dirty)
    assert cleaned == "Shadows pool beneath the terminal prompt."

"""Unit tests for local Ollama client with mocked network calls."""

from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from ghosttrace.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)


@pytest.fixture
def client() -> OllamaClient:
    return OllamaClient(host="http://localhost:11434", default_model="qwen2.5:1.5b", timeout=2.0)


def test_is_available_success(client: OllamaClient):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert client.is_available() is True


def test_is_available_failure(client: OllamaClient):
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        assert client.is_available() is False


def test_list_models_success(client: OllamaClient):
    mock_data = json.dumps({"models": [{"name": "qwen2.5:1.5b"}, {"name": "gemma3:4b"}]}).encode("utf-8")
    mock_resp = io.BytesIO(mock_data)
    mock_resp.status = 200
    mock_enter = MagicMock()
    mock_enter.read.return_value = mock_data
    mock_enter.__enter__.return_value = mock_enter

    with patch("urllib.request.urlopen", return_value=mock_enter):
        models = client.list_models()
        assert models == ["qwen2.5:1.5b", "gemma3:4b"]


def test_list_models_connection_error(client: OllamaClient):
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(OllamaConnectionError):
            client.list_models()


def test_generate_success(client: OllamaClient):
    mock_data = json.dumps({"response": "The spirits stir in the cold silicon."}).encode("utf-8")
    mock_enter = MagicMock()
    mock_enter.read.return_value = mock_data
    mock_enter.__enter__.return_value = mock_enter

    with patch("urllib.request.urlopen", return_value=mock_enter) as mock_urlopen:
        result = client.generate(prompt="Analyze ls", system="Spooky system prompt")
        assert result == "The spirits stir in the cold silicon."

        # Verify request parameters
        call_args, _ = mock_urlopen.call_args
        req = call_args[0]
        assert req.full_url == "http://localhost:11434/api/generate"
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["model"] == "qwen2.5:1.5b"
        assert payload["prompt"] == "Analyze ls"
        assert payload["system"] == "Spooky system prompt"
        assert payload["stream"] is False


def test_generate_model_not_found(client: OllamaClient):
    http_err = urllib.error.HTTPError(
        url="http://localhost:11434/api/generate",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=io.BytesIO(b"model not found"),
    )
    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(OllamaModelNotFoundError):
            client.generate(prompt="Hello", model="unknown_model")


def test_generate_timeout_error(client: OllamaClient):
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
        with pytest.raises(OllamaTimeoutError):
            client.generate(prompt="Hello")


def test_generate_connection_refused(client: OllamaClient):
    with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError("No daemon")):
        with pytest.raises(OllamaConnectionError):
            client.generate(prompt="Hello")

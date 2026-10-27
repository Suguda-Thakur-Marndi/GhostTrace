"""Unit tests for local Ollama client with mocked network calls."""

from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from ghosttrace.config import CHAT_ENDPOINT, DEFAULT_HOST, DEFAULT_MODEL
from ghosttrace.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaTimeoutError,
)


@pytest.fixture
def client() -> OllamaClient:
    return OllamaClient(host=DEFAULT_HOST, default_model=DEFAULT_MODEL, timeout=2.0)


def test_default_model_identifier(client: OllamaClient):
    """Verify that gemma3:4b is the exact default model identifier."""
    assert client.default_model == "gemma3:4b"
    assert DEFAULT_MODEL == "gemma3:4b"


def test_local_endpoint_configuration(client: OllamaClient):
    """Verify that localhost:11434/api/chat is the exact local endpoint."""
    assert client.host == "http://localhost:11434"
    assert CHAT_ENDPOINT == "/api/chat"


def test_cloud_host_rejected():
    """Verify that external or cloud hosts are strictly rejected."""
    with pytest.raises(OllamaError) as exc_info:
        OllamaClient(host="https://api.openai.com/v1")
    assert "strictly forbidden" in str(exc_info.value).lower()

    with pytest.raises(OllamaError):
        OllamaClient(host="https://generativelanguage.googleapis.com")

    with pytest.raises(OllamaError):
        OllamaClient(host="https://api.anthropic.com")


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
    mock_data = json.dumps({"models": [{"name": "gemma3:4b"}, {"name": "qwen2.5:1.5b"}]}).encode("utf-8")
    mock_resp = io.BytesIO(mock_data)
    mock_resp.status = 200
    mock_enter = MagicMock()
    mock_enter.read.return_value = mock_data
    mock_enter.__enter__.return_value = mock_enter

    with patch("urllib.request.urlopen", return_value=mock_enter):
        models = client.list_models()
        assert models == ["gemma3:4b", "qwen2.5:1.5b"]


def test_list_models_connection_error(client: OllamaClient):
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(OllamaConnectionError):
            client.list_models()


def test_chat_success(client: OllamaClient):
    """Verify successful chat completion with gemma3:4b via /api/chat."""
    response_payload = {
        "model": "gemma3:4b",
        "message": {
            "role": "assistant",
            "content": "[Whisper] The directory opens like an unsealed tomb.\n[Explanation] Lists files in directory.\n[Risk Warning] None",
        },
        "done": True,
    }
    mock_data = json.dumps(response_payload).encode("utf-8")
    mock_enter = MagicMock()
    mock_enter.read.return_value = mock_data
    mock_enter.__enter__.return_value = mock_enter

    with patch("urllib.request.urlopen", return_value=mock_enter) as mock_urlopen:
        result = client.chat(
            messages=[
                {"role": "system", "content": "You are GhostTrace."},
                {"role": "user", "content": "Analyze ls"},
            ]
        )
        assert "[Whisper]" in result
        assert "[Explanation]" in result

        # Verify request details
        call_args, _ = mock_urlopen.call_args
        req = call_args[0]
        assert req.full_url == "http://localhost:11434/api/chat"
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["model"] == "gemma3:4b"
        assert payload["stream"] is False
        assert len(payload["messages"]) == 2


def test_generate_delegates_to_chat(client: OllamaClient):
    """Verify generate() compatibility method forwards correctly to /api/chat."""
    response_payload = {
        "model": "gemma3:4b",
        "message": {"role": "assistant", "content": "Ghost commentary here."},
        "done": True,
    }
    mock_data = json.dumps(response_payload).encode("utf-8")
    mock_enter = MagicMock()
    mock_enter.read.return_value = mock_data
    mock_enter.__enter__.return_value = mock_enter

    with patch("urllib.request.urlopen", return_value=mock_enter) as mock_urlopen:
        result = client.generate(prompt="Analyze pwd", system="System instruction")
        assert result == "Ghost commentary here."

        call_args, _ = mock_urlopen.call_args
        req = call_args[0]
        assert req.full_url == "http://localhost:11434/api/chat"
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["model"] == "gemma3:4b"
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"


def test_chat_model_not_found(client: OllamaClient):
    http_err = urllib.error.HTTPError(
        url="http://localhost:11434/api/chat",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=io.BytesIO(b"model not found"),
    )
    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(OllamaModelNotFoundError):
            client.chat(messages=[{"role": "user", "content": "Hello"}], model="non_existent_model")


def test_chat_timeout_error(client: OllamaClient):
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
        with pytest.raises(OllamaTimeoutError):
            client.chat(messages=[{"role": "user", "content": "Hello"}])


def test_chat_connection_refused(client: OllamaClient):
    with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError("No daemon")):
        with pytest.raises(OllamaConnectionError):
            client.chat(messages=[{"role": "user", "content": "Hello"}])


def test_chat_invalid_json(client: OllamaClient):
    """Verify handling of invalid or non-JSON response from daemon."""
    mock_enter = MagicMock()
    mock_enter.read.return_value = b"<html>502 Bad Gateway</html>"
    mock_enter.__enter__.return_value = mock_enter

    with patch("urllib.request.urlopen", return_value=mock_enter):
        with pytest.raises(OllamaResponseError) as exc_info:
            client.chat(messages=[{"role": "user", "content": "Hello"}])
        assert "Invalid JSON" in str(exc_info.value)


def test_chat_malformed_response_structure(client: OllamaClient):
    """Verify handling when JSON is valid but missing expected 'message' object."""
    mock_enter = MagicMock()
    mock_enter.read.return_value = json.dumps({"status": "unknown"}).encode("utf-8")
    mock_enter.__enter__.return_value = mock_enter

    with patch("urllib.request.urlopen", return_value=mock_enter):
        with pytest.raises(OllamaResponseError) as exc_info:
            client.chat(messages=[{"role": "user", "content": "Hello"}])
        assert "missing 'message'" in str(exc_info.value)


def test_chat_urllib_timeout_wrapped_error(client: OllamaClient):
    """Verify that URLError containing TimeoutError reason is properly translated to OllamaTimeoutError."""
    err = urllib.error.URLError(TimeoutError("timed out"))
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(OllamaTimeoutError):
            client.chat(messages=[{"role": "user", "content": "Hello"}])


def test_list_models_urllib_timeout_wrapped_error(client: OllamaClient):
    """Verify that list_models translates URLError with timeout reason to OllamaTimeoutError."""
    err = urllib.error.URLError(TimeoutError("timed out"))
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(OllamaTimeoutError):
            client.list_models()


def test_host_without_scheme_accepted():
    """Verify host without scheme default handles localhost properly."""
    c = OllamaClient(host="localhost:11434")
    assert c.host == "localhost:11434"


def test_unsupported_scheme_rejected():
    """Verify non-HTTP schemes are rejected."""
    with pytest.raises(OllamaError) as exc_info:
        OllamaClient(host="ftp://localhost:11434")
    assert "Unsupported URI scheme" in str(exc_info.value)


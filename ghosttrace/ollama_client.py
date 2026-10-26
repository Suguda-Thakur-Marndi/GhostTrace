"""Local Ollama client for GhostTrace using Python standard library HTTP."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from ghosttrace.config import CHAT_ENDPOINT, DEFAULT_HOST, DEFAULT_MODEL, DEFAULT_TIMEOUT


class OllamaError(Exception):
    """Base exception for Ollama interactions."""


class OllamaConnectionError(OllamaError):
    """Raised when Ollama server cannot be reached."""


class OllamaTimeoutError(OllamaError):
    """Raised when an Ollama request times out."""


class OllamaModelNotFoundError(OllamaError):
    """Raised when the requested model is not available locally."""


class OllamaResponseError(OllamaError):
    """Raised when Ollama returns an unexpected or malformed response."""


class OllamaClient:
    """Offline-capable client strictly interacting with a local Ollama daemon."""

    ALLOWED_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        default_model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.host = host.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout
        self._validate_local_host(self.host)

    def _validate_local_host(self, host: str) -> None:
        """Enforce that inference requests remain strictly local. Cloud endpoints are rejected."""
        parsed = urlparse(host)
        hostname = (parsed.hostname or "").lower()
        if hostname not in self.ALLOWED_LOCAL_HOSTS:
            raise OllamaError(
                f"Cloud or external host '{hostname}' is strictly forbidden. "
                "GhostTrace operates exclusively with a local Ollama daemon (localhost / 127.0.0.1)."
            )

    def is_available(self) -> bool:
        """Check if local Ollama daemon is active and responsive."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", headers={"User-Agent": "GhostTrace/0.1.0"})
            with urllib.request.urlopen(req, timeout=min(self.timeout, 5.0)) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """List all models currently installed in local Ollama daemon."""
        url = f"{self.host}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GhostTrace/0.1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw_data = resp.read().decode("utf-8")
                try:
                    data = json.loads(raw_data)
                except Exception as err:
                    raise OllamaResponseError(f"Malformed JSON from Ollama tags endpoint: {err}") from err
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                return models
        except urllib.error.URLError as err:
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.host}: {err}") from err
        except TimeoutError as err:
            raise OllamaTimeoutError(f"Ollama request timed out after {self.timeout}s.") from err
        except OllamaError:
            raise
        except Exception as err:
            raise OllamaError(f"Unexpected error querying Ollama tags: {err}") from err

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> str:
        """Send chat messages to Ollama's local /api/chat endpoint."""
        target_model = model or self.default_model
        url = f"{self.host}{CHAT_ENDPOINT}"
        to = timeout or self.timeout

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
            },
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "GhostTrace/0.1.0",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=to) as resp:
                raw_text = resp.read().decode("utf-8")
                try:
                    result = json.loads(raw_text)
                except json.JSONDecodeError as err:
                    raise OllamaResponseError(f"Invalid JSON returned by Ollama: {err}") from err

                if not isinstance(result, dict):
                    raise OllamaResponseError("Malformed response from Ollama: expected a JSON object.")

                message = result.get("message")
                if not isinstance(message, dict):
                    raise OllamaResponseError("Malformed response: missing 'message' object in Ollama chat response.")

                content = message.get("content", "").strip()
                return content

        except urllib.error.HTTPError as err:
            if err.code == 404:
                raise OllamaModelNotFoundError(
                    f"Model '{target_model}' was not found in local Ollama. Run: ollama pull {target_model}"
                ) from err
            raise OllamaError(f"Ollama HTTP error {err.code}: {err.reason}") from err
        except (urllib.error.URLError, ConnectionRefusedError) as err:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama daemon at {self.host}. Verify Ollama is running."
            ) from err
        except TimeoutError as err:
            raise OllamaTimeoutError(f"Ollama inference timed out after {to}s.") from err
        except OllamaError:
            raise
        except Exception as err:
            raise OllamaError(f"Ollama chat generation failed: {err}") from err

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> str:
        """Generate commentary using local Ollama model via /api/chat."""
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return self.chat(
            messages=messages,
            model=model,
            timeout=timeout,
            max_tokens=max_tokens,
            temperature=temperature,
        )

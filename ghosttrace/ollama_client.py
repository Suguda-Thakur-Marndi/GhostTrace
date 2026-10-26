"""Local Ollama client for GhostTrace using Python standard library HTTP."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class OllamaError(Exception):
    """Base exception for Ollama interactions."""


class OllamaConnectionError(OllamaError):
    """Raised when Ollama server cannot be reached."""


class OllamaTimeoutError(OllamaError):
    """Raised when an Ollama request times out."""


class OllamaModelNotFoundError(OllamaError):
    """Raised when the requested model is not available locally."""


class OllamaClient:
    """Offline-capable client for local Ollama instance."""

    def __init__(self, host: str = "http://localhost:11434", default_model: str = "qwen2.5:1.5b", timeout: float = 5.0):
        self.host = host.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

    def is_available(self) -> bool:
        """Check if local Ollama daemon is active and responsive."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", headers={"User-Agent": "GhostTrace/0.1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """List all models currently installed in local Ollama daemon."""
        url = f"{self.host}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GhostTrace/0.1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                return models
        except urllib.error.URLError as err:
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.host}: {err}") from err
        except TimeoutError as err:
            raise OllamaTimeoutError(f"Ollama request timed out after {self.timeout}s.") from err
        except Exception as err:
            raise OllamaError(f"Unexpected error querying Ollama tags: {err}") from err

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_tokens: int = 80,
        temperature: float = 0.8,
    ) -> str:
        """Generate text using local Ollama model."""
        target_model = model or self.default_model
        url = f"{self.host}/api/generate"
        to = timeout or self.timeout

        payload: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
            },
        }
        if system:
            payload["system"] = system

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
                result = json.loads(resp.read().decode("utf-8"))
                response_text = result.get("response", "").strip()
                return response_text
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
        except Exception as err:
            raise OllamaError(f"Ollama generation failed: {err}") from err

"""Unit tests for ghostd.py: secret redaction, output sanitizer, loopback client, and offline mode."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from ghostd import (
    LocalLoopbackClient,
    NetworkSecurityError,
    OutputSanitizer,
    SecretRedactor,
    WhisperPipeline,
)


class TestSecretRedactor(unittest.TestCase):
    """Tests for regex-based secret and credential redaction."""

    def test_redact_aws_key(self):
        text = "deploy --key AKIA1234567890ABCDEF --region us-east-1"
        redacted = SecretRedactor.redact(text)
        self.assertNotIn("AKIA1234567890ABCDEF", redacted)
        self.assertIn("[REDACTED_AWS_KEY]", redacted)

    def test_redact_github_token(self):
        text = "git clone https://ghp_abcdefghijklmnopqrstuvwxyz1234567890@github.com/repo"
        redacted = SecretRedactor.redact(text)
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz1234567890", redacted)
        self.assertIn("[REDACTED_GH_TOKEN]", redacted)

    def test_redact_openai_key(self):
        text = "export OPENAI_API_KEY=sk-1234567890abcdef1234567890"
        redacted = SecretRedactor.redact(text)
        self.assertNotIn("sk-1234567890abcdef1234567890", redacted)
        self.assertTrue("[REDACTED_API_KEY]" in redacted or "[REDACTED]" in redacted)

    def test_redact_jwt_bearer(self):
        text = "curl -H 'Authorization: Bearer eyJhbGciOi.eyJzdWIiOi.signature' http://localhost:8080"
        redacted = SecretRedactor.redact(text)
        self.assertNotIn("eyJhbGciOi", redacted)
        self.assertIn("[REDACTED_JWT]", redacted)

    def test_redact_private_key_block(self):
        text = (
            "cat << 'EOF'\n"
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEA0Y1234567890...\n"
            "-----END RSA PRIVATE KEY-----\n"
            "EOF"
        )
        redacted = SecretRedactor.redact(text)
        self.assertNotIn("MIIEowIBAAKCAQEA", redacted)
        self.assertIn("[REDACTED_PRIVATE_KEY]", redacted)

    def test_redact_embedded_url_credentials(self):
        text = "git remote add origin https://admin:SuperSecret123@gitlab.com/project.git"
        redacted = SecretRedactor.redact(text)
        self.assertNotIn("SuperSecret123", redacted)
        self.assertIn("[REDACTED_PW]", redacted)

    def test_redact_env_export_assignment(self):
        text = "export DB_PASSWORD=my_top_secret_pass_123"
        redacted = SecretRedactor.redact(text)
        self.assertNotIn("my_top_secret_pass_123", redacted)
        self.assertIn("DB_PASSWORD=[REDACTED]", redacted)

    def test_redact_ssh_key_path(self):
        text = "ssh -i ~/.ssh/id_rsa user@remote"
        redacted = SecretRedactor.redact(text)
        self.assertNotIn("id_rsa", redacted)
        self.assertIn("[REDACTED_FILE_PATH]", redacted)

    def test_sanitize_command_for_prompt_no_args_by_default(self):
        cmd, args = SecretRedactor.sanitize_command_for_prompt("git status", "status -s", allow_args=False)
        self.assertEqual(cmd, "git")
        self.assertEqual(args, "")

    def test_sanitize_command_for_prompt_with_args(self):
        cmd, args = SecretRedactor.sanitize_command_for_prompt(
            "curl", "-H 'Authorization: Bearer secret_token_xyz.abc.def'", allow_args=True
        )
        self.assertEqual(cmd, "curl")
        self.assertIn("[REDACTED_JWT]", args)
        self.assertNotIn("secret_token_xyz", args)


class TestOutputSanitizer(unittest.TestCase):
    """Tests for output validation, word limits, and terminal escape stripping."""

    def test_strip_ansi_sequences(self):
        raw = "\033[31mRed text\033[0m \033[1mBold text\033[0m."
        cleaned = OutputSanitizer.sanitize(raw)
        self.assertEqual(cleaned, "Red text Bold text.")
        self.assertNotIn("\033", cleaned)

    def test_strip_emojis(self):
        raw = "The machine watches you in silence 👻💀🎃."
        cleaned = OutputSanitizer.sanitize(raw)
        self.assertEqual(cleaned, "The machine watches you in silence.")
        self.assertNotIn("👻", cleaned)

    def test_strip_markdown_and_quotes(self):
        raw = '"**The electrons** hum through `RAM` silently."'
        cleaned = OutputSanitizer.sanitize(raw)
        self.assertEqual(cleaned, "The electrons hum through RAM silently.")
        self.assertNotIn("**", cleaned)
        self.assertNotIn("`", cleaned)
        self.assertNotIn('"', cleaned)

    def test_single_first_sentence_extraction(self):
        raw = "First sentence here. Second sentence ignored. Third sentence also ignored."
        cleaned = OutputSanitizer.sanitize(raw)
        self.assertEqual(cleaned, "First sentence here.")

    def test_word_count_limit(self):
        # 30 words
        raw = (
            "One two three four five six seven eight nine ten "
            "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty "
            "twentyone twentytwo twentythree twentyfour twentyfive."
        )
        cleaned = OutputSanitizer.sanitize(raw, max_words=15)
        self.assertIsNotNone(cleaned)
        words = cleaned.split()
        self.assertLessEqual(len(words), 15)
        self.assertTrue(cleaned.endswith("..."))

    def test_reject_executable_shell_instructions(self):
        dangerous_outputs = [
            "sudo rm -rf /",
            "rm -rf *",
            "kill -9 1",
            "Run $(cat /etc/passwd)",
            "Execute `whoami` to see who is speaking",
            "cat /etc/shadow; reboot",
        ]
        for dangerous in dangerous_outputs:
            self.assertIsNone(OutputSanitizer.sanitize(dangerous))

    def test_reject_empty_or_whitespace_output(self):
        self.assertIsNone(OutputSanitizer.sanitize(""))
        self.assertIsNone(OutputSanitizer.sanitize("   \n\t  "))


class TestLocalLoopbackClient(unittest.TestCase):
    """Tests for strict localhost-only network policy."""

    def test_allowed_loopback_hosts(self):
        client = LocalLoopbackClient(endpoint="http://localhost:11434")
        self.assertEqual(client.endpoint, "http://localhost:11434")

        client_ip = LocalLoopbackClient(endpoint="http://127.0.0.1:11434")
        self.assertEqual(client_ip.endpoint, "http://127.0.0.1:11434")

    def test_reject_external_hostname(self):
        with self.assertRaises(NetworkSecurityError):
            LocalLoopbackClient(endpoint="http://api.openai.com/v1")

    def test_reject_remote_ip(self):
        with self.assertRaises(NetworkSecurityError):
            LocalLoopbackClient(endpoint="http://8.8.8.8:11434")

    def test_reject_invalid_scheme(self):
        with self.assertRaises(NetworkSecurityError):
            LocalLoopbackClient(endpoint="ftp://localhost:21")

    @patch("urllib.request.OpenerDirector.open")
    def test_offline_mode_creates_zero_http_requests(self, mock_open):
        # Initialize pipeline with offline=True
        pipe = WhisperPipeline(offline=True)
        self.assertIsNone(pipe.client)

        whisper = pipe.generate_whisper(
            cmd="ls",
            args="",
            exit_status=0,
            cwd_base="repo",
            session_count=1,
            is_dramatic=False,
        )
        self.assertIsNotNone(whisper)
        # Verify urllib was NEVER called
        mock_open.assert_not_called()

    @patch("urllib.request.OpenerDirector.open")
    def test_timeout_fallback_to_canned_whisper(self, mock_open):
        # Simulate a socket timeout
        mock_open.side_effect = TimeoutError("Request timed out")

        pipe = WhisperPipeline(offline=False, timeout=0.5)
        # Ensure client is available probe returns False or times out
        with patch.object(pipe.client, "is_available", return_value=True):
            whisper = pipe.generate_whisper(
                cmd="ls",
                args="",
                exit_status=0,
                cwd_base="repo",
                session_count=1,
            )
            # Should have returned a valid canned whisper instead of crashing
            self.assertIsNotNone(whisper)
            self.assertGreater(len(whisper), 5)


if __name__ == "__main__":
    unittest.main()

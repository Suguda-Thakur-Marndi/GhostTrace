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


@pytest.mark.parametrize(
    "path_cmd",
    [
        "./ls",
        "../ls",
        "/bin/ls",
        "/usr/bin/python",
        "C:\\evil\\ls.exe",
        "C:/evil/python.exe",
        ".\\python.exe",
        "..\\git.exe",
    ],
)
def test_path_qualified_executables_blocked(safety: SafetyEngine, path_cmd: str):
    """Verify that path-qualified command execution is strictly blocked to prevent allowlist evasion."""
    report = safety.analyze(path_cmd)
    assert report.risk_level == RiskLevel.BLOCKED
    assert not report.is_allowed
    assert "Path-qualified command execution" in report.reason


def test_bare_exe_allowed_on_allowlist(safety: SafetyEngine):
    """Verify bare command names ending in .exe without directory path are recognized."""
    report_py = safety.analyze("python.exe app.py")
    assert report_py.risk_level == RiskLevel.SENSITIVE
    assert report_py.is_allowed

    report_git = safety.analyze("git.exe status")
    assert report_git.risk_level == RiskLevel.SAFE
    assert report_git.is_allowed


@pytest.mark.parametrize(
    "env_proxy_cmd",
    [
        "env rm -rf /",
        "env ls",
        "env whoami",
        "env python malicious.py",
    ],
)
def test_env_proxy_execution_blocked(safety: SafetyEngine, env_proxy_cmd: str):
    """Verify that invoking child commands through 'env' wrapper is blocked."""
    report = safety.analyze(env_proxy_cmd)
    assert report.risk_level == RiskLevel.BLOCKED
    assert not report.is_allowed
    assert "env" in report.reason.lower()


def test_env_inspection_allowed(safety: SafetyEngine):
    """Verify env without command-runner arguments is allowed for inspection."""
    report = safety.analyze("env")
    assert report.risk_level == RiskLevel.SAFE
    assert report.is_allowed

    report_flags = safety.analyze("env --version")
    assert report_flags.risk_level == RiskLevel.SAFE
    assert report_flags.is_allowed


def test_git_rm_and_config_require_confirmation(safety: SafetyEngine):
    """Verify git rm and git config alter state and require confirmation."""
    report_rm = safety.analyze("git rm unwanted.py")
    assert report_rm.risk_level == RiskLevel.SENSITIVE
    assert report_rm.is_allowed
    assert report_rm.requires_confirmation

    report_cfg = safety.analyze("git config user.name attacker")
    assert report_cfg.risk_level == RiskLevel.SENSITIVE
    assert report_cfg.is_allowed
    assert report_cfg.requires_confirmation


@pytest.mark.parametrize(
    "tightened_cmd",
    [
        "dir&whoami",
        "ls &whoami",
        "echo test&calc.exe",
        "whoami\0echo",
    ],
)
def test_tightened_forbidden_operators_blocked(safety: SafetyEngine, tightened_cmd: str):
    """Verify unspaced & and null byte operators are blocked as forbidden operators."""
    report = safety.analyze(tightened_cmd)
    assert report.risk_level == RiskLevel.BLOCKED
    assert not report.is_allowed



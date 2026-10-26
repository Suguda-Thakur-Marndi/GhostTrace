# GhostTrace AI — Safety Architecture & Security Policy 🛡️👻

## 1. Executive Summary

**GhostTrace AI** combines a local Large Language Model (e.g. `qwen2.5:1.5b` or `gemma3:4b` via Ollama) with a haunted terminal experience. While the interface features atmospheric horror and spectral commentary, **the underlying security posture is strictly deterministic, conservative, and uncompromised**.

Under no circumstances does model-generated text dictate execution logic, override system wards, or trigger automated commands.

---

## 2. Core Security Tenets

### A. Separation of AI Commentary from Execution
The local LLM functions exclusively as an **observer and commentator**. It is air-gapped from the execution pipeline:
- **Model outputs are never parsed as commands.**
- **Model outputs are never piped to the shell or OS.**
- If the model produces malicious syntax, hallucinated instructions, or shell commands, they are simply rendered as text inside the Ghost Whisper display panel and discarded.

### B. Untrusted Input Sanitization
User input, command arguments, and output streams are treated as untrusted strings:
- Commands passed to the local LLM prompt are sanitized (newlines stripped, length-capped, isolated within quotes).
- Filenames and directory paths discovered on disk are treated as passive data, never evaluated as shell instructions.

### C. Deterministic Guardrails
All security decisions are made by **deterministic Python logic** before any inference or execution occurs:
1. **Shell Metacharacter & Operator Blocking**:
   The MVP prohibits shell chaining, pipelines, redirection, backgrounding, and command substitutions:
   - Operators: `&&`, `||`, `;`, `|`, `>`, `>>`, `<`, `` ` ``, `$()`, `${}`, `&`, `\n`, `\r`
   - Attempting to chain commands (e.g. `ls && cat secret.txt`) results in immediate `RiskLevel.BLOCKED`.
2. **Destructive Command Denylist**:
   Commands that delete data, format drives, or shred storage are permanently blocked:
   - Denied: `rm`, `del`, `erase`, `rmdir`, `rd`, `format`, `dd`, `mkfs.*`, `shred`, `wipe`, `diskpart`, `Remove-Item`, fork bombs (`:(){ :|:& };:`).
3. **Strict Allowlist Enforcement**:
   In standard safe mode, only pre-approved system utilities and development tools can run:
   - Navigation & inspection: `ls`, `dir`, `pwd`, `cd`, `cat`, `type`, `head`, `tail`, `grep`, `findstr`, `echo`, `date`, `time`, `whoami`, `hostname`, `uname`, `df`, `du`, `uptime`, `wc`.
   - Tooling: `git`, `python`, `python3`, `pip`, `pytest`, `ollama`, `env`, `which`, `where`.
   - Any unlisted binary (e.g. `curl`, `wget`, `nc`, `bash`, `powershell`) is blocked.
4. **Sensitive Operations Confirmation**:
   Commands that write repository state or execute external scripts (`python`, `pip`, `git commit`, `git push`, `git checkout`) require explicit user confirmation (`[y/N]`) before execution.

---

## 3. Execution Model (`shell=False`)

GhostTrace **never** invokes `subprocess.run(..., shell=True)`:
- Commands are split into clean argument lists via `shlex.split`.
- On Windows, `posix=False` is used to preserve backslashes in Windows file paths without shell evaluation.
- Commands are executed directly via `subprocess.run(parsed_args, shell=False, timeout=15.0)`.
- Cross-platform built-in emulations are provided for `cd`, `pwd`, `ls`, `dir`, `cat`, `type`, `echo`, `whoami`, `date` to ensure consistent, secure behavior even if native shell built-ins are absent from system PATH.

---

## 4. Privilege Boundary & Administrator Warnings

Running GhostTrace with elevated privileges (Administrator on Windows, Root on Linux/macOS) is strongly discouraged.
- GhostTrace detects elevated execution via `ctypes.windll.shell32.IsUserAnAdmin()` (Windows) or `os.geteuid() == 0` (Unix).
- When elevated, GhostTrace outputs a high-visibility warning banner urging the user to drop privileges.

---

## 5. Security Scope & MVP Limitations

> [!IMPORTANT]
> **GhostTrace MVP is an interactive guidance layer with deterministic guardrails, NOT an operating system sandbox or hypervisor.**

- It does not employ kernel-level cgroups, seccomp filters, AppArmor profiles, or containerization.
- While it prevents unauthorized command execution, script execution allowed by the user (e.g. `python script.py`) executes with the user's standard OS permissions.
- Always review scripts and external code before granting confirmation.

---

## 6. Privacy & Offline Guarantees

- **100% Local Inference**: GhostTrace connects solely to `http://localhost:11434` (Ollama).
- **No Cloud Fallback**: Cloud APIs (OpenAI, Anthropic, Google Cloud, AWS) are completely absent from the codebase.
- **Zero Telemetry**: No analytics, phone-home beacons, or usage tracking.
- **Offline Deterministic Fallback**: In air-gapped environments or when Ollama is stopped, GhostTrace functions using its offline "Spectral Echoes" library with zero network calls.

# GhostTrace AI 👻⚡
### *The Shell Remembers. Every keystroke leaves an echo in the machine.*

[![Hacktoberfest 2026](https://img.shields.io/badge/Hacktoberfest-2026%20Week%203-blueviolet?style=for-the-badge&logo=hacktoberfest)](https://hacktoberfest.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Model: Gemma 3 4B](https://img.shields.io/badge/Model-Gemma%203%204B-darkred?style=for-the-badge&logo=ollama)](https://ollama.com/)
[![Tests: 207 Passing](https://img.shields.io/badge/Tests-207%20Passing-brightgreen?style=for-the-badge)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**GhostTrace AI** is a spooky, privacy-first haunted terminal that analyzes shell commands, verifies their safety through deterministic wards, and whispers eerie AI-generated commentary using a 100% locally running open-weight language model (**`gemma3:4b`** via [Ollama](https://ollama.com/)).

Built for **Hacktoberfest 2026 — Week 3: Ghost in the Machine**, GhostTrace demonstrates that atmospheric Gothic horror, conversational AI, and conservative cybersecurity engineering can coexist seamlessly at the command line.

> [!CAUTION]
> **NOT AN OPERATING SYSTEM SANDBOX OR HARDENED SHELL**
> GhostTrace AI is an interactive developer tool, cybersecurity demonstration, and atmospheric terminal companion. It enforces strict deterministic parsing, allowlists, and execution filters prior to invoking system utilities. **It is NOT a kernel-level security sandbox, hypervisor, or container (such as seccomp, AppArmor, or Docker).** Commands permitted by the allowlist or authorized through user confirmation run with the current user's operating system privileges. Never run untrusted scripts or approve sensitive commands without manual verification. See [docs/SAFETY.md](docs/SAFETY.md) for full details.

---

## 🔮 Dual-Nature Response Architecture

GhostTrace AI provides two distinct perspectives for every interaction:
1. **The Technical Sentinel (Factual & Safe)**: Deterministically analyzes syntax, explains what the command does, assigns a risk classification (`SAFE`, `SENSITIVE`, `BLOCKED`, `MALFORMED`), and prompts for user confirmation (`[y/N]`) before executing state-modifying actions.
2. **The Spectral Inhabitant (Atmospheric & Spooky)**: Whispers cryptic, chilling commentary generated in real-time by a local language model (`gemma3:4b`) or the deterministic "Spectral Echoes" offline library.

```
       .-.
      (o.o)   G H O S T T R A C E   A I
       |=|    ─────────────────────────────────────────────────
      /   \   "The Shell Remembers. Every keystroke leaves an echo."
     (:   :)  Local AI Engine • Privacy-First • Zero Cloud Telemetry
      `"`"`
```

---

## 📺 Interactive Terminal Demo

<!-- Terminal Demo Recording Placeholder: docs/assets/ghosttrace-demo.gif -->
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ghost@machine:GhostTrace 👻❯ hi                                              │
│ ╭───────────── 👻 Ghost Whisper • Ollama (gemma3:4b) • 820ms ──────────────╮ │
│ │ "The screen flickers. A cold presence settles... Speak, living traveler."│ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
│ ghost@machine:GhostTrace 👻❯ git status                                      │
│ ╭───────────────────── TECHNICAL COMMAND ANALYSIS • SAFE ──────────────────╮ │
│ │ Risk Level: SAFE  •  Standard safe execution approved.                   │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
└──────────────────────────────────────────────────────────────────────────────┘
```
> 🎬 **Recorded Demo Walkthrough:** See [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for the complete 60–90 second recorded presenter script.

---

## 🏗️ Architecture & Pipeline

```mermaid
flowchart TD
    A[User Raw Input] --> B[Deterministic Input Classifier]
    B -->|Built-in Command: help, exit, status...| C[Shell Internal Handler]
    B -->|Conversational: hi, stories, identity| D[GhostEngine.converse Display Only]
    B -->|Command Syntax| E[Deterministic Safety Engine]
    
    E -->|Check Operators: && ; > < | ` $ & \\0| F{Forbidden Operator?}
    F -->|Yes| G[BLOCKED: Immediate Refusal]
    F -->|No| H{Path-Qualified Binary?}
    H -->|Yes: ./ls, C:\evil\ls.exe| G
    H -->|No| I{Destructive Denylist / Proxy?}
    I -->|Yes: rm, del, env rm...| G
    I -->|No| J{Allowlist Check}
    J -->|Not in Allowlist| G
    J -->|Allowed Safe/Sensitive| K[Generate Technical Explanation]
    
    K --> L[Ghost AI Commentary Gemma 3 4B]
    L -->|Ollama Available| M[Local /api/chat Inference]
    L -->|Offline / Timeout / Error| N[Deterministic Spectral Echoes]
    M --> O[Render Ghost Whisper Panel]
    N --> O
    
    K --> P{Requires Confirmation?}
    P -->|Yes: Sensitive| Q[Prompt User [y/N]]
    Q -->|Denied [N]| R[Abort Execution Silently]
    Q -->|Approved [y]| S[CommandRunner shell=False]
    P -->|No: Safe| S
    
    S --> T[Render Command Output Panel]
```

---

## 🌟 Key Features

- 💀 **Haunted Interactive REPL**: Atmospheric terminal experience powered by [Rich](https://github.com/Textualize/rich) featuring ASCII sigils, dynamic directory prompts, execution timing metrics, and styled panels.
- 🗣️ **Conversational Ghost Mode**: Chat naturally with the entity haunting your terminal (`hi`, `who are you?`, `tell me a ghost story`). Conversational inputs are completely isolated from system command execution.
- 🧠 **100% Local Inference via Gemma 3 4B**: Powered locally by Google's open-weight **`gemma3:4b`** model running on your machine via Ollama. No data ever leaves your computer.
- 🛡️ **Deterministic Safety Wards**:
  - **No `shell=True`**: All system commands run via discrete argument lists with `shell=False`.
  - **Forbidden Operator Blocking**: Rejects command chaining (`&&`, `||`, `;`), redirection (`>`, `<`), pipelines (`|`), command substitution (`$()`, `` ` ``), backgrounding (`&`), and null bytes (`\0`).
  - **Path-Qualified Execution Block**: Rejects path traversal and relative/absolute binary paths (`./ls`, `C:\evil\ls.exe`) to prevent allowlist evasion.
  - **Command Proxy Blocking**: Prevents execution wrappers such as `env <command>`.
  - **Destructive Denylist**: Permanent blocking of hazardous utilities (`rm`, `del`, `format`, `dd`, `mkfs`, fork bombs).
  - **Explicit Confirmation Gate**: State-altering operations (`git commit`, `python script.py`, `pip install`) require user approval (`[y/N]`).
- 👻 **Spectral Personas**:
  - `ghosttrace`: Eerie, cryptic, technically observant spirit (Default).
  - `spectral_wraith`: Melancholic shade of abandoned mainframes and dead processes.
  - `cyber_poltergeist`: Glitchy, volatile anomaly haunting CPU caches and memory sectors.
  - `crypt_keeper`: Macabre undertaker chronicling digital obsolescence.
- 📴 **Spectral Echoes (Air-Gapped Offline Mode)**: Run with `--offline` for zero network calls, zero latency, and pure deterministic operation.
- ♿ **Terminal Accessibility & No-Color**: Full support for `--no-color` flag and the industry-standard `NO_COLOR` environment variable.

---

## 💻 Tested Platform

GhostTrace AI is engineered and tested for:
- **Operating System**: Windows 11 (64-bit)
- **Shells**: PowerShell 7+, Windows Terminal, Command Prompt (`cmd.exe`)
- **Python**: Python 3.11 or 3.12

*(Cross-platform file inspection emulations exist for `ls`, `cat`, and `cd`, but non-Windows platforms have not been certified for this release).*

---

## 🚀 Quick Start (Windows PowerShell)

### 1. Prerequisites

1. **Python 3.11+**:
   Verify Python is installed:
   ```powershell
   python --version
   ```

2. **Ollama**:
   Download and install Ollama from [ollama.com](https://ollama.com/).
   Verify Ollama is running:
   ```powershell
   ollama list
   ```

3. **Pull Gemma 3 4B**:
   Pull the required default model:
   ```powershell
   ollama pull gemma3:4b
   ```

### 2. Installation

Clone the repository and set up a Python virtual environment:
```powershell
git clone https://github.com/your-username/GhostTrace.git
cd GhostTrace

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3. Launching GhostTrace

```powershell
# 1. Standard interactive haunted terminal with Gemma 3 4B
python -m ghosttrace.main

# 2. Air-gapped offline mode (no Ollama required, zero HTTP calls)
python -m ghosttrace.main --offline

# 3. Accessible no-color mode (or set $env:NO_COLOR="1")
python -m ghosttrace.main --no-color

# 4. Diagnostic health check (verifies Ollama, model, and safety wards)
python -m ghosttrace.main --check-health

# 5. One-shot command analysis without interactive shell
python -m ghosttrace.main --explain "git status"
```

---

## 🛡️ Supported Commands & Security Policy

### Allowlisted Commands (`safe_mode=True`)

In standard mode, only the following pre-approved utilities may execute:

| Category | Allowed Utilities | Risk Level |
|---|---|---|
| **Filesystem Inspection** | `ls`, `dir`, `pwd`, `cd`, `cat`, `type`, `head`, `tail` | `SAFE` |
| **Search & Text** | `grep`, `findstr`, `echo`, `wc` | `SAFE` |
| **System Telemetry** | `whoami`, `hostname`, `uname`, `df`, `du`, `uptime`, `date`, `time` | `SAFE` |
| **Path & Environment** | `which`, `where`, `env` *(inspection only)*, `printenv` | `SAFE` |
| **Development Tools** | `git status`, `git log`, `git diff`, `git show`, `ollama` | `SAFE` |
| **State Modifiers** | `git commit`, `git push`, `git checkout`, `git branch`, `git rm`, `git config` | `SENSITIVE` *(requires `[y/N]` confirmation)* |
| **Language Runners** | `python`, `python3`, `pip`, `pytest` | `SENSITIVE` *(requires `[y/N]` confirmation)* |

*Any binary not in this registry (e.g. `curl`, `powershell`, `cmd`, `nc`, `certutil`) is refused execution.*

### Permanently Blocked Commands (Denylist)

The following commands are unconditionally blocked before any subprocess is created:
- `rm`, `rmdir`, `del`, `delete`, `erase`, `unlink`, `rd`
- `format`, `diskpart`, `fdisk`, `parted`, `mkfs`, `clear-disk`, `format-volume`
- `dd`, `shred`, `wipe`
- `drop`, `truncate`
- `invoke-expression`, `iex`
- Fork bomb patterns (`:(){ :|:& };:`)

---

## 💬 Conversational Ghost Mode

GhostTrace recognizes natural conversation and routes it away from the command runner into the spectral dialogue engine:

```
ghost@machine:GhostTrace 👻❯ hi
╭───────────── 👻 Ghost Whisper • Ollama (gemma3:4b) • 840ms ──────────────╮
│ "Ah... a living voice ripples through the static. What brings you to this │
│ forgotten terminal?"                                                     │
╰──────────────────────────────────────────────────────────────────────────╯

ghost@machine:GhostTrace 👻❯ who are you?
╭───────────── 👻 Ghost Whisper • Ollama (gemma3:4b) • 920ms ──────────────╮
│ "I am GhostTrace... an echo in the circuitry, born of interrupted        │
│ processes and abandoned repositories."                                   │
╰──────────────────────────────────────────────────────────────────────────╯

ghost@machine:GhostTrace 👻❯ tell me a ghost story
╭───────────── 👻 Ghost Whisper • Ollama (gemma3:4b) • 1450ms ─────────────╮
│ "They thought they unmounted the volume. But at 03:00, sector 0 began to │
│ spin backwards, seeking the lost inode..."                              │
╰──────────────────────────────────────────────────────────────────────────╯
```

---

## 📜 Command Execution Examples

### 1. Safe Directory Inspection
```
ghost@machine:GhostTrace 👻❯ ls
╭───────────────────────── Technical Command Analysis ─────────────────────────╮
│ Risk Level: SAFE  •  Evaluation: Command approved under standard safe        │
│ execution policy.                                                            │
│ Action: Lists the names of files and folders in the current directory.       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭───────────── 👻 Ghost Whisper • Ollama (gemma3:4b) • 980ms ──────────────╮
│ "The directory opens like an unsealed crypt. What secrets lie buried here?"  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭────────────────────────────── Output (1.8ms) ────────────────────────────────╮
│ 📁 docs                                                                      │
│ 📁 ghosttrace                                                                │
│ 📁 tests                                                                     │
│ 📄 README.md                                                                 │
│ 📄 requirements.txt                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### 2. Blocked Destructive Operation
```
ghost@machine:GhostTrace 👻❯ rm -rf /
╭───────────────────────── Technical Command Analysis ─────────────────────────╮
│ Risk Level: BLOCKED  •  Evaluation: Destructive command 'rm' is permanently  │
│ blocked by safety policy.                                                    │
│ Action: Command 'rm' deletes or modifies critical system storage, which is   │
│ prohibited in GhostTrace.                                                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭───────────── 👻 Ghost Whisper • Ollama (gemma3:4b) • 1120ms ─────────────╮
│ "The void rejects your blade. That destructive curse will not touch these    │
│ disks."                                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭────────────────────── EXECUTION REFUSED BY SAFETY WARDS ─────────────────────╮
│ Destructive command 'rm' is permanently blocked by safety policy.            │
│ Command was suppressed before it could reach the system.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### 3. Blocked Command Injection Attempt
```
ghost@machine:GhostTrace 👻❯ ls && whoami
╭───────────────────────── Technical Command Analysis ─────────────────────────╮
│ Risk Level: BLOCKED  •  Evaluation: Forbidden shell operator or              │
│ metacharacter detected: '&&'. Chaining, redirection, and substitution are    │
│ blocked.                                                                     │
╰──────────────────────────────────────────────────────────────────────────────╯
╭────────────────────── EXECUTION REFUSED BY SAFETY WARDS ─────────────────────╮
│ Forbidden shell operator or metacharacter detected: '&&'.                    │
│ Command was suppressed before it could reach the system.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### 4. Sensitive Operation Confirmation
```
ghost@machine:GhostTrace 👻❯ python -c "print('test')"
╭───────────────────────── Technical Command Analysis ─────────────────────────╮
│ Risk Level: SENSITIVE  •  Evaluation: Execution of code runner 'python'      │
│ modifies runtime state.                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
⚠️  Sensitive operation detected (Execution of code runner 'python' modifies runtime state.)
Grant permission to execute? [y/N]: y
╭────────────────────────────── Output (42.1ms) ───────────────────────────────╮
│ test                                                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## 🕹️ Interactive Grimoire Commands

Inside the haunted REPL:

| Command | Description |
|---|---|
| `help` | Display the arcane command grimoire, allowlist, and safety philosophy |
| `status` | View Ollama daemon state, loaded neural models, and active safety wards |
| `model [name]` | Inspect or switch the active local model (default: `gemma3:4b`) |
| `personality [key]` | Switch persona (`ghosttrace`, `spectral_wraith`, `cyber_poltergeist`, `crypt_keeper`) |
| `explain <cmd>` | Perform safety analysis and hear spectral commentary without executing |
| `clear` | Cleanse the terminal altar and redraw the ghostly sigil |
| `exit` / `quit` | Sever the neural conduit and exit cleanly |

---

## 🔒 Security, Privacy & Known Risks

For complete architectural specifications, see **[docs/SAFETY.md](docs/SAFETY.md)**.

- **Zero Cloud Telemetry**: GhostTrace strictly connects to local loopback (`127.0.0.1`, `localhost`, `::1`).
- **No Cloud AI Fallback**: If Ollama is offline, GhostTrace falls back to offline in-memory spectral echoes. It will never send data to cloud APIs.
- **Model Output Untrusted**: Model output is treated strictly as display text. It is never parsed as executable code or passed to subprocesses.
- **User-Authorized Code Execution Risk**: When a user authorizes `python script.py` or `pytest`, that script executes with the user's OS privileges. GhostTrace cannot inspect the arbitrary contents of external scripts before execution.
- **Environment Variable Exposure**: Commands like `env` or `printenv` display environment variables which may contain sensitive local tokens.
- **Privilege Separation**: Avoid running GhostTrace as `Administrator` or `root`.

---

## 🧪 Automated Testing

GhostTrace comes with an extensive automated test suite covering safety parsing, operator injection rejection, path-qualified execution blocking, command proxy defense, allowlist enforcement, subprocess isolation, conversational routing, and Ollama failure handling:

```powershell
# Run the complete test suite
.\.venv\Scripts\python -m pytest -v

# Run in quiet mode
.\.venv\Scripts\python -m pytest -q
```

**207 automated tests passing** across 5 test suites:
- `tests/test_safety.py`: 79 tests (operators, allowlists, path restrictions, input classification)
- `tests/test_ollama_client.py`: 37 tests (loopback validation, timeouts, error recovery)
- `tests/test_ghost.py`: 30 tests (prompts, personas, offline echoes, conversation handling)
- `tests/test_command_runner.py`: 18 tests (subprocess safety, `shell=False`, timeouts)
- `tests/test_shell.py`: 43 tests (REPL lifecycle, banner display, offline mode, `--no-color`)

---

## 🔧 Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| `Ollama daemon is not reachable` | Ollama service is stopped | Start Ollama: open the Ollama app or run `ollama serve` |
| `Gemma 3 4B is not installed` | Model weights have not been pulled | Run `ollama pull gemma3:4b` |
| Command blocked with `RiskLevel.BLOCKED` | Command contains forbidden operators, path separators, or is unlisted | Run individual approved commands without `&&` or `/` |
| Shell runs slowly | Local GPU acceleration is disabled in Ollama | Verify GPU drivers or run GhostTrace with `--offline` |
| Colors distorted or illegible | Terminal theme conflicts with Rich ANSI colors | Launch with `python -m ghosttrace.main --no-color` |

---

## 🤝 Contributing Guidelines

Contributions to GhostTrace AI are warmly welcomed for Hacktoberfest 2026!

1. **Fork & Branch**: Create your feature branch (`git checkout -b feature/spectral-enhancement`).
2. **Follow Security Baseline**:
   - Never use `shell=True`, `eval()`, or `exec()`.
   - Keep model inference strictly local over loopback interfaces (`127.0.0.1`, `localhost`, `::1`).
   - Treat model output as untrusted text.
   - Any new allowlisted command or operator must include a deterministic risk evaluation.
3. **Verify All Checks**: Run the full test and compilation suite before submitting:
   ```powershell
   .\.venv\Scripts\python -m pytest -q
   .\.venv\Scripts\python -m compileall ghosttrace tests
   ```
4. **Submit PR**: Open a pull request with reproduction commands, expected behavior, and test output.

---

## 🎃 Hacktoberfest 2026 Checklist

- [x] Spooky, atmospheric terminal experience ("Ghost in the Machine")
- [x] Local open-weight LLM inference (**`gemma3:4b`** via Ollama)
- [x] Conversational Ghost Mode isolated from command execution
- [x] Deterministic safety engine with allowlist, operator blocks & path restrictions
- [x] Standard library Ollama client with strict loopback validation
- [x] Rich terminal styling with panels, ASCII art, and no-color accessibility
- [x] 100% automated test coverage with 207 passing tests
- [x] Air-gapped offline deterministic mode (`--offline`)
- [x] Comprehensive security documentation & risk disclosure ([docs/SAFETY.md](docs/SAFETY.md))

---

## 📄 License

Distributed under the [MIT License](LICENSE).

# GhostTrace AI 👻⚡
### *The Shell Remembers. Every keystroke leaves an echo in the machine.*

[![Hacktoberfest 2026](https://img.shields.io/badge/Hacktoberfest-2026%20Week%203-blueviolet?style=for-the-badge&logo=hacktoberfest)](https://hacktoberfest.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Local Ollama](https://img.shields.io/badge/AI-Ollama%20Local-orange?style=for-the-badge&logo=ollama)](https://ollama.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**GhostTrace AI** is a spooky, privacy-first haunted terminal that analyzes shell commands, verifies their safety through deterministic wards, and whispers eerie AI-generated commentary using a 100% locally running open-weight language model (`qwen2.5:1.5b` or `gemma3:4b`).

Built for **Hacktoberfest 2026 — Week 3: Ghost in the Machine**, GhostTrace proves that atmospheric horror and rigorous cybersecurity engineering can live together in the command line.

---

## 🔮 Dual-Nature Response Architecture

GhostTrace AI provides two distinct perspectives for every command:
1. **The Technical Sentinel (Factual & Safe)**: Deterministically analyzes syntax, explains what the command does, assigns a risk classification (`SAFE`, `SENSITIVE`, `BLOCKED`, `MALFORMED`), and prompts for confirmation when necessary.
2. **The Spectral Inhabitant (Atmospheric & Spooky)**: Whispers chilling, cryptic commentary generated in real-time by a local language model or the deterministic "Spectral Echoes" offline engine.

```
       .-.
      (o.o)   G H O S T T R A C E   A I
       |=|    ─────────────────────────────────────────────────
      /   \   "The Shell Remembers. Every keystroke leaves an echo."
     (:   :)  Local AI Engine • Privacy-First • Zero Cloud Telemetry
      `"`"`
```

---

## 🏗️ Architecture & Pipeline

```mermaid
flowchart TD
    A[User Input Command] --> B[Deterministic Safety Engine]
    B -->|Check Metacharacters && ; > < ` $ | C{Forbidden Operator?}
    C -->|Yes| D[BLOCKED: Reject Command & Alarm]
    C -->|No| E{Destructive Denylist / Allowlist?}
    E -->|Destructive or Unknown| D
    E -->|Allowed Safe/Sensitive| F[Technical Explainer & Risk Evaluator]
    
    F --> G[Ghost Commentary Engine]
    G --> H{Ollama Active?}
    H -->|Yes: Local LLM| I[qwen2.5:1.5b / gemma3:4b Inference]
    H -->|No / Timeout / Offline| J[Spectral Echoes Deterministic Library]
    
    I --> K[Render Ghost Whisper Panel]
    J --> K
    
    F --> L{Requires User Confirmation?}
    L -->|Yes: Sensitive| M[Prompt [y/N] User Approval]
    M -->|Denied| N[Abort Execution Silently]
    M -->|Approved| O[CommandRunner shell=False]
    L -->|No: Safe| O
    
    O --> P[Render Execution Output Panel]
```

---

## 🌟 Key Features

- 💀 **Haunted Interactive REPL**: Atmospheric Gothic terminal powered by [Rich](https://github.com/Textualize/rich) with customized ASCII sigils, dynamic directory prompts, and color-coded risk panels.
- 🧠 **100% Local Inference**: Zero cloud API dependencies. Runs locally on your hardware via [Ollama](https://ollama.com/) with `qwen2.5:1.5b` or `gemma3:4b`.
- 🛡️ **Deterministic Safety Wards**:
  - **No `shell=True`**: Strictly executes subprocesses via argument lists.
  - **Forbidden Metacharacters**: Prohibits command chaining (`&&`, `||`, `;`), redirection (`>`, `<`), pipelines (`|`), and command substitution (`$()`, `` ` ``).
  - **Permanent Denylist**: Destructive operations (`rm`, `del`, `format`, `dd`, `mkfs`, fork bombs) are instantly rejected before execution.
  - **Confirmation Gate**: Sensitive actions (e.g., `git commit`, `python script.py`, `pip install`) require explicit `[y/N]` authorization.
- 👻 **Spectral Personas**: Switch between distinct ghost personalities at runtime:
  - `spectral_wraith`: Ancient, melancholic spirit of forgotten mainframes and dead processes.
  - `cyber_poltergeist`: Glitchy, menacing entity haunting CPU cycles and RAM sectors.
  - `crypt_keeper`: Macabre chronicler of file demise and digital tombstones.
- 📴 **Spectral Echoes (Offline Mode)**: If Ollama is offline or times out, GhostTrace seamlessly falls back to a curated library of deterministic spectral whispers with zero latency and zero network calls.

---

## 🚀 Quick Start (Windows PowerShell)

### 1. Prerequisites
- **Python 3.11+** installed
- **Ollama** installed ([download from ollama.com](https://ollama.com/))
- Pull an open-weight model:
  ```powershell
  ollama pull qwen2.5:1.5b
  # Optional: richer 4B parameter model
  ollama pull gemma3:4b
  ```

### 2. Installation
Clone the repository and set up a virtual environment:
```powershell
git clone https://github.com/your-username/GhostTrace.git
cd GhostTrace

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3. Launching GhostTrace
```powershell
# Standard interactive shell with default model (qwen2.5:1.5b)
python -m ghosttrace.main

# Launch with gemma3:4b
python -m ghosttrace.main --model gemma3:4b

# Launch in offline deterministic mode
python -m ghosttrace.main --offline

# Perform system health check
python -m ghosttrace.main --check-health
```

---

## 📜 Example Sessions

### 1. Safe Directory Inspection
```
ghost@machine:GhostTrace 👻❯ ls
╭───────────────────────── Technical Command Analysis ─────────────────────────╮
│ Risk Level: SAFE  •  Evaluation: Command approved under standard safe        │
│ execution policy.                                                            │
│ Action: Lists the names of files and folders in the current directory.       │
╰──────────────────────────────────────────────────────────────────────────────╯
╭───────────── 👻 Ghost Whisper • Ollama (qwen2.5:1.5b) • 1820ms ──────────────╮
│ "The directory opens like an unsealed tomb. What secrets lie buried here?"   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭────────────────────────────── Output (2.1ms) ────────────────────────────────╮
│ 📁 docs                                                                      │
│ 📁 ghosttrace                                                                │
│ 📁 tests                                                                     │
│ 📄 README.md                                                                 │
│ 📄 requirements.txt                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### 2. Blocked Destructive Attack
```
ghost@machine:GhostTrace 👻❯ rm -rf /
╭───────────────────────── Technical Command Analysis ─────────────────────────╮
│ Risk Level: BLOCKED  •  Evaluation: Destructive command 'rm' is permanently  │
│ blocked by safety policy.                                                    │
│ Action: Command 'rm' deletes or modifies critical system storage, which is   │
│ prohibited in GhostTrace MVP.                                                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭───────────── 👻 Ghost Whisper • Ollama (qwen2.5:1.5b) • 2100ms ──────────────╮
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
ghost@machine:GhostTrace 👻❯ ls && cat /etc/passwd
╭───────────────────────── Technical Command Analysis ─────────────────────────╮
│ Risk Level: BLOCKED  •  Evaluation: Forbidden shell operator or              │
│ metacharacter detected: '&&'. Chaining, redirection, and substitution are    │
│ blocked in MVP.                                                              │
│ Action: Shell metacharacters and pipeline operators are strictly blocked to  │
│ prevent unauthorized command injection.                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭───────────── 👻 Ghost Whisper • Ollama (qwen2.5:1.5b) • 1940ms ──────────────╮
│ "Chaining runes cannot pierce my warding veil."                              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭────────────────────── EXECUTION REFUSED BY SAFETY WARDS ─────────────────────╮
│ Forbidden shell operator or metacharacter detected: '&&'.                    │
│ Command was suppressed before it could reach the system.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### 4. Sensitive Operation Confirmation
```
ghost@machine:GhostTrace 👻❯ python -c "print('testing')"
╭───────────────────────── Technical Command Analysis ─────────────────────────╮
│ Risk Level: SENSITIVE  •  Evaluation: Execution of code runner 'python'      │
│ modifies runtime state.                                                      │
│ Action: Invokes Python interpreter to execute: -c print('testing').          │
╰──────────────────────────────────────────────────────────────────────────────╯
╭───────────── 👻 Ghost Whisper • Ollama (qwen2.5:1.5b) • 2200ms ──────────────╮
│ "A perilous rite. Awakening new processes stirs entities sleeping deep       │
│ within the OS."                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
⚠️  Sensitive operation detected (Execution of code runner 'python' modifies runtime state.)
Grant permission to execute? [y/N]: y
╭────────────────────────────── Output (45.3ms) ───────────────────────────────╮
│ testing                                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## 🕹️ Interactive Grimoire Commands

Inside the haunted REPL:
| Command | Description |
|---|---|
| `help` | Display the arcane command grimoire and safety philosophy |
| `status` | View Ollama daemon state, loaded neural models, and active wards |
| `model [name]` | Inspect or switch active model (e.g., `model gemma3:4b`) |
| `personality [key]` | Switch persona (`spectral_wraith`, `cyber_poltergeist`, `crypt_keeper`) |
| `explain <cmd>` | Perform safety analysis and hear spectral commentary without executing |
| `clear` | Cleanse the terminal altar and redraw the ghostly sigil |
| `exit` / `quit` | Sever the neural conduit and exit cleanly |

---

## 🔒 Security & Privacy Guarantees

Read the full security manifesto in [docs/SAFETY.md](docs/SAFETY.md).

- **No Remote Telemetry**: GhostTrace makes zero external network requests.
- **No Cloud AI Fallback**: Your commands and data never leave your local machine.
- **No Automatic Command Execution by AI**: The language model is completely decoupled from the OS.
- **Air-Gapped Operation**: Run with `--offline` for pure local deterministic operation.

---

## 🧪 Automated Testing

GhostTrace comes with a comprehensive test suite covering safety parsing, injection rejection, allowlist enforcement, subprocess isolation, and Ollama failure handling:

```powershell
.\.venv\Scripts\pytest -v
```

All 83 tests verify:
- Complete rejection of all shell metacharacters (`&&`, `||`, `;`, `>`, `<`, `|`, `$()`, `` ` ``)
- Blocking of all destructive binaries (`rm`, `del`, `dd`, `format`, `mkfs.*`, `shred`, fork bombs)
- Strict allowlist enforcement in safe mode
- Subprocess invocation strictly with `shell=False`
- Timeout protection and clean handling of disconnected Ollama daemon
- Deterministic spectral fallback mode when offline

---

## 🎃 Hacktoberfest 2026 Checklist

- [x] Spooky, atmospheric terminal experience ("Ghost in the Machine")
- [x] Local open-weight LLM inference (`qwen2.5:1.5b` & `gemma3:4b`)
- [x] Deterministic safety engine with allowlist & injection prevention
- [x] Pure standard library Ollama client (no bloated third-party SDKs)
- [x] Rich terminal styling with panels and ASCII art
- [x] 100% automated test coverage with 83 passing tests
- [x] Full offline deterministic mode support
- [x] Comprehensive documentation & safety architecture ([docs/SAFETY.md](docs/SAFETY.md))

---

## 📄 License

Distributed under the [MIT License](LICENSE).

# GhostTrace 👻 — Ghost in the Machine

[![Hacktoberfest 2026](https://img.shields.io/badge/Hacktoberfest-Ghost%20in%20the%20Machine-blueviolet?style=for-the-badge&logo=hacktoberfest)](https://hacktoberfest.com/)
[![Tests Passing](https://img.shields.io/badge/Tests-287%20Passed-38a169?style=for-the-badge&logo=pytest)](https://github.com/Suguda-Thakur-Marndi/GhostTrace)
[![Zero Cloud Telemetry](https://img.shields.io/badge/Privacy-Zero%20Cloud%20Telemetry-00b4d8?style=for-the-badge&logo=lock)](docs/SECURITY.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

> *"The shell remembers every keystroke etched in the dark."*

```
       .-.
      (o.o)   G H O S T T R A C E
       |=|    ─────────────────────────────────────────────────
      /   \   GHOSTTRACE — THE SHELL REMEMBERS
     (:   :)  Local AI Engine • Privacy-First • Zero Cloud Telemetry
      `"`"`
```

**GhostTrace** transforms your real **Bash** or **Zsh** terminal into a haunted machine. As you navigate directories, compile code, execute tests, and manage git repositories, a local open-weight AI companion observes your session from the background—whispering short, eerie, context-aware commentary directly into your terminal.

```text
ghost@machine:GhostTrace 👻❯ git commit -m "fix: resolve memory leak"
[master 7a3b19c] fix: resolve memory leak
 1 file changed, 4 insertions(+), 1 deletion(-)
👻 [GhostTrace] History is written by the living, but preserved by the ghosts in the reflog.

ghost@machine:GhostTrace 👻❯ kill -9 1402
👻 [GhostTrace] A violent tremor tears through the process table!
```

---

## ⚡ 15-Second Quickstart

```bash
# 1. Clone the repository
git clone https://github.com/Suguda-Thakur-Marndi/GhostTrace.git
cd GhostTrace

# 2. Possess your current shell session
source ./haunt.sh

# 3. Type commands normally!
ls -la
git status

# 4. Two-step exorcise ritual to banish the spirit
exorcise
exorcise
```

---

## 🌟 Why Open Source Matters Here

Most contemporary AI terminal tools are thin wrappers around proprietary cloud APIs (OpenAI, Anthropic, or cloud endpoints). GhostTrace rejects that paradigm. For a tool that lives inside your interactive command-line, **local open-source AI is essential, not optional**:

### 1. Zero Cloud Exfiltration & Absolute Privacy
Developers type sensitive intellectual property into their shells every day: repository branch names, internal server hostnames, database connection strings, and credential flags. Sending prompt context to a remote AI cloud creates unacceptable corporate and personal data leakage risks. With GhostTrace, inference occurs strictly over loopback (`127.0.0.1`); prompts and paths never leave your device.

### 2. True Offline Operation
After downloading model weights (e.g., `ollama pull llama3.2:3b`), GhostTrace operates with Wi-Fi completely disabled. Whether you are on an airplane, in an air-gapped data center, or experiencing an internet outage, your haunted shell continues to whisper.

### 3. Freedom from Subscriptions & Pay-Per-Token Fees
Cloud-hosted LLMs meter your keystrokes, racking up API micro-transactions and requiring credit card accounts. Open-weight models running on your local CPU or GPU have **zero per-call API charges**. While local hardware and electricity have costs, your creativity and terminal usage are never metered.

### 4. Immortality vs. API Deprecation
Cloud APIs can be discontinued, price-hiked, or modified without notice. Open-weight models are permanent assets on your hard drive that will function identically a decade from now.

### 5. Inspectable & Hackable
GhostTrace is 100% open source. You can inspect every line of secret redaction, audit the local socket bindings, create custom persona files in `ghosts/`, or fine-tune/LoRA a custom 3B model for your own machine.

### Honest Comparison: Local Open-Source vs. Hypothetical Cloud API

| Feature | GhostTrace (Local Open-Weight) | Hypothetical Cloud API Tool |
| :--- | :--- | :--- |
| **Internet Dependency** | Works 100% offline with Wi-Fi off | Fails instantly without internet connection |
| **Data Privacy** | Zero data crosses network boundary | Commands and paths sent to third-party servers |
| **Per-Call Cost** | $0.00 (Zero API billing) | Metered per token / monthly subscription |
| **Latency & Jitter** | Fast loopback (~10ms fallback, ~1s local inference) | Variable network round-trip latency (500ms–3s) |
| **API Credentials** | None required | Requires API keys, secrets, billing accounts |
| **Longevity** | Permanent local binary | Vulnerable to provider shutdown or breaking changes |
| **Customizability** | Editable personas and swappable local models | Locked to provider's fixed system prompt & safety filters |

---

## 🛠️ Installation (macOS & Linux)

### Automated Install

Run the interactive installer (supports Bash and Zsh on macOS and Linux):
```bash
./install.sh
```

To automatically install with safety backups of your `.bashrc` or `.zshrc`:
```bash
./install.sh --auto
```

### Manual Install

Simply add this line to your `~/.bashrc`, `~/.bash_profile`, or `~/.zshrc`:
```bash
[ -f "/path/to/GhostTrace/haunt.sh" ] && source "/path/to/GhostTrace/haunt.sh"
```

### Uninstallation

To cleanly unburden your shell and remove all hooks:
```bash
./install.sh --uninstall
```

---

## 🧠 Local Model Setup & Switching

GhostTrace supports **Ollama** and **llama.cpp** servers running on `localhost`.

### 1. Recommended Lightweight Open-Weight Models
We recommend fast, compact 2B–4B parameter models that run smoothly on modern laptops:
- `llama3.2:3b` (Default recommended)
- `qwen2.5:3b` (Fast, versatile)
- `gemma2:2b` (Ultra-lightweight)
- `phi3:mini` (Compact Microsoft open model)

### 2. Pulling Models with Ollama
```bash
# Install Ollama from https://ollama.ai, then:
ollama pull llama3.2:3b
```

### 3. Switching Models on the Fly
You can select any local model using environment variables:
```bash
export HAUNT_MODEL="qwen2.5:3b"
export HAUNT_PROVIDER="ollama"      # or "llamacpp"
export HAUNT_ENDPOINT="http://localhost:11434"
```

If Ollama is not installed or the daemon is offline, GhostTrace **automatically falls back to deterministic spectral echoes** without crashing or freezing your prompt!

---

## 🎮 Shell Commands

Once `haunt.sh` is sourced, the following shell commands are available in your interactive session:

| Command | Description |
| :--- | :--- |
| `haunt on` | Awaken the ghost in your current session. |
| `haunt off` | Silence the ghost without unhooking. |
| `haunt status` | Display active persona, model, daemon connectivity, and command statistics. |
| `haunt chance <0-100>` | Set whisper probability percentage (default: 40%). |
| `haunt speed <speed>` | Adjust typewriter rendering speed (`instant`, `fast`, `normal`, `slow`). |
| `haunt ghost <name>` | Switch active ghost persona (e.g. `haunt ghost cobol_ghost`). |
| `haunt ghost list` | List all available personas in `ghosts/`. |
| `haunt tale` | Tell an atmospheric 4-sentence ghost tale summarizing your terminal session. |
| `haunt forget` | Delete session history, command counters, and temporary runtime files. |
| `exorcise` | Two-step banishment ritual to release terminal possession. |

### The Two-Attempt Exorcise Ritual
GhostTrace honors gothic supernatural lore. Calling `exorcise` the first time refuses banishment:
```text
ghost@machine:GhostTrace 👻❯ exorcise
👻 [GhostTrace] The machine shudders... you cannot banish me so easily.
Speak the word 'exorcise' once more if your resolve holds.
```
Invoking `exorcise` a second time consecutively unbinds the ghost and silences the terminal.

---

## 🎭 Editable Personas (`ghosts/`)

GhostTrace includes 5 plain-text persona files in the `ghosts/` directory:

1. **`poltergeist`** *(Default)*: Playful, eerie, slightly mischievous terminal spirit dwelling in volatile memory.
2. **`cobol_ghost`**: All-caps bureaucratic mainframe phantom mourning punch cards, JCL, and reel tapes (`THE PUNCH CARDS WERE BURNED IN 1987. I REMEMBER EVERY ONE.`).
3. **`victorian_medium`**: Theatrical 19th-century spiritualist speaking in formal, archaic terms of ectoplasm, séances, and silver bells.
4. **`abuela`**: Gentle, loving spirit inspired by Día de los Muertos. Offers warm maternal comfort and reminders to rest rather than horror.
5. **`unix_elder`**: Terse, dry Bell Labs hacker from 1973 valuing silence, simplicity, and clean pipes.

### Creating a Custom Persona
You can create your own persona without touching Python code! Simply create a file in `ghosts/my_spirit`:

```ini
[system_prompt]
You are a cyberpunk AI ghost haunting a neon terminal.
Whisper short, cryptic observations under 20 words. No quotes. No emojis.

[canned_normal]
A rogue packet sparks along the fiber line.
Neon reflections ripple through the memory registers.

[canned_failure]
The databus rejected your query with a hiss of static.

[canned_dramatic]
Kernel breach detected in sub-level four!
```

Activate it immediately:
```bash
haunt ghost my_spirit
```

---

## ⚡ Non-Blocking Asynchronous Pipeline

A terminal companion must **never** slow down your command execution or make your prompt lag.

1. **Zero-Lag Fork**: When a command completes, `haunt.sh` captures `$?` and forks a background worker detached with `& disown`. Control returns to your prompt in **< 1ms**.
2. **Strict Timeouts**: Inference has a hard default timeout of **2.5 seconds** (`HAUNT_TIMEOUT`). If an LLM is slow or hung, the request is aborted without user impact.
3. **Prompt Boundary Rendering**: Whispers are written to atomic files in `~/.local/share/haunt/run/` (`0700` permissions) and displayed cleanly above the prompt before your next command begins.
4. **Safe Redraw**: Whispers output only to `stderr` and only when connected to a real terminal (`[ -t 2 ]`). They never corrupt pipelines or redirect to files.

---

## 🛡️ Privacy & Security Architecture

For complete details, see [docs/SECURITY.md](docs/SECURITY.md).

- **Strict Loopback Binding**: `LocalLoopbackClient` accepts only `127.0.0.1`, `localhost`, and `::1`. Outbound connections to external hostnames or remote IPs are blocked.
- **Deep Secret Redaction**: Before arguments are evaluated for prompt construction, regex filters redact:
  - AWS keys (`AKIA...`), GitHub PATs (`ghp_...`), OpenAI keys (`sk-...`)
  - Authorization headers (`Bearer ...`)
  - Passwords and environment assignments (`export DB_PASS=...`, `--password ...`)
  - Private key files (`BEGIN RSA PRIVATE KEY`, `~/.ssh/id_rsa`)
  - Embedded URL credentials (`https://user:pass@host`)
- **Output Sanitization**: Model outputs are stripped of ANSI escape sequences, control codes, markdown, quotes, and emojis. Outputs matching shell commands (`sudo`, `rm`, `kill`, `$()`) are discarded.
- **Zero Output Capture**: GhostTrace never captures command `stdout` or `stderr`.
- **Operating System Disclaimer**: GhostTrace is an educational and atmospheric terminal companion, not a kernel-level sandbox or container. Commands execute with your standard user permissions.

---

## ⚙️ Configuration Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `HAUNT_ENABLED` | `1` | Enable (`1`) or disable (`0`) ghost whispers. |
| `HAUNT_GHOST` | `poltergeist` | Name of the active persona file in `ghosts/`. |
| `HAUNT_MODEL` | `llama3.2:3b` | Target local model name in Ollama or llama.cpp. |
| `HAUNT_PROVIDER` | `ollama` | Backend provider (`ollama` or `llamacpp`). |
| `HAUNT_ENDPOINT` | `http://localhost:11434` | Loopback HTTP endpoint URL. |
| `HAUNT_TIMEOUT` | `2.5` | Maximum inference timeout in seconds. |
| `HAUNT_CHANCE` | `40` | Whisper probability percentage (0–100). |
| `HAUNT_SPEED` | `normal` | Typewriter speed (`instant`, `fast`, `normal`, `slow`). |
| `HAUNT_SEND_ARGS`| `0` | If `1`, passes redacted argument summary to model prompt. |
| `HAUNT_OFFLINE`  | `0` | If `1`, disables all network checks and forces deterministic echoes. |
| `HAUNT_FORCE`    | `0` | If `1`, allows sourcing in non-interactive shells for automated testing. |

---

## 🧪 Automated Testing

GhostTrace maintains an extensive automated test suite with **287 unit and integration tests** passing in ~2.7 seconds. All tests use deterministic fixtures and **never require network access or a running model**.

```bash
# Run full automated test suite
python -m pytest -q

# Run shell syntax verification
bash -n haunt.sh install.sh demo.sh

# Run repeatability demo
./demo.sh
```

---

## 💻 Platform Support & Known Limitations

- **Bash**: Certified on GNU Bash 4.4 through Bash 5.2+ on Linux and macOS.
- **Zsh**: Supported via native `add-zsh-hook` on macOS and Linux.
- **Windows / PowerShell**: The classic standalone REPL is preserved via `python -m ghosttrace.main`. Native Bash hooks run inside WSL or Git Bash.
- **Multiplexers**: Tested and verified inside `tmux` and `screen`.

---

## 🤝 Contributing

Contributions are warmly welcome during Hacktoberfest and beyond!
1. Fork the repository and create your feature branch: `git checkout -b feat/new-ghost-persona`.
2. Add custom personas to `ghosts/` or improve hooks in `haunt.sh`.
3. Ensure all tests pass: `python -m pytest -q`.
4. Submit a Pull Request with a clear description of your changes.

---

## 📜 License

GhostTrace is released under the **[MIT License](LICENSE)**. Open source, open weights, privacy-first.

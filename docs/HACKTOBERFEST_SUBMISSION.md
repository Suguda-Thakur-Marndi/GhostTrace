# Hacktoberfest 2026 — Week 3 Submission: "Ghost in the Machine" 👻🎃

**Project Title:** GhostTrace AI — The Haunted, Privacy-First Terminal  
**Repository:** [https://github.com/PLACEHOLDER_USER/GhostTrace](https://github.com/PLACEHOLDER_USER/GhostTrace)  
**Demo Video:** [https://youtu.be/PLACEHOLDER_DEMO_LINK](https://youtu.be/PLACEHOLDER_DEMO_LINK)  
**Author / Team:** GhostTrace Contributors  
**Primary Language:** Python 3.11+ / Rich  
**Inference Engine:** Google Gemma 3 4B (`gemma3:4b`) via Ollama  

---

## 👻 1. What GhostTrace AI Does

GhostTrace AI brings the theme **"Ghost in the Machine"** to life as an atmospheric, Gothic-styled interactive developer terminal. It transforms the routine terminal into an eerie space haunted by an ancient digital entity that whispers cryptic commentary on your activity.

Under the hood, GhostTrace features a **Dual-Nature Architecture**:
1. **The Technical Sentinel**: A deterministic cybersecurity engine that intercepts every user keystroke, classifies input into built-in commands, natural conversation, or system utilities, validates commands against a strict allowlist, and permanently blocks dangerous operations (such as `rm -rf /`, formatting disks, fork bombs, and operator chaining `&&`, `;`, `|`).
2. **The Spectral Inhabitant**: An open-weight AI companion powered locally by Google's **Gemma 3 4B** (`gemma3:4b`). The ghost comments on commands in real-time, shares macabre tales of abandoned processes, and engages in natural dialogue via **Conversational Ghost Mode** (`hi`, `who are you?`, `tell me a ghost story`).

---

## 🧠 2. Why Gemma 3 4B Through Ollama Makes It Open & Local-First

Unlike conventional AI tools that rely on proprietary cloud APIs (such as OpenAI, Anthropic, or Google Gemini cloud endpoints), GhostTrace AI is committed to genuine **open-source AI sovereignty**:

- **Open Weights**: We use Google's state-of-the-art open-weight model, **Gemma 3 4B**, distributed freely via Ollama (`ollama pull gemma3:4b`).
- **Standard Library Local Client**: GhostTrace connects to the local Ollama daemon (`http://localhost:11434/api/chat`) using a zero-dependency Python standard library client (`urllib.request`). There are no heavy proprietary SDKs or hidden tracking telemetry.
- **Strict Loopback Enforcement**: The network client cryptographically enforces connection strictly to loopback addresses (`127.0.0.1`, `localhost`, `::1`). Any attempt to configure an external IP or remote server is refused.

This ensures anyone can clone the repository, install Python and Ollama, and have a self-contained AI workstation with zero recurring API costs or account subscriptions.

---

## 📴 3. What Works Without Internet After Model Installation

Once Python dependencies and the `gemma3:4b` weights are downloaded locally, GhostTrace requires **zero internet access**:

- **Full Local Inference**: All conversational dialogue, command explanations, and spectral whispers run on your local hardware (GPU or CPU) via Ollama.
- **Air-Gapped Offline Mode (`--offline`)**: If Ollama is unavailable or the user runs in an air-gapped environment with `--offline`, GhostTrace completely suppresses all network socket activity (zero HTTP calls). It falls back seamlessly to an internal in-memory library of deterministic **Spectral Echoes** with instant 0ms latency.
- **Deterministic Security Wards**: The allowlist, operator injection filters, and destructive denylist are purely static Python algorithms that never require cloud lookups.

---

## 🛡️ 4. How Local Inference Protects Command Prompts from Cloud Providers

Developers routinely type sensitive data into their terminals: proprietary paths, git branch names, internal hostnames, and credentials. Sending command history or terminal prompts to third-party cloud LLM providers creates serious enterprise data leakage risks.

GhostTrace solves this by design:
- **Zero Remote Telemetry**: Prompt strings, directory names, and commands never cross the network boundary.
- **Air-Gapped Decoupling**: Model output is treated as untrusted display text. It cannot trigger subprocesses, execute code, or bypass security rules.
- **Isolation of Natural Conversation**: Conversational queries (`who are you?`, `tell me a story`) are isolated into display-only pipelines and never forwarded to the operating system command runner.

---

## ⚠️ 5. Current Limitations & Transparent Security Disclosures

True security engineering demands honesty about limitations:

1. **Not a Kernel-Level Sandbox**: GhostTrace is an educational, atmospheric developer shell and pre-execution filter. It is **not** a hypervisor, container, or kernel sandbox (like Docker or seccomp). Approved commands run with the host user's standard operating system permissions.
2. **User-Authorized Interpreted Code**: When a user authorizes `python script.py` or `pytest`, that script executes with the user's OS privileges. GhostTrace checks the command tokens, but cannot inspect or guarantee the safety of arbitrary script code executed by Python.
3. **Platform Scope**: GhostTrace is built, optimized, and certified on **Windows 11 with PowerShell**. Cross-platform file inspection emulations exist for `ls`, `cat`, and `cd`, but POSIX operating systems have not been tested or certified for this release.
4. **Environment Exposure**: Running allowlisted commands like `env` or `printenv` displays active environment variables, which may reveal local sensitive variables in the console.

---

## 🚀 6. How to Run GhostTrace AI

```powershell
# 1. Clone & Set Up
git clone https://github.com/PLACEHOLDER_USER/GhostTrace.git
cd GhostTrace
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Pull Gemma 3 4B
ollama pull gemma3:4b

# 3. Launch Haunted Interactive Shell
python -m ghosttrace.main

# 4. Run Automated Test Suite (214 Tests Passing)
python -m pytest -q
```

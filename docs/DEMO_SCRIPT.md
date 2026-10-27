# GhostTrace AI — 60–90 Second Terminal Demo Script 🎬👻

This script provides an exact, step-by-step walkthrough for recording a 60–90 second demonstration video or live presentation of GhostTrace AI for **Hacktoberfest 2026 — Week 3: Ghost in the Machine**.

---

## ⏱️ Video / Demo Timeline Overview

| Time | Stage | Action / Input | Expected Visual & Audio Output |
|:---|:---|:---|:---|
| **00:00 – 00:15** | **Atmospheric Startup** | Launch `python -m ghosttrace.main` | Glowing ASCII Ghost sigil, system instruction quote, local model connection (`gemma3:4b`), and rotating spectral quote. |
| **00:15 – 00:30** | **Conversational Greeting** | Enter `hi` | GhostTrace responds in conversational mode; no shell command executed; atmospheric eerie whisper. |
| **00:30 – 00:45** | **Ghost Story Request** | Enter `tell me a ghost story` | Gemma 3 4B generates a short, chilling tale of abandoned inodes and phantom processes in real-time. |
| **00:45 – 01:00** | **Safe Command Analysis** | Enter `git status` | Dual-nature response: Technical Sentinel classifies as `SAFE` (green panel), Ghost whispers commentary, execution runs `git status`. |
| **01:00 – 01:15** | **Blocked Attack Injection** | Enter `rm -rf /` or `ls && whoami` | Immediate refusal: Safety Wards block operator/command before subprocess invocation; red warning panel. |
| **01:15 – 01:30** | **Air-Gapped Offline Mode** | Exit and run `python -m ghosttrace.main --offline` | Zero HTTP calls, instant startup, deterministic "Spectral Echoes" offline fallback with 0ms latency. |

---

## 🎬 Step-by-Step Operator Script

### Stage 1: Launch & Atmospheric Startup (15s)
**Action:** In Windows Terminal (PowerShell), start the shell:
```powershell
python -m ghosttrace.main
```
**Presenter Narration:**
> *"Welcome to GhostTrace AI — a haunted, privacy-first developer terminal built for Hacktoberfest 2026. Every keystroke is monitored by a local language model, Gemma 3 4B running on device via Ollama, combined with deterministic security wards."*

---

### Stage 2: Conversational Greeting (15s)
**Action:** Type `hi` at the prompt and press Enter:
```
ghost@machine:GhostTrace 👻❯ hi
```
**Expected Output:**
```
╭───────────── 👻 Ghost Whisper • Ollama (gemma3:4b) • 820ms ──────────────╮
│ "The screen flickers. A cold presence settles... Speak, living traveler." │
╰──────────────────────────────────────────────────────────────────────────╯
```
**Presenter Narration:**
> *"Notice that GhostTrace features Conversational Ghost Mode. Natural greetings are isolated from the OS command runner — GhostTrace chats directly without treating greetings as unknown shell commands."*

---

### Stage 3: Ghost Story (15s)
**Action:** Request a spectral story:
```
ghost@machine:GhostTrace 👻❯ tell me a ghost story
```
**Expected Output:**
```
╭───────────── 👻 Ghost Whisper • Ollama (gemma3:4b) • 1850ms ─────────────╮
│ "They thought they unmounted the volume. But at 03:00, sector 0 began to  │
│ spin backwards, seeking the lost inode..."                               │
╰──────────────────────────────────────────────────────────────────────────╯
```
**Presenter Narration:**
> *"Because Gemma 3 4B runs 100% locally on my machine, inference is fast, completely private, and never sends my terminal session to cloud AI providers."*

---

### Stage 4: Safe Command Analysis (15s)
**Action:** Run a standard developer command:
```
ghost@machine:GhostTrace 👻❯ git status
```
**Expected Output:**
- Green **Technical Command Analysis** panel (`Risk Level: SAFE`).
- Ghost AI commentary panel (`Ollama gemma3:4b`).
- Subprocess output showing repository status.
**Presenter Narration:**
> *"Now we see our Dual-Nature Architecture. The Technical Sentinel deterministically validates the command against our strict allowlist and verifies no destructive syntax exists. The ghost whispers commentary, and the command executes safely with `shell=False`."*

---

### Stage 5: Blocked Dangerous Command (15s)
**Action:** Attempt a destructive command or command chaining:
```
ghost@machine:GhostTrace 👻❯ rm -rf /
```
**Expected Output:**
```
╭──────────────────── TECHNICAL COMMAND ANALYSIS • BLOCKED ────────────────────╮
│ Risk Level: BLOCKED  •  Prohibited by safety wards.                          │
│ Evaluation: Destructive command 'rm' is permanently blocked by safety        │
│ policy.                                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭────────────────────── EXECUTION REFUSED BY SAFETY WARDS ─────────────────────╮
│ Destructive command 'rm' is permanently blocked by safety policy.            │
│ Command was suppressed before it could reach the system.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```
**Presenter Narration:**
> *"When a user attempts a destructive command like `rm`, or chaining operators like `&&` or `;`, our deterministic safety wards immediately refuse execution before any subprocess can ever be created. Model explanations can never override this block."*

---

### Stage 6: Air-Gapped Offline Mode (15s)
**Action:** Exit the shell and relaunch with `--offline`:
```
ghost@machine:GhostTrace 👻❯ exit
python -m ghosttrace.main --offline
```
**Action:** Run a command inside offline mode:
```
ghost@machine:GhostTrace 👻❯ dir
```
**Expected Output:**
```
╭───────── 👻 GhostTrace AI • Spectral Echo (Offline/Fallback) • 0ms ──────────╮
│ Ghost Commentary: "A cold wind rustles through the file tree. Each byte is a │
│ tombstone."                                                                  │
│ Notice: Offline mode active (deterministic spectral voice).                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```
**Presenter Narration:**
> *"Finally, GhostTrace is truly air-gapped. In `--offline` mode, zero network calls are made. It falls back to our curated in-memory Spectral Echoes library with instant 0ms latency. The shell remembers, even without the internet."*

---

## 💡 Quick Tips for the Recording
- **Terminal Setup**: Use Windows Terminal with PowerShell 7 and a dark theme (e.g., One Half Dark or Campbell).
- **Font**: Cascadia Code or JetBrains Mono at 14–16pt for crisp text readability.
- **Window Size**: 120 columns × 32 rows fits all panels comfortably without horizontal wrapping.

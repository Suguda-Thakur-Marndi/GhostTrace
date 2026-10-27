# GhostTrace: Ghost in the Machine — Implementation Plan

**Target Event:** Hacktoberfest — *Ghost in the Machine*  
**Architecture:** Non-blocking Shell Possession (Bash/Zsh) with Local Open-Weight LLMs  
**Baseline Test Status:** 226/226 tests passing in 0.47s  
**Runtime Dependencies:** Python 3.10+ Standard Library (Zero third-party runtime dependencies)  
**Development Dependencies:** `pytest>=8.0.0`, `rich>=13.7.0`  

---

## 1. Executive Summary & Core Vision

GhostTrace transforms an ordinary Bash or Zsh terminal session into a haunted machine. Rather than confining the user inside an artificial Python REPL wrapper, GhostTrace hooks directly into real interactive shell sessions via `haunt.sh`. 

As commands are executed, GhostTrace asynchronously observes:
- Command name and sanitized argument summary (never raw secrets or sensitive data)
- Exit status code
- Current working directory basename
- Time of day (local hour)
- Cumulative session command count

Whispers are generated locally using open-weight models (via Ollama or llama.cpp) or deterministic offline fallbacks, with a strict timeout (default ~2.5s). Crucially:
- **Zero Prompt Lag:** Shell prompts and command execution are never delayed. Inference runs completely in the background.
- **Zero Cloud Leakage:** All network calls are strictly restricted to validated loopback interfaces (`localhost`, `127.0.0.1`, `::1`). Offline mode produces zero HTTP requests.
- **Safety First:** Whispers are plain text comments output strictly above the prompt or to stderr; model outputs are never executed, evaluated, or piped into shell commands.

---

## 2. Existing Repository Audit & Baseline

### 2.1 Existing Architecture
- **`ghosttrace/config.py`**: Configuration management dataclass, hardcoded personality definitions (`ghosttrace`, `spectral_wraith`, `cyber_poltergeist`, `crypt_keeper`), allowed command lists.
- **`ghosttrace/ollama_client.py`**: Localhost-enforced HTTP client using `urllib.request`.
- **`ghosttrace/safety.py`**: Deterministic risk analyzer with command tokenization, forbidden operators, allowlist, and elevation checks.
- **`ghosttrace/command_runner.py`**: `subprocess.run(shell=False)` command execution runner with built-in commands (`cd`, `pwd`, `ls`, `cat`, etc.).
- **`ghosttrace/ghost.py`**: `GhostEngine` producing triad responses (`[Whisper]`, `[Explanation]`, `[Risk Warning]`) and conversational replies.
- **`ghosttrace/shell.py`**: Interactive REPL loop built with `rich`.
- **`ghosttrace/main.py`**: CLI entry point with `--model`, `--personality`, `--offline`, `--check-health`, `--explain`.

### 2.2 Reusable vs. Shell-Possession Components
| Component | Reusability | Action for Real Shell Possession |
| :--- | :--- | :--- |
| **Localhost Validator (`ollama_client.py`)** | High | Extract/expand to support both Ollama (`/api/chat`) and llama.cpp (`/v1/chat/completions`), strict loopback validation, zero redirects. |
| **Safety Tokenizer & Sanitizer (`safety.py`)** | High | Enhance with deep secret redaction (API keys, bearer tokens, passwords, `export FOO=...`, SSH keys, embedded URL credentials). |
| **Deterministic Fallback (`ghost.py`)** | High | Extract into modular canned whisper pools for offline/fast fallback mode. |
| **Personas (`config.py`)** | Partial | Move to user-editable, plain-text files in `ghosts/` (`poltergeist`, `cobol_ghost`, `victorian_medium`, `abuela`, `unix_elder`), loaded dynamically. |
| **Command Runner (`command_runner.py`)** | REPL-only | Preserve for the existing Python REPL. The shell possession architecture uses native Bash/Zsh command execution. |
| **REPL Loop (`shell.py`)** | REPL-only | Preserve untouched so existing REPL workflows and 226 tests continue functioning. |

---

## 3. Target Architecture & File Structure

```text
GhostTrace/
├── haunt.sh                   # Interactive Bash/Zsh shell integration & hook definitions
├── ghostd.py                  # Background daemon / CLI worker for inference & session state
├── ghosts/                    # Editable plain-text persona files
│   ├── poltergeist            # Default mischievous, atmospheric terminal ghost
│   ├── cobol_ghost            # All-caps bureaucratic mainframe spirit
│   ├── victorian_medium       # Theatrical séance host with archaic supernatural tone
│   ├── abuela                 # Warm, comforting spirit of remembrance
│   └── unix_elder             # Terse, dry Bell Labs computing spirit
├── install.sh                 # macOS & Linux installation script (idempotent, safe backups)
├── demo.sh                    # Repeatable terminal demonstration script
├── ghosttrace/                # Preserved original Python package (REPL & backward compat)
├── tests/
│   ├── test_command_runner.py # Existing REPL tests
│   ├── test_ghost.py          # Existing REPL tests
│   ├── test_ollama_client.py  # Existing REPL tests
│   ├── test_safety.py         # Existing REPL tests
│   ├── test_shell.py          # Existing REPL tests
│   ├── test_ghostd.py         # NEW: Daemon, redaction, localhost-only, timeout tests
│   ├── test_personas.py       # NEW: Persona loading, safety, custom personas
│   ├── test_haunt_shell.py    # NEW: Shell hook, PROMPT_COMMAND, exit code tests
│   └── test_dramatic.py       # NEW: Dramatic events, 13th command, midnight, tale, forget
├── docs/
│   ├── IMPLEMENTATION_PLAN.md # This document
│   ├── ARCHITECTURE.md        # Deep dive into shell possession & async pipeline
│   ├── SECURITY.md            # Threat model, secret redaction, and local isolation limits
│   ├── PERSONAS.md            # Guide to writing custom ghosts
│   ├── HACKTOBERFEST_SUBMISSION.md
│   └── DEMO_SCRIPT.md
└── README.md                  # Comprehensive open-source documentation
```

---

## 4. Phase-by-Phase Implementation Roadmap

### Phase 0: Repository Audit & Planning (Current Phase)
- Inspect all files, test suites, and git status.
- Document baseline test results (226 tests passing).
- Commit to backward compatibility with existing `ghosttrace` package.
- Output `docs/IMPLEMENTATION_PLAN.md`.

### Phase 1: Bash and Zsh Possession (`haunt.sh`)
- Implement `haunt.sh` with dual Bash 4+ and Zsh compatibility.
- Interactive-only gate: check `[[ $- == *i* ]]` unless `HAUNT_FORCE=1`.
- Bash: `PROMPT_COMMAND` handling (both string and array forms in Bash 5.1+), preserving `$?`.
- Zsh: `add-zsh-hook` for `preexec`, `precmd`, and `zshexit`.
- Guard against duplicate sourcing via `__HAUNT_LOADED`.
- Shell commands: `haunt on|off|status|chance N|speed S|ghost NAME|ghost list|tale|forget` and two-attempt `exorcise`.
- Terminal output to `stderr` only when connected to a TTY (`[ -t 2 ]`).

### Phase 2: Asynchronous Whisper Pipeline
- Lockless, non-blocking queue using user-private temporary directory (`~/.local/share/haunt/run/` or `$XDG_RUNTIME_DIR/haunt/`).
- Permission: `0700` directory, `0600` files.
- Request-ID based decoupling: worker writes to `<req_id>.whisper.tmp` then renames to `<req_id>.whisper` atomically.
- Prompt boundary reader: `precmd` checks for ready whisper matching recent request, prints it, and unlinks file.
- Redraw safety: whisper printed before prompt redraw; no input line corruption.

### Phase 3: Local Open-Weight LLM Engine (`ghostd.py`)
- Standard library HTTP client supporting Ollama (`/api/chat`) and llama.cpp (`/v1/chat/completions`).
- Hard default timeout of 2.5s (configurable via `HAUNT_TIMEOUT`).
- Strict output sanitization:
  - Strip ANSI escape sequences & terminal control codes.
  - Strip markdown formatting (`**`, `__`, backticks) and quotation marks.
  - Single first sentence only (< 20 words).
  - Rejection of empty, malformed, or executable-like outputs.
- Deterministic fallback if LLM is offline, slow, or returns invalid text.

### Phase 4: Privacy & Network Security
- Loopback-only enforcement: resolve host and verify against `127.0.0.1`, `::1`, `localhost`. Block non-loopback IPs and DNS rebinding tricks.
- Comprehensive secret redaction:
  - Patterns: AWS keys, GitHub tokens (`ghp_...`), JWTs, Bearer tokens, private keys (`BEGIN PRIVATE KEY`), passwords, `export KEY=VALUE`.
  - Path sanitization: only basename of CWD, strip home directory prefixes from arguments.
  - Command output is *never* captured or transmitted.
- Offline guarantee: when `HAUNT_OFFLINE=1` or during offline fallback, no sockets or HTTP requests are created.

### Phase 5: Persona System (`ghosts/`)
- Plain text persona files in `ghosts/`:
  1. `poltergeist`: Default eerie, witty terminal companion.
  2. `cobol_ghost`: Bureaucratic all-caps mainframe phantom mourning punch cards.
  3. `victorian_medium`: Archaic, theatrical séance speaker.
  4. `abuela`: Tender, loving spirit of remembrance (Día de los Muertos style).
  5. `unix_elder`: Laconic Bell Labs hacker from the 1970s.
- Validation: persona names sanitized (`[a-zA-Z0-9_-]+`), directory traversal prevented (`../` rejected).

### Phase 6: Dramatic Events & Session State
- 40% default whisper probability (`HAUNT_CHANCE=40`).
- 100% trigger on dramatic events:
  - `rm -rf`, `sudo`, `kill -9`, `git reset --hard`
  - Exit codes 127 (command not found), 130 (SIGINT / ^C), 139 (SIGSEGV)
- Atmospheric triggers:
  - Midnight to 05:00 hours
  - Every 13th command in session
  - First command of the calendar day
  - Repeated failures (3+ consecutive non-zero exit codes)
  - Shell exit farewell
- Session store: minimal stats file in `~/.local/share/haunt/stats.json` (no raw commands or secrets).
- `haunt forget` command securely wipes history and session state.

### Phase 7: Ghost Tale (`haunt tale`)
- Synthesizes a 4-sentence gothic/cyberpunk ghost story summarizing the current session's journey.
- Input: at most last 20 sanitized command summaries.
- Local LLM prompt with strict 4-sentence constraint and persona styling.
- Canned 4-sentence fallback if model is offline or times out.

### Phase 8: Installer & Demo
- `install.sh`: Detects shell, checks Python version, checks Ollama presence, offers safe automated sourcing into `.bashrc` or `.zshrc` with backup, provides uninstall script.
- `demo.sh`: Interactive demo presenting all 8 dramatic scenarios cleanly.

### Phase 9: Documentation & Hacktoberfest Story
- Complete overhaul of `README.md` with GIFs/visuals, quickstart, configuration, architectural rationale, and "Why Open Source Matters Here" essay.
- Detailed architecture, security, and persona guides in `docs/`.

### Phase 10: Automated Test Suite & Verification
- Unit and integration tests covering:
  - Shell hook mechanics, `PROMPT_COMMAND` handling, exit status preservation
  - Secret redaction and pattern safety
  - ANSI/escape sequence stripping
  - Loopback-only enforcement and offline zero-network verification
  - Persona loader and directory traversal rejection
  - Dramatic event triggers and rate limiting
  - `haunt tale` and `haunt forget`
  - Non-blocking async queue mechanics

---

## 5. Security & Threat Model

| Threat | Impact | Mitigation |
| :--- | :--- | :--- |
| **Command / Secret Leakage** | High | Secret regex redaction runs *before* queueing. Only command names and sanitized arg summaries are used. Never capture stdout/stderr. |
| **Prompt Lag / Shell Freezing** | High | Shell hook initiates background process via `nohup` / `&` and immediately returns control to user. Worker times out at 2.5s. |
| **Remote Network Exfiltration** | Critical | Strict loopback validation (`127.0.0.1`, `localhost`, `::1`). No redirects, no proxy bypass. Zero HTTP requests in offline mode. |
| **Terminal Corruption** | Medium | Whispers are sanitized of all control chars and ANSI escapes, then rendered only at clean prompt boundaries when `[ -t 2 ]`. |
| **Model Hallucination Execution** | Critical | GhostTrace NEVER executes or passes LLM output into `eval` or shell pipelines. Whispers are display-only. |
| **Unauthorized File Access** | Medium | Session files stored in `~/.local/share/haunt/` with `0700` / `0600` permissions. Persona loader rejects path traversals. |

---

## 6. Verification & Quality Gates

Every phase must satisfy:
1. `python -m pytest -q` (all existing 226 tests + all new tests pass).
2. `python -m compileall -q .` (clean bytecode compilation with zero syntax errors).
3. `bash -n haunt.sh install.sh demo.sh` (valid shell syntax).
4. Zero uncommitted Git changes without user request.
5. All tests run with deterministic offline mocks; no external services or models required.

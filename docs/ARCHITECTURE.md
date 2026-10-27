# GhostTrace Architecture: Possession & Asynchronous Whispers

GhostTrace implements a dual architecture designed for production-grade open-source usage:
1. **Real Shell Possession (`haunt.sh`)**: Hooks directly into the user's interactive Bash or Zsh session to whisper context-aware commentary.
2. **Local AI Daemon & Worker (`ghostd.py`)**: Asynchronous background pipeline coordinating local open-weight model inference (Ollama / llama.cpp), deterministic offline echoes, secret redaction, and session state.
3. **Preserved Haunted REPL (`ghosttrace/`)**: The original standalone Python REPL with deterministic safety gates, preserved for cross-platform and Windows terminal exploration.

```
       Interactive Shell (Bash / Zsh)
  ┌────────────────────────────────────────┐
  │  PROMPT_COMMAND / add-zsh-hook         │
  │  1. Capture Exit Status ($?)           │
  │  2. Extract Command & CWD Name         │
  │  3. Prime/Check History (no empty Enter)
  │  4. Read & Render Ready Whispers       │
  └──────────────────┬─────────────────────┘
                     │ Fork & Disown (0ms Prompt Lag)
                     ▼
  ┌────────────────────────────────────────┐
  │  ghostd.py Worker                      │
  │  1. Deep Secret Redaction              │
  │  2. Dramatic Event & Rate-Limit Check  │
  │  3. Strict Localhost HTTP Request      │
  │     (Ollama: /api/chat, 2.5s timeout)  │
  │  4. Output Sanitizer (<20 words, 1 sent)
  │  5. Atomic Write to ~/.local/share/haunt
  └──────────────────┬─────────────────────┘
                     │
                     ▼
  ┌────────────────────────────────────────┐
  │  Localhost-Only LLM / Fallback         │
  │  • Ollama (llama3.2:3b / qwen2.5:3b)   │
  │  • llama.cpp server                    │
  │  • Offline Canned Persona Echoes       │
  └────────────────────────────────────────┘
```

---

## 1. Shell Possession Mechanics (`haunt.sh`)

### 1.1 Interactive-Only Gate
The hook executes only in interactive shells where `[[ $- == *i* ]]` or when explicitly forced for automated testing via `HAUNT_FORCE=1`. Non-interactive shell scripts, cron jobs, background pipelines, subshells, and build tools are completely unaffected.

### 1.2 Bash 4+ & Bash 5.1+ Integration
In Bash, command interception occurs via `PROMPT_COMMAND`:
- **Preserving `$?`**: The exit status of the user's command is captured as the very first operation:
  ```bash
  __haunt_bash_prompt() {
      local __haunt_exit=$?
      # ...
      return $__haunt_exit
  }
  ```
  Returning `$__haunt_exit` ensures that existing prompts, prompt themes (like Starship or Oh-My-Bash), and conditional styling see the original exit code.
- **Array and String Forms**: Supports Bash 5.1+ array `PROMPT_COMMAND` declarations without clobbering existing array entries, as well as classic string-based `PROMPT_COMMAND`.
- **Empty Enter Handling**: Compares `HISTCMD` against the previously recorded history counter. If the user presses Enter on an empty line, `HISTCMD` does not advance, and no whisper is queued.
- **Trap Preservation**: Attaches an exit farewell to `trap ... EXIT` without overwriting existing traps.

### 1.3 Zsh Integration
In Zsh, GhostTrace uses the native `add-zsh-hook` facility:
- `preexec`: Captures command text into a session variable before execution.
- `precmd`: Runs prior to prompt redraw, captures the original exit status, dispatches the async worker, and displays whispers.
- `zshexit`: Renders an atmospheric farewell when the session closes.

---

## 2. Asynchronous Whisper Pipeline (`ghostd.py`)

To ensure GhostTrace never delays the shell prompt or blocks command execution:
1. **Immediate Fork & Return**: The shell spawns a background Python subshell detached via `& disown 2>/dev/null` and returns immediately.
2. **Private File Queue**: Background workers communicate via user-private run directory (`~/.local/share/haunt/run/` or `$XDG_RUNTIME_DIR/haunt/`), created with `0700` permissions.
3. **Atomic Result Files**: Completed whispers are written to `<req_id>.res.tmp` with `0600` permissions and atomically renamed to `<req_id>.res`.
4. **Prompt Boundary Display**: When the shell is ready to render the prompt, it checks for completed result files, types them to stderr via the typewriter effect, and unlinks the file.

---

## 3. Persona Subsystem (`ghosts/`)

Personas are plain-text, editable files stored in `ghosts/`:
- `poltergeist`: Default mischievous, eerie terminal phantom.
- `cobol_ghost`: All-caps bureaucratic mainframe spirit mourning punch cards and batch jobs.
- `victorian_medium`: Formal 19th-century spiritualist speaking of ectoplasm, séances, and bells.
- `abuela`: Tender, loving spirit of remembrance inspired by Día de los Muertos.
- `unix_elder`: Terse, laconic Bell Labs hacker prioritizing simplicity and clean pipes.

Users can create new personas in `ghosts/my_ghost` without touching Python code. Persona names are validated against `^[a-zA-Z0-9_-]+$` to prevent directory traversal vulnerabilities.

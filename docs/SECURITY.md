# GhostTrace Security & Privacy Threat Model

**Version:** 0.2.0  
**Audit Scope:** Shell Hook, Async Daemon, Local Model Client, Secret Redactor, and Storage  

---

## 1. Core Security & Privacy Principles

1. **Zero Cloud Telemetry**: GhostTrace never transmits prompts, paths, command names, arguments, or environment variables to any remote server or cloud AI provider.
2. **Localhost-Only Enforcement**: Outbound HTTP requests are cryptographically restricted to loopback destinations (`127.0.0.1`, `localhost`, `::1`). Non-loopback IPs, remote hostnames, DNS rebinding, and HTTP redirects are permanently blocked.
3. **Never Execute Model Output**: Whispers are treated strictly as untrusted display strings. GhostTrace never passes LLM output into `eval`, `exec`, or shell pipelines.
4. **Zero Command Output Capture**: GhostTrace observes command execution metadata (command name, exit status code, working directory basename, hour, and session count). It never captures stdout or stderr streams.
5. **Deep Secret Redaction**: Before any argument summary reaches prompt construction, regex filters redact API keys, tokens, passwords, authorization headers, private key blocks, and sensitive credential paths.

---

## 2. Threat Analysis & Mitigations

| Threat Vector | Risk Level | Mitigation Strategy |
| :--- | :--- | :--- |
| **Command / Credential Leakage** | Critical | Secrets are redacted *before* prompt generation. Full filesystem paths are truncated to directory basenames. Home directories (`/home/user`) are stripped. Command output is never read. |
| **Outbound Data Exfiltration** | Critical | `LocalLoopbackClient` rejects all external hostnames and non-loopback IP addresses. HTTP redirects are blocked (`LocalhostNoRedirectHandler`). External proxies are bypassed via `ProxyHandler({})`. |
| **Terminal Redraw & Prompt Freezing** | High | Inference runs in detached background processes (`nohup`/`& disown`). Hard inference timeout defaults to 2.5s. Whispers print above clean prompt boundaries to `stderr` only when `[ -t 2 ]`. |
| **Terminal Escapes & Control Injection** | High | `OutputSanitizer` strips ANSI escape codes (`\x1b[...]`) and control characters (`[\x00-\x1f]`) to prevent terminal hijacking or status-line spoofing. |
| **Malicious Shell Code Injection** | High | Model outputs matching executable commands (e.g. `sudo`, `rm`, `kill`, `$(...)`, `;`, `|`, `&`) are rejected. Output is limited to one short sentence (<20 words). |
| **Directory Traversal in Personas** | Medium | Persona loader validates names against `^[a-zA-Z0-9_-]+$` and rejects path traversal sequences (`../`, `/`). |
| **Multi-User Permission Snooping** | Medium | Run queues and session stats are stored under `~/.local/share/haunt/` with `0700` directory and `0600` file permissions. |

---

## 3. Secret Redaction Engine

GhostTrace scans all command arguments with deterministic regular expressions before constructing prompt context:

- **AWS Access Keys**: `AKIA[0-9A-Z]{16}` ➔ `[REDACTED_AWS_KEY]`
- **GitHub Personal Access Tokens**: `gh[pousr]_[A-Za-z0-9_]{36,255}` ➔ `[REDACTED_GH_TOKEN]`
- **OpenAI API Keys**: `sk-[A-Za-z0-9]{20,}` ➔ `[REDACTED_API_KEY]`
- **JWT / Bearer Tokens**: `Bearer [A-Za-z0-9\-_=.]+` ➔ `Bearer [REDACTED_JWT]`
- **Private Keys**: `-----BEGIN [A-Z ]*PRIVATE KEY-----` ➔ `[REDACTED_PRIVATE_KEY]`
- **URLs with Credentials**: `https://user:password@host` ➔ `https://[REDACTED_USER]:[REDACTED_PW]@host`
- **Shell Variable Assignments**: `export DB_PASS=secret` ➔ `export DB_PASS=[REDACTED]`
- **CLI Password Arguments**: `--password secret`, `-p secret` ➔ `--password [REDACTED]`
- **Sensitive Key Paths**: `~/.ssh/id_rsa`, `credentials.json`, `.env` ➔ `[REDACTED_FILE_PATH]`

---

## 4. Transparent Disclaimer: Local Inference vs. OS Sandboxing

> [!IMPORTANT]
> GhostTrace is a haunted terminal companion that observes commands and provides atmospheric commentary.
> It is **not** an operating system sandbox, virtual machine, container, or seccomp barrier.
>
> When you run commands in your Bash or Zsh session, those commands execute with your standard user account permissions. GhostTrace does not attempt to restrict or isolate commands you run in your shell. For sandboxing, use Docker, Podman, bubblewrap, or dedicated virtual machines.

# GhostTrace: 15-Second & 60-Second Live Demonstration Script

This script walks through demonstrating GhostTrace's shell possession capabilities.
You can run this demo automatically using:
```bash
./demo.sh
```

---

## 15-Second Fast Demo

1. **Activate Possession**:
   ```bash
   source ./haunt.sh
   # 👻 GhostTrace: The shell has been possessed. Type commands normally...
   ```
2. **Execute Command**:
   ```bash
   git status
   # 👻 [GhostTrace] Untracked files rustle like dry leaves in forgotten branches.
   ```
3. **Trigger Banishment**:
   ```bash
   exorcise
   # 👻 [GhostTrace] The machine shudders... you cannot banish me so easily.
   exorcise
   # 👻 [GhostTrace] The ghost wails and dissolves into cold static. The machine is free.
   ```

---

## Complete 8-Scenario Walkthrough

### Scenario 1: Shell Initialization Greeting
- **Command**: `source ./haunt.sh`
- **Behavior**: Verifies interactive shell, primes history counter, displays greeting.

### Scenario 2: Normal Command & Contextual Whisper
- **Command**: `ls -la`
- **Behavior**: Command output prints normally. GhostTrace evaluates command name (`ls`), status (`0`), and directory basename in background. A short phosphor-green whisper types out above the prompt.

### Scenario 3: Command Failure
- **Command**: `cat nonexistent_ghost_file.txt`
- **Behavior**: Command fails with exit status `1`. The ghost detects non-zero exit and produces a failure whisper about resistance in the registers.

### Scenario 4: Switching Personas (`cobol_ghost`)
- **Command**: `haunt ghost cobol_ghost`
- **Command**: `git status`
- **Behavior**: `cobol_ghost` responds in ALL-CAPS bureaucratic mainframe style mourning punch cards and JCL.

### Scenario 5: Dramatic Event Trigger (100% Chance)
- **Command**: `kill -9 9999`
- **Behavior**: Bypasses the 40% chance roll and immediately triggers a dramatic response.

### Scenario 6: Midnight / 13th Command Special Trigger
- **Command**: Run the 13th command in the session or run during midnight hours (00:00–05:00).
- **Behavior**: Triggers atmospheric 13th command or midnight-themed whisper.

### Scenario 7: 100% Offline Mode
- **Command**: `export HAUNT_OFFLINE=1; python3 -c 'print("offline")'`
- **Behavior**: Complete zero-network execution using deterministic in-memory spectral echoes.

### Scenario 8: Status & Two-Attempt Exorcise
- **Command**: `haunt status` (shows PID, persona, model, endpoint, session stats)
- **Command**: `exorcise` (1st attempt fails with refusal)
- **Command**: `exorcise` (2nd attempt disables haunt and restores ordinary terminal)

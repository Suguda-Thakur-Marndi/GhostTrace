#!/usr/bin/env bash
# demo.sh - Repeatable Demonstration Script for GhostTrace
# Shows all 8 core capabilities of the haunted terminal companion.
# Suitable for automated terminal recordings, demos, and Hacktoberfest showcases.

set -euo pipefail

GREEN="\033[38;5;35m"
YELLOW="\033[38;5;220m"
RED="\033[38;5;196m"
CYAN="\033[38;5;51m"
BOLD="\033[1m"
DIM="\033[2m"
ITALIC="\033[3m"
RESET="\033[0m"

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HAUNT_FORCE=1
export HAUNT_SPEED="fast"
export HAUNT_DELAY="0.008"

# Locate python
PYTHON_BIN="python3"
if ! command -v python3 >/dev/null 2>&1 && command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

banner_step() {
    local step_num="$1"
    local title="$2"
    echo ""
    echo -e "${CYAN}${BOLD}════════════════════════════════════════════════════════════════════${RESET}"
    echo -e "${CYAN}${BOLD} SCENARIO ${step_num}: ${title}${RESET}"
    echo -e "${CYAN}${BOLD}════════════════════════════════════════════════════════════════════${RESET}"
    sleep 0.8
}

simulate_prompt() {
    local cmd="$1"
    echo -ne "${BOLD}${GREEN}ghost${RESET}${DIM}@${RESET}${BOLD}${GREEN}machine${RESET}:${DIM}GhostTrace${RESET}${BOLD}${GREEN} 👻❯ ${RESET}"
    local len=${#cmd}
    for (( i=0; i<len; i++ )); do
        echo -ne "${cmd:$i:1}"
        sleep 0.03
    done
    echo ""
    sleep 0.3
}

# ==============================================================================
# HEADER
# ==============================================================================

clear 2>/dev/null || true
echo -e "${BOLD}${GREEN}"
cat << 'EOF'
       .-.
      (o.o)   G H O S T T R A C E
       |=|    Live Interactive Shell Demonstration
      /   \   Hacktoberfest: Ghost in the Machine
     (:   :)  Local AI • Privacy-First • Zero Cloud Telemetry
      `"`"`
EOF
echo -e "${RESET}"
sleep 1

# ==============================================================================
# SCENARIO 1: SHELL INITIALIZATION GREETING
# ==============================================================================

banner_step "1" "Shell Initialization & Possession Greeting"
simulate_prompt "source ./haunt.sh"
echo -e "${GREEN}👻 GhostTrace:${RESET} ${ITALIC}The shell has been possessed. Type commands normally...${RESET}"
sleep 1

# ==============================================================================
# SCENARIO 2: NORMAL COMMAND & CONTEXTUAL WHISPER
# ==============================================================================

banner_step "2" "Normal Command Execution & Contextual Whisper"
simulate_prompt "ls -la"
echo "total 64"
echo "drwxr-xr-x  6 user  staff   192 Oct 27 12:00 ."
echo "drwxr-xr-x  8 user  staff   256 Oct 27 11:30 .."
echo "-rw-r--r--  1 user  staff  1080 Oct 27 11:00 LICENSE"
echo "-rw-r--r--  1 user  staff  2500 Oct 27 11:45 README.md"
echo "-rwxr-xr-x  1 user  staff  5400 Oct 27 12:00 haunt.sh"
sleep 0.4
# Execute actual whisper through ghostd.py with poltergeist persona
"$PYTHON_BIN" "${DEMO_DIR}/ghostd.py" whisper --cmd "ls" --status 0 --cwd "GhostTrace" --chance 100 --persona "poltergeist" | while IFS= read -r line; do
    echo -e "${GREEN}👻 [GhostTrace]${RESET} ${ITALIC}${line}${RESET}"
done
sleep 1.2

# ==============================================================================
# SCENARIO 3: COMMAND FAILURE
# ==============================================================================

banner_step "3" "Command Failure (Exit Code 1)"
simulate_prompt "cat nonexistent_spectral_file.txt"
echo "cat: nonexistent_spectral_file.txt: No such file or directory" >&2
sleep 0.4
"$PYTHON_BIN" "${DEMO_DIR}/ghostd.py" whisper --cmd "cat" --status 1 --cwd "GhostTrace" --chance 100 --persona "poltergeist" | while IFS= read -r line; do
    echo -e "${GREEN}👻 [GhostTrace]${RESET} ${ITALIC}${line}${RESET}"
done
sleep 1.2

# ==============================================================================
# SCENARIO 4: PERSONA SWITCH (cobol_ghost)
# ==============================================================================

banner_step "4" "Switch Persona to 'cobol_ghost' (Mainframe Spirit)"
simulate_prompt "haunt ghost cobol_ghost"
echo "Ghost persona set to 'cobol_ghost'."
sleep 0.6
simulate_prompt "git status"
echo "On branch master"
echo "nothing to commit, working tree clean"
sleep 0.4
"$PYTHON_BIN" "${DEMO_DIR}/ghostd.py" whisper --cmd "git" --status 0 --cwd "GhostTrace" --chance 100 --persona "cobol_ghost" | while IFS= read -r line; do
    echo -e "${GREEN}👻 [GhostTrace]${RESET} ${ITALIC}${line}${RESET}"
done
sleep 1.2

# ==============================================================================
# SCENARIO 5: DRAMATIC EVENT (SIGKILL / 100% TRIGGER)
# ==============================================================================

banner_step "5" "Dramatic Event Trigger (kill -9 / 100% Whisper Chance)"
simulate_prompt "kill -9 9999"
echo "bash: kill: (9999) - No such process" >&2
sleep 0.4
# Dramatic events bypass chance roll automatically in ghostd.py
"$PYTHON_BIN" "${DEMO_DIR}/ghostd.py" whisper --cmd "kill" --args "-9 9999" --status 1 --cwd "GhostTrace" --chance 0 --persona "unix_elder" | while IFS= read -r line; do
    echo -e "${GREEN}👻 [GhostTrace]${RESET} ${ITALIC}${line}${RESET}"
done
sleep 1.2

# ==============================================================================
# SCENARIO 6: MIDNIGHT BEHAVIOR / 13TH COMMAND MOMENT
# ==============================================================================

banner_step "6" "Atmospheric Special Event (Simulated 13th Command)"
simulate_prompt "date"
echo "Sun Oct 27 00:13:00 UTC 2026"
sleep 0.4
# Force 13th command trigger
"$PYTHON_BIN" "${DEMO_DIR}/ghostd.py" whisper --cmd "date" --status 0 --cwd "GhostTrace" --chance 100 --persona "victorian_medium" | while IFS= read -r line; do
    echo -e "${GREEN}👻 [GhostTrace]${RESET} ${ITALIC}${line}${RESET}"
done
sleep 1.2

# ==============================================================================
# SCENARIO 7: OFFLINE ZERO-NETWORK FALLBACK
# ==============================================================================

banner_step "7" "100% Offline Mode (Zero Network Calls, Canned Spectral Echo)"
simulate_prompt "HAUNT_OFFLINE=1 python3 -c 'print(\"offline work\")'"
echo "offline work"
sleep 0.4
export HAUNT_OFFLINE=1
"$PYTHON_BIN" "${DEMO_DIR}/ghostd.py" whisper --cmd "python3" --status 0 --cwd "GhostTrace" --chance 100 --persona "abuela" | while IFS= read -r line; do
    echo -e "${GREEN}👻 [GhostTrace]${RESET} ${ITALIC}${line}${RESET}"
done
export HAUNT_OFFLINE=0
sleep 1.2

# ==============================================================================
# SCENARIO 8: HAUNT STATUS & TWO-ATTEMPT EXORCISE
# ==============================================================================

banner_step "8" "Possession Status & Two-Step Exorcise Ritual"
simulate_prompt "haunt status"
"$PYTHON_BIN" "${DEMO_DIR}/ghostd.py" status
sleep 1

simulate_prompt "exorcise"
echo -e "${RED}👻 [GhostTrace] The machine shudders... you cannot banish me so easily.${RESET}"
echo -e "${DIM}Speak the word 'exorcise' once more if your resolve holds.${RESET}"
sleep 1

simulate_prompt "exorcise"
echo -e "${GREEN}👻 [GhostTrace] The ghost wails and dissolves into cold static. The machine is free.${RESET}"
sleep 1

echo ""
echo -e "${BOLD}${GREEN}Demonstration Complete!${RESET}"
echo -e "${DIM}Try GhostTrace in your own shell: source ./haunt.sh${RESET}"

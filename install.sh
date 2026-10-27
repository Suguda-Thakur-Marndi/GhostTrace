#!/usr/bin/env bash
# install.sh - GhostTrace Setup and Installation Script
# Supports macOS and Linux.
# Detects Bash, Zsh, Python 3.10+, and Ollama without running remote scripts.
# Idempotent, safe backups before configuration changes, zero telemetry.

set -euo pipefail

# ANSI color codes
GREEN="\033[38;5;35m"
YELLOW="\033[38;5;220m"
RED="\033[38;5;196m"
BOLD="\033[1m"
DIM="\033[2m"
RESET="\033[0m"

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HAUNT_SCRIPT="${INSTALL_DIR}/haunt.sh"
MARKER="# GhostTrace Terminal Possession"
SOURCE_LINE="[ -f \"${HAUNT_SCRIPT}\" ] && source \"${HAUNT_SCRIPT}\""

echo -e "${BOLD}${GREEN}"
cat << 'EOF'
       .-.
      (o.o)   G H O S T T R A C E
       |=|    Terminal Possession Installer
      /   \   Hacktoberfest: Ghost in the Machine
     (:   :)  Local AI • Privacy-First • Zero Cloud Telemetry
      `"`"`
EOF
echo -e "${RESET}"

# ==============================================================================
# 1. DEPENDENCY AUDIT
# ==============================================================================

echo -e "${BOLD}1. Auditing System Dependencies...${RESET}"

# Python check
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -n "$PYTHON_BIN" ]; then
    PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.major)")
    PY_MINOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.minor)")
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
        echo -e "  [${GREEN}✓${RESET}] Python ${PY_VER} detected (${PYTHON_BIN})"
    else
        echo -e "  [${YELLOW}!${RESET}] Python ${PY_VER} detected. Python 3.10+ is recommended."
    fi
else
    echo -e "  [${RED}✗${RESET}] Python 3 is not installed or not in PATH."
    echo -e "      Install Python 3.10+ from your package manager (e.g., apt install python3 or brew install python)."
fi

# Shell detection
BASH_AVAIL=0
ZSH_AVAIL=0

if command -v bash >/dev/null 2>&1; then
    BASH_VER=$(bash -c 'echo ${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}')
    echo -e "  [${GREEN}✓${RESET}] GNU Bash ${BASH_VER} detected"
    BASH_AVAIL=1
fi

if command -v zsh >/dev/null 2>&1; then
    ZSH_VER=$(zsh -c 'echo $ZSH_VERSION')
    echo -e "  [${GREEN}✓${RESET}] Zsh ${ZSH_VER} detected"
    ZSH_AVAIL=1
else
    echo -e "  [${DIM}•${RESET}] Zsh not found (optional)"
fi

# Local model daemon check
echo ""
echo -e "${BOLD}2. Auditing Local Open-Weight LLM Providers...${RESET}"
OLLAMA_AVAIL=0
if command -v ollama >/dev/null 2>&1; then
    echo -e "  [${GREEN}✓${RESET}] Ollama CLI detected"
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "  [${GREEN}✓${RESET}] Local Ollama daemon is running on localhost:11434"
        OLLAMA_AVAIL=1
        MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*' | cut -d'"' -f4 || true)
        if [ -n "$MODELS" ]; then
            echo -e "      Found local models: ${MODELS}"
        else
            echo -e "      ${YELLOW}Notice:${RESET} No models found in Ollama."
            echo -e "      Suggested quickstart model: ${BOLD}ollama pull llama3.2:3b${RESET}"
        fi
    else
        echo -e "  [${YELLOW}!${RESET}] Ollama CLI is installed, but daemon is not currently running."
        echo -e "      Start with: ${BOLD}ollama serve${RESET}"
        echo -e "      GhostTrace will gracefully fall back to deterministic spectral echoes."
    fi
else
    echo -e "  [${YELLOW}!${RESET}] Ollama was not found in PATH."
    echo -e "      GhostTrace operates 100% offline out-of-the-box using built-in deterministic echoes."
    echo -e "      To enable neural whispers, install Ollama from https://ollama.ai and run:"
    echo -e "      ${BOLD}ollama pull llama3.2:3b${RESET}"
fi

# ==============================================================================
# 2. INSTALLATION TARGET DISCOVERY
# ==============================================================================

echo ""
echo -e "${BOLD}3. Shell Configuration Integration...${RESET}"

TARGET_RCS=()
if [ -f "${HOME}/.bashrc" ]; then
    TARGET_RCS+=("${HOME}/.bashrc")
elif [ -f "${HOME}/.bash_profile" ]; then
    TARGET_RCS+=("${HOME}/.bash_profile")
fi

if [ -f "${HOME}/.zshrc" ]; then
    TARGET_RCS+=("${HOME}/.zshrc")
fi

install_to_file() {
    local rc_file="$1"
    if grep -qF "$MARKER" "$rc_file" 2>/dev/null; then
        echo -e "  [${GREEN}✓${RESET}] GhostTrace already integrated into ${rc_file} (skipping)."
        return 0
    fi

    # Create safety backup
    local backup="${rc_file}.haunt.bak.$(date +%s)"
    cp "$rc_file" "$backup"
    echo -e "  [${GREEN}✓${RESET}] Created backup: ${backup}"

    # Append hook
    {
        echo ""
        echo "$MARKER"
        echo "$SOURCE_LINE"
    } >> "$rc_file"
    echo -e "  [${GREEN}✓${RESET}] Successfully installed hook into ${rc_file}"
}

uninstall_from_file() {
    local rc_file="$1"
    if [ ! -f "$rc_file" ]; then
        return 0
    fi
    if grep -qF "$MARKER" "$rc_file" 2>/dev/null; then
        local backup="${rc_file}.haunt.bak.$(date +%s)"
        cp "$rc_file" "$backup"
        sed -i.bak "/${MARKER}/d" "$rc_file" 2>/dev/null || sed -i "" "/${MARKER}/d" "$rc_file"
        sed -i.bak "\|${HAUNT_SCRIPT}|d" "$rc_file" 2>/dev/null || sed -i "" "\|${HAUNT_SCRIPT}|d" "$rc_file"
        echo -e "  [${GREEN}✓${RESET}] Removed GhostTrace hooks from ${rc_file}"
    fi
}

MODE="${1:-}"

if [ "$MODE" = "--uninstall" ]; then
    echo -e "Uninstalling GhostTrace hooks from rc files..."
    for rc in "${TARGET_RCS[@]}"; do
        uninstall_from_file "$rc"
    done
    echo -e "${GREEN}Uninstall complete. Your shells are unpossessed.${RESET}"
    exit 0
fi

if [ "$MODE" = "--check" ]; then
    echo -e "${GREEN}Environment audit complete.${RESET}"
    exit 0
fi

if [ "$MODE" = "--auto" ] || [ "$MODE" = "-y" ]; then
    for rc in "${TARGET_RCS[@]}"; do
        install_to_file "$rc"
    done
    echo ""
    echo -e "${GREEN}${BOLD}Installation Complete!${RESET}"
    echo -e "Open a new terminal or run: ${BOLD}source \"${HAUNT_SCRIPT}\"${RESET}"
    exit 0
fi

# Interactive prompt
echo ""
echo -e "Detected shell configuration files:"
for rc in "${TARGET_RCS[@]}"; do
    echo -e "  - ${rc}"
done
echo ""
echo -e "GhostTrace will never modify your files without consent."
echo -e "Would you like to automatically integrate the hook with safety backups? [y/N]: "
read -r CONFIRM || CONFIRM="n"

if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    for rc in "${TARGET_RCS[@]}"; do
        install_to_file "$rc"
    done
    echo ""
    echo -e "${GREEN}${BOLD}Installation Complete!${RESET}"
    echo -e "To activate the ghost in your current session:"
    echo -e "    ${BOLD}source \"${HAUNT_SCRIPT}\"${RESET}"
else
    echo ""
    echo -e "${BOLD}Manual Activation:${RESET}"
    echo -e "Add this single line to your ~/.bashrc or ~/.zshrc:"
    echo -e "    ${GREEN}${SOURCE_LINE}${RESET}"
    echo ""
    echo -e "Or source it on demand whenever you want a haunted session:"
    echo -e "    ${BOLD}source \"${HAUNT_SCRIPT}\"${RESET}"
fi

echo ""
echo -e "${DIM}To uninstall at any time: ./install.sh --uninstall${RESET}"

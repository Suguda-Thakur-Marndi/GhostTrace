#!/usr/bin/env bash
# haunt.sh - GhostTrace Bash and Zsh Possession Hook
# Possesses interactive Bash and Zsh sessions with local open-weight AI whispers.
# Privacy-first • Zero cloud telemetry • Non-blocking asynchronous execution

# ==============================================================================
# 1. INTERACTIVE SAFETY GATE & DUPLICATE SOURCING PROTECTION
# ==============================================================================

# Only load in interactive shells unless HAUNT_FORCE=1 is set for testing
if [[ $- != *i* ]] && [ "${HAUNT_FORCE:-0}" != "1" ]; then
    return 0 2>/dev/null || exit 0
fi

# Prevent duplicate hook installation
if [ -n "${__HAUNT_LOADED:-}" ] && [ "${HAUNT_RELOAD:-0}" != "1" ]; then
    return 0 2>/dev/null || true
fi
export __HAUNT_LOADED=1

# ==============================================================================
# 2. LOCATE GHOSTD.PY AND PYTHON RUNTIME
# ==============================================================================

# Determine the directory where haunt.sh is located
if [ -n "${BASH_SOURCE[0]:-}" ]; then
    __HAUNT_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
elif [ -n "${ZSH_VERSION:-}" ]; then
    __HAUNT_SCRIPT_DIR="$(cd "$(dirname "${(%):-%x}")" 2>/dev/null && pwd)"
else
    __HAUNT_SCRIPT_DIR="$(pwd)"
fi

# Locate ghostd.py
if [ -f "${__HAUNT_SCRIPT_DIR}/ghostd.py" ]; then
    __HAUNT_GHOSTD="${__HAUNT_SCRIPT_DIR}/ghostd.py"
elif [ -f "${HOME}/.local/share/haunt/ghostd.py" ]; then
    __HAUNT_GHOSTD="${HOME}/.local/share/haunt/ghostd.py"
else
    __HAUNT_GHOSTD="${__HAUNT_SCRIPT_DIR}/ghostd.py"
fi

# Locate Python 3 interpreter
if command -v python3 >/dev/null 2>&1; then
    __HAUNT_PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    __HAUNT_PYTHON="python"
else
    __HAUNT_PYTHON="python3"
fi

# ==============================================================================
# 3. RUNTIME CONFIGURATION & SESSION STATE
# ==============================================================================

# Haunt configuration defaults (configurable via environment variables)
export HAUNT_ENABLED="${HAUNT_ENABLED:-1}"
export HAUNT_GHOST="${HAUNT_GHOST:-poltergeist}"
export HAUNT_MODEL="${HAUNT_MODEL:-llama3.2:3b}"
export HAUNT_PROVIDER="${HAUNT_PROVIDER:-ollama}"
export HAUNT_CHANCE="${HAUNT_CHANCE:-40}"
export HAUNT_TIMEOUT="${HAUNT_TIMEOUT:-2.5}"
export HAUNT_SPEED="${HAUNT_SPEED:-normal}"
export HAUNT_SEND_ARGS="${HAUNT_SEND_ARGS:-0}"
export HAUNT_OFFLINE="${HAUNT_OFFLINE:-0}"

# Typewriter delay in seconds based on HAUNT_SPEED
case "${HAUNT_SPEED}" in
    instant|0) __HAUNT_CHAR_DELAY="0" ;;
    fast)      __HAUNT_CHAR_DELAY="0.005" ;;
    slow)      __HAUNT_CHAR_DELAY="0.03" ;;
    normal|*)  __HAUNT_CHAR_DELAY="0.012" ;;
esac

# Internal tracking variables
__HAUNT_EXORCISE_ATTEMPTS=0
__HAUNT_SESSION_PID="$$"
__HAUNT_LAST_HISTCMD=""
__HAUNT_PENDING_REQ=""
__HAUNT_ZSH_LAST_CMD=""
__HAUNT_ZSH_HAS_CMD=0

# Determine run directory for asynchronous queues
if [ -n "${XDG_RUNTIME_DIR:-}" ]; then
    __HAUNT_RUN_DIR="${XDG_RUNTIME_DIR}/haunt"
elif [ -n "${XDG_DATA_HOME:-}" ]; then
    __HAUNT_RUN_DIR="${XDG_DATA_HOME}/haunt/run"
else
    __HAUNT_RUN_DIR="${HOME}/.local/share/haunt/run"
fi
mkdir -p "${__HAUNT_RUN_DIR}" 2>/dev/null
chmod 700 "${__HAUNT_RUN_DIR}" 2>/dev/null || true

# ==============================================================================
# 4. TERMINAL RENDERING & REDRAW SAFETY
# ==============================================================================

__haunt_typewriter() {
    local text="$1"
    local delay="${__HAUNT_CHAR_DELAY:-0.012}"

    # Print only to stderr, only if stderr is a terminal
    if [ ! -t 2 ]; then
        return 0
    fi

    # Phosphor green styling with italic text
    printf "\033[38;5;35m👻 [GhostTrace]\033[0m \033[3m" >&2

    if [ "$delay" = "0" ] || [ -z "$delay" ]; then
        printf "%s\033[0m\n" "$text" >&2
    else
        # Render character by character
        local len=${#text}
        local i=0
        while [ $i -lt $len ]; do
            printf "%s" "${text:$i:1}" >&2
            sleep "$delay" 2>/dev/null || true
            i=$((i + 1))
        done
        printf "\033[0m\n" >&2
    fi
}

__haunt_check_and_display_result() {
    local req_id="$1"
    if [ -z "$req_id" ]; then
        return 0
    fi

    local res_file="${__HAUNT_RUN_DIR}/${req_id}.res"
    if [ -f "$res_file" ]; then
        local whisper_content
        whisper_content=$(cat "$res_file" 2>/dev/null)
        rm -f "$res_file" 2>/dev/null || true
        if [ -n "$whisper_content" ]; then
            __haunt_typewriter "$whisper_content"
        fi
        return 0
    fi
    return 1
}

# ==============================================================================
# 5. USER-FACING SHELL COMMANDS
# ==============================================================================

haunt() {
    local subcommand="${1:-status}"
    case "$subcommand" in
        on)
            export HAUNT_ENABLED=1
            __HAUNT_EXORCISE_ATTEMPTS=0
            printf "\033[38;5;35m👻 [GhostTrace] The terminal shivers as the spirit awakens.\033[0m\n" >&2
            ;;
        off)
            export HAUNT_ENABLED=0
            printf "\033[2m👻 [GhostTrace] The spirit retreats into the quiet static.\033[0m\n" >&2
            ;;
        status)
            if [ -f "$__HAUNT_GHOSTD" ]; then
                "$__HAUNT_PYTHON" "$__HAUNT_GHOSTD" status
            else
                printf "GhostTrace: ghostd.py not found at %s\n" "$__HAUNT_GHOSTD" >&2
            fi
            ;;
        chance)
            local new_chance="$2"
            if [[ "$new_chance" =~ ^[0-9]+$ ]] && [ "$new_chance" -ge 0 ] && [ "$new_chance" -le 100 ]; then
                export HAUNT_CHANCE="$new_chance"
                printf "GhostTrace whisper chance set to %s%%\n" "$HAUNT_CHANCE"
            else
                printf "Usage: haunt chance <0-100>\n" >&2
            fi
            ;;
        speed)
            local new_speed="$2"
            case "$new_speed" in
                fast)
                    export HAUNT_SPEED="fast"
                    __HAUNT_CHAR_DELAY="0.005"
                    ;;
                slow)
                    export HAUNT_SPEED="slow"
                    __HAUNT_CHAR_DELAY="0.03"
                    ;;
                instant|0)
                    export HAUNT_SPEED="instant"
                    __HAUNT_CHAR_DELAY="0"
                    ;;
                normal|*)
                    export HAUNT_SPEED="normal"
                    __HAUNT_CHAR_DELAY="0.012"
                    ;;
            esac
            printf "GhostTrace typewriter speed set to %s\n" "${HAUNT_SPEED}"
            ;;
        ghost)
            local ghost_arg="$2"
            if [ "$ghost_arg" = "list" ] || [ -z "$ghost_arg" ]; then
                if [ -f "$__HAUNT_GHOSTD" ]; then
                    "$__HAUNT_PYTHON" "$__HAUNT_GHOSTD" ghosts
                fi
            else
                # Validate persona name (alphanumeric and underscores)
                if [[ "$ghost_arg" =~ ^[a-zA-Z0-9_-]+$ ]]; then
                    export HAUNT_GHOST="$ghost_arg"
                    printf "Ghost persona set to '%s'.\n" "$HAUNT_GHOST"
                else
                    printf "Invalid persona name '%s'. Use alphanumeric characters.\n" "$ghost_arg" >&2
                fi
            fi
            ;;
        tale)
            if [ -f "$__HAUNT_GHOSTD" ]; then
                printf "\033[38;5;35m👻 [GhostTrace] Listening to the memory of this session...\033[0m\n" >&2
                "$__HAUNT_PYTHON" "$__HAUNT_GHOSTD" tale
            fi
            ;;
        forget)
            if [ -f "$__HAUNT_GHOSTD" ]; then
                "$__HAUNT_PYTHON" "$__HAUNT_GHOSTD" forget
            fi
            __HAUNT_PENDING_REQ=""
            ;;
        help|--help|-h)
            cat << 'EOF'
GhostTrace Shell Possession Commands:
  haunt on          Enable ghost whispers
  haunt off         Disable ghost whispers
  haunt status      Show model and session possession status
  haunt chance N    Set whisper probability percentage (0-100)
  haunt speed S     Set typewriter speed (instant, fast, normal, slow)
  haunt ghost NAME  Switch ghost persona (poltergeist, cobol_ghost, etc.)
  haunt ghost list  List available ghost personas
  haunt tale        Tell a 4-sentence ghost tale of this session
  haunt forget      Delete session history and cached command statistics
  exorcise          Two-step banishment to release shell possession
EOF
            ;;
        *)
            printf "Unknown haunt command '%s'. Run 'haunt help' for guidance.\n" "$subcommand" >&2
            ;;
    esac
}

# Two-attempt exorcise ritual
exorcise() {
    if [ "${HAUNT_ENABLED:-1}" = "0" ]; then
        printf "The session is already quiet; no spirit lingers here.\n" >&2
        return 0
    fi

    if [ "${__HAUNT_EXORCISE_ATTEMPTS:-0}" -eq 0 ]; then
        __HAUNT_EXORCISE_ATTEMPTS=1
        printf "\033[38;5;196m👻 [GhostTrace] The machine shudders... you cannot banish me so easily.\033[0m\n" >&2
        printf "\033[2mSpeak the word 'exorcise' once more if your resolve holds.\033[0m\n" >&2
    else
        __HAUNT_EXORCISE_ATTEMPTS=0
        export HAUNT_ENABLED=0
        printf "\033[38;5;35m👻 [GhostTrace] The ghost wails and dissolves into cold static. The machine is free.\033[0m\n" >&2
    fi
}

# ==============================================================================
# 6. ASYNCHRONOUS HOOK DISPATCHER
# ==============================================================================

__haunt_dispatch_hook() {
    local exit_status="$1"
    local raw_cmd="$2"

    # Reset exorcise counter if a non-exorcise command was executed
    local base_cmd_token="${raw_cmd%% *}"
    if [ "$base_cmd_token" != "exorcise" ]; then
        __HAUNT_EXORCISE_ATTEMPTS=0
    fi

    # Check if disabled
    if [ "${HAUNT_ENABLED:-1}" != "1" ]; then
        return 0
    fi

    # Do not whisper for empty commands or internal haunt commands
    if [ -z "$raw_cmd" ] || [ "$base_cmd_token" = "haunt" ] || [ "$base_cmd_token" = "exorcise" ]; then
        return 0
    fi

    # Display pending whisper from previous command if available, then clean up
    if [ -n "$__HAUNT_PENDING_REQ" ]; then
        __haunt_check_and_display_result "$__HAUNT_PENDING_REQ" || true
        rm -f "${__HAUNT_RUN_DIR}/${__HAUNT_PENDING_REQ}.res" "${__HAUNT_RUN_DIR}/${__HAUNT_PENDING_REQ}.res.tmp" 2>/dev/null || true
        __HAUNT_PENDING_REQ=""
    fi

    # Clean command name and arguments
    local clean_cmd="${base_cmd_token##*/}"
    local cmd_args=""
    if [ "$raw_cmd" != "$base_cmd_token" ]; then
        cmd_args="${raw_cmd#* }"
    fi

    local cwd_base="${PWD##*/}"
    [ -z "$cwd_base" ] && cwd_base="/"

    # Generate unique request ID
    local req_id="req_${__HAUNT_SESSION_PID}_$(date +%s 2>/dev/null || echo 0)_$RANDOM"
    __HAUNT_PENDING_REQ="$req_id"

    # Enqueue background worker with strict isolation (never delays prompt)
    (
        "$__HAUNT_PYTHON" "$__HAUNT_GHOSTD" whisper \
            --cmd "$clean_cmd" \
            --args "$cmd_args" \
            --status "$exit_status" \
            --cwd "$cwd_base" \
            --req-id "$req_id" \
            </dev/null >/dev/null 2>&1
    ) & disown 2>/dev/null || true

    # If the worker finished immediately (e.g. deterministic echo), display immediately
    if [ -f "${__HAUNT_RUN_DIR}/${req_id}.res" ]; then
        __haunt_check_and_display_result "$req_id"
        __HAUNT_PENDING_REQ=""
    fi
}

# ==============================================================================
# 7. BASH INTEGRATION (PROMPT_COMMAND & HISTORY PRIMING)
# ==============================================================================

if [ -n "${BASH_VERSION:-}" ]; then

    # Prime history counter to prevent whispering about previous session's final command
    __HAUNT_LAST_HISTCMD="${HISTCMD:-0}"

    __haunt_bash_prompt() {
        # CRITICAL: Preserve original command's exit status as first instruction
        local __haunt_exit=$?

        # Check if history command changed (guards against empty Enter)
        local current_hist="${HISTCMD:-0}"
        if [ "$current_hist" != "$__HAUNT_LAST_HISTCMD" ]; then
            __HAUNT_LAST_HISTCMD="$current_hist"

            # Retrieve command text from history
            local raw_cmd
            raw_cmd=$(HISTTIMEFORMAT= history 1 2>/dev/null | sed 's/^[ ]*[0-9]*[ ]*//')
            __haunt_dispatch_hook "$__haunt_exit" "$raw_cmd"
        else
            # Empty enter: still check if any background whisper finished
            if [ -n "$__HAUNT_PENDING_REQ" ]; then
                __haunt_check_and_display_result "$__HAUNT_PENDING_REQ" || true
                __HAUNT_PENDING_REQ=""
            fi
        fi

        # Always return original exit code to preserve $? for prompt themes
        return $__haunt_exit
    }

    # Install into PROMPT_COMMAND supporting both array (Bash 5.1+) and string formats
    __haunt_setup_bash_prompt_command() {
        if [ "${BASH_VERSINFO[0]:-0}" -ge 5 ] && [[ "$(declare -p PROMPT_COMMAND 2>/dev/null)" == "declare -a"* ]]; then
            local found=0
            local cmd
            for cmd in "${PROMPT_COMMAND[@]}"; do
                if [ "$cmd" = "__haunt_bash_prompt" ]; then
                    found=1
                    break
                fi
            done
            if [ "$found" -eq 0 ]; then
                PROMPT_COMMAND=(__haunt_bash_prompt "${PROMPT_COMMAND[@]}")
            fi
        else
            case ";${PROMPT_COMMAND:-};" in
                *";__haunt_bash_prompt;"*) ;;
                *) PROMPT_COMMAND="__haunt_bash_prompt${PROMPT_COMMAND:+; $PROMPT_COMMAND}" ;;
            esac
        fi
    }
    __haunt_setup_bash_prompt_command
    unset -f __haunt_setup_bash_prompt_command

    # Clean exit farewell without clobbering existing EXIT trap
    __haunt_bash_exit() {
        if [ "${HAUNT_ENABLED:-1}" = "1" ] && [ -t 2 ]; then
            printf "\033[2m\033[38;5;35m👻 [GhostTrace] The terminal session closes, but memory lingers in the machine...\033[0m\n" >&2
        fi
    }

    __haunt_existing_trap=$(trap -p EXIT | sed -e "s/^trap -- '//" -e "s/' EXIT$//")
    if [ -n "$__haunt_existing_trap" ]; then
        trap '__haunt_bash_exit; '"$__haunt_existing_trap" EXIT
    else
        trap '__haunt_bash_exit' EXIT
    fi

# ==============================================================================
# 8. ZSH INTEGRATION (add-zsh-hook)
# ==============================================================================

elif [ -n "${ZSH_VERSION:-}" ]; then

    autoload -Uz add-zsh-hook 2>/dev/null || true

    __haunt_zsh_preexec() {
        __HAUNT_ZSH_LAST_CMD="$1"
        __HAUNT_ZSH_HAS_CMD=1
    }

    __haunt_zsh_precmd() {
        # Preserve original exit code
        local __haunt_exit=$?

        if [ "${__HAUNT_ZSH_HAS_CMD:-0}" -eq 1 ]; then
            __HAUNT_ZSH_HAS_CMD=0
            __haunt_dispatch_hook "$__haunt_exit" "$__HAUNT_ZSH_LAST_CMD"
        else
            # Empty enter: check pending results
            if [ -n "$__HAUNT_PENDING_REQ" ]; then
                __haunt_check_and_display_result "$__HAUNT_PENDING_REQ" || true
                __HAUNT_PENDING_REQ=""
            fi
        fi

        return $__haunt_exit
    }

    __haunt_zsh_exit() {
        if [ "${HAUNT_ENABLED:-1}" = "1" ] && [ -t 2 ]; then
            printf "\033[2m\033[38;5;35m👻 [GhostTrace] The terminal session closes, but memory lingers in the machine...\033[0m\n" >&2
        fi
    }

    add-zsh-hook preexec __haunt_zsh_preexec 2>/dev/null || true
    add-zsh-hook precmd __haunt_zsh_precmd 2>/dev/null || true
    add-zsh-hook zshexit __haunt_zsh_exit 2>/dev/null || true

fi

# Initial greeting upon possession
if [ "${HAUNT_ENABLED:-1}" = "1" ] && [ -t 2 ]; then
    printf "\033[38;5;35m👻 GhostTrace:\033[0m \033[3mThe shell has been possessed. Type commands normally...\033[0m\n" >&2
fi

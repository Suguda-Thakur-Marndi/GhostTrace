"""Haunted terminal REPL interface for GhostTrace using Rich."""

from __future__ import annotations

import os
import random
import sys
import time
from pathlib import Path
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ghosttrace.command_runner import CommandRunner
from ghosttrace.config import PERSONALITIES, STARTUP_MESSAGES, GhostConfig
from ghosttrace.ghost import GhostEngine, GhostWhisper
from ghosttrace.ollama_client import OllamaClient
from ghosttrace.safety import InputCategory, RiskLevel, SafetyEngine, SafetyReport, classify_input

ASCII_BANNER = r"""
       .-.
      (o.o)   [bold green]G H O S T T R A C E[/bold green]
       |=|    [dim]─────────────────────────────────────────────────[/dim]
      /   \   [bold green]GHOSTTRACE — THE SHELL REMEMBERS[/bold green]
     (:   :)  [dim]Local AI Engine • Privacy-First • Zero Cloud Telemetry[/dim]
      `"`"`
"""


class HauntedShell:
    """Atmospheric interactive terminal REPL hosting the ghost in the machine."""

    def __init__(self, config: Optional[GhostConfig] = None, no_color: Optional[bool] = None):
        self.config = config or GhostConfig.load()
        self.console = Console(legacy_windows=False, no_color=no_color)

        self.safety = SafetyEngine(allowed_commands=self.config.allowed_commands, safe_mode=self.config.safe_mode)
        self.client = OllamaClient(
            host=self.config.ollama_url,
            default_model=self.config.model,
            timeout=self.config.timeout_seconds,
        )
        self.ghost = GhostEngine(config=self.config, client=self.client)
        self.runner = CommandRunner(timeout=15.0)
        self.is_running = False

    def get_rotating_messages(self, count: int = 3) -> List[str]:
        """Select rotating atmospheric ghost messages for startup."""
        if len(STARTUP_MESSAGES) >= count:
            return random.sample(STARTUP_MESSAGES, count)
        return STARTUP_MESSAGES[:count]

    def print_banner(self) -> None:
        """Render the startup haunted sigil, rotating ghost messages, and environmental status."""
        self.console.print(ASCII_BANNER)

        # Rotating ghost messages
        messages = self.get_rotating_messages(3)
        for msg in messages:
            if self.config.animations_enabled:
                time.sleep(0.04)
            self.console.print(f" [dim green]•[/dim green] [italic dim]{msg}[/italic dim]")
        self.console.print()

        # Elevation warning if running as root/admin
        if self.safety.is_elevated():
            self.console.print(
                Panel(
                    "[bold red]WARNING: Running with elevated (Administrator/Root) privileges![/bold red]\n"
                    "[dim]It is strongly recommended to run GhostTrace in standard user space to minimize risk.[/dim]",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )

        # Quick startup status line - skip HTTP probe entirely if offline_only
        model_name = self.config.model
        model_warning = ""

        if self.config.offline_only:
            daemon_status = "[dim yellow]OFFLINE (Forced)[/dim yellow]"
        else:
            is_alive = self.client.is_available()
            if is_alive:
                daemon_status = "[bold green]ONLINE[/bold green]"
                try:
                    models = self.client.list_models()
                    if model_name not in models and not any(m.startswith(f"{model_name}:") or m == model_name for m in models):
                        model_warning = (
                            f" [bold yellow]Notice:[/bold yellow] Model [bold white]'{model_name}'[/bold white] is not installed locally.\n"
                            f" [dim]Run: [bold white]ollama pull {model_name}[/bold white] in another terminal. GhostTrace will use deterministic fallback.\n[/dim]"
                        )
                except Exception:
                    pass
            else:
                daemon_status = "[bold red]OFFLINE (Fallback)[/bold red]"
                model_warning = (
                    " [bold yellow]Notice:[/bold yellow] Ollama daemon is not reachable at localhost:11434.\n"
                    " [dim]Verify Ollama is running with 'ollama serve'. GhostTrace will use deterministic fallback.\n[/dim]"
                )

        persona = PERSONALITIES.get(self.config.personality, {}).get("title", self.config.personality)

        self.console.print(
            f" [dim]Neural Core:[/dim] [bold green]{model_name}[/bold green] | "
            f"[dim]Daemon:[/dim] {daemon_status} | "
            f"[dim]Spirit Persona:[/dim] [bold green]{persona}[/bold green] | "
            f"[dim]Wards:[/dim] [bold green]{'STRICT' if self.config.safe_mode else 'LENIENT'}[/bold green]"
        )
        if model_warning:
            self.console.print(model_warning)
        self.console.print(
            " [dim]Type [bold white]'help'[/bold white] for the Grimoire or [bold white]'exit'[/bold white] to unbind the spirit.\n[/dim]"
        )

    def run(self) -> None:
        """Run the main interactive REPL loop."""
        self.is_running = True
        self.print_banner()

        while self.is_running:
            try:
                # Custom ghost prompt showing current directory in restrained phosphor green and muted gray
                cwd_name = Path(os.getcwd()).name or os.getcwd()
                prompt_text = f"[bold green]ghost[/bold green][dim]@[/dim][bold green]machine[/bold green]:[dim]{cwd_name}[/dim][bold green] 👻❯[/bold green] "

                # Use console.input for rich prompt display
                user_input = self.console.input(prompt_text).strip()

                if not user_input:
                    continue

                self.handle_input(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[dim italic]^C (Interrupt) The spirit holds the line... prompt reset.[/dim italic]")
                continue
            except EOFError:
                self.console.print("\n[dim italic]The ghost retreats into the static... session terminated.[/dim italic]")
                self.is_running = False
                break
            except Exception as err:
                self.console.print(f"[bold red]Spectral fault:[/bold red] {err}")

    def handle_input(self, raw_input: str) -> None:
        """Process user input, deterministically routing between built-ins, conversation, and commands."""
        category = classify_input(raw_input)

        if category == InputCategory.BUILTIN:
            parts = raw_input.split(maxsplit=1)
            command_key = parts[0].lower()
            arg_str = parts[1] if len(parts) > 1 else ""

            if command_key in ("exit", "quit"):
                self.cmd_exit()
            elif command_key == "help":
                self.cmd_help()
            elif command_key in ("clear", "cls"):
                self.cmd_clear()
            elif command_key == "status":
                self.cmd_status()
            elif command_key == "model":
                self.cmd_model(arg_str)
            elif command_key == "personality":
                self.cmd_personality(arg_str)
            elif command_key == "explain":
                self.cmd_explain(arg_str)
        elif category == InputCategory.CONVERSATION:
            self.execute_conversation_pipeline(raw_input)
        else:
            # System command execution flow
            self.execute_command_pipeline(raw_input)

    def execute_conversation_pipeline(self, raw_input: str) -> None:
        """Process conversational input without ever invoking the OS command runner."""
        whisper = self.ghost.converse(raw_input)
        self._render_ghost_conversation(whisper)

    def cmd_exit(self) -> None:
        """Leave the haunted terminal."""
        self.console.print(
            Panel(
                "[italic green]\"You close the terminal portal, but the memory lingers in the machine's silicon... farewell.\"[/italic green]",
                title="[dim]Departing Whisper[/dim]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
        self.is_running = False

    def cmd_clear(self) -> None:
        """Clear terminal and re-render the ghostly banner."""
        self.console.clear()
        self.print_banner()

    def cmd_help(self) -> None:
        """Display the haunted terminal grimoire."""
        table = Table(title="[bold green]GHOSTTRACE — THE GRIMOIRE[/bold green]", box=box.ROUNDED)
        table.add_column("Command", style="green bold", width=22)
        table.add_column("Description", style="white")

        table.add_row("help", "Display this arcane grimoire of commands")
        table.add_row("status", "Inspect Ollama connection, neural model, wards, and environment")
        table.add_row("model [name]", "View or switch local Ollama neural model (e.g., gemma3:4b)")
        table.add_row("personality [name]", "View or switch spirit persona (ghosttrace, spectral_wraith, cyber_poltergeist, crypt_keeper)")
        table.add_row("explain <cmd>", "Analyze risk and technical purpose without executing")
        table.add_row("clear", "Cleanse the terminal altar and restore the sigil")
        table.add_row("exit / quit", "Sever the neural conduit and exit the terminal")
        table.add_row("", "")
        table.add_row("[dim]System Commands[/dim]", "[dim]ls, dir, cd, pwd, cat, type, git, python, whoami, etc.[/dim]")

        self.console.print(table)
        self.console.print(
            "[dim]Safety note: Shell chaining (&&, ;), pipes (|), redirections (>), and destructive commands (rm, del) are strictly blocked.[/dim]\n"
        )

    def cmd_status(self) -> None:
        """Inspect and report application and model status."""
        if self.config.offline_only:
            daemon_status = "[dim yellow]OFFLINE (Offline Mode)[/dim yellow]"
            models = ["[dim]Query skipped in offline mode[/dim]"]
        else:
            is_ollama_alive = self.client.is_available()
            models = []
            if is_ollama_alive:
                try:
                    models = self.client.list_models()
                except Exception:
                    models = []
            daemon_status = (
                "[bold green]ONLINE (localhost:11434)[/bold green]"
                if is_ollama_alive
                else "[bold red]OFFLINE (Using Spectral Echoes fallback)[/bold red]"
            )

        table = Table(title="[bold green]GHOSTTRACE SYSTEM SANCTUM[/bold green]", box=box.ROUNDED)
        table.add_column("Property", style="bold green", width=24)
        table.add_column("Current State", style="white")

        table.add_row("Ollama Daemon", daemon_status)
        table.add_row("Active Model", f"[bold green]{self.config.model}[/bold green]")
        table.add_row("Available Models", ", ".join(models) if models else "[dim]None discovered[/dim]")
        table.add_row("Inference Timeout", f"{self.config.timeout_seconds} seconds")
        table.add_row("Animations", "[bold green]ENABLED[/bold green]" if self.config.animations_enabled else "[dim]DISABLED[/dim]")
        table.add_row("Persona Style", self.config.personality)
        table.add_row("Safety Ward (Safe Mode)", "[bold green]ACTIVE (Strict Allowlist)[/bold green]" if self.config.safe_mode else "[bold yellow]INACTIVE[/bold yellow]")
        table.add_row("Privilege Level", "[bold red]ADMINISTRATOR / ROOT[/bold red]" if self.safety.is_elevated() else "[bold green]STANDARD USER (Safe)[/bold green]")
        table.add_row("Current Directory", os.getcwd())

        self.console.print(table)

    def cmd_model(self, model_name: str) -> None:
        """List or switch the active LLM."""
        if not model_name:
            if self.config.offline_only:
                self.console.print(f"[dim]Active model:[/dim] [bold green]{self.config.model}[/bold green] [dim](Offline mode active)[/dim]")
                return
            try:
                available = self.client.list_models()
                self.console.print(f"[dim]Active model:[/dim] [bold green]{self.config.model}[/bold green]")
                self.console.print(f"[dim]Available local models:[/dim] {', '.join(available) or 'None'}")
                self.console.print("[dim]To switch, run: model <model_name>[/dim]")
            except Exception as err:
                self.console.print(f"[red]Could not query Ollama models: {err}[/red]")
            return

        target = model_name.strip()
        self.config.model = target
        self.ghost.config.model = target
        self.client.default_model = target
        self.console.print(f"[bold green]Neural core shifted to:[/bold green] [bold green]{target}[/bold green]")

    def cmd_personality(self, persona_key: str) -> None:
        """List or switch the spirit persona."""
        if not persona_key:
            self.console.print("[bold green]Available Spirit Personas:[/bold green]")
            for key, val in PERSONALITIES.items():
                mark = " [bold green]➔ (active)[/bold green]" if key == self.config.personality else ""
                self.console.print(f"  • [bold green]{key}[/bold green]: {val['title']} — [dim]{val['description']}[/dim]{mark}")
            self.console.print("[dim]To switch, run: personality <key>[/dim]")
            return

        key = persona_key.strip().lower()
        if key in PERSONALITIES:
            self.config.personality = key
            self.ghost.config.personality = key
            self.console.print(f"[bold green]The ghost's essence transforms into:[/bold green] [bold green]{PERSONALITIES[key]['title']}[/bold green]")
        else:
            self.console.print(f"[bold red]Unknown persona '{key}'. Available: {', '.join(PERSONALITIES.keys())}[/bold red]")

    def cmd_explain(self, cmd_to_explain: str) -> None:
        """Explain a command and preview its safety without executing."""
        if not cmd_to_explain:
            self.console.print("[yellow]Usage: explain <command>[/yellow]")
            return

        report = self.safety.analyze(cmd_to_explain)
        is_blocked = report.risk_level in (RiskLevel.BLOCKED, RiskLevel.MALFORMED)
        whisper = self.ghost.whisper(cmd_to_explain, report)

        self._render_technical_analysis(report)
        self._render_ghost_whisper(whisper, is_blocked=is_blocked)

        if is_blocked:
            self.console.print(
                Panel(
                    f"[bold red]Refused by safety wards:[/bold red] {report.reason}\n"
                    f"[bold red]Execution Status:[/bold red] BLOCKED (Will never reach the operating system)\n"
                    f"[dim]The commentary above is an explanation of the submitted text only, NOT an authorization or approval.[/dim]",
                    title="[bold red]EXECUTION REFUSED BY SAFETY WARDS[/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            self.console.print("[bold red]Verdict: BLOCKED. Command was not executed.[/bold red]\n")
        else:
            self.console.print("[dim italic]Analysis complete. Command was not executed (dry-run explain mode).[/dim italic]\n")

    def execute_command_pipeline(self, raw_command: str) -> None:
        """Analyze, execute safely, and whisper eerie post-command commentary."""
        # 1. Deterministic safety analysis
        report = self.safety.analyze(raw_command)
        is_blocked = report.risk_level in (RiskLevel.BLOCKED, RiskLevel.MALFORMED)

        # 2. Render technical explanation & risk level
        self._render_technical_analysis(report)

        # 3. Handle BLOCKED or MALFORMED commands
        if is_blocked:
            whisper = self.ghost.whisper(raw_command, report)
            self._render_ghost_whisper(whisper, is_blocked=True)
            self.console.print(
                Panel(
                    f"[bold red]Refused by safety wards:[/bold red] {report.reason}\n"
                    f"[bold red]Execution Status:[/bold red] BLOCKED (Suppressed before reaching OS)\n"
                    f"[dim]The commentary above is an explanation of the submitted text only, NOT an authorization or approval.[/dim]",
                    title="[bold red]EXECUTION REFUSED BY SAFETY WARDS[/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            return

        # 4. Handle SENSITIVE commands requiring explicit user confirmation
        if report.requires_confirmation and self.config.require_confirmation:
            confirm = self.console.input(
                f"[bold yellow]⚠️  Sensitive operation detected ({report.reason})[/bold yellow]\n"
                f"[bold white]Grant permission to execute? [y/N]: [/bold white]"
            ).strip().lower()

            if confirm not in ("y", "yes"):
                self.console.print("[dim italic]Execution aborted by user. The ghost smiles from the shadows.[/dim italic]\n")
                return

        # 5. Execute through CommandRunner with shell=False
        result = self.runner.execute(report)

        # 6. Render command output and exit status
        self._render_execution_result(result)

        # 7. Generate and render automatic post-command eerie AI commentary
        whisper = self.ghost.whisper(raw_command, report, result=result)
        self._render_ghost_whisper(whisper, is_blocked=False)

    def _render_ghost_conversation(self, whisper: GhostWhisper) -> None:
        """Render conversational ghost response with distinct GHOST CONVERSATION heading."""
        source_badge = (
            f"[bold green]Ollama ({whisper.model})[/bold green]"
            if whisper.source == "ollama"
            else "[dim yellow]Spectral Echo (Offline/Fallback)[/dim yellow]"
        )
        latency = f"[dim]{whisper.latency_ms:.0f}ms[/dim]"
        notice = f"\n[dim red]Notice: {whisper.error_notice}[/dim red]" if whisper.error_notice else ""

        reply_text = whisper.commentary or whisper.text
        content = f"[italic green]\"{reply_text}\"[/italic green]{notice}"

        self.console.print(
            Panel(
                content,
                title=f"[bold green]👻 GHOST CONVERSATION[/bold green] [dim]•[/dim] {source_badge} [dim]•[/dim] {latency}",
                border_style="green",
                box=box.ROUNDED,
            )
        )

    def _render_technical_analysis(self, report: SafetyReport) -> None:
        """Render technical explanation and risk classification panel with distinct visual styles."""
        risk_styles = {
            RiskLevel.SAFE: ("green", "SAFE", "[dim]Standard safe execution approved.[/dim]"),
            RiskLevel.SENSITIVE: ("yellow", "CAUTION / SENSITIVE", "[bold yellow]Action modifies state or executes custom code.[/bold yellow]"),
            RiskLevel.BLOCKED: ("red", "BLOCKED", "[bold red]Prohibited by safety wards.[/bold red]"),
            RiskLevel.MALFORMED: ("red", "MALFORMED", "[bold red]Invalid or malformed command syntax.[/bold red]"),
        }
        color, badge, status_note = risk_styles.get(
            report.risk_level, ("white", report.risk_level.value, "")
        )

        body = (
            f"[bold {color}]Risk Level: {badge}[/bold {color}]  [dim]•[/dim]  {status_note}\n"
            f"[dim]Evaluation:[/dim] {report.reason}\n"
            f"[bold white]Technical Action:[/bold white] {report.explanation}"
        )
        self.console.print(
            Panel(
                body,
                title=f"[bold]TECHNICAL COMMAND ANALYSIS[/bold] [dim]•[/dim] [{color}]{badge}[/{color}]",
                border_style=color,
                box=box.ROUNDED,
            )
        )

    def _render_ghost_whisper(self, whisper: GhostWhisper, is_blocked: bool = False) -> None:
        """Render spectral commentary panel with restrained phosphor-green and muted gray styling."""
        source_badge = (
            f"[bold green]Ollama ({whisper.model})[/bold green]"
            if whisper.source == "ollama"
            else "[dim yellow]Spectral Echo (Offline/Fallback)[/dim yellow]"
        )
        latency = f"[dim]{whisper.latency_ms:.0f}ms[/dim]"

        notice = f"\n[dim red]Notice: {whisper.error_notice}[/dim red]" if whisper.error_notice else ""

        if is_blocked:
            panel_title = f"[bold red]👻 GhostTrace • Passive Text Explanation (Not Executed)[/bold red] [dim]•[/dim] {source_badge} [dim]•[/dim] {latency}"
            border_style = "red"
        else:
            panel_title = f"[bold green]👻 GhostTrace[/bold green] [dim]•[/dim] {source_badge} [dim]•[/dim] {latency}"
            border_style = "green"

        if whisper.commentary and whisper.explanation:
            body_parts = [
                f"[bold green]Ghost Commentary:[/bold green] [italic]\"{whisper.commentary}\"[/italic]",
                f"[dim]Technical Explanation (Passive Text Analysis):[/dim] {whisper.explanation}",
            ]
            if is_blocked:
                body_parts.append(
                    "[bold red]⚠️  Security Notice:[/bold red] [red]Commentary explains submitted text only. Command is blocked and cannot execute.[/red]"
                )
            elif whisper.risk_warning and whisper.risk_warning.lower() != "none":
                body_parts.append(f"[bold red]Risk Warning:[/bold red] {whisper.risk_warning}")
            content = "\n".join(body_parts) + notice
        else:
            content = f"[italic green]\"{whisper.text}\"[/italic green]{notice}"
            if is_blocked:
                content += "\n[bold red]⚠️  Security Notice: Commentary explains submitted text only. Command is blocked and cannot execute.[/bold red]"

        self.console.print(
            Panel(
                content,
                title=panel_title,
                border_style=border_style,
                box=box.ROUNDED,
            )
        )

    def _render_execution_result(self, result: CommandRunner.ExecutionResult) -> None:
        """Render command execution outcome."""
        if result.stdout:
            self.console.print(
                Panel(
                    result.stdout.rstrip(),
                    title=f"[dim green]Output[/dim green] [dim]({result.duration_ms:.1f}ms)[/dim]",
                    border_style="dim green",
                    box=box.ROUNDED,
                )
            )

        if result.stderr:
            border = "yellow" if result.returncode == 0 else "red"
            self.console.print(
                Panel(
                    result.stderr.rstrip(),
                    title=f"[bold {border}]Standard Error (code {result.returncode})[/bold {border}]",
                    border_style=border,
                    box=box.ROUNDED,
                )
            )

        if not result.stdout and not result.stderr and result.returncode == 0:
            self.console.print("[dim italic]Command executed silently with return code 0.[/dim italic]")
        self.console.print()

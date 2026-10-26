"""Haunted terminal REPL interface for GhostTrace AI using Rich."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ghosttrace.command_runner import CommandRunner
from ghosttrace.config import PERSONALITIES, GhostConfig
from ghosttrace.ghost import GhostEngine
from ghosttrace.ollama_client import OllamaClient
from ghosttrace.safety import RiskLevel, SafetyEngine

ASCII_BANNER = r"""
       .-.
      (o.o)   [bold magenta]G H O S T T R A C E   A I[/bold magenta]
       |=|    [dim cyan]─────────────────────────────────────────────────[/dim cyan]
      /   \   [italic green]"The Shell Remembers. Every keystroke leaves an echo."[/italic green]
     (:   :)  [dim]Local AI Engine • Privacy-First • Zero Cloud Telemetry[/dim]
      `"`"`
"""


class HauntedShell:
    """Atmospheric interactive terminal REPL hosting the ghost in the machine."""

    def __init__(self, config: Optional[GhostConfig] = None):
        self.config = config or GhostConfig.load()
        self.console = Console(legacy_windows=False)

        self.safety = SafetyEngine(allowed_commands=self.config.allowed_commands, safe_mode=self.config.safe_mode)
        self.client = OllamaClient(
            host=self.config.ollama_url,
            default_model=self.config.model,
            timeout=self.config.timeout_seconds,
        )
        self.ghost = GhostEngine(config=self.config, client=self.client)
        self.runner = CommandRunner(timeout=15.0)
        self.is_running = False

    def print_banner(self) -> None:
        """Render the startup haunted sigil and environmental status."""
        self.console.print(ASCII_BANNER)

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

        # Quick startup status line
        model_name = self.config.model
        persona = PERSONALITIES.get(self.config.personality, {}).get("title", self.config.personality)
        self.console.print(
            f" [dim]Spirit Guide:[/dim] [bold magenta]{persona}[/bold magenta] | "
            f"[dim]Neural Core:[/dim] [bold cyan]{model_name}[/bold cyan] | "
            f"[dim]Wards:[/dim] [bold green]{'STRICT' if self.config.safe_mode else 'LENIENT'}[/bold green]"
        )
        self.console.print(" [dim]Type [bold white]'help'[/bold white] for the Grimoire or [bold white]'exit'[/bold white] to unbind the spirit.\n[/dim]")

    def run(self) -> None:
        """Run the main interactive REPL loop."""
        self.is_running = True
        self.print_banner()

        while self.is_running:
            try:
                # Custom ghost prompt showing current directory
                cwd_name = Path(os.getcwd()).name or os.getcwd()
                prompt_text = f"[bold green]ghost[/bold green][dim]@[/dim][bold cyan]machine[/bold cyan]:[bold magenta]{cwd_name}[/bold magenta][dim] 👻❯[/dim] "
                
                # Use console.input for rich prompt display
                user_input = self.console.input(prompt_text).strip()

                if not user_input:
                    continue

                self.handle_input(user_input)

            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[dim italic]The ghost retreats into the static... session terminated.[/dim italic]")
                self.is_running = False
                break
            except Exception as err:
                self.console.print(f"[bold red]Spectral fault:[/bold red] {err}")

    def handle_input(self, raw_input: str) -> None:
        """Process user input, routing between built-in shell commands and system commands."""
        parts = raw_input.split(maxsplit=1)
        command_key = parts[0].lower()
        arg_str = parts[1] if len(parts) > 1 else ""

        # Internal shell commands
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
        else:
            # System command execution flow
            self.execute_command_pipeline(raw_input)

    def cmd_exit(self) -> None:
        """Leave the haunted terminal."""
        self.console.print(
            Panel(
                "[italic magenta]\"You close the terminal portal, but the memory lingers in the machine's silicon... farewell.\"[/italic magenta]",
                title="[dim]Departing Whisper[/dim]",
                border_style="magenta",
                box=box.ROUNDED,
            )
        )
        self.is_running = False

    def cmd_clear(self) -> None:
        """Clear terminal and re-render the ghostly banner."""
        os.system("cls" if os.name == "nt" else "clear")
        self.print_banner()

    def cmd_help(self) -> None:
        """Display the haunted terminal grimoire."""
        table = Table(title="[bold magenta]GHOSTTRACE AI — THE GRIMOIRE[/bold magenta]", box=box.ROUNDED)
        table.add_column("Command", style="cyan bold", width=20)
        table.add_column("Description", style="white")

        table.add_row("help", "Display this arcane grimoire of commands")
        table.add_row("status", "Inspect Ollama connection, neural model, wards, and environment")
        table.add_row("model [name]", "View or switch local Ollama neural model (e.g., qwen2.5:1.5b)")
        table.add_row("personality [name]", "View or switch spirit persona (spectral_wraith, cyber_poltergeist, crypt_keeper)")
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
        is_ollama_alive = self.client.is_available()
        models = []
        if is_ollama_alive:
            try:
                models = self.client.list_models()
            except Exception:
                models = []

        table = Table(title="[bold cyan]GHOSTTRACE SYSTEM SANCTUM[/bold cyan]", box=box.ROUNDED)
        table.add_column("Property", style="bold green", width=24)
        table.add_column("Current State", style="white")

        table.add_row(
            "Ollama Daemon",
            "[bold green]ONLINE (localhost:11434)[/bold green]"
            if is_ollama_alive
            else "[bold red]OFFLINE (Using Spectral Echoes fallback)[/bold red]",
        )
        table.add_row("Active Model", f"[bold cyan]{self.config.model}[/bold cyan]")
        table.add_row("Available Models", ", ".join(models) if models else "[dim]None discovered[/dim]")
        table.add_row("Inference Timeout", f"{self.config.timeout_seconds} seconds")
        table.add_row("Persona Style", self.config.personality)
        table.add_row("Safety Ward (Safe Mode)", "[bold green]ACTIVE (Strict Allowlist)[/bold green]" if self.config.safe_mode else "[bold yellow]INACTIVE[/bold yellow]")
        table.add_row("Privilege Level", "[bold red]ADMINISTRATOR / ROOT[/bold red]" if self.safety.is_elevated() else "[bold green]STANDARD USER (Safe)[/bold green]")
        table.add_row("Current Directory", os.getcwd())

        self.console.print(table)

    def cmd_model(self, model_name: str) -> None:
        """List or switch the active LLM."""
        if not model_name:
            # List models
            try:
                available = self.client.list_models()
                self.console.print(f"[dim]Active model:[/dim] [bold cyan]{self.config.model}[/bold cyan]")
                self.console.print(f"[dim]Available local models:[/dim] {', '.join(available) or 'None'}")
                self.console.print("[dim]To switch, run: model <model_name>[/dim]")
            except Exception as err:
                self.console.print(f"[red]Could not query Ollama models: {err}[/red]")
            return

        target = model_name.strip()
        self.config.model = target
        self.ghost.config.model = target
        self.client.default_model = target
        self.console.print(f"[bold green]Neural core shifted to:[/bold green] [bold cyan]{target}[/bold cyan]")

    def cmd_personality(self, persona_key: str) -> None:
        """List or switch the spirit persona."""
        if not persona_key:
            self.console.print("[bold magenta]Available Spirit Personas:[/bold magenta]")
            for key, val in PERSONALITIES.items():
                mark = " [bold green]➔ (active)[/bold green]" if key == self.config.personality else ""
                self.console.print(f"  • [bold cyan]{key}[/bold cyan]: {val['title']} — [dim]{val['description']}[/dim]{mark}")
            self.console.print("[dim]To switch, run: personality <key>[/dim]")
            return

        key = persona_key.strip().lower()
        if key in PERSONALITIES:
            self.config.personality = key
            self.ghost.config.personality = key
            self.console.print(f"[bold green]The ghost's essence transforms into:[/bold green] [bold magenta]{PERSONALITIES[key]['title']}[/bold magenta]")
        else:
            self.console.print(f"[bold red]Unknown persona '{key}'. Available: {', '.join(PERSONALITIES.keys())}[/bold red]")

    def cmd_explain(self, cmd_to_explain: str) -> None:
        """Explain a command and preview its safety without executing."""
        if not cmd_to_explain:
            self.console.print("[yellow]Usage: explain <command>[/yellow]")
            return

        report = self.safety.analyze(cmd_to_explain)
        whisper = self.ghost.whisper(cmd_to_explain, report)

        self._render_technical_analysis(report)
        self._render_ghost_whisper(whisper)
        self.console.print("[dim italic]Analysis complete. Command was not executed.[/dim italic]\n")

    def execute_command_pipeline(self, raw_command: str) -> None:
        """Analyze, whisper, verify confirmation, and execute the command safely."""
        # 1. Deterministic safety analysis
        report = self.safety.analyze(raw_command)

        # 2. Render technical explanation & risk level
        self._render_technical_analysis(report)

        # 3. Generate and render the Ghost AI commentary
        whisper = self.ghost.whisper(raw_command, report)
        self._render_ghost_whisper(whisper)

        # 4. Handle BLOCKED or MALFORMED commands
        if report.risk_level in (RiskLevel.BLOCKED, RiskLevel.MALFORMED):
            self.console.print(
                Panel(
                    f"[bold red]EXECUTION REFUSED BY SAFETY WARDS[/bold red]\n"
                    f"[white]{report.reason}[/white]\n"
                    f"[dim]Command was suppressed before it could reach the system.[/dim]",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            return

        # 5. Handle SENSITIVE commands requiring explicit user confirmation
        if report.requires_confirmation and self.config.require_confirmation:
            confirm = self.console.input(
                f"[bold yellow]⚠️  Sensitive operation detected ({report.reason})[/bold yellow]\n"
                f"[bold white]Grant permission to execute? [y/N]: [/bold white]"
            ).strip().lower()

            if confirm not in ("y", "yes"):
                self.console.print("[dim italic]Execution aborted by user. The ghost smiles from the shadows.[/dim italic]\n")
                return

        # 6. Execute through CommandRunner with shell=False
        result = self.runner.execute(report)

        # 7. Render output
        self._render_execution_result(result)

    def _render_technical_analysis(self, report: SafetyReport) -> None:
        """Render technical explanation and risk classification panel."""
        risk_colors = {
            RiskLevel.SAFE: "green",
            RiskLevel.SENSITIVE: "yellow",
            RiskLevel.BLOCKED: "red",
            RiskLevel.MALFORMED: "dark_orange",
        }
        color = risk_colors.get(report.risk_level, "white")

        body = (
            f"[bold {color}]Risk Level: {report.risk_level.value}[/bold {color}]  [dim]•[/dim]  "
            f"[dim]Evaluation:[/dim] {report.reason}\n"
            f"[bold white]Action:[/bold white] {report.explanation}"
        )
        self.console.print(
            Panel(
                body,
                title="[dim cyan]Technical Command Analysis[/dim cyan]",
                border_style=color,
                box=box.ROUNDED,
            )
        )

    def _render_ghost_whisper(self, whisper: GhostWhisper) -> None:
        """Render spectral commentary panel."""
        source_badge = (
            f"[bold cyan]Ollama ({whisper.model})[/bold cyan]"
            if whisper.source == "ollama"
            else "[dim yellow]Spectral Echo (Offline/Fallback)[/dim yellow]"
        )
        latency = f"[dim]{whisper.latency_ms:.0f}ms[/dim]"

        notice = f"\n[dim red]Notice: {whisper.error_notice}[/dim red]" if whisper.error_notice else ""
        content = f"[italic magenta]\"{whisper.text}\"[/italic magenta]{notice}"

        self.console.print(
            Panel(
                content,
                title=f"[bold green]👻 Ghost Whisper[/bold green] [dim]•[/dim] {source_badge} [dim]•[/dim] {latency}",
                border_style="magenta",
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

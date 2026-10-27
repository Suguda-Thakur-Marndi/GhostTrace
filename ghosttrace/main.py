"""Entry point for GhostTrace haunted terminal."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from rich.console import Console

from ghosttrace import __version__
from ghosttrace.config import PERSONALITIES, GhostConfig
from ghosttrace.ghost import GhostEngine
from ghosttrace.ollama_client import OllamaClient
from ghosttrace.safety import SafetyEngine
from ghosttrace.shell import HauntedShell


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="ghosttrace",
        description="GhostTrace - Spooky, privacy-first haunted terminal with local AI commentary.",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Local Ollama model name (e.g., qwen2.5:1.5b, gemma3:4b).",
    )
    parser.add_argument(
        "--personality",
        "-p",
        choices=list(PERSONALITIES.keys()),
        default=None,
        help="Ghost commentary personality.",
    )
    parser.add_argument(
        "--offline",
        "--no-ai",
        action="store_true",
        dest="offline",
        help="Run in offline deterministic mode (uses Spectral Echoes fallback, bypasses Ollama).",
    )
    parser.add_argument(
        "--no-animation",
        action="store_true",
        help="Disable startup delays and animations for accessibility and automated testing.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color output (also respects NO_COLOR environment variable).",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Ollama daemon URL (default: http://localhost:11434).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Model inference timeout in seconds (default: 15.0).",
    )
    parser.add_argument(
        "--check-health",
        action="store_true",
        help="Perform non-interactive environment and model diagnostics.",
    )
    parser.add_argument(
        "--explain",
        type=str,
        default=None,
        help="Perform non-interactive safety analysis and spectral commentary on a command without execution.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"GhostTrace v{__version__}",
    )
    return parser.parse_args(args)



def run_health_check(config: GhostConfig, no_color: Optional[bool] = None) -> int:
    """Perform non-interactive diagnostic inspection."""
    console = Console(legacy_windows=False, no_color=no_color)

    console.print(f"[bold magenta]GhostTrace v{__version__} — Diagnostics[/bold magenta]")

    client = OllamaClient(host=config.ollama_url, timeout=3.0)
    is_alive = client.is_available()

    if is_alive:
        console.print(f" [bold green]✓[/bold green] Ollama daemon reachable at {config.ollama_url}")
        try:
            models = client.list_models()
            console.print(f" [bold green]✓[/bold green] Found {len(models)} local model(s): {', '.join(models)}")
            if config.model in models or any(m.startswith(f"{config.model}:") for m in models):
                console.print(f" [bold green]✓[/bold green] Target model '{config.model}' is installed.")
            else:
                console.print(f" [bold yellow]![/bold yellow] Target model '{config.model}' is not in local library. Run: ollama pull {config.model}")
        except Exception as e:
            console.print(f" [bold yellow]![/bold yellow] Failed to list models: {e}")
    else:
        console.print(f" [bold red]✗[/bold red] Ollama daemon NOT reachable at {config.ollama_url}.")
        console.print("   [dim]GhostTrace will use deterministic Spectral Echoes fallback.[/dim]")

    safety = SafetyEngine()
    if safety.is_elevated():
        console.print(" [bold red]![/bold red] Process is running with elevated privileges (Admin/Root).")
    else:
        console.print(" [bold green]✓[/bold green] Running as standard user.")

    return 0 if is_alive else 1


def run_one_shot_explain(cmd: str, config: GhostConfig, no_color: Optional[bool] = None) -> int:
    """Run non-interactive command analysis."""
    shell = HauntedShell(config, no_color=no_color)
    shell.cmd_explain(cmd)
    return 0


def main(args: Optional[list[str]] = None) -> int:
    """Application main entry point."""
    parsed = parse_args(args)
    config = GhostConfig.load()

    if parsed.model:
        config.model = parsed.model
    if parsed.personality:
        config.personality = parsed.personality
    if parsed.offline:
        config.offline_only = True
    if parsed.no_animation:
        config.animations_enabled = False
    if parsed.host:
        config.ollama_url = parsed.host
    if parsed.timeout:
        config.timeout_seconds = parsed.timeout

    no_color = True if parsed.no_color else None

    if parsed.check_health:
        return run_health_check(config, no_color=no_color)

    if parsed.explain:
        return run_one_shot_explain(parsed.explain, config, no_color=no_color)

    # Launch interactive haunted shell
    shell = HauntedShell(config, no_color=no_color)
    shell.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

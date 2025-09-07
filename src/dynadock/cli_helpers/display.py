#!/usr/bin/env python3
"""
Display helper functions for DynaDock CLI
"""

from typing import Dict, Any, Tuple, List
from rich.console import Console
from rich.table import Table

console = Console()


def display_running_services(
    allocated_ports: Dict[str, int],
    domain: str,
    enable_tls: bool,
    status_by_service: List[Any] | Dict[str, Tuple[str, str]] | None = None,
) -> None:
    """Pretty-print a table with service → port/url mapping."""
    status_map: Dict[str, Tuple[str, str]] = {}
    if status_by_service is not None:
        if isinstance(status_by_service, list):
            for container in status_by_service:
                service_lbl = container.labels.get("com.docker.compose.service", "unknown")
                health = container.attrs.get("State", {}).get("Health", {}).get("Status", "-")
                status_map[service_lbl] = (container.status, health)
        else:
            status_map = status_by_service

    table = Table(title="Running Services", header_style="bold magenta")
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Port", style="green", justify="right")
    table.add_column("URL", style="yellow")
    
    show_status = bool(status_map)
    if show_status:
        table.add_column("Status", style="blue")
        table.add_column("Health", style="magenta")

    for service, port in allocated_ports.items():
        url = f"{'https' if enable_tls else 'http'}://{service}.{domain}"
        row = [service, str(port), url]
        
        if show_status:
            status, health = status_map.get(service, ("-", "-"))
            row.extend([status, health])
            
        table.add_row(*row)

    console.print(table)


def display_startup_progress(message: str):
    """Display startup progress message"""
    console.print(f"[blue]{message}[/blue]")


def display_success(message: str):
    """Display success message"""
    console.print(f"[green]✅ {message}[/green]")


def display_warning(message: str):
    """Display warning message"""
    console.print(f"[yellow]⚠️  {message}[/yellow]")


def display_error(message: str):
    """Display error message"""
    console.print(f"[red]❌ {message}[/red]")


def display_info(message: str):
    """Display info message"""
    console.print(f"[blue]ℹ️  {message}[/blue]")

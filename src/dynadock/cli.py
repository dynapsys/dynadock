"""Dynadock command-line interface.

This module wires together the core helpers of the *dynadock* package and
exposes them through a user-friendly CLI implemented with *click*.

The heavy lifting (port allocation, env generation, docker orchestration,
Caddy reverse-proxy setup, …) is delegated to helper classes in the package.
This file must therefore stay relatively small and orchestration-oriented.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Tuple, List, Dict, Any

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .docker_manager import DockerManager
from .env_generator import EnvGenerator
from .caddy_config import CaddyConfig
from .utils import find_compose_file

__all__ = ["cli"]

console = Console()

###############################################################################
# Root command-group
###############################################################################


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--compose-file",
    "-f",
    type=click.Path(file_okay=True, dir_okay=False, exists=False, readable=True),
    default=None,
    help="Path to the docker-compose YAML file. If omitted the first compose "
    "file found in the current working directory or its parents is used.",
)
@click.option(
    "--env-file",
    "-e",
    type=click.Path(file_okay=True, dir_okay=False),
    default=".env.dynadock",
    help="Path where the generated environment file should be written.",
)
@click.pass_context
def cli(ctx: click.Context, compose_file: str | None, env_file: str) -> None:
    """DynaDock – Dynamic docker-compose orchestrator with TLS & Caddy love."""

    ctx.ensure_object(dict)

    # Resolve compose file lazily
    if compose_file is None:
        compose_file = find_compose_file()
        if compose_file is None:
            console.print("[red]Error: could not locate a docker-compose YAML file.[/red]")
            sys.exit(1)

    compose_path = Path(compose_file).resolve()
    ctx.obj["compose_file"] = str(compose_path)
    ctx.obj["env_file"] = env_file
    ctx.obj["project_dir"] = compose_path.parent


###############################################################################
# Helper
###############################################################################


def _display_running_services(
    allocated_ports: Dict[str, int],
    domain: str,
    enable_tls: bool,
    status_by_service: List[Any] | Dict[str, Tuple[str, str]] | None = None,
) -> None:
    """Pretty-print a table with service → port/url mapping.
    
    Args:
        allocated_ports: Mapping of service names to their allocated ports
        domain: Base domain for service URLs
        enable_tls: Whether HTTPS should be used for URLs
        status_by_service: Either a list of container objects or a dict mapping service names to (status, health) tuples
    """
    # Convert container list to status map if needed
    status_map: Dict[str, Tuple[str, str]] = {}
    if status_by_service is not None:
        if isinstance(status_by_service, list):
            # Convert list of containers to service → (status, health) mapping
            for container in status_by_service:
                service_lbl = container.labels.get("com.docker.compose.service", "unknown")
                health = container.attrs.get("State", {}).get("Health", {}).get("Status", "-")
                status_map[service_lbl] = (container.status, health)
        else:
            # Already in the correct format
            status_map = status_by_service

    table = Table(title="Running Services", header_style="bold magenta")
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Port", style="green", justify="right")
    table.add_column("URL", style="yellow")
    
    # Only add status/health columns if we have status info
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


###############################################################################
# Up command
###############################################################################


@cli.command()
@click.option("--domain", "-d", default="local.dev", help="Base domain for sub-domains.")
@click.option("--reload", is_flag=True, help="Reload configuration and restart if already running.")
@click.option("--start-port", "-p", default=8000, type=int, help="Starting port for allocation")
@click.option("--enable-tls", is_flag=True, help="Enable TLS with an internal CA via Caddy")
@click.option(
    "--cors-origins",
    "-c",
    multiple=True,
    help="Additional CORS allowed origins (can be passed multiple times).",
)
@click.option("--detach", is_flag=True, help="Run in background without following logs")
@click.pass_context
def up(  # noqa: D401
    ctx: click.Context,
    domain: str,
    start_port: int,
    enable_tls: bool,
    cors_origins: Tuple[str, ...],
    detach: bool,
    reload: bool,
) -> None:
    """Start services with dynamic port allocation and routing."""

    compose_file: str = ctx.obj["compose_file"]
    env_file: str = ctx.obj["env_file"]
    project_dir: Path = ctx.obj["project_dir"]

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Initializing…", total=6)

        docker_manager = DockerManager(compose_file, project_dir, env_file)
        env_generator = EnvGenerator(env_file)
        caddy_config = CaddyConfig(project_dir)
        progress.update(task, advance=1, description="Parsing docker-compose file…")

        services = docker_manager.parse_compose()
        allocated_ports = docker_manager.allocate_ports(services, start_port)
        progress.update(task, advance=1, description="Generating environment variables…")

        env_vars = env_generator.generate(
            services=services,
            ports=allocated_ports,
            domain=domain,
            enable_tls=enable_tls,
            cors_origins=list(cors_origins),
        )
        progress.update(task, advance=1, description="Rendering minimal Caddy configuration…")
        caddy_config.generate_minimal()
        progress.update(task, advance=1, description="Starting Caddy reverse-proxy…")
        caddy_config.start_caddy()
        progress.update(task, advance=1, description="Starting application containers…")

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Starting application containers...", total=1)
        try:
            docker_manager.up(env_vars, detach=True)
            progress.update(task, advance=1)
        except RuntimeError as e:
            console.print(f"[red]Error: {e}[/red]")
            caddy_config.stop_caddy()
            raise click.Abort()

    console.print("\n[bold green]✓ All services started![/bold green]\n")

    # Generate the full Caddy config and reload Caddy
    console.print("[dim]Configuring reverse-proxy...[/dim]")
    caddy_config.generate(services, allocated_ports, domain, enable_tls, list(cors_origins))
    caddy_config.reload_caddy()
    
    # Show service status and URLs
    status_by_service = docker_manager.ps()
    _display_running_services(allocated_ports, domain, enable_tls, status_by_service)
    
    if not detach:
        console.print("\n[dim]Press Ctrl+C to stop all services...[/dim]")
        try:
            # If not detaching, tail the logs
            docker_manager.logs()
        except KeyboardInterrupt:
            console.print("\n[dim]Stopping services...[/dim]")
            docker_manager.down()
            console.print("\n[green]✓ All services stopped.[/green]")


###############################################################################
# Down command
###############################################################################


@cli.command()
@click.option("--remove-volumes", "-v", is_flag=True, help="Remove docker volumes as well.")
@click.option("--remove-images", is_flag=True, help="Remove images (docker-compose --rmi all)")
@click.option("--prune", is_flag=True, help="Shortcut for --remove-volumes --remove-images")
@click.pass_context
def down(ctx: click.Context, remove_volumes: bool, remove_images: bool, prune: bool) -> None:
    """Stop and remove all services including the reverse-proxy."""

    compose_file: str = ctx.obj["compose_file"]
    project_dir: Path = ctx.obj["project_dir"]
    env_file: str = ctx.obj["env_file"]

    docker_manager = DockerManager(compose_file, project_dir, env_file)
    caddy_config = CaddyConfig(project_dir)

    if prune:
        remove_volumes = True
        remove_images = True

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Stopping services…", total=3)
        progress.update(task, advance=1, description="Stopping application containers…")
        docker_manager.down(remove_volumes=remove_volumes, remove_images=remove_images)
        progress.update(task, advance=1, description="Stopping Caddy reverse-proxy…")
        caddy_config.stop_caddy()
        progress.update(task, advance=1, description="✓ Cleanup complete!")

    console.print("[green]All services have been stopped and removed.[/green]")


###############################################################################
# Misc helper commands
###############################################################################


@cli.command(name="status")
@click.pass_context
def status(ctx: click.Context) -> None:  # noqa: D401
    """Alias for ps command."""
    ctx.invoke(ps)


@cli.command()
@click.pass_context
def ps(ctx: click.Context) -> None:  # noqa: D401
    """Show status of running services."""

    compose_file: str = ctx.obj["compose_file"]
    project_dir: Path = ctx.obj["project_dir"]
    env_file: str = ctx.obj["env_file"]

    docker_manager = DockerManager(compose_file, project_dir, env_file)
    containers = docker_manager.ps()

    if not containers:
        console.print("[yellow]No services are currently running.[/yellow]")
        return

    # Map service → (status, health)
    status_map: Dict[str, Tuple[str, str]] = {}
    for container in containers:
        service_lbl = container.labels.get("com.docker.compose.service", "unknown")
        health = container.attrs.get("State", {}).get("Health", {}).get("Status", "-")
        status_map[service_lbl] = (container.status, health)

    # Load previously generated env vars to obtain port mapping
    from dotenv import dotenv_values

    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    ports: Dict[str, int] = {}
    for key, val in env_values.items():
        if key.endswith("_PORT"):
            ports[key[:-5].lower()] = int(val)  # strip _PORT suffix

    _display_running_services(ports, env_values.get("DYNADOCK_DOMAIN", "local.dev"), env_values.get("DYNADOCK_ENABLE_TLS", "false") == "true", status_map)


@cli.command()
@click.pass_context
def logs(ctx: click.Context) -> None:  # noqa: D401
    """Tail logs from all services (docker-compose logs -f)."""

    compose_file = ctx.obj["compose_file"]
    project_dir = ctx.obj["project_dir"]
    docker_manager = DockerManager(compose_file, project_dir)
    docker_manager.logs()


@cli.command(name="exec")
@click.option("--service", "-s", required=True, help="Service name (as in compose file)")
@click.option("--command", "-c", default="/bin/sh", help="Command to run inside the container")
@click.pass_context
def _exec(ctx: click.Context, service: str, command: str) -> None:  # noqa: D401
    """Execute COMMAND in a running container."""

    compose_file = ctx.obj["compose_file"]
    project_dir = ctx.obj["project_dir"]
    docker_manager = DockerManager(compose_file, project_dir)
    docker_manager.exec(service, command)

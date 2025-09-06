from __future__ import annotations

import sys
import subprocess
import time
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
    if compose_file is None:
        compose_file = find_compose_file()
        if compose_file is None:
            console.print("[red]Error: could not locate a docker-compose YAML file.[/red]")
            sys.exit(1)

    compose_path = Path(compose_file).resolve()
    ctx.obj["compose_file"] = str(compose_path)
    ctx.obj["env_file"] = env_file
    ctx.obj["project_dir"] = compose_path.parent

def verify_domain_access(allocated_ports: Dict[str, int], domain: str, enable_tls: bool) -> None:
    """Verify that services are accessible via their configured domains."""
    protocol = "https" if enable_tls else "http"
    
    # Check if /etc/hosts has entries for the domains
    hosts_configured = False
    try:
        with open("/etc/hosts", "r") as f:
            hosts_content = f.read()
            if domain in hosts_content:
                hosts_configured = True
    except:
        pass
    
    if not hosts_configured:
        console.print(f"[yellow]⚠ Warning: No entries found for *.{domain} in /etc/hosts[/yellow]")
        console.print(f"[yellow]  You need to add these entries to /etc/hosts to access services by domain:[/yellow]\n")
    
    # Test each service
    all_accessible = True
    for service, port in allocated_ports.items():
        service_domain = f"{service}.{domain}"
        
        # Test localhost access (should always work)
        localhost_url = f"http://localhost:{port}"
        localhost_ok = test_url_with_curl(localhost_url, service, "localhost")
        
        # Test domain access
        domain_url = f"{protocol}://{service_domain}"
        domain_ok = test_url_with_curl(domain_url, service, "domain")
        
        if not domain_ok:
            all_accessible = False
            if not hosts_configured:
                console.print(f"[dim]  127.0.0.1 {service_domain}[/dim]")
    
    if not hosts_configured and not all_accessible:
        console.print("\n[yellow]After adding these entries, services will be accessible via their domains.[/yellow]")
        console.print("[dim]You can also access services directly via localhost:[port][/dim]\n")

def test_url_with_curl(url: str, service: str, access_type: str) -> bool:
    """Test if a URL is accessible using curl."""
    try:
        # Wait a bit for services to be ready
        if access_type == "localhost":
            time.sleep(1)
        
        # Use curl with timeout and ignore SSL certificate errors for self-signed certs
        cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-k", "--connect-timeout", "3", "-m", "5", url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
        
        if result.returncode == 0:
            http_code = result.stdout.strip()
            if http_code and http_code != "000" and int(http_code) < 500:
                if access_type == "localhost":
                    console.print(f"  [green]✓[/green] {service}: [green]localhost:{url.split(':')[-1]} is accessible (HTTP {http_code})[/green]")
                else:
                    console.print(f"  [green]✓[/green] {service}: [green]{url} is accessible (HTTP {http_code})[/green]")
                return True
            else:
                if access_type == "localhost":
                    console.print(f"  [yellow]⚠[/yellow] {service}: [yellow]localhost:{url.split(':')[-1]} returned HTTP {http_code}[/yellow]")
                elif access_type == "domain":
                    # Domain might not be resolvable - this is expected
                    return False
        else:
            if access_type == "domain":
                # Don't show error for domain access if it's expected to fail
                return False
            else:
                console.print(f"  [red]✗[/red] {service}: [red]{url} is not accessible (curl exit code: {result.returncode})[/red]")
        return False
    except subprocess.TimeoutExpired:
        if access_type == "localhost":
            console.print(f"  [red]✗[/red] {service}: [red]{url} timed out[/red]")
        return False
    except Exception as e:
        if access_type == "localhost":
            console.print(f"  [red]✗[/red] {service}: [red]Failed to test {url}: {e}[/red]")
        return False

def _display_running_services(
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

    docker_manager = DockerManager(compose_file, project_dir, env_file)
    env_generator = EnvGenerator(env_file)
    caddy_config = CaddyConfig(project_dir)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Initializing…", total=6)

        progress.update(task, advance=1, description="Parsing docker-compose file…")
        services = docker_manager.parse_compose()

        progress.update(task, advance=1, description="Allocating ports…")
        allocated_ports = docker_manager.allocate_ports(services, start_port)

        progress.update(task, advance=1, description="Generating environment variables…")
        env_vars = env_generator.generate(
            services=services,
            ports=allocated_ports,
            domain=domain,
            enable_tls=enable_tls,
            cors_origins=list(cors_origins),
        )

        progress.update(task, advance=1, description="Starting Caddy reverse-proxy…")
        caddy_config.generate_minimal()
        caddy_config.start_caddy()

        progress.update(task, advance=1, description="Starting application containers…")
        try:
            docker_manager.up(env_vars, detach=True)
        except RuntimeError as e:
            console.print(f"[red]Error starting services: {e}[/red]")
            caddy_config.stop_caddy()
            raise click.Abort()
        
        progress.update(task, advance=1, description="Configuring reverse-proxy…")
        caddy_config.generate(services, allocated_ports, domain, enable_tls, list(cors_origins))
        caddy_config.reload_caddy()

    console.print("\n[bold green]✓ All services started![/bold green]\n")
    
    # Verify domain accessibility
    console.print("\n[bold blue]Verifying service accessibility:[/bold blue]")
    console.print("[dim]Testing with curl...[/dim]\n")
    verify_domain_access(allocated_ports, domain, enable_tls)
    
    status_by_service = docker_manager.ps()
    _display_running_services(allocated_ports, domain, enable_tls, status_by_service)
    
    if not detach:
        console.print("\n[dim]Press Ctrl+C to stop all services...[/dim]")
        try:
            docker_manager.logs()
        except KeyboardInterrupt:
            console.print("\n[dim]Stopping services...[/dim]")
            docker_manager.down()
            console.print("\n[green]✓ All services stopped.[/green]")

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

    status_map: Dict[str, Tuple[str, str]] = {}
    for container in containers:
        service_lbl = container.labels.get("com.docker.compose.service", "unknown")
        health = container.attrs.get("State", {}).get("Health", {}).get("Status", "-")
        status_map[service_lbl] = (container.status, health)

    from dotenv import dotenv_values

    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    ports: Dict[str, int] = {}
    for key, val in env_values.items():
        if key.endswith("_PORT"):
            ports[key[:-5].lower()] = int(val)

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

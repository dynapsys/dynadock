from __future__ import annotations

import sys
import subprocess
import time
import shutil
from pathlib import Path
from typing import Tuple, List, Dict, Any

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import logging

from .docker_manager import DockerManager
from .env_generator import EnvGenerator
from .caddy_config import CaddyConfig
from .network_manager import NetworkManager
from .dns_manager import DnsManager
from .network_diagnostics import NetworkDiagnostics
from .utils import find_compose_file
from dotenv import dotenv_values
from .preflight import PreflightChecker
from .hosts_manager import HostsManager
from .cli_helpers.verification import verify_domain_access
from .cli_helpers.display import display_running_services, display_success, display_warning, display_error

__all__ = ["cli"]

console = Console()

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('.dynadock/dynadock.log')
    ]
)
logger = logging.getLogger('dynadock')

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
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging output.",
)
@click.pass_context
def cli(ctx: click.Context, compose_file: str | None, env_file: str, verbose: bool) -> None:
    """DynaDock – Dynamic docker-compose orchestrator with TLS & Caddy love."""
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("🔍 Verbose logging enabled")
    
    logger.info(f"🚀 DynaDock CLI started - compose_file: {compose_file}, env_file: {env_file}")
    
    # Ensure .dynadock directory exists for logs
    Path('.dynadock').mkdir(exist_ok=True)
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

def verify_domain_access(
    allocated_ports: Dict[str, int],
    domain: str,
    enable_tls: bool,
    *,
    retries: int = 2,
    initial_wait: float = 1.0,
    ip_map: Dict[str, str] | None = None,
) -> Tuple[bool, Dict[str, Dict[str, bool]]]:
    """Verify that services are accessible. Returns (all_ok, per-service results).

    Each service is checked against both domain and localhost URLs with a few
    retries using exponential backoff. Detailed curl results are printed.
    """
    protocol = "https" if enable_tls else "http"

    console.print("[dim]Checking service accessibility...[/dim]")
    results: Dict[str, Dict[str, bool]] = {}

    for service, port in allocated_ports.items():
        service_domain = f"{service}.{domain}"
        domain_url = f"{protocol}://{service_domain}"
        localhost_url = f"http://localhost:{port}"

        ok_domain = False
        ok_local = False
        wait = max(0.1, initial_wait)

        logger.info(f"🔍 Verifying service access: {service} on {service_domain}:{port}")
        
        for attempt in range(retries + 1):
            if not ok_domain:
                logger.debug(f"🌐 Testing domain URL: {domain_url} (attempt {attempt + 1})")
                ok_domain = test_url_with_curl(domain_url, service, "domain")
            if not ok_local:
                ok_local = test_url_with_curl(localhost_url, service, "localhost")
            if ok_domain or ok_local:
                break
            time.sleep(wait)
            wait = min(5.0, wait * 1.6)

        results[service] = {"domain": ok_domain, "localhost": ok_local}

    all_ok = all((v["domain"] or v["localhost"]) for v in results.values())
    console.print("\n[dim]Verification complete.[/dim]")
    # Suggest /etc/hosts entries if domain fails but localhost works
    try:
        if not all_ok and ip_map:
            console.print("\n[yellow]Suggestions for domain access:[/yellow]")
            any_suggest = False
            for svc, res in results.items():
                if (not res.get("domain")) and res.get("localhost"):
                    ip = ip_map.get(svc)
                    if ip:
                        console.print(f"  - Add to /etc/hosts: [cyan]{ip}\t{svc}.{domain}[/cyan]")
                        any_suggest = True
            if any_suggest:
                if shutil.which("resolvectl") is None:
                    console.print("  - Your system lacks 'resolvectl' – consider using '--manage-hosts' on 'up'.")
                else:
                    console.print("  - Ensure local DNS is running or use '--manage-hosts' as a fallback.")
    except Exception:
        pass
    return all_ok, results

# Functions moved to cli_helpers.verification module

# Function moved to cli_helpers.display module

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
@click.option("--manage-hosts", is_flag=True, help="Also write fallback entries into /etc/hosts (requires sudo)")
@click.option("--auto-fix", is_flag=True, help="Attempt automatic preflight fixes (containers, DNS cache)")
@click.option("--strict-health", is_flag=True, help="Fail and stop all services if health verification fails")
@click.option("--health-retries", default=3, show_default=True, help="Retries for post-start health verification", type=int)
@click.option("--health-wait", default=1.0, show_default=True, help="Initial wait between health retries (seconds)", type=float)
@click.pass_context
def up(  # noqa: D401
    ctx: click.Context,
    domain: str,
    start_port: int,
    enable_tls: bool,
    cors_origins: Tuple[str, ...],
    detach: bool,
    reload: bool,
    manage_hosts: bool,
    auto_fix: bool,
    strict_health: bool,
    health_retries: int,
    health_wait: float,
) -> None:
    """Start services with dynamic port allocation and routing."""
    compose_file: str = ctx.obj["compose_file"]
    env_file: str = ctx.obj["env_file"]
    project_dir: Path = ctx.obj["project_dir"]

    docker_manager = DockerManager(compose_file, project_dir, env_file)
    env_generator = EnvGenerator(env_file)
    caddy_config = CaddyConfig(project_dir)
    network_manager = NetworkManager(project_dir)
    dns_manager = DnsManager(project_dir, domain)
    hosts_manager = HostsManager(project_dir)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Initializing…", total=8)

        progress.update(task, advance=1, description="Running preflight checks…")
        preflight = PreflightChecker(project_dir).run()
        if preflight.errors:
            console.print("[red]\nPreflight errors detected:[/red]")
            console.print(preflight.pretty())
            if auto_fix:
                console.print("\n[yellow]Attempting auto-fixes…[/yellow]")
                actions = PreflightChecker(project_dir).try_autofix()
                for a in actions:
                    console.print(f"  - {a}")
                preflight = PreflightChecker(project_dir).run()
                if preflight.errors:
                    console.print("[red]\nStill failing after auto-fix. Aborting.[/red]")
                    raise click.Abort()
            else:
                console.print("[yellow]Run again with --auto-fix or resolve the issues above.[/yellow]")
                raise click.Abort()
        if preflight.warnings:
            console.print("[yellow]\nPreflight warnings:[/yellow]")
            console.print(preflight.pretty())

        progress.update(task, advance=1, description="Parsing docker-compose file…")
        services = docker_manager.parse_compose()

        progress.update(task, advance=1, description="Allocating ports…")
        allocated_ports = docker_manager.allocate_ports(services, start_port)

        progress.update(task, advance=1, description=f"Setting up virtual network for domain '{domain}'…")
        dns_ok = True
        allocated_ips = {}
        
        if not manage_hosts:
            # Only set up virtual network if not using hosts-only mode
            try:
                allocated_ips = network_manager.setup_interfaces(services, domain)
                if not allocated_ips:  # Script failed, fall back to hosts mode
                    console.print("[yellow]Virtual network setup failed, falling back to /etc/hosts mode[/yellow]")
                    dns_ok = False
                else:
                    # Start local DNS resolver for *.domain -> service IPs
                    console.print("[dim]Starting local DNS resolver (dnsmasq)…[/dim]")
                    try:
                        dns_manager.start_dns(allocated_ips)
                        console.print("[green]✓ Local DNS ready[/green]")
                    except Exception as dns_err:  # noqa: BLE001
                        dns_ok = False
                        console.print(f"[yellow]⚠ Local DNS could not be started: {dns_err}[/yellow]")
                        console.print("[yellow]Falling back to /etc/hosts (requires sudo)…[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Network setup error: {e}, falling back to /etc/hosts mode[/yellow]")
                dns_ok = False
        else:
            console.print("[yellow]Using /etc/hosts mode (--manage-hosts specified)[/yellow]")
            dns_ok = False

        progress.update(task, advance=1, description="Generating environment variables…")
        env_vars = env_generator.generate(
            services=services,
            ports=allocated_ports,
            domain=domain,
            enable_tls=enable_tls,
            cors_origins=list(cors_origins),
        )

        # Optional hosts fallback
        use_hosts = manage_hosts or (shutil.which("resolvectl") is None) or (not locals().get("dns_ok", True))
        if use_hosts:
            console.print("[yellow]Applying /etc/hosts fallback entries (requires sudo)…[/yellow]")
            try:
                # If no virtual IPs allocated (--manage-hosts mode), use localhost for all services
                hosts_ips = allocated_ips if allocated_ips else {service: "127.0.0.1" for service in services}
                hosts_manager.apply(hosts_ips, domain)
                console.print("[green]✓ /etc/hosts updated[/green]")
            except Exception as he:  # noqa: BLE001
                console.print(f"[red]Failed to update /etc/hosts: {he}[/red]")

        progress.update(task, advance=1, description="Starting Caddy reverse-proxy…")
        caddy_config.generate_minimal()
        try:
            caddy_config.start_caddy()
        except subprocess.CalledProcessError as ce:
            console.print("[red]\nFailed to start Caddy reverse-proxy.[/red]")
            console.print("[yellow]Common causes: Ports 80/443 are in use by another process.[/yellow]")
            console.print("[dim]Tip: Free the ports or stop the conflicting service, then try again.[/dim]")
            # Cleanup partial setup
            try:
                dns_manager.stop_dns()
            finally:
                network_manager.teardown_interfaces(domain)
            raise click.Abort()

        progress.update(task, advance=1, description="Starting application containers…")
        try:
            docker_manager.up(env_vars, detach=True)
        except RuntimeError as e:
            console.print(f"[red]Error starting services: {e}[/red]")
            caddy_config.stop_caddy()
            try:
                dns_manager.stop_dns()
            finally:
                network_manager.teardown_interfaces(domain)
            raise click.Abort()
        
        progress.update(task, advance=1, description="Configuring reverse-proxy…")
        caddy_config.generate(services, allocated_ports, domain, enable_tls, list(cors_origins), allocated_ips)
        caddy_config.reload_caddy()

    console.print("\n[bold green]✓ All services started![/bold green]\n")
    
    console.print("\n[bold blue]Verifying service accessibility:[/bold blue]")
    console.print("[dim]Testing with curl...[/dim]\n")
    all_ok, results = verify_domain_access(allocated_ports, domain, enable_tls, retries=health_retries, initial_wait=health_wait, ip_map=allocated_ips)

    if strict_health and not all_ok:
        failed = [svc for svc, res in results.items() if not (res["domain"] or res["localhost"]) ]
        console.print(f"\n[red]Health verification failed for: {', '.join(failed)}[/red]")
        console.print("[yellow]Stopping all services due to --strict-health...[/yellow]")
        try:
            docker_manager.down()
        finally:
            try:
                dns_manager.stop_dns()
            finally:
                network_manager.teardown_interfaces(domain)
        raise click.Abort()
    
    status_by_service = docker_manager.ps()
    _display_running_services(allocated_ports, domain, enable_tls, status_by_service)
    
    if not detach:
        console.print("\n[dim]Press Ctrl+C to stop all services...[/dim]")
        try:
            docker_manager.logs()
        except KeyboardInterrupt:
            console.print("\n[dim]Stopping services...[/dim]")
            docker_manager.down()
            network_manager.teardown_interfaces(domain)
            console.print("\n[green]✓ All services stopped.[/green]")

@cli.command()
@click.option("--remove-volumes", "-v", is_flag=True, help="Remove docker volumes as well.")
@click.option("--remove-images", is_flag=True, help="Remove images (docker-compose --rmi all)")
@click.option("--prune", is_flag=True, help="Shortcut for --remove-volumes --remove-images")
@click.option("--remove-hosts", is_flag=True, help="Remove dynadock entries from /etc/hosts")
@click.pass_context
def down(ctx: click.Context, remove_volumes: bool, remove_images: bool, prune: bool, remove_hosts: bool) -> None:
    """Stop and remove all services including the reverse-proxy."""
    compose_file: str = ctx.obj["compose_file"]
    project_dir: Path = ctx.obj["project_dir"]
    env_file: str = ctx.obj["env_file"]

    docker_manager = DockerManager(compose_file, project_dir, env_file)
    caddy_config = CaddyConfig(project_dir)
    network_manager = NetworkManager(project_dir)

    if prune:
        remove_volumes = True
        remove_images = True

    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    domain = env_values.get("DYNADOCK_DOMAIN", "local.dev")

    dns_manager = DnsManager(project_dir, domain)
    hosts_manager = HostsManager(project_dir)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Stopping services…", total=5)
        progress.update(task, advance=1, description="Stopping application containers…")
        docker_manager.down(remove_volumes=remove_volumes, remove_images=remove_images)
        progress.update(task, advance=1, description="Stopping Caddy reverse-proxy…")
        caddy_config.stop_caddy()
        progress.update(task, advance=1, description="Stopping local DNS resolver…")
        try:
            dns_manager.stop_dns()
        except Exception:
            console.print("[yellow]Warning: Could not stop local DNS resolver.[/yellow]")
        progress.update(task, advance=1, description="Tearing down virtual network…")
        try:
            network_manager.teardown_interfaces(domain)
        except subprocess.CalledProcessError as e:
            console.print(f"\n[bold yellow]Warning: Could not tear down virtual network interfaces.[/bold yellow]")
            console.print(f"[yellow]  Command: {' '.join(e.cmd)}[/yellow]")
            console.print(f"[yellow]  Exit Code: {e.returncode}[/yellow]")
            console.print(f"[yellow]  Stderr: {e.stderr.decode().strip() if e.stderr else 'N/A'}[/yellow]")
            console.print("[dim]  This may happen if the 'up' command failed prematurely. Manual cleanup may be required.[/dim]")
        except FileNotFoundError:
            console.print(f"\n[bold red]Error: 'manage_veth.sh' script not found.[/bold red]")
            console.print("[dim]  Please ensure the 'scripts' directory is in the project root.[/dim]")
        if remove_hosts:
            progress.update(task, advance=0, description="Removing /etc/hosts entries…")
            try:
                hosts_manager.remove()
                console.print("[green]✓ /etc/hosts entries removed[/green]")
            except Exception:
                console.print("[yellow]Warning: Could not remove /etc/hosts entries[/yellow]")
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


@cli.command()
@click.pass_context
@click.option("--stop-on-fail", is_flag=True, help="Stop all services if health fails")
def health(ctx: click.Context, stop_on_fail: bool) -> None:  # noqa: D401
    """Run health checks against all services using current .env.dynadock."""
    env_file: str = ctx.obj["env_file"]
    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    if not env_values:
        console.print("[red]No .env.dynadock found. Run `up` first.[/red]")
        raise SystemExit(1)

    domain = env_values.get("DYNADOCK_DOMAIN", "local.dev")
    enable_tls = env_values.get("DYNADOCK_ENABLE_TLS", "false").lower() == "true"
    protocol = "https" if enable_tls else "http"

    ports: Dict[str, int] = {}
    for key, val in env_values.items():
        if key.endswith("_PORT"):
            service = key[:-5].lower()
            try:
                ports[service] = int(val)
            except ValueError:
                continue

    if not ports:
        console.print("[red]No service ports found in .env.dynadock.[/red]")
        raise SystemExit(1)

    console.print("[bold blue]\nHealth checking services...[/bold blue]")
    all_ok = True
    for service, port in ports.items():
        domain_url = f"{protocol}://{service}.{domain}"
        local_url = f"http://localhost:{port}"
        ok_domain = test_url_with_curl(domain_url, service, "domain")
        ok_local = test_url_with_curl(local_url, service, "localhost")
        if not (ok_domain or ok_local):
            all_ok = False

    if all_ok:
        console.print("\n[green]All services healthy.[/green]")
        raise SystemExit(0)
    else:
        console.print("\n[red]One or more services are unhealthy or unreachable.[/red]")
        if stop_on_fail:
            compose_file: str = ctx.obj["compose_file"]
            project_dir: Path = ctx.obj["project_dir"]
            docker_manager = DockerManager(compose_file, project_dir)
            console.print("[yellow]Stopping services (--stop-on-fail)...[/yellow]")
            try:
                docker_manager.down()
            except Exception:
                pass
        raise SystemExit(2)


@cli.command(name="net-diagnose")
@click.option("--domain", "-d", default="local.dev", help="Base domain for sub-domains.")
@click.pass_context
def net_diagnose(ctx: click.Context, domain: str) -> None:
    """Diagnose Dynadock virtual networking and DNS setup."""
    project_dir: Path = ctx.obj["project_dir"]
    env_file: str = ctx.obj["env_file"]
    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    domain = env_values.get("DYNADOCK_DOMAIN", domain)

    diag = NetworkDiagnostics(project_dir, domain)
    report = diag.diagnose()
    console.print(report)


@cli.command(name="net-repair")
@click.option("--domain", "-d", default="local.dev", help="Base domain for sub-domains.")
@click.pass_context
def net_repair(ctx: click.Context, domain: str) -> None:
    """Attempt to auto-repair Dynadock virtual networking and DNS."""
    project_dir: Path = ctx.obj["project_dir"]
    env_file: str = ctx.obj["env_file"]
    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    domain = env_values.get("DYNADOCK_DOMAIN", domain)

    diag = NetworkDiagnostics(project_dir, domain)
    actions = diag.repair()
    console.print(actions)


@cli.command(name="doctor")
@click.option("--auto-fix", is_flag=True, help="Attempt automatic fixes (DNS cache, stale containers)")
@click.pass_context
def doctor(ctx: click.Context, auto_fix: bool) -> None:
    """Run preflight and network diagnostics and optionally auto-fix issues."""
    project_dir: Path = ctx.obj["project_dir"]
    env_file: str = ctx.obj["env_file"]
    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    domain = env_values.get("DYNADOCK_DOMAIN", "local.dev")

    pre = PreflightChecker(project_dir)
    report = pre.run()
    console.print("[bold blue]\nPreflight Check[/bold blue]")
    console.print(report.pretty())
    if report.errors and auto_fix:
        console.print("[yellow]\nAttempting auto-fix...[/yellow]")
        for a in pre.try_autofix():
            console.print(f"  - {a}")
        console.print("\nPost-fix preflight status:")
        console.print(pre.run().pretty())

    console.print("[bold blue]\nNetwork Diagnostics[/bold blue]")
    diag = NetworkDiagnostics(project_dir, domain)
    console.print(diag.diagnose())

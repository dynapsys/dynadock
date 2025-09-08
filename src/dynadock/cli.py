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
from .lan_network_manager import LANNetworkManager
from .dns_manager import DnsManager
from .network_diagnostics import NetworkDiagnostics
from .utils import find_compose_file
from dotenv import dotenv_values
from .preflight import PreflightChecker
from .hosts_manager import HostsManager
from .cli_helpers.verification import verify_domain_access, test_url_with_curl
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


# Functions moved to cli_helpers.verification module

# Function moved to cli_helpers.display module

@cli.command()
@click.option("--domain", "-d", default="dynadock.lan", help="Base domain for sub-domains.")
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
@click.option("--lan-visible", is_flag=True, help="Create LAN-visible virtual IPs (requires sudo, no DNS setup needed)")
@click.option("--network-interface", help="Network interface for LAN-visible mode (auto-detected if not specified)")
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
    lan_visible: bool,
    network_interface: str,
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
    caddy_config = CaddyConfig(project_dir=str(project_dir), domain=domain, enable_tls=enable_tls)
    network_manager = NetworkManager(project_dir)
    lan_network_manager = LANNetworkManager(project_dir, network_interface) if lan_visible else None
    dns_manager = DnsManager(project_dir, domain or "dynadock.lan")
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

        progress.update(task, advance=1, description=f"Setting up networking for domain '{domain}'…")
        dns_ok = True
        allocated_ips: Dict[str, str] = {}
        
        if lan_visible:
            # Use LAN-visible virtual IPs mode
            console.print("[cyan]Setting up LAN-visible virtual IPs (requires sudo)…[/cyan]")
            if not lan_network_manager:
                display_error("LAN network manager not initialized despite --lan-visible flag.")
                raise click.Abort()
            try:
                allocated_ips = lan_network_manager.setup_services_lan(services)
                console.print(f"[green]✓ Created {len(allocated_ips)} LAN-visible IPs[/green]")
                # No DNS needed - direct IP access
                dns_ok = True
            except Exception as e:
                console.print(f"[red]❌ LAN networking setup failed: {e}[/red]")
                console.print("[yellow]Falling back to /etc/hosts mode…[/yellow]")
                dns_ok = False
        elif not manage_hosts:
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

        # Optional hosts fallback (skip for LAN-visible mode as IPs are directly accessible)
        use_hosts = (manage_hosts or (shutil.which("resolvectl") is None) or (not locals().get("dns_ok", True))) and not lan_visible
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
                if lan_network_manager:
                    lan_network_manager.cleanup_all()
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
                if lan_network_manager:
                    lan_network_manager.cleanup_all()
            raise click.Abort()
        
        progress.update(task, advance=1, description="Configuring reverse-proxy…")
        caddy_config.generate(
            services=services,
            ports=allocated_ports,
            domain=domain,
            enable_tls=enable_tls,
            cors_origins=list(cors_origins),
            ips=allocated_ips or None,
        )
        caddy_config.reload_caddy()

    console.print("\n[bold green]✓ All services started![/bold green]\n")
    
    # Special handling for LAN-visible networking
    if lan_visible and lan_network_manager and allocated_ips:
        console.print("\n[bold green]✅ LAN-visible services ready![/bold green]")
        console.print("\n[bold cyan]🌐 Services accessible from ANY device on your network:[/bold cyan]\n")
        
        service_urls = lan_network_manager.get_service_urls(allocated_ips, allocated_ports)
        for service, url in service_urls.items():
            console.print(f"   🔗 {service}: [link]{url}[/link]")
        
        console.print("\n[dim]💡 No DNS setup required - access directly from phones, tablets, other computers![/dim]")
        
        # Test LAN connectivity
        console.print("\n[bold blue]Testing LAN connectivity:[/bold blue]")
        connectivity_results = lan_network_manager.test_connectivity(allocated_ips, allocated_ports)
        all_ok = all(connectivity_results.values())
        results = {service: {"domain": result, "localhost": True} for service, result in connectivity_results.items()}
    else:
        console.print("\n[bold blue]Verifying service accessibility:[/bold blue]")
        console.print("[dim]Testing with curl...[/dim]\n")
        all_ok, results = verify_domain_access(
            allocated_ports=allocated_ports,
            domain=domain,
            enable_tls=enable_tls,
            retries=health_retries,
            initial_wait=health_wait,
            ip_map=allocated_ips
        )

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
                if lan_network_manager:
                    lan_network_manager.cleanup_all()
        raise click.Abort()
    
    status_by_service = docker_manager.ps()
    display_running_services(allocated_ports, domain, enable_tls, status_by_service)
    
    if not detach:
        console.print("\n[dim]Press Ctrl+C to stop all services...[/dim]")
        try:
            docker_manager.logs()
        except KeyboardInterrupt:
            console.print("\n[dim]Stopping services...[/dim]")
            docker_manager.down()
            network_manager.teardown_interfaces(domain)
            # Clean up LAN networking if it was used
            try:
                lan_cleanup_manager = LANNetworkManager(project_dir)
                lan_cleanup_manager.cleanup_all()
            except Exception:
                pass  # LAN networking may not have been used
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
    network_manager = NetworkManager(project_dir)
    lan_network_manager = LANNetworkManager(project_dir, None)
    hosts_manager = HostsManager(project_dir)

    if prune:
        remove_volumes = True
        remove_images = True

    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    domain = env_values.get("DYNADOCK_DOMAIN", "dynadock.lan")
    enable_tls_str = env_values.get("DYNADOCK_ENABLE_TLS", "false")
    enable_tls = bool(enable_tls_str and enable_tls_str.lower() == "true")

    caddy_config = CaddyConfig(project_dir=str(project_dir), domain=domain or "dynadock.lan", enable_tls=enable_tls)
    dns_manager = DnsManager(project_dir, domain or "dynadock.lan")

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
        progress.update(task, advance=1, description="Tearing down networks…")
        try:
            if domain:
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

        # Clean up LAN networking
        try:
            if lan_network_manager:
                lan_network_manager.cleanup_all()
        except Exception:
            pass  # LAN networking may not have been used
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
            if val:
                try:
                    ports[key[:-5].lower()] = int(val)
                except (ValueError, TypeError):
                    pass

    domain_val = env_values.get("DYNADOCK_DOMAIN", "dynadock.lan")
    enable_tls_str = env_values.get("DYNADOCK_ENABLE_TLS", "false")
    enable_tls_val = bool(enable_tls_str and enable_tls_str.lower() == "true")
    display_running_services(ports, domain_val or "dynadock.lan", enable_tls_val, status_map)

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

    domain = env_values.get("DYNADOCK_DOMAIN", "dynadock.lan")
    enable_tls_str = env_values.get("DYNADOCK_ENABLE_TLS", "false")
    enable_tls = bool(enable_tls_str and enable_tls_str.lower() == "true")
    protocol = "https" if enable_tls else "http"

    ports: Dict[str, int] = {}
    for key, val in env_values.items():
        if key.endswith("_PORT"):
            service = key[:-5].lower()
            if val:
                try:
                    ports[service] = int(val)
                except (ValueError, TypeError):
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
            env_file: str = ctx.obj["env_file"]
            docker_manager = DockerManager(compose_file, project_dir, env_file)
            console.print("[yellow]Stopping services (--stop-on-fail)...[/yellow]")
            try:
                docker_manager.down()
            except Exception:
                pass
        raise SystemExit(2)


@cli.command(name="net-diagnose")
@click.option("--domain", "-d", default="dynadock.lan", help="Base domain for sub-domains.")
@click.pass_context
def net_diagnose(ctx: click.Context, domain: str) -> None:
    """Diagnose Dynadock virtual networking and DNS setup."""
    project_dir: Path = ctx.obj["project_dir"]
    env_file: str = ctx.obj["env_file"]
    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    domain_str = env_values.get("DYNADOCK_DOMAIN", domain)

    diag = NetworkDiagnostics(project_dir, domain_str or "dynadock.lan")
    report = diag.diagnose()
    console.print(report)


@cli.command(name="net-repair")
@click.option("--domain", "-d", default="dynadock.lan", help="Base domain for sub-domains.")
@click.pass_context
def net_repair(ctx: click.Context, domain: str) -> None:
    """Attempt to auto-repair Dynadock virtual networking and DNS."""
    project_dir: Path = ctx.obj["project_dir"]
    env_file: str = ctx.obj["env_file"]
    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    domain_str = env_values.get("DYNADOCK_DOMAIN", domain)

    diag = NetworkDiagnostics(project_dir, domain_str or "dynadock.lan")
    actions = diag.repair()
    console.print(actions)


@cli.command(name="lan-test")
@click.option("--interface", "-i", help="Network interface (auto-detected if not specified)")
@click.option("--num-ips", "-n", default=3, help="Number of test IPs to create", type=int)
@click.option("--port", "-p", default=8000, help="Starting port for test servers", type=int)
@click.pass_context
def lan_test(ctx: click.Context, interface: str, num_ips: int, port: int) -> None:
    """Test LAN-visible networking functionality (requires sudo)."""
    project_dir: Path = ctx.obj["project_dir"]
    
    console.print("""
[bold cyan]🌐 DynaDock LAN-Visible Networking Test[/bold cyan]

This command will:
1. Check root privileges (required)
2. Detect network configuration
3. Find available IP addresses in your LAN
4. Create virtual IPs visible to all devices on the network
5. Start test HTTP servers on those IPs
6. Test connectivity and provide access URLs

[yellow]⚠️  Requires sudo privileges to create virtual network interfaces[/yellow]
    """)
    
    try:
        lan_manager = LANNetworkManager(project_dir, interface)
        
        # Check root privileges
        if not lan_manager or not lan_manager.check_root_privileges():
            console.print("[red]❌ This command requires sudo privileges[/red]")
            console.print("[dim]Run: sudo dynadock lan-test[/dim]")
            raise click.Abort()
        
        console.print("[bold blue]📡 Network Analysis[/bold blue]")
        current_ip, network_base, cidr, broadcast = lan_manager.get_network_details()
        
        if not current_ip:
            console.print("[red]❌ Could not detect network configuration[/red]")
            raise click.Abort()
        
        console.print("[bold blue]🔍 Finding Available IPs[/bold blue]")
        if not network_base or not cidr:
            console.print("[red]❌ Network base or CIDR not found.[/red]")
            raise click.Abort()
        available_ips = lan_manager.find_free_ips(network_base, cidr, num_ips)
        
        if not available_ips:
            console.print("[red]❌ No available IP addresses found[/red]")
            raise click.Abort()
        
        console.print(f"[green]✅ Found {len(available_ips)} available IPs[/green]")
        
        # Create test services
        test_services: dict[str, dict] = {f"test{i+1}": {} for i in range(len(available_ips))}
        
        console.print("[bold blue]🚀 Creating LAN-Visible IPs[/bold blue]")
        service_ips = lan_manager.setup_services_lan(test_services)
        
        if not service_ips:
            console.print("[red]❌ Failed to create LAN-visible IPs[/red]")
            raise click.Abort()
        
        # Create port mapping for test
        port_map = {service: port + i for i, service in enumerate(service_ips.keys())}
        
        console.print("[bold green]✅ LAN-Visible Test Services Created![/bold green]")
        console.print("\n[bold cyan]🌐 Access URLs (from ANY device on your network):[/bold cyan]")
        
        service_urls = lan_manager.get_service_urls(service_ips, port_map)
        for service, url in service_urls.items():
            console.print(f"   🔗 {service}: [link]{url}[/link]")
        
        console.print("\n[bold blue]🧪 Testing Connectivity[/bold blue]")
        # Note: Since we're not actually starting HTTP servers in this test,
        # we'll just test that the IPs are reachable via ping
        all_reachable = True
        for service, ip in service_ips.items():
            try:
                import subprocess
                result = subprocess.run(f"ping -c 1 {ip}", shell=True, capture_output=True, timeout=2)
                if result.returncode == 0:
                    console.print(f"   ✅ {service} ({ip}) - Reachable")
                else:
                    console.print(f"   ❌ {service} ({ip}) - Not reachable")
                    all_reachable = False
            except Exception:
                console.print(f"   ⚠️ {service} ({ip}) - Test failed")
                all_reachable = False
        
        if all_reachable:
            console.print("\n[bold green]🎉 All test IPs are reachable![/bold green]")
            console.print("[dim]💡 You can now use --lan-visible with 'dynadock up' for real services[/dim]")
        else:
            console.print("\n[yellow]⚠️ Some IPs are not reachable - check network configuration[/yellow]")
        
        console.print(f"\n[bold cyan]📋 Usage Example:[/bold cyan]")
        console.print(f"[dim]# Start your services with LAN-visible networking:[/dim]")
        console.print(f"sudo dynadock up --lan-visible")
        if interface:
            console.print(f"sudo dynadock up --lan-visible --network-interface {interface}")
        
        console.print(f"\n[yellow]⚠️ Cleaning up test IPs in 10 seconds...[/yellow]")
        console.print("[dim]Press Ctrl+C to clean up immediately[/dim]")
        
        try:
            import time
            time.sleep(10)
        except KeyboardInterrupt:
            console.print("\n[dim]Cleaning up...[/dim]")
        
        lan_manager.cleanup_all()
        console.print("[green]✅ Test cleanup completed[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Test failed: {e}[/red]")
        try:
            lan_manager.cleanup_all()
        except Exception:
            pass
        raise click.Abort()


@cli.command(name="doctor")
@click.option("--auto-fix", is_flag=True, help="Attempt automatic fixes (DNS cache, stale containers)")
@click.pass_context
def doctor(ctx: click.Context, auto_fix: bool) -> None:
    """Run preflight and network diagnostics and optionally auto-fix issues."""
    project_dir: Path = ctx.obj["project_dir"]
    env_file: str = ctx.obj["env_file"]
    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    domain = env_values.get("DYNADOCK_DOMAIN", "dynadock.lan")

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
    diag = NetworkDiagnostics(project_dir, domain or "dynadock.lan")
    console.print(diag.diagnose())

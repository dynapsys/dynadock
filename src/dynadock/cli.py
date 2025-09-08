from __future__ import annotations

import sys
import subprocess
import time
import shutil
from pathlib import Path
from typing import Tuple, Dict

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
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
from .cli_helpers.verification import verify_domain_access
from .cli_helpers.display import (
    display_running_services,
    display_error,
)
from .performance_analyzer import PerformanceAnalyzer
from .log_config import setup_logging

__all__ = ["cli"]

console = Console()

logger = logging.getLogger("dynadock")


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
def cli(
    ctx: click.Context, compose_file: str | None, env_file: str, verbose: bool
) -> None:
    """DynaDock – Dynamic docker-compose orchestrator with TLS & Caddy love."""
    setup_logging(verbose)

    logger.info(
        f"🚀 DynaDock CLI started - compose_file: {compose_file}, env_file: {env_file}"
    )
    ctx.ensure_object(dict)
    if compose_file is None:
        compose_file = find_compose_file()
        if compose_file is None:
            console.print(
                "[red]Error: could not locate a docker-compose YAML file.[/red]"
            )
            sys.exit(1)

    compose_path = Path(compose_file).resolve()
    ctx.obj["compose_file"] = str(compose_path)
    ctx.obj["env_file"] = env_file
    ctx.obj["project_dir"] = compose_path.parent


# Functions moved to cli_helpers.verification module

# Function moved to cli_helpers.display module


@cli.command()
@click.option(
    "--domain", "-d", default="dynadock.lan", help="Base domain for sub-domains."
)
@click.option(
    "--reload",
    is_flag=True,
    help="Reload configuration and restart if already running.",
)
@click.option(
    "--start-port", "-p", default=8000, type=int, help="Starting port for allocation"
)
@click.option(
    "--enable-tls", is_flag=True, help="Enable TLS with an internal CA via Caddy"
)
@click.option(
    "--cors-origins",
    "-c",
    multiple=True,
    help="Additional CORS allowed origins (can be passed multiple times).",
)
@click.option("--detach", is_flag=True, help="Run in background without following logs")
@click.option(
    "--manage-hosts",
    is_flag=True,
    help="Also write fallback entries into /etc/hosts (requires sudo)",
)
@click.option(
    "--lan-visible",
    is_flag=True,
    help="Create LAN-visible virtual IPs (requires sudo, no DNS setup needed)",
)
@click.option(
    "--network-interface",
    help="Network interface for LAN-visible mode (auto-detected if not specified)",
)
@click.option(
    "--auto-fix",
    is_flag=True,
    help="Attempt automatic preflight fixes (containers, DNS cache)",
)
@click.option(
    "--strict-health",
    is_flag=True,
    help="Fail and stop all services if health verification fails",
)
@click.option(
    "--health-retries",
    default=3,
    show_default=True,
    help="Retries for post-start health verification",
    type=int,
)
@click.option(
    "--health-wait",
    default=1.0,
    show_default=True,
    help="Initial wait between health retries (seconds)",
    type=float,
)
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

    # --- Timing setup ---
    start_time = time.time()
    last_step_time = start_time

    def log_step_duration(step_name: str):
        nonlocal last_step_time
        current_time = time.time()
        duration = current_time - last_step_time
        logger.info(f"TIMER: Step '{step_name}' finished in {duration:.2f}s")
        last_step_time = current_time

    # ------------------

    docker_manager = DockerManager(compose_file, project_dir, env_file)
    env_generator = EnvGenerator(env_file)
    caddy_config = CaddyConfig(
        project_dir=str(project_dir), domain=domain, enable_tls=enable_tls
    )
    network_manager = NetworkManager(project_dir)
    lan_network_manager = (
        LANNetworkManager(project_dir, network_interface) if lan_visible else None
    )
    dns_manager = DnsManager(project_dir, domain or "dynadock.lan")
    hosts_manager = HostsManager(project_dir)

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console
    ) as progress:
        task = progress.add_task("Initializing…", total=8)

        progress.update(task, advance=1, description="Running preflight checks…")
        preflight_checker = PreflightChecker(project_dir)
        preflight_report = preflight_checker.run()

        if preflight_report.errors:
            console.print("\n[red]❌ Preflight checks failed with errors:[/red]")
            console.print(preflight_report.pretty())
            console.print(
                "\n[yellow]Please resolve the issues above and try again.[/yellow]"
            )
            raise click.Abort()

        if preflight_report.warnings:
            console.print("\n[yellow]Preflight checks passed with warnings:[/yellow]")
            console.print(preflight_report.pretty())
        log_step_duration("Preflight checks")

        progress.update(task, advance=1, description="Parsing docker-compose file…")
        services = docker_manager.parse_compose()
        log_step_duration("Parsing docker-compose file")

        progress.update(task, advance=1, description="Allocating ports…")
        allocated_ports = docker_manager.allocate_ports(services, start_port)
        log_step_duration("Allocating ports")

        progress.update(
            task, advance=1, description=f"Setting up networking for domain '{domain}'…"
        )
        dns_ok = True
        allocated_ips: Dict[str, str] = {}

        if lan_visible:
            # Use LAN-visible virtual IPs mode
            console.print(
                "[cyan]Setting up LAN-visible virtual IPs (requires sudo)…[/cyan]"
            )
            if not lan_network_manager:
                display_error(
                    "LAN network manager not initialized despite --lan-visible flag."
                )
                raise click.Abort()
            try:
                allocated_ips = lan_network_manager.setup_services_lan(services)
                console.print(
                    f"[green]✓ Created {len(allocated_ips)} LAN-visible IPs[/green]"
                )
                # Detect cross-host IP/port conflicts before proceeding
                if allocated_ips:
                    conflicts = lan_network_manager.detect_conflicts(
                        allocated_ips, allocated_ports
                    )
                    if conflicts:
                        console.print(
                            "\n[bold red]❌ LAN IP/port conflicts detected[/bold red]"
                        )
                        table = Table("Service", "IP", "Port", "Issue")
                        for svc, info in conflicts.items():
                            ip = allocated_ips.get(svc, "-")
                            port = allocated_ports.get(svc, 80)
                            issues = []
                            if info.get("ip_in_use_by_other_host"):
                                mac = info.get("remote_mac", "?")
                                issues.append(f"IP owned by other host (MAC {mac})")
                            if info.get("port_in_use_by_other_host"):
                                issues.append("Port in use on other host")
                            if info.get("port_open"):
                                issues.append("Port already open at IP")
                            table.add_row(
                                svc, ip, str(port), "; ".join(issues) or "Unknown"
                            )
                        console.print(table)
                        console.print(
                            "[yellow]Hint: choose different IPs or ports, or stop the conflicting host.[/yellow]"
                        )
                        raise click.Abort()
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
                    console.print(
                        "[yellow]Virtual network setup failed, falling back to /etc/hosts mode[/yellow]"
                    )
                    dns_ok = False
                else:
                    # Start local DNS resolver for *.domain -> service IPs
                    console.print("[dim]Starting local DNS resolver (dnsmasq)…[/dim]")
                    try:
                        dns_manager.start_dns(allocated_ips)
                        console.print("[green]✓ Local DNS ready[/green]")
                    except Exception as dns_err:  # noqa: BLE001
                        dns_ok = False
                        console.print(
                            f"[yellow]⚠ Local DNS could not be started: {dns_err}[/yellow]"
                        )
                        console.print(
                            "[yellow]Falling back to /etc/hosts (requires sudo)…[/yellow]"
                        )
            except Exception as e:
                console.print(
                    f"[yellow]Network setup error: {e}, falling back to /etc/hosts mode[/yellow]"
                )
                dns_ok = False
        else:
            console.print(
                "[yellow]Using /etc/hosts mode (--manage-hosts specified)[/yellow]"
            )
            dns_ok = False
        log_step_duration(
            f"Setting up networking (lan_visible={lan_visible}, manage_hosts={manage_hosts})"
        )

        progress.update(
            task, advance=1, description="Generating environment variables…"
        )
        env_vars = env_generator.generate(
            services=services,
            ports=allocated_ports,
            domain=domain,
            enable_tls=enable_tls,
            cors_origins=list(cors_origins),
        )
        log_step_duration("Generating environment variables")

        # Optional hosts fallback (skip for LAN-visible mode as IPs are directly accessible)
        use_hosts = (
            manage_hosts
            or (shutil.which("resolvectl") is None)
            or (not locals().get("dns_ok", True))
        ) and not lan_visible
        if use_hosts:
            console.print(
                "[yellow]Applying /etc/hosts fallback entries (requires sudo)…[/yellow]"
            )
            try:
                # If no virtual IPs allocated (--manage-hosts mode), use localhost for all services
                hosts_ips = (
                    allocated_ips
                    if allocated_ips
                    else {service: "127.0.0.1" for service in services}
                )
                hosts_manager.apply(hosts_ips, domain)
                console.print("[green]✓ /etc/hosts updated[/green]")
            except Exception as he:  # noqa: BLE001
                console.print(f"[red]Failed to update /etc/hosts: {he}[/red]")
            log_step_duration("Applying /etc/hosts fallback")

        progress.update(task, advance=1, description="Starting Caddy reverse-proxy…")
        caddy_config.generate_minimal()
        try:
            caddy_config.start_caddy()
        except subprocess.CalledProcessError:
            console.print("[red]\nFailed to start Caddy reverse-proxy.[/red]")
            console.print(
                "[yellow]Common causes: Ports 80/443 are in use by another process.[/yellow]"
            )
            console.print(
                "[dim]Tip: Free the ports or stop the conflicting service, then try again.[/dim]"
            )
            # Cleanup partial setup
            try:
                dns_manager.stop_dns()
            finally:
                network_manager.teardown_interfaces(domain)
                if lan_network_manager:
                    lan_network_manager.cleanup_all()
            raise click.Abort()

        log_step_duration("Starting Caddy reverse-proxy")
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

        log_step_duration("Starting application containers")

        # Wait for services with health checks to be healthy
        services_with_health_checks = [
            svc for svc, cfg in services.items() if "healthcheck" in cfg
        ]
        if services_with_health_checks:
            docker_manager.wait_for_healthy_services(services_with_health_checks)
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
        log_step_duration("Configuring reverse-proxy")

    console.print("\n[bold green]✓ All services started![/bold green]\n")

    # Special handling for LAN-visible networking
    if lan_visible and lan_network_manager and allocated_ips:
        console.print("\n[bold green]✅ LAN-visible services ready![/bold green]")
        console.print(
            "\n[bold cyan]🌐 Services accessible from ANY device on your network:[/bold cyan]\n"
        )

        service_urls = lan_network_manager.get_service_urls(
            allocated_ips, allocated_ports
        )
        for service, url in service_urls.items():
            console.print(f"   🔗 {service}: [link]{url}[/link]")

        console.print(
            "\n[dim]💡 No DNS setup required - access directly from phones, tablets, other computers![/dim]"
        )

        # Test LAN connectivity
        console.print("\n[bold blue]Testing LAN connectivity:[/bold blue]")
        connectivity_results = lan_network_manager.test_connectivity(
            allocated_ips, allocated_ports
        )
        all_ok = all(connectivity_results.values())
        results = {
            service: {"domain": result, "localhost": True}
            for service, result in connectivity_results.items()
        }
    else:
        console.print("\n[bold blue]Verifying service accessibility:[/bold blue]")
        console.print("[dim]Testing with curl...[/dim]\n")
        all_ok, results = verify_domain_access(
            services_config=services,
            allocated_ports=allocated_ports,
            domain=domain,
            enable_tls=enable_tls,
            retries=health_retries,
            initial_wait=health_wait,
            ip_map=allocated_ips,
        )

    if strict_health and not all_ok:
        failed = [
            svc
            for svc, res in results.items()
            if not (res["domain"] or res["localhost"])
        ]
        console.print(
            f"\n[red]Health verification failed for: {', '.join(failed)}[/red]"
        )
        console.print(
            "[yellow]Stopping all services due to --strict-health...[/yellow]"
        )
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

    total_duration = time.time() - start_time
    logger.info(f"TIMER: Total 'up' command duration: {total_duration:.2f}s")

    # --- Performance Analysis ---
    analyzer = PerformanceAnalyzer(project_dir)
    analysis_report = analyzer.analyze()
    analyzer.display_report(analysis_report)
    # --------------------------

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
@click.option(
    "--remove-volumes", "-v", is_flag=True, help="Remove docker volumes as well."
)
@click.option(
    "--remove-images", is_flag=True, help="Remove images (docker-compose --rmi all)"
)
@click.option(
    "--prune", is_flag=True, help="Shortcut for --remove-volumes --remove-images"
)
@click.option(
    "--remove-hosts", is_flag=True, help="Remove dynadock entries from /etc/hosts"
)
@click.pass_context
def down(
    ctx: click.Context,
    remove_volumes: bool,
    remove_images: bool,
    prune: bool,
    remove_hosts: bool,
) -> None:
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

    caddy_config = CaddyConfig(
        project_dir=str(project_dir),
        domain=domain or "dynadock.lan",
        enable_tls=enable_tls,
    )
    dns_manager = DnsManager(project_dir, domain or "dynadock.lan")

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), console=console
    ) as progress:
        task = progress.add_task("Stopping services…", total=5)
        progress.update(task, advance=1, description="Stopping application containers…")
        docker_manager.down(remove_volumes=remove_volumes, remove_images=remove_images)
        progress.update(task, advance=1, description="Stopping Caddy reverse-proxy…")
        caddy_config.stop_caddy()
        progress.update(task, advance=1, description="Stopping local DNS resolver…")
        try:
            dns_manager.stop_dns()
        except Exception:
            console.print(
                "[yellow]Warning: Could not stop local DNS resolver.[/yellow]"
            )
        progress.update(task, advance=1, description="Tearing down networks…")
        try:
            if domain:
                network_manager.teardown_interfaces(domain)
        except subprocess.CalledProcessError as e:
            console.print(
                "\n[bold yellow]Warning: Could not tear down virtual network interfaces.[/bold yellow]"
            )
            console.print(f"[yellow]  Command: {' '.join(e.cmd)}[/yellow]")
            console.print(f"[yellow]  Exit Code: {e.returncode}[/yellow]")
            console.print(
                f"[yellow]  Stderr: {e.stderr.decode().strip() if e.stderr else 'N/A'}[/yellow]"
            )
            console.print(
                "[dim]  This may happen if the 'up' command failed prematurely. Manual cleanup may be required.[/dim]"
            )
        except FileNotFoundError:
            console.print(
                "\n[bold red]Error: 'manage_veth.sh' script not found.[/bold red]"
            )
            console.print(
                "[dim]  Please ensure the 'scripts' directory is in the project root.[/dim]"
            )

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
                console.print(
                    "[yellow]Warning: Could not remove /etc/hosts entries[/yellow]"
                )
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
    display_running_services(
        ports, domain_val or "dynadock.lan", enable_tls_val, status_map
    )


@cli.command()
@click.pass_context
def logs(ctx: click.Context) -> None:  # noqa: D401
    """Tail logs from all services (docker-compose logs -f)."""
    compose_file = ctx.obj["compose_file"]


@cli.command(name="net-diagnose")
@click.option(
    "--domain", "-d", default="dynadock.lan", help="Base domain for sub-domains."
)
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
@click.option(
    "--domain", "-d", default="dynadock.lan", help="Base domain for sub-domains."
)
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
@click.option(
    "--interface", "-i", help="Network interface (auto-detected if not specified)"
)
@click.option(
    "--num-ips", "-n", default=3, help="Number of test IPs to create", type=int
)
@click.option(
    "--port", "-p", default=8000, help="Starting port for test servers", type=int
)
@click.pass_context
def lan_test(ctx: click.Context, interface: str, num_ips: int, port: int) -> None:
    """Test LAN-visible networking functionality (requires sudo)."""
    project_dir: Path = ctx.obj["project_dir"]
    lan_manager = LANNetworkManager(project_dir, interface)

    console.print("[bold cyan]🌐 DynaDock LAN-Visible Networking Test[/bold cyan]")
    console.print("[yellow]⚠️ Requires sudo privileges to create virtual IPs[/yellow]")

    if not lan_manager.check_root_privileges():
        console.print("[red]❌ This command requires sudo privileges[/red]")
        console.print("[dim]Run: sudo dynadock lan-test[/dim]")
        raise click.Abort()

    console.print("[bold blue]📡 Network Analysis[/bold blue]")
    current_ip, network_base, cidr, broadcast = lan_manager.get_network_details()
    if not current_ip or not network_base or not cidr:
        console.print("[red]❌ Could not detect network configuration[/red]")
        raise click.Abort()

    console.print("[bold blue]🔍 Finding Available IPs[/bold blue]")
    available_ips = lan_manager.find_free_ips(network_base, cidr, num_ips)
    if not available_ips:
        console.print("[red]❌ No available IP addresses found[/red]")
        raise click.Abort()
    console.print(f"[green]✅ Found {len(available_ips)} available IPs[/green]")

    test_services: dict[str, dict] = {
        f"test{i+1}": {} for i in range(len(available_ips))
    }
    try:
        service_ips = lan_manager.setup_services_lan(test_services)
    except Exception as e:
        console.print(f"[red]❌ Failed to create LAN-visible IPs: {e}[/red]")
        raise click.Abort()
    if not service_ips:
        console.print("[red]❌ Failed to create LAN-visible IPs[/red]")
        raise click.Abort()

    port_map = {service: port + i for i, service in enumerate(service_ips.keys())}
    console.print("[bold green]✅ LAN-Visible Test Services Created![/bold green]")
    service_urls = lan_manager.get_service_urls(service_ips, port_map)
    for service, url in service_urls.items():
        console.print(f"   🔗 {service}: [link]{url}[/link]")

    console.print("\n[bold blue]🧪 Testing Connectivity[/bold blue]")
    connectivity_results = lan_manager.test_connectivity(service_ips, port_map)
    all_ok = all(connectivity_results.values())
    if all_ok:
        console.print("\n[bold green]🎉 All test IPs are reachable![/bold green]")
    else:
        console.print(
            "\n[yellow]⚠️ Some IPs are not reachable - check network configuration[/yellow]"
        )

    console.print("\n[yellow]⚠️ Cleaning up test IPs in 5 seconds...[/yellow]")
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        console.print("\n[dim]Cleaning up...[/dim]")
    finally:
        lan_manager.cleanup_all()
        console.print("[green]✓ Test cleanup completed[/green]")


@cli.command(name="check-conflicts")
@click.option(
    "--lan-visible",
    is_flag=True,
    help="Check conflicts for LAN-visible mode (cross-host IP/port)",
)
@click.option(
    "--start-port", "-p", default=8000, type=int, help="Starting port for allocation"
)
@click.option(
    "--network-interface",
    "-i",
    help="Network interface to use for LAN-visible check (auto-detected if not specified)",
)
@click.pass_context
def check_conflicts(
    ctx: click.Context, lan_visible: bool, start_port: int, network_interface: str
) -> None:
    """Dry-run: detect potential IP/port conflicts before 'up' (no IPs are added)."""
    compose_file: str = ctx.obj["compose_file"]
    env_file: str = ctx.obj["env_file"]
    project_dir: Path = ctx.obj["project_dir"]

    docker_manager = DockerManager(compose_file, project_dir, env_file)
    services = docker_manager.parse_compose()
    if not services:
        console.print("[red]No services found in compose file.[/red]")
        raise SystemExit(1)

    allocated_ports = docker_manager.allocate_ports(services, start_port)

    console.print(
        "\n[bold blue]🔎 Checking for potential conflicts (dry-run)...[/bold blue]"
    )

    if lan_visible:
        # LAN-visible: propose candidate IPs without configuring them
        lan_network_manager = LANNetworkManager(project_dir, network_interface)
        current_ip, network_base, cidr, broadcast = (
            lan_network_manager.get_network_details()
        )
        if not network_base or not cidr:
            console.print(
                "[red]Could not detect network details for LAN-visible check.[/red]"
            )
            raise SystemExit(2)

        service_names = list(services.keys())
        needed = len(service_names)
        candidate_ips = lan_network_manager.find_free_ips(network_base, cidr, needed)

        if len(candidate_ips) < needed:
            console.print(
                f"[yellow]Warning: Only found {len(candidate_ips)} candidate IPs for {needed} services.[/yellow]"
            )

        # Map services to candidate IPs (best-effort)
        service_ip_map = {
            svc: candidate_ips[i]
            for i, svc in enumerate(service_names)
            if i < len(candidate_ips)
        }

        if not service_ip_map:
            console.print(
                "[red]No candidate IPs available to check for conflicts.[/red]"
            )
            raise SystemExit(2)

        # Proactively stimulate ARP entries to improve remote MAC detection
        for ip in service_ip_map.values():
            try:
                import subprocess as _sub

                _sub.run(
                    f"ping -c 1 -W 1 {ip}", shell=True, capture_output=True, timeout=2
                )
            except Exception:
                pass  # Ignore ping failures, this is just a best-effort ARP stimulation
        conflicts = lan_network_manager.detect_conflicts(
            service_ip_map, allocated_ports
        )
        if conflicts:
            console.print("\n[bold red]❌ Potential conflicts detected[/bold red]")
            table = Table("Service", "IP (candidate)", "Port", "Issue")
            for svc, info in conflicts.items():
                ip = service_ip_map.get(svc, "-")
                port = allocated_ports.get(svc, 80)
                issues = []
                if info.get("ip_in_use_by_other_host"):
                    mac = info.get("remote_mac", "?")
                    issues.append(f"IP owned by other host (MAC {mac})")
                if info.get("port_in_use_by_other_host"):
                    issues.append("Port in use on other host")
                if info.get("port_open"):
                    issues.append("Port already open at IP")
                table.add_row(svc, ip, str(port), "; ".join(issues) or "Unknown")
            console.print(table)
            console.print(
                "[yellow]Tip: rerun with different start port or ensure other hosts use different IP ranges.[/yellow]"
            )
            raise SystemExit(3)

        console.print("[green]✓ No conflicts detected for LAN-visible mode.[/green]")
        raise SystemExit(0)

    # Non-LAN: check local port availability only (cross-host conflicts not applicable)
    console.print(
        "[dim]LAN-visible flag not provided; checking only local port availability...[/dim]"
    )
    import socket as _socket

    has_conflict = False
    for service, port in allocated_ports.items():
        with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                console.print(
                    f"[red]❌ Port {port} for service '{service}' is already in use.[/red]"
                )
                has_conflict = True
    if has_conflict:
        console.print(
            "[yellow]Tip: Stop the process using the conflicting port(s) or change start port with -p.[/yellow]"
        )
        raise SystemExit(4)

    console.print("[green]✓ No local port conflicts detected.[/green]")
    raise SystemExit(0)


@cli.command(name="check-conflicts")
@click.option(
    "--lan-visible",
    is_flag=True,
    help="Check conflicts for LAN-visible mode (cross-host IP/port)",
)
@click.option(
    "--start-port", "-p", default=8000, type=int, help="Starting port for allocation"
)
@click.option(
    "--network-interface",
    "-i",
    help="Network interface to use for LAN-visible check (auto-detected if not specified)",
)
@click.pass_context
def check_conflicts(
    ctx: click.Context, lan_visible: bool, start_port: int, network_interface: str
) -> None:
    """Dry-run: detect potential IP/port conflicts before 'up' (no IPs are added)."""
    compose_file: str = ctx.obj["compose_file"]
    env_file: str = ctx.obj["env_file"]
    project_dir: Path = ctx.obj["project_dir"]

    docker_manager = DockerManager(compose_file, project_dir, env_file)
    services = docker_manager.parse_compose()
    if not services:
        console.print("[red]No services found in compose file.[/red]")
        raise SystemExit(1)

    allocated_ports = docker_manager.allocate_ports(services, start_port)

    console.print(
        "\n[bold blue]🔎 Checking for potential conflicts (dry-run)...[/bold blue]"
    )

    if lan_visible:
        # LAN-visible: propose candidate IPs without configuring them
        lan_network_manager = LANNetworkManager(project_dir, network_interface)
        current_ip, network_base, cidr, broadcast = (
            lan_network_manager.get_network_details()
        )
        if not network_base or not cidr:
            console.print(
                "[red]Could not detect network details for LAN-visible check.[/red]"
            )
            raise SystemExit(2)

        service_names = list(services.keys())
        needed = len(service_names)
        candidate_ips = lan_network_manager.find_free_ips(network_base, cidr, needed)

        if len(candidate_ips) < needed:
            console.print(
                f"[yellow]Warning: Only found {len(candidate_ips)} candidate IPs for {needed} services.[/yellow]"
            )

        # Map services to candidate IPs (best-effort)
        service_ip_map = {
            svc: candidate_ips[i]
            for i, svc in enumerate(service_names)
            if i < len(candidate_ips)
        }

        if not service_ip_map:
            console.print(
                "[red]No candidate IPs available to check for conflicts.[/red]"
            )
            raise SystemExit(2)

        # Proactively stimulate ARP entries to improve remote MAC detection
        for ip in service_ip_map.values():
            try:
                import subprocess as _sub

                _sub.run(
                    f"ping -c 1 -W 1 {ip}", shell=True, capture_output=True, timeout=2
                )
            except Exception:
                pass  # Ignore ping failures, this is just a best-effort ARP stimulation
        conflicts = lan_network_manager.detect_conflicts(
            service_ip_map, allocated_ports
        )
        if conflicts:
            console.print("\n[bold red]❌ Potential conflicts detected[/bold red]")
            table = Table("Service", "IP (candidate)", "Port", "Issue")
            for svc, info in conflicts.items():
                ip = service_ip_map.get(svc, "-")
                port = allocated_ports.get(svc, 80)
                issues = []
                if info.get("ip_in_use_by_other_host"):
                    mac = info.get("remote_mac", "?")
                    issues.append(f"IP owned by other host (MAC {mac})")
                if info.get("port_in_use_by_other_host"):
                    issues.append("Port in use on other host")
                if info.get("port_open"):
                    issues.append("Port already open at IP")
                table.add_row(svc, ip, str(port), "; ".join(issues) or "Unknown")
            console.print(table)
            console.print(
                "[yellow]Tip: rerun with different start port or ensure other hosts use different IP ranges.[/yellow]"
            )
            raise SystemExit(3)

        console.print("[green]✓ No conflicts detected for LAN-visible mode.[/green]")
        raise SystemExit(0)

    # Non-LAN: check local port availability only (cross-host conflicts not applicable)
    console.print(
        "[dim]LAN-visible flag not provided; checking only local port availability...[/dim]"
    )
    import socket as _socket

    has_conflict = False
    for service, port in allocated_ports.items():
        with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                console.print(
                    f"[red]❌ Port {port} for service '{service}' is already in use.[/red]"
                )
                has_conflict = True
    if has_conflict:
        console.print(
            "[yellow]Tip: Stop the process using the conflicting port(s) or change start port with -p.[/yellow]"
        )
        raise SystemExit(4)

    console.print("[green]✓ No local port conflicts detected.[/green]")
    raise SystemExit(0)


@cli.command()
@click.option(
    "--interval",
    "-i",
    default=5,
    help="Interval in seconds to check services.",
    type=int,
)
@click.option(
    "--expected-text",
    "-t",
    help="Text to expect in the response body for a successful health check.",
)
@click.pass_context
def watch(ctx: click.Context, interval: int, expected_text: str | None) -> None:
    """Continuously monitor the health of running services with enhanced validation."""
    env_file: str = ctx.obj["env_file"]
    project_dir: Path = ctx.obj["project_dir"]

    # Setup screenshot directory for response captures
    screenshot_dir = project_dir / ".dynadock" / "watch_screenshots"
    if screenshot_dir.exists():
        shutil.rmtree(screenshot_dir)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    env_values = dotenv_values(env_file) if Path(env_file).exists() else {}
    if not env_values:
        console.print("[red]No .env.dynadock found. Run `up` first.[/red]")
        raise SystemExit(1)

    domain = env_values.get("DYNADOCK_DOMAIN", "dynadock.lan")
    enable_tls_str = env_values.get("DYNADOCK_ENABLE_TLS", "false")
    enable_tls = bool(enable_tls_str and enable_tls_str.lower() == "true")
    protocol = "https" if enable_tls else "http"

    docker_manager = DockerManager(ctx.obj["compose_file"], project_dir, env_file)
    services_config = docker_manager.parse_compose()

    ports: Dict[str, int] = {}
    for key, val in env_values.items():
        if key.endswith("_PORT") and val:
            try:
                ports[key[:-5].lower()] = int(val)
            except (ValueError, TypeError):
                pass

    def get_service_urls() -> Dict[str, str]:
        urls = {}
        for service, port in ports.items():
            service_config = services_config.get(service, {})
            raw_labels = service_config.get("labels", [])
            labels = {}
            if isinstance(raw_labels, list):
                for label_str in raw_labels:
                    if "=" in label_str:
                        k, v = label_str.split("=", 1)
                        labels[k] = v
            elif isinstance(raw_labels, dict):
                labels = raw_labels

            if labels.get("dynadock.protocol") == "http":
                urls[service] = f"{protocol}://{service}.{domain}"
        return urls

    service_urls = get_service_urls()
    if not service_urls:
        console.print("[yellow]No HTTP services found to monitor.[/yellow]")
        return

    def test_url_with_content_check(url: str, service: str) -> Tuple[bool, str]:
        """Test URL and optionally validate content. Return (is_healthy, status_msg)"""
        try:
            cmd = ["curl", "-s", "-k", "--connect-timeout", "2", "-m", "4", url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                return False, "Connection failed"

            # Check HTTP status via separate curl call
            status_cmd = [
                "curl",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "-k",
                "--connect-timeout",
                "2",
                "-m",
                "4",
                url,
            ]
            status_result = subprocess.run(
                status_cmd, capture_output=True, text=True, timeout=5
            )

            if status_result.returncode != 0:
                return False, "Status check failed"

            http_code = status_result.stdout.strip()
            if not (http_code.isdigit() and 200 <= int(http_code) < 300):
                return False, f"HTTP {http_code}"

            # Content validation if expected text is provided
            if expected_text:
                response_content = result.stdout
                if expected_text not in response_content:
                    # Save screenshot of response content
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    screenshot_file = (
                        screenshot_dir / f"{service}_{timestamp}_content_mismatch.txt"
                    )
                    with open(screenshot_file, "w") as f:
                        f.write(f"URL: {url}\n")
                        f.write(f"Expected text: {expected_text}\n")
                        f.write(f"HTTP Status: {http_code}\n")
                        f.write(f"Response content:\n{response_content}")

                    return (
                        False,
                        f"Missing expected text, saved to {screenshot_file.name}",
                    )

            return True, "Healthy"

        except Exception as e:
            return False, f"Error: {str(e)}"

    def generate_table() -> Table:
        table = Table(title="DynaDock Service Health Monitor")
        table.add_column("Service", justify="left", style="cyan", no_wrap=True)
        table.add_column("URL", style="magenta")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        table.add_column("Timestamp", justify="right", style="green")

        for service, url in service_urls.items():
            is_healthy, details = test_url_with_content_check(url, service)
            status_icon = (
                "[green]✅ Healthy[/green]" if is_healthy else "[red]❌ Unhealthy[/red]"
            )
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            table.add_row(service, url, status_icon, details, timestamp)

        return table

    try:
        console.print(
            f"[bold cyan]🔍 Starting health monitoring (interval: {interval}s)[/bold cyan]"
        )
        if expected_text:
            console.print(
                f"[dim]Validating response content for text: '{expected_text}'[/dim]"
            )
        console.print(f"[dim]Screenshots saved to: {screenshot_dir}[/dim]\n")

        with Live(
            generate_table(), console=console, screen=True, auto_refresh=False
        ) as live:
            while True:
                time.sleep(interval)
                live.update(generate_table(), refresh=True)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopping service monitor...[/dim]")

        # Cleanup old screenshots (keep only last 10)
        screenshot_files = sorted(
            screenshot_dir.glob("*.txt"), key=lambda x: x.stat().st_mtime, reverse=True
        )
        for old_file in screenshot_files[10:]:
            old_file.unlink()

        if screenshot_files:
            console.print(
                f"[dim]Kept {min(len(screenshot_files), 10)} most recent screenshots in {screenshot_dir}[/dim]"
            )

#!/usr/bin/env python3
"""
Domain verification helper functions for DynaDock CLI
"""

import subprocess
import time
import shutil
from typing import Dict, Any, Tuple, List
from rich.console import Console

console = Console()


def verify_domain_access(
    services_config: Dict[str, Any],
    allocated_ports: Dict[str, int],
    domain: str,
    enable_tls: bool = True,
    retries: int = 3,
    initial_wait: float = 1.0,
    ip_map: Dict[str, str] | None = None
) -> Tuple[bool, Dict[str, Dict[str, bool]]]:
    """
    Verify if services are accessible both via localhost port and domain.
    Returns (all_ok, results_dict)
    """
    console.print("\n[bold cyan]Verifying service accessibility...[/bold cyan]")
    time.sleep(initial_wait)

    results = {}

    for attempt in range(retries):
        all_services_ok = True
        for service, port in allocated_ports.items():
            service_config = services_config.get(service, {})
            raw_labels = service_config.get('labels', [])

            # Normalize labels to always be a dictionary, as docker-compose can have a list or a map
            labels = {}
            if isinstance(raw_labels, list):
                for label_str in raw_labels:
                    if '=' in label_str:
                        key, value = label_str.split('=', 1)
                        labels[key] = value
            elif isinstance(raw_labels, dict):
                labels = raw_labels

            # Skip services that are not explicitly marked as HTTP
            if labels.get('dynadock.protocol') != 'http':
                continue

            if results.get(service, {}).get("domain") or results.get(service, {}).get("localhost"):
                continue  # Skip already verified services

            console.print(f"\n[blue]Testing {service} (Attempt {attempt + 1}/{retries}):[/blue]")

            # Test localhost access
            localhost_url = f"http://localhost:{port}"
            localhost_ok = test_url_with_curl(localhost_url, service, "localhost")

            # Test domain access
            domain_scheme = "https" if enable_tls else "http"
            domain_url = f"{domain_scheme}://{service}.{domain}"
            domain_ok = test_url_with_curl(domain_url, service, "domain")

            if not domain_ok and not localhost_ok:
                all_services_ok = False

            results[service] = {"localhost": localhost_ok, "domain": domain_ok}

        if all_services_ok:
            break
        if attempt < retries - 1:
            console.print(f"\n[yellow]Retrying in {initial_wait} seconds...[/yellow]")
            time.sleep(initial_wait)

    all_ok = all((v.get("domain") or v.get("localhost")) for v in results.values())
    console.print("\n[dim]Verification complete.[/dim]")

    # Suggest /etc/hosts entries if domain fails but localhost works
    _suggest_hosts_entries(results, ip_map, domain, all_ok)

    return all_ok, results


def test_url_with_curl(url: str, service: str, access_type: str) -> bool:
    """Test if a URL is accessible using curl."""
    try:
        if access_type == "localhost":
            time.sleep(1)
        
        cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-k", 
               "--connect-timeout", "3", "-m", "5", url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
        
        if result.returncode == 0:
            http_code = result.stdout.strip()
            if http_code and http_code != "000" and int(http_code) < 500:
                if access_type == "localhost":
                    port = url.split(':')[-1]
                    console.print(f"  [green]✓[/green] {service}: [green]localhost:{port} is accessible (HTTP {http_code})[/green]")
                else:
                    console.print(f"  [green]✓[/green] {service}: [green]{url} is accessible (HTTP {http_code})[/green]")
                return True
            else:
                if access_type == "localhost":
                    port = url.split(':')[-1]
                    console.print(f"  [yellow]⚠[/yellow] {service}: [yellow]localhost:{port} returned HTTP {http_code}[/yellow]")
                elif access_type == "domain":
                    return False
        else:
            if access_type == "domain":
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


def _suggest_hosts_entries(results: Dict, ip_map: Dict[str, str] | None, domain: str, all_ok: bool):
    """Suggest /etc/hosts entries if needed"""
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

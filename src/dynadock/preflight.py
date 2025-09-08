from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Tuple

from pathlib import Path

__all__ = ["PreflightChecker", "PreflightReport"]

logger = logging.getLogger(__name__)


@dataclass
class PreflightReport:
    ok: bool
    warnings: List[str]
    errors: List[str]
    suggestions: List[str]

    def pretty(self) -> str:
        lines: List[str] = []
        if self.errors:
            lines.append("[red]Errors:[/red]")
            lines += [f"  - {e}" for e in self.errors]
        if self.warnings:
            lines.append("[yellow]Warnings:[/yellow]")
            lines += [f"  - {w}" for w in self.warnings]
        if self.suggestions:
            lines.append("[cyan]Suggestions:[/cyan]")
            lines += [f"  - {s}" for s in self.suggestions]
        if not (self.errors or self.warnings or self.suggestions):
            lines.append("All preflight checks passed.")
        return "\n".join(lines)


def _port_in_use(port: int, proto: str = "tcp") -> Tuple[bool, str]:
    # Try ss first
    try:
        flags = "-ltnp" if proto == "tcp" else "-lunp"
        p = subprocess.run(["ss", flags], capture_output=True, text=True, check=False)
        if p.returncode == 0 and str(port) in p.stdout:
            return True, p.stdout
    except FileNotFoundError:
        pass
    # Fallback to lsof
    try:
        p2 = subprocess.run(["lsof", f"-i:{port}"], capture_output=True, text=True, check=False)
        if p2.returncode == 0 and p2.stdout.strip():
            return True, p2.stdout
    except FileNotFoundError:
        pass
    return False, ""


class PreflightChecker:
    """Environment checks before running dynadock up."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir)
        logger.info("PreflightChecker initialized")

    def run(self) -> PreflightReport:
        warnings: List[str] = []
        errors: List[str] = []
        suggestions: List[str] = []

        logger.info("Running preflight checks...")

        # Binaries
        for bin_name in ("docker", "ip", "curl"):
            if shutil.which(bin_name) is None:
                errors.append(f"Required binary not found: {bin_name}")
                suggestions.append(f"Install {bin_name} and ensure it's on PATH")

        # docker-compose or docker compose plugin
        compose_ok = False
        if shutil.which("docker-compose") is not None:
            compose_ok = True
        elif shutil.which("docker") is not None:
            try:
                subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
                compose_ok = True
            except Exception:
                pass
        if not compose_ok:
            errors.append("Neither docker-compose nor 'docker compose' plugin is available")
            suggestions.append("Install docker-compose or Docker Compose plugin (e.g. 'docker compose')")

        # Optional: resolvectl
        if shutil.which("resolvectl") is None:
            warnings.append("systemd-resolved (resolvectl) not found – DNS stub domain may not be configured automatically.")
            suggestions.append("Consider installing or enable fallback via --manage-hosts")

        # Docker accessibility
        if shutil.which("docker") is not None:
            p = subprocess.run(["docker", "ps"], capture_output=True, text=True, check=False)
            if p.returncode != 0:
                errors.append("Cannot communicate with Docker daemon (docker ps failed)")
                suggestions.append("Ensure your user is in the 'docker' group or Docker is running")

        # Passwordless sudo (for veth and DNS setup)
        logger.info("Checking for passwordless sudo...")
        try:
            sp = subprocess.run(["sudo", "-n", "true"], check=False)
            if sp.returncode != 0:
                errors.append("Passwordless sudo is required for network setup. It is not available.")
                suggestions.append("To enable, run 'sudo visudo' and add the following line, replacing 'your_username' with your actual username:")
                suggestions.append("    your_username ALL=(ALL) NOPASSWD: /usr/bin/ip, /usr/bin/python3")
                suggestions.append("Alternatively, use the --manage-hosts flag to run without virtual networking.")
            else:
                logger.info("✅ Passwordless sudo is available.")
        except Exception:
            warnings.append("Sudo not available – some features will be degraded (no veth/DNS). Use --manage-hosts fallback.")

        # Ports
        logger.info("Checking for port conflicts...")
        # ss/lsof availability note
        if shutil.which("ss") is None and shutil.which("lsof") is None:
            warnings.append("Neither 'ss' nor 'lsof' found – port usage checks may be unreliable.")
            suggestions.append("Install 'ss' (iproute2) or 'lsof' to enable better port diagnostics.")

        for port in (80, 443, 53):
            logger.debug(f"Checking port {port}...")
            in_use, detail = _port_in_use(port, "tcp" if port != 53 else "udp")
            if in_use:
                warnings.append(f"Port {port} appears to be in use.")
                if detail:
                    suggestions.append(f"Check processes using port {port}:")
                    suggestions.extend([f"    {line}" for line in detail.splitlines()[:5]])
                if port in (80, 443):
                    suggestions.append("Use 'make free-port-80' or stop the conflicting process/container.")
                if port == 53:
                    suggestions.append("Port 53 conflict prevents local DNS – Dynadock will fallback to --manage-hosts.")

        logger.info("Preflight checks completed.")
        return PreflightReport(ok=not errors, warnings=warnings, errors=errors, suggestions=suggestions)

    def try_autofix(self) -> List[str]:
        actions: List[str] = []
        # Remove stale dynadock containers if present
        for name in ("dynadock-caddy", "dynadock-dns"):
            try:
                subprocess.run(["docker", "rm", "-f", name], check=False, capture_output=True)
                actions.append(f"Ensured container '{name}' is not running")
            except Exception:
                pass
        # Flush resolved cache
        if shutil.which("resolvectl") is not None:
            subprocess.run(["sudo", "resolvectl", "flush-caches"], check=False)
            actions.append("Flushed systemd-resolved DNS cache")
        return actions

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict

import docker

__all__ = ["DnsManager"]


class DnsManager:
    """Manage a local DNS resolver (dnsmasq) for *.domain to service IPs.

    Strategy:
    - Generate a dnsmasq config mapping service FQDNs to their allocated IPs
      using lines of the form: address=/service.domain/172.20.0.10
    - Run a dnsmasq container listening on 127.0.0.1:5353 TCP/UDP
    - Configure systemd-resolved to route ~<domain> to 127.0.0.1
    - Teardown on down
    """

    _CONTAINER_NAME = "dynadock-dns"

    def __init__(self, project_dir: Path, domain: str) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.domain = domain
        self.dns_dir = self.project_dir / ".dynadock" / "dns"
        self.dns_dir.mkdir(parents=True, exist_ok=True)
        self.conf_path = self.dns_dir / "dynadock.conf"
        self.client = docker.from_env()

    def _write_config(self, ip_map: Dict[str, str]) -> None:
        lines = []
        for service, ip in sorted(ip_map.items()):
            fqdn = f"{service}.{self.domain}"
            lines.append(f"address=/{fqdn}/{ip}\n")
        with self.conf_path.open("w", encoding="utf-8") as fp:
            fp.writelines(lines)

    def is_running(self) -> bool:
        try:
            container = self.client.containers.get(self._CONTAINER_NAME)
            return container.status == "running"
        except docker.errors.NotFound:
            return False

    def start_dns(self, ip_map: Dict[str, str]) -> None:
        """Start dnsmasq and configure systemd-resolved stub domain."""
        self._write_config(ip_map)

        # Ensure no stale container exists
        self.stop_dns(remove=True)

        # Run dnsmasq container listening only on localhost:5353 (TCP/UDP)
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            self._CONTAINER_NAME,
            "-p",
            "127.0.0.1:5353:53/udp",
            "-p",
            "127.0.0.1:5353:53/tcp",
            "-v",
            f"{self.conf_path}:/etc/dnsmasq.d/dynadock.conf:ro",
            "--cap-add",
            "NET_ADMIN",
            "--restart",
            "unless-stopped",
            "andyshinn/dnsmasq:2.86",
            "-k",
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # Configure systemd-resolved stub domain to forward ~domain to 127.0.0.1
        # These may fail on systems without systemd-resolved; ignore errors but print hints
        subprocess.run(["sudo", "resolvectl", "dns", "lo", "127.0.0.1"], check=False)
        subprocess.run(["sudo", "resolvectl", "domain", "lo", f"~{self.domain}"], check=False)

    def reload_dns(self) -> None:
        if not self.is_running():
            return
        try:
            subprocess.run(["docker", "exec", self._CONTAINER_NAME, "kill", "-HUP", "1"], check=True)
        except subprocess.CalledProcessError:
            # Fallback: restart container
            subprocess.run(["docker", "restart", self._CONTAINER_NAME], check=False)

    def stop_dns(self, remove: bool = True) -> None:
        """Stop dns and revert resolved config."""
        try:
            container = self.client.containers.get(self._CONTAINER_NAME)
            container.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Revert stub domain on loopback if possible
        subprocess.run(["sudo", "resolvectl", "revert", "lo"], check=False)

        if remove and self.conf_path.exists():
            try:
                self.conf_path.unlink()
            except OSError:
                pass

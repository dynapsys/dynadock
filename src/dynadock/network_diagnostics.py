from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Tuple, List

import docker

from .dns_manager import DnsManager

__all__ = ["NetworkDiagnostics"]


def _run(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, check=False)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {' '.join(cmd)}"


class NetworkDiagnostics:
    """Diagnose and attempt repair of Dynadock virtual networking and DNS."""

    _IP_MAP_FILE = ".dynadock_ip_map.json"

    def __init__(self, project_dir: Path, domain: str) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.domain = domain
        self.ip_map_path = self.project_dir / self._IP_MAP_FILE
        self.client = docker.from_env()

    def _load_ip_map(self) -> Dict[str, str]:
        if not self.ip_map_path.exists():
            return {}
        try:
            return json.loads(self.ip_map_path.read_text())
        except json.JSONDecodeError:
            return {}

    def diagnose(self) -> str:
        lines: List[str] = []
        lines.append("[bold]Dynadock Network Diagnostics[/bold]")
        lines.append("")

        # 1) IP map
        ip_map = self._load_ip_map()
        if ip_map:
            lines.append(f"- IP map: found {len(ip_map)} entries at {self.ip_map_path}")
        else:
            lines.append(f"- IP map: [red]missing[/red] at {self.ip_map_path}")

        # 2) Virtual interfaces
        rc, out, err = _run(["ip", "link", "show"])
        if rc == 0:
            count = sum(1 for line in out.splitlines() if "dynadock-" in line)
            lines.append(f"- Virtual interfaces: found {count} matching 'dynadock-*'")
        else:
            lines.append(f"- Virtual interfaces: [yellow]cannot check[/yellow] ({err or 'ip not available'})")

        # 3) DNS container
        try:
            container = self.client.containers.get("dynadock-dns")
            lines.append(f"- DNS container: {container.status}")
        except docker.errors.NotFound:
            lines.append("- DNS container: [red]not found[/red]")
        except Exception as e:  # noqa: BLE001
            lines.append(f"- DNS container: [yellow]error[/yellow] ({e})")

        # 4) systemd-resolved stub domain
        rc, out, err = _run(["resolvectl", "status", "lo"])
        if rc == 0:
            domain_ok = f"~{self.domain}" in out
            dns_ok = "127.0.0.1" in out
            lines.append(f"- systemd-resolved stub (~{self.domain}): {'OK' if domain_ok and dns_ok else '[red]MISSING[/red]'}")
        else:
            lines.append("- systemd-resolved: [yellow]not available[/yellow] (non-systemd or command missing)")

        # 5) Name resolution check
        test_host = None
        if ip_map:
            test_host = f"{sorted(ip_map.keys())[0]}.{self.domain}"
            rc, out, err = _run(["getent", "hosts", test_host])
            if rc == 0 and out:
                lines.append(f"- getent hosts {test_host}: OK ({out.split()[0]})")
            else:
                lines.append(f"- getent hosts {test_host}: [red]FAILED[/red]")
        else:
            lines.append("- Skipping getent check: no IP map")

        # 6) HTTP check via curl (domain)
        if test_host:
            rc, out, err = _run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "-k", f"https://{test_host}"])
            if rc == 0 and out and out != "000":
                lines.append(f"- curl https://{test_host}: HTTP {out}")
            else:
                # Try HTTP fallback
                rc2, out2, err2 = _run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", f"http://{test_host}"])
                if rc2 == 0 and out2 and out2 != "000":
                    lines.append(f"- curl http://{test_host}: HTTP {out2}")
                else:
                    lines.append(f"- curl domain {test_host}: [red]FAILED[/red]")

        return "\n".join(lines)

    def repair(self) -> str:
        lines: List[str] = []
        lines.append("[bold]Dynadock Network Auto-Repair[/bold]")
        ip_map = self._load_ip_map()

        # Re-apply systemd-resolved stub domain
        rc1, out1, err1 = _run(["sudo", "resolvectl", "dns", "lo", "127.0.0.1"])
        rc2, out2, err2 = _run(["sudo", "resolvectl", "domain", "lo", f"~{self.domain}"])
        if rc1 == 0 and rc2 == 0:
            lines.append("- systemd-resolved: stub domain configured for loopback")
        else:
            lines.append("- systemd-resolved: could not configure (non-systemd or permission)")

        # Ensure DNS container is running
        try:
            dns = DnsManager(self.project_dir, self.domain)
            if ip_map:
                dns.start_dns(ip_map)
                lines.append("- DNS: started/reloaded dnsmasq container")
            else:
                lines.append("- DNS: no ip_map – skipped")
        except Exception as e:  # noqa: BLE001
            lines.append(f"- DNS: failed to start ({e})")

        # Try to re-create virtual interfaces from ip_map
        repo_root = Path(__file__).resolve().parents[2]
        manage_veth = (repo_root / "scripts" / "manage_veth.sh").resolve()
        if manage_veth.exists() and ip_map:
            rc, out, err = _run(["sudo", str(manage_veth), "up", str(self.ip_map_path)])
            if rc == 0:
                lines.append("- Virtual interfaces: ensured up")
            else:
                lines.append(f"- Virtual interfaces: failed to ensure up (rc={rc})")
        else:
            lines.append("- Virtual interfaces: skipped (no script or no ip_map)")

        lines.append("")
        lines.append("Run `net-diagnose` again to verify.")
        return "\n".join(lines)

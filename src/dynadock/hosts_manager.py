from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict

__all__ = ["HostsManager"]


class HostsManager:
    """Safely manage /etc/hosts entries for DynaDock as a fallback.

    Adds a domain-scoped block between markers to avoid clobbering user edits.
    """

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir)
        self.marker_start = "# BEGIN DYNADOCK HOSTS"
        self.marker_end = "# END DYNADOCK HOSTS"

    def _build_block(self, ip_map: Dict[str, str], domain: str) -> str:
        lines = [self.marker_start]
        for service, ip in sorted(ip_map.items()):
            lines.append(f"{ip}\t{service}.{domain}")
        lines.append(self.marker_end)
        return "\n".join(lines) + "\n"

    def apply(self, ip_map: Dict[str, str], domain: str) -> None:
        """Insert or replace the dynadock block in /etc/hosts using sudo."""
        block_file = self.project_dir / ".dynadock_hosts_block.tmp"
        block_file.write_text(self._build_block(ip_map, domain), encoding="utf-8")
        sed_script_remove = r"/^# BEGIN DYNADOCK HOSTS$/,/^# END DYNADOCK HOSTS$/d"
        script = f"set -e; sed -i.bak '{sed_script_remove}' /etc/hosts; cat '{block_file}' >> /etc/hosts"
        try:
            subprocess.run(["sudo", "bash", "-c", script], check=True)
        finally:
            try:
                block_file.unlink()
            except OSError:
                pass

    def remove(self) -> None:
        sed_script_remove = r"/^# BEGIN DYNADOCK HOSTS$/,/^# END DYNADOCK HOSTS$/d"
        script = f"set -e; sed -i.bak '{sed_script_remove}' /etc/hosts"
        subprocess.run(["sudo", "bash", "-c", script], check=False)

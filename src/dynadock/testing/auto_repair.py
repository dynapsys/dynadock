#!/usr/bin/env python3
"""
Auto-repair functionality for DynaDock issues
"""

import subprocess
from typing import List


def auto_repair_issues(issues: List[str]) -> List[str]:
    """Attempt to automatically repair common issues"""
    repairs_attempted = []

    for issue in issues:
        if "container" in issue.lower() and "not running" in issue.lower():
            repair_result = _start_containers()
            repairs_attempted.append(repair_result)

        elif "caddy" in issue.lower() and "not" in issue.lower():
            repair_result = _start_caddy()
            repairs_attempted.append(repair_result)

        elif "port" in issue.lower() and ("443" in issue or "80" in issue):
            repair_result = _check_port_conflicts()
            repairs_attempted.append(repair_result)

    return repairs_attempted


def _start_containers() -> str:
    """Try to start Docker containers"""
    try:
        subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd="/home/tom/github/dynapsys/dynadock/examples/fullstack",
            timeout=30,
            check=True,
            capture_output=True,
        )
        return "✅ Started Docker containers"
    except subprocess.CalledProcessError as e:
        return f"❌ Failed to start containers: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return f"❌ Failed to start containers: {e}"


def _start_caddy() -> str:
    """Try to start Caddy container"""
    try:
        # First stop existing Caddy if running
        subprocess.run(
            ["docker", "stop", "dynadock-caddy"], capture_output=True, timeout=10
        )
        subprocess.run(
            ["docker", "rm", "dynadock-caddy"], capture_output=True, timeout=10
        )

        # Start new Caddy container
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                "dynadock-caddy",
                "-p",
                "80:80",
                "-p",
                "443:443",
                "-v",
                "/home/tom/github/dynapsys/dynadock/examples/fullstack/.dynadock/caddy:/etc/caddy",
                "-v",
                "/home/tom/github/dynapsys/dynadock/certs:/etc/caddy/certs:ro",
                "caddy:2-alpine",
                "caddy",
                "run",
                "--config",
                "/etc/caddy/working.conf",
            ],
            timeout=30,
            check=True,
            capture_output=True,
        )
        return "✅ Started Caddy container"
    except subprocess.CalledProcessError as e:
        return f"❌ Failed to start Caddy: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return f"❌ Failed to start Caddy: {e}"


def _check_port_conflicts() -> str:
    """Check for port conflicts"""
    try:
        result = subprocess.run(
            ["netstat", "-tlnp"], capture_output=True, text=True, timeout=10
        )

        port_80_used = ":80 " in result.stdout
        port_443_used = ":443 " in result.stdout

        conflicts = []
        if port_80_used:
            conflicts.append("80")
        if port_443_used:
            conflicts.append("443")

        if conflicts:
            return f"⚠️  Port conflicts detected on: {', '.join(conflicts)}"
        else:
            return "✅ No port conflicts found"

    except Exception as e:
        return f"❌ Failed to check port conflicts: {e}"


def repair_hosts_file() -> str:
    """Add missing /etc/hosts entries"""
    try:
        hosts_entries = [
            "127.0.0.1 frontend.dynadock.lan",
            "127.0.0.1 backend.dynadock.lan",
            "127.0.0.1 mailhog.dynadock.lan",
            "127.0.0.1 postgres.dynadock.lan",
            "127.0.0.1 redis.dynadock.lan",
        ]

        # Check current hosts file
        with open("/etc/hosts", "r") as f:
            current_content = f.read()

        missing_entries = []
        for entry in hosts_entries:
            if entry.split()[1] not in current_content:
                missing_entries.append(entry)

        if missing_entries:
            return f"⚠️  Missing hosts entries: {len(missing_entries)} entries need to be added manually"
        else:
            return "✅ All required hosts entries present"

    except Exception as e:
        return f"❌ Failed to check hosts file: {e}"

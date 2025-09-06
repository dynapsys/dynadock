import types
from pathlib import Path

import pytest

from dynadock.preflight import PreflightChecker

pytestmark = pytest.mark.unit


class DummyProc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _mk_which(mapping: dict[str, str | None]):
    def _which(name: str):
        return mapping.get(name)
    return _which


def test_preflight_binaries_missing(monkeypatch, tmp_path: Path):
    # No required binaries present
    monkeypatch.setattr("dynadock.preflight.shutil.which", _mk_which({}))

    # subprocess.run should simulate missing 'ss' and 'lsof' (raise FileNotFoundError)
    def fake_run(args, *_, **__):
        prog = args[0]
        if prog in {"ss", "lsof"}:
            raise FileNotFoundError()
        if prog == "sudo":
            # Simulate sudo not available producing exception in try/except
            raise RuntimeError("sudo not available")
        return DummyProc(1, "", "")

    monkeypatch.setattr("dynadock.preflight.subprocess.run", fake_run)

    report = PreflightChecker(tmp_path).run()

    # Expect errors for each missing required binary + compose missing
    assert any("Required binary not found: docker" in e for e in report.errors)
    assert any("Required binary not found: ip" in e for e in report.errors)
    assert any("Required binary not found: curl" in e for e in report.errors)
    assert any("Neither docker-compose nor 'docker compose' plugin is available" in e for e in report.errors)

    # Warnings for no resolvectl, no ss/lsof, and sudo not available
    assert any("resolvectl" in w for w in report.warnings)
    assert any("Neither 'ss' nor 'lsof' found" in w for w in report.warnings)
    assert any("Sudo not available" in w for w in report.warnings)

    assert report.ok is False


def test_preflight_compose_plugin_ok(monkeypatch, tmp_path: Path):
    # docker, ip, curl, resolvectl, ss available; docker-compose not installed
    monkeypatch.setattr(
        "dynadock.preflight.shutil.which",
        _mk_which({
            "docker": "/usr/bin/docker",
            "ip": "/usr/sbin/ip",
            "curl": "/usr/bin/curl",
            "resolvectl": "/usr/bin/resolvectl",
            "ss": "/usr/sbin/ss",
            # docker-compose intentionally None -> plugin path used
        }),
    )

    def fake_run(args, *_, **__):
        # docker compose version succeeds
        if args[:3] == ["docker", "compose", "version"]:
            return DummyProc(0, "Docker Compose version v2.24.0")
        # docker ps succeeds
        if args[:2] == ["docker", "ps"]:
            return DummyProc(0, "")
        # sudo -n true succeeds
        if args[:3] == ["sudo", "-n", "true"]:
            return DummyProc(0, "")
        # ss checks -> no ports in use
        if args[0] == "ss":
            return DummyProc(0, "")
        return DummyProc(0, "")

    monkeypatch.setattr("dynadock.preflight.subprocess.run", fake_run)

    report = PreflightChecker(tmp_path).run()

    assert report.errors == []
    # No warnings expected in the happy path
    assert report.ok is True


def test_preflight_docker_inaccessible(monkeypatch, tmp_path: Path):
    # Binaries present so we get to docker ps check
    monkeypatch.setattr(
        "dynadock.preflight.shutil.which",
        _mk_which({
            "docker": "/usr/bin/docker",
            "ip": "/usr/sbin/ip",
            "curl": "/usr/bin/curl",
            "resolvectl": "/usr/bin/resolvectl",
            "ss": "/usr/sbin/ss",
        }),
    )

    def fake_run(args, *_, **__):
        if args[:3] == ["docker", "compose", "version"]:
            return DummyProc(0, "Docker Compose version v2.24.0")
        if args[:2] == ["docker", "ps"]:
            return DummyProc(1, "", "Cannot connect to the Docker daemon")
        if args[:3] == ["sudo", "-n", "true"]:
            return DummyProc(0, "")
        if args[0] == "ss":
            return DummyProc(0, "")
        return DummyProc(0, "")

    monkeypatch.setattr("dynadock.preflight.subprocess.run", fake_run)

    report = PreflightChecker(tmp_path).run()

    assert any("Cannot communicate with Docker daemon" in e for e in report.errors)
    assert report.ok is False


def test_preflight_ports_in_use(monkeypatch, tmp_path: Path):
    # All binaries present
    monkeypatch.setattr(
        "dynadock.preflight.shutil.which",
        _mk_which({
            "docker": "/usr/bin/docker",
            "ip": "/usr/sbin/ip",
            "curl": "/usr/bin/curl",
            "resolvectl": "/usr/bin/resolvectl",
            "ss": "/usr/sbin/ss",
        }),
    )

    def fake_run(args, *_, **__):
        if args[:3] == ["docker", "compose", "version"]:
            return DummyProc(0, "Docker Compose version v2.24.0")
        if args[:2] == ["docker", "ps"]:
            return DummyProc(0, "")
        if args[:3] == ["sudo", "-n", "true"]:
            return DummyProc(0, "")
        if args[0] == "ss":
            # args[1] is flags: -ltnp (tcp) or -lunp (udp)
            flags = args[1]
            if "-ltnp" in flags:
                # Simulate port 80 in use, but not 443
                return DummyProc(0, "LISTEN 0 128 *:80 *:* users:(\"nginx\")")
            else:
                # UDP check -> port 53 in use
                return DummyProc(0, "UNCONN 0 0 *:53 *:* users:(\"dnsmasq\")")
        return DummyProc(0, "")

    monkeypatch.setattr("dynadock.preflight.subprocess.run", fake_run)

    report = PreflightChecker(tmp_path).run()

    # Expect warnings for port 80 and 53, but not 443
    assert any("Port 80 appears to be in use" in w for w in report.warnings)
    assert any("Port 53 appears to be in use" in w for w in report.warnings)
    assert not any("Port 443 appears to be in use" in w for w in report.warnings)

    # And suggestions include free-port-80 and hosts fallback message
    assert any("free-port-80" in s for s in report.suggestions)
    assert any("Port 53 conflict prevents local DNS" in s for s in report.suggestions)


def test_try_autofix_actions(monkeypatch, tmp_path: Path):
    # resolvectl available to trigger DNS cache flush action
    monkeypatch.setattr(
        "dynadock.preflight.shutil.which",
        _mk_which({"resolvectl": "/usr/bin/resolvectl"}),
    )

    calls: list[list[str]] = []

    def fake_run(args, *_, **__):
        calls.append(list(args))
        return DummyProc(0, "")

    monkeypatch.setattr("dynadock.preflight.subprocess.run", fake_run)

    actions = PreflightChecker(tmp_path).try_autofix()

    assert "Ensured container 'dynadock-caddy' is not running" in actions
    assert "Ensured container 'dynadock-dns' is not running" in actions
    assert "Flushed systemd-resolved DNS cache" in actions

    # Ensure docker rm and resolvectl were attempted
    assert any(c[:3] == ["docker", "rm", "-f"] for c in calls)
    assert any(c[:2] == ["sudo", "resolvectl"] for c in calls)

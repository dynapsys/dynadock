from pathlib import Path
from typing import Dict

import pytest

from dynadock.hosts_manager import HostsManager

pytestmark = pytest.mark.unit


class DummyProc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_build_block_formatting(tmp_path: Path):
    hm = HostsManager(tmp_path)
    ip_map: Dict[str, str] = {"api": "172.20.0.10", "web": "172.20.0.11", "db": "172.20.0.12"}

    # Intentionally unsorted keys to verify sorting by service name
    ip_map_unsorted = {"web": ip_map["web"], "db": ip_map["db"], "api": ip_map["api"]}

    block = hm._build_block(ip_map_unsorted, domain="dynadock.lan")

    # Block should contain markers and sorted entries
    lines = [line for line in block.strip().splitlines()]
    assert lines[0] == hm.marker_start
    assert lines[-1] == hm.marker_end

    # Extract host lines between markers
    host_lines = lines[1:-1]
    # Expected sorted order: api, db, web
    assert host_lines == [
        f"{ip_map['api']}\tapi.dynadock.lan",
        f"{ip_map['db']}\tdb.dynadock.lan",
        f"{ip_map['web']}\tweb.dynadock.lan",
    ]


def test_apply_writes_temp_and_calls_sudo(monkeypatch, tmp_path: Path):
    hm = HostsManager(tmp_path)
    calls: list[list[str]] = []
    captured_script: list[str] = []

    def fake_run(args, *_, **__):
        # Capture command and script argument
        calls.append(list(args))
        if args[0] == "sudo" and args[1] == "bash" and args[2] == "-c":
            captured_script.append(args[3])
        return DummyProc(0, "")

    monkeypatch.setattr("dynadock.hosts_manager.subprocess.run", fake_run)

    ip_map = {"api": "172.20.0.10", "web": "172.20.0.11"}
    hm.apply(ip_map, domain="dynadock.lan")

    # Ensure sudo bash -c was called once
    assert any(c[:3] == ["sudo", "bash", "-c"] for c in calls)

    # Verify the script contains sed removal and appends the temp block file into /etc/hosts
    assert captured_script, "Expected to capture the bash script passed to sudo"
    script = captured_script[0]
    assert "sed -i.bak '" in script
    assert "# BEGIN DYNADOCK HOSTS" in script and "# END DYNADOCK HOSTS" in script
    assert "cat '" in script and "' >> /etc/hosts" in script

    # The temporary file should be removed after apply()
    tmp_block = tmp_path / ".dynadock_hosts_block.tmp"
    assert not tmp_block.exists(), "Temporary hosts block file should be cleaned up"


def test_remove_calls_sudo_with_sed(monkeypatch, tmp_path: Path):
    hm = HostsManager(tmp_path)
    calls: list[list[str]] = []
    captured_script: list[str] = []

    def fake_run(args, *_, **__):
        calls.append(list(args))
        if args[:3] == ["sudo", "bash", "-c"]:
            captured_script.append(args[3])
        return DummyProc(0, "")

    monkeypatch.setattr("dynadock.hosts_manager.subprocess.run", fake_run)

    hm.remove()

    assert any(c[:3] == ["sudo", "bash", "-c"] for c in calls)
    assert captured_script, "Expected a sed removal script to be passed"
    script = captured_script[0]
    assert "sed -i.bak '" in script
    assert "BEGIN DYNADOCK HOSTS" in script and "END DYNADOCK HOSTS" in script

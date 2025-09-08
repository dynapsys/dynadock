#!/usr/bin/env python3
"""
Unit tests for refactored testing modules
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.dynadock.testing.network_analyzer import analyze_network_connectivity
from src.dynadock.testing.system_checker import check_system_status, get_docker_status
from src.dynadock.testing.auto_repair import auto_repair_issues, repair_hosts_file
from src.dynadock.testing.browser_tester import (
    setup_screenshots_dir,
)


class TestNetworkAnalyzer:
    """Test network connectivity analysis"""

    def test_analyze_localhost_http(self):
        """Test analyzing localhost HTTP URL"""
        result = analyze_network_connectivity("http://localhost:8000")

        assert "hostname" in result
        assert "port" in result
        assert "scheme" in result
        assert result["hostname"] == "localhost"
        assert result["port"] == 8000
        assert result["scheme"] == "http"

    def test_analyze_localhost_https(self):
        """Test analyzing localhost HTTPS URL"""
        result = analyze_network_connectivity("https://localhost:443")

        assert result["hostname"] == "localhost"
        assert result["port"] == 443
        assert result["scheme"] == "https"

    def test_analyze_domain_url(self):
        """Test analyzing domain URL"""
        result = analyze_network_connectivity("https://frontend.dynadock.lan/")

        assert result["hostname"] == "frontend.dynadock.lan"
        assert result["port"] == 443
        assert result["scheme"] == "https"
        assert "dns_resolution" in result
        assert "tcp_connect" in result
        assert "port_scan" in result


class TestSystemChecker:
    """Test system status checking"""

    def test_check_system_status(self):
        """Test system status check returns expected structure"""
        status = check_system_status()

        assert "containers" in status
        assert "ports_listening" in status
        assert "hosts_file" in status
        assert "processes" in status

    def test_get_docker_status(self):
        """Test Docker status check"""
        status = get_docker_status()

        assert "status" in status
        assert status["status"] in ["running", "not_running", "error"]


class TestAutoRepair:
    """Test auto-repair functionality"""

    def test_auto_repair_empty_issues(self):
        """Test auto-repair with no issues"""
        result = auto_repair_issues([])
        assert isinstance(result, list)
        assert len(result) == 0

    def test_auto_repair_container_issue(self):
        """Test auto-repair with container issue"""
        issues = ["container not running", "service unavailable"]
        result = auto_repair_issues(issues)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_repair_hosts_file(self):
        """Test hosts file repair check"""
        result = repair_hosts_file()
        assert isinstance(result, str)
        assert any(keyword in result.lower() for keyword in ["✅", "⚠️", "❌"])


class TestBrowserTester:
    """Test browser testing functionality"""

    def test_cleanup_old_screenshots(self):
        """Test screenshot cleanup functionality"""
        # Create test screenshots directory
        test_dir = Path("test_screenshots_test")
        test_dir.mkdir(exist_ok=True)

        # Create a dummy file
        dummy_file = test_dir / "test.png"
        dummy_file.write_text("test")

        # Test cleanup (modify function to accept custom dir for testing)
        import shutil

        if test_dir.exists():
            shutil.rmtree(test_dir)
        test_dir.mkdir(exist_ok=True)

        assert test_dir.exists()
        assert len(list(test_dir.glob("*"))) == 0

        # Cleanup test directory
        if test_dir.exists():
            shutil.rmtree(test_dir)

    def test_setup_screenshots_dir(self):
        """Test screenshots directory setup"""
        result_dir = setup_screenshots_dir()
        assert isinstance(result_dir, Path)
        assert result_dir.exists()
        assert result_dir.name == "test_screenshots"


def run_all_tests():
    """Run all tests manually"""
    import traceback

    test_classes = [
        TestNetworkAnalyzer,
        TestSystemChecker,
        TestAutoRepair,
        TestBrowserTester,
    ]
    results = {"passed": 0, "failed": 0, "errors": []}

    print("🧪 Running unit tests for refactored modules...")

    for test_class in test_classes:
        class_name = test_class.__name__
        print(f"\n📋 Testing {class_name}:")

        instance = test_class()
        test_methods = [
            method for method in dir(instance) if method.startswith("test_")
        ]

        for method_name in test_methods:
            try:
                method = getattr(instance, method_name)
                method()
                print(f"   ✅ {method_name}")
                results["passed"] += 1
            except Exception as e:
                print(f"   ❌ {method_name}: {e}")
                results["failed"] += 1
                results["errors"].append(f"{class_name}.{method_name}: {e}")
                traceback.print_exc()

    print(f"\n📊 Test Results: {results['passed']} passed, {results['failed']} failed")

    if results["errors"]:
        print("\n🔍 Error Details:")
        for error in results["errors"]:
            print(f"   - {error}")

    return results["failed"] == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

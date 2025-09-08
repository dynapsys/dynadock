#!/usr/bin/env python3
"""
Tests for the DynaDock health check script.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import subprocess
import logging

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import health_check after setting up mocks
with patch("logging.basicConfig"), patch("logging.getLogger"):
    import health_check


class TestHealthCheck(unittest.TestCase):
    """Test cases for the health check script."""

    def setUp(self):
        """Set up test fixtures."""
        self.original_services = health_check.SERVICES.copy()

        # Configure test logging
        logging.basicConfig(level=logging.CRITICAL)  # Suppress logs during tests

        # Mock services for testing
        health_check.SERVICES = {
            "test_service": {
                "url": "http://test-service",
                "expected_status": 200,
                "verify_ssl": False,
                "timeout": 1,
                "retries": 2,
                "retry_delay": 0.1,
            }
        }

    def tearDown(self):
        """Restore original services."""
        health_check.SERVICES = self.original_services

    def test_health_check_result_dataclass(self):
        """Test HealthCheckResult dataclass."""
        result = health_check.HealthCheckResult(
            service_name="test_service",
            is_healthy=True,
            message="Test message",
            response_time=0.5,
        )
        self.assertEqual(result.service_name, "test_service")
        self.assertTrue(result.is_healthy)
        self.assertEqual(result.message, "Test message")
        self.assertEqual(result.response_time, 0.5)

    def test_health_checker_initialization(self):
        """Test HealthChecker initialization."""
        checker = health_check.HealthChecker()
        self.assertIsNotNone(checker.session)
        self.assertTrue(hasattr(checker.session.adapters["http://"], "max_retries"))

    @patch("health_check.requests.Session")
    def test_health_checker_check_service_health_success(self, mock_session):
        """Test successful health check with retries."""
        # Setup mock session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.return_value.get.return_value = mock_response

        # Test the function
        checker = health_check.HealthChecker(mock_session.return_value)
        result = checker.check_service_health(
            "test_service", health_check.SERVICES["test_service"]
        )

        # Assertions
        self.assertTrue(result.is_healthy)
        self.assertIn("Healthy", result.message)
        mock_session.return_value.get.assert_called_once()

    @patch("health_check.requests.Session")
    def test_health_checker_check_service_health_retry(self, mock_session):
        """Test health check with retries on failure."""
        # Setup mock session to fail once then succeed
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_failure = MagicMock()
        mock_response_failure.status_code = 500

        mock_session.return_value.get.side_effect = [
            mock_response_failure,  # First attempt fails
            mock_response_success,  # Second attempt succeeds
        ]

        # Test the function
        checker = health_check.HealthChecker(mock_session.return_value)
        result = checker.check_service_health(
            "test_service", health_check.SERVICES["test_service"]
        )

        # Assertions
        self.assertTrue(result.is_healthy)
        self.assertEqual(mock_session.return_value.get.call_count, 2)

    @patch("health_check.requests.Session")
    def test_health_checker_check_service_health_failure(self, mock_session):
        """Test failed health check after all retries."""
        # Setup mock session to always fail
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_session.return_value.get.return_value = mock_response

        # Test the function
        checker = health_check.HealthChecker(mock_session.return_value)
        result = checker.check_service_health(
            "test_service", health_check.SERVICES["test_service"]
        )

        # Assertions
        self.assertFalse(result.is_healthy)
        self.assertIn("Failed after", result.message)
        # Should be initial call + number of retries (2 retries configured in test)
        self.assertEqual(mock_session.return_value.get.call_count, 2)

    @patch("health_check.subprocess.run")
    def test_stop_all_services_success(self, mock_run):
        """Test successful service stop."""
        # Mock successful subprocess run
        mock_run.return_value.returncode = 0

        # Test the function
        result = health_check.stop_all_services()

        # Assertions
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["docker-compose", "down"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    @patch("health_check.subprocess.run")
    def test_stop_all_services_failure(self, mock_run):
        """Test failed service stop."""
        # Mock failed subprocess run
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="Error")

        # Test the function
        result = health_check.stop_all_services()

        # Assertions
        self.assertFalse(result)

    @patch("health_check.subprocess.run")
    def test_check_docker_services_success(self, mock_run):
        """Test successful Docker services check."""
        # Mock successful subprocess run with test services
        mock_run.return_value.stdout = "test_service\ncaddy\n"
        mock_run.return_value.returncode = 0

        # Test the function
        result = health_check.check_docker_services()

        # Assertions
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["docker-compose", "ps", "--services", "--status", "running"],
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("health_check.subprocess.run")
    def test_check_docker_services_missing(self, mock_run):
        """Test Docker services check with missing services."""
        # Mock subprocess run with missing services
        mock_run.return_value.stdout = "test_service\n"  # Missing caddy
        mock_run.return_value.returncode = 0

        # Test the function
        result = health_check.check_docker_services()

        # Assertions
        self.assertFalse(result)

    @patch("health_check.HealthChecker")
    @patch("health_check.check_docker_services")
    @patch("health_check.logger")
    def test_main_success(self, mock_logger, mock_check_docker, mock_checker_class):
        """Test main function with successful health checks."""
        # Setup mocks
        mock_check_docker.return_value = True
        mock_checker = MagicMock()
        mock_checker_class.return_value = mock_checker

        # Mock successful health check result
        mock_result = health_check.HealthCheckResult(
            service_name="test_service",
            is_healthy=True,
            message="Healthy",
            response_time=0.1,
        )
        mock_checker.check_service_health.return_value = mock_result

        # Test the function
        result = health_check.main()

        # Assertions
        self.assertEqual(result, 0)
        mock_checker.check_service_health.assert_called_once()

        # Check logger calls
        mock_logger.info.assert_any_call(
            "🚀 Starting DynaDock service health checks..."
        )
        mock_logger.info.assert_any_call("✅ %s: %s", "test_service", "Healthy")
        mock_logger.info.assert_any_call(
            "\n✅ All services are healthy! (Avg response time: %.2fs)", 0.1
        )

    @patch("health_check.HealthChecker")
    @patch("health_check.check_docker_services")
    @patch("health_check.stop_all_services")
    @patch("health_check.logger")
    def test_main_service_down(
        self, mock_logger, mock_stop, mock_check_docker, mock_checker_class
    ):
        """Test main function with a down service."""
        # Setup mocks
        mock_check_docker.return_value = True
        mock_checker = MagicMock()
        mock_checker_class.return_value = mock_checker
        mock_stop.return_value = True

        # Mock failed health check result
        mock_result = health_check.HealthCheckResult(
            service_name="test_service",
            is_healthy=False,
            message="Failed",
            response_time=0,
        )
        mock_checker.check_service_health.return_value = mock_result

        # Test the function
        result = health_check.main()

        # Assertions
        self.assertEqual(result, 1)
        mock_stop.assert_called_once()

        # Check logger calls
        mock_logger.info.assert_any_call(
            "🚀 Starting DynaDock service health checks..."
        )
        mock_logger.error.assert_any_call("❌ %s: %s", "test_service", "Failed")
        mock_logger.error.assert_any_call(
            "\n❌ Health check failed for services: %s", "test_service"
        )

    @patch("health_check.check_docker_services")
    @patch("health_check.logger")
    def test_main_docker_services_down(self, mock_logger, mock_check_docker):
        """Test main function when Docker services are down."""
        # Setup mock
        mock_check_docker.return_value = False

        # Test the function
        result = health_check.main()

        # Assertions
        self.assertEqual(result, 1)
        mock_logger.error.assert_called_with(
            "❌ Not all required services are running. Please start them with 'docker-compose up -d'"
        )


if __name__ == "__main__":
    unittest.main()

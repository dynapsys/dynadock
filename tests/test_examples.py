#!/usr/bin/env python3
"""
Automated tests for DynaDock examples.
Tests that example applications start correctly and respond to requests.
"""

import os
import sys
import time
import subprocess
import requests
import pytest
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
TIMEOUT = 120  # seconds to wait for services to start


class TestExamples:
    """Test suite for DynaDock examples."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup for each test."""
        # This fixture can be used for setup tasks if needed in the future.
        # Cleanup is handled in each test via try/finally.
        yield
    
    def wait_for_service(self, url, timeout=TIMEOUT):
        """Wait for a service to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, verify=False, timeout=5)
                if response.status_code < 500:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        return False
    
    def get_service_ports(self, env_file):
        """Read service ports from .env.dynadock file."""
        ports = {}
        if not env_file.exists():
            return ports
            
        with open(env_file, 'r') as f:
            content = f.read()
            # Match patterns like: API_PORT=8001 or WEB_PORT=8000
            for match in re.finditer(r'^([A-Z_]+)_PORT=(\d+)', content, re.MULTILINE):
                service = match.group(1).lower()
                port = int(match.group(2))
                ports[service] = port
        return ports
    
    def run_dynadock_command(self, args, cwd=None, timeout=30):
        """Run a dynadock command and return the result."""
        cmd = ["dynadock"] + args
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result
    
    @pytest.mark.timeout(180)
    def test_simple_web_example(self):
        """Test the simple-web example."""
        example_dir = EXAMPLES_DIR / "simple-web"
        env_file = example_dir / ".env.dynadock"
        
        try:
            # Start services
            result = self.run_dynadock_command(["up", "--detach"], cwd=example_dir)
            assert result.returncode == 0, f"Failed to start services: {result.stderr}"
            
            # Give services time to start and get port allocations
            time.sleep(5)
            
            # Get allocated ports
            ports = self.get_service_ports(env_file)
            web_port = ports.get('web', 8000)
            api_port = ports.get('api', 8001)
            
            # Wait for services to be ready
            assert self.wait_for_service(f"http://localhost:{web_port}"), f"Web service did not start on port {web_port}"
            assert self.wait_for_service(f"http://localhost:{api_port}"), f"API service did not start on port {api_port}"
            
            # Test web service
            response = requests.get(f"http://localhost:{web_port}")
            assert response.status_code == 200
            assert "DynaDock Simple Web Example" in response.text
            
            # Test API service  
            response = requests.get(f"http://localhost:{api_port}")
            assert response.status_code == 200
            # The nginxdemos/hello image returns a plain text response
            assert "Server address" in response.text or "nginx" in response.text.lower()
        finally:
            # Stop services and remove all resources
            self.run_dynadock_command(["down", "--prune"], cwd=example_dir)
    
    @pytest.mark.timeout(180)
    def test_rest_api_example(self):
        """Test the REST API example with database."""
        example_dir = EXAMPLES_DIR / "rest-api"
        env_file = example_dir / ".env.dynadock"
        
        try:
            # Start services
            result = self.run_dynadock_command(["up", "--detach"], cwd=example_dir)
            assert result.returncode == 0, f"Failed to start services: {result.stderr}"
            
            # Give services and databases time to initialize
            time.sleep(15)
            
            # Get allocated ports
            ports = self.get_service_ports(env_file)
            api_port = ports.get('api', 8000)
            
            # Wait for API service to be ready
            assert self.wait_for_service(f"http://localhost:{api_port}/health"), f"API service did not start on port {api_port}"
            
            # Test health endpoint
            response = requests.get(f"http://localhost:{api_port}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["ok", "degraded"]
            assert "services" in data
            
            # Test API root
            response = requests.get(f"http://localhost:{api_port}/")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "endpoints" in data
            
            # Test users endpoint
            response = requests.get(f"http://localhost:{api_port}/api/users")
            assert response.status_code == 200
            data = response.json()
            assert "users" in data
            assert isinstance(data["users"], list)
            
            # Test creating a user
            new_user = {"name": "Test User", "email": "test@example.com"}
            response = requests.post(f"http://localhost:{api_port}/api/users", json=new_user)
            assert response.status_code == 201
            created_user = response.json()
            assert created_user["name"] == new_user["name"]
            assert created_user["email"] == new_user["email"]
            
            # Test cache endpoint
            cache_data = {"value": "test_value", "ttl": 60}
            response = requests.post(f"http://localhost:{api_port}/api/cache/test_key", json=cache_data)
            assert response.status_code == 200
            
            response = requests.get(f"http://localhost:{api_port}/api/cache/test_key")
            assert response.status_code == 200
            data = response.json()
            assert data["value"] == "test_value"
        finally:
            # Stop services and remove all resources
            self.run_dynadock_command(["down", "--prune"], cwd=example_dir)
    
    @pytest.mark.timeout(360)
    @pytest.mark.skipif(
        os.getenv("SKIP_FULLSTACK_TEST", "false").lower() == "true",
        reason="Fullstack test is resource intensive"
    )
    def test_fullstack_example(self):
        """Test the fullstack example."""
        example_dir = EXAMPLES_DIR / "fullstack"
        env_file = example_dir / ".env.dynadock"

        try:
            # Start services
            result = self.run_dynadock_command(["up", "--detach"], cwd=example_dir, timeout=300)
            assert result.returncode == 0, f"Failed to start services: {result.stderr}"

            # Give services more time to initialize
            time.sleep(15)

            # Get allocated ports
            ports = self.get_service_ports(env_file)
            frontend_port = ports.get('frontend', 8000)
            backend_port = ports.get('backend', 8001)

            # Wait for services to be ready
            assert self.wait_for_service(f"http://localhost:{frontend_port}"), f"Frontend service did not start on port {frontend_port}"
            assert self.wait_for_service(f"http://localhost:{backend_port}/api/health"), f"Backend service did not start on port {backend_port}"

            # Test backend health
            response = requests.get(f"http://localhost:{backend_port}/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["ok", "degraded"]

            # Test backend API root
            response = requests.get(f"http://localhost:{backend_port}/api")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "endpoints" in data

            # Test user registration
            user_data = {
                "email": "testuser@example.com",
                "password": "testpassword123",
                "name": "Test User"
            }
            response = requests.post(f"http://localhost:{backend_port}/api/auth/register", json=user_data)
            assert response.status_code == 201, f"User registration failed: {response.json()}"
            data = response.json()
            assert "token" in data
            assert "user" in data
            token = data["token"]

            # Test user login
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            response = requests.post(f"http://localhost:{backend_port}/api/auth/login", json=login_data)
            assert response.status_code == 200
            data = response.json()
            assert "token" in data

            # Test authenticated endpoints
            headers = {"Authorization": f"Bearer {token}"}

            # Get profile
            response = requests.get(f"http://localhost:{backend_port}/api/auth/profile", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == user_data["email"]

            # Create todo
            todo_data = {"title": "Test todo item"}
            response = requests.post(f"http://localhost:{backend_port}/api/todos", json=todo_data, headers=headers)
            assert response.status_code == 201
            todo = response.json()
            assert todo["title"] == todo_data["title"]
            todo_id = todo["id"]

            # Get todos
            response = requests.get(f"http://localhost:{backend_port}/api/todos", headers=headers)
            assert response.status_code == 200
            todos = response.json()
            assert len(todos) > 0
            assert any(t["id"] == todo_id for t in todos)

            # Update todo
            update_data = {"completed": True}
            response = requests.put(f"http://localhost:{backend_port}/api/todos/{todo_id}",
                                   json=update_data, headers=headers)
            assert response.status_code == 200
            updated_todo = response.json()
            assert updated_todo["completed"] == True

            # Delete todo
            response = requests.delete(f"http://localhost:{backend_port}/api/todos/{todo_id}", headers=headers)
            assert response.status_code == 200

            # Test frontend is serving
            response = requests.get(f"http://localhost:{frontend_port}")
            assert response.status_code == 200
            assert "<!doctype html>" in response.text.lower()
        finally:
            # Stop services and remove all resources
            self.run_dynadock_command(["down", "--prune"], cwd=example_dir)
    
    def test_dynadock_health_check(self):
        """Test DynaDock's built-in health check functionality."""
        example_dir = EXAMPLES_DIR / "simple-web"
        
        # Start services
        result = self.run_dynadock_command(["up", "--detach"], cwd=example_dir)
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services
        time.sleep(10)
        
        # Run status command to check health
        result = self.run_dynadock_command(["status"], cwd=example_dir)
        assert result.returncode == 0, f"Status check failed: {result.stderr}"
        # Just verify the command works - exact output may vary
        
        # Stop services and remove all resources
        result = self.run_dynadock_command(["down", "--prune"], cwd=example_dir)
        assert result.returncode == 0
    
    @pytest.mark.skip(reason="Scaling not implemented in current dynadock version")
    def test_dynadock_scaling(self):
        """Test DynaDock service scaling."""
        example_dir = EXAMPLES_DIR / "simple-web"
        
        # Start services with scaling
        result = self.run_dynadock_command(["up", "--detach"], cwd=example_dir)
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Check that multiple instances are running
        result = subprocess.run(
            ["docker", "ps", "--filter", "label=com.docker.compose.service=api"],
            capture_output=True,
            text=True
        )
        # Count running containers
        lines = result.stdout.strip().split('\n')
        container_count = len(lines) - 1  # Subtract header line
        assert container_count >= 2, f"Expected at least 2 api containers, got {container_count}"
        
        # Stop services and remove all resources
        result = self.run_dynadock_command(["down", "--prune"], cwd=example_dir)
        assert result.returncode == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

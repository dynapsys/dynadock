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
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
TIMEOUT = 120  # seconds to wait for services to start


class TestExamples:
    """Test suite for DynaDock examples."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and cleanup for each test."""
        yield
        # Cleanup after test
        subprocess.run(["dynadock", "down", "-v"], capture_output=True, text=True)
    
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
    
    def run_dynadock_command(self, args, cwd=None):
        """Run a dynadock command and return the result."""
        cmd = ["dynadock"] + args
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result
    
    @pytest.mark.timeout(180)
    def test_simple_web_example(self):
        """Test the simple-web example."""
        example_dir = EXAMPLES_DIR / "simple-web"
        
        # Start services
        result = self.run_dynadock_command(["up", "-d"], cwd=example_dir)
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services to be ready
        assert self.wait_for_service("http://localhost:3001"), "Web service did not start"
        assert self.wait_for_service("http://localhost:3002"), "API service did not start"
        
        # Test web service
        response = requests.get("http://localhost:3001")
        assert response.status_code == 200
        assert "DynaDock Simple Web Example" in response.text
        
        # Test API service
        response = requests.get("http://localhost:3002")
        assert response.status_code == 200
        assert "Hello from API" in response.text
        
        # Check health endpoint
        response = requests.get("http://localhost:3002/health")
        assert response.status_code == 200
        
        # Stop services
        result = self.run_dynadock_command(["down"], cwd=example_dir)
        assert result.returncode == 0
    
    @pytest.mark.timeout(180)
    def test_rest_api_example(self):
        """Test the REST API example with database."""
        example_dir = EXAMPLES_DIR / "rest-api"
        
        # Start services
        result = self.run_dynadock_command(["up", "-d"], cwd=example_dir)
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services to be ready
        time.sleep(10)  # Give databases time to initialize
        assert self.wait_for_service("http://localhost:3001/health"), "API service did not start"
        
        # Test health endpoint
        response = requests.get("http://localhost:3001/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        assert "services" in data
        
        # Test API root
        response = requests.get("http://localhost:3001/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        
        # Test users endpoint
        response = requests.get("http://localhost:3001/api/users")
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], list)
        
        # Test creating a user
        new_user = {"name": "Test User", "email": "test@example.com"}
        response = requests.post("http://localhost:3001/api/users", json=new_user)
        assert response.status_code == 201
        created_user = response.json()
        assert created_user["name"] == new_user["name"]
        assert created_user["email"] == new_user["email"]
        
        # Test cache endpoint
        cache_data = {"value": "test_value", "ttl": 60}
        response = requests.post("http://localhost:3001/api/cache/test_key", json=cache_data)
        assert response.status_code == 200
        
        response = requests.get("http://localhost:3001/api/cache/test_key")
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "test_value"
        
        # Stop services
        result = self.run_dynadock_command(["down", "-v"], cwd=example_dir)
        assert result.returncode == 0
    
    @pytest.mark.timeout(240)
    @pytest.mark.skipif(
        os.getenv("SKIP_FULLSTACK_TEST", "false").lower() == "true",
        reason="Fullstack test is resource intensive"
    )
    def test_fullstack_example(self):
        """Test the fullstack example."""
        example_dir = EXAMPLES_DIR / "fullstack"
        
        # Start services
        result = self.run_dynadock_command(["up", "-d"], cwd=example_dir)
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services to be ready
        time.sleep(15)  # Give services more time to initialize
        assert self.wait_for_service("http://localhost:3001"), "Frontend service did not start"
        assert self.wait_for_service("http://localhost:3002/api/health"), "Backend service did not start"
        
        # Test backend health
        response = requests.get("http://localhost:3002/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        
        # Test backend API root
        response = requests.get("http://localhost:3002/api")
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
        response = requests.post("http://localhost:3002/api/auth/register", json=user_data)
        assert response.status_code == 201
        data = response.json()
        assert "token" in data
        assert "user" in data
        token = data["token"]
        
        # Test user login
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        response = requests.post("http://localhost:3002/api/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        
        # Test authenticated endpoints
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get profile
        response = requests.get("http://localhost:3002/api/auth/profile", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        
        # Create todo
        todo_data = {"title": "Test todo item"}
        response = requests.post("http://localhost:3002/api/todos", json=todo_data, headers=headers)
        assert response.status_code == 201
        todo = response.json()
        assert todo["title"] == todo_data["title"]
        todo_id = todo["id"]
        
        # Get todos
        response = requests.get("http://localhost:3002/api/todos", headers=headers)
        assert response.status_code == 200
        todos = response.json()
        assert len(todos) > 0
        assert any(t["id"] == todo_id for t in todos)
        
        # Update todo
        update_data = {"completed": True}
        response = requests.put(f"http://localhost:3002/api/todos/{todo_id}", 
                               json=update_data, headers=headers)
        assert response.status_code == 200
        updated_todo = response.json()
        assert updated_todo["completed"] == True
        
        # Delete todo
        response = requests.delete(f"http://localhost:3002/api/todos/{todo_id}", headers=headers)
        assert response.status_code == 200
        
        # Test frontend is serving
        response = requests.get("http://localhost:3001")
        assert response.status_code == 200
        assert "<!DOCTYPE html>" in response.text
        
        # Stop services
        result = self.run_dynadock_command(["down", "-v"], cwd=example_dir)
        assert result.returncode == 0
    
    def test_dynadock_health_check(self):
        """Test DynaDock's built-in health check functionality."""
        example_dir = EXAMPLES_DIR / "simple-web"
        
        # Start services with health check
        result = self.run_dynadock_command(["up", "-d", "--health-check"], cwd=example_dir)
        assert result.returncode == 0, f"Failed to start services: {result.stderr}"
        
        # Wait for services
        time.sleep(10)
        
        # Run health check command
        result = self.run_dynadock_command(["health"], cwd=example_dir)
        assert result.returncode == 0, f"Health check failed: {result.stderr}"
        assert "healthy" in result.stdout.lower()
        
        # Stop services
        result = self.run_dynadock_command(["down"], cwd=example_dir)
        assert result.returncode == 0
    
    def test_dynadock_scaling(self):
        """Test DynaDock service scaling."""
        example_dir = EXAMPLES_DIR / "simple-web"
        
        # Start services with scaling
        result = self.run_dynadock_command(["up", "-d", "--scale", "api=3"], cwd=example_dir)
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
        
        # Stop services
        result = self.run_dynadock_command(["down"], cwd=example_dir)
        assert result.returncode == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

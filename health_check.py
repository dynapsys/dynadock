#!/usr/bin/env python3
"""
DynaDock Service Health Check

This script checks the health of all DynaDock services by making HTTP requests
to their respective health endpoints. If any service is down, it will stop all
services and exit with a non-zero status code.

Features:
- Automatic retries with exponential backoff
- Detailed error reporting
- Graceful handling of service startup delays
- Docker Compose integration
"""

import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests
import subprocess
from requests.adapters import HTTPAdapter, Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('health_check.log')
    ]
)
logger = logging.getLogger(__name__)

# Disable SSL warnings for self-signed certificates
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Service configuration
SERVICES = {
    'api': {
        'url': 'http://localhost',  # Using HTTP to avoid SSL issues
        'expected_status': 200,
        'verify_ssl': False,
        'timeout': 5,
        'retries': 3,
        'retry_delay': 2,
    },
    'redis': {
        'url': 'http://localhost/redis',
        'expected_status': 200,
        'verify_ssl': False,
        'timeout': 5,
        'retries': 3,
        'retry_delay': 2,
    },
}

class HealthCheckError(Exception):
    """Custom exception for health check failures."""
    pass

@dataclass
class HealthCheckResult:
    """Container for health check results."""
    service_name: str
    is_healthy: bool
    message: str
    response_time: float

class HealthChecker:
    """Handles health checking of services with retries and backoff."""
    
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def check_service_health(self, service_name: str, config: dict) -> HealthCheckResult:
        """Check the health of a single service with retries."""
        url = config['url']
        expected_status = config['expected_status']
        verify_ssl = config.get('verify_ssl', False)
        timeout = config.get('timeout', 5)
        max_retries = config.get('retries', 3)
        retry_delay = config.get('retry_delay', 2)
        
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.time()
                response = self.session.get(
                    url,
                    verify=verify_ssl,
                    timeout=timeout,
                    headers={'User-Agent': f'DynaDock-HealthCheck/1.0 (Attempt {attempt}/{max_retries})'}
                )
                response_time = time.time() - start_time
                
                if response.status_code == expected_status:
                    return HealthCheckResult(
                        service_name=service_name,
                        is_healthy=True,
                        message=f"Healthy (Status {response.status_code} in {response_time:.2f}s)",
                        response_time=response_time
                    )
                else:
                    last_error = f"Unexpected status code {response.status_code} (expected {expected_status})"
            
            except requests.exceptions.RequestException as e:
                last_error = str(e)
            
            if attempt < max_retries:
                logger.warning(
                    "%s: Attempt %d/%d failed - %s. Retrying in %ds...",
                    service_name, attempt, max_retries, last_error, retry_delay
                )
                time.sleep(retry_delay * attempt)  # Exponential backoff
        
        return HealthCheckResult(
            service_name=service_name,
            is_healthy=False,
            message=f"Failed after {max_retries} attempts: {last_error}",
            response_time=0
        )

def stop_all_services() -> bool:
    """Stop all Docker Compose services."""
    try:
        logger.info("Stopping all services...")
        result = subprocess.run(
            ['docker-compose', 'down'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.debug("Service stop output: %s", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Error stopping services: %s", e.stderr)
        return False

def check_docker_services() -> bool:
    """Check if all services are running via Docker Compose."""
    try:
        result = subprocess.run(
            ['docker-compose', 'ps', '--services', '--status', 'running'],
            check=True,
            capture_output=True,
            text=True
        )
        running_services = set(result.stdout.strip().split('\n'))
        expected_services = set(SERVICES.keys()) | {'caddy'}
        
        if not expected_services.issubset(running_services):
            missing = expected_services - running_services
            logger.error("Missing services: %s", ', '.join(missing))
            return False
            
        return True
    except subprocess.CalledProcessError as e:
        logger.error("Failed to check Docker services: %s", e.stderr)
        return False

def main() -> int:
    """Main entry point for the health check script."""
    logger.info("🚀 Starting DynaDock service health checks...")
    
    # First, verify all services are running
    if not check_docker_services():
        logger.error("❌ Not all required services are running. Please start them with 'docker-compose up -d'")
        return 1
    
    checker = HealthChecker()
    results = []
    
    # Check each service
    for service_name, config in SERVICES.items():
        result = checker.check_service_health(service_name, config)
        results.append(result)
        
        if result.is_healthy:
            logger.info("✅ %s: %s", service_name, result.message)
        else:
            logger.error("❌ %s: %s", service_name, result.message)
    
    # Calculate summary
    failed_services = [r.service_name for r in results if not r.is_healthy]
    avg_response_time = sum(r.response_time for r in results if r.is_healthy) / max(1, len(results) - len(failed_services))
    
    # Handle failures
    if failed_services:
        logger.error("\n❌ Health check failed for services: %s", ', '.join(failed_services))
        
        if stop_all_services():
            logger.info("✅ All services stopped successfully.")
        else:
            logger.error("❌ Failed to stop some services.")
        
        return 1
    
    logger.info(
        "\n✅ All services are healthy! (Avg response time: %.2fs)",
        avg_response_time
    )
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\nHealth check interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.exception("An unexpected error occurred: %s", str(e))
        sys.exit(1)

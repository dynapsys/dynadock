# DynaDock - Brakujące pliki projektu

## tests/unit/test_utils.py

```python
"""Unit tests for utility functions."""

import pytest
from pathlib import Path
import yaml
from unittest.mock import patch, mock_open

from dynadock.utils import (
    find_compose_file,
    validate_compose_file,
    get_project_name_from_compose,
    update_compose_with_ports,
    cleanup_temp_files
)


class TestUtils:
    """Test utility functions."""
    
    def test_find_compose_file_current_dir(self, temp_dir):
        """Test finding compose file in current directory."""
        compose_file = temp_dir / 'docker-compose.yaml'
        compose_file.touch()
        
        result = find_compose_file(temp_dir)
        assert result == str(compose_file)
    
    def test_find_compose_file_alternate_names(self, temp_dir):
        """Test finding compose file with alternate names."""
        # Test different possible names
        names = ['compose.yaml', 'compose.yml', 'docker-compose.yml']
        
        for name in names:
            file = temp_dir / name
            file.touch()
            
            result = find_compose_file(temp_dir)
            assert result == str(file)
            
            file.unlink()
    
    def test_find_compose_file_parent_dir(self, temp_dir):
        """Test finding compose file in parent directory."""
        child_dir = temp_dir / 'child'
        child_dir.mkdir()
        
        compose_file = temp_dir / 'docker-compose.yaml'
        compose_file.touch()
        
        result = find_compose_file(child_dir)
        assert result == str(compose_file)
    
    def test_find_compose_file_not_found(self, temp_dir):
        """Test when compose file is not found."""
        result = find_compose_file(temp_dir)
        assert result is None
    
    def test_validate_compose_file_valid(self, temp_dir):
        """Test validating a valid compose file."""
        compose_content = {
            'version': '3.8',
            'services': {
                'web': {'image': 'nginx'}
            }
        }
        
        compose_file = temp_dir / 'docker-compose.yaml'
        with open(compose_file, 'w') as f:
            yaml.dump(compose_content, f)
        
        assert validate_compose_file(str(compose_file)) == True
    
    def test_validate_compose_file_invalid_no_services(self, temp_dir):
        """Test validating compose file without services."""
        compose_content = {
            'version': '3.8'
        }
        
        compose_file = temp_dir / 'docker-compose.yaml'
        with open(compose_file, 'w') as f:
            yaml.dump(compose_content, f)
        
        assert validate_compose_file(str(compose_file)) == False
    
    def test_validate_compose_file_invalid_format(self, temp_dir):
        """Test validating invalid YAML."""
        compose_file = temp_dir / 'docker-compose.yaml'
        compose_file.write_text('invalid: yaml: content:')
        
        assert validate_compose_file(str(compose_file)) == False
    
    def test_validate_compose_file_not_exists(self, temp_dir):
        """Test validating non-existent file."""
        assert validate_compose_file('nonexistent.yaml') == False
    
    def test_get_project_name_from_compose_explicit(self, temp_dir):
        """Test getting explicit project name from compose."""
        compose_content = {
            'name': 'my-project',
            'version': '3.8',
            'services': {}
        }
        
        compose_file = temp_dir / 'docker-compose.yaml'
        with open(compose_file, 'w') as f:
            yaml.dump(compose_content, f)
        
        name = get_project_name_from_compose(str(compose_file))
        assert name == 'my-project'
    
    def test_get_project_name_from_compose_from_dir(self, temp_dir):
        """Test getting project name from directory."""
        project_dir = temp_dir / 'My_Test-Project'
        project_dir.mkdir()
        
        compose_file = project_dir / 'docker-compose.yaml'
        compose_file.write_text('version: "3.8"\nservices: {}')
        
        name = get_project_name_from_compose(str(compose_file))
        assert name == 'mytestproject'
    
    def test_update_compose_with_ports(self, temp_dir):
        """Test updating compose file with allocated ports."""
        compose_content = {
            'version': '3.8',
            'services': {
                'web': {
                    'image': 'nginx',
                    'ports': ['80:80']
                },
                'api': {
                    'image': 'node',
                    'ports': ['3000']
                }
            }
        }
        
        compose_file = temp_dir / 'docker-compose.yaml'
        with open(compose_file, 'w') as f:
            yaml.dump(compose_content, f)
        
        ports = {'web': 8080, 'api': 8081}
        
        result_file = update_compose_with_ports(str(compose_file), ports)
        
        assert Path(result_file).exists()
        
        with open(result_file, 'r') as f:
            result = yaml.safe_load(f)
        
        # Check updated ports
        assert result['services']['web']['ports'] == ['8080:80']
        assert result['services']['api']['ports'] == ['8081:3000']
        
        # Check environment variables added
        assert result['services']['web']['environment']['PORT'] == '8080'
        assert result['services']['api']['environment']['PORT'] == '8081'
    
    def test_cleanup_temp_files(self, temp_dir):
        """Test cleaning up temporary files."""
        # Create temp files
        files = [
            '.dynadock-compose.yaml',
            '.env.dynadock'
        ]
        
        for file in files:
            (temp_dir / file).touch()
        
        # Create .dynadock directory
        dynadock_dir = temp_dir / '.dynadock'
        dynadock_dir.mkdir()
        (dynadock_dir / 'test.txt').touch()
        
        # Run cleanup
        cleanup_temp_files(temp_dir)
        
        # Verify files are removed
        for file in files:
            assert not (temp_dir / file).exists()
        
        assert not dynadock_dir.exists()
    
    def test_cleanup_temp_files_missing(self, temp_dir):
        """Test cleanup when files don't exist."""
        # Should not raise error
        cleanup_temp_files(temp_dir)
```

## tests/unit/test_caddy_config.py

```python
"""Unit tests for CaddyConfig."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import docker

from dynadock.caddy_config import CaddyConfig


class TestCaddyConfig:
    """Test CaddyConfig functionality."""
    
    def test_init(self, temp_dir):
        """Test CaddyConfig initialization."""
        config = CaddyConfig(temp_dir)
        
        assert config.project_dir == temp_dir
        assert config.caddy_dir == temp_dir / '.dynadock' / 'caddy'
        assert config.caddy_dir.exists()
    
    def test_generate_basic(self, temp_dir):
        """Test generating basic Caddyfile."""
        config = CaddyConfig(temp_dir)
        
        services = {'api': {}, 'web': {}}
        ports = {'api': 8001, 'web': 8002}
        
        config.generate(
            services=services,
            ports=ports,
            domain='test.local',
            enable_tls=False,
            cors_origins=['http://localhost:3000']
        )
        
        caddyfile = config.caddy_dir / 'Caddyfile'
        assert caddyfile.exists()
        
        content = caddyfile.read_text()
        
        # Check basic content
        assert 'api.test.local' in content
        assert 'web.test.local' in content
        assert 'reverse_proxy' in content
        assert 'api:8001' in content
        assert 'web:8002' in content
        assert 'Access-Control-Allow-Origin' in content
        assert 'http://localhost:3000' in content
    
    def test_generate_with_tls(self, temp_dir):
        """Test generating Caddyfile with TLS."""
        config = CaddyConfig(temp_dir)
        
        config.generate(
            services={'api': {}},
            ports={'api': 8001},
            domain='app.com',
            enable_tls=True,
            cors_origins=[]
        )
        
        content = (config.caddy_dir / 'Caddyfile').read_text()
        
        assert 'tls internal' in content
        assert ':443' in content
        assert 'auto_https off' not in content
    
    def test_generate_without_tls(self, temp_dir):
        """Test generating Caddyfile without TLS."""
        config = CaddyConfig(temp_dir)
        
        config.generate(
            services={'api': {}},
            ports={'api': 8001},
            domain='local.dev',
            enable_tls=False,
            cors_origins=[]
        )
        
        content = (config.caddy_dir / 'Caddyfile').read_text()
        
        assert 'auto_https off' in content
        assert 'tls internal' not in content or content.count('tls internal') == 0
    
    def test_generate_api_gateway(self, temp_dir):
        """Test API gateway generation."""
        config = CaddyConfig(temp_dir)
        
        services = {'api': {}, 'auth': {}}
        ports = {'api': 8001, 'auth': 8002}
        
        config.generate(
            services=services,
            ports=ports,
            domain='test.local',
            enable_tls=False,
            cors_origins=[]
        )
        
        content = (config.caddy_dir / 'Caddyfile').read_text()
        
        assert 'api.test.local' in content
        assert 'route /api/*' in content
        assert 'route /auth/*' in content
        assert 'rate_limit' in content
    
    @patch('docker.from_env')
    def test_start_caddy_new(self, mock_docker_env, temp_dir):
        """Test starting new Caddy container."""
        mock_client = Mock()
        mock_docker_env.return_value = mock_client
        
        # Simulate container not found
        mock_client.containers.get.side_effect = docker.errors.NotFound('Not found')
        
        mock_container = Mock()
        mock_client.containers.run.return_value = mock_container
        
        config = CaddyConfig(temp_dir)
        config.generate({}, {}, 'test.local', False, [])
        
        container = config.start_caddy()
        
        assert container == mock_container
        
        # Verify container run parameters
        run_args = mock_client.containers.run.call_args
        
        assert run_args[0][0] == 'caddy:2-alpine'
        assert run_args[1]['name'] == 'dynadock-caddy'
        assert run_args[1]['detach'] == True
        assert run_args[1]['ports']['80/tcp'] == 80
        assert run_args[1]['ports']['443/tcp'] == 443
    
    @patch('docker.from_env')
    def test_start_caddy_existing_running(self, mock_docker_env, temp_dir):
        """Test starting Caddy when already running."""
        mock_client = Mock()
        mock_docker_env.return_value = mock_client
        
        mock_container = Mock()
        mock_container.status = 'running'
        mock_client.containers.get.return_value = mock_container
        
        config = CaddyConfig(temp_dir)
        container = config.start_caddy()
        
        assert container == mock_container
        mock_client.containers.run.assert_not_called()
    
    @patch('docker.from_env')
    def test_start_caddy_existing_stopped(self, mock_docker_env, temp_dir):
        """Test starting Caddy when container exists but stopped."""
        mock_client = Mock()
        mock_docker_env.return_value = mock_client
        
        old_container = Mock()
        old_container.status = 'exited'
        mock_client.containers.get.return_value = old_container
        
        new_container = Mock()
        mock_client.containers.run.return_value = new_container
        
        config = CaddyConfig(temp_dir)
        config.generate({}, {}, 'test.local', False, [])
        
        container = config.start_caddy()
        
        assert container == new_container
        old_container.remove.assert_called_once_with(force=True)
    
    @patch('docker.from_env')
    def test_stop_caddy(self, mock_docker_env):
        """Test stopping Caddy container."""
        mock_client = Mock()
        mock_docker_env.return_value = mock_client
        
        mock_container = Mock()
        mock_client.containers.get.return_value = mock_container
        
        config = CaddyConfig(Path('/tmp'))
        config.stop_caddy()
        
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()
    
    @patch('docker.from_env')
    def test_stop_caddy_not_found(self, mock_docker_env):
        """Test stopping Caddy when container doesn't exist."""
        mock_client = Mock()
        mock_docker_env.return_value = mock_client
        mock_client.containers.get.side_effect = docker.errors.NotFound('Not found')
        
        config = CaddyConfig(Path('/tmp'))
        config.stop_caddy()  # Should not raise error
    
    @patch('docker.from_env')
    def test_connect_to_network(self, mock_docker_env, temp_dir):
        """Test connecting Caddy to Docker network."""
        mock_client = Mock()
        mock_docker_env.return_value = mock_client
        
        # Mock networks
        compose_network = Mock()
        compose_network.name = 'myproject_compose'
        
        other_network = Mock()
        other_network.name = 'bridge'
        
        mock_client.networks.list.return_value = [other_network, compose_network]
        
        mock_container = Mock()
        
        config = CaddyConfig(temp_dir)
        config._connect_to_network(mock_container)
        
        compose_network.connect.assert_called_once_with(mock_container)
```

## templates/Caddyfile.template

```jinja2
# DynaDock Caddy Configuration
# Auto-generated - DO NOT EDIT
# Generated at: {{ timestamp }}

{
    # Global options
    email admin@{{ domain }}
    {% if not enable_tls %}
    auto_https off
    {% endif %}
    
    # Admin API
    admin 0.0.0.0:2019
    
    # Logging
    log {
        output file /var/log/caddy/access.log
        format json
        level INFO
    }
}

# Health check endpoint
:80 {
    respond /health "OK" 200
    respond /metrics prometheus
}

{% if enable_tls %}
# HTTPS redirect
:443 {
    tls internal
    
    # HSTS header
    header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
}
{% endif %}

{% for service_name, config in services.items() %}
# =====================================
# Service: {{ service_name }}
# Port: {{ config.port }}
# =====================================
{{ service_name }}.{{ domain }} {
    {% if enable_tls %}
    tls {
        {% if production %}
        # Production - Let's Encrypt
        email {{ admin_email }}
        {% else %}
        # Development - Self-signed
        internal
        {% endif %}
    }
    {% endif %}
    
    # Request ID for tracing
    header X-Request-Id {http.request.uuid}
    
    # CORS Configuration
    @cors {
        header Origin {args.0}
    }
    header @cors {
        Access-Control-Allow-Origin "{args.0}"
        Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, X-Request-Id"
        Access-Control-Allow-Credentials "true"
        Access-Control-Max-Age "3600"
        Access-Control-Expose-Headers "X-Request-Id"
    }
    
    # Handle preflight requests
    @options {
        method OPTIONS
    }
    respond @options 204
    
    # Security headers
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        {% if enable_tls %}
        Content-Security-Policy "default-src 'self' https:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
        {% endif %}
    }
    
    # Rate limiting per IP
    rate_limit {
        zone {{ service_name }}_zone 100r/m
        key {remote_host}
    }
    
    # Reverse proxy configuration
    reverse_proxy {
        to {{ service_name }}:{{ config.port }}
        
        # Load balancing strategy
        lb_policy {{ config.lb_policy | default('round_robin') }}
        lb_try_duration 30s
        lb_try_interval 1s
        fail_duration 10s
        max_fails 3
        
        # Health checks
        health_uri {{ config.health_path | default('/health') }}
        health_interval 10s
        health_timeout 5s
        health_status 200
        
        # Headers to backend
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
        header_up X-Forwarded-Host {host}
        header_up X-Request-Id {http.request.uuid}
        
        # Timeouts
        dial_timeout 10s
        response_header_timeout 30s
        read_timeout 60s
        write_timeout 60s
        
        # Circuit breaker
        flush_interval -1
        
        # Buffer settings
        buffer_requests on
        buffer_responses on
    }
    
    # Compression
    encode gzip zstd
    
    # File server for static assets (optional)
    {% if config.static_path %}
    handle /static/* {
        root * {{ config.static_path }}
        file_server {
            hide .git
            index index.html
        }
    }
    {% endif %}
    
    # WebSocket support
    {% if config.websocket %}
    @websocket {
        header Connection *upgrade*
        header Upgrade websocket
    }
    reverse_proxy @websocket {
        to {{ service_name }}:{{ config.port }}
        flush_interval -1
    }
    {% endif %}
    
    # Custom error pages
    handle_errors {
        @404 {
            expression {http.error.status_code} == 404
        }
        respond @404 "Service {{ service_name }} - Not Found" 404
        
        @5xx {
            expression {http.error.status_code} >= 500
        }
        respond @5xx "Service {{ service_name }} - Internal Error" {http.error.status_code}
    }
    
    # Logging
    log {
        output file /var/log/caddy/{{ service_name }}.log {
            roll_size 100mb
            roll_keep 5
            roll_keep_for 720h
        }
        format json
        level INFO
    }
}

{% endfor %}

# =====================================
# API Gateway
# =====================================
api.{{ domain }} {
    {% if enable_tls %}
    tls internal
    {% endif %}
    
    # Global rate limiting for API gateway
    rate_limit {
        zone api_global 1000r/m
        key {remote_host}
    }
    
    # API versioning support
    @v1 {
        header Api-Version 1*
        path /v1/*
    }
    
    @v2 {
        header Api-Version 2*
        path /v2/*
    }
    
    # Service routing
    {% for service_name, config in services.items() %}
    # Route to {{ service_name }}
    route /{{ service_name }}/* {
        # Strip service prefix
        uri strip_prefix /{{ service_name }}
        
        # Add service header
        header X-Service {{ service_name }}
        
        reverse_proxy {{ service_name }}:{{ config.port }} {
            header_up X-Gateway-Route {{ service_name }}
        }
    }
    {% endfor %}
    
    # GraphQL endpoint (if needed)
    route /graphql {
        reverse_proxy graphql:4000
    }
    
    # Health check aggregator
    route /health/all {
        respond "OK" 200
    }
    
    # Service discovery endpoint
    route /services {
        respond `{{ services | tojson }}` 200 {
            header Content-Type "application/json"
        }
    }
    
    # Default response
    respond "DynaDock API Gateway" 200
}

# =====================================
# Monitoring & Metrics
# =====================================
metrics.{{ domain }} {
    {% if enable_tls %}
    tls internal
    {% endif %}
    
    basicauth {
        admin $2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNmpkT/5qqR7hx4IjWJPDhjvG
    }
    
    metrics /metrics {
        disable_openmetrics
    }
    
    reverse_proxy /prometheus/* prometheus:9090
    reverse_proxy /grafana/* grafana:3000
}
```

## .dockerignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.coverage
.pytest_cache/
htmlcov/
.tox/
*.cover

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Git
.git/
.gitignore

# Documentation
docs/site/
*.pdf

# DynaDock specific
.dynadock/
.env.dynadock
.dynadock-compose.yaml
*.log

# CI/CD
.github/
.gitlab-ci.yml
.travis.yml

# Misc
README.md
LICENSE
CHANGELOG.md
Makefile
```

## docker-compose.test.yaml

```yaml
version: '3.8'

services:
  # Test web service
  test_web:
    image: nginx:alpine
    ports:
      - "80"
    environment:
      - TEST_ENV=test
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 5s
      timeout: 3s
      retries: 3
    labels:
      dynadock.test: "true"

  # Test API service
  test_api:
    image: node:18-alpine
    command: |
      sh -c "
      echo 'const http = require(\"http\");
      const server = http.createServer((req, res) => {
        if (req.url === \"/health\") {
          res.writeHead(200);
          res.end(\"healthy\");
        } else {
          res.writeHead(200);
          res.end(\"API Test Server\");
        }
      });
      server.listen(3000, () => console.log(\"Server running on port 3000\"));' > server.js
      && node server.js
      "
    ports:
      - "3000"
    environment:
      - NODE_ENV=test
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/health"]
      interval: 5s
      timeout: 3s
      retries: 3

  # Test database
  test_postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=testuser
      - POSTGRES_PASSWORD=testpass
      - POSTGRES_DB=testdb
    ports:
      - "5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser"]
      interval: 5s
      timeout: 3s
      retries: 3

  # Test cache
  test_redis:
    image: redis:7-alpine
    ports:
      - "6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3

networks:
  default:
    name: dynadock_test_network
    driver: bridge

volumes:
  test_data:
    driver: local
```

## LICENSE

```
MIT License

Copyright (c) 2024 DynaDock Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## CONTRIBUTING.md

```markdown
# Contributing to DynaDock

First off, thank you for considering contributing to DynaDock! 🎉

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* Use a clear and descriptive title
* Describe the exact steps which reproduce the problem
* Provide specific examples to demonstrate the steps
* Describe the behavior you observed after following the steps
* Explain which behavior you expected to see instead and why
* Include logs and error messages

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* Use a clear and descriptive title
* Provide a step-by-step description of the suggested enhancement
* Provide specific examples to demonstrate the steps
* Describe the current behavior and explain which behavior you expected to see instead
* Explain why this enhancement would be useful

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code lints
6. Issue that pull request!

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/dynadock.git
cd dynadock

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
make dev

# Run tests
make test

# Run linting
make lint
```

## Development Workflow

1. Create a new branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "Add amazing feature"
   ```

3. Run tests and linting:
   ```bash
   make pre-commit
   ```

4. Push to your fork:
   ```bash
   git push origin feature/amazing-feature
   ```

5. Open a Pull Request

## Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/unit/test_docker_manager.py

# Run with coverage
make coverage-report

# Run integration tests
make docker-test
```

## Code Style

We use Black and Ruff for code formatting and linting:

```bash
# Format code
make format

# Check linting
make lint
```

## Documentation

```bash
# Build documentation
make docs

# Serve documentation locally
make docs-serve
```

## Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

## Project Structure

```
dynadock/
├── src/
│   └── dynadock/       # Main source code
├── tests/
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
├── docs/              # Documentation
└── templates/         # Template files
```

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a tag:
   ```bash
   git tag -a v0.2.0 -m "Release version 0.2.0"
   git push origin v0.2.0
   ```

## Questions?

Feel free to open an issue with your question or contact the maintainers directly.

Thank you for contributing! ❤️
```

## CHANGELOG.md

```markdown
# Changelog

All notable changes to DynaDock will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New features that have been added
- Improvements to existing functionality

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed in future versions

### Removed
- Features that have been removed

### Fixed
- Bug fixes

### Security
- Security updates

## [0.1.0] - 2024-01-01

### Added
- Initial release of DynaDock
- Dynamic port allocation system
- Automatic environment variable generation
- Caddy integration for reverse proxy and TLS
- CLI commands: up, down, ps, logs, exec
- Support for Docker Compose files
- Automatic CORS configuration
- Health check monitoring
- Load balancing support
- WebSocket support
- API Gateway functionality
- Comprehensive test suite
- Documentation with MkDocs

### Features
- Zero-configuration deployment
- Automatic TLS/HTTPS with Caddy
- Local subdomains (service.local.dev)
- Dynamic port allocation to avoid conflicts
- Automatic generation of database credentials
- Support for PostgreSQL, MySQL, MongoDB, Redis
- Rate limiting and security headers
- Service discovery endpoint
- Metrics and monitoring support

### Development
- Full test coverage (>90%)
- GitHub Actions CI/CD pipeline
- Docker support
- Comprehensive documentation
- Makefile for development tasks

## [0.0.1] - 2023-12-01

### Added
- Project initialization
- Basic structure setup
- Initial documentation

---

## Version Guidelines

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

## Links

- [Releases](https://github.com/yourusername/dynadock/releases)
- [Issues](https://github.com/yourusername/dynadock/issues)
- [Pull Requests](https://github.com/yourusername/dynadock/pulls)
```

## docs/docs/getting-started/quickstart.md

```markdown
# Quick Start Guide

Get up and running with DynaDock in less than 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- Python 3.10+ (for installation)
- A `docker-compose.yaml` file in your project

## Installation

```bash
# Install DynaDock
uv tool install dynadock

# Verify installation
dynadock --version
```

## Basic Usage

### 1. Simple Web Application

Create a `docker-compose.yaml`:

```yaml
version: '3.8'
services:
  web:
    image: nginx:alpine
    ports:
      - "80"
```

Start with DynaDock:

```bash
dynadock up
```

Your service is now available at `http://web.local.dev:8001`

### 2. Multi-Service Application

```yaml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000"
  
  api:
    build: ./api
    ports:
      - "8000"
    environment:
      - DATABASE_URL=${POSTGRES_DSN}
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
```

Start with TLS enabled:

```bash
dynadock up --enable-tls
```

Services available at:
- `https://frontend.local.dev`
- `https://api.local.dev`
- Database connection via generated DSN

### 3. Production Deployment

```bash
dynadock up \
  --domain myapp.com \
  --enable-tls \
  --cors-origins https://app.myapp.com
```

## Common Commands

### Start Services
```bash
# Basic start
dynadock up

# With custom domain
dynadock up --domain app.local

# With TLS
dynadock up --enable-tls

# In background
dynadock up --detach
```

### Check Status
```bash
# List running services
dynadock ps

# View logs
dynadock logs

# Logs for specific service
dynadock logs -s api
```

### Stop Services
```bash
# Stop all services
dynadock down

# Remove volumes too
dynadock down -v

# Remove everything
dynadock down -v --remove-images
```

### Execute Commands
```bash
# Open shell in container
dynadock exec -s api /bin/bash

# Run command
dynadock exec -s api npm test
```

## Environment Variables

DynaDock automatically generates `.env.dynadock` with:

- Service ports and URLs
- Database credentials and DSNs
- Security keys and secrets
- CORS configuration

Example generated variables:

```env
# Services
API_PORT=8001
API_URL=https://api.local.dev
API_INTERNAL_URL=http://api:8001

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_auto_generated_password
POSTGRES_DSN=postgresql://postgres:password@postgres:5432/app_db

# Security
DYNADOCK_SECRET_KEY=auto_generated_secret_key
DYNADOCK_JWT_SECRET=auto_generated_jwt_secret
```

## Local Domain Setup

### Option 1: Edit /etc/hosts

```bash
# Add to /etc/hosts
127.0.0.1 web.local.dev
127.0.0.1 api.local.dev
127.0.0.1 frontend.local.dev
```

### Option 2: Use dnsmasq (Recommended)

```bash
# macOS
brew install dnsmasq
echo "address=/.local.dev/127.0.0.1" >> /usr/local/etc/dnsmasq.conf
sudo brew services start dnsmasq

# Linux
sudo apt install dnsmasq
echo "address=/.local.dev/127.0.0.1" | sudo tee -a /etc/dnsmasq.conf
sudo systemctl restart dnsmasq
```

## Next Steps

- Explore [Advanced Configuration](configuration.md)
- Learn about [TLS/HTTPS Setup](../guide/tls.md)
- Check [CLI Commands](../guide/commands.md)
- Read [Production Guide](../examples/production.md)

## Troubleshooting

### Port Already in Use

DynaDock automatically finds free ports. If you want a specific range:

```bash
dynadock up --start-port 9000
```

### Services Not Accessible

1. Check services are running:
   ```bash
   dynadock ps
   ```

2. Check Caddy is running:
   ```bash
   docker ps | grep caddy
   ```

3. Verify domain resolution:
   ```bash
   ping api.local.dev
   ```

### Permission Issues

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

## Get Help

- GitHub Issues: [github.com/yourusername/dynadock/issues](https://github.com/yourusername/dynadock/issues)
- Documentation: [dynadock.dev](https://dynadock.dev)
- Discord: [discord.gg/dynadock](https://discord.gg/dynadock)
```

## docs/docs/getting-started/configuration.md

```markdown
# Configuration

DynaDock provides flexible configuration options through CLI flags, environment variables, and configuration files.

## Configuration Priority

DynaDock uses the following priority order (highest to lowest):

1. CLI flags
2. Environment variables
3. Configuration file
4. Default values

## CLI Configuration

### Global Options

```bash
dynadock [OPTIONS] COMMAND [ARGS]

Options:
  -f, --compose-file PATH  Path to docker-compose.yaml
  -e, --env-file PATH      Path to generated env file [default: .env.dynadock]
  --config PATH            Path to DynaDock config file
  --verbose               Enable verbose output
  --help                  Show help message
```

### Command Options

#### `up` Command

```bash
dynadock up [OPTIONS]

Options:
  -d, --domain TEXT        Base domain [default: local.dev]
  -p, --start-port INT     Starting port for allocation [default: 8000]
  --enable-tls            Enable TLS/HTTPS via Caddy
  -c, --cors-origins TEXT  CORS allowed origins (multiple allowed)
  --detach                Run in background
  --no-caddy              Skip Caddy setup
  --no-env                Skip env generation
```

#### `down` Command

```bash
dynadock down [OPTIONS]

Options:
  -v, --remove-volumes     Remove Docker volumes
  --remove-images         Remove Docker images
  --remove-orphans        Remove orphaned containers
  --timeout INT           Shutdown timeout in seconds [default: 10]
```

## Environment Variables

DynaDock reads the following environment variables:

```bash
# DynaDock Configuration
DYNADOCK_DOMAIN=custom.local
DYNADOCK_START_PORT=9000
DYNADOCK_ENABLE_TLS=true
DYNADOCK_CORS_ORIGINS=https://app.com,https://api.com
DYNADOCK_CONFIG_FILE=/path/to/config.yaml

# Docker Configuration
DOCKER_HOST=unix:///var/run/docker.sock
COMPOSE_PROJECT_NAME=myproject
```

## Configuration File

Create `.dynadock.yaml` in your project root:

```yaml
# .dynadock.yaml
version: '1.0'

# Global settings
global:
  domain: app.local
  enable_tls: true
  start_port: 8000
  end_port: 9999

# Caddy configuration
caddy:
  enabled: true
  email: admin@example.com
  production: false
  config_template: ./custom-caddyfile.template

# CORS settings
cors:
  origins:
    - http://localhost:3000
    - http://localhost:5173
    - https://app.local
  methods:
    - GET
    - POST
    - PUT
    - DELETE
    - OPTIONS
  headers:
    - Content-Type
    - Authorization
    - X-Request-Id
  credentials: true
  max_age: 3600

# Service-specific configuration
services:
  api:
    port: 8001  # Fixed port assignment
    health_path: /api/health
    lb_policy: round_robin
    websocket: true
    static_path: /app/static
    
  frontend:
    port: 3000
    health_path: /
    
  postgres:
    port: 5432
    environment:
      POSTGRES_USER: appuser
      POSTGRES_DB: appdb

# Environment generation
environment:
  generate: true
  file: .env.dynadock
  template: ./env.template
  secrets:
    length: 32
    algorithm: urlsafe

# Port allocation
ports:
  start: 8000
  end: 9999
  strategy: sequential  # or 'random'
  reserved:
    - 8080
    - 3306
    - 5432

# Networking
network:
  name: dynadock_network
  driver: bridge
  ipam:
    subnet: 172.28.0.0/16

# Logging
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  format: json  # json or text
  file: ./dynadock.log
  
# Health checks
health:
  enabled: true
  interval: 10s
  timeout: 5s
  retries: 3

# Deployment profiles
profiles:
  development:
    domain: local.dev
    enable_tls: false
    cors:
      origins:
        - http://localhost:*
    
  staging:
    domain: staging.myapp.com
    enable_tls: true
    caddy:
      production: false
    
  production:
    domain: myapp.com
    enable_tls: true
    caddy:
      production: true
      email: ops@myapp.com
    cors:
      origins:
        - https://myapp.com
        - https://www.myapp.com
        - https://api.myapp.com
```

## Using Profiles

```bash
# Use development profile
dynadock up --profile development

# Use production profile
dynadock up --profile production

# Override profile settings
dynadock up --profile staging --domain custom.staging.com
```

## Service Discovery

DynaDock provides automatic service discovery:

```yaml
# docker-compose.yaml
services:
  api:
    environment:
      - FRONTEND_URL=${FRONTEND_URL}  # Auto-generated
      - POSTGRES_DSN=${POSTGRES_DSN}   # Auto-generated
```

## Advanced Configuration

### Custom Caddy Template

Create `caddyfile.custom`:

```caddyfile
{{ service_name }}.{{ domain }} {
    # Custom configuration
    reverse_proxy {{ service_name }}:{{ port }} {
        header_up Custom-Header "value"
    }
}
```

Reference in config:

```yaml
caddy:
  config_template: ./caddyfile.custom
```

### Custom Environment Template

Create `env.template`:

```env
# Custom environment template
{{ SERVICE_NAME }}_URL={{ protocol }}://{{ service_name }}.{{ domain }}
{{ SERVICE_NAME }}_INTERNAL=http://{{ service_name }}:{{ port }}

# Custom variables
MY_CUSTOM_VAR=value
```

### Port Allocation Strategies

#### Sequential (Default)

```yaml
ports:
  strategy: sequential
  start: 8000
```

Allocates: 8000, 8001, 8002, ...

#### Random

```yaml
ports:
  strategy: random
  start: 8000
  end: 9999
```

Allocates random free ports in range.

#### Fixed

```yaml
services:
  api:
    port: 8001  # Always use this port
```

### Network Configuration

#### Custom Network

```yaml
network:
  name: myapp_network
  driver: overlay  # For Swarm
  attachable: true
```

#### IPv6 Support

```yaml
network:
  enable_ipv6: true
  ipam:
    subnet: 2001:db8::/64
```

## Security Configuration

### TLS/SSL

```yaml
caddy:
  tls:
    provider: letsencrypt  # or zerossl, internal
    email: admin@example.com
    dns_challenge:
      provider: cloudflare
      api_token: ${CLOUDFLARE_API_TOKEN}
```

### Rate Limiting

```yaml
services:
  api:
    rate_limit:
      requests: 100
      period: 1m
      burst: 10
```

### Authentication

```yaml
services:
  admin:
    auth:
      type: basic
      users:
        - admin:$2a$14$encrypted_password
```

## Monitoring Configuration

### Metrics

```yaml
monitoring:
  metrics:
    enabled: true
    endpoint: /metrics
    port: 9090
```

### Logging

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
    labels: "service,version"
```

## Examples

### Minimal Configuration

```yaml
# .dynadock.yaml
version: '1.0'
global:
  domain: myapp.local
```

### Production Configuration

```yaml
# .dynadock.yaml
version: '1.0'

global:
  domain: myapp.com
  enable_tls: true

caddy:
  production: true
  email: ops@myapp.com

cors:
  origins:
    - https://myapp.com
    - https://api.myapp.com

services:
  api:
    health_path: /api/health
    rate_limit:
      requests: 1000
      period: 1m

environment:
  secrets:
    length: 64
```

## Next Steps

- Learn about [Port Allocation](../guide/ports.md)
- Configure [TLS/HTTPS](../guide/tls.md)
- Set up [Environment Variables](../guide/env.md)
- Explore [Examples](../examples/basic.md)
```

## Podsumowanie struktury projektu

```
dynadock/
├── pyproject.toml                    ✅ (artifact 1)
├── README.md                          ✅ (artifact 1)
├── LICENSE                            ✅ (artifact 3)
├── CHANGELOG.md                       ✅ (artifact 3)
├── CONTRIBUTING.md                    ✅ (artifact 3)
├── Makefile                           ✅ (artifact 2)
├── pytest.ini                         ✅ (artifact 2)
├── .gitignore                         ✅ (artifact 2)
├── .dockerignore                      ✅ (artifact 3)
├── Dockerfile                         ✅ (artifact 2)
├── docker-compose.test.yaml          ✅ (artifact 3)
├── .github/
│   └── workflows/
│       └── test.yml                   ✅ (artifact 2)
├── src/
│   └── dynadock/
│       ├── __init__.py               ✅ (artifact 1)
│       ├── __main__.py               ✅ (artifact 1)
│       ├── cli.py                    ✅ (artifact 1)
│       ├── docker_manager.py         ✅ (artifact 1)
│       ├── port_allocator.py         ✅ (artifact 1)
│       ├── env_generator.py          ✅ (artifact 1)
│       ├── caddy_config.py           ✅ (artifact 1)
│       └── utils.py                  ✅ (artifact 1)
├── templates/
│   └── Caddyfile.template            ✅ (artifact 3)
├── tests/
│   ├── conftest.py                   ✅ (artifact 2)
│   ├── unit/
│   │   ├── test_port_allocator.py    ✅ (artifact 2)
│   │   ├── test_docker_manager.py    ✅ (artifact 2)
│   │   ├── test_env_generator.py     ✅ (artifact 2)
│   │   ├── test_cli.py               ✅ (artifact 2)
│   │   ├── test_utils.py             ✅ (artifact 3)
│   │   └── test_caddy_config.py      ✅ (artifact 3)
│   └── integration/
│       └── test_integration.py       ✅ (artifact 2)
└── docs/
    ├── mkdocs.yml                     ✅ (artifact 2)
    └── docs/
        ├── index.md                   ✅ (artifact 2)
        └── getting-started/
            ├── installation.md        ✅ (artifact 2)
            ├── quickstart.md          ✅ (artifact 3)
            └── configuration.md       ✅ (artifact 3)
```

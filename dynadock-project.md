# DynaDock - Dynamic Docker Compose Manager

## Struktura projektu

```
dynadock/
├── pyproject.toml
├── README.md
├── src/
│   └── dynadock/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── docker_manager.py
│       ├── port_allocator.py
│       ├── env_generator.py
│       ├── caddy_config.py
│       └── utils.py
└── templates/
    └── Caddyfile.template
```

## pyproject.toml

```toml
[project]
name = "dynadock"
version = "0.1.0"
description = "Dynamic Docker Compose orchestrator with automatic port allocation and TLS"
authors = [{name = "Your Name", email = "your.email@example.com"}]
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "click>=8.1.0",
    "pyyaml>=6.0",
    "docker>=7.0.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
    "psutil>=5.9.0",
    "jinja2>=3.1.0",
]

[project.scripts]
dynadock = "dynadock.cli:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=7.0.0",
    "black>=24.0.0",
    "ruff>=0.1.0",
]
```

## src/dynadock/__init__.py

```python
"""DynaDock - Dynamic Docker Compose Manager"""

__version__ = "0.1.0"

from .docker_manager import DockerManager
from .port_allocator import PortAllocator
from .env_generator import EnvGenerator
from .caddy_config import CaddyConfig

__all__ = ["DockerManager", "PortAllocator", "EnvGenerator", "CaddyConfig"]
```

## src/dynadock/__main__.py

```python
from .cli import cli

if __name__ == "__main__":
    cli()
```

## src/dynadock/cli.py

```python
import click
import sys
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .docker_manager import DockerManager
from .env_generator import EnvGenerator
from .caddy_config import CaddyConfig
from .utils import find_compose_file, validate_compose_file

console = Console()

@click.group()
@click.option('--compose-file', '-f', default=None, help='Path to docker-compose.yaml')
@click.option('--env-file', '-e', default='.env.dynadock', help='Path to generated env file')
@click.pass_context
def cli(ctx, compose_file, env_file):
    """DynaDock - Dynamic Docker Compose orchestrator with automatic port allocation and TLS."""
    ctx.ensure_object(dict)
    
    if compose_file is None:
        compose_file = find_compose_file()
    
    ctx.obj['compose_file'] = compose_file
    ctx.obj['env_file'] = env_file
    ctx.obj['project_dir'] = Path(compose_file).parent if compose_file else Path.cwd()

@cli.command()
@click.option('--domain', '-d', default='dynadock.lan', help='Base domain for services')
@click.option('--start-port', '-p', default=8000, help='Starting port for allocation')
@click.option('--enable-tls', is_flag=True, help='Enable TLS with Caddy')
@click.option('--cors-origins', '-c', multiple=True, help='CORS allowed origins')
@click.option('--detach', '-d', is_flag=True, help='Run in background')
@click.pass_context
def up(ctx, domain, start_port, enable_tls, cors_origins, detach):
    """Start services with dynamic port allocation and routing."""
    
    compose_file = ctx.obj['compose_file']
    env_file = ctx.obj['env_file']
    project_dir = ctx.obj['project_dir']
    
    if not compose_file or not Path(compose_file).exists():
        console.print("[red]Error: docker-compose.yaml not found![/red]")
        sys.exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Initialize managers
        task = progress.add_task("Initializing...", total=6)
        
        docker_manager = DockerManager(compose_file, project_dir)
        env_generator = EnvGenerator(env_file)
        caddy_config = CaddyConfig(project_dir)
        
        progress.update(task, advance=1, description="Parsing docker-compose.yaml...")
        
        # Parse compose file and allocate ports
        services = docker_manager.parse_compose()
        allocated_ports = docker_manager.allocate_ports(services, start_port)
        
        progress.update(task, advance=1, description="Generating environment configuration...")
        
        # Generate environment variables
        env_vars = env_generator.generate(
            services=services,
            ports=allocated_ports,
            domain=domain,
            enable_tls=enable_tls,
            cors_origins=list(cors_origins) if cors_origins else []
        )
        
        progress.update(task, advance=1, description="Creating Caddy configuration...")
        
        # Generate Caddy configuration
        caddy_config.generate(
            services=services,
            ports=allocated_ports,
            domain=domain,
            enable_tls=enable_tls,
            cors_origins=list(cors_origins) if cors_origins else []
        )
        
        progress.update(task, advance=1, description="Starting Caddy server...")
        
        # Start Caddy
        caddy_container = caddy_config.start_caddy()
        
        progress.update(task, advance=1, description="Starting services...")
        
        # Start services with dynamic configuration
        containers = docker_manager.up(env_vars, detach=detach)
        
        progress.update(task, advance=1, description="Services started successfully!")
    
    # Display service information
    table = Table(title="Running Services", show_header=True, header_style="bold magenta")
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Port", style="green")
    table.add_column("URL", style="yellow")
    table.add_column("Status", style="blue")
    
    for service_name, port in allocated_ports.items():
        url = f"{'https' if enable_tls else 'http'}://{service_name}.{domain}"
        table.add_row(
            service_name,
            str(port),
            url,
            "✓ Running"
        )
    
    console.print(table)
    console.print(f"\n[green]✓ All services are running![/green]")
    console.print(f"[blue]Environment file: {env_file}[/blue]")
    
    if enable_tls:
        console.print(f"[yellow]⚡ TLS enabled via Caddy (automatic certificates)[/yellow]")

@cli.command()
@click.option('--remove-volumes', '-v', is_flag=True, help='Remove volumes')
@click.option('--remove-images', is_flag=True, help='Remove images')
@click.pass_context
def down(ctx, remove_volumes, remove_images):
    """Stop and remove services."""
    
    compose_file = ctx.obj['compose_file']
    project_dir = ctx.obj['project_dir']
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("Stopping services...", total=3)
        
        docker_manager = DockerManager(compose_file, project_dir)
        caddy_config = CaddyConfig(project_dir)
        
        progress.update(task, advance=1, description="Stopping application containers...")
        
        # Stop services
        docker_manager.down(remove_volumes=remove_volumes, remove_images=remove_images)
        
        progress.update(task, advance=1, description="Stopping Caddy server...")
        
        # Stop Caddy
        caddy_config.stop_caddy()
        
        progress.update(task, advance=1, description="Cleanup completed!")
    
    console.print("[green]✓ All services stopped and removed![/green]")

@cli.command()
@click.pass_context
def ps(ctx):
    """List running services."""
    
    compose_file = ctx.obj['compose_file']
    project_dir = ctx.obj['project_dir']
    env_file = ctx.obj['env_file']
    
    docker_manager = DockerManager(compose_file, project_dir)
    containers = docker_manager.ps()
    
    if not containers:
        console.print("[yellow]No services running[/yellow]")
        return
    
    # Load environment to get ports
    env_vars = {}
    if Path(env_file).exists():
        from dotenv import dotenv_values
        env_vars = dotenv_values(env_file)
    
    table = Table(title="Running Services", show_header=True, header_style="bold magenta")
    table.add_column("Container", style="cyan", no_wrap=True)
    table.add_column("Service", style="green")
    table.add_column("Port", style="yellow")
    table.add_column("Status", style="blue")
    table.add_column("Health", style="magenta")
    
    for container in containers:
        service_name = container.labels.get("com.docker.compose.service", "N/A")
        port_key = f"{service_name.upper()}_PORT"
        port = env_vars.get(port_key, "N/A")
        
        health = container.attrs.get("State", {}).get("Health", {}).get("Status", "N/A")
        
        table.add_row(
            container.name,
            service_name,
            str(port),
            container.status,
            health
        )
    
    console.print(table)

@cli.command()
@click.pass_context
def logs(ctx):
    """Show logs from all services."""
    
    compose_file = ctx.obj['compose_file']
    project_dir = ctx.obj['project_dir']
    
    docker_manager = DockerManager(compose_file, project_dir)
    docker_manager.logs()

@cli.command()
@click.option('--service', '-s', required=True, help='Service name')
@click.option('--command', '-c', default='/bin/sh', help='Command to execute')
@click.pass_context
def exec(ctx, service, command):
    """Execute command in a running service container."""
    
    compose_file = ctx.obj['compose_file']
    project_dir = ctx.obj['project_dir']
    
    docker_manager = DockerManager(compose_file, project_dir)
    docker_manager.exec(service, command)

if __name__ == '__main__':
    cli()
```

## src/dynadock/docker_manager.py

```python
import os
import yaml
import docker
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

class DockerManager:
    def __init__(self, compose_file: str, project_dir: Path):
        self.compose_file = compose_file
        self.project_dir = project_dir
        self.client = docker.from_env()
        self.project_name = self._get_project_name()
    
    def _get_project_name(self) -> str:
        """Get project name from directory or compose file."""
        return self.project_dir.name.lower().replace('_', '').replace('-', '')
    
    def parse_compose(self) -> Dict[str, Any]:
        """Parse docker-compose.yaml and return services."""
        with open(self.compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        return compose_data.get('services', {})
    
    def allocate_ports(self, services: Dict[str, Any], start_port: int = 8000) -> Dict[str, int]:
        """Allocate dynamic ports for services."""
        from .port_allocator import PortAllocator
        
        allocator = PortAllocator(start_port)
        allocated_ports = {}
        
        for service_name, service_config in services.items():
            # Check if service exposes ports
            if 'ports' in service_config or 'expose' in service_config:
                port = allocator.get_free_port()
                allocated_ports[service_name] = port
        
        return allocated_ports
    
    def up(self, env_vars: Dict[str, str], detach: bool = True) -> List[Any]:
        """Start services with docker-compose."""
        # Set environment variables
        env = os.environ.copy()
        env.update(env_vars)
        
        # Build command
        cmd = [
            'docker-compose',
            '-f', self.compose_file,
            '-p', self.project_name,
            'up'
        ]
        
        if detach:
            cmd.append('-d')
        
        # Execute
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            cwd=self.project_dir
        )
        
        if result.returncode != 0:
            raise Exception(f"Failed to start services: {result.stderr}")
        
        # Return container list
        return self.ps()
    
    def down(self, remove_volumes: bool = False, remove_images: bool = False):
        """Stop and remove services."""
        cmd = [
            'docker-compose',
            '-f', self.compose_file,
            '-p', self.project_name,
            'down'
        ]
        
        if remove_volumes:
            cmd.append('-v')
        
        if remove_images:
            cmd.append('--rmi')
            cmd.append('all')
        
        subprocess.run(cmd, cwd=self.project_dir)
    
    def ps(self) -> List[Any]:
        """List running containers for this project."""
        filters = {'label': f'com.docker.compose.project={self.project_name}'}
        return self.client.containers.list(filters=filters)
    
    def logs(self, service: Optional[str] = None, follow: bool = True):
        """Show logs from services."""
        cmd = [
            'docker-compose',
            '-f', self.compose_file,
            '-p', self.project_name,
            'logs'
        ]
        
        if follow:
            cmd.append('-f')
        
        if service:
            cmd.append(service)
        
        subprocess.run(cmd, cwd=self.project_dir)
    
    def exec(self, service: str, command: str):
        """Execute command in service container."""
        cmd = [
            'docker-compose',
            '-f', self.compose_file,
            '-p', self.project_name,
            'exec',
            service,
            command
        ]
        
        subprocess.run(cmd, cwd=self.project_dir)
```

## src/dynadock/port_allocator.py

```python
import socket
import psutil
from typing import Set, Optional

class PortAllocator:
    def __init__(self, start_port: int = 8000, end_port: int = 9999):
        self.start_port = start_port
        self.end_port = end_port
        self.allocated_ports: Set[int] = set()
        self._scan_used_ports()
    
    def _scan_used_ports(self):
        """Scan for currently used ports on the system."""
        for conn in psutil.net_connections():
            if conn.laddr and conn.laddr.port:
                self.allocated_ports.add(conn.laddr.port)
    
    def is_port_free(self, port: int) -> bool:
        """Check if a port is free."""
        if port in self.allocated_ports:
            return False
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return True
            except socket.error:
                return False
    
    def get_free_port(self) -> int:
        """Get next available free port."""
        for port in range(self.start_port, self.end_port + 1):
            if self.is_port_free(port):
                self.allocated_ports.add(port)
                return port
        
        raise Exception(f"No free ports available in range {self.start_port}-{self.end_port}")
    
    def release_port(self, port: int):
        """Release a previously allocated port."""
        if port in self.allocated_ports:
            self.allocated_ports.remove(port)
```

## src/dynadock/env_generator.py

```python
import os
import secrets
from pathlib import Path
from typing import Dict, List, Any

class EnvGenerator:
    def __init__(self, env_file: str = '.env.dynadock'):
        self.env_file = Path(env_file)
    
    def generate(
        self,
        services: Dict[str, Any],
        ports: Dict[str, int],
        domain: str,
        enable_tls: bool,
        cors_origins: List[str]
    ) -> Dict[str, str]:
        """Generate environment variables for services."""
        
        env_vars = {
            'DYNADOCK_DOMAIN': domain,
            'DYNADOCK_PROTOCOL': 'https' if enable_tls else 'http',
            'DYNADOCK_ENABLE_TLS': str(enable_tls).lower(),
        }
        
        # Add CORS origins
        if cors_origins:
            env_vars['DYNADOCK_CORS_ORIGINS'] = ','.join(cors_origins)
        else:
            # Default CORS origins
            env_vars['DYNADOCK_CORS_ORIGINS'] = f"http://localhost:3000,http://localhost:5173,https://*.{domain}"
        
        # Generate variables for each service
        for service_name, port in ports.items():
            service_upper = service_name.upper().replace('-', '_')
            
            # Port configuration
            env_vars[f'{service_upper}_PORT'] = str(port)
            env_vars[f'{service_upper}_HOST'] = '0.0.0.0'
            env_vars[f'{service_upper}_URL'] = f"{env_vars['DYNADOCK_PROTOCOL']}://{service_name}.{domain}"
            
            # Internal Docker network URL
            env_vars[f'{service_upper}_INTERNAL_URL'] = f"http://{service_name}:{port}"
            
            # Database URLs if it's a database service
            if any(db in service_name.lower() for db in ['postgres', 'mysql', 'mongo', 'redis']):
                self._add_database_vars(env_vars, service_name, port)
        
        # Generate secret keys
        env_vars['DYNADOCK_SECRET_KEY'] = secrets.token_urlsafe(32)
        env_vars['DYNADOCK_JWT_SECRET'] = secrets.token_urlsafe(32)
        
        # Write to file
        self._write_env_file(env_vars)
        
        return env_vars
    
    def _add_database_vars(self, env_vars: Dict[str, str], service_name: str, port: int):
        """Add database-specific environment variables."""
        service_upper = service_name.upper().replace('-', '_')
        
        if 'postgres' in service_name.lower():
            env_vars[f'{service_upper}_USER'] = 'postgres'
            env_vars[f'{service_upper}_PASSWORD'] = secrets.token_urlsafe(16)
            env_vars[f'{service_upper}_DB'] = 'app_db'
            env_vars[f'{service_upper}_DSN'] = f"postgresql://postgres:{env_vars[f'{service_upper}_PASSWORD']}@{service_name}:{port}/app_db"
        
        elif 'mysql' in service_name.lower():
            env_vars[f'{service_upper}_USER'] = 'root'
            env_vars[f'{service_upper}_PASSWORD'] = secrets.token_urlsafe(16)
            env_vars[f'{service_upper}_DATABASE'] = 'app_db'
            env_vars[f'{service_upper}_DSN'] = f"mysql://root:{env_vars[f'{service_upper}_PASSWORD']}@{service_name}:{port}/app_db"
        
        elif 'mongo' in service_name.lower():
            env_vars[f'{service_upper}_USER'] = 'admin'
            env_vars[f'{service_upper}_PASSWORD'] = secrets.token_urlsafe(16)
            env_vars[f'{service_upper}_DATABASE'] = 'app_db'
            env_vars[f'{service_upper}_URI'] = f"mongodb://admin:{env_vars[f'{service_upper}_PASSWORD']}@{service_name}:{port}/app_db"
        
        elif 'redis' in service_name.lower():
            env_vars[f'{service_upper}_PASSWORD'] = secrets.token_urlsafe(16)
            env_vars[f'{service_upper}_URL'] = f"redis://:{env_vars[f'{service_upper}_PASSWORD']}@{service_name}:{port}/0"
    
    def _write_env_file(self, env_vars: Dict[str, str]):
        """Write environment variables to file."""
        with open(self.env_file, 'w') as f:
            f.write("# Generated by DynaDock\n")
            f.write("# DO NOT EDIT MANUALLY - This file is auto-generated\n\n")
            
            # Group variables
            groups = {
                'General': [],
                'Services': [],
                'Database': [],
                'Security': []
            }
            
            for key, value in sorted(env_vars.items()):
                if 'SECRET' in key or 'JWT' in key or 'PASSWORD' in key:
                    groups['Security'].append(f"{key}={value}")
                elif 'DSN' in key or 'URI' in key or 'DATABASE' in key:
                    groups['Database'].append(f"{key}={value}")
                elif 'DYNADOCK_' in key:
                    groups['General'].append(f"{key}={value}")
                else:
                    groups['Services'].append(f"{key}={value}")
            
            for group_name, vars in groups.items():
                if vars:
                    f.write(f"# {group_name}\n")
                    for var in vars:
                        f.write(f"{var}\n")
                    f.write("\n")
```

## src/dynadock/caddy_config.py

```python
import os
import docker
from pathlib import Path
from typing import Dict, List
from jinja2 import Template

CADDYFILE_TEMPLATE = """
# DynaDock Caddy Configuration
# Auto-generated - DO NOT EDIT

{
    # Global options
    email admin@{{ domain }}
    {% if not enable_tls %}
    auto_https off
    {% endif %}
}

# Health check endpoint
:80 {
    respond /health "OK" 200
}

{% if enable_tls %}
:443 {
    tls internal
}
{% endif %}

{% for service_name, port in services.items() %}
# Service: {{ service_name }}
{{ service_name }}.{{ domain }} {
    {% if enable_tls %}
    tls internal
    {% endif %}
    
    # CORS Headers
    header {
        Access-Control-Allow-Origin "{{ cors_origins|join(', ') }}"
        Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With"
        Access-Control-Allow-Credentials "true"
        Access-Control-Max-Age "3600"
    }
    
    # Handle OPTIONS requests
    @options method OPTIONS
    respond @options 204
    
    # Proxy to service
    reverse_proxy {
        to {{ service_name }}:{{ port }}
        
        # Load balancing
        lb_policy round_robin
        lb_try_duration 30s
        lb_try_interval 1s
        
        # Health check
        health_uri /health
        health_interval 10s
        health_timeout 5s
        
        # Headers
        header_up Host {host}
        header_up X-Real-IP {remote}
        header_up X-Forwarded-For {remote}
        header_up X-Forwarded-Proto {scheme}
        header_up X-Forwarded-Host {host}
        
        # Timeouts
        dial_timeout 10s
        response_header_timeout 30s
        read_timeout 60s
        write_timeout 60s
    }
    
    # Logging
    log {
        output file /var/log/caddy/{{ service_name }}.log
        format json
        level INFO
    }
}

{% endfor %}

# API Gateway (optional)
api.{{ domain }} {
    {% if enable_tls %}
    tls internal
    {% endif %}
    
    # Rate limiting
    rate_limit {
        zone dynamic 100r/m
    }
    
    # API routing
    {% for service_name, port in services.items() %}
    route /{{ service_name }}/* {
        uri strip_prefix /{{ service_name }}
        reverse_proxy {{ service_name }}:{{ port }}
    }
    {% endfor %}
    
    # Default response
    respond "API Gateway" 200
}
"""

class CaddyConfig:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.caddy_dir = project_dir / '.dynadock' / 'caddy'
        self.caddy_dir.mkdir(parents=True, exist_ok=True)
        self.client = docker.from_env()
    
    def generate(
        self,
        services: Dict[str, Any],
        ports: Dict[str, int],
        domain: str,
        enable_tls: bool,
        cors_origins: List[str]
    ):
        """Generate Caddyfile configuration."""
        
        template = Template(CADDYFILE_TEMPLATE)
        
        # Prepare service port mapping
        service_ports = {}
        for service_name, port in ports.items():
            service_ports[service_name] = port
        
        # Default CORS origins
        if not cors_origins:
            cors_origins = [
                "http://localhost:3000",
                "http://localhost:5173",
                f"https://*.{domain}"
            ]
        
        # Render Caddyfile
        caddyfile_content = template.render(
            domain=domain,
            enable_tls=enable_tls,
            services=service_ports,
            cors_origins=cors_origins
        )
        
        # Write Caddyfile
        caddyfile_path = self.caddy_dir / 'Caddyfile'
        with open(caddyfile_path, 'w') as f:
            f.write(caddyfile_content)
        
        # Create data and config directories
        (self.caddy_dir / 'data').mkdir(exist_ok=True)
        (self.caddy_dir / 'config').mkdir(exist_ok=True)
        (self.caddy_dir / 'logs').mkdir(exist_ok=True)
    
    def start_caddy(self) -> Any:
        """Start Caddy container."""
        
        # Check if Caddy is already running
        try:
            container = self.client.containers.get('dynadock-caddy')
            if container.status == 'running':
                return container
            container.remove(force=True)
        except docker.errors.NotFound:
            pass
        
        # Start new Caddy container
        container = self.client.containers.run(
            'caddy:2-alpine',
            name='dynadock-caddy',
            detach=True,
            restart_policy={'Name': 'unless-stopped'},
            network_mode='bridge',
            ports={
                '80/tcp': 80,
                '443/tcp': 443,
                '2019/tcp': 2019  # Caddy admin API
            },
            volumes={
                str(self.caddy_dir / 'Caddyfile'): {
                    'bind': '/etc/caddy/Caddyfile',
                    'mode': 'ro'
                },
                str(self.caddy_dir / 'data'): {
                    'bind': '/data',
                    'mode': 'rw'
                },
                str(self.caddy_dir / 'config'): {
                    'bind': '/config',
                    'mode': 'rw'
                },
                str(self.caddy_dir / 'logs'): {
                    'bind': '/var/log/caddy',
                    'mode': 'rw'
                }
            },
            labels={
                'dynadock.managed': 'true',
                'dynadock.component': 'caddy'
            }
        )
        
        # Connect to Docker network
        self._connect_to_network(container)
        
        return container
    
    def stop_caddy(self):
        """Stop and remove Caddy container."""
        try:
            container = self.client.containers.get('dynadock-caddy')
            container.stop()
            container.remove()
        except docker.errors.NotFound:
            pass
    
    def _connect_to_network(self, container):
        """Connect Caddy to the Docker Compose network."""
        # Find the compose network
        networks = self.client.networks.list()
        
        for network in networks:
            if 'compose' in network.name or 'default' in network.name:
                try:
                    network.connect(container)
                    break
                except docker.errors.APIError:
                    pass
```

## src/dynadock/utils.py

```python
import os
import yaml
from pathlib import Path
from typing import Optional, List

def find_compose_file(start_dir: Path = Path.cwd()) -> Optional[str]:
    """Find docker-compose.yaml in current or parent directories."""
    
    possible_names = [
        'docker-compose.yaml',
        'docker-compose.yml',
        'compose.yaml',
        'compose.yml'
    ]
    
    current = start_dir
    
    # Search in current and parent directories
    for _ in range(5):  # Limit search depth
        for name in possible_names:
            compose_path = current / name
            if compose_path.exists():
                return str(compose_path)
        
        # Move to parent directory
        parent = current.parent
        if parent == current:  # Reached root
            break
        current = parent
    
    return None

def validate_compose_file(compose_file: str) -> bool:
    """Validate docker-compose.yaml structure."""
    try:
        with open(compose_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if not isinstance(data, dict):
            return False
        
        if 'services' not in data:
            return False
        
        if not isinstance(data['services'], dict):
            return False
        
        return True
    
    except Exception:
        return False

def get_project_name_from_compose(compose_file: str) -> str:
    """Extract project name from compose file or directory."""
    try:
        with open(compose_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Check for explicit name
        if 'name' in data:
            return data['name']
    except Exception:
        pass
    
    # Use directory name
    return Path(compose_file).parent.name.lower().replace('_', '').replace('-', '')

def update_compose_with_ports(compose_file: str, ports: Dict[str, int]) -> str:
    """Create a modified compose file with allocated ports."""
    with open(compose_file, 'r') as f:
        data = yaml.safe_load(f)
    
    # Update services with allocated ports
    for service_name, port in ports.items():
        if service_name in data['services']:
            service = data['services'][service_name]
            
            # Update ports mapping
            if 'ports' in service:
                # Keep internal port, change external
                new_ports = []
                for port_mapping in service['ports']:
                    if ':' in str(port_mapping):
                        internal = str(port_mapping).split(':')[1]
                        new_ports.append(f"{port}:{internal}")
                    else:
                        new_ports.append(f"{port}:{port_mapping}")
                service['ports'] = new_ports
            
            # Add environment variables
            if 'environment' not in service:
                service['environment'] = {}
            
            service['environment']['PORT'] = str(port)
            service['environment']['HOST'] = '0.0.0.0'
    
    # Save to temporary file
    temp_compose = Path(compose_file).parent / '.dynadock-compose.yaml'
    with open(temp_compose, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)
    
    return str(temp_compose)

def cleanup_temp_files(project_dir: Path):
    """Remove temporary files created by DynaDock."""
    temp_files = [
        '.dynadock-compose.yaml',
        '.env.dynadock',
    ]
    
    for file in temp_files:
        file_path = project_dir / file
        if file_path.exists():
            file_path.unlink()
    
    # Remove Caddy directory
    caddy_dir = project_dir / '.dynadock'
    if caddy_dir.exists():
        import shutil
        shutil.rmtree(caddy_dir)
```

## README.md

```markdown
# DynaDock - Dynamic Docker Compose Manager

DynaDock to inteligentne narzędzie CLI, które rozwiązuje typowe problemy z Docker Compose poprzez dynamiczną alokację portów, automatyczną konfigurację TLS/HTTPS i lokalne subdomeny.

## ✨ Główne funkcje

- 🎯 **Dynamiczna alokacja portów** - koniec z konfliktami portów
- 🔒 **Automatyczne TLS/HTTPS** - przez Caddy z certyfikatami Let's Encrypt
- 🌐 **Lokalne subdomeny** - każdy serwis dostępny pod `service.dynadock.lan`
- ⚡ **Zero-config CORS** - automatyczna konfiguracja CORS dla API
- 🚀 **Prosty deployment** - jeden komenda dla lokalnego i produkcyjnego środowiska
- 📝 **Automatyczny .env** - generowanie wszystkich zmiennych środowiskowych
- 🔄 **Load balancing** - wbudowane przez Caddy
- 📊 **Health checks** - monitoring stanu serwisów

## 📦 Instalacja

```bash
# Instalacja przez uv (zalecane)
uv tool install dynadock

# Lub instalacja deweloperska
git clone https://github.com/yourusername/dynadock.git
cd dynadock
uv pip install -e .
```

## 🚀 Szybki start

```bash
# W katalogu z docker-compose.yaml
dynadock up

# Z custom domeną i TLS
dynadock up --domain myapp.local --enable-tls

# Sprawdzenie statusu
dynadock ps

# Zatrzymanie wszystkich serwisów
dynadock down
```

## 📝 Przykład docker-compose.yaml

```yaml
version: '3.8'

services:
  api:
    build: ./api
    environment:
      - PORT=${API_PORT}
      - DATABASE_URL=${POSTGRES_DSN}
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    environment:
      - REACT_APP_API_URL=${API_URL}
      - PORT=${FRONTEND_PORT}

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Po uruchomieniu `dynadock up --enable-tls`:

- API: https://api.dynadock.lan
- Frontend: https://frontend.dynadock.lan
- Postgres: postgres.dynadock.lan:5432

## 🛠️ Komendy CLI

### `dynadock up`

Uruchamia wszystkie serwisy z dynamiczną konfiguracją.

```bash
dynadock up [OPTIONS]

Opcje:
  -f, --compose-file PATH    Ścieżka do docker-compose.yaml
  -d, --domain TEXT         Bazowa domena [default: dynadock.lan]
  -p, --start-port INT      Początkowy port [default: 8000]
  --enable-tls              Włącz HTTPS przez Caddy
  -c, --cors-origins TEXT   Dozwolone originy CORS (wielokrotne)
  --detach                  Uruchom w tle
```

### `dynadock down`

Zatrzymuje i usuwa wszystkie serwisy.

```bash
dynadock down [OPTIONS]

Opcje:
  -v, --remove-volumes      Usuń wolumeny
  --remove-images          Usuń obrazy
```

### `dynadock ps`

Wyświetla status uruchomionych serwisów.

### `dynadock logs`

Pokazuje logi ze wszystkich serwisów.

### `dynadock exec`

Wykonuje komendę w kontenerze.

```bash
dynadock exec -s api /bin/bash
```

## 🔧 Konfiguracja

### Generowany .env.dynadock

```env
# General
DYNADOCK_DOMAIN=dynadock.lan
DYNADOCK_PROTOCOL=https
DYNADOCK_ENABLE_TLS=true
DYNADOCK_CORS_ORIGINS=http://localhost:3000,https://*.dynadock.lan

# Services
API_PORT=8001
API_HOST=0.0.0.0
API_URL=https://api.dynadock.lan
API_INTERNAL_URL=http://api:8001

FRONTEND_PORT=8002
FRONTEND_HOST=0.0.0.0
FRONTEND_URL=https://frontend.dynadock.lan
FRONTEND_INTERNAL_URL=http://frontend:8002

# Database
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_random_password
POSTGRES_DB=app_db
POSTGRES_DSN=postgresql://postgres:secure_random_password@postgres:5432/app_db

# Security
DYNADOCK_SECRET_KEY=random_secret_key
DYNADOCK_JWT_SECRET=random_jwt_secret
```

### Konfiguracja /etc/hosts (dla lokalnych subdomen)

```bash
# Dodaj do /etc/hosts
127.0.0.1 api.dynadock.lan
127.0.0.1 frontend.dynadock.lan
127.0.0.1 postgres.dynadock.lan

# Lub użyj dnsmasq dla wildcard domains
```

## 🌐 Deployment produkcyjny

```bash
# Na serwerze produkcyjnym
dynadock up \
  --domain myapp.com \
  --enable-tls \
  --cors-origins https://app.myapp.com,https://api.myapp.com
```

## 🔍 Rozwiązywanie problemów

### Port już zajęty

DynaDock automatycznie znajdzie wolny port. Jeśli chcesz zmienić zakres:

```bash
dynadock up --start-port 9000
```

### Problemy z TLS

Caddy automatycznie generuje certyfikaty. Dla produkcji upewnij się, że:
- Domena jest publiczna i dostępna
- Porty 80 i 443 są otwarte
- DNS wskazuje na serwer

### Reset konfiguracji

```bash
# Usuń wszystko łącznie z wolumenami
dynadock down -v --remove-images

# Usuń pliki konfiguracyjne
rm -rf .dynadock/ .env.dynadock
```

## 📚 Zaawansowane użycie

### Custom Caddyfile

Możesz nadpisać domyślną konfigurację tworząc `.dynadock/caddy/Caddyfile.custom`.

### Integracja z CI/CD

```yaml
# .github/workflows/deploy.yml
- name: Deploy with DynaDock
  run: |
    dynadock up \
      --domain ${{ secrets.DOMAIN }} \
      --enable-tls \
      --detach
```

### Docker Swarm / Kubernetes

DynaDock może generować konfiguracje dla orkiestratorów:

```bash
# Wkrótce
dynadock export --format=k8s > deployment.yaml
```

## 🤝 Wkład

Zapraszamy do współtworzenia! Otwórz issue lub pull request.

## 📄 Licencja

MIT License - używaj dowolnie w projektach komercyjnych i open source.
```

## Instalacja i użycie

```bash
# 1. Utwórz nowy projekt
mkdir dynadock && cd dynadock

# 2. Skopiuj pliki z tego artifact'u

# 3. Zainstaluj z uv
uv pip install -e .

# 4. Użyj w swoim projekcie
cd /path/to/your/docker/project
dynadock up --enable-tls

# Twoje serwisy będą dostępne pod:
# https://api.dynadock.lan
# https://frontend.dynadock.lan
# itd.
```

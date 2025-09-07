# DynaDock - Szczegółowa Dokumentacja Kodu

## 📋 Spis Treści

1. [Struktura Projektu](#struktura-projektu)
2. [Core Modules](#core-modules)
3. [CLI Interface](#cli-interface)
4. [Network Management](#network-management)
5. [Configuration System](#configuration-system)
6. [Testing Framework](#testing-framework)
7. [Example Projects](#example-projects)

## 📁 Struktura Projektu

```
dynadock/
├── src/dynadock/              # 🧠 Core engine
│   ├── cli.py                 # 🎯 CLI entry point
│   ├── docker_manager.py      # 🐳 Docker orchestration
│   ├── caddy_config.py        # 🔄 Reverse proxy
│   ├── network_manager.py     # 🌐 Network management
│   ├── lan_network_manager.py # 📡 LAN visibility
│   ├── env_generator.py       # ⚙️ Environment config
│   ├── hosts_manager.py       # 🗂️ DNS management
│   ├── utils.py               # 🛠️ Utilities
│   ├── exceptions.py          # ⚠️ Error handling
│   ├── cli_helpers/           # 🤝 CLI support
│   │   ├── verification.py    # ✅ Domain verification
│   │   └── display.py         # 📺 Output formatting
│   ├── resources/             # 📦 Static resources
│   └── testing/               # 🧪 Test framework
│       ├── auto_repair.py     # 🔧 Auto-fix
│       ├── browser_tester.py  # 🌍 Browser automation
│       └── network_analyzer.py # 📊 Network diagnostics
├── examples/                  # 🚀 Example projects
│   ├── fullstack/            # Full-stack web app
│   ├── microservices/        # Enterprise microservices
│   ├── django-postgres/      # Django + PostgreSQL
│   └── react-nginx/          # React + Nginx
├── docs/                     # 📚 Documentation
├── templates/                # 📄 Configuration templates
├── certs/                    # 🔐 TLS certificates
└── tests/                    # 🧪 Unit tests
```

## 🧠 Core Modules

### 1. CLI Interface - [`cli.py`](../src/dynadock/cli.py)

Główny punkt wejścia systemu implementujący Click-based CLI.

#### Kluczowe Funkcje:

```python
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--compose-file", "-f", help="Path to docker-compose file")
@click.option("--domain", default="dynadock.lan", help="Base domain")
def cli(ctx, compose_file, domain):
    """DynaDock - Advanced Docker Orchestration with Local Domains"""
```

**Główne Komendy:**

| Komenda | Funkcja | Parametry |
|---------|---------|-----------|
| `up` | Uruchom wszystkie usługi | `--tls`, `--lan-visible`, `--domain` |
| `down` | Zatrzymaj wszystkie usługi | `--clean`, `--preserve-data` |
| `status` | Sprawdź status usług | `--format json\|table` |
| `logs` | Pokaż logi usług | `--service`, `--lines` |
| `health-check` | Sprawdź zdrowie systemu | `--verbose` |

#### Przykład Implementacji:

```python
@cli.command()
@click.option("--tls", is_flag=True, help="Enable HTTPS with trusted certificates")
@click.option("--lan-visible", is_flag=True, help="Make services accessible from LAN")
def up(tls, lan_visible):
    """Start all services with automatic domain configuration"""
    
    # 1. Initialize managers
    docker_manager = DockerManager(compose_file)
    network_manager = NetworkManager(project_dir)
    caddy_config = CaddyConfig(domain, enable_tls=tls)
    
    # 2. Setup network
    if lan_visible:
        lan_manager = LANNetworkManager()
        ip_mappings = lan_manager.setup_lan_visibility()
    
    # 3. Generate configurations
    services = docker_manager.get_services()
    ports = network_manager.allocate_ports(services)
    
    # 4. Start Caddy proxy
    caddy_config.generate(services, ports, cors_origins, ip_mappings)
    caddy_config.start_caddy()
    
    # 5. Start Docker services
    docker_manager.start_services()
    
    # 6. Verify connectivity
    verify_domain_access(services, domain, enable_tls=tls)
```

### 2. Docker Manager - [`docker_manager.py`](../src/dynadock/docker_manager.py)

Zaawansowane zarządzanie kontenerami Docker z integracją docker-compose.

#### Klasa DockerManager:

```python
class DockerManager:
    """Manages Docker containers and compose services"""
    
    def __init__(self, compose_file: str = None, project_dir: Path = None):
        self.compose_file = compose_file or "docker-compose.yaml"
        self.project_dir = project_dir or Path.cwd()
        self.client = docker.from_env()
        
    def get_services(self) -> Dict[str, Any]:
        """Parse docker-compose.yaml and extract service definitions"""
        
    def start_services(self, services: List[str] = None) -> None:
        """Start specified services or all if none provided"""
        
    def stop_services(self, services: List[str] = None) -> None:
        """Stop specified services or all if none provided"""
        
    def check_health(self) -> Dict[str, str]:
        """Check health status of all running containers"""
```

#### Health Check Implementation:

```python
def check_health(self) -> Dict[str, str]:
    """Comprehensive health check for all services"""
    health_status = {}
    
    for container in self.client.containers.list():
        # Check container status
        status = container.status
        
        # Check health endpoint if available
        if hasattr(container, 'health'):
            health = container.attrs['State']['Health']['Status']
            status = f"{status} ({health})"
            
        health_status[container.name] = status
    
    return health_status
```

### 3. Caddy Configuration - [`caddy_config.py`](../src/dynadock/caddy_config.py)

Automatyczna generacja konfiguracji Caddy reverse proxy z obsługą TLS.

#### Template System:

```python
CADDYFILE_TEMPLATE = """
# Dynamic Caddyfile generated by DynaDock
{
    email admin@{{ domain }}
    {% if not enable_tls %}
    auto_https off
    {% endif %}
}

# Health endpoint on port 80
:80 {
    respond /health "OK" 200
}

{% for service, data in services.items() %}
# Service: {{ service }}
{{ service }}.{{ domain }} {
    {% if enable_tls %}
    tls /etc/caddy/certs/_wildcard.{{ domain }}+2.pem /etc/caddy/certs/_wildcard.{{ domain }}+2-key.pem
    {% endif %}
    
    reverse_proxy {{ data.ip }}:{{ data.port }}
    
    header {
        Access-Control-Allow-Origin "*"
        Access-Control-Allow-Methods "GET,POST,PUT,DELETE,OPTIONS,PATCH"
        Access-Control-Allow-Headers "*"
    }
}
{% endfor %}
"""
```

#### Certificate Management:

```python
def setup_certificates(self, domain: str) -> bool:
    """Setup mkcert certificates for domain"""
    cert_dir = Path("certs")
    cert_file = cert_dir / f"_wildcard.{domain}+2.pem"
    key_file = cert_dir / f"_wildcard.{domain}+2-key.pem"
    
    if cert_file.exists() and key_file.exists():
        return True
    
    # Generate new certificates
    cmd = ["mkcert", f"*.{domain}", "localhost", "127.0.0.1"]
    result = subprocess.run(cmd, cwd=cert_dir, capture_output=True)
    
    return result.returncode == 0
```

### 4. Network Management - [`network_manager.py`](../src/dynadock/network_manager.py)

Inteligentne zarządzanie portami, IP i siecią Docker.

#### Port Allocation:

```python
class NetworkManager:
    def allocate_ports(self, services: List[str]) -> Dict[str, int]:
        """Automatically allocate free ports for services"""
        allocated_ports = {}
        start_port = 8000
        
        for service in services:
            port = self._find_free_port(start_port)
            allocated_ports[service] = port
            start_port = port + 1
            
        return allocated_ports
    
    def _find_free_port(self, start_port: int) -> int:
        """Find next available port starting from given port"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            for port in range(start_port, 65535):
                try:
                    s.bind(('', port))
                    return port
                except OSError:
                    continue
        raise RuntimeError("No free ports available")
```

#### Docker Network Creation:

```python
def create_network(self, name: str = "dynadock-network") -> str:
    """Create isolated Docker network for services"""
    try:
        network = self.client.networks.create(
            name,
            driver="bridge",
            options={
                "com.docker.network.bridge.name": f"br-{name}",
                "com.docker.network.driver.mtu": "1500"
            }
        )
        return network.id
    except docker.errors.APIError as e:
        if "already exists" in str(e):
            return self.client.networks.get(name).id
        raise
```

### 5. LAN Network Manager - [`lan_network_manager.py`](../src/dynadock/lan_network_manager.py)

Zaawansowany system udostępniania usług w całej sieci LAN.

#### Virtual Interface Setup:

```python
class LANNetworkManager:
    def setup_lan_visibility(self) -> Dict[str, str]:
        """Configure services for LAN-wide access"""
        
        # 1. Detect network interface
        interface = self._detect_network_interface()
        
        # 2. Find available IP range
        network = self._get_network_range(interface)
        
        # 3. Create virtual interfaces
        ip_mappings = {}
        base_ip = ipaddress.IPv4Network(network).network_address + 10
        
        for i, service in enumerate(services):
            vip = str(base_ip + i)
            
            # Create virtual interface
            self._create_virtual_interface(f"dynadock{i}", vip, interface)
            
            # Send gratuitous ARP
            self._send_gratuitous_arp(vip, interface)
            
            ip_mappings[service] = vip
            
        return ip_mappings
```

#### Cross-Platform Network Detection:

```python
def _detect_network_interface(self) -> str:
    """Auto-detect primary network interface"""
    
    # Method 1: Check default route
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            match = re.search(r'dev (\w+)', result.stdout)
            if match:
                return match.group(1)
    except FileNotFoundError:
        pass
    
    # Method 2: Parse /proc/net/route
    try:
        with open('/proc/net/route', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) > 1 and parts[1] == '00000000':
                    return parts[0]
    except FileNotFoundError:
        pass
    
    # Method 3: Fallback to common interfaces
    for iface in ['eth0', 'enp0s3', 'wlan0', 'ens33']:
        if self._interface_exists(iface):
            return iface
    
    raise RuntimeError("Could not detect network interface")
```

### 6. Environment Generator - [`env_generator.py`](../src/dynadock/env_generator.py)

Dynamiczne generowanie zmiennych środowiskowych dla kontenerów.

```python
class EnvGenerator:
    def generate_env_file(self, services: Dict[str, Any], 
                         ports: Dict[str, int]) -> Path:
        """Generate .env file for docker-compose"""
        
        env_vars = {
            'DYNADOCK_DOMAIN': self.domain,
            'DYNADOCK_TLS_ENABLED': str(self.enable_tls).lower(),
            'COMPOSE_PROJECT_NAME': self.project_name,
        }
        
        # Add service-specific variables
        for service, port in ports.items():
            env_vars[f'{service.upper()}_PORT'] = str(port)
            env_vars[f'{service.upper()}_URL'] = f"https://{service}.{self.domain}"
        
        # Write to .env.dynadock file
        env_file = self.project_dir / '.env.dynadock'
        with env_file.open('w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        return env_file
```

### 7. Testing Framework - [`testing/`](../src/dynadock/testing/)

Kompleksowy framework do testowania i diagnostyki systemu.

#### Network Analyzer - [`network_analyzer.py`](../src/dynadock/testing/network_analyzer.py)

```python
class NetworkAnalyzer:
    def analyze_connectivity(self, url: str) -> Dict[str, Any]:
        """Comprehensive network analysis for URL"""
        
        results = {
            'dns': self._test_dns_resolution(url),
            'tcp': self._test_tcp_connection(url),
            'http': self._test_http_response(url),
            'ssl': self._test_ssl_certificate(url),
            'ports': self._scan_ports(url)
        }
        
        return results
    
    def _test_dns_resolution(self, url: str) -> Dict[str, Any]:
        """Test DNS resolution with timing"""
        start_time = time.time()
        try:
            parsed = urllib.parse.urlparse(url)
            ip = socket.gethostbyname(parsed.hostname)
            elapsed = time.time() - start_time
            
            return {
                'success': True,
                'ip': ip,
                'time': elapsed,
                'hostname': parsed.hostname
            }
        except socket.gaierror as e:
            return {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time
            }
```

#### Browser Tester - [`browser_tester.py`](../src/dynadock/testing/browser_tester.py)

```python
class BrowserTester:
    def test_service_ui(self, url: str, screenshot_path: str = None) -> Dict[str, Any]:
        """Test service UI with browser automation"""
        
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-web-security')
        options.add_argument('--ignore-certificate-errors')
        
        with webdriver.Chrome(options=options) as driver:
            try:
                # Navigate to service
                driver.get(url)
                
                # Wait for page load
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                
                # Take screenshot
                if screenshot_path:
                    driver.save_screenshot(screenshot_path)
                
                # Check for common elements
                results = {
                    'title': driver.title,
                    'url': driver.current_url,
                    'status': 'success',
                    'elements': self._analyze_page_elements(driver)
                }
                
                return results
                
            except Exception as e:
                return {
                    'status': 'error',
                    'error': str(e),
                    'url': url
                }
```

## 🚀 Example Projects

### 1. Full-Stack Application - [`examples/fullstack/`](../examples/fullstack/)

Kompletna aplikacja web z React frontend i Node.js backend.

#### Docker Compose Configuration:

```yaml
version: '3.8'

services:
  frontend:
    build: 
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "8000:80"
    depends_on:
      - backend
    environment:
      - REACT_APP_API_URL=https://backend.dynadock.lan
    networks:
      - app-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8001:5000"
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/app
      - REDIS_URL=redis://redis:6379
    networks:
      - app-network

  postgres:
    image: postgres:14-alpine
    environment:
      - POSTGRES_DB=app
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    networks:
      - app-network

  mailhog:
    image: mailhog/mailhog
    ports:
      - "8025:8025"
      - "1025:1025"
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  postgres_data:
```

#### Frontend Dockerfile:

```dockerfile
# Multi-stage build for React
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 2. Microservices Architecture - [`examples/microservices/`](../examples/microservices/)

Enterprise-grade mikrousługi z API Gateway i monitoringiem.

#### Service Directory Structure:

```
microservices/
├── docker-compose.yaml
├── .dynadock.yaml
├── services/
│   ├── auth/              # Authentication service
│   ├── user/              # User management
│   ├── product/           # Product catalog
│   ├── order/             # Order processing
│   └── notification/      # Email/SMS notifications
├── infrastructure/
│   ├── kong/              # API Gateway config
│   ├── prometheus/        # Metrics collection
│   └── grafana/           # Monitoring dashboards
└── README.md
```

#### API Gateway Configuration:

```yaml
# Kong API Gateway
kong:
  image: kong:latest
  environment:
    - KONG_DATABASE=off
    - KONG_DECLARATIVE_CONFIG=/kong/kong.yml
    - KONG_PROXY_ACCESS_LOG=/dev/stdout
    - KONG_ADMIN_ACCESS_LOG=/dev/stdout
    - KONG_PROXY_ERROR_LOG=/dev/stderr
    - KONG_ADMIN_ERROR_LOG=/dev/stderr
  ports:
    - "8000:8000"  # Proxy port
    - "8443:8443"  # Secure proxy port
    - "8001:8001"  # Admin API
  volumes:
    - ./infrastructure/kong/kong.yml:/kong/kong.yml
```

## 🔧 Configuration Files

### Main Configuration - `.dynadock.yaml`

```yaml
version: "1.0"

# Domain configuration
domain: "dynadock.lan"
tls_enabled: true

# Service definitions
services:
  frontend:
    port: 8000
    health_check: "/health"
    cors_origins:
      - "https://backend.dynadock.lan"
      - "http://localhost:3000"
  
  backend:
    port: 8001
    health_check: "/api/health"
    environment:
      - "DATABASE_URL=${DATABASE_URL}"
      - "REDIS_URL=${REDIS_URL}"

# Network configuration
network:
  lan_visible: false
  custom_ports: true
  ip_range: "172.20.0.0/16"

# Monitoring
monitoring:
  enabled: true
  metrics_port: 9090
  logs_retention: "7d"
```

### Environment Template - `.env.dynadock`

```bash
# DynaDock Configuration
DYNADOCK_DOMAIN=dynadock.lan
DYNADOCK_TLS_ENABLED=true
DYNADOCK_LAN_VISIBLE=false

# Service URLs
FRONTEND_URL=https://frontend.dynadock.lan
BACKEND_URL=https://backend.dynadock.lan
MAILHOG_URL=https://mailhog.dynadock.lan

# Database Configuration
POSTGRES_DB=dynadock_app
POSTGRES_USER=dynadock_user
POSTGRES_PASSWORD=secure_password_here

# Redis Configuration
REDIS_URL=redis://redis:6379

# Development Settings
NODE_ENV=development
DEBUG=true
LOG_LEVEL=info
```

## 📊 Monitoring i Diagnostyka

### Health Check Endpoints

Każda usługa powinna implementować standardowe endpointy:

```javascript
// Node.js Express example
app.get('/health', (req, res) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    service: 'backend',
    version: process.env.npm_package_version,
    uptime: process.uptime(),
    database: await checkDatabaseConnection(),
    redis: await checkRedisConnection()
  };
  
  res.status(200).json(health);
});

app.get('/ready', (req, res) => {
  // Readiness probe - check if service is ready to accept traffic
  const ready = await checkServiceReadiness();
  res.status(ready ? 200 : 503).json({ ready });
});
```

### Metrics Collection

```python
# Python Flask example with Prometheus metrics
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('request_duration_seconds', 'Request latency')

@app.route('/metrics')
def metrics():
    return generate_latest()

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request  
def after_request(response):
    REQUEST_COUNT.labels(request.method, request.endpoint).inc()
    REQUEST_LATENCY.observe(time.time() - request.start_time)
    return response
```

---

*Ta dokumentacja zawiera kompletną referencję kodu dla projektu DynaDock. Dla dodatkowych szczegółów, sprawdź poszczególne pliki źródłowe.*

# DynaDock - Architektura i Szczegółowy Opis Rozwiązania

## 📋 Spis Treści

1. [Przegląd Architektury](#przegląd-architektury)
2. [Komponenty Systemu](#komponenty-systemu)
3. [Przepływ Danych](#przepływ-danych)
4. [Struktura Kodu](#struktura-kodu)
5. [Konfiguracja i Deployment](#konfiguracja-i-deployment)
6. [Sieć i Certyfikaty](#sieć-i-certyfikaty)
7. [Przykłady Implementacji](#przykłady-implementacji)

## 🏗️ Przegląd Architektury

DynaDock to zaawansowany system orkiestracji kontenerów Docker z automatycznym zarządzaniem domenami lokalnymi, certyfikatami HTTPS i siecią. System zapewnia seamless development experience dla aplikacji wielousługowych.

```
┌─────────────────────────────────────────────────────────────────┐
│                        DYNADOCK ECOSYSTEM                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   CLI Tool  │  │ Web Browser │  │   Development Tools     │ │
│  │             │  │             │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│         │                │                        │             │
│         ▼                ▼                        ▼             │
├─────────────────────────────────────────────────────────────────┤
│                      CADDY PROXY LAYER                         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           HTTPS Reverse Proxy (Port 443)                   │ │
│  │     *.dynadock.lan → Docker Services                       │ │
│  │                                                             │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │ │
│  │  │   Frontend  │ │   Backend   │ │   Infrastructure    │  │ │
│  │  │ :8000 → 80  │ │ :8001 → 80  │ │    Services        │  │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                     DOCKER CONTAINER LAYER                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                Docker Compose Networks                      │ │
│  │                                                             │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │ │
│  │  │  Web Apps   │ │ API Services│ │     Databases       │  │ │
│  │  │             │ │             │ │                     │  │ │
│  │  │ • React     │ │ • Node.js   │ │ • PostgreSQL        │  │ │
│  │  │ • Angular   │ │ • Python    │ │ • MongoDB           │  │ │
│  │  │ • Vue       │ │ • FastAPI   │ │ • Redis             │  │ │
│  │  │ • Django    │ │ • Express   │ │ • Elasticsearch     │  │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                     NETWORK & SECURITY LAYER                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                                                             │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │ │
│  │  │ DNS Manager │ │ TLS Certs   │ │  Network Manager    │  │ │
│  │  │             │ │             │ │                     │  │ │
│  │  │ • /etc/hosts│ │ • mkcert    │ │ • Port Allocation   │  │ │
│  │  │ • dnsmasq   │ │ • Wildcards │ │ • IP Management     │  │ │
│  │  │ • systemd   │ │ • Auto-trust│ │ • LAN Visibility    │  │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Komponenty Systemu

### 1. Core CLI Engine
**Lokalizacja**: [`src/dynadock/cli.py`](../src/dynadock/cli.py)

Główny punkt wejścia systemu zapewniający:
- **Lifecycle Management**: `up`, `down`, `status`, `logs`
- **Network Modes**: `--lan-visible`, `--tls`, `--domain`
- **Development Tools**: `health-check`, `diagnostics`
- **Configuration**: `.dynadock.yaml` parsing

```python
# Główne komendy CLI
@click.group()
def cli():
    """DynaDock - Advanced Docker Orchestration with Local Domains"""

@cli.command()
@click.option("--tls", is_flag=True, help="Enable HTTPS with trusted certificates")
@click.option("--lan-visible", is_flag=True, help="Make services visible across LAN")
def up(tls, lan_visible):
    """Start all services with automatic domain configuration"""
```

### 2. Docker Management Layer
**Lokalizacja**: [`src/dynadock/docker_manager.py`](../src/dynadock/docker_manager.py)

Zaawansowane zarządzanie kontenerami Docker:
- **Compose Integration**: Automatyczne wykrywanie i uruchamianie `docker-compose.yaml`
- **Health Monitoring**: Sprawdzanie statusu kontenerów i readiness
- **Log Aggregation**: Centralizowane zbieranie logów z wszystkich usług
- **Resource Management**: Monitoring wykorzystania zasobów

```python
class DockerManager:
    def start_services(self, services: List[str] = None):
        """Start specified services or all if none provided"""
        
    def check_health(self) -> Dict[str, str]:
        """Check health status of all running containers"""
        
    def get_service_logs(self, service: str, lines: int = 100):
        """Get logs from specific service"""
```

### 3. Caddy Reverse Proxy Configuration
**Lokalizacja**: [`src/dynadock/caddy_config.py`](../src/dynadock/caddy_config.py)

Automatyczna konfiguracja reverse proxy:
- **Dynamic Caddyfile Generation**: Template-based configuration
- **TLS Certificate Management**: Integration z mkcert dla trusted certificates
- **Load Balancing**: Automatic distribution dla multiple instances
- **CORS Headers**: Pre-configured dla development

```python
class CaddyConfig:
    def generate(self, services: Dict[str, Any]) -> Path:
        """Generate Caddyfile with service mappings"""
        
    def reload_caddy(self):
        """Hot-reload configuration without downtime"""
```

### 4. Network Infrastructure
**Lokalizacja**: [`src/dynadock/network_manager.py`](../src/dynadock/network_manager.py)

Kompleksowe zarządzanie siecią:
- **Port Allocation**: Automatyczne przydzielanie wolnych portów
- **IP Management**: Dynamic IP assignment dla services
- **Network Isolation**: Docker network creation i management
- **Service Discovery**: Automatic service registration

```python
class NetworkManager:
    def allocate_ports(self, services: List[str]) -> Dict[str, int]:
        """Allocate free ports for services"""
        
    def create_network(self, name: str) -> str:
        """Create isolated Docker network"""
```

### 5. LAN Visibility System
**Lokalizacja**: [`src/dynadock/lan_network_manager.py`](../src/dynadock/lan_network_manager.py)

Zaawansowany system dostępu z całej sieci LAN:
- **Virtual Interface Creation**: Setup veth pairs dla network bridging
- **ARP Announcements**: Gratuitous ARP dla immediate visibility
- **Cross-device Access**: Telefony, tablety, inne komputery
- **Security Isolation**: Network-level security controls

```python
class LANNetworkManager:
    def setup_lan_visibility(self) -> Dict[str, str]:
        """Configure services for LAN-wide access"""
        
    def cleanup_lan_interfaces(self):
        """Clean up virtual network interfaces"""
```

## 📊 Przepływ Danych

### Startup Sequence Flow

```
1. CLI Initialization
   ├── Parse .dynadock.yaml
   ├── Validate Docker environment
   └── Initialize managers

2. Network Setup
   ├── Port allocation
   ├── IP management
   └── LAN visibility (if --lan-visible)

3. Service Discovery
   ├── Parse docker-compose.yaml
   ├── Identify service dependencies
   └── Build startup order

4. Certificate Management
   ├── Check existing certificates
   ├── Generate if missing (mkcert)
   └── Configure Caddy TLS

5. Caddy Configuration
   ├── Generate Caddyfile
   ├── Start Caddy container
   └── Configure reverse proxy

6. Service Startup
   ├── Start Docker Compose services
   ├── Wait for health checks
   └── Verify connectivity

7. Domain Verification
   ├── Test DNS resolution
   ├── Verify HTTPS connectivity
   └── Display access URLs
```

### Request Flow

```
User Request → Caddy Proxy → Docker Service → Response
     ↓              ↓             ↓            ↑
DNS Resolution → TLS Termination → Load Balance → Headers
     ↓              ↓             ↓            ↑
/etc/hosts    → Certificate  → Port Forward → CORS
```

## 📁 Struktura Kodu

### Core Modules

```
src/dynadock/
├── cli.py                    # 🎯 Main CLI interface
├── docker_manager.py         # 🐳 Docker orchestration
├── caddy_config.py          # 🔄 Reverse proxy config
├── network_manager.py       # 🌐 Network management
├── lan_network_manager.py   # 📡 LAN visibility
├── env_generator.py         # ⚙️ Environment config
├── utils.py                 # 🛠️ Helper functions
├── exceptions.py            # ⚠️ Error handling
├── hosts_manager.py         # 🗂️ DNS management
└── testing/                 # 🧪 Test framework
    ├── auto_repair.py       # 🔧 Auto-fix issues
    ├── browser_tester.py    # 🌍 Browser automation
    └── network_analyzer.py  # 📊 Network diagnostics
```

### Configuration Files

```
├── .dynadock.yaml          # Main configuration
├── .env.dynadock          # Environment variables
├── docker-compose.yaml    # Service definitions
└── .dynadock/            # Runtime directory
    ├── caddy/           # Caddy configuration
    │   ├── Caddyfile   # Generated proxy config
    │   ├── data/       # Caddy runtime data
    │   └── logs/       # Access logs
    └── ip_map.env      # Service IP mappings
```

## 🔐 Sieć i Certyfikaty

### TLS Certificate Management

DynaDock używa **mkcert** dla generowania trusted local certificates:

```bash
# Automatic certificate generation
mkcert "*.dynadock.lan" localhost 127.0.0.1

# Certificate files
certs/
├── _wildcard.dynadock.lan+2.pem     # Public certificate
├── _wildcard.dynadock.lan+2-key.pem # Private key
└── mkcert                           # CA certificate
```

### DNS Configuration

Automatyczna konfiguracja DNS resolution:

```bash
# /etc/hosts entries (automatic)
127.0.0.1 frontend.dynadock.lan
127.0.0.1 backend.dynadock.lan
127.0.0.1 mailhog.dynadock.lan

# Or systemd-resolved integration
# Or dnsmasq configuration for advanced setups
```

### Network Security

```
┌─────────────────────────────────────────┐
│           Security Layers               │
├─────────────────────────────────────────┤
│ 1. TLS Encryption (HTTPS)              │
│    └── mkcert trusted certificates     │
├─────────────────────────────────────────┤
│ 2. Network Isolation                   │
│    └── Docker networks + firewalls     │
├─────────────────────────────────────────┤
│ 3. Access Control                      │
│    └── CORS policies + auth headers    │
├─────────────────────────────────────────┤
│ 4. Local Network Only                  │
│    └── No external routing (default)   │
└─────────────────────────────────────────┘
```

## 🚀 Konfiguracja i Deployment

### Standard Configuration

**`.dynadock.yaml`** - Main configuration file:

```yaml
version: "1.0"
domain: "dynadock.lan"
services:
  frontend:
    port: 8000
    health_check: "/health"
  backend:
    port: 8001
    health_check: "/api/health"
  mailhog:
    port: 8025
    health_check: "/"
```

### Environment Variables

**`.env.dynadock`** - Environment configuration:

```bash
DYNADOCK_DOMAIN=dynadock.lan
DYNADOCK_TLS_ENABLED=true
DYNADOCK_LAN_VISIBLE=false
DYNADOCK_LOG_LEVEL=INFO
```

### Deployment Modes

#### 1. Standard Mode (Local Development)
```bash
dynadock up --tls
# Services accessible at https://*.dynadock.lan
```

#### 2. LAN-Visible Mode (Team Development)
```bash
sudo dynadock up --lan-visible
# Services accessible from any device on network
```

#### 3. Production-Ready Mode
```bash
dynadock up --domain production.local --tls
# Production-like setup with proper certificates
```

## 📋 Przykłady Implementacji

### 1. Full-Stack Web Application
**Lokalizacja**: [`examples/fullstack/`](../examples/fullstack/)

Complete React + Node.js + PostgreSQL stack:
- **Frontend**: React SPA z hot-reload
- **Backend**: Node.js API z Express
- **Database**: PostgreSQL z migrations
- **Cache**: Redis dla sessions
- **Email**: MailHog dla development

### 2. Microservices Architecture
**Lokalizacja**: [`examples/microservices/`](../examples/microservices/)

Enterprise-grade microservices setup:
- **5 Core Services**: Auth, User, Product, Order, Notification
- **API Gateway**: Kong z routing i load balancing
- **Multiple Databases**: PostgreSQL, MongoDB, Elasticsearch
- **Message Queue**: RabbitMQ dla async communication
- **Monitoring**: Prometheus + Grafana dashboards

### 3. Django + PostgreSQL
**Lokalizacja**: [`examples/django-postgres/`](../examples/django-postgres/)

Production-ready Django application:
- **Django Framework**: z Celery workers
- **PostgreSQL**: z connection pooling
- **Redis**: dla caching i task queue
- **Static Files**: nginx serving
- **Admin Interface**: Django admin panel

### 4. React + Nginx
**Lokalizacja**: [`examples/react-nginx/`](../examples/react-nginx/)

Optimized frontend deployment:
- **React Build**: Production-optimized bundle
- **Nginx**: Static file serving + API proxy
- **Multi-stage Build**: Optimized Docker images
- **Health Checks**: Application monitoring

## 🔗 Linki do Kluczowych Plików

### Core Implementation
- [**CLI Entry Point**](../src/dynadock/cli.py) - Main command interface
- [**Docker Manager**](../src/dynadock/docker_manager.py) - Container orchestration
- [**Caddy Config**](../src/dynadock/caddy_config.py) - Reverse proxy setup
- [**Network Manager**](../src/dynadock/network_manager.py) - Network configuration
- [**LAN Network Manager**](../src/dynadock/lan_network_manager.py) - Cross-device access

### Configuration Templates
- [**Caddyfile Template**](../templates/Caddyfile.template) - Proxy configuration
- [**Docker Compose Example**](../examples/fullstack/docker-compose.yaml) - Service definitions
- [**Environment Config**](../.env.dynadock) - Runtime variables

### Testing & Diagnostics
- [**Network Analyzer**](../src/dynadock/testing/network_analyzer.py) - Connection testing
- [**Browser Tester**](../src/dynadock/testing/browser_tester.py) - UI automation
- [**Auto Repair**](../src/dynadock/testing/auto_repair.py) - Issue resolution

### Documentation
- [**Usage Guide**](../docs/USAGE.md) - Detailed usage instructions
- [**Troubleshooting**](../docs/TROUBLESHOOTING.md) - Common issues & fixes
- [**Testing Framework**](../docs/TESTING_FRAMEWORK.md) - Test methodology

## 🏗️ Architecture Patterns

DynaDock implementuje kilka kluczowych wzorców architektonicznych:

### 1. Plugin Architecture
Modular design pozwalający na easy extension:
```python
# Plugin interface
class NetworkPlugin:
    def setup(self): pass
    def teardown(self): pass

# Implementation examples
class DockerNetworkPlugin(NetworkPlugin): ...
class LANVisibilityPlugin(NetworkPlugin): ...
```

### 2. Template-Based Configuration
Flexible configuration system:
```python
# Dynamic Caddyfile generation
template = Template(CADDYFILE_TEMPLATE)
config = template.render(
    domain=self.domain,
    services=service_mappings,
    tls_enabled=self.enable_tls
)
```

### 3. Health Check Pipeline
Comprehensive service monitoring:
```python
# Multi-layer health verification
def verify_service_health(service):
    checks = [
        check_container_running(),
        check_port_accessible(),
        check_http_response(),
        check_https_certificate()
    ]
    return all(checks)
```

---

*Ta dokumentacja jest częścią projektu DynaDock - Advanced Docker Orchestration Platform*

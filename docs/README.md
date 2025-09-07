# 📚 DynaDock - Kompletna Dokumentacja

## 🎯 Przegląd Dokumentacji

DynaDock to zaawansowana platforma orkiestracji kontenerów Docker z automatycznym zarządzaniem domenami lokalnymi, certyfikatami HTTPS i siecią LAN. Ta dokumentacja zawiera wszystkie szczegóły techniczne, przykłady implementacji i przewodniki użytkownika.

---

## 📖 Główne Dokumenty

### 🏗️ **[Architektura i Opis Rozwiązania](./ARCHITECTURE.md)**
**Szczegółowy opis architektury systemu z diagramami**
- Przegląd kompletnej architektury DynaDock
- Diagramy przepływu danych i komponentów
- Wzorce architektoniczne i design patterns  
- Opis wszystkich warstw systemu
- Konfiguracja sieci i certyfikatów TLS

### 💻 **[Szczegółowa Dokumentacja Kodu](./CODE_REFERENCE.md)**
**Kompletna referencja kodu źródłowego**
- Struktura projektu i organizacja plików
- Dokumentacja wszystkich modułów core
- Przykłady implementacji z kodem źródłowym
- API reference dla kluczowych klas
- Szczegóły konfiguracji i deployment

### 🚀 **[Przewodnik Użytkownika](./USAGE.md)**
**Praktyczny przewodnik używania DynaDock**
- Instrukcje instalacji i konfiguracji
- Przykłady użycia CLI
- Konfiguracja różnych trybów działania
- Zarządzanie usługami i monitorowanie

### 🔧 **[Rozwiązywanie Problemów](./TROUBLESHOOTING.md)**
**Przewodnik rozwiązywania najczęstszych problemów**
- Diagnostyka problemów sieciowych
- Problemy z certyfikatami TLS
- Błędy Docker i docker-compose
- Narzędzia diagnostyczne

### 🧪 **[Framework Testowy](./TESTING_FRAMEWORK.md)**
**Dokumentacja systemu testowania i diagnostyki**
- Automated testing framework
- Network connectivity testing
- Browser automation testing
- Performance benchmarking

---

## 🔗 Szybka Nawigacja po Kodzie

### Core Engine - [`src/dynadock/`](../src/dynadock/)

| Moduł | Plik | Opis |
|-------|------|------|
| **CLI Interface** | [`cli.py`](../src/dynadock/cli.py) | Główny interfejs wiersza poleceń |
| **Docker Manager** | [`docker_manager.py`](../src/dynadock/docker_manager.py) | Zarządzanie kontenerami Docker |
| **Caddy Config** | [`caddy_config.py`](../src/dynadock/caddy_config.py) | Konfiguracja reverse proxy |
| **Network Manager** | [`network_manager.py`](../src/dynadock/network_manager.py) | Zarządzanie siecią i portami |
| **LAN Network** | [`lan_network_manager.py`](../src/dynadock/lan_network_manager.py) | Dostęp z całej sieci LAN |
| **Environment** | [`env_generator.py`](../src/dynadock/env_generator.py) | Generowanie zmiennych środowiskowych |
| **DNS Manager** | [`hosts_manager.py`](../src/dynadock/hosts_manager.py) | Zarządzanie /etc/hosts i DNS |
| **Utilities** | [`utils.py`](../src/dynadock/utils.py) | Funkcje pomocnicze |
| **Exceptions** | [`exceptions.py`](../src/dynadock/exceptions.py) | Obsługa błędów |

### CLI Helpers - [`src/dynadock/cli_helpers/`](../src/dynadock/cli_helpers/)

| Moduł | Plik | Opis |
|-------|------|------|
| **Verification** | [`verification.py`](../src/dynadock/cli_helpers/verification.py) | Weryfikacja dostępności domen |
| **Display** | [`display.py`](../src/dynadock/cli_helpers/display.py) | Formatowanie wyników CLI |

### Testing Framework - [`src/dynadock/testing/`](../src/dynadock/testing/)

| Moduł | Plik | Opis |
|-------|------|------|
| **Auto Repair** | [`auto_repair.py`](../src/dynadock/testing/auto_repair.py) | Automatyczne naprawy systemowe |
| **Browser Tester** | [`browser_tester.py`](../src/dynadock/testing/browser_tester.py) | Automatyzacja przeglądarki |
| **Network Analyzer** | [`network_analyzer.py`](../src/dynadock/testing/network_analyzer.py) | Analiza połączeń sieciowych |

---

## 🚀 Przykłady Projektów - [`examples/`](../examples/)

### 📱 **[Full-Stack Web Application](../examples/fullstack/)**
**Kompletna aplikacja React + Node.js + PostgreSQL**
- React frontend z hot-reload
- Node.js API backend
- PostgreSQL database z migracjami
- Redis cache i session storage
- MailHog dla testowania email

**Pliki kluczowe:**
- [`docker-compose.yaml`](../examples/fullstack/docker-compose.yaml) - Definicja usług
- [`frontend/Dockerfile`](../examples/fullstack/frontend/Dockerfile) - React container
- [`backend/Dockerfile`](../examples/fullstack/backend/Dockerfile) - Node.js API
- [`README.md`](../examples/fullstack/README.md) - Instrukcje uruchomienia

### 🏢 **[Microservices Architecture](../examples/microservices/)**
**Enterprise-grade architektura mikrousług**
- 5 głównych usług: Auth, User, Product, Order, Notification
- Kong API Gateway z routingiem
- Multiple databases: PostgreSQL, MongoDB, Elasticsearch
- RabbitMQ message broker
- Prometheus + Grafana monitoring

**Pliki kluczowe:**
- [`docker-compose.yaml`](../examples/microservices/docker-compose.yaml) - Orkiestracja usług
- [`services/`](../examples/microservices/services/) - Kod mikrousług
- [`infrastructure/`](../examples/microservices/infrastructure/) - Konfiguracja infrastruktury
- [`README.md`](../examples/microservices/README.md) - Dokumentacja architektury

### 🐍 **[Django + PostgreSQL](../examples/django-postgres/)**
**Production-ready Django application**
- Django framework z Celery workers
- PostgreSQL z connection pooling
- Redis dla cache i task queue
- Nginx static file serving
- Django admin panel

**Pliki kluczowe:**
- [`docker-compose.yaml`](../examples/django-postgres/docker-compose.yaml) - Stack definicja
- [`django_app/`](../examples/django-postgres/django_app/) - Django kod
- [`Dockerfile`](../examples/django-postgres/Dockerfile) - Django container
- [`requirements.txt`](../examples/django-postgres/requirements.txt) - Python dependencies

### ⚛️ **[React + Nginx](../examples/react-nginx/)**
**Zoptymalizowany frontend deployment**
- React production build
- Nginx static serving + API proxy
- Multi-stage Docker build
- Health checks i monitoring

**Pliki kluczowe:**
- [`Dockerfile`](../examples/react-nginx/Dockerfile) - Multi-stage build
- [`nginx.conf`](../examples/react-nginx/nginx.conf) - Nginx konfiguracja
- [`src/`](../examples/react-nginx/src/) - React aplikacja

---

## ⚙️ Konfiguracja i Szablony - [`templates/`](../templates/)

### 📄 **Szablony Konfiguracyjne**

| Plik | Opis |
|------|------|
| [`Caddyfile.template`](../templates/Caddyfile.template) | Template reverse proxy Caddy |

### 🔐 **Certyfikaty TLS - [`certs/`](../certs/)**

| Plik | Opis |
|------|------|
| `_wildcard.dynadock.lan+2.pem` | Certyfikat publiczny wildcard |
| `_wildcard.dynadock.lan+2-key.pem` | Klucz prywatny certyfikatu |
| `mkcert` | mkcert CA certificate |

---

## 🧪 Testy i Diagnostyka

### Unit Tests - [`tests/`](../tests/)

| Katalog/Plik | Opis |
|---------------|------|
| [`unit/`](../tests/unit/) | Unit testy dla poszczególnych modułów |
| [`fixtures/`](../tests/fixtures/) | Test fixtures i mock data |
| [`conftest.py`](../tests/conftest.py) | Pytest configuration |

### Diagnostics - [`diagnostics/`](../diagnostics/)

| Plik | Opis |
|------|------|
| [`comprehensive_diagnostic_report.py`](../diagnostics/comprehensive_diagnostic_report.py) | Pełen raport diagnostyczny |
| [`simple_network_test.py`](../diagnostics/simple_network_test.py) | Prosty test sieci |
| [`detailed_test_3_cases.py`](../diagnostics/detailed_test_3_cases.py) | Szczegółowe testy 3 przypadków |

---

## 📋 Pliki Konfiguracyjne Główne

### Project Root Files

| Plik | Opis |
|------|------|
| [`pyproject.toml`](../pyproject.toml) | Python project configuration |
| [`Makefile`](../Makefile) | Build i development commands |
| [`README.md`](../README.md) | Główny README projektu |
| [`CHANGELOG.md`](../CHANGELOG.md) | Historia zmian |
| [`TODO.md`](../TODO.md) | Zadania do wykonania |
| [`.dynadock.yaml`](../.dynadock.yaml) | Główna konfiguracja DynaDock |
| [`.env.dynadock`](../.env.dynadock) | Zmienne środowiskowe |
| [`docker-compose.yaml`](../docker-compose.yaml) | Development stack |

---

## 🎯 Szybki Start

### 1. **Podstawowe Uruchomienie**
```bash
# Przejdź do przykładu
cd examples/fullstack

# Uruchom z HTTPS
dynadock up --tls

# Dostęp do usług
# https://frontend.dynadock.lan
# https://mailhog.dynadock.lan
```

### 2. **Tryb LAN-Visible**  
```bash
# Dostęp z całej sieci lokalnej
sudo dynadock up --lan-visible

# Usługi dostępne dla telefonów, tabletów, etc.
```

### 3. **Diagnostyka**
```bash
# Sprawdź status systemu
dynadock health-check

# Uruchom testy sieci
python3 diagnostics/simple_network_test.py

# Pełna diagnostyka
python3 diagnostics/comprehensive_diagnostic_report.py
```

---

## 🔍 Znajdowanie Informacji

### Według Kategorii:

- **🏗️ Architektura**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- **💻 Kod źródłowy**: [CODE_REFERENCE.md](./CODE_REFERENCE.md)  
- **🚀 Użytkowanie**: [USAGE.md](./USAGE.md)
- **🔧 Problemy**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **🧪 Testowanie**: [TESTING_FRAMEWORK.md](./TESTING_FRAMEWORK.md)

### Według Funkcjonalności:

- **CLI Commands**: [cli.py](../src/dynadock/cli.py) + [USAGE.md](./USAGE.md)
- **Network Setup**: [network_manager.py](../src/dynadock/network_manager.py) + [ARCHITECTURE.md](./ARCHITECTURE.md)
- **HTTPS/TLS**: [caddy_config.py](../src/dynadock/caddy_config.py) + [certs/](../certs/)
- **Docker Integration**: [docker_manager.py](../src/dynadock/docker_manager.py)
- **Examples**: [examples/](../examples/) + każdy ma własny README

### Według Problemu:

- **Nie mogę uruchomić**: [USAGE.md](./USAGE.md) → Installation
- **Błędy sieci**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) → Network Issues  
- **Problemy HTTPS**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) → TLS Certificate Issues
- **Docker errors**: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) → Docker Issues

---

## 🆘 Wsparcie i Pomoc

### Najczęstsze Problemy:
1. **DNS nie rozwiązuje domen** → [Troubleshooting DNS](./TROUBLESHOOTING.md#dns-resolution-issues)
2. **Certyfikaty HTTPS nie działają** → [TLS Certificate Issues](./TROUBLESHOOTING.md#tls-certificate-issues)
3. **Usługi nie uruchamiają się** → [Docker Issues](./TROUBLESHOOTING.md#docker-issues)
4. **LAN visibility nie działa** → [Network Issues](./TROUBLESHOOTING.md#network-issues)

### Narzędzia Diagnostyczne:
- `dynadock health-check --verbose`
- `python3 diagnostics/simple_network_test.py`
- `python3 diagnostics/comprehensive_diagnostic_report.py`

---

*Ostatnia aktualizacja: Wrzesień 2025 - DynaDock v2.0 z domeną dynadock.lan*

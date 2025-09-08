# DynaDock 

> Inteligentny orchestrator Docker Compose z automatyczną alokacją portów, TLS i lokalnymi subdomenami

[![PyPI version](https://img.shields.io/pypi/v/dynadock.svg)](https://pypi.org/project/dynadock/)
[![Python Version](https://img.shields.io/pypi/pyversions/dynadock.svg)](https://pypi.org/project/dynadock/)
[![Tests](https://github.com/dynapsys/dynadock/actions/workflows/test.yml/badge.svg)](https://github.com/dynapsys/dynadock/actions/workflows/test.yml)
[![License](https://img.shields.io/pypi/l/dynadock.svg)](LICENSE)
[![PyPI Downloads](https://img.shields.io/pypi/dm/dynadock.svg)](https://pypi.org/project/dynadock/)

## Dlaczego DynaDock?

DynaDock rozwiązuje najczęstsze problemy przy pracy z Docker Compose:

- **Konflikty portów** - automatycznie znajduje wolne porty
- **Certyfikaty SSL** - automatyczne HTTPS przez Caddy
- **Lokalne domeny** - każdy serwis dostępny pod własną subdomeną
- **Zero konfiguracji** - działa od razu po instalacji
- **Health checks** - automatyczne monitorowanie serwisów

## Spis treści

- [Dlaczego DynaDock?](#dlaczego-dynadock)
- [Instalacja](#instalacja)
- [Szybki start](#szybki-start)
- [Przykłady użycia](#przykłady-użycia)
- [Funkcjonalności](#funkcjonalności)
- [Komendy CLI](#komendy-cli)
- [Konfiguracja](#konfiguracja)
- [Przykładowe projekty](#przykładowe-projekty)
- [Rozwiązywanie problemów](#rozwiazywanie-problemow)
- [Rozwój](#rozwój)
- [Wkład](#wkład)
- [Autor](#autor)
- [Licencja](#licencja)
- [Podziękowania](#podziękowania)

## Instalacja

### Z PyPI (zalecane)

```bash
pip install dynadock
```

### Z uv (najszybsze)

```bash
uv tool install dynadock
```

### Ze źródeł

```bash
git clone https://github.com/dynapsys/dynadock.git
cd dynadock
make install
```

## Szybki start

### 1. Podstawowe użycie

```bash
# W katalogu z docker-compose.yaml
dynadock up

# Twoje serwisy będą dostępne pod:
# http://api.dynadock.lan:8000
# http://web.dynadock.lan:8001
# http://redis.dynadock.lan:8002
```

### 2. Z HTTPS (zalecane)

```bash
dynadock up --enable-tls

# Serwisy dostępne pod:
# https://api.dynadock.lan
# https://web.dynadock.lan
# https://redis.dynadock.lan
```

### 3. Własna domena

```bash
dynadock up --domain myapp.local --enable-tls

# Serwisy dostępne pod:
# https://api.myapp.local
# https://web.myapp.local
```

## Przykłady użycia

### Aplikacja Node.js z MongoDB

```yaml
# docker-compose.yaml
version: '3.8'
services:
  app:
    build: .
    environment:
      - NODE_ENV=development
  
  mongodb:
    image: mongo:6
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=secret
```

```bash
dynadock up --enable-tls

# Dostępne pod:
# https://app.dynadock.lan - aplikacja Node.js
# https://mongodb.dynadock.lan - MongoDB (z auth)
```

### Python FastAPI z PostgreSQL

```yaml
# docker-compose.yaml
version: '3.8'
services:
  api:
    build: .
    command: uvicorn main:app --reload
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres/db
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=db
```

```bash
dynadock up --enable-tls --domain backend.dev

# Dostępne pod:
# https://api.backend.dev - FastAPI
# https://postgres.backend.dev - PostgreSQL
```

### Mikroserwisy z Redis i RabbitMQ

```yaml
# docker-compose.yaml
version: '3.8'
services:
  gateway:
    build: ./gateway
    depends_on:
      - auth-service
      - user-service
  
  auth-service:
    build: ./services/auth
    environment:
      - REDIS_URL=redis://redis:6379
  
  user-service:
    build: ./services/user
    environment:
      - RABBITMQ_URL=amqp://rabbitmq:5672
  
  redis:
    image: redis:7-alpine
  
  rabbitmq:
    image: rabbitmq:3-management
```

```bash
dynadock up --enable-tls --scale user-service=3

# Dostępne pod:
# https://gateway.dynadock.lan - API Gateway
# https://auth-service.dynadock.lan - Auth Service
# https://user-service.dynadock.lan - User Service (load balanced)
# https://redis.dynadock.lan - Redis
# https://rabbitmq.dynadock.lan - RabbitMQ Management
```

## Funkcjonalności

### 🔧 Automatyczna konfiguracja

- **Alokacja portów**: Znajduje wolne porty (8000-9999)
- **Generowanie .env**: Tworzy `.env.dynadock` z wszystkimi zmiennymi
- **Certyfikaty SSL**: Automatyczne HTTPS przez Caddy
- **Health checks**: Monitorowanie stanu serwisów
- **CORS**: Automatyczna konfiguracja dla API

### 🌐 Reverse Proxy (Caddy)

- **Load balancing**: Dla skalowanych serwisów
- **WebSocket support**: Automatyczne przekierowanie WS
- **Kompresja**: Gzip/Brotli dla odpowiedzi
- **Cache**: Inteligentne cache'owanie statycznych zasobów
- **Security headers**: Automatyczne nagłówki bezpieczeństwa

### 🔍 Monitoring

- **Health checks**: Sprawdzanie dostępności serwisów
- **Metryki**: Prometheus-compatible metrics
- **Logi**: Scentralizowane logowanie
- **Alerts**: Powiadomienia o problemach

## Komendy CLI

### Podstawowe komendy

```bash
# Uruchomienie serwisów
dynadock up [OPTIONS]

# Zatrzymanie serwisów
dynadock down

# Status serwisów
dynadock ps

# Logi
dynadock logs [SERVICE]

# Wykonanie komendy w kontenerze
dynadock exec SERVICE COMMAND

# Health check
dynadock health
```

### Opcje `dynadock up`

| Opcja | Opis | Domyślnie |
|-------|------|-----------|
| `--domain` | Domena bazowa | `dynadock.lan` |
| `--enable-tls` | Włącz HTTPS | `false` |
| `--port-range` | Zakres portów | `8000-9999` |
| `--scale SERVICE=N` | Skalowanie serwisu | `1` |
| `--cors-origins` | Dozwolone origins | `*` |
| `--no-caddy` | Wyłącz Caddy proxy | `false` |
| `--env-file` | Dodatkowy plik .env | - |

### Przykłady zaawansowane

```bash
# Produkcja z Let's Encrypt
dynadock up --domain app.com --enable-tls --email admin@app.com

# Development z custom ports
dynadock up --port-range 3000-4000 --enable-tls

# Skalowanie z load balancing
dynadock up --scale api=5 --scale worker=3

# Z custom CORS
dynadock up --cors-origins https://app.com,https://admin.app.com
```

## Konfiguracja

### Plik `.dynadock.yaml`

```yaml
# .dynadock.yaml
domain: myapp.local
enable_tls: true
port_range: 8000-9999
services:
  api:
    scale: 3
    health_check: /health
    cors_origins:
      - https://app.myapp.local
  redis:
    expose_port: false
caddy:
  email: admin@example.com
  staging: false  # dla Let's Encrypt
```

### Zmienne środowiskowe

DynaDock automatycznie generuje `.env.dynadock`:

```bash
# .env.dynadock (generowany automatycznie)
DYNADOCK_DOMAIN=myapp.local
DYNADOCK_PROTOCOL=https
DYNADOCK_API_PORT=8000
DYNADOCK_API_URL=https://api.myapp.local
DYNADOCK_WEB_PORT=8001
DYNADOCK_WEB_URL=https://web.myapp.local
DYNADOCK_REDIS_PORT=8002
DYNADOCK_REDIS_URL=redis://redis.myapp.local:8002
```

## Przykładowe projekty

Repozytorium zawiera kompletne przykłady w katalogu `examples/`:

### 1. Simple Web App

```bash
cd examples/simple-web
dynadock up --enable-tls
# Otwórz: https://web.dynadock.lan
```

### 2. REST API z bazą danych

```bash
cd examples/rest-api
dynadock up --enable-tls
# API: https://api.dynadock.lan
# Docs: https://api.dynadock.lan/docs
```

### 3. Mikroserwisy

```bash
cd examples/microservices
dynadock up --enable-tls --scale worker=3
# Gateway: https://gateway.dynadock.lan
# Services: https://[service].dynadock.lan
```

### 4. Full-stack aplikacja

```bash
cd examples/fullstack
dynadock up --enable-tls
# Frontend: https://app.dynadock.lan
# Backend: https://api.dynadock.lan
# Admin: https://admin.dynadock.lan
```

## Rozwiązywanie problemów

### Port już zajęty

```bash
# Sprawdź zajęte porty
dynadock debug ports

# Użyj innego zakresu
dynadock up --port-range 9000-9999
```

### Problemy z DNS

```bash
# Dodaj do /etc/hosts
echo "127.0.0.1 api.dynadock.lan web.dynadock.lan" | sudo tee -a /etc/hosts

# Lub użyj systemd-resolved (under development, check `dynadock --help` for availability)
dynadock setup-dns
```

### Certyfikaty SSL

```bash
# Zaufaj certyfikatom Caddy (under development, check `dynadock --help` for availability)
dynadock trust-certs

# Lub wyłącz TLS w development
dynadock up --no-tls
```

### Problemy z siecią Docker

```bash
# Reset sieci Docker (under development, check `dynadock --help` for availability)
dynadock network reset

# Lub użyj host network
dynadock up --network host
```

## Rozwój

### Wymagania

- Python 3.8+
- Docker 20.10+
- Make (opcjonalne)
- uv (zalecane)

### Setup środowiska

```bash
# Klonuj repo
git clone https://github.com/dynapsys/dynadock.git
cd dynadock

# Instalacja dev dependencies
make dev

# Lub z uv
uv pip install -e ".[dev]"
```

### Uruchamianie testów

```bash
# Wszystkie testy
make test

# Tylko unit tests
make test-unit

# Tylko integration tests
make test-integration

# Z coverage
make coverage

# W trybie watch
make test-watch
```

### Budowanie dokumentacji

```bash
# Buduj dokumentację
make docs

# Serwuj lokalnie
make docs-serve
# Otwórz: http://localhost:8000
```

### Linting i formatowanie

```bash
# Sprawdź kod
make lint

# Formatuj kod
make format

# Pre-commit checks
make pre-commit
```

## Wkład

Zapraszamy do współtworzenia DynaDock! Zobacz nasz [przewodnik dla kontrybutorów](CONTRIBUTING.md), aby dowiedzieć się więcej.

### Jak pomóc?

1. 🍴 Fork repozytorium
2. 🌿 Stwórz branch (`git checkout -b feature/amazing`)
3. ✨ Commituj zmiany (`git commit -m 'Add amazing feature'`)
4. 📤 Push do brancha (`git push origin feature/amazing`)
5. 🎉 Otwórz Pull Request

### Zgłaszanie błędów

Użyj [GitHub Issues](https://github.com/dynapsys/dynadock/issues) do zgłaszania błędów.

## Autor

**DynaDock** jest rozwijany i utrzymywany przez zespół [Dynapsys](https://github.com/dynapsys).

## Licencja

MIT - zobacz [LICENSE](LICENSE)

## Podziękowania

- [Caddy](https://caddyserver.com/) - za świetny reverse proxy
- [Docker](https://docker.com/) - za konteneryzację
- [Click](https://click.palletsprojects.com/) - za CLI framework
- [Rich](https://github.com/willmcgugan/rich) - za piękne terminale

---

*Stworzone z ❤️ przez [Dynapsys](https://github.com/dynapsys)*

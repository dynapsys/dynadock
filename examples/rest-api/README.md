# REST API Example

Przykład REST API z PostgreSQL i Redis uruchomiony przez DynaDock.

## 🚀 Uruchomienie

```bash
# Przejdź do katalogu przykładu
cd examples/rest-api

# Uruchom z HTTPS
dynadock up --enable-tls

# Lub bez HTTPS
dynadock up
```

## 📋 Dostępne serwisy

- **API**: https://api.local.dev - REST API (Node.js/Express)
- **PostgreSQL**: https://postgres.local.dev - Baza danych
- **Redis**: https://redis.local.dev - Cache
- **Adminer**: https://adminer.local.dev - GUI dla bazy danych

## 🧪 Testowanie API

### Health Check
```bash
curl https://api.local.dev/health
```

### Lista użytkowników
```bash
curl https://api.local.dev/api/users
```

### Dodanie użytkownika
```bash
curl -X POST https://api.local.dev/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "test@example.com"}'
```

### Cache
```bash
# Zapisz wartość
curl -X POST https://api.local.dev/api/cache/mykey \
  -H "Content-Type: application/json" \
  -d '{"value": "Hello World", "ttl": 60}'

# Odczytaj wartość
curl https://api.local.dev/api/cache/mykey
```

## 📁 Struktura

```
rest-api/
├── docker-compose.yaml  # Konfiguracja Docker Compose
├── Dockerfile          # Obraz Docker dla API
├── package.json        # Zależności Node.js
├── server.js          # Kod serwera API
├── init.sql           # Inicjalizacja bazy danych
└── README.md          # Ten plik
```

## ⚙️ Funkcjonalności

- **Express.js** - Framework web
- **PostgreSQL** - Relacyjna baza danych
- **Redis** - Cache i sesje
- **Helmet** - Security headers
- **CORS** - Cross-origin resource sharing
- **Rate limiting** - Ochrona przed nadużyciami
- **Health checks** - Monitorowanie statusu

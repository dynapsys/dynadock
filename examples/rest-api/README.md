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

- **API**: https://api.dynadock.lan - REST API (Node.js/Express)
- **PostgreSQL**: https://postgres.dynadock.lan - Baza danych
- **Redis**: https://redis.dynadock.lan - Cache
- **Adminer**: https://adminer.dynadock.lan - GUI dla bazy danych

## 🧪 Testowanie API

### Health Check
```bash
curl https://api.dynadock.lan/health
```

### Lista użytkowników
```bash
curl https://api.dynadock.lan/api/users
```

### Dodanie użytkownika
```bash
curl -X POST https://api.dynadock.lan/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "test@example.com"}'
```

### Cache
```bash
# Zapisz wartość
curl -X POST https://api.dynadock.lan/api/cache/mykey \
  -H "Content-Type: application/json" \
  -d '{"value": "Hello World", "ttl": 60}'

# Odczytaj wartość
curl https://api.dynadock.lan/api/cache/mykey
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

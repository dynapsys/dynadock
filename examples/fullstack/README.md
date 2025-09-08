# Fullstack Application Example

Pełna aplikacja webowa z frontendem React i backendem Node.js/Express.

## 🚀 Uruchomienie

```bash
# Przejdź do katalogu przykładu
cd examples/fullstack

# Uruchom z HTTPS
dynadock up --enable-tls

# Lub bez HTTPS
dynadock up
```

## 📋 Dostępne serwisy

- **Frontend**: https://frontend.dynadock.lan - Aplikacja React
- **Backend**: https://backend.dynadock.lan - REST API
- **PostgreSQL**: https://postgres.dynadock.lan - Baza danych
- **Redis**: https://redis.dynadock.lan - Cache i sesje
- **MailHog**: https://mailhog.dynadock.lan - Email testing (UI na porcie 8025)

## 🧪 Funkcjonalności

- **Autentykacja**: Rejestracja i logowanie użytkowników
- **Todo List**: CRUD operacje na zadaniach
- **Cache**: Redis do przyspieszenia odpowiedzi
- **Health Checks**: Monitoring statusu wszystkich serwisów
- **Rate Limiting**: Ochrona przed nadużyciami

## 📁 Struktura

```
fullstack/
├── frontend/               # Aplikacja React
│   ├── Dockerfile
│   ├── package.json
│   ├── nginx.conf
│   ├── public/
│   └── src/
│       ├── App.js
│       ├── App.css
│       ├── index.js
│       └── index.css
├── backend/               # API Node.js/Express
│   ├── Dockerfile
│   ├── package.json
│   └── server.js
├── docker-compose.yaml    # Konfiguracja Docker Compose
└── README.md             # Ten plik
```

## 🔒 Bezpieczeństwo

- JWT do autoryzacji
- Bcrypt do hashowania haseł
- Helmet.js dla security headers
- CORS skonfigurowany
- Rate limiting na endpointach API
- Walidacja danych wejściowych

## 💡 Wskazówki

1. **Dostęp do bazy**: Użyj Adminer lub połącz się bezpośrednio:
   ```bash
   docker exec -it <postgres-container> psql -U user -d appdb
   ```

2. **Podgląd emaili**: MailHog przechwytuje wszystkie emaile wysyłane przez aplikację

3. **Logi**: Sprawdź logi serwisów:
   ```bash
   dynadock logs backend
   dynadock logs frontend
   ```

## 🎨 Technologie

- **Frontend**: React, Axios, React Router, React Toastify
- **Backend**: Express, PostgreSQL, Redis, JWT, Bcrypt
- **Infrastruktura**: Docker, Nginx, Caddy (przez DynaDock)

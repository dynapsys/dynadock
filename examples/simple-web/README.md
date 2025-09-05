# Simple Web Example

Prosty przykład aplikacji web z serwerem API uruchomionej przez DynaDock.

## 🚀 Uruchomienie

```bash
# Przejdź do katalogu przykładu
cd examples/simple-web

# Uruchom z HTTPS
dynadock up --enable-tls

# Lub bez HTTPS
dynadock up
```

## 📋 Dostępne serwisy

- **Web**: https://web.local.dev - Statyczna strona HTML
- **API**: https://api.local.dev - Prosty API server

## 🧪 Testowanie

1. Otwórz przeglądarkę i przejdź do https://web.local.dev
2. Kliknij przycisk "Test API Connection" aby przetestować połączenie z API
3. Sprawdź logi: `dynadock logs`

## 📁 Struktura

```
simple-web/
├── docker-compose.yaml  # Konfiguracja Docker Compose
├── html/               # Pliki statyczne
│   └── index.html     # Główna strona
└── README.md          # Ten plik
```

## ⚙️ Konfiguracja

Docker Compose definiuje dwa serwisy:
- `web` - Nginx serwujący pliki statyczne
- `api` - Prosty API server zwracający plain text

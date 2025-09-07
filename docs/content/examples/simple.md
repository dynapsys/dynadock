# Example: Simple Compose Project

This walkthrough shows how **DynaDock** can super-charge an ordinary `docker-compose.yaml`.

---

## 1. The original compose file

```yaml
version: '3.8'

services:
  api:
    image: ghcr.io/example/flask-api:latest
    ports:
      - "5000"  # ← hard-coded port that may clash
  redis:
    image: redis:7-alpine
```

Problems:
1. Port **5000** may already be used.🔀
2. No HTTPS certificates.
3. No *.env* file with service URLs for other tools.

---

## 2. Run with DynaDock

```bash
# 1. Install if you haven't already
uv pip install dynadock

# 2. Bring everything up with dynamic ports & TLS
dynadock up --enable-tls
```

What happens under the hood:
* **PortAllocator** picks free ports (e.g. 8012 for API, 6379 stays default for Redis).
* A **Caddyfile** is rendered and Caddy issues local certificates.
* An *.env* file (`.env.dynadock`) is generated:

```dotenv
API_URL=https://api.dynadock.lan
REDIS_URL=redis://localhost:6379
```

You can now:

```bash
curl $API_URL/health
```

---

## 3. Inspect status

```bash
dynadock status
```

Sample output:

```text
SERVICE   URL                     PORT  STATE  TLS
api       https://api.dynadock.lan   8012  UP     ✅
redis     redis://localhost       6379  UP     ❌
```

---

## 4. Custom configuration

Create `.dynadock.yaml` to tweak behaviours:

```yaml
port_range:
  start: 8500
  end: 8999

domain: myproject.local
```

Re-run `dynadock up --reload` to apply.

---

## 5. Tear-down

```bash
dynadock down --prune
```

All containers, networks and the Caddy instance are removed.

---

### Next steps
* Check out the [Quick Start](../getting-started/quickstart.md) guide.
* See [Configuration](../getting-started/configuration.md) for `.dynadock.yaml` options.

—

Happy hacking! 🚀

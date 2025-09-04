# DynaDock Documentation

Welcome to **DynaDock** – a dynamic Docker Compose orchestrator that eliminates common local-development pain points:

* 🚀 Automatic *port allocation* – no more conflicts
* 🔒 One-command *TLS/HTTPS* via Caddy
* 🏷️ Local *sub-domains* like `api.local.dev`
* 📄 Automatic *.env* generation for every service

---

## Quick Start

```bash
# Install the CLI (requires Python ≥3.10 and the uv package-manager)
uv tool install dynadock

# Inside any directory containing a docker-compose.yaml
# spin everything up with TLS enabled:
dynadock up --enable-tls
```

Browse to `https://api.local.dev` (or the services defined in your compose file) – certificates are created automatically.

---

## Project Resources

| Resource | Location |
| -------- | -------- |
| Source code | `src/` |
| Command-line interface | `dynadock.cli` |
| Tests | `tests/` |
| MkDocs configuration | `docs/mkdocs.yml` |
| Make targets | `Makefile` |

---

Continue with the *Getting Started* guide for installation options, configuration flags and more examples (coming soon).

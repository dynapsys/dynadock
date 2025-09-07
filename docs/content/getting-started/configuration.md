# Configuration

DynaDock is *zero-config* by default – it analyses your `docker-compose.yaml` and generates sensible defaults.
However, you can override behaviour using the hidden file `.dynadock.yaml` placed next to your compose file.

## `.dynadock.yaml` reference

| Key | Type | Description |
|-----|------|-------------|
| `port_range` | object | Customise port allocation range |
| `tls.enabled` | bool | Enable/disable automatic TLS |
| `domain` | string | Base domain for local sub-domains |
| `caddyfile` | string | Path to a custom Caddyfile template |

Example:

```yaml
# .dynadock.yaml
port_range:
  start: 8000
  end: 8999

tls:
  enabled: true

domain: dynadock.lan
```

---

After editing the file, re-run:

```bash
dynadock up --reload
```

DynaDock will pick up your new configuration.

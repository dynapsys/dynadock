# Quick Start

The fastest way to see **DynaDock** in action.

1. **Install** (Python ≥3.10):
   ```bash
   uv pip install dynadock
   ```

2. **Navigate** to a folder that contains a valid `docker-compose.yaml` (or create one – see [examples](../examples/simple.md)).

3. **Run**:
   ```bash
   dynadock up --enable-tls
   ```
   * DynaDock allocates free ports, provisions TLS with Caddy and prints service URLs.*

4. **Tear-down**:
   ```bash
   dynadock down
   ```

---

### Typical CLI workflow

```bash
# Allocate ports & bring everything up
 dynadock up

# View current allocation
 dynadock status

# Export to Kubernetes manifests
 dynadock export --format k8s > deployment.yaml

# Clean up containers & resources
 dynadock down --prune
```

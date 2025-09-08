# 🚀 DynaDock

[![PyPI version](https://img.shields.io/pypi/v/dynadock.svg)](https://pypi.org/project/dynadock/)
[![Python versions](https://img.shields.io/pypi/pyversions/dynadock.svg)](https://pypi.org/project/dynadock/)
[![License](https://img.shields.io/github/license/dynapsys/dynadock)](https://github.com/dynapsys/dynadock/blob/main/LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/dynapsys/dynadock/test.yml?branch=main)](https://github.com/dynapsys/dynadock/actions)

**Advanced Docker Orchestration Platform with Automatic Local Domain Management**

DynaDock is an intelligent Docker container orchestration system that eliminates common development problems through dynamic port allocation, automatic HTTPS with a Caddy reverse proxy, and seamless local domain routing with LAN support.

---

## Quick Navigation

- **Project Documentation**
  - [Architecture](docs/ARCHITECTURE.md) - System diagrams and description
  - [Code Reference](docs/CODE_REFERENCE.md) - Source code documentation
- **User Guide**
  - [Installation & Usage](docs/USAGE.md) - Setup and configuration instructions
  - [Troubleshooting](docs/TROUBLESHOOTING.md) - Problem-solving guide
- **Development**
  - [Testing Framework](docs/TESTING_FRAMEWORK.md) - Testing and diagnostics system
  - [Contributing](#contributing) - How to contribute to the project

---

## ✨ Key Features

- **🔌 Dynamic Port Allocation**: Automatically scans for and allocates free ports to services, eliminating port conflicts.
- **🔒 Automatic TLS/HTTPS**: Caddy reverse proxy with automatic, trusted local certificates via `mkcert`.
- **🌐 Local Subdomain Routing**: Each service is accessible via a `service.dynadock.lan` URL with automatic routing.
- **⚡ Zero-Config Deployment**: Generates `.env.dynadock` files automatically for a seamless startup experience.
- **LAN-Visible Networking**: Access services from any device on your local network without any DNS configuration.

## 🚀 Quick Start

1. **Install DynaDock**:

   ```bash
   pip install dynadock
   ```

2. **Navigate to your project** directory (must contain a `docker-compose.yaml`):

   ```bash
   cd examples/fullstack/
   ```

3. **Start services** with LAN-visible networking (requires sudo):

   ```bash
   sudo dynadock up --lan-visible
   ```

Your services will be assigned local IP addresses and will be accessible from any device on your network.

## ✍️ Author

This project is developed and maintained by **Tom Sapletta**.

## Contributing

Contributions are welcome! If you have any ideas, suggestions, or bug reports, please open an issue or submit a pull request. For more information, please see the [contribution guidelines](CONTRIBUTING.md).

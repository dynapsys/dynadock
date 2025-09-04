# Installation

There are three supported ways to install **DynaDock**:

## 1. pip / uv (recommended)

```bash
uv pip install dynadock
```

The CLI `dynadock` will be available in your `$PATH`.

## 2. From source

Clone this repository and install in *editable* mode with dev extras:

```bash
git clone https://github.com/yourusername/dynadock.git
cd dynadock
uv pip install -e .[dev]
```

## 3. Docker image

```bash
docker pull dynapsys/dynadock:latest
docker run --rm -it -v "$PWD:/workspace" dynapsys/dynadock dynadock --help
```

---

> ℹ️  DynaDock requires Python 3.10 or higher and Docker Engine ≥ 20.10.

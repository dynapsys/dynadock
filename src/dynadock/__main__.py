"""DynaDock CLI entry point.

This module allows execution with `python -m dynadock` and simply
forwards to the top-level `dynadock.cli` entry function.
"""

from __future__ import annotations

from .cli import cli


def main() -> None:  # pragma: no cover – convenience wrapper
    """Invoke the Dynadock CLI."""
    cli()


if __name__ == "__main__":  # pragma: no cover – executed via `python -m`
    main()

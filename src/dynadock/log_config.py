from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the entire application."""
    log_dir = Path(".dynadock")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "dynadock.log"

    # Get the root logger
    root_logger = logging.getLogger()

    # Remove any existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set the logging level
    log_level = logging.DEBUG if verbose else logging.INFO
    root_logger.setLevel(log_level)

    # Create handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # Add handlers to the root logger
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)

    # Set the logger for the application
    logger = logging.getLogger("dynadock")
    logger.setLevel(log_level)

    if verbose:
        logger.debug("🔍 Verbose logging re-initialized")

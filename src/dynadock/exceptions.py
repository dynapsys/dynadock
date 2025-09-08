"""
DynaDock custom exceptions and error handling utilities.

This module provides a standardized exception hierarchy and error handling
utilities for consistent error management across the DynaDock project.
"""

from __future__ import annotations

import logging
import traceback
from typing import Optional, Any, Dict
from functools import wraps


class DynaDockError(Exception):
    """Base exception for all DynaDock-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DynaDockConfigError(DynaDockError):
    """Raised when there's an issue with DynaDock configuration."""

    pass


class DynaDockDockerError(DynaDockError):
    """Raised when Docker operations fail."""

    pass


class DynaDockNetworkError(DynaDockError):
    """Raised when network operations fail."""

    pass


class DynaDockPortError(DynaDockError):
    """Raised when port allocation fails."""

    pass


class DynaDockCaddyError(DynaDockError):
    """Raised when Caddy configuration or operations fail."""

    pass


class DynaDockValidationError(DynaDockError):
    """Raised when input validation fails."""

    pass


class DynaDockTimeoutError(DynaDockError):
    """Raised when operations timeout."""

    pass


class ErrorHandler:
    """Centralized error handling utilities."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def log_and_raise(
        self,
        exception_class: type[DynaDockError],
        message: str,
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an error and raise a DynaDock exception."""
        error_details = details or {}

        if original_error:
            error_details["original_error"] = str(original_error)
            error_details["original_type"] = type(original_error).__name__

        self.logger.error(f"❌ {message}")
        if original_error:
            self.logger.debug(f"Original error: {original_error}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")

        raise exception_class(message, error_details)

    def handle_subprocess_error(
        self, cmd: list[str], error: Exception, operation: str = "command execution"
    ) -> None:
        """Handle subprocess errors consistently."""
        import subprocess

        if isinstance(error, subprocess.CalledProcessError):
            stderr = error.stderr if error.stderr else "No error output"
            details = {
                "command": " ".join(cmd),
                "returncode": error.returncode,
                "stderr": stderr,
            }
            self.log_and_raise(
                DynaDockDockerError,
                f"Failed {operation}: {' '.join(cmd)}",
                error,
                details,
            )
        elif isinstance(error, subprocess.TimeoutExpired):
            details = {"command": " ".join(cmd), "timeout": error.timeout}
            self.log_and_raise(
                DynaDockTimeoutError,
                f"Command timed out after {error.timeout}s: {' '.join(cmd)}",
                error,
                details,
            )
        else:
            self.log_and_raise(
                DynaDockError,
                f"Unexpected error during {operation}",
                error,
                {"command": " ".join(cmd)},
            )

    def safe_execute(self, func, *args, **kwargs):
        """Execute a function with standardized error handling."""
        try:
            return func(*args, **kwargs)
        except DynaDockError:
            # Re-raise DynaDock errors as-is
            raise
        except Exception as e:
            self.log_and_raise(DynaDockError, f"Unexpected error in {func.__name__}", e)


def handle_errors(
    exception_class: type[DynaDockError] = DynaDockError,
    logger: Optional[logging.Logger] = None,
):
    """Decorator for standardized error handling."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(logger)
            try:
                return func(*args, **kwargs)
            except DynaDockError:
                # Re-raise DynaDock errors as-is
                raise
            except Exception as e:
                handler.log_and_raise(exception_class, f"Error in {func.__name__}", e)

        return wrapper

    return decorator


def validate_required_args(**kwargs) -> None:
    """Validate that required arguments are provided and not None/empty."""
    missing = []
    for name, value in kwargs.items():
        if value is None or (isinstance(value, (str, list, dict)) and not value):
            missing.append(name)

    if missing:
        raise DynaDockValidationError(
            f"Missing required arguments: {', '.join(missing)}",
            {"missing_args": missing},
        )


def format_error_message(error: Exception, include_traceback: bool = False) -> str:
    """Format error messages consistently."""
    if isinstance(error, DynaDockError):
        message = f"DynaDock Error: {error.message}"
        if error.details:
            details = ", ".join(f"{k}={v}" for k, v in error.details.items())
            message += f" ({details})"
    else:
        message = f"{type(error).__name__}: {str(error)}"

    if include_traceback:
        message += f"\n{traceback.format_exc()}"

    return message

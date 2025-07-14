"""
Structured logging system for AIStudioProxy.

This module provides a centralized logging system using structlog with support
for JSON formatting, log rotation, and contextual logging.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from structlog.types import FilteringBoundLogger

from .config import LogConfig, get_config


def setup_logger(log_config: Optional[LogConfig] = None) -> FilteringBoundLogger:
    """
    Set up the structured logging system.

    Args:
        log_config: Optional log configuration. If None, uses global config.

    Returns:
        Configured structlog logger instance.
    """
    if log_config is None:
        log_config = get_config().log

    # Configure standard library logging
    _configure_stdlib_logging(log_config)

    # Configure structlog
    _configure_structlog(log_config)

    # Get the configured logger
    logger = structlog.get_logger()

    # Log the logger initialization
    logger.info(
        "Logger initialized",
        level=log_config.level,
        format=log_config.format,
        file_path=log_config.file_path,
    )

    return logger


def _configure_stdlib_logging(log_config: LogConfig) -> None:
    """Configure the standard library logging."""
    # Set the root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_config.level))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatters
    if log_config.format == "json":
        formatter = logging.Formatter(fmt="%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_config.level))
    root_logger.addHandler(console_handler)

    # File handler with rotation (if file path is specified)
    if log_config.file_path:
        file_path = Path(log_config.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Parse max_size (e.g., "10MB" -> 10 * 1024 * 1024)
        max_bytes = _parse_size(log_config.max_size)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=file_path,
            maxBytes=max_bytes,
            backupCount=log_config.backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, log_config.level))
        root_logger.addHandler(file_handler)


def _configure_structlog(log_config: LogConfig) -> None:
    """Configure structlog with appropriate processors."""
    # Common processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add format-specific processors
    if log_config.format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _parse_size(size_str: str) -> int:
    """
    Parse size string like '10MB' into bytes.

    Args:
        size_str: Size string (e.g., '10MB', '1GB', '500KB')

    Returns:
        Size in bytes
    """
    size_str = size_str.upper().strip()

    # Size multipliers
    multipliers = {
        "TB": 1024**4,
        "GB": 1024**3,
        "MB": 1024**2,
        "KB": 1024,
        "B": 1,
    }

    # Extract number and unit
    for unit, multiplier in multipliers.items():
        if size_str.endswith(unit):
            number_str = size_str[: -len(unit)].strip()
            try:
                number = float(number_str)
                return int(number * multiplier)
            except ValueError:
                # This will be caught by the final try-except
                pass

    # Default to treating as bytes if parsing fails
    try:
        return int(size_str)
    except ValueError:
        return 10 * 1024 * 1024  # Default to 10MB


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""

    @property
    def logger(self) -> FilteringBoundLogger:
        """Get a logger bound to this class."""
        if not hasattr(self, "_logger"):
            self._logger = structlog.get_logger(self.__class__.__name__)
        return self._logger

    def log_method_call(self, method_name: str, **kwargs: Any) -> None:
        """Log a method call with parameters."""
        self.logger.debug(
            f"Calling {method_name}",
            method=method_name,
            class_name=self.__class__.__name__,
            **kwargs,
        )

    def log_method_result(
        self, method_name: str, result: Any = None, **kwargs: Any
    ) -> None:
        """Log a method result."""
        self.logger.debug(
            f"Method {method_name} completed",
            method=method_name,
            class_name=self.__class__.__name__,
            result_type=type(result).__name__ if result is not None else None,
            **kwargs,
        )

    def log_error(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an error with context."""
        self.logger.error(
            f"Error in {self.__class__.__name__}",
            error_type=type(error).__name__,
            error_message=str(error),
            class_name=self.__class__.__name__,
            **(context or {}),
        )


def get_logger(name: Optional[str] = None) -> FilteringBoundLogger:
    """
    Get a logger instance.

    Args:
        name: Logger name. If None, uses the caller's module name.

    Returns:
        Configured structlog logger instance.
    """
    return structlog.get_logger(name)


def configure_third_party_loggers() -> None:
    """Configure third-party library loggers to reduce noise."""
    # Reduce noise from third-party libraries
    noisy_loggers = [
        "urllib3.connectionpool",
        "requests.packages.urllib3.connectionpool",
        "asyncio",
        "playwright",
        "camoufox",
    ]

    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


# Global logger instance
logger = structlog.get_logger(__name__)


def init_logging() -> FilteringBoundLogger:
    """
    Initialize the logging system with default configuration.

    Returns:
        Configured logger instance.
    """
    logger_instance = setup_logger()
    configure_third_party_loggers()
    return logger_instance

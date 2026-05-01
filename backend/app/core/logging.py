"""Structured JSON logging configuration.

This module configures structured logging compatible with Google Cloud Logging.
Logs are output as JSON for easier parsing and querying in production.
"""

import logging
import sys
from datetime import UTC, datetime
from typing import Any

from pythonjsonlogger import jsonlogger

from app.config import get_settings

settings = get_settings()


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging.

    Adds timestamp, severity level, and other GCP-compatible fields.
    """

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.now(UTC).isoformat()

        # Add severity level (GCP uses severity instead of levelname)
        log_record["severity"] = record.levelname

        # Add service context
        log_record["service"] = {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

        # Add source location
        log_record["sourceLocation"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Remove default fields that are redundant
        log_record.pop("levelname", None)


def setup_logging() -> None:
    """Configure application logging.

    Sets up JSON-formatted logging for production and human-readable
    logging for development.
    """
    # Determine log level
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Use JSON formatter in production or when LOG_JSON=true
    formatter: logging.Formatter
    if settings.is_production or settings.log_json:
        formatter = CustomJsonFormatter("%(timestamp)s %(severity)s %(name)s %(message)s")
    else:
        # Human-readable format for development
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

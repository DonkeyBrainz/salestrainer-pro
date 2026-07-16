"""Structured JSON logging configuration.

This module configures structured logging compatible with Google Cloud Logging.
Logs are output as JSON for easier parsing and querying in production.
"""

import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

from pythonjsonlogger import jsonlogger

from app.config import get_settings

settings = get_settings()

# Third-party transport libraries log raw request headers (incl. API keys) at
# DEBUG — this is exactly how a Gemini key once ended up committed in a saved
# log file. Redact known-sensitive patterns regardless of logger/level so a
# future DEBUG session or saved log can't leak a live credential again.
_SECRET_PATTERNS = [
    re.compile(r"(x-goog-api-key:\s*)\S+", re.IGNORECASE),
    re.compile(r"(Authorization:\s*Bearer\s+)\S+", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
]


class RedactSecretsFilter(logging.Filter):
    """Scrubs API keys / bearer tokens out of log messages before they're emitted."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for pattern in _SECRET_PATTERNS:
            message = pattern.sub(
                lambda m: (m.group(1) + "<redacted>") if m.groups() else "<redacted>",
                message,
            )
        record.msg = message
        record.args = ()
        return True


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
    handler.addFilter(RedactSecretsFilter())
    root_logger.addHandler(handler)

    # Silence noisy loggers. websockets/grpc/google.genai log raw request
    # headers (including the Gemini API key) at DEBUG — the redact filter
    # above is defense in depth, but there's no reason to emit this at all.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("grpc").setLevel(logging.WARNING)
    logging.getLogger("google.genai").setLevel(logging.WARNING)
    logging.getLogger("google.auth").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

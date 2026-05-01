"""Type stubs for pythonjsonlogger.jsonlogger."""

import logging
from typing import Any

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, fmt: str | None = None, *args: Any, **kwargs: Any) -> None: ...
    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None: ...

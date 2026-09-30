"""Structured logging configuration for Chronicle."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from chronicle.config import settings


class ErrorCategory(str, Enum):
    """Standardized error categories for consistent observability."""

    API = "api"
    DATABASE = "database"
    NETWORK = "network"
    NLP = "nlp"
    CLUSTERING = "clustering"
    SYSTEM = "system"


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        extra_data = getattr(record, "extra_data", None)
        if isinstance(extra_data, dict):
            log_data.update(extra_data)

        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """Configure root Chronicle logger once and return it."""
    logger = logging.getLogger("chronicle")

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    if logger.handlers:
        for existing_handler in logger.handlers:
            existing_handler.setLevel(level)
        return logger

    handler: logging.Handler
    if settings.log_file:
        from pathlib import Path

        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(settings.log_file)
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setLevel(level)

    if settings.log_format == "json":
        formatter: logging.Formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger that inherits Chronicle handlers."""
    base_logger = setup_logging()
    logger = logging.getLogger(name)
    logger.setLevel(base_logger.level)
    logger.handlers = base_logger.handlers
    logger.propagate = False
    return logger


def log_with_context(
    logger: logging.Logger, level: str, message: str, **kwargs: Any
) -> None:
    """Log message with additional structured context."""
    level_value = getattr(logging, level.upper(), logging.INFO)
    if kwargs:
        logger.log(level_value, message, extra={"extra_data": kwargs})
    else:
        logger.log(level_value, message)


def log_metric(
    logger: logging.Logger, name: str, value: float = 1.0, **tags: Any
) -> None:
    """Emit a lightweight metric event via structured logs."""
    log_with_context(logger, "INFO", "metric", metric=name, value=value, **tags)


def log_exception(
    logger: logging.Logger,
    category: ErrorCategory,
    message: str,
    exc: Exception,
    **context: Any,
) -> None:
    """Log exceptions with standardized error taxonomy and context."""
    extra_data = {"error_category": category.value, **context}
    logger.error(
        f"{message}: {exc}",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={"extra_data": extra_data},
    )


# Global logger instance for package-level use
logger = setup_logging()

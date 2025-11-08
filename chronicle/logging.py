"""Structured logging configuration for Chronicle."""
from __future__ import annotations
import logging
import sys
import json
from typing import Any
from datetime import datetime
from chronicle.config import settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data)


def setup_logging() -> logging.Logger:
    """Configure logging for Chronicle."""
    logger = logging.getLogger("chronicle")
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Set level from config
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Create handler
    if settings.log_file:
        from pathlib import Path
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(settings.log_file)
    else:
        handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter
    if settings.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Don't propagate to root logger
    logger.propagate = False
    
    return logger


# Global logger instance
logger = setup_logging()


def log_with_context(level: str, message: str, **kwargs: Any) -> None:
    """Log message with additional context."""
    extra_record = type('obj', (object,), {'extra_data': kwargs})()
    getattr(logger, level.lower())(message, extra=extra_record)

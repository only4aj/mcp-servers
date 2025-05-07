# Reusable logging configuration - can be copied directly from the YouTube example
import logging
from logging.config import dictConfig
import os

"""Configures basic logging for the application."""
# Use specific env var prefix if desired, or keep generic
logging_level = os.getenv("MCP_TELEGRAM_LOG_LEVEL", "INFO").upper()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # Preserve existing loggers
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO", # Console logs INFO and above by default
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": "app.log", # Log file name
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": "DEBUG" # File logs DEBUG and above by default
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": f"{logging_level}" # Overall level set by env var
    },
    # Configure logging for specific libraries if needed
    "loggers": {
        "uvicorn.error": {
            "level": "INFO", # Example: Control uvicorn error level
            "handlers": ["console", "file"],
            "propagate": False,
        },
         "uvicorn.access": {
            "level": "WARNING", # Example: Reduce access log noise
            "handlers": ["console", "file"],
            "propagate": False,
        }
    }
}

def configure_logging():
    """Apply logging configuration."""
    dictConfig(LOGGING_CONFIG)
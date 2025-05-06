import logging
from logging.config import dictConfig
import os

"""Configures basic logging for the application."""
# Use specific env var prefix
logging_level = os.getenv("MCP_ARXIV_LOG_LEVEL", "INFO").upper()
log_file_path = os.getenv("MCP_ARXIV_LOG_FILE", "app_arxiv.log") # Unique log file

# Ensure log directory exists if a path is specified
log_dir = os.path.dirname(log_file_path)
if log_dir and not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except OSError as e:
        print(f"Warning: Could not create log directory '{log_dir}'. Logging to file might fail. Error: {e}")
        log_file_path = "app_arxiv.log" # Fallback to current dir

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
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
            "level": "INFO",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": log_file_path,
            "maxBytes": 10485760,
            "backupCount": 5,
            "level": "DEBUG"
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": f"{logging_level}"
    },
    "loggers": {
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
         "uvicorn.access": {
            "level": "WARNING",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "arxiv": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        }
    }
}

def configure_logging():
    """Apply logging configuration."""
    try:
        dictConfig(LOGGING_CONFIG)
        logging.getLogger(__name__).info(f"Logging configured. Level: {logging_level}, File: {log_file_path}")
    except Exception as e:
        logging.basicConfig(level=logging_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.getLogger(__name__).error(f"Failed dict logging config: {e}. Falling back.", exc_info=True)
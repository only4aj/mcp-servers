from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from pathlib import Path

# --- Configuration and Error Classes --- #

class TelegramClientError(Exception):
    """Base exception for Telegram client errors."""
    pass

class TelegramApiError(TelegramClientError):
    """Exception raised for errors during Telegram Bot API calls."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details

    def __str__(self) -> str:
        base = super().__str__()
        if self.status_code:
            return f"{base} (HTTP Status: {self.status_code})"
        if self.details:
            return f"{base} Details: {self.details}"
        return base

class TelegramConfig:
    """
    Configuration for connecting to the Telegram Bot API.
    Reads directly from environment variables.
    """
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        self.token = os.environ.get("TELEGRAM_TOKEN")
        self.channel = os.environ.get("TELEGRAM_CHANNEL")
        
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN environment variable is not set")
        if not self.channel:
            raise ValueError("TELEGRAM_CHANNEL environment variable is not set")
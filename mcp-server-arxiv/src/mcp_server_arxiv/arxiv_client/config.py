import logging
from typing import Optional, Any
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# --- Configuration and Error Classes --- #

class ArxivClientError(Exception):
    """Base exception for ArXiv client errors."""
    pass

class ArxivConfigError(ArxivClientError):
    """Configuration-related errors for ArXiv client."""
    pass

class ArxivApiError(ArxivClientError):
    """Exception raised for errors during ArXiv API calls or processing."""
    pass

class ArxivConfig(BaseSettings):
    """
    Configuration for the ArXiv Search Service.
    Reads from environment variables prefixed with ARXIV_.
    """
    model_config = SettingsConfigDict(
        env_prefix="ARXIV_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    default_max_results: int = Field(default=5, ge=1, le=50)
    default_max_text_length: Optional[int] = Field(default=None, ge=100) # Optional limit

    def __init__(self, **values: Any):
        try:
            super().__init__(**values)
            logger.info("ArxivConfig loaded successfully.")
            logger.debug(f"Arxiv Config: MaxResultsDefault={self.default_max_results}, MaxTextLengthDefault={self.default_max_text_length}")
        except ValidationError as e:
            logger.error(f"Arxiv configuration validation failed: {e}", exc_info=True)
            raise ArxivConfigError(f"Arxiv configuration validation failed: {e}") from e
        except Exception as e:
             logger.error(f"Unexpected error loading ArxivConfig: {e}", exc_info=True)
             raise ArxivConfigError(f"Unexpected error loading ArxivConfig: {e}") from e
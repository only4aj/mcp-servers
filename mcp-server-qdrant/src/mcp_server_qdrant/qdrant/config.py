import logging
from typing import Optional, Union

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mcp_server_qdrant.qdrant.embeddings.types import EmbeddingProviderType

logger = logging.getLogger(__name__)

# --- Configuration and Error Classes --- #

class QdrantServiceError(Exception):
    """Base class for Qdrant service-related errors."""
    pass

class QdrantConfigError(QdrantServiceError):
    """Configuration-related errors for Qdrant client."""
    pass

class QdrantAPIError(QdrantServiceError):
    """Errors during Qdrant API operations."""
    pass

class EmbeddingProviderSettings(BaseSettings):
    """
    Configuration for the embedding provider.
    """
    
    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    provider_type: EmbeddingProviderType = Field(
        default=EmbeddingProviderType.FASTEMBED,
        validation_alias="PROVIDER",
    )
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias="MODEL",
    )


class QdrantConfig(BaseSettings):
    """
    Configuration for connecting to Qdrant vector database service.
    Reads from environment variables prefixed with QDRANT_.
    """

    model_config = SettingsConfigDict(
        env_prefix="QDRANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Connection settings
    host: str = "localhost"  # Qdrant server host
    port: int = 6333  # REST API port
    grpc_port: int = 6334  # gRPC API port (optional)
    api_key: str | None = None  # API key for cloud deployments
    local_path: str | None = None  # Local path for storage (alternative to host/port)
    
    @model_validator(mode="after")
    def empty_string_to_none(self) -> "QdrantConfig":
        """Convert empty strings to None for all fields with None in their type annotation."""
        for field_name, field in self.__class__.model_fields.items():
            # Check if field type annotation includes None
            annotation = getattr(field, "annotation", None)
            has_none_type = getattr(annotation, "__args__", None) and type(None) in annotation.__args__
            
            # If field can be None and current value is empty string, convert to None
            if has_none_type:
                value = getattr(self, field_name, None)
                if isinstance(value, str) and value == "":
                    setattr(self, field_name, None)
                    
        return self
    
    @property
    def location(self) -> str:
        """Return the location string for Qdrant client."""
        if not self.host:
            return ""
        return f"{self.host}:{self.port}" 
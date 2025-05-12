import logging
import uuid
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient, models

from mcp_server_qdrant.qdrant.embeddings.base import EmbeddingProvider
from mcp_server_qdrant.qdrant.embeddings.factory import create_embedding_provider
from mcp_server_qdrant.qdrant.config import QdrantConfig, QdrantAPIError, EmbeddingProviderSettings

logger = logging.getLogger(__name__)

# --- Type Definitions --- #

Metadata = Dict[str, Any]


class Entry(BaseModel):
    """
    A single entry in the Qdrant collection.
    """

    content: str
    metadata: Optional[Metadata] = None

    def __str__(self) -> str:
        """
        Return a string representation of the entry.
        """
        return f"Entry(content={self.content}, metadata={self.metadata})"


# --- Main Service Class --- #

class QdrantConnector:
    """
    Encapsulates the connection to a Qdrant server and all the methods to interact with it.
    """

    def __init__(
        self,
        config: QdrantConfig,
        embedding_provider: EmbeddingProvider,
    ):
        """
        Initialize the Qdrant connector.
        
        Args:
            config: The Qdrant configuration
            embedding_provider: The embedding provider to use
        """
        self._config = config
        self._embedding_provider = embedding_provider
        self._client = None

        # TODO remove
        print(f"config: {config}")
        
        # Initialize the client
        self._client = AsyncQdrantClient(
            location=config.location, 
            api_key=config.api_key,
            path=config.local_path
        )
        
        logger.info(f"Initialized Qdrant connector: location={config.location or 'local'}")

    async def get_collection_names(self) -> List[str]:
        """
        Get the names of all collections in the Qdrant server.
        
        Returns:
            A list of collection names
        """
        response = await self._client.get_collections()
        return [collection.name for collection in response.collections]

    async def store(self, entry: Entry, collection_name: str) -> None:
        """
        Store information in the Qdrant collection with metadata.
        
        Args:
            entry: The entry to store (content + metadata)
            collection_name: Optional collection name, defaults to config
            
        Raises:
            QdrantAPIError: If there's an issue storing the entry
        """
    
        try:
            # Create the collection if it doesn't exist
            await self._ensure_collection_exists(collection_name)

            # Embed the document
            embeddings = await self._embedding_provider.embed_documents([entry.content])

            # Add to Qdrant
            vector_name = self._embedding_provider.get_vector_name()
            payload = {"document": entry.content, "metadata": entry.metadata}
            
            await self._client.upsert(
                collection_name=collection_name,
                points=[
                    models.PointStruct(
                        id=uuid.uuid4().hex,
                        vector={vector_name: embeddings[0]},
                        payload=payload,
                    )
                ],
            )
            logger.debug(f"Stored entry in collection '{collection_name}'")
            
        except Exception as e:
            error_msg = f"Failed to store entry in Qdrant: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise QdrantAPIError(error_msg) from e

    async def search(
        self, query: str, collection_name: str, limit: int = 10
    ) -> List[Entry]:
        """
        Find entries in the Qdrant collection by semantic similarity.
        
        Args:
            query: The search query
            collection_name: Optional collection name, defaults to config
            limit: Max number of results, defaults to config
            
        Returns:
            List of entries found, empty list if none or collection doesn't exist
            
        Raises:
            QdrantAPIError: If there's an issue searching the entries
        """
            
        try:
            collection_exists = await self._client.collection_exists(collection_name)
            if not collection_exists:
                logger.warning(f"Collection '{collection_name}' does not exist")
                return []

            # Embed the query
            query_vector = await self._embedding_provider.embed_query(query)
            vector_name = self._embedding_provider.get_vector_name()

            # Search in Qdrant
            search_results = await self._client.query_points(
                collection_name=collection_name,
                query=query_vector,
                using=vector_name,
                limit=limit,
            )
            
            logger.debug(f"Found {len(search_results.points)} results for query in '{collection_name}'")

            return [
                Entry(
                    content=result.payload["document"],
                    metadata=result.payload.get("metadata"),
                )
                for result in search_results.points
            ]
        except Exception as e:
            error_msg = f"Failed to search in Qdrant: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise QdrantAPIError(error_msg) from e

    async def _ensure_collection_exists(self, collection_name: str) -> None:
        """
        Ensure that the collection exists, creating it if necessary.
        
        Args:
            collection_name: The collection name to check/create
        """
        collection_exists = await self._client.collection_exists(collection_name)
        if not collection_exists:
            # Create the collection with the appropriate vector size
            vector_size = self._embedding_provider.get_vector_size()

            # Use the vector name as defined in the embedding provider
            vector_name = self._embedding_provider.get_vector_name()
            await self._client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    vector_name: models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    )
                },
            )
            logger.info(f"Created new collection '{collection_name}'")


@lru_cache(maxsize=1)
def get_qdrant_connector() -> QdrantConnector:
    """
    Get a singleton instance of the QdrantConnector.
    
    The connector is created with default configuration from environment 
    variables and cached for reuse.
    
    Returns:
        QdrantConnector instance
    """
    config = QdrantConfig()
    embedding_provider_settings = EmbeddingProviderSettings()
    embedding_provider = create_embedding_provider(embedding_provider_settings)
    return QdrantConnector(config, embedding_provider) 
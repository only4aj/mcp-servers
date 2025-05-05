import logging
from typing import Any
from functools import lru_cache
import json
from langchain_tavily import TavilySearch
from langchain_core.documents import Document
from mcp_server_tavily.tavily.config import TavilyConfig, TavilyServiceError, TavilyApiError, TavilyConfigError
from mcp_server_tavily.tavily.models import TavilySearchResult

logger = logging.getLogger(__name__)

class _TavilyService:
    """Encapsulates Tavily client logic and configuration."""

    def __init__(self, config: TavilyConfig):
        self.config = config
        logger.info("TavilyService initialized.")

    def _create_tavily_tool(self, max_results: int | None = None) -> Any:
        """Creates an instance of the TavilySearch tool with current config."""
        
        try:
            return TavilySearch(
                api_key=self.config.api_key,
                max_results = max_results or self.config.max_results,
                topic=self.config.topic,
                search_depth=self.config.search_depth,
                include_answer=self.config.include_answer,
                include_raw_content=self.config.include_raw_content,
                include_images=self.config.include_images
            )
        except Exception as e:
            logger.error(f"Passed TavilyConfig did not match TavilySearch parameters schema: {self.config}", exc_info=True)
            raise TavilyConfigError(f"Error creating TavilySearch tool: {e}") from e

    async def search(self, query: str, max_results: int | None = None) -> list[TavilySearchResult]:
        """
        Performs a web search using the Tavily API.

        Args:
            query: The search query string.
            max_results: Optional override for the maximum number of results.

        Returns:
            A list of search result dictionaries on success.

        Raises:
            TavilyApiError: For errors during the Tavily API call.
            TavilyServiceError: For general client issues.
        """
        
        if not query:
            logger.warning("Received empty query for Tavily search.")
            raise ValueError("Search query cannot be empty.")
        
        logger.info(f"Performing Tavily search for query: '{query[:100]}...'")

        try:
            # Create tool
            tool = self._create_tavily_tool(max_results=max_results)

            # Perform search
            results = await tool.ainvoke(query)
            
            logger.debug(f"Tavily raw response type: {type(results)}")
            
            if not results:
                logger.warning("Tavily returned empty results.")
                return [TavilySearchResult(title="No Results", url="#", content="No results were found for this search query.")]
            
            if results == "error":
                logger.warning("Tavily returned an error.")
                return [TavilySearchResult(title="Search Error", url="#", content="The Tavily API returned an error. This might be due to API key issues, rate limiting, or service unavailability.")]
            
            if isinstance(results, str):
                logger.warning(f"Tavily returned a string instead of a list: {results}")
                results =  [TavilySearchResult(title="Search Result", url="#", content=results)]
            
            logger.debug(f"Tavily processed results: {results}")
            logger.info(f"Tavily search successful, received {len(results)} results.")
            return [TavilySearchResult(title=result.title, 
                                       url=result.url, 
                                       content=result.content) for result in results]

        except Exception as e:
            logger.error(f"Error during Tavily API call for query '{query}': {e}", exc_info=True)
            return [TavilySearchResult(title="Search Error", url="#", content=f"An error occurred during the search: {str(e)}")]

 
@lru_cache(maxsize=1)
def get_tavily_service() -> _TavilyService:
    """
    Factory function to get a singleton instance of the Tavily service.
    Handles configuration loading and service initialization.

    Returns:
        An initialized _TavilyService instance.

    Raises:
        TavilyConfigError: If configuration loading or validation fails.
        TavilyServiceError: If the langchain-tavily package isn't installed.
    """
    config = TavilyConfig() 
    service = _TavilyService(config=config)
    logger.info("Tavily service instance retrieved successfully.")
    return service
    
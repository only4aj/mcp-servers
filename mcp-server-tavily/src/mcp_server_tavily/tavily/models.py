from dataclasses import dataclass


@dataclass(frozen=True)
class TavilySearchResult:
    """Represents a search result from the Tavily API."""

    title: str
    url: str
    content: str

    def __str__(self) -> str:
        """Returns a string representation of the TavilySearchResult object."""
        return f"Title: {self.title}\nURL: {self.url}\nContent: {self.content}"

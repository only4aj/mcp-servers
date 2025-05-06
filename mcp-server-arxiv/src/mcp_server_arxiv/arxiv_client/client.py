import asyncio
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache
import os
import tempfile



import arxiv
import fitz 


# Handle both module imports and direct script execution
try:
    from .config import ArxivConfig, ArxivClientError, ArxivApiError, ArxivConfigError
except ImportError:
    from mcp_server_arxiv.arxiv_client.config import ArxivConfig, ArxivClientError, ArxivApiError, ArxivConfigError

logger = logging.getLogger(__name__)

# Type alias must be defined before use
ArxivResultDict = Dict[str, Any]

async def _download_and_extract_pdf(paper: arxiv.Result, temp_dir: str, max_text_length: Optional[int]) -> str:
    """Helper function to download and extract text from a single PDF."""
    return await _async_download_and_extract(paper, temp_dir, max_text_length)

async def _async_download_and_extract(paper: arxiv.Result, temp_dir: str, max_text_length: Optional[int]) -> str:
    """Asynchronous version of download/extract logic."""
    loop = asyncio.get_running_loop()
    full_text = "N/A"
    temp_pdf_path = None
    try:
        # Define a safe filename
        safe_filename = f"{paper.get_short_id().replace('/', '_')}.pdf"
        temp_pdf_path = os.path.join(temp_dir, safe_filename)
        logger.info(f"  Downloading PDF for {paper.entry_id} to: {temp_pdf_path}")
        
        # Run download in executor as it's a blocking operation
        await loop.run_in_executor(
            None,
            lambda: paper.download_pdf(dirpath=temp_dir, filename=safe_filename)
        )
        logger.info(f"  Download successful for {paper.entry_id}.")

        logger.info(f"  Parsing PDF: {temp_pdf_path}")
        # PDF parsing is CPU-bound, run in executor
        def parse_pdf():
            doc = fitz.open(temp_pdf_path)
            extracted_pages = [page.get_text("text", sort=True) for page in doc]
            doc.close()
            return "\n".join(extracted_pages).strip()
            
        full_text = await loop.run_in_executor(None, parse_pdf)

        if not full_text:
             full_text = "[Could not extract text content from PDF]"
        elif max_text_length is not None and len(full_text) > max_text_length:
             full_text = full_text[:max_text_length] + f"... (truncated to {max_text_length} chars)"
        logger.info(f"  Successfully extracted text for {paper.entry_id} (length: {len(full_text)} chars).")
        return full_text

    except FileNotFoundError:
         error_msg = "[Download failed or file not found after download attempt]"
         logger.error(f"  Error for {paper.entry_id}: {error_msg}")
         return error_msg
    except arxiv.arxiv.DownloadError as e:
        error_msg = f"[Failed to download PDF: {e}]"
        logger.error(f"  Error for {paper.entry_id}: {error_msg}")
        return error_msg
    except fitz.fitz.FitzError as e:
        error_msg = f"[Failed to parse PDF: {e}]"
        logger.error(f"  Error for {paper.entry_id}: {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = f"[Unexpected error processing PDF {paper.entry_id}: {type(e).__name__} - {e}]"
        logger.error(f"  Error for {paper.entry_id}: {error_msg}", exc_info=True)
        return error_msg
    finally:
         # Cleanup individual PDF immediately after processing
         if temp_pdf_path and os.path.exists(temp_pdf_path):
             try:
                 os.remove(temp_pdf_path)
                 logger.debug(f"  Deleted temporary PDF: {temp_pdf_path}")
             except Exception as e:
                 logger.warning(f"  Failed to delete temporary PDF {temp_pdf_path}: {e}")

class ArxivService:
    """Encapsulates ArXiv client logic and configuration."""

    def __init__(self, config: ArxivConfig):
        self.config = config
        if arxiv is None or fitz is None:
            logger.error("arxiv or PyMuPDF package not installed. Arxiv service unavailable.")
            raise ArxivClientError("Required package 'arxiv' or 'PyMuPDF' not installed.")
        self.client = arxiv.Client() # Standard sync client
        logger.info("ArxivService initialized.")

    async def search(
        self,
        query: str,
        max_results_override: Optional[int] = None,
        max_text_length_override: Optional[int] = None
    ) -> List[ArxivResultDict]:
        """
        Performs an ArXiv search, downloads PDFs, and extracts text asynchronously.

        Args:
            query: The search query string.
            max_results_override: Optional override for the maximum number of results.
            max_text_length_override: Optional override for maximum text length per paper.

        Returns:
            A list of dictionaries, each representing a paper with its details and extracted text.

        Raises:
            ArxivApiError: For errors during the ArXiv API call or processing.
            ArxivClientError: For general client issues.
            ValueError: If query is empty.
        """
        logger.info(f"Performing ArXiv search for query: '{query[:100]}...'")
        if not query:
            logger.warning("Received empty query for ArXiv search.")
            raise ValueError("Search query cannot be empty.")

        effective_max_results = max_results_override if max_results_override is not None else self.config.default_max_results
        effective_max_text_length = max_text_length_override if max_text_length_override is not None else self.config.default_max_text_length

        try:
            loop = asyncio.get_running_loop()
            
            # Create search object in executor
            search_obj = await loop.run_in_executor(
                None,
                lambda: arxiv.Search(
                    query=query,
                    max_results=effective_max_results * 2, 
                    sort_by=arxiv.SortCriterion.Relevance
                )
            )
            
            # Get results iterator in executor
            results_iterator = await loop.run_in_executor(
                None, 
                self.client.results,
                search_obj
            )

            final_results_list = []
            processed_count = 0
            tasks = []

            # Use a single temporary directory for all downloads in this search
            with tempfile.TemporaryDirectory() as temp_dir:
                 logger.info(f"Created temporary directory for downloads: {temp_dir}")

                 # Iterate through results and create async tasks for PDF processing
                 while processed_count < effective_max_results:
                    try:
                        # Get next paper from iterator in executor
                        paper = await loop.run_in_executor(
                            None,
                            lambda: next(results_iterator, None)
                        )
                        
                        if paper is None:
                             logger.info("No more results from ArXiv iterator.")
                             break

                        logger.info(f"Processing paper: {paper.title[:80]}...")
                        paper_info = {
                             "title": paper.title,
                             "authors": [author.name for author in paper.authors],
                             "published": paper.published.strftime('%Y-%m-%d') if paper.published else "N/A",
                             "summary": paper.summary,
                             "link": paper.entry_id,
                             "pdf_link": paper.pdf_url,
                             "full_text": "Fetching...", # Placeholder
                             "error": None
                        }
                        # Create a task to download/extract PDF
                        task = asyncio.create_task(
                             _download_and_extract_pdf(paper, temp_dir, effective_max_text_length),
                             name=f"pdf_process_{paper.entry_id}"
                        )
                        tasks.append((task, paper_info)) # Store task and its corresponding info dict
                        processed_count += 1

                    except StopIteration: 
                         logger.info("ArXiv iterator finished.")
                         break
                    except Exception as iter_err:
                        logger.error(f"Error fetching next result from ArXiv iterator: {iter_err}", exc_info=True)
                        continue 

                 # Wait for all PDF processing tasks to complete
                 if tasks:
                     logger.info(f"Waiting for {len(tasks)} PDF processing tasks to complete...")
                     results = await asyncio.gather(*[t[0] for t in tasks], return_exceptions=True)
                     logger.info("All PDF processing tasks finished.")

                     # Populate the full_text or error field in paper_info dicts
                     for i, result_or_exc in enumerate(results):
                         task, paper_info_dict = tasks[i] # Get corresponding info
                         if isinstance(result_or_exc, Exception):
                             logger.error(f"Task {task.get_name()} failed: {result_or_exc}")
                             paper_info_dict["full_text"] = f"[Error processing PDF: {result_or_exc}]"
                             paper_info_dict["error"] = str(result_or_exc)
                         elif isinstance(result_or_exc, str):
                             paper_info_dict["full_text"] = result_or_exc
                             if result_or_exc.startswith("["): 
                                 paper_info_dict["error"] = result_or_exc
                         else:
                              logger.warning(f"Task {task.get_name()} returned unexpected type: {type(result_or_exc)}")
                              paper_info_dict["full_text"] = "[Unexpected processing result type]"
                              paper_info_dict["error"] = "Unexpected result type"

                         final_results_list.append(paper_info_dict) 

            logger.info(f"ArXiv search successful, processed {len(final_results_list)} papers.")
            return final_results_list

        except ValueError as ve: 
            raise ve 
        except Exception as e:
            logger.error(f"Error during ArXiv search for query '{query}': {e}", exc_info=True)
            raise ArxivApiError(f"Error during ArXiv search operation: {e}") from e

    def format_results(self, results: List[ArxivResultDict]) -> str:
        """Formats the list of ArXiv result dictionaries into a readable string."""
        if not results:
            return "No relevant papers found or processed on arXiv."

        formatted_lines = ["ArXiv Search Results:"]
        for i, paper in enumerate(results):
            formatted_lines.append("\n---")
            formatted_lines.append(f"\nPaper {i+1}:")
            formatted_lines.append(f"  Title: {paper.get('title', 'N/A')}")
            formatted_lines.append(f"  Authors: {', '.join(paper.get('authors', ['N/A']))}")
            formatted_lines.append(f"  Published: {paper.get('published', 'N/A')}")
            formatted_lines.append(f"  Link: {paper.get('link', '#')}")
            formatted_lines.append(f"  PDF Link: {paper.get('pdf_link', '#')}")
            formatted_lines.append(f"  Summary: {paper.get('summary', 'N/A')}")
            # Include full text, respecting truncation note
            full_text = paper.get('full_text', 'N/A')
            formatted_lines.append(f"  Full Text: {full_text}") # Already potentially truncated
            if paper.get('error'):
                 formatted_lines.append(f"  Processing Error: {paper['error']}")


        return "\n".join(formatted_lines)


_arxiv_service_instance = None

async def get_arxiv_service() -> ArxivService:
    """
    Factory function to get a singleton instance of the Arxiv service.
    Handles configuration loading and service initialization.

    Returns:
        An initialized ArxivService instance.

    Raises:
        ArxivConfigError: If configuration loading or validation fails.
        ArxivClientError: If required libraries aren't installed.
    """
    global _arxiv_service_instance
    
    if _arxiv_service_instance is not None:
        return _arxiv_service_instance
        
    logger.debug("Attempting to get Arxiv service instance...")
    try:
        config = ArxivConfig() # Load and validate config
        _arxiv_service_instance = ArxivService(config=config)
        logger.info("Arxiv service instance created successfully.")
        return _arxiv_service_instance
    except (ArxivConfigError, ArxivClientError) as e:
        logger.error(f"FATAL: Failed to initialize Arxiv service: {e}", exc_info=True)
        raise # Re-raise specific error
    except Exception as e:
        logger.error(f"FATAL: Unexpected error initializing Arxiv service: {e}", exc_info=True)
        raise ArxivConfigError(f"Unexpected error during Arxiv service initialization: {e}") from e
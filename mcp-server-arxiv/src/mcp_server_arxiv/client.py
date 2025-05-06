# src/mcp_server_arxiv/client.py

import os
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# MCP and agent-related imports
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langgraph.prebuilt import create_react_agent
    from langchain_together import ChatTogether
    from langchain_core.tools import StructuredTool
    from langchain_core.messages import HumanMessage
except ImportError as e:
    pass

try:
    from mcp_server_arxiv.logging_config import configure_logging
except ImportError:
    try:
        from .logging_config import configure_logging
    except ImportError:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.warning("Could not import logging_config module. Using basic logging.")

configure_logging() 
logger = logging.getLogger("arxiv-mcp-client") 

env_path = load_dotenv()
if env_path:
    logger.info(f"Loaded environment variables from: {env_path}")
else:
    logger.warning("No .env file found. Relying on system environment variables.")


async def main():
    """
    Main function demonstrating use of the ArXiv MCP server.
    Connects, fetches tools, runs agent example (optional), and direct tool call example.
    """
    try:
        logger.info("--- Starting ArXiv MCP Client Example ---")

        # --- LLM Setup (Optional - for Agent Example) ---
        llm_api_key = os.getenv('TOGETHER_API_KEY')
        model = None
        if not llm_api_key:
            logger.warning("LLM API Key (TOGETHER_API_KEY) not found. Agent example will be skipped.")
        else:
            try:
                # Using a smaller/faster model for testing if needed
                model = ChatTogether(model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", api_key=llm_api_key)
                logger.info(f"LLM Model initialized: {model}")
            except Exception as llm_err:
                logger.error(f"Failed to initialize LLM: {llm_err}", exc_info=True)
                logger.warning("Proceeding without LLM for agent example.")
                model = None

        # --- MCP Server Connection ---
        # Use environment variable for port, default to 8006 for ArXi
        arxiv_port = os.getenv('MCP_ARXIV_PORT', '8006')
        arxiv_host = os.getenv('MCP_ARXIV_HOST', 'host.docker.internal') 
        arxiv_server_url = f"http://{arxiv_host}:{arxiv_port}/sse"
        logger.info(f"Attempting to connect to MCP ArXiv server at {arxiv_server_url}...")

        # Use context manager for the client
        async with MultiServerMCPClient(
            {
                "arxiv_searcher": {
                    "url": arxiv_server_url,
                    "transport": "sse"
                }
                # Add other servers here if needed
            }
        ) as client:
            logger.info("Successfully connected to MCP server(s).")

            # --- List Available Tools ---
            logger.info("Fetching available tools...")
            tools: list[StructuredTool] = client.get_tools()

            if not tools:
                logger.error(f"No tools found from server(s). Checked URL: {arxiv_server_url}. Exiting.")
                return

            logger.info(f"Available tool names: {[tool.name for tool in tools]}")

            # Find the specific ArXiv tool
            arxiv_tool = next((t for t in tools if t.name == "arxiv_search"), None)

            if not arxiv_tool:
                logger.error("The required 'arxiv_search' tool was not found on the server. Exiting.")
                return

            logger.info(f"Found Tool: Name='{arxiv_tool.name}', Description='{arxiv_tool.description}'")
            logger.debug(f"Tool Args Schema: {arxiv_tool.args_schema}")


            # --- Example 1: Using a ReAct Agent (Optional) ---
            if model: # Check if LLM model was successfully initialized
                logger.info("\n--- Running ReAct Agent Example ---")
                try:
                    # Pass only the relevant tool(s) to the agent
                    agent_executor = create_react_agent(model, [arxiv_tool])
                    agent_prompt = "Find recent papers on traversable wormholes using the arXiv tool."
                    logger.info(f"Invoking agent with prompt: \"{agent_prompt}\"")

                    # Invoke the agent
                    agent_response = await agent_executor.ainvoke({"messages": [HumanMessage(content=agent_prompt)]})

                    logger.info("Agent finished processing.")
                    # The final response is usually in the last message
                    final_message = agent_response["messages"][-1]
                    logger.info(f"Agent Final Response Type: {type(final_message).__name__}")
                    logger.info(f"Agent Final Response Content (Preview):\n{final_message.content[:500]}...")
                    print("\n--- Agent Response (Formatted String) ---")
                    print(final_message.content)
                    print("-" * 40)

                except Exception as agent_err:
                    logger.error(f"Error invoking ReAct agent: {agent_err}", exc_info=True)
            else:
                logger.info("\n--- Skipping ReAct Agent Example (LLM not configured) ---")


            # --- Example 2: Directly Calling the Tool ---
            logger.info("\n--- Running Direct Tool Call Example ---")
            if arxiv_tool:
                # Example 1: Basic search
                search_query_1 = "Detecting exoplanets via microlensing"
                tool_input_1 = {
                    "query": search_query_1,
                    "max_results": 2, 
                    # "max_text_length": 1000 # Optionally limit text length
                }
                logger.info(f"Directly calling tool '{arxiv_tool.name}' with input: {tool_input_1}")
                try:
                    # Use .arun() which typically returns the formatted string result
                    result_str_1: str = await arxiv_tool.arun(tool_input_1)

                    logger.info("Direct call 1 successful.")
                    print("\n--- Direct Call Result 1 (Formatted String) ---")
                    print(result_str_1)
                    print("-" * 40)

                except Exception as tool_call_err:
                    logger.error(f"Error directly calling tool '{arxiv_tool.name}' (Call 1): {tool_call_err}", exc_info=True)

                # Example 2: More specific search
                await asyncio.sleep(1) # Small delay if needed
                search_query_2 = "Alcubierre drive negative energy requirements"
                tool_input_2 = {
                    "query": search_query_2,
                    "max_results": 3
                }
                logger.info(f"\nDirectly calling tool '{arxiv_tool.name}' with input: {tool_input_2}")
                try:
                    result_str_2: str = await arxiv_tool.arun(tool_input_2)
                    logger.info("Direct call 2 successful.")
                    print("\n--- Direct Call Result 2 (Formatted String) ---")
                    print(result_str_2)
                    print("-" * 40)
                except Exception as tool_call_err:
                    logger.error(f"Error directly calling tool '{arxiv_tool.name}' (Call 2): {tool_call_err}", exc_info=True)

            else:
                # This case should have been caught earlier
                logger.error("Could not find the 'arxiv_search' tool for direct call example.")


    # --- Error Handling for Connection ---
    except ConnectionRefusedError:
         logger.error(f"Connection refused. Is the MCP ArXiv server running and accessible at {arxiv_server_url}?")
         logger.error("Ensure the Docker container or local process is running and the port mapping is correct.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the client: {str(e)}", exc_info=True)


# --- Run Main Function ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client script interrupted by user.")
    logger.info("--- ArXiv MCP Client Example Finished ---")
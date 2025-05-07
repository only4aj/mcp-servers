import os
import asyncio
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_together import ChatTogether
from langchain_core.tools import StructuredTool
from langchain_core.messages import ToolMessage, HumanMessage

# Import the logging configuration directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from mcp_server_telegram.logging_config import configure_logging
except ImportError:
    # If that fails, try a direct import from the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)
    from logging_config import configure_logging

configure_logging()

logger = logging.getLogger(__name__)

load_dotenv()


async def main():
    try:
        logger.info("Starting the Telegram MCP client example")

        # --- LLM Setup  ---
        llm_api_key = os.getenv('TOGETHER_API_KEY') 
        if not llm_api_key:
             logger.warning("LLM API Key not found. Agent invocation will likely fail.")
             model = None # Set model to None if no key
        else:
            model = ChatTogether(model="deepseek-ai/DeepSeek-V3", api_key=llm_api_key)

        # Just log the Telegram configuration for information
        telegram_token = os.getenv('TELEGRAM_TOKEN')
        telegram_channel = os.getenv('TELEGRAM_CHANNEL')
        
        if not telegram_token or not telegram_channel:
            logger.warning("Telegram token or channel not found in environment variables.")
            logger.warning("Please make sure TELEGRAM_TOKEN and TELEGRAM_CHANNEL are set in your .env file.")
        else:
            logger.info(f"Using Telegram channel: {telegram_channel}")

        logger.info("Connecting to MCP Telegram server")
        telegram_server_url = f"http://localhost:{os.getenv('MCP_TELEGRAM_PORT', 8002)}/sse"

        async with MultiServerMCPClient(
            {
                "telegram_poster": { 
                    "url": telegram_server_url,
                    "transport": "sse"
                }
            }
        ) as client:

            # List available tools from all connected servers
            logger.info("Fetching available tools from MCP server(s)")
            tools: list[StructuredTool] = client.get_tools()

            if not tools:
                logger.error(f"No tools found from server at {telegram_server_url}. Exiting.")
                return

            logger.info(f"Available tools: {[tool.name for tool in tools]}")
            for tool in tools:
                logger.info(f"Tool Details: Name='{tool.name}', Description='{tool.description}', Args={tool.args_schema}")

            # # --- Example 1: Using a ReAct Agent ---
            if model: # Only run agent if LLM is configured
                logger.info("Creating ReAct agent with the Telegram tool")
                agent = create_react_agent(model, tools)

                # Ask the agent to perform a task that requires posting to Telegram
                agent_prompt = (
                    "Post the following important update to the team channel: "
                    "'Project Alpha deployment is scheduled for tomorrow at 10 AM UTC.' "
                    f"Use the Telegram token '{telegram_token}' and channel '{telegram_channel}' "
                    "for the configuration."
                )
                logger.info(f"Invoking agent with prompt: \"{agent_prompt}\"")

                agent_response = await agent.ainvoke({"messages": [HumanMessage(content=agent_prompt)]})

                logger.info("Agent finished processing.")
                # The final response from the agent (might be confirmation or the tool output)
                final_message = agent_response["messages"][-1]
                logger.info(f"Agent Final Response Type: {type(final_message)}")
                logger.info(f"Agent Final Response Content: {final_message.content}")
            else:
                 logger.info("Skipping ReAct agent example as LLM is not configured.")


            # --- Example 2: Directly Calling the Tool ---
            logger.info("\nDirectly calling the 'post_to_telegram' tool")
            telegram_tool = next((t for t in tools if t.name == "post_to_telegram"), None)

            if telegram_tool:
                message_to_post = "This is a direct message sent via the MCP client."
                tool_input = {
                    "message": message_to_post
                }

                logger.info(f"Calling tool '{telegram_tool.name}' with input: {tool_input}")
                try:
                    # Use .ainvoke for structured input/output if needed, or .arun for simpler cases
                    # result: ToolMessage = await telegram_tool.ainvoke(tool_input)
                    result_str: str = await telegram_tool.arun(tool_input) # arun often returns a string summary

                    logger.info(f"Direct call result: {result_str}")
                    # If using ainvoke: logger.info(f"Direct call result (ToolMessage): {result}")

                except Exception as tool_call_err:
                    logger.error(f"Error directly calling tool '{telegram_tool.name}': {tool_call_err}", exc_info=True)
            else:
                logger.warning("Could not find the 'post_to_telegram' tool for direct call example.")


    except ConnectionRefusedError:
         logger.error(f"Connection refused. Is the MCP Telegram server running at {telegram_server_url}?")
    except Exception as e:
        logger.error(f"An error occurred in the client: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
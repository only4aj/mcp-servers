import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Literal, Optional, List

from mcp.server import Server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field, ValidationError
from .twitter import TwitterClient, get_twitter_client

logger = logging.getLogger(__name__)


# Request Models
class CreateTweetRequest(BaseModel):
    text: str = Field(..., max_length=280)
    image_content: Optional[str] = Field(None, description="Base64 encoded image content")
    poll_options: Optional[List[str]] = Field(None, min_items=2, max_items=4)
    poll_duration: Optional[int] = Field(None, ge=5, le=10080)
    in_reply_to_tweet_id: Optional[str] = Field(None, description="tweet id of user to whom is replying")
    quote_tweet_idd : Optional[str] = Field(None,description="tweet id of a tweet, which is being quoted")

class RetweetTweetRequest(BaseModel):
    tweet_id: str

class GetTweetsRequest(BaseModel):
    user_id: str
    max_results: int = Field(10, ge=1, le=100)


class FollowUserRequest(BaseModel):
    user_id: str


# Tool Names
class ToolNames(StrEnum):
    CREATE_TWEET = "create_tweet"
    GET_USER_TWEETS = "get_user_tweets"
    FOLLOW_USER = "follow_user"
    RETWEET_TWEET = "retweet_tweet"


@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[dict]:
    context = {}
    try:
        context["twitter_client"] = get_twitter_client()
        yield context
    except Exception as e:
        logger.error(f"Lifespan error: {str(e)}", exc_info=True)
        raise


server = Server("twitter-server", lifespan=server_lifespan)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name=ToolNames.CREATE_TWEET,
            description="""
        Create a new tweet with optional media, polls, replies or quotes.

        Args:
            text (str): The text content of the tweet. Will be truncated to the
                configured maximum tweet length if necessary.
            image_content_str (str, optional): A Base64-encoded string of image data
                to attach as media. Requires media uploads to be enabled in config.
            poll_options (list[str], optional): A list of 2 to N options (where N is
                config.poll_max_options) to include in a poll.
            poll_duration (int, optional): Duration of the poll in minutes (must be
                between 5 and config.poll_max_duration).
            in_reply_to_tweet_id (str, optional): The ID of an existing tweet to reply to.
                Note: Your `text` must include “@username” of the tweet’s author.
            quote_tweet_id (str, optional): The ID of an existing tweet to quote. The
                quoted tweet will appear inline, with your `text` shown above it.

        Returns:
            str: A success message ("tweet posted") if the tweet was created.

        Raises:
            ValueError: If poll_options length is out of bounds or poll_duration is invalid.
            Exception: Propagates any error from the Twitter API client or media upload.
        """,
            inputSchema=CreateTweetRequest.model_json_schema(),
        ),
        Tool(
            name=ToolNames.GET_USER_TWEETS,
            description= """
        Retrieve recent tweets posted by a specified user.

        Args:
            user_id (str): The ID of the user whose tweets to fetch.
            max_results (int, optional): The maximum number of tweets to return.
                Must be between 1 and 100. Defaults to 10.

        Returns:
            tweepy.Response or str:
                - On success: A Tweepy Response object containing a list of tweets.
                  Each tweet includes at least the fields "id", "text", and "created_at".
                - On failure: An error message string.

        Raises:
            Exception: Propagates any exception raised by the Twitter API client,
                such as invalid user ID, suspended account, or rate limit errors.
        """,
            inputSchema=GetTweetsRequest.model_json_schema(),
        ),
        Tool(
            name=ToolNames.FOLLOW_USER,
            description="""
        Follow another Twitter user by their user ID.

        Args:
            user_id (str): The ID of the user to follow.

        Returns:
            str: Success message confirming the follow, e.g., 
                "Successfully followed user: <user_id>".

        Raises:
            Exception: Propagates any exception raised by the Twitter API client,
                such as attempting to follow a protected account, already following,
                or rate limit errors.
        """,
            inputSchema=FollowUserRequest.model_json_schema(),
        ),
        Tool(
            name=ToolNames.RETWEET_TWEET,
            description="""
        Retweet an existing tweet on behalf of the authenticated user.

        Args:
            tweet_id (str): The ID of the tweet to retweet.

        Returns:
            str: Success message confirming the retweet, e.g., 
                "Successfully retweeted post <tweet_id>".

        Raises:
            Exception: Propagates any exception raised by the Twitter API client,
                such as invalid tweet ID, already retweeted, or rate limit errors.
        """,
            inputSchema=FollowUserRequest.model_json_schema(),
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    client: TwitterClient = server.request_context.lifespan_context.get("twitter_client")

    try:
        match name:
            case ToolNames.CREATE_TWEET:
                request = CreateTweetRequest(**arguments)
                response = client.create_tweet(
                    text=request.text,
                    image_content_str=request.image_content,
                    poll_options=request.poll_options,
                    poll_duration=request.poll_duration
                )
                return [TextContent(text=f"Tweet created: {response}")]

            case ToolNames.GET_USER_TWEETS:
                request = GetTweetsRequest(**arguments)
                response = client.get_user_tweets(
                    user_id=request.user_id,
                    max_results=request.max_results
                )
                tweets = "\n".join([t.text for t in response.data])
                return [TextContent(text=f"Recent tweets:\n{tweets}")]

            case ToolNames.FOLLOW_USER:
                request = FollowUserRequest(**arguments)
                response = client.follow_user(request.user_id)
                return [TextContent(text=f"Following user: {request.user_id}")]

            case ToolNames.RETWEET_TWEET:
                request = RetweetTweetRequest(**arguments)
                response = client.retweet_tweet(request.tweet_id)
                return [TextContent(text=f"Retweeting tweet: {request.tweet_id}")]

            case _:
                return [TextContent(text=f"Unknown tool: {name}")]

    except ValidationError as ve:
        return [TextContent(text=f"Validation error: {str(ve)}")]
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return [TextContent(text=f"Server error: {str(e)}")]
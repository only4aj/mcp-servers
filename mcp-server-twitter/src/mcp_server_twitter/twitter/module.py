import logging
import base64
import io
from functools import lru_cache
import tweepy
from tweepy import API, Client
from dotenv import load_dotenv
logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self, config):
        """
        Initialize Twitter API client with provided configuration.
        """
        self.config = config
        self.client = Client(
            consumer_key=config.API_KEY,
            consumer_secret=config.API_SECRET_KEY,
            access_token=config.ACCESS_TOKEN,
            access_token_secret=config.ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
        auth = tweepy.OAuthHandler(config.API_KEY, config.API_SECRET_KEY)
        auth.set_access_token( config.ACCESS_TOKEN , config.ACCESS_TOKEN_SECRET)
        self.api = API(auth, wait_on_rate_limit=True)

    def _upload_media(self, image_content_str: str):
        """
        Internal method to upload media to Twitter.
        """
        image_content = base64.b64decode(image_content_str)
        image_file = io.BytesIO(image_content)
        image_file.name = "image.png"
        # Let Tweepy's errors propagate
        return self.api.media_upload(filename=image_file.name, file=image_file)

    def create_tweet(
            self,
            text: str,
            image_content_str: str = None,
            poll_options: list[str] = None,
            poll_duration: int = None,
            in_reply_to_tweet_id: str = None,
            quote_tweet_id: str = None
    ):
        """
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
        """
        try:
            media_ids = []
            if image_content_str and self.config.media_upload_enabled:
                media = self._upload_media(image_content_str)
                media_ids.append(media.media_id)

            poll_params = {}
            if poll_options:
                if len(poll_options) < 2 or len(poll_options) > self.config.poll_max_options:
                    raise ValueError(f"Poll must have 2-{self.config.poll_max_options} options")
                if not poll_duration or not 5 <= poll_duration <= self.config.poll_max_duration:
                    raise ValueError(f"Poll duration must be 5-{self.config.poll_max_duration} minutes")

                poll_params = {
                    "poll_options": poll_options,
                    "poll_duration_minutes": poll_duration
                }
            self.client.create_tweet(
                text=text[:self.config.max_tweet_length],
                media_ids=media_ids or None,
                in_reply_to_tweet_id=in_reply_to_tweet_id,
                quote_tweet_id=quote_tweet_id,
                **poll_params)
            return "tweet posted"

        except Exception as e:
            return str(e)

    def retweet_tweet(self, tweet_id: str):
        """
        Retweet an existing tweet on behalf of the authenticated user.

        Args:
            tweet_id (str): The ID of the tweet to retweet.

        Returns:
            str: Success message confirming the retweet, e.g.,
                "Successfully retweeted post <tweet_id>".

        Raises:
            Exception: Propagates any exception raised by the Twitter API client,
                such as invalid tweet ID, already retweeted, or rate limit errors.
        """
        try:
            self.client.retweet(tweet_id=tweet_id)
            return f"Successfully retweet post {tweet_id}"
        except Exception as e:
            return str(e)


    def get_user_tweets(self, user_id: str, max_results: int = 10):
        """
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
        """
        try:
            tweets = self.client.get_users_tweets(
            id=user_id,
            max_results=max_results,
            tweet_fields=["id", "text", "created_at"])
            return tweets
        except Exception as e:
            return str(e)


    def follow_user(self, user_id: str):
        """
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
        """
        try:
            self.client.follow_user(user_id=user_id)
            return f"Successfully followed user: {user_id}"
        except Exception as e:
            return str(e)


@lru_cache(maxsize=1)
def get_twitter_client() -> TwitterClient:
    logger.info("Creating TwitterClient instance...")

    config = __import__('mcp_server_twitter.twitter.config', fromlist=['TwitterConfig']).TwitterConfig()
    print(config)
    client = TwitterClient(config=config)
    user  = (client.client.get_me())
    print(f"Authenticated as: {user.data['username']}")
    return client

import logging
import requests
from typing import Optional

from .config import TelegramConfig, TelegramApiError, TelegramClientError

logger = logging.getLogger(__name__) # Use module-specific logger

# Telegram's max message length is 4096 chars
MAX_MESSAGE_LENGTH = 4000 # Keep a buffer

def send_msg_to_telegram(config: TelegramConfig, text: str) -> bool:
    """Send message text to the configured Telegram channel.

    Args:
        config: The Telegram configuration object.
        text: The message content to send.

    Returns:
        True if the message was sent successfully, False otherwise.

    Raises:
        TelegramClientError: If configuration is invalid.
    """
    logger.info(f"Attempting to send message to Telegram channel {config.channel}")

    if not config.token:
        raise TelegramClientError("TELEGRAM_TOKEN is missing in configuration")
    if not config.channel:
        raise TelegramClientError("TELEGRAM_CHANNEL is missing in configuration")

    # Ensure text is not too long
    if len(text) > MAX_MESSAGE_LENGTH:
        logger.warning(
            f"Message exceeds Telegram's maximum length. Truncating from {len(text)} to {MAX_MESSAGE_LENGTH} chars."
        )
        text = text[:MAX_MESSAGE_LENGTH] + "... [message truncated]"

    url = f"https://api.telegram.org/bot{config.token}/sendMessage"
    payload = {
        "chat_id": config.channel,
        "text": text,
        "parse_mode": "HTML"  # Default to HTML
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10) # Added timeout

        # Check for common 400 error and retry without parse_mode
        if response.status_code == 400:
            error_json = response.json()
            error_desc = error_json.get('description', '').lower()
            # Specific check if the error is likely related to parsing
            if 'parse error' in error_desc or 'can\'t parse entities' in error_desc:
                logger.warning("Got 400 error likely due to HTML parse mode, retrying without it.")
                payload["parse_mode"] = "" # Remove parse mode
                response = requests.post(url, json=payload, headers=headers, timeout=10)
            else:
                 # Log the original 400 error if not parse related
                 logger.error(f"Failed to send message (400 Bad Request): {error_desc}")
                 return False # Return False for non-retryable 400 errors

        response.raise_for_status() # Raise HTTPError for other non-2xx status codes after retry attempt

        logger.info(f"Message sent successfully to channel {config.channel}")
        return True

    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code
        details = {}
        try:
            details = http_err.response.json()
        except requests.exceptions.JSONDecodeError:
            details = {"raw_response": http_err.response.text}
        logger.error(f"HTTP error sending message to Telegram: {http_err}", exc_info=True)
        # Optionally raise a more specific error, but for now return False
        # raise TelegramApiError(str(http_err), status_code=status_code, details=details) from http_err
        return False
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error sending message to Telegram: {conn_err}", exc_info=True)
        return False
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout error sending message to Telegram: {timeout_err}", exc_info=True)
        return False
    except requests.exceptions.RequestException as req_err:
        logger.error(f"General request error sending message to Telegram: {req_err}", exc_info=True)
        return False
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred sending message to Telegram: {e}", exc_info=True)
        return False
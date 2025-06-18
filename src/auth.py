import os
import requests
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

def get_headers():
    load_dotenv()
    return {
        'x-api-key': 'shelobs_hevy_web',
        'auth-token': os.getenv('AUTH_TOKEN'),
        'Hevy-Platform': 'web',
        'Accept': 'application/json, text/plain, */*'
    }

from src.webhook import send_discord_notification

def get_current_username(config) -> str | None:
    # trying to grab our own username from the api
    url = f"{config['api']['base_url']}/user/account"
    headers = get_headers()

    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()
        username = data.get('username')
        if username:
            logger.info(f"fetched username: {username}")
            return username
        else:
            logger.error("username not found in api response.")
            send_discord_notification("hevy bot could not fetch username from api.")
            return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"http error fetching username: {e}")
        send_discord_notification(f"hevy bot http error fetching username: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"error fetching username: {e}")
        send_discord_notification(f"hevy bot error fetching username: {str(e)}")
        return None


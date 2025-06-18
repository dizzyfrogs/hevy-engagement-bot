import os
import requests
import logging 

logger = logging.getLogger(__name__)

def send_discord_notification(message):
    # sending a message to discord for updates
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        logger.warning("discord webhook url not configured. can't send notifications.") 
        return False
        
    payload = {'content': message}
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"failed to send discord alert: {e}")
        return False


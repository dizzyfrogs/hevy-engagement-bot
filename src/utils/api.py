import requests
import os
from typing import List, Dict, Optional
import time
import logging 

logger = logging.getLogger(__name__) # logger for api stuff

from src.auth import get_headers
from src.utils import delay, handle_rate_limit 
from src.webhook import send_discord_notification

class DailyFollowLimitReached(Exception):
    # custom error for when we hit the daily follow limit, happens sometimes
    pass

def get_following(username: str, base_url: str, config: dict) -> List[str]: 
    # getting all the people we're following
    url = f"{base_url}/following/{username}"
    try:
        res = requests.get(url, headers=get_headers())
        if res.status_code == 429: # oh no, rate limited!
            handle_rate_limit(config)
            return []
        res.raise_for_status()
        following = res.json()
        return [user['username'] for user in following]
    except Exception as e:
        logger.error(f"error fetching following list: {e}")
        return []

def get_user_workouts(username: str, base_url: str, config: dict, limit: int = 3, offset: int = 0) -> List[dict]: 
    # getting a user's recent workouts
    url = f"{base_url}/user_workouts_paged"
    params = {
        "username": username,
        "limit": limit,
        "offset": offset
    }
    try:
        res = requests.get(url, headers=get_headers(), params=params)
        if res.status_code == 429: # rate limit
            handle_rate_limit(config)
            return []
        res.raise_for_status()
        data = res.json()
        return data.get('workouts', [])
    except Exception as e:
        logger.error(f"error fetching workouts for {username}: {e}")
        return []

def follow_user(username: str, base_url: str, following_cache: Dict[str, dict], config: dict) -> bool: 
    # trying to follow someone
    url = f"{base_url}/follow"
    payload = {"username": username}
    try:
        res = requests.post(url, headers=get_headers(), json=payload)
        if res.status_code == 429: # rate limit
            handle_rate_limit(config)
            return False
        if res.status_code == 400:
            logger.warning(f"failed to follow {username} (400 error).")
            return False
        if res.status_code == 403: # probably hit the daily limit
            error_data = res.json()
            if error_data.get('error') == 'daily-limit-reached':
                logger.warning("daily follow limit reached for today.")
                send_discord_notification("daily follow limit reached. bot is taking a break from following.")
                raise DailyFollowLimitReached("daily follow limit reached")
        res.raise_for_status()
        
        # update our cache so we know we followed them
        following_cache[username] = {
            'follow_time': int(time.time())
        }
        
        return True
    except DailyFollowLimitReached:
        raise # important to re-raise this
    except Exception as e:
        logger.error(f"failed to follow {username}: {e}")
        return False

def unfollow_user(username: str, base_url: str, config: dict) -> bool: 
    # trying to unfollow someone
    url = f"{base_url}/unfollow"
    payload = {"username": username}
    try:
        res = requests.post(url, headers=get_headers(), json=payload)
        if res.status_code == 429: # rate limit
            handle_rate_limit(config)
            return False
        if res.status_code == 400:
            logger.warning(f"failed to unfollow {username}. bad request.")
            return False
        res.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"failed to unfollow {username}: {e}")
        return False

def get_discovery_feed(base_url: str, config: dict, last_index: Optional[str] = None) -> List[dict]: 
    # getting the discovery feed, lots of posts here
    url = f"{base_url}/discover_feed_workouts_paged"
    if last_index is not None:
        url = f"{url}/{last_index}" # for pagination, so we see new stuff
        
    try:
        res = requests.get(url, headers=get_headers())
        
        if res.status_code == 429: # rate limit
            handle_rate_limit(config)
            return []
            
        if res.status_code != 200:
            logger.warning(f"failed to fetch discovery feed. status code: {res.status_code}")
            return []
            
        res.raise_for_status()
        
        data = res.json()
        return data.get('workouts', [])
        
    except Exception as e:
        logger.error(f"error fetching discovery feed: {e}")
        return []

def get_workout_likes(workout_id: str, base_url: str, config: dict) -> List[str]: 
    # getting who liked a workout, good source for new follows
    url = f"{base_url}/workout_likes/{workout_id}"
    try:
        res = requests.get(url, headers=get_headers())
        if res.status_code == 429: # rate limit
            handle_rate_limit(config)
            return []
        if res.status_code == 200:
            return [u['username'] for u in res.json()]
        logger.warning(f"failed to fetch likes for workout {workout_id}. status code: {res.status_code}")
        return []
    except Exception as e:
        logger.error(f"error fetching likes for workout {workout_id}: {e}")
        return []

def get_last_workout_id_for_user(username: str, base_url: str, config: dict) -> Optional[str]: 
    # getting the id of a user's latest workout
    url = f"{base_url}/user_workouts_paged"
    params = {
        "username": username,
        "limit": 1
    }
    try:
        res = requests.get(url, headers=get_headers(), params=params)
        if res.status_code == 429: # rate limit
            handle_rate_limit(config)
            return None
        if res.status_code != 200:
            logger.warning(f"failed to get last workout id for {username}. status code: {res.status_code}")
            return None
        data = res.json()
        workouts = data.get("workouts", [])
        return workouts[0]['id'] if workouts else None
    except Exception as e:
        logger.error(f"error fetching last workout id for {username}: {e}")
        return None

def like_workout(workout_id: str, base_url: str, config: dict) -> bool: 
    # trying to like a workout, engagement!
    url = f"{base_url}/workout/like/{workout_id}"
    try:
        res = requests.post(url, headers=get_headers())
        if res.status_code == 429: # another rate limit, havent encountered yet so not sure if they're real lol
            handle_rate_limit(config)
            return False
        res.raise_for_status()
        return res.status_code == 200
    except Exception as e:
        logger.error(f"failed to like workout {workout_id}: {e}")
        return False

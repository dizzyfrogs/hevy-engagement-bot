import time
import random
from datetime import datetime, timedelta, timezone
import os
import yaml
import logging

logger = logging.getLogger(__name__)

def interruptible_sleep(duration, check_interval=0.1):
    # sleep for a bit, but you can interrupt it with ctrl+c if you're impatient
    start_time = time.time()
    while time.time() - start_time < duration:
        try:
            time.sleep(min(check_interval, duration - (time.time() - start_time)))
        except KeyboardInterrupt:
            logger.info("sleep interrupted by user (ctrl+c).")
            raise # gotta let the interruption go through

def delay(config):
    # just a random delay to make us seem less like a bot, keeps us from getting banned
    delay_config = config['api']['request_delay']
    sleep_duration = random.uniform(delay_config['min'], delay_config['max'])
    interruptible_sleep(sleep_duration)

def handle_rate_limit(config):
    # when the api tells us to chill out, we wait a bit longer
    logger.warning("rate limited. waiting for a bit.")
    sleep_duration = config['api']['rate_limit_delay']
    interruptible_sleep(sleep_duration)

def is_user_inactive(last_post_date: str, threshold_days: int) -> bool:
    # checks if a user hasn't posted in a while, don't want to follow ghosts
    if not last_post_date:
        return True
        
    last_post = datetime.fromisoformat(last_post_date.replace('Z', '+00:00'))
    threshold = datetime.now() - timedelta(days=threshold_days)
    return last_post < threshold

def should_unfollow_user(user: dict, whitelist: set, unfollowed: set, 
                        inactive_threshold: int, follow_back_threshold: int) -> bool:
    # decides if we should unfollow someone based on a few rules
    username = user.get('username')
    
    # don't unfollow if they're on our special list or we already unfollowed them
    if username in whitelist or username in unfollowed:
        return False
        
    # check if they're inactive
    if is_user_inactive(user.get('last_post_date'), inactive_threshold):
        return True
        
    # check if they haven't followed back within the set time
    follow_date = user.get('follow_date')
    if follow_date:
        follow_date = datetime.fromisoformat(follow_date.replace('Z', '+00:00'))
        if datetime.now() - follow_date > timedelta(days=follow_back_threshold):
            return True
            
    return False # if none of the above, keep following for now

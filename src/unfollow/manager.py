import os
from typing import List, Set, Dict
import yaml
import time
import logging

logger = logging.getLogger(__name__)

from src.auth import get_headers, get_current_username
from src.persistence import load_unfollowed, load_followers_cache, save_followers_cache, load_whitelist, save_unfollowed
from src.utils import delay, handle_rate_limit
from src.utils.api import get_following, get_user_workouts, unfollow_user
from src.webhook import send_discord_notification

class UnfollowManager:
    def __init__(self, config):
        self.config = config
        self.headers = get_headers()
        self.base_url = self.config['api']['base_url']
        self.following_cache = load_followers_cache()
            
    def run(self):
        # starting the unfollow process, time to clean up
        logger.info("starting unfollow process...")
        
        unfollowed_inactive = []
        unfollowed_no_followback = []
        unfollowed_count = 0

        try:
            inactive_threshold = self.config.get('unfollow', {}).get('inactive_threshold', 21)
            follow_back_threshold = self.config.get('unfollow', {}).get('follow_back_threshold', 7)
            logger.info(f"unfollow settings: inactive_threshold={inactive_threshold} days, follow_back_threshold={follow_back_threshold} days")
            
            unfollowed = load_unfollowed()
            following_cache = load_followers_cache()
            whitelist = load_whitelist()
            
            current_username = get_current_username(self.config)
            if not current_username:
                logger.error("could not retrieve current username. aborting unfollow process.")
                return
                
            # grab who we're currently following
            following = get_following(current_username, self.base_url, self.config)
            logger.info(f"found {len(following)} users we're following.")
            
            for username in following:
                daily_unfollow_cap = self.config['unfollow'].get('daily_unfollow_cap', 100)
                if unfollowed_count >= daily_unfollow_cap:
                    logger.info("daily unfollow cap reached. stopping.")
                    break

                if username in unfollowed or username in whitelist:
                    continue # skip if already unfollowed or whitelisted
                    
                if username not in following_cache:
                    continue # only unfollow people the bot followed
                    
                # get their recent workouts to check activity
                workouts = get_user_workouts(username, self.base_url, self.config)
                if not workouts:
                    continue
                    
                last_workout = workouts[0]
                last_workout_time = last_workout.get('end_time', 0)
                current_time = int(time.time())
                days_since_workout = (current_time - last_workout_time) / (24 * 60 * 60)
                
                follow_time = following_cache[username].get('follow_time')
                if follow_time is None:
                    continue
                    
                days_since_follow = (current_time - follow_time) / (24 * 60 * 60)
                
                if days_since_workout > inactive_threshold:
                    logger.info(f"unfollowing {username} (inactive for {int(days_since_workout)} days).")
                    if unfollow_user(username, self.base_url, self.config):
                        unfollowed.add(username)
                        unfollowed_count += 1
                        unfollowed_inactive.append(f"{username} (inactive for {int(days_since_workout)}+ days)")
                        delay(self.config)
                elif days_since_follow > follow_back_threshold:
                    logger.info(f"unfollowing {username} (didn't follow back after {int(days_since_follow)} days).")
                    if unfollow_user(username, self.base_url, self.config):
                        unfollowed.add(username)
                        unfollowed_count += 1
                        unfollowed_no_followback.append(f"{username} (hasn't followed back in {int(days_since_follow)}+ days)")
                        delay(self.config)
        
        except KeyboardInterrupt:
            logger.info("unfollow process interrupted by user. sending summary...")
        except Exception as e:
            logger.error(f"an error occurred during the unfollow process: {e}")
            send_discord_notification(f"unfollow process encountered an error: {e}")
        finally:
            save_unfollowed(unfollowed)
                
            if unfollowed_count > 0:
                message = f"unfollowed {unfollowed_count} users:\n"
                if unfollowed_no_followback:
                    message += "users who didn't follow back:\n"
                    for user_info in unfollowed_no_followback:
                        message += f"- {user_info}\n"
                if unfollowed_inactive:
                    message += "users inactive:\n"
                    for user_info in unfollowed_inactive:
                        message += f"- {user_info}\n"
                send_discord_notification(message.strip())
            else:
                send_discord_notification(f"unfollowed {unfollowed_count} users.")
                
            logger.info("unfollow process completed.")

import os
from typing import Set
import yaml
import time
import logging

logger = logging.getLogger(__name__)

from src.auth import get_headers
from src.utils import delay, handle_rate_limit
from src.utils.api import get_discovery_feed, get_workout_likes, get_last_workout_id_for_user, like_workout
from src.webhook import send_discord_notification

class LikeManager:
    def __init__(self, config):
        self.config = config
        self.headers = get_headers()
        self.base_url = self.config['api']['base_url']
        
    def run(self):
        # starting the like process, spread some love
        logger.info("starting like process...")
        
        index = None
        liked_users = set()
        
        like_cap = self.config.get('like', {}).get('like_cap', 50)
        logger.info(f"like settings: like_cap={like_cap}")

        try:
            while len(liked_users) < like_cap:
                # get new workouts to check
                workouts = get_discovery_feed(self.base_url, self.config, index)
                if not workouts or len(workouts) < 1:
                    logger.info("no more workouts to fetch for liking.")
                    break
                
                for workout in workouts:
                    workout_id = workout.get("id")
                    if not workout_id:
                        continue
                    
                    # check comments first
                    for comment_entry in workout.get("comments", []):
                        username = comment_entry.get("username")
                        if not username:
                            continue

                        username = username.lower()
                        if username in liked_users:
                            continue
                        
                        # get their last workout id to like it
                        last_id = get_last_workout_id_for_user(username, self.base_url, self.config)
                        if not last_id:
                            continue
                        
                        if like_workout(last_id, self.base_url, self.config):
                            logger.info(f"liked @{username}'s workout ({last_id}) from comments.")
                            liked_users.add(username)
                            delay(self.config)
                        
                        if len(liked_users) >= like_cap:
                            break
                    
                    if len(liked_users) >= like_cap:
                        break

                    # then process likes on the workout itself
                    workout_likers = get_workout_likes(workout_id, self.base_url, self.config)
                    for liker_username in workout_likers:
                        username = liker_username.lower()
                        if username in liked_users:
                            continue
                            
                        last_id = get_last_workout_id_for_user(username, self.base_url, self.config)
                        if not last_id:
                            continue
                            
                        if like_workout(last_id, self.base_url, self.config):
                            logger.info(f"liked @{username}'s workout ({last_id}) from workout likes.")
                            liked_users.add(username)
                            delay(self.config)

                        if len(liked_users) >= like_cap:
                            break

                    if len(liked_users) >= like_cap:
                        break
                
                # get the index for the next batch
                last_index = workouts[-1].get('index')
                if not last_index:
                    break
                    
                delay(self.config)
        except KeyboardInterrupt:
            logger.info("like process interrupted by user. sending summary...")
        except Exception as e:
            logger.error(f"an error occurred during the liking process: {e}")
            send_discord_notification(f"like process encountered an error: {e}")
        finally:
            if len(liked_users) > 0:
                message = f"liked {len(liked_users)} posts."
                send_discord_notification(message)
            else:
                send_discord_notification("like process completed. no new posts liked.")
                
            logger.info("like process completed.")

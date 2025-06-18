import os
from typing import List, Set, Dict
import yaml
import time
import logging

logger = logging.getLogger(__name__)

from src.auth import get_headers
from src.persistence import load_unfollowed, load_followers_cache, save_followers_cache
from src.utils import delay, handle_rate_limit
from src.utils.api import get_discovery_feed, get_user_workouts, follow_user, DailyFollowLimitReached
from src.webhook import send_discord_notification

class FollowManager:
    def __init__(self, config):
        self.config = config
        self.headers = get_headers()
        self.base_url = self.config['api']['base_url']
        self.following_cache = load_followers_cache()
            
    def process_workout(self, workout: dict, unfollowed: Set[str], 
                       following_cache: Dict[str, dict]) -> List[str]:
        # checking a workout for potential people to follow
        potential_follows = []
        
        # look at who liked the workout
        for like in workout.get('likes', []):
            user = like.get('user')
            if user and self._should_follow_user(user, unfollowed, following_cache):
                potential_follows.append((user['username'], self.config['follow']['like_priority']))
                
        # look at who commented on the workout
        for comment in workout.get('comments', []):
            user = comment.get('user')
            if user and self._should_follow_user(user, unfollowed, following_cache):
                potential_follows.append((user['username'], self.config['follow']['comment_priority']))
                
        return potential_follows
        
    def _should_follow_user(self, user: dict, unfollowed: Set[str], 
                          following_cache: Dict[str, dict]) -> bool:
        # deciding if we should actually follow this person
        username = user.get('username')
        
        # skip if already unfollowed or already following
        if username in unfollowed or username in following_cache:
            return False
            
        # check their recent workouts to see if they're active
        workouts = get_user_workouts(username, self.base_url, self.config)
        if not workouts:
            return False
            
        last_workout = workouts[0]
        last_workout_time = last_workout.get('end_time', 0)
        current_time = int(time.time())
        
        # if their last workout was super old, probably not worth following
        if current_time - last_workout_time > 30 * 24 * 60 * 60:
            return False
            
        delay(self.config)
        return True
        
    def run(self):
        # main function for following new people
        logger.info("starting follow process...")
        
        unfollowed = load_unfollowed()
        following_cache = load_followers_cache()
        
        followed_users_list = []
        
        last_index = None
        followed_count = 0
        target_count = self.config['follow']['target_count']

        daily_limit_hit_and_notified = False
        
        try:
            while followed_count < target_count:
                # get the next batch of workouts
                workouts = get_discovery_feed(self.base_url, self.config, last_index)
                if not workouts:
                    logger.info("no more workouts to fetch.")
                    break
                    
                for workout in workouts:
                    # process comments first
                    for comment in workout.get('comments', []):
                        username = comment.get('username')
                        if username and self._should_follow_user(comment, unfollowed, following_cache):
                            try:
                                if follow_user(username, self.base_url, following_cache, self.config):
                                    followed_count += 1
                                    followed_users_list.append(username)
                                    logger.info(f"followed {username} from comments ({followed_count}/{target_count}).")
                                    if followed_count >= target_count:
                                        break
                                    delay(self.config)
                                else:
                                    logger.warning(f"failed to follow {username}.")
                                    break
                            except DailyFollowLimitReached:
                                raise
                    
                    if followed_count >= target_count:
                        break
                        
                    # then process likes
                    for like in workout.get('likes', []):
                        username = like.get('username')
                        if username and self._should_follow_user(like, unfollowed, following_cache):
                            try:
                                if follow_user(username, self.base_url, following_cache, self.config):
                                    followed_count += 1
                                    followed_users_list.append(username)
                                    logger.info(f"followed {username} from likes ({followed_count}/{target_count}).")
                                    if followed_count >= target_count:
                                        break
                                    delay(self.config)
                                else:
                                    logger.warning(f"failed to follow {username}.")
                                    break
                            except DailyFollowLimitReached:
                                raise
                    
                    if followed_count >= target_count:
                        break
                
                # get the index for pagination
                last_index = workouts[-1].get('index')
                if not last_index:
                    break
                    
                delay(self.config)
        except DailyFollowLimitReached:
            logger.warning("stopping follow process due to daily limit reached.")
            send_discord_notification("daily follow limit reached!")
            daily_limit_hit_and_notified = True
            return
        except KeyboardInterrupt:
            logger.info("follow process interrupted by user. sending summary...")
        except Exception as e:
            logger.error(f"an error occurred during the follow process: {e}")
            send_discord_notification(f"follow process encountered an error: {e}")
        finally:
            save_followers_cache(following_cache)
            
            if followed_count > 0:
                message = f"followed {followed_count} new users:\n"
                for user in followed_users_list:
                    message += f"- {user}\n"
                send_discord_notification(message.strip())
            elif not daily_limit_hit_and_notified:
                send_discord_notification("follow process completed. no new users followed.")
                
            logger.info("follow process completed.")

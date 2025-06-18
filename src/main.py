import os
import argparse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import yaml
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# quiet down apscheduler a bit, it's chatty
logging.getLogger('apscheduler').setLevel(logging.WARNING)

from .auth import get_headers, get_current_username
from .follow.manager import FollowManager
from .unfollow.manager import UnfollowManager
from .like.manager import LikeManager
from .webhook import send_discord_notification

def load_config_central():
    config_path = 'config/config.yaml'
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"error: config file not found at {config_path}")
        exit(1)
    except yaml.YAMLError as e:
        logger.error(f"error parsing config file: {e}")
        exit(1)


def setup_scheduler(config):
    # setting up the schedule
    scheduler = BackgroundScheduler()
    
    scheduler.add_job(
        lambda: FollowManager(config).run(),
        CronTrigger.from_crontab(config['scheduler']['follow_schedule']),
        id='follow'
    )
    
    scheduler.add_job(
        lambda: UnfollowManager(config).run(),
        CronTrigger.from_crontab(config['scheduler']['unfollow_schedule']),
        id='unfollow'
    )

    scheduler.add_job(
        lambda: LikeManager(config).run(),
        CronTrigger.from_crontab(config['scheduler']['like_schedule']),
        id='like'
    )
    
    return scheduler

def main():
    parser = argparse.ArgumentParser(description='hevy follower manager')
    parser.add_argument('--follow', action='store_true', help='run follow process')
    parser.add_argument('--unfollow', action='store_true', help='run unfollow process')
    parser.add_argument('--like', action='store_true', help='run like process')
    parser.add_argument('--auto', action='store_true', help='run in automatic mode with scheduler')
    
    args = parser.parse_args()
    
    logger.info("loading environment variables...")
    load_dotenv()
    
    config = load_config_central()

    if args.follow:
        logger.info("running follow process...")
        FollowManager(config).run()
        return
        
    if args.unfollow:
        logger.info("running unfollow process...")
        UnfollowManager(config).run()
        return
    
    if args.like:
        logger.info("running like process...")
        LikeManager(config).run()
        return
        
    if args.auto:
        logger.info("starting automatic mode...")
        logger.info("scheduler will run the following jobs:")
        
        logger.info(f"  - follow process: {config['scheduler']['follow_schedule']}")
        logger.info(f"  - unfollow process: {config['scheduler']['unfollow_schedule']}")
        logger.info(f"  - like process: {config['scheduler']['like_schedule']}")
        
        scheduler = setup_scheduler(config)
        scheduler.start()
        logger.info("scheduler started successfully!")
        
        try:
            while True:
                pass # let the scheduler do its thing
        except (KeyboardInterrupt, SystemExit):
            logger.info("shutting down scheduler...")
            scheduler.shutdown()
            logger.info("scheduler shut down successfully!")
    else:
        logger.warning("no mode specified. use --help for available options.")

if __name__ == '__main__':
    main()


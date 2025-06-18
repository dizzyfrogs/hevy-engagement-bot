import os
import json
from datetime import datetime
from typing import Set, Dict, Any

def load_json_file(filepath: str, default: Any = None) -> Any:
    # trying to load some json data from a file
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

def save_json_file(filepath: str, data: Any):
    # saving some data to a json file
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def load_whitelist() -> Set[str]:
    # loading our special list of users we don't want to unfollow
    return set(load_json_file('data/whitelist.json', []))

def load_unfollowed() -> Set[str]:
    # loading the list of people we've already unfollowed
    return set(load_json_file('data/unfollowed.json', []))

def load_followers_cache() -> Dict[str, dict]:
    # grabbing our cache of who we're following
    return load_json_file('data/followed_cache.json', {})

def save_unfollowed(users: Set[str]):
    # saving the list of unfollowed users
    save_json_file('data/unfollowed.json', list(users))

def save_followers_cache(cache: Dict[str, dict]):
    # saving our updated following cache
    save_json_file('data/followed_cache.json', cache)

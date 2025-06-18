# Hevy Engagement Bot

A Python bot designed to enhance user engagement on the Hevy fitness tracking application, ultimately aiming to increase follower count for the bot's user. It intelligently interacts with active users and automates the management of your following list.

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Results](#proven-results)
- [Setup](#setup)
- [Usage](#usage)
- [Requirements](#requirements)

## Features 

**Follow Management**
- Automatically identifies and follows users who actively engage with workouts (commenting or liking)
- Ensures that targeted users have recent activity on the platform before a follow request is sent, avoiding inactive accounts
- Locally caches users previously followed by the bot to prevent redundant follow requests

**Unfollow Management**
- Automatically unfollows users who have been inactive for a configurable duration
- Identifies and unfollows users who do not follow back within a configurable period
- Allows for whitelisting of users who the bot should never unfollow
- Only users originally followed by the bot are considered for unfollowing, so that manual connections are preserved

**Post Liking**
- Acts as a workaround for the daily follow limit, as there is no known limit for liking posts.
- Discovers new workouts through the Hevy feed and automatically likes them to increase visibility.

**Notifications**
- Integrates with Discord webhooks to send notifications and summaries of bot activities (users followed, unfollowed, etc.)

**Scheduling**
- Can be configured to run all processes automatically at predefined intervals using a cron-based scheduler

## How It Works
The Hevy Engagement Bot operates by interacting with the Hevy API to simulate user activity. Here's a general overview of its process:

  1. **Authentication**: The bot authenticates with the Hevy API using your provided auth token
  2. **Configuration**: It loads settings from `config/config.yaml`, which sets daily limits, delays, and scheduling.
  3. **Discovery Feed Analysis**:
  - The bot fetches the "Discovery Feed," which contains recent workouts, comments, and likes from other Hevy users.
  - It parses this data to identify potential users to follow or workouts to like based on their activity.
  - Before following, it quickly checks the target's recent workout activity to make sure they're not inactive.
  4. **Follow/Like Execution**: The bot sends follow/like requests through the API.
  5. **Following Cache Update**: When a user is followed, their details and the timestamp of the follow are added to a local cache. This helps determine unfollow criteria and avoid duplicate follows.
  6. **Unfollow Logic**:
  - The bot reviews the users in its followed cache.
  - It checks each cached user's last workout date to determine inactivity.
  - It also checks if the user has followed back within the defined threshold.
  - Users meeting the unfollow criteria (and are not on the whitelist) are unfollowed.
  - A separate unfollowed cache tracks users that have been unfollowed to prevent refollowing them.
  7. **Notifications**: Throughout the operation, the bot sends notifications to a Discord webhook.

## Proven Results

This bot has been rigorously tested on a dedicated Hevy account. Over a period of just one month, the account's follower count increased from **31 to over 1,000 followers**, demonstrating the effectiveness of taking advantage of engagement techniques.
![image](https://github.com/user-attachments/assets/b72d5892-df20-4316-b7b9-13990d37d8b1) ➔ ![image](https://github.com/user-attachments/assets/d474a60c-b672-44cf-b57a-ac6b8404a67a)

## Setup

To get the Hevy Engagement Bot up and running, follow these steps:
1. **Environment Variables (`.env` file)**:
  Create a file names `.env` in the root directory.
  ```
  # API Credentials
  AUTH_TOKEN=
  # Discord Webhook (Optional)
  DISCORD_WEBHOOK_URL=
  ```
2. **Configuration File (`config/config.yaml` - Optional)**:
  Customize the bot's configuration by editing the `config/config.yaml` file.
  ```yaml
    # Scheduler Settings
    scheduler:
      follow_schedule: "0 12 * * *"    # Run at 12 PM daily
      unfollow_schedule: "0 12 * * *"  # Run at 12 PM daily
      like_schedule: "0 * * * *"       # Run every hour at minute 0

    # API Settings
    api:
      base_url: "https://api.hevyapp.com"
      rate_limit_delay: 300  # 5 minutes
      request_delay:
        min: 1.5
        max: 3.0

    # Follow Settings
    follow:
      target_count: 30     # Daily follow limit
      comment_priority: 2  # Higher priority for users who comment
      like_priority: 1     # Lower priority for users who only like

    # Unfollow Settings
    unfollow:
      inactive_threshold: 21    # days
      follow_back_threshold: 7  # days
      daily_unfollow_cap: 100

    # Like Settings
    like:
      like_cap: 50         # Max number of workouts to like per run
  ```
3. **Whitelist (`data/whitelist.json` - Optional)**:
  If there are specific users you wish to permanently exclude from the unfollow process, add their usernames to `data/whitelist.json`. Example:
  
```JSON
[
  "username1",
  "username2",
  "username3"
]
```

## Usage

Before running the bot, ensure all required Python dependencies are installed.

1. **Install Dependencies**:
  Navigate to the root directory in your terminall and run:
  ```command
  pip install -r requirements.txt
  ```
2. **Run the Bot**:
  You can execure the bot in various modes using certain arguments:
  ```command
  python -m src.main --auto
  python -m src.main --follow
  python -m src.main --unfollow
  python -m src.main --like
  ```

## Requirements

- Python 3.8 or a more recent version
- All packages listed in the `requirements.txt` file

## License

MIT License

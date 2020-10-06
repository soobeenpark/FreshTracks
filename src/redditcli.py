"""A module for dealing with the Reddit API.

Contains most helper methods used by program that interacts with Reddit's
API.

author: Soobeen Park
file: redditcli.py
"""

from datetime import datetime, timezone
import praw
from typing import List


def init_reddit_client(botname, config_interp) -> praw.Reddit:
    """Returns instantiated PRAW API client.

    Args:
        botname (str): Name of bot in praw.ini file.
        config_interp (str): Setting to pass PRAW initializer.

    Return:
        praw.Reddit: Initialized PRAW client.
    """
    reddit = praw.Reddit(botname, config_interpolation=config_interp)
    return reddit


def retrieve_fresh(reddit, last_accessed_time, subreddit_name) -> List:
    """Retrieve all fresh posts in subreddit since script was last run.

    In each of the posts, we make the assumption that the string "FRESH"
    appears in each submission title with new music content.

    Args:
        reddit (praw.Reddit): Initialized reddit client.
        last_accessed_time (int): utc time of most recent reddit post in DB.
        subreddit_name (str): Name of the subreddit we are handling.

    Returns:
        list: The list of new posts since the script was last ran.
    """

    # Get reddit instance from PRAW
    print("Read-only mode?: ", reddit.read_only)

    # Get subreddit that we want
    subreddit = reddit.subreddit(subreddit_name)

    # Initialize list to store only [FRESH] posts we haven't seen before
    fresh_posts = []

    # Add new posts from last hour into our fresh_posts list
    limit_max = 1000
    for submission in subreddit.new(limit=50):
        # Get time that submission was created
        submission_created_time = datetime.fromtimestamp(
            submission.created_utc, tz=timezone.utc)

        # If we reach a post that we've already seen, break
        if submission_created_time < last_accessed_time:
            break

        # Add the new post to our list to process
        if "FRESH" in submission.title:
            fresh_posts.append(submission)

    return fresh_posts


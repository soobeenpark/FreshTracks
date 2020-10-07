"""A module for dealing with the Reddit API.

Contains most helper methods used by program that interacts with Reddit's
API.

author: Soobeen Park
file: redditcli.py
"""

from datetime import datetime, timezone
import pprint
import praw
import pytz
from typing import List


class RedditCli:
    """General class to help with interacting with Reddit API."""

    def __init__(self, botname, config_interp):
        """Instantiated Reddit API client.

        Args:
            botname (str): Name of bot in praw.ini file.
            config_interp (str): Setting to pass PRAW initializer.
        """
        self.reddit = praw.Reddit(botname, config_interpolation=config_interp)
        self.limit_max = 100   # Max amount of posts to retreive at once


    def retrieve_fresh(self, last_accessed_time, subreddit_name) -> List:
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

        # Get subreddit that we want
        subreddit = self.reddit.subreddit(subreddit_name)

        # Initialize list to store only [FRESH] posts we haven't seen before
        fresh_posts = []

        # Add new posts from last hour into our fresh_posts list
        for submission in subreddit.new(limit=self.limit_max):
            # Get time that submission was created
            submission_created_time = datetime.fromtimestamp(
                submission.created_utc, tz=timezone.utc)

            # If we reach a post that we've already seen, break
            if submission_created_time <= last_accessed_time:
                break

            # Add the new post to our list to process
            if "FRESH" in submission.title:
                fresh_posts.append(submission)

        return fresh_posts

#!/usr/bin/env python

"""
@author: Soobeen Park
@file: main.py

TODO: Add documentation
"""

from datetime import datetime, timezone, timedelta
import logging
import pprint
import praw
import pymongo
from pymongo import MongoClient
import re
import spotipy
import sys
from typing import List


def get_last_accessed_time(db, subreddit_name) -> datetime:
    """Retrieve most recent datetime that is stored in the database

    Args:
        db (pymongo.database.Database): Connected MongoDB instance.
        subreddit_name (str): The name of the subreddit being accessed.

    Returns:
        datetime.datetime: The datetime that the script last accessed new posts.
    """
    # Find most recently posted song on subreddit
    last_accessed_time = 0
    collection = db[subreddit_name]
    cur = collection.find({}).sort('created_utc', pymongo.DESCENDING).limit(1)
    results = list(cur)

    if results:
        last_inserted = results[0]
        last_accessed_time = last_inserted['created_utc']
    else:
        # If no results in database, set last accessed to 1 week ago
        last_accessed_time = datetime.now(timezone.utc) - timedelta(weeks=1)

    print("Last accessed: ", last_accessed_time)
    return last_accessed_time


def retrieve_fresh(last_accessed_time, subreddit_name) -> List:
    """Retrieve all fresh posts in subreddit since script was last run.

    In each of the posts, we make the assumption that the string "FRESH"
    appears in each submission title with new music content.

    Args:
        last_accessed_time (int): utc time of most recent reddit post in DB.
        subreddit_name (str): Name of the subreddit we are handling.

    Returns:
        list: The list of new posts since the script was last ran.
    """

    # Get reddit instance from PRAW
    reddit = praw.Reddit("bot1", config_interpolation="basic")
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


def process_fresh(fresh_posts):
    """Separates out the fresh posts according to their specific type

    Posts tagged FRESH can be of any of the following types:
        1. [FRESH] - Usually meaning new singles, but not a strict convention.
        2. [FRESH ALBUM] - New album.
        3. [FRESH STREAM] - Previously released song, but just now available on
                            streaming platforms.
        4. [FRESH PERFORMANCE] - New live performance, usually video.
                                 Also, usually uploaded as a YouTube link.
        5. [FRESH VIDEO] - New music video that has been released.


    The function only stores posts tagged [FRESH], [FRESH ALBUM], and
    [FRESH STREAM] into the database, since we aren't interested in videos.
    
    Note that these conventions differ according to the subreddit, so it is
    advised to check the rules of the specific subreddit to make sure this
    function conforms to them.

    params:
        fresh_posts (List): The list of all retrieved submissions with FRESH in
                            the title, to be processed.
    """
    # List of dict containing necessary information to search in Spotify
    processed_posts = []

    for post in fresh_posts:
        print(post.title)
        post_dict = dict()
        post_dict["created_utc"] = post.created_utc
        post_dict["ups"] = post.ups

        if post.media and "spotify" in post.media["oembed"]["provider_name"].lower():
            # Artist and Title already provided by Spotify - capture that
            pprint.pprint(post.media["oembed"]["description"])
            desc_regex = re.compile(r"""^Listen\ to\s
                    (?P<title>.+)\s                  # Title
                    on\ Spotify.\s
                    (?P<artist>.+)\s                  # Artist
                    (·)?\s
                    (?P<type>\w+)\s                 # Type
                    (·)?\s
                    (?P<year>\d+)                   # Year
                    (\s·\s(?P<num_songs>\d+)\ssongs)?    # Num songs (if exist)
                    .$""", re.VERBOSE)
            match = desc_regex.search(post.media["oembed"]["description"])

            if match:
                # Regex properly parsed
                gd = match.groupdict()
                if gd.get("num_songs", None) == None:
                    gd["num_songs"] = 1

                post_dict.update(gd)
            else:
                raise Exception("Error parsing in process_fresh()")

        else:
            # Have to parse Artist and Title from post title,
            # then search if that combo exists in Spotify
            print()

        print(post_dict)



if __name__ == "__main__":
    # Setup logger to log any exceptions
    log_format_str = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(filename="../tmp/error.log", level=logging.ERROR,
            format=log_format_str)
    logger = logging.getLogger(__name__)

    try:
        # Connect to local MongoDB instance
        client = MongoClient()  # Connect to local mongo server
        db = client.freshtracks  # Use freshtracks database

        subreddit_name = "indieheads"

        # Get the date and time of the most recently added [FRESH] track
        last_accessed_time = get_last_accessed_time(db, subreddit_name)


        # Retrieve new posts in subreddit since last time script was run
        fresh_posts = retrieve_fresh(last_accessed_time, subreddit_name)

        # Filter new posts to only those with [FRESH] tags in them
        process_fresh(fresh_posts)
    except Exception as e:
        # Log and exit program
        print("Exception caught")
        logger.exception(e)
        sys.exit(1)

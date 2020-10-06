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


def is_valid_freshtype(freshtype) -> bool:
    """Parses the freshtype string to see if it is "valid"

    For which freshtypes are considered valid, see the documentation for
    process_fresh().

    Args:
        freshtype (str): The freshtype tagged in the reddit post title.

    Returns:
        bool: True if valid freshtype, false if otherwise.
    """
    freshtype_lower = freshtype.lower()
    valid_qualifiers = ["album", "ep", "single", "stream"]
    if freshtype_lower == "fresh":
        return True
    elif any(vq in freshtype_lower for vq in valid_qualifiers):
        return True
    else:
        return False
    

def parse_post_embdedded_media(media_description_str) -> dict:
    """Parses the embedded Spotify media description in the reddit post

    Args:
        media_description_str (str): The post's Spotify media description str

    Return:
        dict: A dictionary containing parsed information from the arg.
    """
    desc_regex = re.compile(r"""^Listen\ to\s
            (?P<title>.+)\s                 # Title
            on\ Spotify.\s
            (?P<artist>.+)\s                # Artist
            (·)?\s
            (?P<type>\w+)\s                 # Type
            (·)?\s
            (?P<year>\d+)                   # Year
            (\s·\s(?P<num_songs>\d+)\ssongs)?    # Num songs (if exist)
            .$""", re.VERBOSE)
    match = desc_regex.search(media_description_str)

    if match:
        # Regex properly parsed
        gd = match.groupdict()
        if gd.get("num_songs", None) == None:
            gd["num_songs"] = 1

    else:
        raise Exception("Error parsing in process_fresh()")
    
    return gd


def parse_post_title(title_str) -> dict:
    """Parses the post title

    Args:
        title_str (str): The post's title string.

    Return:
        dict: A dictionary containing parsed information from the arg.
    """

    title_regex = re.compile(r"""
        \[\s*(?P<freshtype>fresh\s*\w*)\s*\]\s*     # FRESH type
        ((?P<artist1>.+)\s                          # Artist1
        -\s
        (?P<title1>.+)                              # Title1
        |
        (?P<artist2>.+)                             # Artist2
        -
        (?P<title2>.+))                             # Title 2
        """, re.VERBOSE | re.IGNORECASE)
    match = title_regex.search(title_str)

    if match:
        # Regex properly parsed
        gd = match.groupdict()
        if gd["artist1"]:     # Regex matched artist1-title1 groups
            assert(gd["title1"])
            gd["artist"] = gd["artist1"]
            gd["title"] = gd["title1"]
        else:           # Regex matched artist2-title2 groups
            assert(gd["artist2"] and gd["title2"])
            gd["artist1"] = gd["artist2"]
            gd["title1"] = gd["title2"]

        gd["artist"] = re.sub(r"\(.*\)", "", gd["artist1"])
        gd["title"] = re.sub(r"\(.*\)", "", gd["title1"])

    else:
        # No match found
        gd = None

    return gd


def process_fresh(fresh_posts):
    """Separates out the fresh posts according to their specific type

    Posts tagged FRESH can be of any of the following types:
        1. [FRESH] - Usually meaning new singles, but not a strict convention.
        2. [FRESH ALBUM] - New album.
        3. [FRESH EP] - New EP.
        4. [FRESH SINGLE] - New single.
        5. [FRESH STREAM] - Previously released song, but just now available on
                            streaming platforms.
        6. [FRESH PERFORMANCE] - New live performance, usually video.
                                 Also, usually uploaded as a YouTube link.
        7. [FRESH VIDEO] - New music video that has been released.


    The function only stores "valid" posts tagged [FRESH], [FRESH ALBUM], 
    [FRESH EP], [FRESH SINGLE], or [FRESH STREAM] into the database,
    since we aren't interested in videos.
    
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
            # Artist and Title already provided by Spotify in Reddit embedded
            # media. Just simply capture that string.
            parsed_dict = parse_post_embdedded_media(post.media["oembed"]["description"])

        else:
            # Have to parse Artist and Title from post title,
            # then search if that combo exists in Spotify.
            # We make the (big) assumption that title is a string in the format
            # of '[FRESH (____)] Artist - Title'
            parsed_dict = parse_post_title(post.title)
            if not parsed_dict:
                # If no match able to be parsed, discard this post
                continue

        post_dict.update(parsed_dict)
        print(post_dict)
        print()




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

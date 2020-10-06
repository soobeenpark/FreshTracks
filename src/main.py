#!/usr/bin/env python

"""TODO: Add documentation

author: Soobeen Park
file: main.py
"""

from datetime import datetime, timezone, timedelta
import logging
import pprint
import pymongo
from pymongo import MongoClient
import re
import redditcli as rcli
import spotifycli as scli
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys
from typing import List


def get_last_accessed_time(db, subreddit_name) -> datetime:
    """Retrieve most recent datetime that is stored in the database.

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


def parse_post_embdedded_media(media_description_str) -> dict:
    """Parses the embedded Spotify media description in the reddit post.

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
        raise Exception("Error parsing in parse_post_embdedded_media()")
    
    return gd


def parse_post_title(title_str) -> dict:
    """Parses the post title.

    Args:
        title_str (str): The post's title string.

    Return:
        dict: A dictionary containing parsed information from the arg.
            If parsing failed or invalid freshtype, an empty dict is returned.
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

    return_dict = dict()
    if match:
        # Regex properly parsed
        gd = match.groupdict()

        # Exit early if not a valid freshtype in title
        if not is_valid_freshtype(gd["freshtype"]):
            return dict()

        if gd["artist1"]:     # Regex matched artist1-title1 groups
            assert(gd["title1"])
            gd["artist"] = gd["artist1"]
            gd["title"] = gd["title1"]
        else:           # Regex matched artist2-title2 groups
            assert(gd["artist2"] and gd["title2"])
            gd["artist1"] = gd["artist2"]
            gd["title1"] = gd["title2"]

        return_dict["artist"] = re.sub(r"\(.*\)", "", gd["artist1"]).strip()
        return_dict["title"] = re.sub(r"\(.*\)", "", gd["title1"]).strip()
        return_dict["freshtype"] = gd["freshtype"]

    return return_dict


def is_valid_freshtype(freshtype) -> bool:
    """Checks if the tag used in [FRESH ___] is a "valid" type.

    We are only interested in processing valid freshtypes.
    For a list of valid freshtypes, see the documentation for 
    prepare_fresh_for_search()

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
    

def prepare_fresh_for_search(fresh_posts) -> List:
    """Parses the post details so that they are ready to search in Spotify.

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

    Params:
        spot (spotify.Spotify): The initialized Spotify client.
        fresh_posts (List): The list of all retrieved submissions with FRESH in
                            the title, to be prepared.

    Returns:
        list: A list containing a parsed dictionary of each post per element.
    """
    # List of dict containing necessary information to search in Spotify
    prepared_posts = []

    for post in fresh_posts:
        print(post.title)
        post_dict = dict()
        post_dict["reddit_post_id"] = post.id
        post_dict["created_utc"] = post.created_utc
        post_dict["ups"] = post.ups

        if post.media and "spotify" in post.media["oembed"]["provider_name"].lower():
            # Artist and Title already provided by Spotify in Reddit embedded
            # media. Just simply capture that string.
            parsed_dict = parse_post_embdedded_media(
                    post.media["oembed"]["description"])

            # Add this value for ease of processing later
            parsed_dict["embedded_media"] = True

        else:
            # Have to parse Artist and Title from post title,
            # then search if that combo exists in Spotify.
            # We make the (big) assumption that title is a string in the format
            # of '[FRESH (____)] Artist - Title'
            parsed_dict = parse_post_title(post.title)
            if not parsed_dict:
                # If no match able to be parsed, discard this post
                continue

            # Add this value for ease of processing later
            parsed_dict["embedded_media"] = False

        post_dict.update(parsed_dict)
        prepared_posts.append(post_dict)

    return prepared_posts


def search_and_populate_posts(spot, prepared_posts) -> List:
    """Call to Spotify search() to populate each post dict with Spotify details.

    In particular, we are interested in using search to obtain the following
    missing ingredients:
        - artist
        - album
        - track
        - total_tracks
        - track_number (within each album)
        - album_type (one from {single, album, compilation})
        - spotify_album_uri

    Args:
        spot (spotify.Spotify): Initialized Spotify client.
        prepared_posts (list): The list that was prepared to use with searches.

    Return:
        list: A list of dicts, where each element is a dict that contains
            the populated Spotify information for each post.
    """
    posts_to_insert = []

    for prepared_post in prepared_posts:
        # Store the result in searched
        searched = dict()

        artist = prepared_post["artist"]
        title = prepared_post["title"]

        if not prepared_post["embedded_media"]:
            # First try to search based as a track
            search_resp = scli.search(spot, artist, title, "track")
            items = search_resp["tracks"]["items"]
            if items:
                item = items[0]
                searched = scli.populate_from_track(item)

        if not searched:
            # Search by track above didn't get applied, because either
            # embedded_media or search by track failed. So now search by
            # album.
            search_resp = scli.search(spot, artist, title, "album")
            items = search_resp["albums"]["items"]
            if items:
                item = items[0]
                searched = scli.populate_from_album(spot, item)

        if not searched:
            # If still not populated, then this post is unfortunately discarded.
            continue

        #Finally add some of the existing relevant data in to the dict to add
        searched["reddit_post_id"] = prepared_post["reddit_post_id"]
        searched["created_utc"] = prepared_post["created_utc"]
        searched["upvotes"] = prepared_post["ups"]

        # Add to list
        posts_to_insert.append(searched)

    return posts_to_insert


def main():
    """Script to execute.
    """
    # Setup logger to log any exceptions
    log_format_str = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(filename="../tmp/error.log", level=logging.ERROR,
            format=log_format_str)
    logger = logging.getLogger(__name__)

    try:
        # Connect to local MongoDB instance
        client = MongoClient()  # Connect to local mongo server
        db = client.freshtracks  # Use freshtracks database

        # Initialize Reddit client
        reddit = rcli.init_reddit_client("bot1", "basic")
        subreddit_name = "indieheads"

        # Initialize Spotify client
        spot = scli.init_spotify_client()

        # Get the date and time of the most recently added [FRESH] track
        last_accessed_time = get_last_accessed_time(db, subreddit_name)

        # Retrieve new posts in subreddit since last time script was run
        fresh_posts = rcli.retrieve_fresh(reddit, last_accessed_time,
                subreddit_name)

        # Filter new posts to only those with [FRESH] tags in them
        prepared_posts = prepare_fresh_for_search(fresh_posts)

        # Search and populate Reddit post with Spotify data
        post_to_insert = search_and_populate_posts(spot, prepared_posts)

    except Exception as e:
        print(e)
        # Log and exit program
        print("Exception caught")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()

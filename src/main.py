#!/usr/bin/env python

"""Automatically updates Spotify playlists from [FRESH] tagged Reddit posts.

author: Soobeen Park
file: main.py
"""

import logging
import os
import sys
from freshtracks import FreshTracks


def main():
    """Script to execute.
    """
    # Setup directory for logging files
    log_files_path = "../tmp/"
    if not os.path.exists(log_files_path):
        os.makedirs(log_files_path)

    # Setup logger to log any exceptions
    log_format_str = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(filename=log_files_path + "error.log",
                        level=logging.ERROR,
                        format=log_format_str)
    logger = logging.getLogger(__name__)

    try:
        print("==============================================")
        # Subreddit settings
        indieheads = {"subreddit_name": "indieheads",
                      "upvote_thresh": 20,
                      "playlist_id": "3QlWwTD13vWFH6UOTH9514"}
        hiphopheads = {"subreddit_name": "hiphopheads",
                       "upvote_thresh": 20,
                       "playlist_id": "3KwOTBOoSfymm3trVqr0oJ"}
        popheads = {"subreddit_name": "popheads",
                    "upvote_thresh": 20,
                    "playlist_id": "72aULoyZowHVuHH1kETADA"}
        subreddit_settings = [indieheads, hiphopheads, popheads]

        for subreddit_setting in subreddit_settings:
            print(
                "Getting FreshTracks from r/" +
                subreddit_setting["subreddit_name"])
            freshtracks = FreshTracks(subreddit_setting)
            freshtracks.run()
            print("\n\n")

    except Exception as e:
        print(e)
        # Log and exit program
        print("Exception caught")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()

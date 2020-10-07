#!/usr/bin/env python

"""TODO: Add documentation 

author: Soobeen Park
file: main.py
"""

from freshtracks import FreshTracks
import logging
import sys


def main():
    """Script to execute.
    """
    # Setup logger to log any exceptions
    log_format_str = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(filename="../tmp/error.log", level=logging.ERROR,
            format=log_format_str)
    logger = logging.getLogger(__name__)

    try:
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

        # TODO: Go through each subreddit
        subreddit_setting = subreddit_settings[0]
        freshtracks = FreshTracks(subreddit_setting)
        freshtracks.run()


    except Exception as e:
        print(e)
        # Log and exit program
        print("Exception caught")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()

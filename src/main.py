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
        subreddit_name = "indieheads"
        freshtracks = FreshTracks(subreddit_name)
        freshtracks.run()


    except Exception as e:
        print(e)
        # Log and exit program
        print("Exception caught")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()

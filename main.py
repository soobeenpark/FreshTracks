#!/usr/bin/env python

import praw
import pprint

def main():
    reddit = praw.Reddit("bot1", config_interpolation="basic")
    print("Read-only mode?: ", reddit.read_only)

    # Print hottest N posts on subreddit
    for i, submission in enumerate(reddit.subreddit("indieheads").hot(limit=20)):
        print(i, submission.title)

    # Print out what attributes are available in "submission" object
    pprint.pprint(vars(submission))



if __name__ == "__main__":
    main()


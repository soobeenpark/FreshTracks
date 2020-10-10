"""A module that retrieves the FreshTracks.

This contains the main meat of the program.

author: Soobeen Park
file: freshtracks.py
"""

from datetime import datetime, timezone, timedelta
import pprint
import pymongo
from pymongo.errors import DuplicateKeyError
import pytz
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys
from typing import List

from redditcli import RedditCli
from spotifycli import SpotifyCli
from models.post import Post
from models.playlisttrack import PlaylistTrack


class FreshTracks:
    """Class that contains most of the meat of the program."""

    def __init__(self, subreddit_setting):
        """Instantiates FreshTracks.

        Args:
            subreddit_setting (dict): Info needed for each subreddit.
        """
        self.rcli = RedditCli("bot1", "basic")
        self.scli = SpotifyCli()
        self.subreddit_name = subreddit_setting["subreddit_name"]
        self.upvote_thresh = subreddit_setting["upvote_thresh"]
        self.playlist_id = subreddit_setting["playlist_id"]

        # How far ago we go to keep tracks active in playlist (ie. one week)
        self.one_week_ago = datetime.now(timezone.utc) - timedelta(weeks=1)

        # Get the date and time of the most recently added [FRESH] track
        self.last_accessed_time = self.get_last_accessed_time()



    def get_last_accessed_time(self) -> datetime:
        """Retrieve most recent datetime that is stored in the database.

        Args:
            subreddit_name (str): The name of the subreddit being accessed.

        Returns:
            datetime.datetime: The datetime that the script last accessed new
                                posts.
        """
        # Find most recently posted song on subreddit
        last_accessed_time = 0
        try:
            results = Post.objects.raw({"subreddit": self.subreddit_name}) \
                .order_by([("created_utc", pymongo.DESCENDING)]) \
                .limit(1)
            last_accessed_time = results[0].created_utc
            last_accessed_time = pytz.utc.localize(last_accessed_time) # tzaware
        except Post.DoesNotExist:
            # If no results in database, set last accessed to 1 week ago
            last_accessed_time = self.one_week_ago

        print("\tLast accessed: ", last_accessed_time)
        return last_accessed_time


    def parse_post_embdedded_media(self, media_description_str) -> dict:
        """Parses the embedded Spotify media description in the reddit post.

        Args:
            media_description_str (str): Post's Spotify media description str

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
            if gd.get("num_songs", None) is None:
                gd["num_songs"] = 1

        else:
            # Return empty dict for fail to parse
            return dict()

        return gd


    def parse_post_title_wo_FRESH(self, freshtype, title_str) -> dict:
        """Parses the post title, that does not contain [FRESH (___)] in title.

        Args:
            freshtype (str): The freshtype tagged in the reddit post.
            title_str (str): The post's title string.

        Return:
            dict: A dictionary containing parsed information from the arg.
                If parsing failed or invalid freshtype, empty dict is returned.
        """
        # Exit early if not a valid freshtype in title
        if not freshtype or not self.is_valid_freshtype(freshtype):
            return dict()

        # The regex below is divided into 2 different artist-title groups to
        # account for any dashes/hyphens in the artist or title names
        title_regex = re.compile(r"""
            ((?P<artist1>.+)\s?                         # Artist1
            -\s?
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

            if gd["artist1"]:     # Regex matched artist1-title1 groups
                assert(gd["title1"])
                gd["artist"] = gd["artist1"]
                gd["title"] = gd["title1"]
            else:           # Regex matched artist2-title2 groups
                assert(gd["artist2"] and gd["title2"])
                gd["artist1"] = gd["artist2"]
                gd["title1"] = gd["title2"]

            return_dict["artist"] = re.sub(
                r"\(.*\)", "", gd["artist1"]).strip()
            return_dict["title"] = re.sub(r"\(.*\)", "", gd["title1"]).strip()
            return_dict["freshtype"] = freshtype

        return return_dict


    def parse_post_title_with_FRESH(self, title_str) -> dict:
        """Parses the post title with FRESH in the title.

        We assume that the post title must be of '[FRESH (___)] Artist - Title'.
        Otherwise, an empty dict is returned.

        Args:
            title_str (str): The post's title string.

        Return:
            dict: A dictionary containing parsed information from the arg.
                If parsing failed or invalid freshtype, empty dict is returned.
        """

        # The regex below is divided into 2 different artist-title groups to
        # account for any dashes/hyphens in the artist or title names
        title_regex = re.compile(r"""
            \[\s*(?P<freshtype>fresh\s*\w*)\s*\]\s*     # FRESH type
            ((?P<artist1>.+)\s?                         # Artist1
            -\s?
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
            if not self.is_valid_freshtype(gd["freshtype"]):
                return dict()

            if gd["artist1"]:     # Regex matched artist1-title1 groups
                assert(gd["title1"])
                gd["artist"] = gd["artist1"]
                gd["title"] = gd["title1"]
            else:           # Regex matched artist2-title2 groups
                assert(gd["artist2"] and gd["title2"])
                gd["artist1"] = gd["artist2"]
                gd["title1"] = gd["title2"]

            return_dict["artist"] = re.sub(
                r"\(.*\)", "", gd["artist1"]).strip()
            return_dict["title"] = re.sub(r"\(.*\)", "", gd["title1"]).strip()
            return_dict["freshtype"] = gd["freshtype"]

        return return_dict


    def is_valid_freshtype(self, freshtype) -> bool:
        """Checks if the tag used in [FRESH ___] is a "valid" type.

        We are only interested in processing valid freshtypes.
        For a list of valid freshtypes, see the documentation for
        prepare_fresh_for_search()

        Args:
            freshtype (str): The freshtype tagged in the reddit post.

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


    def has_embedded_media(self, post) -> bool:
        """Helper method to check if post has embedded media we can use.

        Args:
            post (json): The Reddit post submission.

        Return:
            bool: True if the post has embedded Spotify media with valid 
                description, False otherwise.
        """
        if not post.media:
            return False
        if "oembed" not in post.media:
            return False
        if "provider_name" not in post.media.get("oembed"):
            return False
        if "description" not in post.media.get("oembed"):
            return False
        if "spotify" not in post.media["oembed"]["provider_name"].lower():
            return False
        return True


    def parse_fresh(self, fresh_posts) -> List:
        """Parses the post details so that they are ready to search in Spotify.

        Posts tagged FRESH can be of any of the following types:
            1. [FRESH] - Usually means new singles, but not a strict convention.
            2. [FRESH ALBUM] - New album.
            3. [FRESH EP] - New EP.
            4. [FRESH SINGLE] - New single.
            5. [FRESH STREAM] - Previously released song, but just now available
                                on streaming platforms.
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
            fresh_posts (List): The list of all retrieved submissions with FRESH
                                in the title, to be prepared.

        Returns:
            list: A list containing parsed dictionary of each post per element.
        """
        # List of dict containing necessary information to search in Spotify
        prepared_posts = []

        for post in fresh_posts:
            parsed_dict = dict()

            if self.has_embedded_media(post):
                # Artist and Title already provided by Spotify in Reddit
                # embedded media. Just simply capture that string.
                parsed_dict = self.parse_post_embdedded_media(
                    post.media["oembed"]["description"])

            if not parsed_dict:
                # Post doesn't have appropriate embedded media.
                # Have to parse Artist and Title from post title,
                # then search if that combo exists in Spotify.
                if self.subreddit_name in ("indieheads", "hiphopheads"):
                    parsed_dict = self.parse_post_title_with_FRESH(post.title)

                elif self.subreddit_name in ("popheads") and \
                        "link_flair_text" in vars(post):
                    parsed_dict = self.parse_post_title_wo_FRESH( \
                            post.link_flair_text, post.title)

                else:
                    raise Exception("Select parsing method for subreddit " + \
                            self.subreddit_name)

            if not parsed_dict:
                # If no match able to be parsed, discard this post
                continue

            # Add rest of relevant values
            parsed_dict["reddit_post_id"] = post.id
            parsed_dict["created_utc"] = post.created_utc
            parsed_dict["ups"] = post.ups
            # Add this for ease of processing later
            parsed_dict["has_embedded_media"] = self.has_embedded_media(post)

            prepared_posts.append(parsed_dict)

        return prepared_posts


    def search_and_populate_posts(self, prepared_posts) -> List:
        """Call to Spotify search() to populate each post dict with Spotify
        details.

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
            prepared_posts (list): The list that was prepared to search with.

        Return:
            list: A list of dicts, where each element is a dict that contains
                the populated Spotify information for each post.
        """
        populated_posts = []

        for prepared_post in prepared_posts:
            # Store the result in searched
            searched = dict()

            artist = prepared_post["artist"]
            title = prepared_post["title"]

            if not prepared_post["has_embedded_media"]:
                # First try to search based as a track
                search_resp = self.scli.search(artist, title, "track")
                items = search_resp["tracks"]["items"]
                if items:
                    item = items[0]
                    searched = self.scli.populate_from_track(item)

            if not searched:
                # Search by track above didn't get applied, because either has
                # embedded media or search by track failed. So now search by
                # album.
                search_resp = self.scli.search(artist, title, "album")
                items = search_resp["albums"]["items"]
                if items:
                    item = items[0]
                    searched = self.scli.populate_from_album(item)

            if not searched:
                # If still not populated, then this discard this post.
                continue
            
            # Finally add some of the existing relevant data in to the dict to
            # add
            searched["reddit_post_id"] = prepared_post["reddit_post_id"]
            searched["created_utc"] = prepared_post["created_utc"]
            searched["upvotes"] = prepared_post["ups"]
            searched["parsed_artist"] = artist
            searched["parsed_title"] = title

            # Add to list
            populated_posts.append(searched)

        return populated_posts


    def save_posts(self, posts_to_insert):
        """Saves the posts as documents in the Posts collection.

        Args:
            posts_to_insert (list): A list of dicts, each containing
                                    info about a post.
        """
        count = 0
        for p in posts_to_insert:
            post_obj = Post(**p)
            try:
                # force_insert will raise DuplicateKeyError instead of
                # quietly overwriting existing document
                post_obj.save(force_insert=True)
            except DuplicateKeyError:
                # If post/album already exists, then discard this post
                continue
            count += 1
            print("\t\t...Saving to DB: " + p["artist"] + " - " + p["track"])
        print("\tAfter filtering, saved %d posts into DB" % count)


    def refresh_upvotes(self):
        """Refreshes upvotes on each post within past week.
        """
        posts_past_week = Post.objects.raw({"$and":
                [{"created_utc": {"$gte": self.one_week_ago}},
                {"subreddit": self.subreddit_name}]})
        count = 0
        for post in posts_past_week:
            reddit_post_id = post.reddit_post_id
            upvotes = self.rcli.reddit.submission(id=reddit_post_id).ups
            post.upvotes = upvotes
            post.save()
            count += 1
        print("\tRefreshed %d posts' upvotes" % count)


    def remove_playlist_old(self):
        """Removes stale tracks from Playlist.

        Reflects changes to both Post and PlaylistTrack document.

        """
        posts = Post.objects.raw({"$and": 
            [{"subreddit": self.subreddit_name},
                {"exists_in_playlist": True}]})
        post_ids = [p.reddit_post_id for p in posts]
        # Get all tracks in playlist in order
        playlisttracks = PlaylistTrack.objects \
                .raw({"_id": {"$in": post_ids}}) \
                .order_by([("playlist_position", pymongo.ASCENDING)])

        num_removed = 0
        tracks_to_remove = []
        for i, playlisttrack in enumerate(list(playlisttracks)):
            # tzaware
            created_utc = pytz.utc.localize(playlisttrack.post.created_utc)

            post = playlisttrack.post
            if created_utc < self.one_week_ago or \
                    post.upvotes < self.upvote_thresh:

                print("\t\t>>> Removing " + post.artist + " - " + post.track)

                # Remove from collection
                playlisttrack.delete()

                # Add track to remove it later
                assert(i == playlisttrack.playlist_position)
                tracks_to_remove.append({"uri": post.spotify_track_uri,
                    "positions": [i]})

                # Update post
                post.exists_in_playlist = False
                post.save()

                # Final increment
                num_removed += 1

            else:
                # Adjust playlist position
                playlisttrack.playlist_position = i-num_removed
                playlisttrack.save()

        # Remove all appropriate tracks from Spotify playlist
        self.scli.spot.playlist_remove_specific_occurrences_of_items(
                playlist_id=self.playlist_id, items=tracks_to_remove)
        assert(num_removed == len(tracks_to_remove))
        print("\tRemoved %d stale/downvoted tracks from playlist" % num_removed)


    def replace_album_most_popular_track(self):
        """Ensure that the most popular track of an album is in playlist.
        """
        # Get all posts from subreddit that are in playlist
        posts = Post.objects.raw({"$and": 
            [{"subreddit": self.subreddit_name},
                {"exists_in_playlist": True}]})
        post_ids = [p.reddit_post_id for p in posts]
        # Get all tracks in playlist in order
        playlisttracks = PlaylistTrack.objects \
                .raw({"_id": {"$in": post_ids}}) \
                .order_by([("playlist_position", pymongo.ASCENDING)])

        count = 0
        for playlisttrack in list(playlisttracks):
            post = playlisttrack.post
            track = self.scli.get_most_popular(post.spotify_album_uri)
            if not track:
                # couldn't find most popular track.
                continue

            # Update track if most popular changed
            if track["uri"] != post.spotify_track_uri:
                count += 1

                # Update in Spotify playlist
                playlisttrack = list(PlaylistTrack.objects \
                        .raw({"_id": post.reddit_post_id}))[0]
                pos = playlisttrack.playlist_position

                self.scli.replace_track_at_pos(self.playlist_id, 
                        playlisttrack.post.spotify_track_uri, track["uri"], pos)

                # Update in DB
                post.track = track["name"]
                post.track_number = track["track_number"]
                post.spotify_track_uri = track["uri"]
                post.save()
                playlisttrack.delete()
                PlaylistTrack(post=post, playlist_position=pos).save()


        print("\t%d tracks in playlist have been swapped out for the " \
            "more popular track in same album!" % count)


    def update_playlist_ordered(self):
        """Inserts/Updates tracks into Playlist in order.

        Ensures that the playlist songs are in sorted order according to their
        respective reddit upvote counts
        """
        # Find posts to update the playlist with
        posts = Post.objects.raw({"$and": 
                [{"created_utc": {"$gte": self.one_week_ago}},
                {"upvotes": {"$gte": self.upvote_thresh}},
                {"subreddit": self.subreddit_name}]}) \
                .order_by([("upvotes", pymongo.DESCENDING)])

        
        insert_count = 0
        for i, post in enumerate(list(posts)):
            if post.exists_in_playlist: # Reorder existing track
                # Update playlist on Spotify
                playlisttrack = list(PlaylistTrack.objects.
                        raw({"_id": post.reddit_post_id}))[0]
                

                self.scli.spot.playlist_reorder_items(
                        playlist_id=self.playlist_id,
                        range_start=playlisttrack.playlist_position,
                        insert_before=i)

                # Update new playlist position in DB
                playlisttrack.playlist_position = i
                playlisttrack.save()

            else: # Insert track that didn't exist in playlist
                insert_count += 1
                print("\t\t<<< Inserting " + post.artist + " - " + post.track)

                # Insert to collection
                PlaylistTrack(post=post, playlist_position=i) \
                    .save(force_insert=True)

                # Insert to Spotify playlist
                self.scli.spot.playlist_add_items(playlist_id=self.playlist_id,
                        items=[post.spotify_track_uri], position=i)

                # Update post
                post.exists_in_playlist = True
                post.save()

        
        print("\tInserted %d new tracks into the playlist" % insert_count)
        print("\tThere are now %d tracks in the playlist" % len(list(posts)))


    def run(self):
        """Driver to run the whole program."""
        # Retrieve new posts in subreddit since last time script was run
        fresh_posts = self.rcli.retrieve_fresh(self.last_accessed_time,
                self.subreddit_name)
        print("\tRetrieved ", len(fresh_posts), " posts from ",
                self.subreddit_name)

        
        # Filter new posts to only those with [FRESH] tags in them
        prepared_posts = self.parse_fresh(fresh_posts)

        # Search and populate Reddit post with Spotify data
        populated_posts = self.search_and_populate_posts(prepared_posts)
        # Finally, add subreddit_name to each post
        posts_to_insert = [dict(pp, subreddit=self.subreddit_name) 
                for pp in populated_posts]

        # Save posts
        self.save_posts(posts_to_insert)

        # Refresh upvotes on posts from past week
        self.refresh_upvotes()

        # Remove stale/downvoted posts
        self.remove_playlist_old()

        # Refresh which track of an album is most popular
        self.replace_album_most_popular_track()

        # Insert/Update [FRESH] tracks in the playlist within past week
        self.update_playlist_ordered()

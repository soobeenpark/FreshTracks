# FreshTracks
Automatically update [FRESH]est new Album / Track releases.

# What is this?
On certain reddit subreddits such as r/indieheads, r/hiphopheads, or r/popheads, new music is uploaded by users with a [FRESH] tag in the title. For many users like myself, this is the main source of finding new music. Often times though, it's easy to miss a lot of great new music unless you frequent the subreddit 24/7. Thus, this is an effort to automate pulling all the [FRESH] tracks that get posted and neatly organize them into auto-updating Spotify playlists, one for each subreddit.

# Playlist Design
1. The playlist only includes [FRESH] tracks up to one week since first posted to reddit. Older tracks are removed.

2. The tracks in the playlist are sorted according to their number of upvotes in each reddit post.  <br>
This is a great way to see which of the recent songs are generating the most buzz within each subreddit.

3. To sort by recently added date (freshest) instead of number of upvotes (default), simply sort by date using the mechanism Spotify provides.

4. The reddit posts tagged [FRESH] are sometimes albums/EPs which contain multiple tracks.  <br>
A decision was made to include only the most popular track (by Spotify's algorithm standards) on each [FRESH] album/EP, so as to avoid flooding the playlist with multiple tracks from the same artist and album.

5. The playlist gets updated **every hour**. <br>
Every hour:
    - Old stale tracks are removed.
    - New fresh tracks are added.
    - The number of upvotes is refreshed and playlist sorted accordingly.
    - On each [FRESH] post with an album/EP, the most popular song is updated if it has changed within the past hour.\*

\* A small caveat as a result is that the "added date" on the Spotify playlist may not 100% accurately represent how fresh the track is. This is because if the most popular track on an album/EP changed, then the older popular track has to be removed and the newer popular track inserted from the playlist, which updates the date added. However, this does not change when the album/EP track gets removed from the playlist, since that date is calculated by the original reddit post's created date. However, these cases are **very rare**.


# Running the script
The script is designed to be run as a cron job every hour.

The script uses a Mongo database to keep track of [FRESH] tracks in the playlist, as well as all tracks that have ever been added (including old stale tracks after they are removed from the playlist). Make sure to have a MongoDB server running before running the script.

Steps:
` TODO: fill in steps with code `  


# Dependencies
Built using Python 3.8 (venv).
Ubuntu 20.04 LTS.
Please refer to `requirements.txt` to view the full list of dependencies used.

Some of the main dependencies used are:
1. PRAW - Python Reddit API Wrapper
2. Spotipy - Python Spotify API Wrapper
3. MongoDB + PyMongo - To store track and playlist data
4. PyMODM - ODM/ORM-like layer above PyMongo

In order to run this script, the username, password, app client_id, and app client_secret need to be set in a separate `praw.ini` config file.

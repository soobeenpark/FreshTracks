from pymodm import connect, MongoModel, fields
import pymongo
from pymongo import IndexModel

connect("mongodb://localhost:27017/FreshTracks", alias="FreshTracks")

class Post(MongoModel):
    reddit_post_id = fields.CharField(required=True, primary_key=True)
    subreddit = fields.CharField()
    artist = fields.CharField()
    album = fields.CharField()
    album_type = fields.CharField()
    total_tracks = fields.IntegerField()
    spotify_album_uri = fields.CharField()
    track = fields.CharField()
    track_num = fields.IntegerField()
    spotify_track_uri = fields.CharField()
    created_utc = fields.DateTimeField()
    upvotes = fields.IntegerField()
    exists_in_playlist = fields.BooleanField(default=False)
    parsed_artist = fields.CharField()
    parsed_title = fields.CharField()

    class Meta:
        connection_alias = "FreshTracks"
        # Ensure that only one track per same album can exist in each subreddit playlist
        indexes = [
                IndexModel(
                    keys=[("spotify_album_uri", pymongo.ASCENDING),
                          ("subreddit", pymongo.ASCENDING)],
                    unique=True)
                ]


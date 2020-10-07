from pymodm import connect, MongoModel, fields
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

    class Meta:
        connection_alias = "FreshTracks"
        indexes = [
                IndexModel([("spotify_album_uri", 1)], unique=True)
                ]


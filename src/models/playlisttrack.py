from pymodm import connect, MongoModel, fields
from models.post import Post

connect("mongodb://localhost:27017/FreshTracks", alias="FreshTracks")

class PlaylistTrack(MongoModel):
    post = fields.ReferenceField(Post, primary_key=True)
    playlist_position = fields.IntegerField() # Uses zero-indexing

    class Meta:
        connection_alias = "FreshTracks"

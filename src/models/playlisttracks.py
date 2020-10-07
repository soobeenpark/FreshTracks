from pymodm import connect, MongoModel, fields
from models.post import Post

connect("mongodb://localhost:27017/FreshTracks", alias="FreshTracks")

class PlaylistTracks(MongoModel):
    post = fields.ReferenceField(Post)
    playlist_position = fields.IntegerField()

    class Meta:
        connection_alias = "FreshTracks"

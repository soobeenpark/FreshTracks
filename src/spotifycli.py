"""A module for dealing with the Spotify API.

Contains most helper methods used by program that interacts with
Spotify's API.

author: Soobeen Park
file: spotifycli.py
"""

import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials 


def init_spotify_client() -> spotipy.Spotify:
    """Returns instantiated spotipy client.

    Uses Client Credential Flow for authentication.

    NOTE: This function assumes that the following environment vars are set.
        SPOTIPY_CLIENT_ID='your-spotify-client-id'
        SPOTIPY_CLIENT_SECRET='your-spotify-client-secret'
    
    Return:
        spotipy.Spotify: Initialized spotipy client.
    """
    auth_manager = SpotifyClientCredentials()
    spot = spotipy.Spotify(auth_manager=auth_manager)

    return spot


def search(spot, artist, title, type_str) -> json:
    """Search an artist + title combo in Spotify.
    
    Args:
        spot (spotify.Spotify): Initialized Spotify client.
        artist (str): The artist.
        title (str): The song / single / album / EP.
        type_str (str): query param to pass to search's type argument.

    Return:
        json: Spotify search response JSON object on success.
    """
    query_str = title + " artist:" + artist

    result = spot.search(q=query_str, type=type_str, limit=1)

    return result



def populate_from_track(item) -> dict:
    """Populates the info that we care about from a track item to a dict.

    item is a spotify search result item that returned type "track".

    Args:
        item (json): Spotify track search response JSON object.

    Return:
        dict: The populated dict with the fields that are of interest.
    """
    populated = dict()
    populated["artist"] = item["album"]["artists"][0]["name"]
    populated["track"] = item["name"]
    populated["album"] = item["album"]["name"]
    populated["album_type"] = item["album"]["album_type"]
    populated["spotify_album_uri"] = item["album"]["uri"]
    populated["total_tracks"] = item["album"]["total_tracks"]
    populated["track_num"] = item["track_number"]
    populated["spotify_track_uri"] = item["uri"]
    return populated


def populate_from_album(spot, item) -> dict:
    """Populates the info that we care about from an album item to a dict.

    item is a spotify search result item that returned type "album".

    Args:
        spot (spotify.Spotify): Initialized Spotify client.
        item (json): Spotify album search response JSON object.

    Return:
        dict: The populated dict with the fields that are of interest.
    """
    populated = dict()
    populated["artist"] = item["artists"][0]["name"]
    populated["album"] = item["name"]
    populated["album_type"] = item["album_type"]
    populated["spotify_album_uri"] = item["uri"]
    populated["total_tracks"] = item["total_tracks"]

    # Getting a track is a bit more tricky.
    # For the initial fresh posts, the first track is always inserted.
    # Once in the playlist, the script will update the track to the most
    # popular track in the album (according to Spotify's algorithm).
    populated["track_num"] = 1

    # Retreive the first track on the album
    tracks = spot.album_tracks(item["uri"], 1)

    populated["track"] = tracks["items"][0]["name"]
    populated["spotify_track_uri"] = tracks["items"][0]["uri"]
    return populated


if __name__ == "__main__":
    # Example of how to use initialized spotipy client
    print("Running spotifycli.py...")

    spotify = init_spotify_client()
    
    print("Printing all names of albums by James Blake")
    james_blake_uri = "spotify:artist:53KwLdlmrlCelAZMaLVZqU"

    results = spotify.artist_albums(james_blake_uri, album_type='album')
    albums = results['items']
    while results['next']:
        results = spotify.next(results)
        albums.extend(results['items'])

    for album in albums:
        print(album['name'])

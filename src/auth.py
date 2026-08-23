"""
Spotify OAuth authentication.

Uses the Authorization Code flow via spotipy, scoped to read-only access
over the current user's own data - the only data surface Development Mode
still exposes as of 2026 (see NOTES_ON_API_ACCESS.md).
"""

import os

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Scopes needed for everything this project reads. Keep this minimal and
# read-only - we never write to the user's account.
SCOPES = " ".join(
    [
        "user-top-read",
        "user-library-read",
        "playlist-read-private",
    ]
)


def get_spotify_client() -> spotipy.Spotify:
    """Return an authenticated spotipy client for the current user.

    Reads credentials from environment variables (populated via .env):
    SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI.
    Opens a browser window for the one-time OAuth consent, then caches
    the token locally (see .cache in .gitignore).
    """
    load_dotenv()

    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET. "
            "Copy .env.example to .env and fill in your app credentials, "
            "or run with --sample to use synthetic demo data instead."
        )

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPES,
        cache_path=".cache",
    )

    return spotipy.Spotify(auth_manager=auth_manager)

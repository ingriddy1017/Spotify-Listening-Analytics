"""
Fetch the current user's data from the Spotify Web API and shape it into
pandas DataFrames. Each function hits one endpoint family, so if Spotify
adds/removes access to a given endpoint, only that function is affected.

Field access throughout uses .get() with fallbacks rather than direct
indexing (playlist["tracks"]["total"], etc.) - Spotify has changed response
shapes and dropped fields more than once in 2025-2026 (see
NOTES_ON_API_ACCESS.md), and a missing field here shouldn't crash the whole
pipeline.
"""

import time
from typing import Optional

import pandas as pd
import requests

TOP_ARTIST_TIME_RANGES = ("short_term", "medium_term", "long_term")
LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"


def _first_artist_name(track: dict) -> str:
    artists = track.get("artists") or []
    return artists[0].get("name", "unknown") if artists else "unknown"


def _first_artist_id(track: dict):
    artists = track.get("artists") or []
    return artists[0].get("id") if artists else None


def get_top_artists(sp, time_range: str = "medium_term", limit: int = 50) -> pd.DataFrame:
    """Current user's top artists for a single time_range
    (short_term/medium_term/long_term). See get_top_artists_all_ranges for
    combined coverage across all three."""
    results = sp.current_user_top_artists(limit=limit, time_range=time_range)
    rows = []
    for rank, artist in enumerate(results.get("items", []), start=1):
        genres = artist.get("genres") or ["unknown"]
        rows.append(
            {
                "rank": rank,
                "artist_id": artist.get("id"),
                "artist_name": artist.get("name", "unknown"),
                "genres": ",".join(genres),
                "time_range": time_range,
            }
        )
    return pd.DataFrame(rows)


def get_top_artists_all_ranges(sp, limit: int = 50) -> pd.DataFrame:
    """Top artists across all three time ranges Spotify exposes
    (short/medium/long term), combined into one DataFrame.

    This is the main lever for getting *more* usable data out of an
    account within Development Mode's limits: it's three separate,
    fully-allowed calls rather than one, and each range can surface
    different artists - which meaningfully widens the genre coverage
    used for the saved-tracks analysis, especially now that the batch
    `GET /artists` lookup is blocked (see attach_genres_to_saved_tracks).
    """
    frames = []
    for time_range in TOP_ARTIST_TIME_RANGES:
        try:
            frames.append(get_top_artists(sp, time_range=time_range, limit=limit))
        except Exception as exc:  # noqa: BLE001 - one range failing shouldn't lose the others
            print(f"Warning: could not fetch top artists for {time_range} ({exc}).")
    if not frames:
        return pd.DataFrame(columns=["rank", "artist_id", "artist_name", "genres", "time_range"])
    return pd.concat(frames, ignore_index=True)


def get_top_tracks(sp, time_range: str = "medium_term", limit: int = 50) -> pd.DataFrame:
    """Current user's top tracks."""
    results = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    rows = []
    for rank, track in enumerate(results.get("items", []), start=1):
        album = track.get("album") or {}
        rows.append(
            {
                "rank": rank,
                "track_id": track.get("id"),
                "track_name": track.get("name", "unknown"),
                "artist_name": _first_artist_name(track),
                "album_name": album.get("name", "unknown"),
                "release_date": album.get("release_date"),
            }
        )
    return pd.DataFrame(rows)


def get_saved_tracks(sp, max_tracks: Optional[int] = None) -> pd.DataFrame:
    """Current user's saved ("liked") tracks, paginated, with the date each
    was added - this is what powers the diversity-over-time analysis.

    max_tracks=None (the default) pulls your entire library. Pass a number
    to cap it (useful for a quick test run on a large library).
    """
    rows = []
    limit = 50
    offset = 0
    while True:
        page = sp.current_user_saved_tracks(limit=limit, offset=offset)
        items = page.get("items", [])
        if not items:
            break
        for item in items:
            track = item.get("track") or {}
            rows.append(
                {
                    "added_at": item.get("added_at"),
                    "track_id": track.get("id"),
                    "track_name": track.get("name", "unknown"),
                    "artist_id": _first_artist_id(track),
                    "artist_name": _first_artist_name(track),
                }
            )
        offset += limit
        if max_tracks is not None and offset >= max_tracks:
            break
        if page.get("next") is None:
            break
    return pd.DataFrame(rows)


def get_playlists(sp, limit: int = 50) -> pd.DataFrame:
    """Current user's own playlists (metadata only).

    Track count is read defensively: Spotify's Development Mode response
    has dropped/renamed fields like this before, so a missing "tracks" key
    (or a missing "total" inside it) falls back to None rather than
    crashing the whole fetch.
    """
    results = sp.current_user_playlists(limit=limit)
    rows = []
    for playlist in results.get("items", []):
        tracks_field = playlist.get("tracks") or {}
        track_count = tracks_field.get("total") if isinstance(tracks_field, dict) else None
        rows.append(
            {
                "playlist_id": playlist.get("id"),
                "playlist_name": playlist.get("name", "unknown"),
                "track_count": track_count,
                "public": playlist.get("public"),
            }
        )
    return pd.DataFrame(rows)


def _lastfm_top_genre(artist_name: str, api_key: str, timeout: int = 5) -> Optional[str]:
    """Look up an artist's top user-generated tag on Last.fm and return it
    as a lowercase genre string, or None if nothing usable comes back.

    Last.fm's API is free for individual/non-commercial use (no business
    registration or MAU minimum, unlike Spotify's Extended Quota Mode) -
    see README.md for how to get a key.
    """
    params = {
        "method": "artist.gettoptags",
        "artist": artist_name,
        "api_key": api_key,
        "format": "json",
    }
    try:
        resp = requests.get(LASTFM_API_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception:  # noqa: BLE001 - a single failed lookup shouldn't stop the rest
        return None

    tags = (data.get("toptags") or {}).get("tag") or []
    if not tags:
        return None
    top_tag = tags[0].get("name")
    return top_tag.lower() if top_tag else None


def _enrich_missing_genres_via_lastfm(
    df: pd.DataFrame, artists_genre_map: dict, api_key: str, rate_limit_seconds: float = 0.2
) -> None:
    """Mutates artists_genre_map in place, filling in a genre (via Last.fm)
    for any artist_id that's still missing after the Spotify-based lookups.
    Caches by artist name so repeated artists cost one API call, not one
    per track."""
    missing = df[["artist_id", "artist_name"]].drop_duplicates()
    missing = missing[~missing["artist_id"].isin(artists_genre_map.keys())]
    if missing.empty:
        return

    name_cache: dict = {}
    found, not_found = 0, 0
    for row in missing.itertuples():
        name = row.artist_name
        if name not in name_cache:
            name_cache[name] = _lastfm_top_genre(name, api_key)
            time.sleep(rate_limit_seconds)  # be polite to Last.fm's free tier
        genre = name_cache[name]
        if genre:
            artists_genre_map[row.artist_id] = [genre]
            found += 1
        else:
            not_found += 1

    print(f"Last.fm genre enrichment: filled in {found} artist(s), {not_found} had no usable tag.")


def attach_genres_to_saved_tracks(
    sp, saved_tracks_df: pd.DataFrame, artists_genre_map: dict, lastfm_api_key: Optional[str] = None
) -> pd.DataFrame:
    """Add a `genres` column to saved tracks. Tries, in order:
      1. artists_genre_map (pre-seeded from your top-artists pull - free)
      2. Spotify's batch GET /artists (may be 403 in Development Mode as of
         Spotify's 2026 changes - skipped automatically if so)
      3. Last.fm's artist.getTopTags, if lastfm_api_key is provided (see
         README.md for how to get a free key)
      4. "unknown", if none of the above found anything

    Each stage only runs for artists still missing after the previous one,
    and a failure at any stage falls through to the next rather than
    crashing the pipeline.
    """
    df = saved_tracks_df.copy()
    missing_ids = [aid for aid in df["artist_id"].dropna().unique() if aid not in artists_genre_map]

    lookup_failed = False
    for i in range(0, len(missing_ids), 50):
        if lookup_failed:
            break
        batch = missing_ids[i : i + 50]
        try:
            artists = sp.artists(batch).get("artists", [])
        except Exception as exc:  # noqa: BLE001 - endpoint may be 403 in Dev Mode
            print(
                f"Warning: batch artist lookup unavailable ({exc}). "
                "Falling back to Last.fm (if configured) or 'unknown'."
            )
            lookup_failed = True
            break
        for artist in artists:
            if artist and artist.get("id"):
                artists_genre_map[artist["id"]] = artist.get("genres") or ["unknown"]

    if lastfm_api_key:
        _enrich_missing_genres_via_lastfm(df, artists_genre_map, lastfm_api_key)

    df["genres"] = df["artist_id"].map(lambda aid: ",".join(artists_genre_map.get(aid, ["unknown"])))
    return df


def build_artist_genre_map(top_artists_df: pd.DataFrame) -> dict:
    """artist_id -> [genres] lookup, seeded from the top-artists pull to
    minimize extra API calls. Safe to build from a multi-time-range
    DataFrame (get_top_artists_all_ranges) - duplicate artist_ids across
    ranges just overwrite with the same genres."""
    return {
        row.artist_id: row.genres.split(",") if row.genres else ["unknown"]
        for row in top_artists_df.itertuples()
        if pd.notna(row.artist_id)
    }


def save_all(
    sp,
    data_dir: str = "data",
    max_tracks: Optional[int] = None,
    lastfm_api_key: Optional[str] = None,
) -> dict:
    """Fetch everything this project needs and write it to CSVs in data_dir.
    Returns the DataFrames for immediate use as well. Each source is fetched
    independently and wrapped so one failing endpoint doesn't take down the
    others - failures print a warning and fall back to an empty DataFrame
    with the expected columns.

    max_tracks: cap on saved tracks fetched (None = your whole library).
    lastfm_api_key: optional, enables genre fallback via Last.fm for
    artists Spotify's endpoints won't give genres for.
    """

    def _safe(label, fn, empty_columns):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - deliberately broad: keep pipeline alive
            print(f"Warning: could not fetch {label} ({exc}). Continuing without it.")
            return pd.DataFrame(columns=empty_columns)

    top_artists = _safe(
        "top artists",
        lambda: get_top_artists_all_ranges(sp),
        ["rank", "artist_id", "artist_name", "genres", "time_range"],
    )
    top_tracks = _safe(
        "top tracks",
        lambda: get_top_tracks(sp),
        ["rank", "track_id", "track_name", "artist_name", "album_name", "release_date"],
    )
    saved_tracks = _safe(
        "saved tracks",
        lambda: get_saved_tracks(sp, max_tracks=max_tracks),
        ["added_at", "track_id", "track_name", "artist_id", "artist_name"],
    )
    playlists = _safe(
        "playlists", lambda: get_playlists(sp), ["playlist_id", "playlist_name", "track_count", "public"]
    )

    if not saved_tracks.empty:
        genre_map = build_artist_genre_map(top_artists) if not top_artists.empty else {}
        try:
            saved_tracks = attach_genres_to_saved_tracks(
                sp, saved_tracks, genre_map, lastfm_api_key=lastfm_api_key
            )
        except Exception as exc:  # noqa: BLE001 - keep pipeline alive on any genre-lookup failure
            print(f"Warning: genre attachment failed entirely ({exc}). Using 'unknown' for all genres.")
            saved_tracks["genres"] = "unknown"
    else:
        saved_tracks["genres"] = []

    top_artists.to_csv(f"{data_dir}/top_artists.csv", index=False)
    top_tracks.to_csv(f"{data_dir}/top_tracks.csv", index=False)
    saved_tracks.to_csv(f"{data_dir}/saved_tracks.csv", index=False)
    playlists.to_csv(f"{data_dir}/playlists.csv", index=False)

    return {
        "top_artists": top_artists,
        "top_tracks": top_tracks,
        "saved_tracks": saved_tracks,
        "playlists": playlists,
    }

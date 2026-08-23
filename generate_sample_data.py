"""
Generates synthetic listening data shaped exactly like what src/fetch_data.py
would pull from the real Spotify API, so the analysis/visualization pipeline
can be demoed without Spotify credentials.

Run: python generate_sample_data.py
"""

import os
import random

import numpy as np
import pandas as pd

random.seed(7)
np.random.seed(7)

GENRE_POOL = [
    "indie pop",
    "alt rock",
    "hip hop",
    "r&b",
    "electropop",
    "jazz",
    "classical",
    "folk",
    "house",
    "k-pop",
]

# Skewed genre weights so the synthetic HHI is realistic (not perfectly even)
GENRE_WEIGHTS = [0.28, 0.18, 0.14, 0.10, 0.08, 0.06, 0.05, 0.05, 0.04, 0.02]

ARTIST_POOL = [f"Artist {chr(65 + i)}" for i in range(30)]
ARTIST_GENRE = {artist: random.choices(GENRE_POOL, weights=GENRE_WEIGHTS)[0] for artist in ARTIST_POOL}


def make_top_artists(n=50) -> pd.DataFrame:
    chosen = random.choices(ARTIST_POOL, k=n)
    rows = [
        {
            "rank": i + 1,
            "artist_id": f"synthetic_artist_{ARTIST_POOL.index(a)}",
            "artist_name": a,
            "genres": ARTIST_GENRE[a],
        }
        for i, a in enumerate(chosen)
    ]
    return pd.DataFrame(rows)


def make_top_tracks(n=50) -> pd.DataFrame:
    rows = []
    for i in range(n):
        artist = random.choice(ARTIST_POOL)
        rows.append(
            {
                "rank": i + 1,
                "track_id": f"synthetic_track_{i}",
                "track_name": f"Track {i + 1}",
                "artist_name": artist,
                "album_name": f"Album {random.randint(1, 12)}",
                "release_date": f"{random.randint(2016, 2026)}-{random.randint(1,12):02d}-01",
            }
        )
    return pd.DataFrame(rows)


def make_saved_tracks(n=400) -> pd.DataFrame:
    rows = []
    # Simulate genre taste gradually diversifying over ~18 months
    start = pd.Timestamp("2025-02-01")
    for i in range(n):
        days_offset = int(np.random.beta(2, 1.3) * 545)  # skew toward more-recent adds
        added_at = start + pd.Timedelta(days=days_offset)
        month_index = days_offset // 30
        # widen the effective genre pool over time to simulate diversification
        pool_width = min(len(GENRE_POOL), 4 + month_index // 2)
        weights = GENRE_WEIGHTS[:pool_width]
        weights = [w / sum(weights) for w in weights]
        genre = random.choices(GENRE_POOL[:pool_width], weights=weights)[0]
        candidates = [a for a, g in ARTIST_GENRE.items() if g == genre] or ARTIST_POOL
        artist = random.choice(candidates)
        rows.append(
            {
                "added_at": added_at.isoformat() + "Z",
                "track_id": f"synthetic_saved_{i}",
                "track_name": f"Saved Track {i}",
                "artist_id": f"synthetic_artist_{ARTIST_POOL.index(artist)}",
                "artist_name": artist,
                "genres": genre,
            }
        )
    return pd.DataFrame(rows).sort_values("added_at").reset_index(drop=True)


def make_playlists(n=8) -> pd.DataFrame:
    rows = [
        {
            "playlist_id": f"synthetic_playlist_{i}",
            "playlist_name": f"Playlist {i + 1}",
            "track_count": random.randint(10, 120),
            "public": random.choice([True, False]),
        }
        for i in range(n)
    ]
    return pd.DataFrame(rows)


def main(data_dir="data"):
    os.makedirs(data_dir, exist_ok=True)
    make_top_artists().to_csv(f"{data_dir}/top_artists.csv", index=False)
    make_top_tracks().to_csv(f"{data_dir}/top_tracks.csv", index=False)
    make_saved_tracks().to_csv(f"{data_dir}/saved_tracks.csv", index=False)
    make_playlists().to_csv(f"{data_dir}/playlists.csv", index=False)
    print(f"Synthetic demo data written to {data_dir}/")


if __name__ == "__main__":
    main()

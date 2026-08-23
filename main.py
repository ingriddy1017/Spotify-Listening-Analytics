"""
Spotify Listening Analytics - main pipeline.

Usage:
    python main.py                     # fetches your whole library via the Spotify API
    python main.py --sample            # uses synthetic demo data (no credentials needed)
    python main.py --max-tracks 200    # cap how many saved tracks to pull (real data only)

Optional: set LASTFM_API_KEY in your .env to fill in genres for artists
Spotify's API won't give genres for (see README.md).
"""

import argparse
import os

import pandas as pd

from src import analysis, visualize

DATA_DIR = "data"
FIGURES_DIR = "outputs/figures"


def load_data(use_sample: bool, max_tracks: int | None) -> dict:
    if use_sample:
        if not os.path.exists(f"{DATA_DIR}/saved_tracks.csv"):
            print("No sample data found - generating it now...")
            import generate_sample_data

            generate_sample_data.main(DATA_DIR)
    else:
        from src.auth import get_spotify_client
        from src.fetch_data import save_all

        print("Authenticating with Spotify (a browser window will open)...")
        sp = get_spotify_client()

        # get_spotify_client() loads .env, so LASTFM_API_KEY (if set) is
        # available here too - genre enrichment is skipped if it's unset.
        lastfm_api_key = os.getenv("LASTFM_API_KEY") or None

        print("Fetching your listening data...")
        save_all(sp, DATA_DIR, max_tracks=max_tracks, lastfm_api_key=lastfm_api_key)

    return {
        "top_artists": pd.read_csv(f"{DATA_DIR}/top_artists.csv"),
        "top_tracks": pd.read_csv(f"{DATA_DIR}/top_tracks.csv"),
        "saved_tracks": pd.read_csv(f"{DATA_DIR}/saved_tracks.csv"),
        "playlists": pd.read_csv(f"{DATA_DIR}/playlists.csv"),
    }


def run(use_sample: bool, max_tracks: int | None):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    data = load_data(use_sample, max_tracks)
    saved_tracks = data["saved_tracks"]

    # --- Genre concentration (HHI) ---
    hhi, shares = analysis.genre_hhi(saved_tracks)
    print(f"\nGenre HHI: {hhi:,.0f}  ({analysis.interpret_hhi(hhi)})")
    visualize.plot_genre_shares(shares, hhi, f"{FIGURES_DIR}/genre_concentration.png")

    # --- Diversity trend over time ---
    trend = analysis.diversity_trend(saved_tracks)
    visualize.plot_diversity_trend(trend, f"{FIGURES_DIR}/diversity_trend.png")
    if len(trend) >= 2:
        change = trend["shannon_diversity"].iloc[-1] - trend["shannon_diversity"].iloc[0]
        direction = "broadened" if change > 0 else "narrowed"
        print(f"Listening diversity has {direction} by {abs(change):.2f} (Shannon index) since your first month.")

    # --- Artist frequency / concentration ---
    freq = analysis.artist_frequency(saved_tracks)
    visualize.plot_artist_frequency(freq, f"{FIGURES_DIR}/artist_frequency.png")
    top10_share = analysis.top_n_concentration(saved_tracks, n=10)
    print(f"Your top 10 artists account for {top10_share:.0%} of your saved-track library.")

    print(f"\nCharts saved to {FIGURES_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spotify Listening Analytics pipeline")
    parser.add_argument(
        "--sample", action="store_true", help="Use synthetic demo data instead of the real Spotify API"
    )
    parser.add_argument(
        "--max-tracks",
        type=int,
        default=None,
        help="Cap the number of saved tracks fetched (default: your whole library). Ignored with --sample.",
    )
    args = parser.parse_args()
    run(use_sample=args.sample, max_tracks=args.max_tracks)

import pandas as pd
import pytest

from src import analysis


def make_saved_tracks(genre_sequence, start="2025-01-01"):
    """Helper: build a minimal saved_tracks-shaped DataFrame from a list of
    genre strings, one per synthetic track, spaced a day apart."""
    dates = pd.date_range(start, periods=len(genre_sequence), freq="D")
    return pd.DataFrame(
        {
            "added_at": dates.astype(str),
            "track_id": [f"t{i}" for i in range(len(genre_sequence))],
            "track_name": [f"Track {i}" for i in range(len(genre_sequence))],
            "artist_id": [f"a{i % 3}" for i in range(len(genre_sequence))],
            "artist_name": [f"Artist {i % 3}" for i in range(len(genre_sequence))],
            "genres": genre_sequence,
        }
    )


def test_hhi_single_genre_is_max_concentration():
    df = make_saved_tracks(["pop"] * 10)
    hhi, shares = analysis.genre_hhi(df)
    assert hhi == pytest.approx(10000.0)
    assert shares["pop"] == 1.0


def test_hhi_even_split_is_lower_than_concentrated():
    concentrated = make_saved_tracks(["pop"] * 9 + ["jazz"])
    even = make_saved_tracks(["pop", "jazz", "rock", "folk"] * 3)

    hhi_concentrated, _ = analysis.genre_hhi(concentrated)
    hhi_even, _ = analysis.genre_hhi(even)

    assert hhi_concentrated > hhi_even


def test_interpret_hhi_bands():
    assert "diversified" in analysis.interpret_hhi(1000)
    assert "moderately" in analysis.interpret_hhi(2000)
    assert "highly concentrated" in analysis.interpret_hhi(5000)


def test_artist_frequency_counts_and_shares_sum_to_one_over_full_set():
    df = make_saved_tracks(["pop"] * 9)  # 3 artists, 3 tracks each (see helper)
    freq = analysis.artist_frequency(df, top_n=3)
    assert freq["track_count"].sum() == 9
    assert freq["share"].sum() == pytest.approx(1.0)


def test_top_n_concentration_bounds():
    df = make_saved_tracks(["pop"] * 9)
    share = analysis.top_n_concentration(df, n=10)  # n > number of artists
    assert share == pytest.approx(1.0)


def test_diversity_trend_has_one_row_per_month_present():
    # Two tracks in Jan, two in Feb
    df = make_saved_tracks(["pop", "jazz"], start="2025-01-15")
    df2 = make_saved_tracks(["pop", "jazz"], start="2025-02-15")
    combined = pd.concat([df, df2], ignore_index=True)

    trend = analysis.diversity_trend(combined)
    assert len(trend) == 2
    assert set(trend["n_tracks"]) == {2}

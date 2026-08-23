"""
Analysis functions applied to the fetched listening data.

Two economics-style metrics anchor this project:
  - Herfindahl-Hirschman Index (HHI): concentration of listening across genres
  - Shannon diversity index: how that concentration changes over time
"""

import numpy as np
import pandas as pd


def _genre_shares(df: pd.DataFrame, genre_col: str = "genres") -> pd.Series:
    """Explode a comma-separated genre column into individual genre counts,
    then normalize to shares that sum to 1."""
    exploded = df[genre_col].fillna("unknown").str.split(",").explode().str.strip()
    exploded = exploded.replace("", "unknown")
    counts = exploded.value_counts()
    return counts / counts.sum()


def genre_hhi(df: pd.DataFrame, genre_col: str = "genres") -> tuple[float, pd.Series]:
    """Herfindahl-Hirschman Index of genre concentration, scaled 0-10000
    (matching the convention used in antitrust/market-structure analysis).

    Returns (hhi, genre_shares) so callers can also plot the underlying
    distribution.
    """
    shares = _genre_shares(df, genre_col)
    hhi = float((shares**2).sum() * 10000)
    return hhi, shares


def interpret_hhi(hhi: float) -> str:
    """Rough qualitative read of an HHI score, using the same bands the
    U.S. DOJ/FTC use for market concentration."""
    if hhi < 1500:
        return "unconcentrated / highly diversified listening"
    if hhi < 2500:
        return "moderately concentrated listening"
    return "highly concentrated listening (a few genres dominate)"


def diversity_trend(saved_tracks_df: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    """Shannon diversity index of genre mix per time bucket (default:
    calendar month), based on when tracks were added to the library.

    H = -sum(p_i * ln(p_i)) over genre shares within each bucket.
    Higher H = more evenly spread across genres that period.
    """
    df = saved_tracks_df.copy()
    df["added_at"] = pd.to_datetime(df["added_at"], utc=True).dt.tz_localize(None)
    df["period"] = df["added_at"].dt.to_period(freq).dt.to_timestamp()

    records = []
    for period, group in df.groupby("period"):
        shares = _genre_shares(group)
        shannon_h = float(-(shares * np.log(shares)).sum())
        records.append({"period": period, "shannon_diversity": shannon_h, "n_tracks": len(group)})

    return pd.DataFrame(records).sort_values("period").reset_index(drop=True)


def artist_frequency(saved_tracks_df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Top-N artists by saved-track count, plus each artist's share of the
    total library - a quick read on how concentrated your library is by
    artist rather than genre."""
    counts = saved_tracks_df["artist_name"].value_counts()
    shares = counts / counts.sum()
    df = pd.DataFrame({"artist_name": counts.index, "track_count": counts.values, "share": shares.values})
    return df.head(top_n)


def top_n_concentration(saved_tracks_df: pd.DataFrame, n: int = 10) -> float:
    """Share of your total saved-track library accounted for by your top-N
    artists - a long-tail concentration check, same idea as top-10 holdings
    weight in a portfolio."""
    counts = saved_tracks_df["artist_name"].value_counts()
    total = counts.sum()
    return float(counts.head(n).sum() / total) if total else 0.0

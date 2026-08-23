"""
Chart functions. Each one builds a figure and saves it to outputs/figures/,
and also returns the Figure object so app_streamlit.py can render it inline.
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")


def plot_genre_shares(shares: pd.Series, hhi: float, out_path: str, top_n: int = 12):
    top = shares.sort_values(ascending=False).head(top_n)

    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(x=top.values * 100, y=top.index, ax=ax, palette="viridis", hue=top.index, legend=False)
    ax.set_xlabel("Share of listening (%)")
    ax.set_ylabel("Genre")
    ax.set_title(f"Genre concentration  —  HHI = {hhi:,.0f}")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    return fig


def plot_diversity_trend(trend_df: pd.DataFrame, out_path: str):
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.lineplot(data=trend_df, x="period", y="shannon_diversity", marker="o", ax=ax)
    ax.set_xlabel("Month")
    ax.set_ylabel("Shannon diversity index (genres)")
    ax.set_title("Listening diversity over time")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    return fig


def plot_artist_frequency(freq_df: pd.DataFrame, out_path: str):
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(
        x="track_count", y="artist_name", data=freq_df, ax=ax, palette="mako", hue="artist_name", legend=False
    )
    ax.set_xlabel("Saved tracks")
    ax.set_ylabel("Artist")
    ax.set_title("Most-saved artists in your library")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    return fig

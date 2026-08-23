"""
Optional interactive dashboard for the Spotify Listening Analytics project.

Run:
    streamlit run app_streamlit.py

Expects data/*.csv to already exist - run `python main.py` (or `python
main.py --sample`) first to generate them.
"""

import os

import pandas as pd
import streamlit as st

from src import analysis, visualize

DATA_DIR = "data"

st.set_page_config(page_title="Spotify Listening Analytics", layout="wide")
st.title("🎧 Spotify Listening Analytics")

if not os.path.exists(f"{DATA_DIR}/saved_tracks.csv"):
    st.warning(
        "No data found yet. Run `python main.py` (for your real Spotify data) "
        "or `python main.py --sample` (for synthetic demo data) first."
    )
    st.stop()

saved_tracks = pd.read_csv(f"{DATA_DIR}/saved_tracks.csv")

col1, col2, col3 = st.columns(3)

hhi, shares = analysis.genre_hhi(saved_tracks)
col1.metric("Genre HHI", f"{hhi:,.0f}", analysis.interpret_hhi(hhi))

top10_share = analysis.top_n_concentration(saved_tracks, n=10)
col2.metric("Top-10 artist share", f"{top10_share:.0%}")

col3.metric("Saved tracks analyzed", f"{len(saved_tracks):,}")

st.subheader("Genre concentration")
fig1 = visualize.plot_genre_shares(shares, hhi, "outputs/figures/genre_concentration.png")
st.pyplot(fig1)

st.subheader("Diversity over time")
trend = analysis.diversity_trend(saved_tracks)
fig2 = visualize.plot_diversity_trend(trend, "outputs/figures/diversity_trend.png")
st.pyplot(fig2)

st.subheader("Most-saved artists")
freq = analysis.artist_frequency(saved_tracks)
fig3 = visualize.plot_artist_frequency(freq, "outputs/figures/artist_frequency.png")
st.pyplot(fig3)

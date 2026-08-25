# Spotify Listening Analytics

A personal-data analytics project built on the Spotify Web API. It pulls your
own top artists, top tracks, and saved-track library, then applies market-style
concentration and diversity metrics to your listening habits — the same
techniques used to analyze portfolio concentration or market share, applied to
a dataset anyone with a Spotify account can access.

## What it does

- **Authenticates** with your personal Spotify account (OAuth, Development Mode)
- **Fetches** your top artists/tracks, saved tracks, and playlists via `spotipy`
- **Computes**:
  - A **Herfindahl-Hirschman Index (HHI)** on your genre mix — a standard
    economics/finance concentration metric, applied here to measure how
    concentrated vs. diversified your listening is
  - A **Shannon diversity trend** of your genre mix over time, using the date
    each track was saved
  - **Artist frequency distribution** (top-N share of your listening)
- **Visualizes** all of the above and saves the charts as PNGs
- Optional **Streamlit dashboard** (`app_streamlit.py`) for an interactive view

## Why this project (and not the "usual" Spotify project)

As of 2026, Spotify has significantly restricted the Web API for individual
developers (Development Mode): audio features (danceability/energy/valence),
recommendations, related artists, and other users' data are no longer
available. This project is scoped to work entirely within what Development
Mode still exposes — **your own account's data** — which is why it leans on
genre/frequency/time-based analysis rather than audio-feature clustering.
See `NOTES_ON_API_ACCESS.md` for details and sources.

## Repo structure

```
spotify-listening-analytics/
├── README.md
├── NOTES_ON_API_ACCESS.md
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py                    # orchestrates fetch -> analyze -> visualize
├── generate_sample_data.py    # creates synthetic demo data (no API needed)
├── app_streamlit.py           # optional interactive dashboard
├── src/
│   ├── auth.py                 # Spotify OAuth client
│   ├── fetch_data.py           # API calls -> pandas DataFrames -> CSV
│   ├── analysis.py             # HHI, diversity trend, artist frequency
│   └── visualize.py            # matplotlib/seaborn chart functions
├── tests/
│   └── test_analysis.py        # unit tests for the analysis math
├── data/                       # CSVs (gitignored except .gitkeep)
└── outputs/figures/            # generated PNG charts
```

## Setup

1. Create a Spotify Developer app at https://developer.spotify.com/dashboard
   (Development Mode is fine — just add yourself as a user, and note the
   app owner needs an active Premium subscription per current Spotify rules).
2. Add `http://127.0.0.1:3000` as a Redirect URI in your app settings.
3. Clone this repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your `SPOTIPY_CLIENT_ID` /
   `SPOTIPY_CLIENT_SECRET`.
5. (Optional but recommended) Get a free Last.fm API key at
   https://www.last.fm/api/account/create — no business registration or
   user-count minimum, unlike Spotify's Extended Quota Mode — and add it
   as `LASTFM_API_KEY` in `.env`. Spotify's batch artist-lookup endpoint
   (used to get genres) is restricted in Development Mode as of 2026; this
   fills in genres for those artists via Last.fm's tag data instead.
6. Run the pipeline:
   ```bash
   python main.py
   ```
   Your browser will open once for Spotify login/consent, then the script
   fetches your data, runs the analysis, and writes charts to
   `outputs/figures/`. This pulls your entire saved-track library by
   default; to cap it (e.g. for a quick test run), use:
   ```bash
   python main.py --max-tracks 200
   ```

### No Spotify account / just want to see it work?

```bash
python generate_sample_data.py   # writes synthetic CSVs to data/
python main.py --sample          # runs analysis+viz on the synthetic data
```

## Example output

See `outputs/figures/` for sample charts generated from synthetic demo data
(genre concentration bar chart, diversity-over-time line chart, top-artist
frequency chart).

## Methodology notes

**HHI (genre concentration):** for each genre *i* with listening share *s_i*
(0–1), `HHI = 10000 * sum(s_i^2)`. Ranges from near 0 (perfectly diversified)
to 10,000 (single genre). The same formula used in antitrust/market-structure
analysis, e.g. by the U.S. DOJ, applied here to genre share instead of firm
market share.

**Shannon diversity:** `H = -sum(p_i * ln(p_i))` over genre shares per time
bucket (month), tracking whether your listening has broadened or narrowed
over time.

## Tests

Unit tests cover the analysis math (HHI, diversity trend, artist
concentration) against small hand-built DataFrames, independent of the API:

```bash
pytest tests/
```

## Tech stack

Python, spotipy (Spotify Web API client), pandas, matplotlib, seaborn,
python-dotenv, Streamlit (optional dashboard).

## License

MIT — see `LICENSE`.

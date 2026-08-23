# Notes on Spotify Web API access (2026)

This project is deliberately scoped around what an individual developer can
actually access on the Spotify Web API today. Spotify tightened developer
access twice recently:

- **April 2025** — Extended Quota Mode (the tier that lets an app serve more
  than a handful of users) now requires a registered business with an active
  service and 250,000+ monthly active users. Individual/hobby developers are
  not eligible.
- **February–March 2026** — Development Mode (the tier available to
  individuals) was restricted further:
  - App owner must have an active Spotify Premium subscription
  - 1 Client ID per developer, 5 authorized users per app (new apps)
  - Several endpoint families were removed or scoped down, including:
    audio features/analysis, recommendations, related artists, artist top
    tracks, other users' profiles/playlists, featured/category playlists,
    and available markets
  - Search result limits reduced
  - Per-entity save/remove/follow endpoints consolidated into generic
    `/me/library` endpoints

**What's still available in Development Mode** (what this project uses):
your own top artists/tracks (`/me/top/...`), your saved tracks/library
(`/me/tracks`, `/me/library`), your playlists (`/me/playlists`), artist
metadata including genres, and playback endpoints.

## Practical limits we hit building this, and how the code handles them

- **`GET /artists` (batch artist lookup) returns 403 in Development Mode.**
  This project used it to backfill genres for saved tracks whose artist
  wasn't already in your top-artists pull. When it 403s,
  `attach_genres_to_saved_tracks` in `src/fetch_data.py` catches it and
  falls back to Last.fm's `artist.getTopTags` (see README.md setup) rather
  than crashing.
- **No path to more access for an individual/student project.** Extended
  Quota Mode (the tier without these restrictions) has required a
  registered business with 250,000+ monthly active users since May 2025.
  Developers requesting exceptions for educational/personal projects have
  been declined — there's no student or research tier. Development Mode's
  limits are the ceiling for a solo project right now.
- **To get more out of what Development Mode does allow:** `top_artists`
  is fetched across all three of Spotify's time ranges (short/medium/long
  term) via `get_top_artists_all_ranges`, not just one, which widens genre
  coverage without touching a restricted endpoint. `get_saved_tracks`
  pulls your whole library by default (`max_tracks=None`) rather than a
  capped sample.

Sources: Spotify for Developers blog ("Update on Developer Access and
Platform Security," Feb 6 2026; "Updating the Criteria for Web API Extended
Access," Apr 15 2025) and the official February 2026 Web API migration guide
and changelog.

If Spotify changes these rules again, check
`src/fetch_data.py` — each function is isolated per endpoint, so anything
that gets re-enabled (or removed) only affects one function, not the whole
pipeline.

# Bridge Stremio Kodi

Kodi addon that plays streams from one or more stream-only Stremio addons directly in Kodi, no Stremio app required.

## Installing from the Kodi repository

1. In Kodi, go to *Settings → Media → File manager → Add source*, and add:

   ```
   https://jibay442.github.io/bridgiodi/
   ```

2. Go to *Add-ons → Install from zip file*, pick the source you just added, and install `repository.bridgiodi-1.0.0.zip`.
3. Go to *Install from repository → Bridgiodi Repository*, and install **Bridgiodi**.

## Requirements

- At least one personal Stremio manifest URL (`https://<provider>/<id>/manifest.json`) — settings tab **Addons Stremio**, up to 5 slots, priority-ordered.
- A free [TMDB](https://www.themoviedb.org) API key — settings tab **Catalogue (TMDB)**.

> This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

## Features

- Movies/TV/Anime catalogs (Popular, Box office, Top rated, Genre, Year) from TMDB.
- Episode lists from Cinemeta (kept separate from TMDB because stream IDs are IMDb/TVDB-numbered, and TMDB's numbering diverges, especially for anime).
- Multi-provider streams: results grouped by provider, provider #1 always wins ties.
- Quality-based stream sorting (resolution, HDR, Dolby Vision, audio, codec, size) — all criteria off by default, configurable in **Filter**.
- Auto-picked streams are probed before playback; dead links are skipped automatically.
- Local resume, independent of Trakt/TMDb Helper.
- Combined movie+series search with history, and Kodi global-search support.
- Optional original-language audio forcing (overrides a file's own "default" flag, which is often a dub).
- Optional [MDBList](https://mdblist.com) integration: Up Next, watchlist, custom/liked lists, watched-status sync.
- TMDb Helper player integration (for Trakt-backed "continue watching"), registered as two players: **Bridgiodi** plays the best-ranked source straight away, **Bridgiodi (select source)** opens TMDb Helper's own source picker. Both are always available — switch per item with **Select player** in the context menu (the Menu button on a remote).
- For Trakt watched-status/resume sync: install the official **Trakt** addon (`script.trakt`), or use Bridgiodi as the player behind **TMDb Helper**, which has its own Trakt integration.

## Known limitations

- No torrent/magnet (`infoHash`) support — direct HTTP streams only.
- No native Trakt integration (Trakt app creation is VIP-only now) — see above for alternatives.

## Manual install (without the repository)

1. Clone this repo.
2. Copy `plugin.video.bridgiodi/` into your Kodi `addons` folder.
3. Configure at least one manifest URL and your TMDB key in settings.

## Development

- `plugin.video.bridgiodi/` — the addon.
- `repository.bridgiodi/` — the repository pointer addon.
- `.github/workflows/release.yml` — builds and publishes the repo + a GitHub Release on every version bump pushed to `main`.
- `CHANGELOG.md` — bump `addon.xml`'s version and add an entry here to cut a release.

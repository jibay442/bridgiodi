# Bridge Stremio Kodi

Kodi addon that plays streams from one or more stream-only Stremio addons (e.g. [Lumio.tv](https://mylumio.tv)) directly in Kodi, no Stremio app required.

## Kodi repository

Install `repository.bridgiodi` once, then Bridgiodi updates automatically through Kodi's normal update mechanism.

- Repo root: https://jibay442.github.io/Bridgiodi/
- Repository zip: https://jibay442.github.io/Bridgiodi/repository.bridgiodi/repository.bridgiodi-1.0.0.zip

Install via *Add-ons → Install from zip file* with that zip.

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
- TMDb Helper player integration (for Trakt-backed "continue watching").
- `script.trakt` works automatically on top — no Bridgiodi-side config needed.

## Known limitations

- No torrent/magnet (`infoHash`) support — direct HTTP streams only.
- No native Trakt integration (Trakt app creation is VIP-only now); use `script.trakt` instead.
- 5 manifest slots max (Kodi settings can't hold a dynamic list).

## Manual install (without the repository)

1. Clone this repo.
2. Copy `plugin.video.bridgiodi/` into your Kodi `addons` folder.
3. Configure at least one manifest URL and your TMDB key in settings.

## Development

- `plugin.video.bridgiodi/` — the addon.
- `repository.bridgiodi/` — the repository pointer addon.
- `.github/workflows/release.yml` — builds and publishes the repo + a GitHub Release on every version bump pushed to `main`.
- `CHANGELOG.md` — bump `addon.xml`'s version and add an entry here to cut a release.

# Changelog

All notable changes to Bridgiodi are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/). Each version header must
match the `version` attribute in `plugin.video.bridgiodi/addon.xml` exactly -
the release workflow pulls this file's matching section as release notes.

## [1.0.0] - 2026-08-06

### Changed
- Renamed from Lumio to Bridgiodi. Works with any stream-only Stremio addon,
  not just Lumio.tv, which the old name implied.
- Up to 5 Stremio manifest URLs can now be configured (priority-ordered).
  Streams from multiple providers are grouped by provider rather than
  intermixed - provider #1 always outranks the others.
- Stream sort priorities all default to "Not used" instead of a built-in
  Resolution > Dolby Vision > HDR > Size preference.
- MDBList list items now show full TMDB metadata (poster, plot, rating,
  cast) instead of title/year only.

### Added
- Local resume playback (works without a Kodi library entry, Trakt, or
  TMDb Helper).
- Combined movie + series search with inline history, and support for
  Kodi's global search.
- Optional "force original-language audio" setting.
- Optional MDBList integration: Up Next, watchlist, custom/liked lists,
  and watched-status sync.
- "Clear cache" button in settings.
- Auto-picked streams are probed before playback and skipped if dead,
  instead of failing silently on an expired link.

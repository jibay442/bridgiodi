# Changelog

All notable changes to Bridgiodi are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/). Each version header must
match the `version` attribute in `plugin.video.bridgiodi/addon.xml` exactly -
the release workflow pulls this file's matching section as release notes.

## [1.0.1] - 2026-08-22

### Fixed
- Episodes are scrobbled to Trakt again when playing through TMDb Helper.
  An episode's series ids were published under the bare `imdb`/`tmdb` unique
  ids, which is where TMDb Helper's scrobbler reads the EPISODE's own TMDB id:
  the series lookup it derived from that could only miss, and it reports
  nothing it can no longer identify. Movies were unaffected, their ids do
  belong under the bare keys.
- Kodi's "install from zip" browser no longer shows an empty folder when
  navigating the added repository source: each addon's zip folder now carries
  its own index page, and the repository zip is also published flat at the
  root of the Pages site.

### Added
- "Bridgiodi (select source)", a second TMDb Helper player that opens TMDb
  Helper's own source picker instead of playing the best-ranked source. Both
  entries stay available per item under "Select player" in the context menu
  (the Menu button on a remote). Press "Register Bridgiodi in TMDb Helper"
  again to write it.
- "Show original-language titles" setting: catalogue and search lists label
  items with TMDB's original title. Info screens already showed both.
- "Romanize non-Latin titles" setting (on by default, alongside the above):
  transliterates Japanese, Chinese, Korean, Cyrillic, Greek and Arabic titles
  rather than leaving the skin's font to draw missing-glyph boxes. Kanji come
  out with their Chinese reading, a limitation of the approach.
- Short quality badges in the stream list (4K, HDR10+, DV, ATMOS, 7.1,
  HEVC...), built from the same detectors the quality sort reacts to.

### Changed
- Quality badges and file size now come first in the stream label. Kodi
  truncates a long release filename with "...", which was silently hiding
  them at the end.

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

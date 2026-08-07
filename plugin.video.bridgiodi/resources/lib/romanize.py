# -*- coding: utf-8 -*-
"""Best-effort Unicode -> Latin transliteration for original-language titles.

Uses the vendored text_unidecode (Artistic License - MIT-compatible)
instead of the GPL-licensed "Unidecode" package this addon's own MIT
license can't absorb. Handles Cyrillic, Greek, Korean, Chinese and
Japanese kana reasonably well; Japanese kanji come out with their
Chinese reading rather than true romaji, since CJK ideographs share
Unicode code points across languages and this library has no per-language
reading dictionary - a known limitation of this whole approach, not a bug.
"""
try:
	from .vendor.text_unidecode import unidecode as _unidecode
except Exception:
	_unidecode = None


def romanize(text):
	if not text or not _unidecode:
		return text or ''
	try:
		return _unidecode(text)
	except Exception:
		return text

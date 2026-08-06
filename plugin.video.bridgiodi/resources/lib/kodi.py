# -*- coding: utf-8 -*-
"""Thin wrappers over the Kodi addon API, shared by the library modules."""
import xbmc
import xbmcaddon
import xbmcvfs

ADDON_ID = 'plugin.video.bridgiodi'

# ISO 639-1 codes where TMDB expects a region to actually localise content
# (a bare code silently falls back to English on TMDB's side for these).
_TMDB_REGION = {
	'fr': 'FR', 'es': 'ES', 'de': 'DE', 'it': 'IT', 'pt': 'PT', 'ja': 'JP',
	'ko': 'KR', 'zh': 'CN', 'ru': 'RU', 'nl': 'NL', 'pl': 'PL', 'tr': 'TR',
	'sv': 'SE', 'da': 'DK', 'fi': 'FI', 'nb': 'NO', 'cs': 'CZ', 'el': 'GR',
	'hu': 'HU', 'ro': 'RO', 'th': 'TH', 'ar': 'SA', 'he': 'IL', 'id': 'ID',
	'uk': 'UA', 'vi': 'VN',
}


def tmdb_language():
	"""Kodi's configured GUI language, as a TMDB 'xx-XX' locale.

	Falls back to 'en-US' when Kodi's language can't be read or has no
	known region mapping, since that's TMDB's own effective default.
	"""
	code = (xbmc.getLanguage(xbmc.ISO_639_1) or '').strip().lower()
	region = _TMDB_REGION.get(code)
	return '%s-%s' % (code, region) if region else 'en-US'


def addon():
	# A fresh Addon on every call: the object caches its settings, and the
	# service is long-running - it has to see edits made while it runs.
	return xbmcaddon.Addon(ADDON_ID)


def setting(key):
	return addon().getSetting(key) or ''


def set_setting(key, value):
	addon().setSetting(key, value)


def setting_int(key, default=0):
	try:
		return int(setting(key) or default)
	except ValueError:
		return default


def setting_bool(key):
	return setting(key) == 'true'


def profile_dir():
	path = xbmcvfs.translatePath(addon().getAddonInfo('profile'))
	if not xbmcvfs.exists(path):
		xbmcvfs.mkdirs(path)
	return path

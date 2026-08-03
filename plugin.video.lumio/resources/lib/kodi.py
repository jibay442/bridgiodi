# -*- coding: utf-8 -*-
"""Thin wrappers over the Kodi addon API, shared by the library modules."""
import xbmcaddon
import xbmcvfs

ADDON_ID = 'plugin.video.lumio'


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

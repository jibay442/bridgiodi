# -*- coding: utf-8 -*-
"""
	Registers Bridgiodi as a player for TMDb Helper.

	TMDb Helper only reads player files from its own addon_data directory - it
	does not scan other addons - so the bundled JSON has to be copied there.
	That writes into another addon's data, so it is never done automatically:
	it happens only when the user presses the button in the settings.
"""
import os

import xbmc
import xbmcvfs

from . import kodi

HELPER_ID = 'plugin.video.themoviedb.helper'
PLAYERS_DIR = 'special://profile/addon_data/%s/players/' % HELPER_ID
PLAYER_FILE = 'bridgiodi.json'


def helper_installed():
	return xbmc.getCondVisibility('System.HasAddon(%s)' % HELPER_ID)


def _source_path():
	# Asked of Kodi rather than assembled from special://home/addons: the addon
	# is not guaranteed to live there, and a hardcoded path fails silently.
	base = xbmcvfs.translatePath(kodi.addon().getAddonInfo('path'))
	return os.path.join(base, 'resources', 'players', PLAYER_FILE)


def target_path():
	return xbmcvfs.translatePath(PLAYERS_DIR + PLAYER_FILE)


def install():
	"""Copy the player file into TMDb Helper. Returns the path written."""
	folder = xbmcvfs.translatePath(PLAYERS_DIR)
	if not xbmcvfs.exists(folder):
		xbmcvfs.mkdirs(folder)
	source, target = _source_path(), target_path()
	handle = xbmcvfs.File(source)
	try:
		payload = handle.read()
	finally:
		handle.close()
	if not payload:
		raise IOError('bundled player file is empty or missing: %s' % source)
	# Written rather than xbmcvfs.copy'd so an existing file is replaced
	# cleanly when the definition changes between addon versions.
	out = xbmcvfs.File(target, 'w')
	try:
		out.write(payload)
	finally:
		out.close()
	return target


def is_installed():
	return xbmcvfs.exists(target_path())

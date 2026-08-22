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
# Two player definitions, both pointing here: the plain one plays the
# best-ranked source, the second one lets TMDb Helper's own dialog pick which
# source to play. TMDb Helper has no notion of a per-player option, so a second
# entry in its player list is what a "choose the source" button looks like.
PLAYER_FILES = ('bridgiodi.json', 'bridgiodi_select.json')


def helper_installed():
	return xbmc.getCondVisibility('System.HasAddon(%s)' % HELPER_ID)


def _source_path(player_file):
	# Asked of Kodi rather than assembled from special://home/addons: the addon
	# is not guaranteed to live there, and a hardcoded path fails silently.
	base = xbmcvfs.translatePath(kodi.addon().getAddonInfo('path'))
	return os.path.join(base, 'resources', 'players', player_file)


def target_path(player_file):
	return xbmcvfs.translatePath(PLAYERS_DIR + player_file)


def _install_one(player_file):
	source, target = _source_path(player_file), target_path(player_file)
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


def install():
	"""Copy the player files into TMDb Helper. Returns the folder written to."""
	folder = xbmcvfs.translatePath(PLAYERS_DIR)
	if not xbmcvfs.exists(folder):
		xbmcvfs.mkdirs(folder)
	for player_file in PLAYER_FILES:
		_install_one(player_file)
	return folder


def is_installed():
	return all(xbmcvfs.exists(target_path(player_file)) for player_file in PLAYER_FILES)

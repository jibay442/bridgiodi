# -*- coding: utf-8 -*-
"""
	JSON disk cache, one file per namespace, with a TTL per entry.

	It exists so a second plugin invocation can read back a plot, a poster or
	an IMDb id without another HTTP round trip AND without pushing them through
	the plugin URL - on the resolve hop that URL already carries the full stream
	link plus all the metadata, re-encoded a second time, and Kodi and Kore
	truncate long ones.

	Nothing here is authoritative: losing the file only costs a refetch.
"""
import json
import os
import time

import xbmcvfs

from . import kodi

# TMDB's terms cap cached metadata at 6 months; a week keeps us far inside that
# and still saves the round trips that matter.
DEFAULT_TTL = 7 * 24 * 3600
_MAX_ENTRIES = 300


def _path(namespace):
	return os.path.join(kodi.profile_dir(), 'cache_%s.json' % namespace)


def _load(namespace):
	path = _path(namespace)
	if not xbmcvfs.exists(path):
		return {}
	handle = xbmcvfs.File(path)
	try:
		raw = handle.read()
	finally:
		handle.close()
	try:
		return json.loads(raw) if raw else {}
	except ValueError:
		return {}


def _save(namespace, entries):
	# Write beside the target then move it into place: a half-written cache is
	# indistinguishable from a corrupt one on the next read.
	path = _path(namespace)
	temp = path + '.tmp'
	handle = xbmcvfs.File(temp, 'w')
	try:
		handle.write(json.dumps(entries))
	finally:
		handle.close()
	xbmcvfs.delete(path)
	xbmcvfs.rename(temp, path)


def get(namespace, key, ttl=DEFAULT_TTL):
	entry = _load(namespace).get(str(key))
	if not entry:
		return None
	if ttl and time.time() - entry.get('stamp', 0) > ttl:
		return None
	return entry.get('value')


def all_entries(namespace, ttl=DEFAULT_TTL):
	"""{key: value} for a whole namespace, in one file read.

	Reading key by key would reload the file once per lookup, which matters
	when a catalogue page needs 40 of them.
	"""
	now = time.time()
	return {key: entry.get('value') for key, entry in _load(namespace).items()
	        if not ttl or now - entry.get('stamp', 0) <= ttl}


def clear_all(exclude_namespaces=()):
	"""Deletes every cache_*.json file except the given namespaces.

	Used by the settings "Clear cache" button - excludes namespaces that
	aren't really a cache (e.g. the MDBList auth token: losing that logs the
	user out, which a cache-clearing button shouldn't do as a side effect).
	Returns how many files were actually removed.
	"""
	profile = kodi.profile_dir()
	keep = {'cache_%s.json' % ns for ns in exclude_namespaces}
	_dirs, files = xbmcvfs.listdir(profile)
	removed = 0
	for name in files:
		if name.startswith('cache_') and name.endswith('.json') and name not in keep:
			if xbmcvfs.delete(os.path.join(profile, name)):
				removed += 1
	return removed


def put(namespace, key, value):
	entries = _load(namespace)
	entries[str(key)] = {'stamp': time.time(), 'value': value}
	excess = len(entries) - _MAX_ENTRIES
	if excess > 0:
		# Evicting the oldest is free - it is a cache, not a store.
		for stale in sorted(entries, key=lambda k: entries[k].get('stamp', 0))[:excess]:
			del entries[stale]
	_save(namespace, entries)
	return value

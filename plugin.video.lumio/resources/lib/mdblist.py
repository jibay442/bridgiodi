# -*- coding: utf-8 -*-
"""
	MDBList API client: OAuth device-code auth, Up Next, and watched sync.

	Entirely optional, alongside TMDB/Cinemeta: disabled until the user turns
	it on AND connects an account in settings, never required for the addon's
	core catalogue/stream/playback path.

	Auth uses the OAuth Device Code flow (https://api.mdblist.com/docs/
	authentication/), which is the one meant for TVs/CLIs that can't receive
	a redirect - a good fit for a Kodi addon. The token is stored through the
	existing disk cache with no TTL (ttl=0 means "never expires on its own");
	losing it just means reconnecting, same as losing any other cache entry.
"""
import time
from urllib.parse import urlencode

from . import cache, kodi, net

API = 'https://api.mdblist.com'
SCOPE = 'write'

# A title counts as "watched" past this fraction of its runtime, mirroring
# the convention Trakt/script.trakt use for scrobbling.
WATCHED_THRESHOLD = 0.8

_TOKEN_NAMESPACE = 'mdblist_auth'
_TOKEN_KEY = 'token'


class MdblistError(Exception):
	pass


class NotConnected(MdblistError):
	pass


def _client_id():
	return kodi.setting('mdblist_client_id').strip()


def _token():
	return cache.get(_TOKEN_NAMESPACE, _TOKEN_KEY, ttl=0)


def _save_token(data):
	token = dict(data)
	token['obtained_at'] = time.time()
	cache.put(_TOKEN_NAMESPACE, _TOKEN_KEY, token)
	return token


def is_connected():
	return bool(_token())


def disconnect():
	cache.put(_TOKEN_NAMESPACE, _TOKEN_KEY, None)


# --- device code auth --------------------------------------------------

def start_device_auth():
	"""dict with device_code/user_code/verification_uri/interval/expires_in."""
	client_id = _client_id()
	if not client_id:
		raise MdblistError('no MDBList client id configured')
	data = net.post_form('%s/oauth/device-authorization/' % API,
	                      {'client_id': client_id, 'scope': SCOPE})
	if 'device_code' not in data:
		raise MdblistError(data.get('error_description') or data.get('error') or 'device authorization failed')
	return data


def poll_device_token(device_code, interval, expires_in, wait, cancelled):
	"""Poll the token endpoint until approved, denied, expired, or cancelled.

	wait(seconds) sleeps between polls (a Kodi-abort-aware wait, so the addon
	settings screen isn't stuck if Kodi wants to shut down). cancelled() is
	checked before every wait and should return True to give up early (e.g.
	the user closed the progress dialog).

	Returns the saved token dict, or None if denied/expired/cancelled.
	"""
	client_id = _client_id()
	deadline = time.time() + expires_in
	while time.time() < deadline:
		if cancelled():
			return None
		wait(interval)
		data = net.post_form('%s/oauth/token/' % API, {
			'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
			'device_code': device_code,
			'client_id': client_id,
		})
		error = data.get('error')
		if not error:
			return _save_token(data)
		if error == 'authorization_pending':
			continue
		if error == 'slow_down':
			interval += 5
			continue
		if error == 'access_denied':
			return None
		raise MdblistError(data.get('error_description') or error)
	return None


def _refresh(token):
	client_id = _client_id()
	if not client_id or not token.get('refresh_token'):
		return None
	data = net.post_form('%s/oauth/token/' % API, {
		'grant_type': 'refresh_token',
		'refresh_token': token['refresh_token'],
		'client_id': client_id,
	})
	if 'access_token' not in data:
		return None
	return _save_token(data)


def _access_token():
	token = _token()
	if not token:
		raise NotConnected('MDBList account not connected')
	obtained_at = token.get('obtained_at', 0)
	expires_in = token.get('expires_in', 0)
	# Refresh a little early rather than exactly at expiry, so a slow request
	# doesn't straddle the boundary and get a 401 mid-flight.
	if expires_in and time.time() > obtained_at + expires_in - 60:
		refreshed = _refresh(token)
		if not refreshed:
			disconnect()
			raise NotConnected('MDBList session expired, reconnect in settings')
		return refreshed['access_token']
	return token['access_token']


def _headers():
	return {'Authorization': 'Bearer %s' % _access_token()}


# --- API calls -----------------------------------------------------------

def get_user():
	return net.get_json('%s/user' % API, headers=_headers())


def get_upnext(limit=25):
	"""In-progress shows with their next unwatched episode, newest first."""
	url = '%s/upnext?%s' % (API, urlencode({'limit': limit, 'hide_unreleased': 'true'}))
	data = net.get_json(url, headers=_headers())
	return data.get('items') or []


def get_upnext_watchlist(limit=25):
	"""Watchlisted shows and their next episode - no watch progress required.

	Distinct from get_upnext(): that one only returns shows already IN
	PROGRESS (at least one watched episode). A show just added to the
	watchlist with nothing watched yet only shows up here.
	"""
	url = '%s/upnext/watchlist?%s' % (API, urlencode({'limit': limit}))
	data = net.get_json(url, headers=_headers())
	return data.get('items') or []


def get_user_lists():
	"""The connected user's own lists: [{id, name, slug, items, likes, ranked}]."""
	data = net.get_json('%s/lists/user' % API, headers=_headers())
	# Documented as a plain array, but kept tolerant of the {'lists': [...]}
	# shape other /lists endpoints use, in case that ever changes.
	return data if isinstance(data, list) else (data.get('lists') or [])


def get_liked_lists(limit=100):
	"""Lists the user has liked, most recently liked first."""
	url = '%s/lists/liked?%s' % (API, urlencode({'limit': limit}))
	data = net.get_json(url, headers=_headers())
	return data.get('lists') or []


def get_list_items(listid):
	"""{'movies': [...], 'shows': [...]} for one list, by numeric id."""
	return net.get_json('%s/lists/%s/items' % (API, listid), headers=_headers())


def _iso_now():
	return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def mark_movie_watched(imdb_id):
	if not imdb_id:
		return
	payload = {'movies': [{'ids': {'imdb': imdb_id}, 'watched_at': _iso_now()}]}
	net.post_json('%s/sync/watched' % API, payload, headers=_headers())


def mark_episode_watched(show_imdb_id, season, episode):
	if not show_imdb_id:
		return
	payload = {'shows': [{
		'ids': {'imdb': show_imdb_id},
		'seasons': [{
			'number': int(season),
			'episodes': [{'number': int(episode), 'watched_at': _iso_now()}],
		}],
	}]}
	net.post_json('%s/sync/watched' % API, payload, headers=_headers())

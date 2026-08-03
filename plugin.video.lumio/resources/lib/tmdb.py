# -*- coding: utf-8 -*-
"""
	TMDB API v3 client.

	This product uses TMDB and the TMDB APIs but is not endorsed, certified, or
	otherwise approved by TMDB.

	Auth is the api_key query parameter, same as Kodi's own
	metadata.themoviedb.org.python scraper - no header plumbing needed.

	Everything returned by this module is a NORMALISED item dict (see
	_list_item), never a raw TMDB payload: the raw ones carry far more than the
	addon shows and would bloat the cache for nothing.
"""
from urllib.parse import urlencode

from . import cache, kodi, net

API = 'https://api.themoviedb.org/3'
IMAGE_BASE = 'https://image.tmdb.org/t/p/'

# Fallback only: TMDB does no server-side translation fallback, so a
# localised request returns empty plots on niche titles instead of English
# ones. details() below re-fetches in English to patch those gaps; browse()
# uses the local language as-is since list screens don't carry a plot fallback.
FALLBACK_LANGUAGE = 'en-US'

POSTER_SIZE = 'w500'
FANART_SIZE = 'w1280'
STILL_SIZE = 'w300'

# TMDB pages are a fixed 20 items and stop at 500. Two pages per screen keeps
# lists from feeling thin next to Cinemeta's old 100-item batches.
MAX_PAGE = 500
PAGES_PER_SCREEN = 2

# TMDB has no anime type and no anime genre; genre 16 (Animation) plus the
# anime keywords is what TMDB moderators recommend.
ANIME_GENRE = '16'
ANIME_KEYWORDS = '210024|287501'
ANIME_BY_KEYWORD = 0   # precise, but keyword tagging is volunteer-driven
ANIME_BY_LANGUAGE = 1  # broad: any Japanese animation

# A rating sort with no vote floor returns titles with two votes.
MIN_VOTES = '200'

# Short enough to catch ranking/catalog drift (popularity and box-office
# order shift day to day), long enough that flipping back and forth across
# screens - or revisiting the same folder a minute later - doesn't re-hit
# TMDB for content that hasn't changed.
BROWSE_TTL = 6 * 3600


class TmdbError(Exception):
	pass


class NoApiKey(TmdbError):
	pass


def image(path, size=POSTER_SIZE):
	return '%s%s%s' % (IMAGE_BASE, size, path) if path else ''


def _call(path, language=None, **params):
	api_key = kodi.setting('tmdb_api_key').strip()
	if not api_key:
		raise NoApiKey('no TMDB api key configured')
	query = {'api_key': api_key, 'language': language or kodi.tmdb_language()}
	query.update({k: v for k, v in params.items() if v not in (None, '')})
	data = net.get_json('%s%s?%s' % (API, path, urlencode(query)))
	if isinstance(data, dict) and data.get('success') is False:
		raise TmdbError(data.get('status_message') or 'unknown error')
	return data or {}


# --- normalisation ---------------------------------------------------------

def _list_item(row, media):
	"""One catalogue row, in the shape the rest of the addon speaks."""
	is_movie = media == 'movie'
	released = (row.get('release_date') if is_movie else row.get('first_air_date')) or ''
	return {
		'tmdb': row.get('id'),
		'media': media,
		'title': (row.get('title') if is_movie else row.get('name')) or '',
		'originaltitle': (row.get('original_title') if is_movie else row.get('original_name')) or '',
		'year': released[:4],
		'premiered': released,
		'plot': row.get('overview') or '',
		'rating': row.get('vote_average') or 0,
		'votes': row.get('vote_count') or 0,
		'poster': image(row.get('poster_path')),
		'fanart': image(row.get('backdrop_path'), FANART_SIZE),
	}


def _runtime_seconds(row, media):
	"""Kodi's duration infolabel is in seconds; TMDB reports minutes."""
	if media == 'movie':
		minutes = row.get('runtime') or 0
	else:
		runtimes = row.get('episode_run_time') or []
		minutes = runtimes[0] if runtimes else 0
	try:
		return int(minutes) * 60
	except (TypeError, ValueError):
		return 0


def _certification(row, media):
	if media == 'movie':
		for entry in (row.get('release_dates') or {}).get('results') or []:
			if entry.get('iso_3166_1') == 'US':
				for release in entry.get('release_dates') or []:
					if release.get('certification'):
						return release['certification']
	else:
		for entry in (row.get('content_ratings') or {}).get('results') or []:
			if entry.get('iso_3166_1') == 'US' and entry.get('rating'):
				return entry['rating']
	return ''


def _crew_names(row, job):
	return [member.get('name') for member in ((row.get('credits') or {}).get('crew') or [])
	        if member.get('job') == job and member.get('name')]


def details(media, tmdb_id):
	"""Full item, cached. Carries the IMDb id everything downstream needs."""
	namespace = 'tmdb_%s' % media
	cached = cache.get(namespace, tmdb_id)
	if cached:
		return cached

	append = 'credits,release_dates' if media == 'movie' else 'external_ids,credits,content_ratings'
	path = '/movie/%s' % tmdb_id if media == 'movie' else '/tv/%s' % tmdb_id
	row = _call(path, append_to_response=append)

	if not row.get('overview') and kodi.tmdb_language() != FALLBACK_LANGUAGE:
		# Niche title with no translation in the local language: patch the
		# text fields from the English response instead of showing them blank.
		fallback = _call(path, language=FALLBACK_LANGUAGE, append_to_response=append)
		row['overview'] = fallback.get('overview') or row.get('overview')
		row['tagline'] = fallback.get('tagline') or row.get('tagline')

	item = _list_item(row, media)
	item.update({
		'imdb': row.get('imdb_id') or (row.get('external_ids') or {}).get('imdb_id') or '',
		'duration': _runtime_seconds(row, media),
		'genre': [genre.get('name') for genre in row.get('genres') or [] if genre.get('name')],
		'cast': [member.get('name') for member in ((row.get('credits') or {}).get('cast') or [])[:15]
		         if member.get('name')],
		'director': _crew_names(row, 'Director'),
		'writer': _crew_names(row, 'Writer') or _crew_names(row, 'Screenplay'),
		'studio': [company.get('name') for company in
		           (row.get('networks') if media == 'tv' else row.get('production_companies')) or []
		           if company.get('name')][:3],
		'mpaa': _certification(row, media),
		'tagline': row.get('tagline') or '',
		# The missing piece for original-language audio selection, kept here so
		# it is already available when that feature lands.
		'original_language': row.get('original_language') or '',
	})
	return cache.put(namespace, tmdb_id, item)


# --- browsing --------------------------------------------------------------

def _pages(path, params, screen):
	"""(rows, has_more) for one screen, made of PAGES_PER_SCREEN TMDB pages."""
	rows, has_more = [], False
	for offset in range(PAGES_PER_SCREEN):
		page = (screen - 1) * PAGES_PER_SCREEN + offset + 1
		if page > MAX_PAGE:
			break
		data = _call(path, page=page, **params)
		rows.extend(data.get('results') or [])
		try:
			total = min(int(data.get('total_pages') or 1), MAX_PAGE)
		except (TypeError, ValueError):
			total = 1
		has_more = page < total
		if not has_more:
			break
	return rows, has_more


def _anime_params():
	if kodi.setting_int('anime_filter', ANIME_BY_KEYWORD) == ANIME_BY_LANGUAGE:
		return {'with_genres': ANIME_GENRE, 'with_original_language': 'ja'}
	return {'with_genres': ANIME_GENRE, 'with_keywords': ANIME_KEYWORDS}


def _browse_cache_key(kind, catalog_id, screen, genre, year):
	# Every input that can change the result set has to be part of the key,
	# or a stale answer from a different language/filter combo gets served.
	return '|'.join(str(part) for part in (
		kind, catalog_id, screen, genre or '', year or '',
		kodi.tmdb_language(),
		kodi.setting_int('anime_filter', ANIME_BY_KEYWORD),
		kodi.setting_bool('tmdb_include_adult'),
	))


def browse(kind, catalog_id, screen=1, genre=None, year=None):
	"""(items, has_more) for one screen of a catalogue.

	kind is 'movie', 'tv', 'anime' or 'anime_movie'; catalog_id is 'popular',
	'box_office', 'top_rated', 'genre' or 'year'.
	"""
	namespace = 'tmdb_browse'
	key = _browse_cache_key(kind, catalog_id, screen, genre, year)
	cached = cache.get(namespace, key, ttl=BROWSE_TTL)
	if cached is not None:
		return cached

	media = 'movie' if kind in ('movie', 'anime_movie') else 'tv'
	is_anime = kind in ('anime', 'anime_movie')
	filtered = is_anime or catalog_id in ('genre', 'year', 'box_office')

	if not filtered and catalog_id in ('popular', 'top_rated'):
		# /movie/popular and /tv/top_rated are already vote-weighted and
		# cheaper than an equivalent discover call, so prefer them.
		rows, has_more = _pages('/%s/%s' % (media, catalog_id), {}, screen)
		result = [[_list_item(row, media) for row in rows], has_more]
		return cache.put(namespace, key, result)

	params = _anime_params() if is_anime else {}
	if catalog_id == 'genre' and genre:
		params['with_genres'] = ','.join(x for x in (params.get('with_genres'), str(genre)) if x)
	if catalog_id == 'year' and year:
		params['primary_release_year' if media == 'movie' else 'first_air_date_year'] = str(year)
	if catalog_id == 'box_office':
		# revenue.desc only exists on /discover/movie - TV has no revenue sort.
		params['sort_by'] = 'revenue.desc'
	elif catalog_id == 'top_rated':
		params['sort_by'] = 'vote_average.desc'
		params['vote_count.gte'] = MIN_VOTES
	else:
		params['sort_by'] = 'popularity.desc'
	params['include_adult'] = 'true' if kodi.setting_bool('tmdb_include_adult') else 'false'

	rows, has_more = _pages('/discover/%s' % media, params, screen)
	result = [[_list_item(row, media) for row in rows], has_more]
	return cache.put(namespace, key, result)


def search(media, query, screen=1):
	rows, has_more = _pages('/search/%s' % media, {'query': query}, screen)
	return [_list_item(row, media) for row in rows], has_more


def genres(media):
	"""[(id, name)] for the genre folder, cached for a month."""
	cached = cache.get('tmdb_genres', media, ttl=30 * 24 * 3600)
	if cached:
		return cached
	rows = _call('/genre/%s/list' % media).get('genres') or []
	pairs = [[row['id'], row['name']] for row in rows if row.get('id') and row.get('name')]
	return cache.put('tmdb_genres', media, pairs)

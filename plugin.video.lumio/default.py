# -*- coding: utf-8 -*-
import sys
import re
import time
from urllib.parse import parse_qsl, quote, urlencode
from urllib.error import URLError, HTTPError

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

from resources.lib import cache, mdblist, net, tmdb, tmdbhelper

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

_UA = net.UA
_SEEDERS = re.compile(r'\U0001F464\s*(\d+)')          # 👤
_FILENAME_MARK = re.compile(r'\U0001F5C2️\s*(.+)')  # 🗂️
_SIZE = re.compile(r'(\d+(?:[.,]\d+)?)\s*([GMK])(?:i?B|o)\b', re.I)
_SIZE_UNITS = {'G': 1024 ** 3, 'M': 1024 ** 2, 'K': 1024}

CINEMETA_BASE = 'https://v3-cinemeta.strem.io'

# String ids, see resources/language/*/strings.po
S_SEARCH_MOVIES = 30036
S_SEARCH_SERIES = 30037
S_SETTINGS = 30044
S_NEXT_PAGE = 30045
S_SEASON = 30046
S_SPECIALS = 30047
S_SEARCH_MOVIES_PROMPT = 30049
S_SEARCH_SERIES_PROMPT = 30050
S_NO_MANIFEST = 30051
S_NO_STREAMS = 30052
S_NO_RESULTS = 30053
S_SEARCH_FAILED = 30054
S_LOAD_LIST_FAILED = 30055
S_LOAD_EPISODES_FAILED = 30056
S_NO_EPISODES = 30057
S_HTTP_ERROR = 30058
S_UNREACHABLE = 30059
S_FETCH_ERROR = 30060
S_NO_API_KEY = 30115
S_MOVIES = 30116
S_SERIES = 30117
S_ANIME = 30118
S_POPULAR = 30119
S_BOX_OFFICE = 30120
S_TOP_RATED = 30121
S_BY_GENRE = 30122
S_BY_YEAR = 30123
S_ANIME_MOVIES = 30124
S_NO_IMDB = 30125
S_TMDB_ERROR = 30126
S_PICK_SOURCE = 30127
S_TH_INSTALLED = 30129
S_TH_MISSING = 30130
S_TH_FAILED = 30131
S_MDBLIST_UPNEXT = 30144
S_MDBLIST_NO_CLIENT_ID = 30145
S_MDBLIST_ENTER_CODE = 30146
S_MDBLIST_WAITING = 30147
S_MDBLIST_CONNECTED = 30148
S_MDBLIST_CANCELLED = 30149
S_MDBLIST_CONNECT_FAILED = 30150
S_MDBLIST_DISCONNECTED = 30151
S_MDBLIST_NOT_CONNECTED = 30152
S_MDBLIST_EMPTY = 30153
S_MDBLIST_LOAD_FAILED = 30154
S_MDBLIST_WATCHLIST = 30155
S_MDBLIST_WATCHLIST_EMPTY = 30156
S_MDBLIST_MY_LISTS = 30157
S_MDBLIST_LIKED_LISTS = 30158
S_MDBLIST_NO_LISTS = 30159


def _(string_id):
	return ADDON.getLocalizedString(string_id)


def _fmt(string_id, *args):
	"""Localised string with arguments, tolerant of a broken translation.

	A translator dropping a %s would otherwise raise here - and when that
	happens inside an error handler it hides the failure it was reporting.
	"""
	text = _(string_id)
	try:
		return text % args
	except (TypeError, ValueError):
		return '%s %s' % (text, ' '.join(str(a) for a in args))


def log(msg):
	xbmc.log('[plugin.video.lumio] %s' % msg, xbmc.LOGINFO)


def log_debug(msg):
	# Logged at INFO on purpose: LOGDEBUG would need Kodi's own debug mode on
	# too, and the point of this setting is to get detail without that.
	if ADDON.getSetting('debug_logging') == 'true':
		log(msg)


def _get_json(url):
	return net.get_json(url)


def manifest_base():
	url = ADDON.getSetting('manifest_url').strip()
	if not url:
		xbmcgui.Dialog().ok(ADDON_NAME, _(S_NO_MANIFEST))
		ADDON.openSettings()
		return None
	return url.rsplit('/manifest.json', 1)[0]


def fetch_streams(kodi_type, video_id):
	base = manifest_base()
	if not base:
		return []
	stream_type = 'series' if kodi_type == 'series' else 'movie'
	url = '%s/stream/%s/%s.json' % (base, stream_type, quote(video_id, safe=':'))
	try:
		data = _get_json(url)
		streams = data.get('streams', [])
		log_debug('%s -> %d streams' % (url, len(streams)))
		return streams
	except HTTPError as e:
		xbmcgui.Dialog().notification(ADDON_NAME, _fmt(S_HTTP_ERROR, e.code), xbmcgui.NOTIFICATION_ERROR)
	except URLError as e:
		xbmcgui.Dialog().notification(ADDON_NAME, _fmt(S_UNREACHABLE, e.reason), xbmcgui.NOTIFICATION_ERROR)
	except Exception as e:
		log('fetch_streams error: %s' % e)
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_FETCH_ERROR), xbmcgui.NOTIFICATION_ERROR)
	return []


def _tmdb_error(error, fallback_id):
	"""One notification for any TMDB failure, and the settings when unusable."""
	if isinstance(error, tmdb.NoApiKey):
		xbmcgui.Dialog().ok(ADDON_NAME, _(S_NO_API_KEY))
		ADDON.openSettings()
		return
	log('tmdb error: %s' % error)
	message = _fmt(S_TMDB_ERROR, error) if isinstance(error, tmdb.TmdbError) else _(fallback_id)
	xbmcgui.Dialog().notification(ADDON_NAME, message, xbmcgui.NOTIFICATION_ERROR)


def tmdb_details(media, tmdb_id):
	"""Cached detail item, or None after telling the user why not."""
	try:
		return tmdb.details(media, tmdb_id)
	except Exception as e:
		_tmdb_error(e, S_LOAD_LIST_FAILED)
		return None


# Cinemeta survives for exactly one job: the season and episode lists. Its
# numbering is what Stremio stream ids (tt...:S:E) are built on, and TMDB's
# diverges from it - badly for anime, where cours get split into seasons and
# long runners use absolute numbering. Sourcing episode indices from TMDB would
# silently stop finding streams.
def cinemeta_series_meta(imdb_id, quiet=False):
	cached = cache.get('cinemeta_series', imdb_id)
	if cached is not None:
		return cached
	url = '%s/meta/series/%s.json' % (CINEMETA_BASE, quote(imdb_id or ''))
	try:
		meta = _get_json(url).get('meta', {})
	except Exception as e:
		log('cinemeta_series_meta error: %s' % e)
		if not quiet:
			xbmcgui.Dialog().notification(ADDON_NAME, _(S_LOAD_EPISODES_FAILED), xbmcgui.NOTIFICATION_ERROR)
		return {}
	return cache.put('cinemeta_series', imdb_id, meta)


def stream_display(stream):
	behavior = stream.get('behaviorHints') or {}
	title = stream.get('title') or ''
	description = stream.get('description') or ''
	blob = '\n'.join(x for x in (title, description) if x)

	name = behavior.get('filename')
	if not name:
		m = _FILENAME_MARK.search(blob)
		if m:
			name = m.group(1).strip()
	if not name:
		name = (title.split('\n')[0] if title else '') or stream.get('name') or 'Unknown'

	size_text = ''
	video_size = behavior.get('videoSize')
	if video_size:
		size_text = '%.2f GB' % (video_size / (1024 ** 3))
	else:
		m = _SIZE.search(blob)
		if m:
			size_text = m.group(0)

	label = name
	if size_text:
		label = '%s  [%s]' % (label, size_text)
	return label, name


def _stream_blob(stream):
	# "name" is included because plenty of stream addons put the quality tags
	# and the file size there rather than in the title or the description, and
	# a size we cannot see ranks as 0 - which silently disables size sorting.
	behavior = stream.get('behaviorHints') or {}
	return ' '.join(filter(None, [
		stream.get('name', ''),
		stream.get('title', ''),
		stream.get('description', ''),
		behavior.get('filename', ''),
	]))


def _size_bytes(blob):
	m = _SIZE.search(blob)
	if not m:
		return 0
	try:
		value = float(m.group(1).replace(',', '.'))
	except ValueError:
		return 0
	return int(value * _SIZE_UNITS.get(m.group(2).upper(), 0))


# Every _rank_* below scores a stream on one criterion, higher being better, so
# they can be combined in any order the user picks (see _quality_key).
_ONE_GB = 1024 ** 3


def _exact_size(blob, behavior):
	"""Size in bytes from behaviorHints, falling back to the text.

	videoSize is coerced rather than trusted: providers have been seen sending
	it as a string, and a raw string here would break the whole sort.
	"""
	try:
		size = int(float(behavior.get('videoSize') or 0))
	except (TypeError, ValueError):
		size = 0
	return size or _size_bytes(blob)


_DEFAULT_SIZE_TOLERANCE_GB = 20


def _size_tolerance():
	try:
		return max(0, int(ADDON.getSetting('size_tolerance_gb') or _DEFAULT_SIZE_TOLERANCE_GB)) * _ONE_GB
	except ValueError:
		return _DEFAULT_SIZE_TOLERANCE_GB * _ONE_GB


def _size_ranker(streams):
	"""Build the size criterion for one result list.

	Sizes are grouped in steps of the tolerance measured DOWN FROM the biggest
	file in the list, not on a fixed 0-20-40 grid. That matters: on a fixed
	grid a boundary can fall between two near-identical files (59 GB and 61 GB
	land in different steps), which is the whole thing we are trying to avoid.
	Anchoring on the biggest file guarantees that everything within one
	tolerance of it ties, so the next priority - Dolby Vision, HDR, ... - is
	what actually decides between them.
	"""
	tolerance = _size_tolerance()
	max_size = max((_exact_size(_stream_blob(s), s.get('behaviorHints') or {}) for s in streams), default=0)

	def rank(blob, behavior):
		size = _exact_size(blob, behavior)
		if not tolerance:
			return size  # tolerance 0 means compare to the byte
		return -((max_size - size) // tolerance)

	return rank


_RESOLUTION_RANK = (
	(re.compile(r'4K|2160p', re.I), 3),
	(re.compile(r'1080p', re.I), 2),
	(re.compile(r'720p', re.I), 1),
)


def _rank_resolution(blob, behavior):
	for pattern, rank in _RESOLUTION_RANK:
		if pattern.search(blob):
			return rank
	return 0


def _rank_hdr(blob, behavior):
	if re.search(r'hdr\s*10\s*\+|hdr\+', blob, re.I):
		return 2
	if re.search(r'\bhdr(10)?\b', blob, re.I):
		return 1
	return 0


def _rank_dolby_vision(blob, behavior):
	return 1 if re.search(r'dolby\s*vision|\bdovi\b|\bdv\b', blob, re.I) else 0


# Second digit capped at 2 and a unit lookahead so file sizes ("2.1 GB") aren't
# mistaken for a channel layout; the (?<!\d) lets "DDP5.1" match.
_AUDIO_CHANNELS = re.compile(r'(?<!\d)([1-9])[.,]([0-2])(?!\d)(?!\s*[GMK](?:i?B|o)\b)', re.I)


def _rank_audio_channels(blob, behavior):
	return max((int(m.group(1)) * 10 + int(m.group(2)) for m in _AUDIO_CHANNELS.finditer(blob)), default=0)


_AUDIO_FORMAT_RANK = (
	(re.compile(r'atmos', re.I), 5),
	(re.compile(r'true\s*hd', re.I), 4),
	(re.compile(r'dts[\s._-]*(?:hd|x)\b', re.I), 3),
	(re.compile(r'\b(?:e-?ac-?3|eac3|ddp|dd\+)\b', re.I), 2),
	(re.compile(r'\b(?:ac-?3|dd|dts|aac)\b', re.I), 1),
)


def _rank_audio_format(blob, behavior):
	for pattern, rank in _AUDIO_FORMAT_RANK:
		if pattern.search(blob):
			return rank
	return 0


_CODEC_RANK = (
	(re.compile(r'\bav1\b', re.I), 3),
	(re.compile(r'hevc|x\.?265|h\.?\s*265', re.I), 2),
	(re.compile(r'\bavc\b|x\.?264|h\.?\s*264', re.I), 1),
)


def _rank_codec(blob, behavior):
	for pattern, rank in _CODEC_RANK:
		if pattern.search(blob):
			return rank
	return 0


# Criterion id (as stored in the sort_priority_N settings) -> ranking function.
# Ids must stay stable, they're the <option> values in resources/settings.xml.
# Size is a placeholder here: it depends on the whole result list, so
# sort_streams swaps in a ranker built for that list (see _size_ranker).
_CRITERIA = {
	1: None,
	2: _rank_resolution,
	3: _rank_hdr,
	4: _rank_dolby_vision,
	5: _rank_audio_channels,
	6: _rank_audio_format,
	7: _rank_codec,
}
_CRITERION_NAMES = {
	1: 'size', 2: 'resolution', 3: 'hdr', 4: 'dolby_vision',
	5: 'audio_channels', 6: 'audio_format', 7: 'codec',
}
_PRIORITY_SETTINGS = tuple('sort_priority_%d' % slot for slot in range(1, len(_CRITERIA) + 1))
_DEFAULT_PRIORITIES = (2, 4, 3, 1)  # resolution > Dolby Vision > HDR > size


def _sort_priorities():
	"""Criteria ids in the user-chosen order, 'not used' and duplicates dropped."""
	priorities = []
	for setting_id in _PRIORITY_SETTINGS:
		try:
			criterion = int(ADDON.getSetting(setting_id) or 0)
		except ValueError:
			continue
		if criterion in _CRITERIA and criterion not in priorities:
			priorities.append(criterion)
	return priorities or list(_DEFAULT_PRIORITIES)


def _quality_key(stream, priorities, criteria):
	blob = _stream_blob(stream)
	behavior = stream.get('behaviorHints') or {}
	key = [criteria[criterion](blob, behavior) for criterion in priorities]
	# Exact byte size as the last resort, so streams that tie on every chosen
	# criterion still come out in a stable order run after run.
	key.append(_exact_size(blob, behavior))
	return tuple(key)


def sort_streams(streams):
	if ADDON.getSetting('sort_by_quality') != 'true':
		return streams
	priorities = _sort_priorities()
	criteria = dict(_CRITERIA)
	criteria[1] = _size_ranker(streams)
	# Decorated sort: the key is computed once per stream, and reused for the
	# debug dump below instead of being recomputed.
	keyed = sorted(((_quality_key(stream, priorities, criteria), stream) for stream in streams),
	               key=lambda pair: pair[0], reverse=True)
	if ADDON.getSetting('debug_logging') == 'true':
		names = [_CRITERION_NAMES[criterion] for criterion in priorities] + ['exact_size']
		log_debug('sort by %s (size tolerance %d GB)' % (' > '.join(names), _size_tolerance() // _ONE_GB))
		for key, stream in keyed:
			log_debug('  %s | %s' % (
				' '.join('%s=%s' % (name, value) for name, value in zip(names, key)),
				_stream_blob(stream)[:110].replace('\n', ' ')))
	return [stream for _, stream in keyed]


def playable_streams(kodi_type, video_id):
	streams = sort_streams(fetch_streams(kodi_type, video_id))
	return [s for s in streams if s.get('url')]


def _without_poster(meta):
	return {k: v for k, v in meta.items() if k != 'poster'}


# Keys of a detail item that map straight onto a Kodi video infolabel.
_INFO_KEYS = ('title', 'originaltitle', 'plot', 'year', 'premiered', 'duration',
              'genre', 'cast', 'director', 'writer', 'studio', 'mpaa', 'tagline',
              'tvshowtitle', 'season', 'episode', 'playcount')


def apply_info(li, item, mediatype, art=True):
	"""Put a full video card on a ListItem.

	Used on EVERY item, including the one handed to setResolvedUrl, because
	Kodi remotes read the playing item through Player.GetItem and a bare
	ListItem shows up there as a filename. Kodi also drops mediatype set this
	way inside setResolvedUrl (xbmc/xbmc#19378), which is the other reason the
	directory item has to carry the same information.

	Sticks to the legacy setInfo/setArt API on purpose: addon.xml requires
	xbmc.python 3.0.0 (Kodi 19) and the InfoTagVideo setters are Kodi 20+.
	"""
	info = {'mediatype': mediatype}
	for key in _INFO_KEYS:
		value = item.get(key)
		if value not in (None, '', [], 0):
			info[key] = value
	try:
		if item.get('rating'):
			info['rating'] = float(item['rating'])
		if item.get('votes'):
			info['votes'] = str(item['votes'])
	except (TypeError, ValueError):
		pass
	li.setInfo('video', info)

	unique = {source: str(item[source]) for source in ('imdb', 'tmdb') if item.get(source)}
	if unique:
		li.setUniqueIDs(unique, 'imdb' if 'imdb' in unique else 'tmdb')

	if art:
		poster, fanart = item.get('poster') or '', item.get('fanart') or ''
		thumb = item.get('thumb') or poster
		artwork = {k: v for k, v in
		           {'poster': poster, 'thumb': thumb, 'fanart': fanart, 'landscape': fanart}.items() if v}
		if artwork:
			li.setArt(artwork)
	return li


def add_pick_source(li, params):
	"""Context-menu entry that opens the source list for a playable item.

	Container.Update rather than RunPlugin: this navigates to a listing, and
	RunPlugin fires an action without ever showing one.
	"""
	url = '%s?%s' % (BASE_URL, urlencode(params))
	li.addContextMenuItems([(_(S_PICK_SOURCE), 'Container.Update(%s)' % url)])


def _episode_meta(imdb_id, season, episode):
	"""One episode out of the cached Cinemeta series meta, or {}."""
	try:
		season, episode = int(season), int(episode)
	except (TypeError, ValueError):
		return {}
	for video in cinemeta_series_meta(imdb_id, quiet=True).get('videos') or []:
		if video.get('season') == season and video.get('episode') == episode:
			return video
	return {}


def _card(params, scrobble_meta=None):
	"""Full metadata for the item being listed or played.

	Read back from the caches by id rather than carried in the plugin URL: on
	the resolve hop that URL already holds the whole stream link plus every
	metadata value re-encoded a second time, and a plot would push it past the
	length where Kodi and Kore start truncating.
	"""
	meta = dict(scrobble_meta or {})
	mediatype = meta.get('mediatype') or 'video'
	media = 'movie' if mediatype == 'movie' else 'tv'

	card = {}
	if params.get('tmdb'):
		try:
			card = dict(tmdb.details(media, params['tmdb']) or {})
		except Exception as e:
			# Enrichment only - never block playback because TMDB is unhappy.
			log('card details unavailable: %s' % e)
	card['mediatype'] = mediatype

	# The URL-carried values are the authority on identity and episode
	# position; the cached detail blob only enriches around them.
	if meta.get('imdbnumber'):
		card['imdb'] = meta['imdbnumber']
	for key in ('title', 'tvshowtitle', 'season', 'episode', 'year'):
		if meta.get(key):
			card[key] = meta[key]
	if meta.get('poster'):
		card.setdefault('poster', meta['poster'])
		card.setdefault('thumb', meta['poster'])

	if mediatype == 'episode' and card.get('imdb'):
		video = _episode_meta(card['imdb'], meta.get('season'), meta.get('episode'))
		if video:
			card['plot'] = video.get('overview') or video.get('description') or card.get('plot') or ''
			if video.get('thumbnail'):
				card['thumb'] = video['thumbnail']
			aired = video.get('released') or video.get('firstAired') or ''
			if aired:
				card['premiered'] = aired[:10]
				card['year'] = aired[:4]
	return card


def play_best(kodi_type, video_id, scrobble_meta=None, resume=None, card=None):
	streams = playable_streams(kodi_type, video_id)
	if not streams:
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_NO_STREAMS), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
		return
	resolve_and_play(streams[0]['url'], scrobble_meta, resume, card)


def list_streams(kodi_type, video_id, scrobble_meta=None, card=None):
	card = card if card is not None else dict(scrobble_meta or {})
	streams = sort_streams(fetch_streams(kodi_type, video_id))
	if not streams:
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_NO_STREAMS), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return

	xbmcplugin.setContent(HANDLE, 'videos')
	for stream in streams:
		url = stream.get('url')
		if not url:
			# Stream-only addon returning a torrent hash isn't handled by this
			# standalone player (no debrid/torrent client here) - skip it.
			continue
		label, _name = stream_display(stream)
		li = xbmcgui.ListItem(label=label)
		# The release filename belongs in the LABEL only, so you can still tell
		# sources apart. It used to overwrite the title in the info tag, which
		# is precisely why Kodi and Kore showed a filename instead of the film.
		apply_info(li, card, card.get('mediatype') or 'video')
		li.setProperty('IsPlayable', 'true')
		play_params = dict(scrobble_meta or {}, action='resolve', url=url)
		if card.get('tmdb'):
			# Carried so the resolve hop can rebuild the same card from cache
			# instead of hauling the plot and artwork through the URL.
			play_params['tmdb'] = card['tmdb']
		play_url = '%s?%s' % (BASE_URL, urlencode(play_params))
		xbmcplugin.addDirectoryItem(HANDLE, play_url, li, isFolder=False)
	xbmcplugin.endOfDirectory(HANDLE)


def resolve_and_play(url, scrobble_meta=None, resume=None, card=None):
	headers = 'User-Agent=%s' % quote(_UA)
	li = xbmcgui.ListItem(path='%s|%s' % (url, headers))
	li.setProperty('IsPlayable', 'true')
	if scrobble_meta:
		# The info tag is what script.trakt and every remote read off the
		# playing item.
		card = card if card is not None else dict(scrobble_meta)
		apply_info(li, card, card.get('mediatype') or 'video')
	if resume:
		position, total = resume
		if total:
			li.setProperty('ResumeTime', str(position))
			li.setProperty('TotalTime', str(total))
	xbmcplugin.setResolvedUrl(HANDLE, True, li)
	_track_mdblist_watched(scrobble_meta)


def _track_mdblist_watched(scrobble_meta):
	"""Blocks until this playback ends, then reports it watched to MDBList.

	Runs in-process rather than via a background service - this addon has
	none, and adding one solely for this would mean an addon.xml change and
	a Kodi restart to register. The tradeoff: this plugin invocation stays
	alive for the whole runtime of the video (Kodi does not require a
	resolver script to exit right after setResolvedUrl).
	"""
	if not scrobble_meta or not scrobble_meta.get('imdbnumber') or not _mdblist_ready():
		return

	monitor = xbmc.Monitor()
	player = xbmc.Player()
	for _i in range(50):
		if monitor.waitForAbort(0.2):
			return
		if player.isPlayingVideo():
			break
	else:
		return

	position, total = 0, 0
	while player.isPlayingVideo():
		try:
			position, total = player.getTime(), player.getTotalTime()
		except Exception:
			pass
		if monitor.waitForAbort(5):
			return

	if not total or position / total < mdblist.WATCHED_THRESHOLD:
		return
	try:
		if scrobble_meta.get('mediatype') == 'episode':
			mdblist.mark_episode_watched(
				scrobble_meta['imdbnumber'], scrobble_meta.get('season'), scrobble_meta.get('episode'))
		else:
			mdblist.mark_movie_watched(scrobble_meta['imdbnumber'])
		log_debug('mdblist: marked %s watched' % scrobble_meta['imdbnumber'])
	except Exception as e:
		log('mdblist watched-sync failed: %s' % e)


def render_items(items, next_page_params=None):
	"""Render a TMDB catalogue page.

	Items come straight from the list endpoint - no per-item detail call, which
	is what keeps a page to one request. The IMDb id is resolved later, when
	one is actually selected.
	"""
	if not items:
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_NO_RESULTS), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return

	media = items[0].get('media') or 'movie'
	is_movie = media == 'movie'
	xbmcplugin.setContent(HANDLE, 'movies' if is_movie else 'tvshows')
	auto_play = ADDON.getSetting('auto_play_best') == 'true'
	if is_movie:
		target_action = 'movie_play_best' if auto_play else 'movie_streams'
	else:
		target_action = 'seasons'

	for item in items:
		year = item.get('year') or ''
		title = item.get('title') or 'Unknown'
		li = xbmcgui.ListItem(label='%s (%s)' % (title, year) if year else title)
		apply_info(li, item, 'movie' if is_movie else 'tvshow')
		is_leaf_movie = is_movie and auto_play
		if is_leaf_movie:
			li.setProperty('IsPlayable', 'true')
		url_params = {'action': target_action, 'tmdb': item.get('tmdb')}
		if is_movie:
			url_params.update({
				'mediatype': 'movie',
				'title': title,
				'year': year,
				'poster': item.get('poster') or '',
			})
		if is_leaf_movie:
			# Auto-play is convenient until the top-ranked source is the wrong
			# one; this is the escape hatch to the full list without going and
			# flipping the setting.
			add_pick_source(li, dict(url_params, action='movie_streams'))
		url = '%s?%s' % (BASE_URL, urlencode(url_params))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=not is_leaf_movie)

	if next_page_params:
		li = xbmcgui.ListItem(label=_(S_NEXT_PAGE))
		url = '%s?%s' % (BASE_URL, urlencode(next_page_params))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
	xbmcplugin.endOfDirectory(HANDLE)


def _browse(kind, catalog_id, screen=1, genre=None, year=None):
	try:
		items, has_more = tmdb.browse(kind, catalog_id, screen=screen, genre=genre, year=year)
	except Exception as e:
		_tmdb_error(e, S_LOAD_LIST_FAILED)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return
	log_debug('catalog %s/%s screen=%s genre=%s year=%s -> %d items, has_more=%s' %
	          (kind, catalog_id, screen, genre, year, len(items), has_more))
	next_page = None
	if has_more:
		next_page = {'action': 'catalog', 'kind': kind, 'catalog': catalog_id, 'screen': screen + 1}
		if genre:
			next_page['genre'] = genre
		if year:
			next_page['year'] = year
	render_items(items, next_page)


def search(media, prompt_id, screen=1, query=None):
	if not query:
		query = xbmcgui.Dialog().input(_(prompt_id))
	if not query:
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return
	try:
		items, has_more = tmdb.search(media, query, screen=screen)
	except Exception as e:
		_tmdb_error(e, S_SEARCH_FAILED)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return
	next_page = None
	if has_more:
		next_page = {'action': 'search', 'media': media, 'query': query, 'screen': screen + 1}
	render_items(items, next_page)


# Section -> the catalogue entries it offers. Box office is movies only:
# revenue.desc does not exist on /discover/tv.
_SECTIONS = {
	'movie': ((S_POPULAR, 'popular'), (S_BOX_OFFICE, 'box_office'), (S_TOP_RATED, 'top_rated')),
	'tv': ((S_POPULAR, 'popular'), (S_TOP_RATED, 'top_rated')),
	'anime': ((S_POPULAR, 'popular'), (S_TOP_RATED, 'top_rated')),
}


def list_section(kind):
	xbmcplugin.setContent(HANDLE, 'videos')
	for string_id, catalog_id in _SECTIONS.get(kind, ()):
		li = xbmcgui.ListItem(label=_(string_id))
		url = '%s?%s' % (BASE_URL, urlencode({'action': 'catalog', 'kind': kind, 'catalog': catalog_id}))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

	if kind == 'anime':
		# Anime films are a separate discover call against /discover/movie.
		li = xbmcgui.ListItem(label=_(S_ANIME_MOVIES))
		url = '%s?%s' % (BASE_URL, urlencode({'action': 'catalog', 'kind': 'anime_movie', 'catalog': 'popular'}))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

	for string_id, action in ((S_BY_GENRE, 'genres'), (S_BY_YEAR, 'years')):
		li = xbmcgui.ListItem(label=_(string_id))
		url = '%s?%s' % (BASE_URL, urlencode({'action': action, 'kind': kind}))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
	xbmcplugin.endOfDirectory(HANDLE)


def list_genres(kind):
	media = 'movie' if kind in ('movie', 'anime_movie') else 'tv'
	try:
		pairs = tmdb.genres(media)
	except Exception as e:
		_tmdb_error(e, S_LOAD_LIST_FAILED)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return
	xbmcplugin.setContent(HANDLE, 'videos')
	for genre_id, name in pairs:
		li = xbmcgui.ListItem(label=name)
		url = '%s?%s' % (BASE_URL, urlencode({
			'action': 'catalog', 'kind': kind, 'catalog': 'genre', 'genre': genre_id}))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
	xbmcplugin.endOfDirectory(HANDLE)


def list_years(kind):
	xbmcplugin.setContent(HANDLE, 'videos')
	current = int(time.strftime('%Y'))
	for year in range(current, current - 40, -1):
		li = xbmcgui.ListItem(label=str(year))
		url = '%s?%s' % (BASE_URL, urlencode({
			'action': 'catalog', 'kind': kind, 'catalog': 'year', 'year': year}))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
	xbmcplugin.endOfDirectory(HANDLE)


def series_imdb(params):
	"""IMDb id of a series, resolved from its TMDB id and cached.

	Everything downstream needs it: the stream lookup, the Cinemeta episode
	list, and the Stremio library key.
	"""
	if params.get('imdb'):
		return params['imdb']
	details = tmdb_details('tv', params.get('tmdb'))
	if details is None:
		return ''
	imdb_id = details.get('imdb')
	if not imdb_id:
		# TMDB's imdb_id is nullable, and no IMDb id means no streams exist for
		# this title - say so rather than showing an empty season list.
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_NO_IMDB), xbmcgui.NOTIFICATION_INFO)
	return imdb_id or ''


def list_seasons(imdb_id, tmdb_id=None):
	meta = cinemeta_series_meta(imdb_id)
	videos = meta.get('videos') or []
	seasons = sorted(set(v.get('season') for v in videos if v.get('season') is not None))
	if not seasons:
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_NO_EPISODES), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return

	xbmcplugin.setContent(HANDLE, 'seasons')
	for season in seasons:
		label = _fmt(S_SEASON, season) if season else _(S_SPECIALS)
		li = xbmcgui.ListItem(label=label)
		params = {'action': 'episodes', 'imdb': imdb_id, 'season': season}
		if tmdb_id:
			params['tmdb'] = tmdb_id
		url = '%s?%s' % (BASE_URL, urlencode(params))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
	xbmcplugin.endOfDirectory(HANDLE)


def list_episodes(imdb_id, season, tmdb_id=None):
	season = int(season)
	meta = cinemeta_series_meta(imdb_id)
	# Episode indices come from Cinemeta on purpose - Stremio stream ids are
	# tt...:S:E and TMDB's numbering diverges from it, badly for anime.
	videos = [v for v in (meta.get('videos') or []) if v.get('season') == season]
	videos.sort(key=lambda v: v.get('episode') or 0)
	if not videos:
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_NO_EPISODES), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return

	xbmcplugin.setContent(HANDLE, 'episodes')
	auto_play = ADDON.getSetting('auto_play_best') == 'true'
	target_action = 'episode_play_best' if auto_play else 'episode_streams'
	tvshowtitle = meta.get('name') or ''
	show = tmdb_details('tv', tmdb_id) if tmdb_id else None
	for video in videos:
		episode = video.get('episode')
		label = '%sx%02d - %s' % (season, episode, video.get('name') or '')
		li = xbmcgui.ListItem(label=label)
		aired = video.get('released') or video.get('firstAired') or ''
		card = dict(show or {})
		card.update({
			'imdb': imdb_id, 'tmdb': tmdb_id,
			'title': video.get('name') or '',
			'tvshowtitle': tvshowtitle,
			'season': season, 'episode': episode,
			'plot': video.get('overview') or video.get('description') or '',
			'premiered': aired[:10], 'year': aired[:4],
			'thumb': video.get('thumbnail') or (show or {}).get('poster') or meta.get('poster') or '',
		})
		apply_info(li, card, 'episode')
		params = {
			'action': target_action,
			'imdb': imdb_id,
			'season': season,
			'episode': episode,
			'mediatype': 'episode',
			'imdbnumber': imdb_id,
			'tvshowtitle': tvshowtitle,
			'title': video.get('name') or '',
			'poster': video.get('thumbnail') or meta.get('poster') or '',
			'tmdb': tmdb_id or '',
		}
		if auto_play:
			li.setProperty('IsPlayable', 'true')
			add_pick_source(li, dict(params, action='episode_streams'))
		url = '%s?%s' % (BASE_URL, urlencode(params))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=not auto_play)
	xbmcplugin.endOfDirectory(HANDLE)


def open_settings():
	ADDON.openSettings()
	xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)


def install_th_player():
	"""Register Lumio as a TMDb Helper player, on explicit request only."""
	if not tmdbhelper.helper_installed():
		xbmcgui.Dialog().ok(ADDON_NAME, _(S_TH_MISSING))
		return
	try:
		target = tmdbhelper.install()
	except Exception as e:
		log('tmdb helper player install failed: %s' % e)
		xbmcgui.Dialog().ok(ADDON_NAME, _fmt(S_TH_FAILED, e))
		return
	log('tmdb helper player written to %s' % target)
	# The path is shown, not just a success tick: if the player still does not
	# appear in TMDb Helper's list, knowing where the file landed is the whole
	# diagnosis.
	xbmcgui.Dialog().ok(ADDON_NAME, '%s\n\n%s' % (_(S_TH_INSTALLED), target))


def _mdblist_ready():
	"""On, AND connected - the two things required before any MDBList call."""
	return ADDON.getSetting('mdblist_enabled') == 'true' and mdblist.is_connected()


def mdblist_connect():
	"""Device-code sign-in, run from the settings screen's Connect button."""
	try:
		auth = mdblist.start_device_auth()
	except mdblist.MdblistError as e:
		message = _(S_MDBLIST_NO_CLIENT_ID) if 'client id' in str(e) else _fmt(S_MDBLIST_CONNECT_FAILED, e)
		xbmcgui.Dialog().ok(ADDON_NAME, message)
		return

	# Stays in the message on every update below: DialogProgress.update()
	# replaces the whole message, so a "waiting" line without it would erase
	# the code from view the moment the first tick lands.
	instructions = _fmt(S_MDBLIST_ENTER_CODE, auth['verification_uri'], auth['user_code'])
	progress = xbmcgui.DialogProgress()
	progress.create(ADDON_NAME, '%s\n%s' % (instructions, _(S_MDBLIST_WAITING)))
	monitor = xbmc.Monitor()

	def wait(seconds):
		# waitForAbort sleeps AND doubles as the Kodi-shutdown check.
		progress.update(50, '%s\n%s' % (instructions, _(S_MDBLIST_WAITING)))
		monitor.waitForAbort(seconds)

	def cancelled():
		return progress.iscanceled() or monitor.abortRequested()

	try:
		token = mdblist.poll_device_token(
			auth['device_code'], auth.get('interval', 5), auth.get('expires_in', 300), wait, cancelled)
	except mdblist.MdblistError as e:
		progress.close()
		xbmcgui.Dialog().ok(ADDON_NAME, _fmt(S_MDBLIST_CONNECT_FAILED, e))
		return
	progress.close()

	if not token:
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_MDBLIST_CANCELLED), xbmcgui.NOTIFICATION_INFO)
		return
	xbmcgui.Dialog().notification(ADDON_NAME, _(S_MDBLIST_CONNECTED), xbmcgui.NOTIFICATION_INFO)


def mdblist_disconnect():
	mdblist.disconnect()
	xbmcgui.Dialog().notification(ADDON_NAME, _(S_MDBLIST_DISCONNECTED), xbmcgui.NOTIFICATION_INFO)


def _upnext_card(item):
	"""Best-effort ListItem info from one /upnext row.

	The response is documented loosely ("show metadata, next-episode
	details..."), not as a typed schema, so everything here is read
	defensively with fallbacks instead of assumed to exist.
	"""
	show = item.get('show') or item
	episode = item.get('next_episode') or item.get('episode') or {}
	ids = show.get('ids') or item.get('ids') or {}
	return {
		'imdb': ids.get('imdb') or '',
		'tvshowtitle': show.get('title') or '',
		'title': episode.get('title') or '',
		'season': episode.get('season'),
		'episode': episode.get('number') or episode.get('episode'),
		'plot': episode.get('overview') or show.get('overview') or '',
		'poster': show.get('poster') or show.get('poster_path') or '',
		'fanart': show.get('fanart') or show.get('backdrop_path') or '',
	}


def _render_upnext(fetch, empty_string_id):
	if not _mdblist_ready():
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_MDBLIST_NOT_CONNECTED), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return
	try:
		items = fetch()
	except Exception as e:
		xbmcgui.Dialog().notification(ADDON_NAME, _fmt(S_MDBLIST_LOAD_FAILED, e), xbmcgui.NOTIFICATION_ERROR)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return
	if not items:
		xbmcgui.Dialog().notification(ADDON_NAME, _(empty_string_id), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return

	xbmcplugin.setContent(HANDLE, 'episodes')
	auto_play = ADDON.getSetting('auto_play_best') == 'true'
	target_action = 'episode_play_best' if auto_play else 'episode_streams'
	for row in items:
		card = _upnext_card(row)
		if not card['imdb'] or not card['season'] or not card['episode']:
			continue
		label = '%s - %sx%02d' % (card['tvshowtitle'] or _(S_MDBLIST_UPNEXT), card['season'], card['episode'])
		li = xbmcgui.ListItem(label=label)
		apply_info(li, dict(card, mediatype='episode'), 'episode')
		if auto_play:
			li.setProperty('IsPlayable', 'true')
		url_params = {
			'action': target_action, 'imdb': card['imdb'], 'season': card['season'], 'episode': card['episode'],
			'mediatype': 'episode', 'imdbnumber': card['imdb'],
			'tvshowtitle': card['tvshowtitle'], 'title': card['title'], 'poster': card['poster'],
		}
		if auto_play:
			add_pick_source(li, dict(url_params, action='episode_streams'))
		url = '%s?%s' % (BASE_URL, urlencode(url_params))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=not auto_play)
	# Never cached: Up Next is meant to reflect what just changed on MDBList
	# (a new watchlist add, a check-in from another device...), so Kodi's
	# usual folder cache would show stale progress here more than it helps.
	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def list_upnext():
	_render_upnext(mdblist.get_upnext, S_MDBLIST_EMPTY)


def list_mdblist_watchlist():
	_render_upnext(mdblist.get_upnext_watchlist, S_MDBLIST_WATCHLIST_EMPTY)


def list_mdblist_lists(mode):
	"""Root screen for either 'user' (own lists) or 'liked' (liked lists)."""
	if not _mdblist_ready():
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_MDBLIST_NOT_CONNECTED), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return
	try:
		rows = mdblist.get_user_lists() if mode == 'user' else mdblist.get_liked_lists()
	except Exception as e:
		xbmcgui.Dialog().notification(ADDON_NAME, _fmt(S_MDBLIST_LOAD_FAILED, e), xbmcgui.NOTIFICATION_ERROR)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return
	if not rows:
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_MDBLIST_NO_LISTS), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return

	xbmcplugin.setContent(HANDLE, 'videos')
	for row in rows:
		name = row.get('name') or ''
		count = row.get('items')
		label = '%s (%d)' % (name, count) if count else name
		li = xbmcgui.ListItem(label=label)
		url = '%s?%s' % (BASE_URL, urlencode({'action': 'mdblist_list_items', 'listid': row.get('id')}))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def _mdblist_list_card(row):
	ids = row.get('ids') or {}
	return {
		'imdb': ids.get('imdb') or row.get('imdb_id') or '',
		'tmdb': ids.get('tmdb') or '',
		'title': row.get('title') or '',
		'year': str(row.get('release_year') or ''),
		'is_movie': (row.get('mediatype') or 'movie') == 'movie',
	}


def list_mdblist_list_items(listid):
	"""Movies/shows inside one MDBList list - links straight into the normal
	streams flow via imdb id, same as any other catalogue entry point."""
	if not _mdblist_ready():
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_MDBLIST_NOT_CONNECTED), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return
	try:
		data = mdblist.get_list_items(listid)
	except Exception as e:
		xbmcgui.Dialog().notification(ADDON_NAME, _fmt(S_MDBLIST_LOAD_FAILED, e), xbmcgui.NOTIFICATION_ERROR)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return
	rows = list(data.get('movies') or []) + list(data.get('shows') or [])
	if not rows:
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_MDBLIST_EMPTY), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		return

	xbmcplugin.setContent(HANDLE, 'videos')
	for row in rows:
		card = _mdblist_list_card(row)
		if not card['imdb']:
			# No IMDb id, no stream lookup possible - same rule TMDB items follow.
			continue
		label = '%s (%s)' % (card['title'], card['year']) if card['year'] else card['title']
		li = xbmcgui.ListItem(label=label)
		apply_info(li, card, 'movie' if card['is_movie'] else 'tvshow')
		url_params = {
			'action': 'movie_streams' if card['is_movie'] else 'seasons',
			'imdb': card['imdb'], 'tmdb': card['tmdb'], 'title': card['title'], 'year': card['year'],
		}
		if card['is_movie']:
			url_params['mediatype'] = 'movie'
		url = '%s?%s' % (BASE_URL, urlencode(url_params))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
	xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def root_menu():
	xbmcplugin.setContent(HANDLE, 'videos')

	items = [
		(S_MOVIES, {'action': 'section', 'kind': 'movie'}),
		(S_SERIES, {'action': 'section', 'kind': 'tv'}),
		(S_ANIME, {'action': 'section', 'kind': 'anime'}),
		(S_SEARCH_MOVIES, {'action': 'search', 'media': 'movie'}),
		(S_SEARCH_SERIES, {'action': 'search', 'media': 'tv'}),
	]
	if _mdblist_ready():
		items.append((S_MDBLIST_UPNEXT, {'action': 'mdblist_upnext'}))
		items.append((S_MDBLIST_WATCHLIST, {'action': 'mdblist_watchlist'}))
		items.append((S_MDBLIST_MY_LISTS, {'action': 'mdblist_my_lists'}))
		items.append((S_MDBLIST_LIKED_LISTS, {'action': 'mdblist_liked_lists'}))
	for string_id, params in items:
		li = xbmcgui.ListItem(label=_(string_id))
		url = '%s?%s' % (BASE_URL, urlencode(params))
		xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

	settings_item = xbmcgui.ListItem(label=_(S_SETTINGS))
	settings_url = '%s?%s' % (BASE_URL, urlencode({'action': 'open_settings'}))
	xbmcplugin.addDirectoryItem(HANDLE, settings_url, settings_item, isFolder=True)

	xbmcplugin.endOfDirectory(HANDLE)


_SCROBBLE_KEYS = ('mediatype', 'imdbnumber', 'title', 'year', 'tvshowtitle', 'season', 'episode', 'poster')


def _scrobble_meta(params):
	meta = {k: params[k] for k in _SCROBBLE_KEYS if params.get(k)}
	for int_key in ('season', 'episode'):
		if int_key in meta:
			try:
				meta[int_key] = int(meta[int_key])
			except (TypeError, ValueError):
				del meta[int_key]
	return meta


def play_external(params):
	"""Entry point used by TMDb Helper (see resources/players/lumio.json).

	One resolvable entry point rather than two players: with auto-play off it
	shows a modal source picker instead of a directory, because a player
	declared resolvable has to answer with setResolvedUrl either way.
	"""
	is_episode = params.get('type') == 'episode'
	if is_episode:
		# TMDb Helper's {imdb} on an episode can be the EPISODE's own id, and
		# tt<episode>:1:1 is a stream id no addon serves. The series tmdb id it
		# also passes is unambiguous, so resolve from that first and keep
		# {imdb} only as a fallback.
		show = tmdb_details('tv', params['tmdb']) if params.get('tmdb') else None
		imdb_id = (show or {}).get('imdb') or params.get('imdb') or ''
	else:
		imdb_id = _movie_imdb(params)
	if not imdb_id:
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_NO_IMDB), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
		return

	meta = {'mediatype': 'episode' if is_episode else 'movie', 'imdbnumber': imdb_id,
	        'title': params.get('title') or '', 'year': params.get('year') or ''}
	if is_episode:
		meta.update({'tvshowtitle': params.get('showname') or '',
		             'season': params.get('season'), 'episode': params.get('episode')})
		video_id = '%s:%s:%s' % (imdb_id, params.get('season'), params.get('episode'))
	else:
		video_id = imdb_id
	meta = _scrobble_meta(meta)
	card = _card(params, meta)

	streams = playable_streams('series' if is_episode else 'movie', video_id)
	if not streams:
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_NO_STREAMS), xbmcgui.NOTIFICATION_INFO)
		xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
		return

	# Launching from TMDb Helper is a "play this" gesture, so it gets its own
	# switch: you can keep the source picker while browsing Lumio and still have
	# one-click playback from TMDb Helper.
	auto = (ADDON.getSetting('external_auto_play') == 'true'
	        or ADDON.getSetting('auto_play_best') == 'true')
	chosen = 0
	if not auto:
		labels = [stream_display(stream)[0] for stream in streams]
		chosen = xbmcgui.Dialog().select(_(S_PICK_SOURCE), labels)
		if chosen < 0:
			xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
			return
	resolve_and_play(streams[chosen]['url'], meta, None, card)


def _movie_imdb(params):
	"""IMDb id of a movie, from the URL or resolved from its TMDB id."""
	if params.get('imdb'):
		return params['imdb']
	details = tmdb_details('movie', params.get('tmdb'))
	if details is None:
		return ''
	if not details.get('imdb'):
		xbmcgui.Dialog().notification(ADDON_NAME, _(S_NO_IMDB), xbmcgui.NOTIFICATION_INFO)
	return details.get('imdb') or ''


def _screen(params):
	try:
		return max(1, int(params.get('screen') or 1))
	except ValueError:
		return 1


def router():
	params = dict(parse_qsl(sys.argv[2][1:]))
	action = params.get('action')
	if action == 'section':
		list_section(params.get('kind'))
	elif action == 'catalog':
		_browse(params.get('kind'), params.get('catalog'), _screen(params),
		        params.get('genre'), params.get('year'))
	elif action == 'genres':
		list_genres(params.get('kind'))
	elif action == 'years':
		list_years(params.get('kind'))
	elif action == 'search':
		media = 'movie' if params.get('media') == 'movie' else 'tv'
		prompt = S_SEARCH_MOVIES_PROMPT if media == 'movie' else S_SEARCH_SERIES_PROMPT
		search(media, prompt, _screen(params), params.get('query'))
	elif action == 'play_external':
		play_external(params)
	elif action == 'install_th_player':
		install_th_player()
	elif action == 'open_settings':
		open_settings()
	elif action == 'mdblist_connect':
		mdblist_connect()
	elif action == 'mdblist_disconnect':
		mdblist_disconnect()
	elif action == 'mdblist_upnext':
		list_upnext()
	elif action == 'mdblist_watchlist':
		list_mdblist_watchlist()
	elif action == 'mdblist_my_lists':
		list_mdblist_lists('user')
	elif action == 'mdblist_liked_lists':
		list_mdblist_lists('liked')
	elif action == 'mdblist_list_items':
		list_mdblist_list_items(params.get('listid'))
	elif action in ('movie_streams', 'movie_play_best'):
		imdb_id = _movie_imdb(params)
		meta = dict(_scrobble_meta(params), imdbnumber=imdb_id) if imdb_id else {}
		if not imdb_id:
			xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
		elif action == 'movie_streams':
			list_streams('movie', imdb_id, meta, _card(params, meta))
		else:
			play_best('movie', imdb_id, meta, None, _card(params, meta))
	elif action == 'seasons':
		imdb_id = series_imdb(params)
		if imdb_id:
			list_seasons(imdb_id, params.get('tmdb'))
		else:
			xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
	elif action == 'episodes':
		list_episodes(params.get('imdb'), params.get('season'), params.get('tmdb'))
	elif action in ('episode_streams', 'episode_play_best'):
		video_id = '%s:%s:%s' % (params.get('imdb'), params.get('season'), params.get('episode'))
		meta = _scrobble_meta(params)
		card = _card(params, meta)
		if action == 'episode_streams':
			list_streams('series', video_id, meta, card)
		else:
			play_best('series', video_id, meta, None, card)
	elif action == 'resolve':
		meta = _scrobble_meta(params)
		resolve_and_play(params.get('url'), meta, None, _card(params, meta))
	else:
		root_menu()


if __name__ == '__main__':
	router()

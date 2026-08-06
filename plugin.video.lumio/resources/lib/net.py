# -*- coding: utf-8 -*-
"""JSON over HTTP, stdlib only. Shared by the plugin and the background service."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Stream CDNs reject the default Python user agent, so everything goes out
# looking like a browser - including the playback request built in default.py.
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
TIMEOUT = 20


def get_json(url, timeout=TIMEOUT, headers=None):
	req_headers = {'User-Agent': UA}
	req_headers.update(headers or {})
	req = Request(url, headers=req_headers)
	with urlopen(req, timeout=timeout) as resp:
		return json.loads(resp.read().decode('utf-8'))


def post_json(url, payload, timeout=TIMEOUT, headers=None):
	body = json.dumps(payload).encode('utf-8')
	req_headers = {'Content-Type': 'application/json', 'User-Agent': UA}
	req_headers.update(headers or {})
	req = Request(url, data=body, method='POST', headers=req_headers)
	try:
		with urlopen(req, timeout=timeout) as resp:
			raw = resp.read().decode('utf-8')
	except HTTPError as e:
		# The Stremio API reports application errors as HTTP 200 with an
		# "error" key, but a genuine HTTP error still tends to carry a body
		# explaining why - read it rather than losing the reason.
		raw = e.read().decode('utf-8')
		if not raw:
			raise
	return json.loads(raw or '{}')


def check_url(url, timeout=6):
	"""True if url responds without a client/server error.

	Used to probe a "best" stream before committing to it: a top-ranked
	source is sometimes a dead/expired signed link on the provider's CDN,
	and a plain HEAD request is far cheaper than letting Kodi's player find
	that out after the fact with no fallback.
	"""
	req = Request(url, method='HEAD', headers={'User-Agent': UA})
	try:
		with urlopen(req, timeout=timeout) as resp:
			return 200 <= resp.status < 400
	except (HTTPError, URLError):
		return False


def post_form(url, fields, timeout=TIMEOUT, headers=None):
	"""application/x-www-form-urlencoded POST - what OAuth token endpoints expect."""
	body = urlencode(fields).encode('utf-8')
	req_headers = {'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': UA}
	req_headers.update(headers or {})
	req = Request(url, data=body, method='POST', headers=req_headers)
	try:
		with urlopen(req, timeout=timeout) as resp:
			raw = resp.read().decode('utf-8')
	except HTTPError as e:
		raw = e.read().decode('utf-8')
		if not raw:
			raise
	return json.loads(raw or '{}')

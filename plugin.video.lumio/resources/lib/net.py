# -*- coding: utf-8 -*-
"""JSON over HTTP, stdlib only. Shared by the plugin and the background service."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# Stream CDNs reject the default Python user agent, so everything goes out
# looking like a browser - including the playback request built in default.py.
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
TIMEOUT = 20


def get_json(url, timeout=TIMEOUT):
	req = Request(url, headers={'User-Agent': UA})
	with urlopen(req, timeout=timeout) as resp:
		return json.loads(resp.read().decode('utf-8'))


def post_json(url, payload, timeout=TIMEOUT):
	body = json.dumps(payload).encode('utf-8')
	req = Request(url, data=body, method='POST',
	              headers={'Content-Type': 'application/json', 'User-Agent': UA})
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

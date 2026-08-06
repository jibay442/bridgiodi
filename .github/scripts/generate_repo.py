#!/usr/bin/env python3
"""Builds the Kodi repository payload: per-addon zips, addons.xml, addons.xml.md5.

Run from the repo root (python3 .github/scripts/generate_repo.py). Scans
every top-level folder with an addon.xml - both plugin.video.bridgiodi and
the repository.bridgiodi pointer addon - zips each as <id>/<id>-<version>.zip,
and writes the concatenated addons.xml plus its md5 checksum: the two files
Kodi polls to detect a new version is available.

Output goes to ./zips, which the release workflow publishes to gh-pages as
the repository root (so addons.xml ends up at the Pages root, matching what
repository.bridgiodi/addon.xml points at).
"""
import hashlib
import os
import shutil
import sys
import xml.etree.ElementTree as ET

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(REPO_ROOT, 'zips')

# Top-level entries that are never addons, even though they sit at repo root.
EXCLUDE = {'.git', '.github', 'zips', 'scripts', 'node_modules'}


def find_addons():
	for name in sorted(os.listdir(REPO_ROOT)):
		if name in EXCLUDE or name.startswith('.'):
			continue
		addon_xml = os.path.join(REPO_ROOT, name, 'addon.xml')
		if os.path.isfile(addon_xml):
			yield name, addon_xml


def zip_addon(addon_id, version):
	dest_dir = os.path.join(OUTPUT_DIR, addon_id)
	os.makedirs(dest_dir, exist_ok=True)
	zip_base = os.path.join(dest_dir, '%s-%s' % (addon_id, version))
	# make_archive appends the .zip suffix itself; root_dir/base_dir together
	# make the zip's internal paths start with "<addon_id>/...", which is
	# exactly the layout Kodi expects when it unpacks an update.
	return shutil.make_archive(zip_base, 'zip', root_dir=REPO_ROOT, base_dir=addon_id)


def main():
	if os.path.isdir(OUTPUT_DIR):
		shutil.rmtree(OUTPUT_DIR)
	os.makedirs(OUTPUT_DIR, exist_ok=True)

	addons_root = ET.Element('addons')
	built = []
	for addon_id, addon_xml_path in find_addons():
		root = ET.parse(addon_xml_path).getroot()
		if root.tag != 'addon' or root.get('id') != addon_id:
			print('skip %s: addon.xml id mismatch or malformed' % addon_id, file=sys.stderr)
			continue
		version = root.get('version')
		addons_root.append(root)
		zip_path = zip_addon(addon_id, version)
		built.append((addon_id, version, zip_path))

	if not built:
		print('no addons found - nothing to do', file=sys.stderr)
		sys.exit(1)

	addons_xml_path = os.path.join(OUTPUT_DIR, 'addons.xml')
	ET.ElementTree(addons_root).write(addons_xml_path, encoding='UTF-8', xml_declaration=True)

	with open(addons_xml_path, 'rb') as f:
		digest = hashlib.md5(f.read()).hexdigest()
	with open(addons_xml_path + '.md5', 'w', encoding='utf-8') as f:
		f.write(digest)

	write_index_html(built)

	print('addons.xml.md5: %s' % digest)
	for addon_id, version, zip_path in built:
		print('%s %s -> %s' % (addon_id, version, os.path.relpath(zip_path, REPO_ROOT)))


def write_index_html(built):
	"""A plain download page at the Pages root - otherwise hitting the bare
	repo URL with no filename 404s, since there's no directory listing."""
	repo_row = next((b for b in built if b[0] == 'repository.bridgiodi'), None)
	other_rows = [b for b in built if b[0] != 'repository.bridgiodi']

	def link(addon_id, version, zip_path):
		href = '%s/%s' % (addon_id, os.path.basename(zip_path))
		return '<li><a href="%s">%s %s</a></li>' % (href, addon_id, version)

	repo_section = ''
	if repo_row:
		repo_section = '<p><a href="%s/%s">Download the Kodi repository zip</a> (install this once in Kodi).</p>' % (
			repo_row[0], os.path.basename(repo_row[2]))

	other_section = ''
	if other_rows:
		other_section = '<ul>%s</ul>' % ''.join(link(*row) for row in other_rows)

	html = """<!doctype html>
<html><head><meta charset="utf-8"><title>Bridgiodi Kodi repository</title></head>
<body>
<h1>Bridgiodi Kodi repository</h1>
%s
%s
<p><a href="addons.xml">addons.xml</a></p>
</body></html>
""" % (repo_section, other_section)

	with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
		f.write(html)


if __name__ == '__main__':
	main()

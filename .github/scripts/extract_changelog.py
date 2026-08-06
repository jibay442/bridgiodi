#!/usr/bin/env python3
"""Prints the CHANGELOG.md section for one version - used as GitHub Release notes.

Usage: python3 .github/scripts/extract_changelog.py 1.0.0
"""
import re
import sys


def main():
	if len(sys.argv) != 2:
		print('usage: extract_changelog.py <version>', file=sys.stderr)
		sys.exit(1)
	version = sys.argv[1]
	text = open('CHANGELOG.md', encoding='utf-8').read()
	pattern = re.compile(
		r'^## \[%s\][^\n]*\n(.*?)(?=\n## \[|\Z)' % re.escape(version), re.S | re.M)
	match = pattern.search(text)
	if not match:
		print('_No changelog entry found for %s in CHANGELOG.md._' % version)
		return
	print(match.group(1).strip())


if __name__ == '__main__':
	main()

#!/usr/bin/env python3

"""
Usage: python3 ./devscripts/update-formulae.py <path-to-formulae-rb> <version>
version can be either 0-aligned (yt-dlp version) or normalized (PyPi version)
"""

# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from devscripts.utils import read_file, write_file

filename, sha256sum, version, url = sys.argv[1:]

normalized_version = '.'.join(str(int(x)) for x in version.split('.'))

formulae_text = read_file(filename)

formulae_text = re.sub(r'sha256 "[0-9a-f]*?" # replace-marker', 'sha256 "%s" # replace-marker' % sha256sum, formulae_text)
formulae_text = re.sub(r'version "[^"]*?" # replace-marker', 'version "%s" # replace-marker' % version, formulae_text)
formulae_text = re.sub(r'url "[^"]*?" # replace-marker', 'url "%s" # replace-marker' % url, formulae_text)

write_file(filename, formulae_text)

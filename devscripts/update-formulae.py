#!/usr/bin/env python3
from __future__ import unicode_literals

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


filename, sha256sum, version, url = sys.argv[1:]

normalized_version = '.'.join(str(int(x)) for x in version.split('.'))

with open(filename, 'r') as r:
    formulae_text = r.read()

formulae_text = re.sub(r'sha256 "[0-9a-f]*?" # replace-marker', 'sha256 "%s" # replace-marker' % sha256sum, formulae_text)
formulae_text = re.sub(r'version "[^"]*?" # replace-marker', 'version "%s" # replace-marker' % version, formulae_text)
formulae_text = re.sub(r'url "[^"]*?" # replace-marker', 'url "%s" # replace-marker' % url, formulae_text)

with open(filename, 'w') as w:
    w.write(formulae_text)

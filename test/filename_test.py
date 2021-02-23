#!/usr/bin/env python3
from __future__ import unicode_literals

import sys

filename = sys.argv[1]

sys.exit(0 if "it's a small world" in filename.lower() else 1)

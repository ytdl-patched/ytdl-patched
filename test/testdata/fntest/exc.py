#!/usr/bin/env python3
from __future__ import unicode_literals

if __name__ == '__main__':
    import sys

    filename = sys.argv[1]

    sys.exit(0 if "it's a small world" in filename.lower() else 1)

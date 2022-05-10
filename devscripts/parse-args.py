# A script to parse options and return dict representation of it

import sys
import os
import pprint
sys.path[:0] = ['.', 'devscripts']

from yt_dlp import parse_options

if os.getenv('FULL_DICT') == 'y':
    none_opts = {}
else:
    _, _, _, none_opts = parse_options([''], ignore_config_files=True)

_, _, _, parsed = parse_options(ignore_config_files=True)

for k, nv in none_opts.items():
    if k not in parsed:
        continue
    pv = parsed[k]
    if pv == nv:
        parsed.pop(k, None)

pprint.pprint(parsed)

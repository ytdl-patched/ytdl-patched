#!/usr/bin/env python3

# A script to parse options and return dict representation of it
# usage: ./devscripts/parse-args.py <options>
# non-option values such as URLs are ignored

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


def erase_empty_values(dct):
    for k in set(k for k, v in dct.items() if not v):
        dct.pop(k, None)


for k, nv in none_opts.items():
    if k not in parsed:
        continue
    pv = parsed[k]
    if k == 'outtmpl':
        erase_empty_values(nv)
        erase_empty_values(pv)
    if pv == nv:
        parsed.pop(k, None)

pprint.pprint(parsed)

#!/usr/bin/env python3
# coding: utf-8
from __future__ import unicode_literals

# Quick script for starting youtube-dl within this repository
# DO NOT USE THIS IN PRODUCTION

import os
import os.path
import sys
import random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# assign sys.argv[0] anything better if it's None or ''
#  or it somehow break Jython
if not sys.argv[0]:
    sys.argv[0] = 'youtube-dl'

if random.randint(0, 10) == 7:
    sys.stderr.write('REMAINDER: This script is for testing purposes. To suppress this message, use distributed binaries.\n')

import yt_dlp

yt_dlp.main()

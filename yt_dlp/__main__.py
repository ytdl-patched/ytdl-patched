#!/usr/bin/env python3

# Execute with
# $ python -m yt_dlp

import sys

if __package__ is None and not hasattr(sys, 'frozen'):
    # direct call of __main__.py
    import os.path
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

# assign sys.argv[0] anything better if it's None or ''
#  or it somehow break Jython
if not sys.argv[0]:
    sys.argv[0] = 'youtube-dl'

import yt_dlp

if __name__ == '__main__':
    yt_dlp.main()

# coding: utf-8
from __future__ import unicode_literals, print_function
import json

import sys
import optparse

sys.path[:0] = ['.']

from youtube_dl.extractor.common import InfoExtractor
from youtube_dl.update import fetch_feed
from test.helper import FakeYDL


class TestIE(InfoExtractor):
    pass


ie = TestIE(FakeYDL({'verbose': False}))
script_id = 'versions.json'
slug = fetch_feed(ie._downloader)["update"]["slug"]

try:
    versions = ie._download_json(
        f"https://github.com/{slug}/raw/gh-pages/versions.json",
        script_id, 'Downloading old versions.py')
except BaseException:
    versions = {
        "versions": {},
        "latest": None,
    }

parser = optparse.OptionParser()
parser.add_option('--windows-default', dest='windows_default')
parser.add_option('--hash-windows-red', dest='hash_windows_red')
parser.add_option('--hash-windows-white', dest='hash_windows_white')
parser.add_option('--hash-bin', dest='hash_bin')
parser.add_option('--hash-tar', dest='hash_tar')
parser.add_option('--version', dest='version')
parser.add_option('--version-numeric', dest='version_numeric')

parsed, _ = parser.parse_args()

versions['latest'] = parsed.version
versions['versions'][parsed.version] = {
    'bin': [
        f"https://github.com/{slug}/releases/download/{parsed.version_numeric}/youtube-dl",
        parsed.hash_bin,
    ],
    'tar': [
        f"https://github.com/{slug}/releases/download/{parsed.version_numeric}/youtube-dl.tar.gz",
        parsed.hash_tar,
    ],
    'exe': [
        f"https://github.com/{slug}/releases/download/{parsed.version_numeric}/youtube-dl-{parsed.windows_default}.exe",
        getattr(parsed, f'hash_windows_{parsed.windows_default}'),
    ],
    'exe-red': [
        f"https://github.com/{slug}/releases/download/{parsed.version_numeric}/youtube-dl-red.exe",
        parsed.hash_windows_red,
    ],
    'exe-white': [
        f"https://github.com/{slug}/releases/download/{parsed.version_numeric}/youtube-dl-white.exe",
        parsed.hash_windows_white,
    ],
}

print(json.dumps(versions))

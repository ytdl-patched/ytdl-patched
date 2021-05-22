# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)


class AskMonaIE(InfoExtractor):
    IE_NAME = 'askmona'
    _VALID_URL = r'https?://(?:www\.)?askmona.org/(?P<id>\d+)/?'
    ALL_POSTS_URL = 'https://askmona.org/%s?n=1000'
    YOUTUBE_RE = r'<a\s+class="youtube"\s*name="([0-9A-Za-z_-]{11})"\s*href="[^"]*"\s*>'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(self.ALL_POSTS_URL % video_id, video_id)

        youtube_results = [self.url_result('https://youtu.be/%s' % frg.group(1))
                           for frg in re.finditer(self.YOUTUBE_RE, webpage)]
        if not youtube_results:
            raise ExtractorError('No videos found', expected=True)
        return self.playlist_result(youtube_results, video_id)


class AskMona3IE(AskMonaIE):
    IE_NAME = 'askmona3'
    _VALID_URL = r'https?://web3\.askmona.org/(?P<id>\d+)/?'
    ALL_POSTS_URL = 'https://web3.askmona.org/%s?n=1000'

# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import ExtractorError

from .youtube import (
    YoutubeIE,
    YoutubePlaylistIE,
    YoutubeTabIE,
)
from .twitter import TwitterIE


class PeingIE(InfoExtractor):
    IE_NAME = 'peing'
    _VALID_URL = r'https?://(?:www\.)?peing\.net/(?:../)?q/(?P<id>[a-f0-9-]{36})'
    # extractors to be searched against
    _SEARCH_IE = (YoutubeIE, YoutubePlaylistIE, YoutubeTabIE, TwitterIE)

    _TEST = {
        'url': 'https://peing.net/ja/q/483f91de-f607-4384-ba5a-28ca22a3aa67',
        'info_dict': {},
        'add_ie': YoutubeIE.ie_key(),
    }

    def _real_extract(self, url):
        question_id = self._match_id(url)
        webpage = self._download_webpage(url, question_id)

        content = self._html_search_meta(
            ('twitter:image:alt', 'og:image:alt'),
            webpage) or self._search_regex(
            (r'<img\s+alt="(.+?)"\s*class="question-eye-catch"\s*onerror="',
             r'<title>(.+?)\s*\|'),
            webpage, 'alternative text', fatal=False)
        if not content:
            raise ExtractorError('Cannot extract alternative text')

        matches = [self.url_result(x.group(0)) for ie in self._SEARCH_IE for x in re.finditer(self.remove_anchors(ie._VALID_URL), content)]
        if not matches:
            raise ExtractorError('There is no video URLs here', expected=True)

        return self.playlist_result(matches, question_id)

    @staticmethod
    def remove_anchors(regex):
        for rr in (r'^\s*(\(\?[a-z]+\))?\s*\^', r'()\$\s*$'):
            regex = re.sub(rr, r'\g<1>', regex)
        return regex

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


class QAWebsitesBaseIE(InfoExtractor):
    # extractors to be searched against
    _SEARCH_IE = (YoutubeIE, YoutubePlaylistIE, YoutubeTabIE, TwitterIE)

    def _extract_text(self, url):
        " Implement this in subclasses "
        return ('question', 'answer')

    def _real_extract(self, url):
        question_id = self._match_id(url)
        (question_text, answer_text) = self._extract_text(url)

        if not question_text and not answer_text:
            raise ExtractorError('Nothing is present')
        if not question_text:
            self.report_warning('Cannot extract question text')
        if not answer_text:
            self.report_warning('Cannot extract answer text')

        matches = set(
            x.group(0)
            for message in (question_text, answer_text)
            for ie in self._SEARCH_IE
            for x in re.finditer(self.remove_anchors(ie._VALID_URL), message))
        if not matches:
            raise ExtractorError('There is no video URLs here', expected=True)

        return self.playlist_result([self.url_result(x) for x in matches], question_id)

    @staticmethod
    def remove_anchors(regex):
        for rr in (r'^\s*(\(\?[a-z]+\))?\s*\^', r'()\$\s*$'):
            regex = re.sub(rr, r'\g<1>', regex)
        return regex


class PeingIE(QAWebsitesBaseIE):
    IE_NAME = 'peing'
    _VALID_URL = r'https?://(?:www\.)?peing\.net/(?:(?:en|ja|zh-CN|zh-TW|ko|dt|th)/)?q/(?P<id>[a-f0-9-]{36})'

    _TEST = {
        'url': 'https://peing.net/ja/q/483f91de-f607-4384-ba5a-28ca22a3aa67',
        'info_dict': {},
        'add_ie': YoutubeIE.ie_key(),
    }

    def _extract_text(self, url):
        question_id = self._match_id(url)
        webpage = self._download_webpage(url, question_id)

        question_text = self._html_search_meta(
            ('twitter:image:alt', 'og:image:alt'),
            webpage) or self._search_regex(
            (r'<img\s+alt="(.+?)"\s*class="question-eye-catch"\s*onerror="',
             r'data-item-body=\'(.+?)\'',
             r'<title>(.+?)\s*\|'),
            webpage, 'question text', fatal=False) or ''

        answer_text = self._html_search_meta(
            'description', webpage) or self._search_regex(
            r"<p\s+class=(['\"])text\1>(.+?)</p>", webpage,
            'answer text', fatal=False, group=2) or ''

        return (question_text, answer_text)

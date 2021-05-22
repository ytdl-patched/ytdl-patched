# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import ExtractorError, clean_html, unescapeHTML

from .youtube import (
    YoutubeIE,
    YoutubePlaylistIE,
    YoutubeTabIE,
)
from .twitter import TwitterIE
from .instagram import InstagramIE


class QAWebsitesBaseIE(InfoExtractor):
    # extractors to be searched against
    _SEARCH_IE = (InstagramIE, YoutubeIE, YoutubePlaylistIE, YoutubeTabIE, TwitterIE)

    def _extract_text(self, url):
        " Implement this in subclasses "
        return ('question', 'answer')

    def _real_extract(self, url):
        question_id = self._match_id(url)
        question_text, answer_text = self._extract_text(url)

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

        return question_text, answer_text


class AskfmIE(QAWebsitesBaseIE):
    IE_NAME = 'ask.fm'
    _VALID_URL = r'https?://ask\.fm/(?P<uploader>[^/]+)/answers/(?P<id>\d+)'

    def _extract_text(self, url):
        question_id = self._match_id(url)
        webpage = self._download_webpage(url, question_id)

        question_text = self._html_search_meta(
            ('og:title'), webpage) or self._search_regex(
            (r'<h1 class="medium">(.+?)</h1>',
             r'data-item-body=\'(.+?)\'',
             r'<title>(.+?)\s*\|'),
            webpage, 'question text', fatal=False)
        if not question_text:
            params = self._search_regex(r'data-params="(.+?)"', webpage, 'question text', fatal=False)
            params = unescapeHTML(params)
            params = self._parse_json(params, question_id, fatal=False)
            if params:
                question_text = params['question[question_text]']
        if not question_text:
            question_text = ''

        answer_text = self._search_regex(
            r'<div class="streamItem_content">(.+?)</div>', webpage,
            'answer text', fatal=False) or self._html_search_meta(
            ('og:description', 'description'), webpage) or ''

        return question_text, answer_text


class MarshmallowQAIE(QAWebsitesBaseIE):
    IE_NAME = 'marshmallow-qa'
    _VALID_URL = r'https?://(?:www\.)?marshmallow-qa\.com/messages/(?P<id>[a-f0-9-]{36})'

    _TEST = {
        'url': 'https://marshmallow-qa.com/messages/513fb153-8e9b-4173-bea9-2210339dd81e',
        'only_matching': True,
    }

    def _extract_text(self, url):
        question_id = self._match_id(url)
        webpage = self._download_webpage(url, question_id)

        question_text = self._search_regex(
            (r'<meta property="(?:og|twitter):title" content="(.+?)\s*\|\s*[^"]+?"\s*/>',
             r'<div data-target="obscene-word\.content">(.+?)</div>',
             r'<title>\s*(.+?)\s*\|'),
            webpage, 'question text', fatal=False) or ''

        answer_text = self._search_regex(
            r'<div class="answer-content pre-wrap text-dark" data-target="obscene-word\.content">(.+?)</div>',
            webpage, 'answer text', fatal=False) or ''

        return question_text, answer_text


class MottohometeIE(QAWebsitesBaseIE):
    IE_NAME = 'mottohomete'
    _VALID_URL = r'https?://(?:www\.)?mottohomete\.net/letters/(?P<id>[a-f0-9-]{36})'

    _TEST = {
        'url': 'https://www.mottohomete.net/letters/cbfc80f6-61b4-44c1-9772-b2de9702f1ce',
        'only_matching': True,
    }

    def _extract_text(self, url):
        question_id = self._match_id(url)
        webpage = self._download_webpage(url, question_id)

        question_text = self._html_search_meta(
            ('twitter:title', 'og:title'),
            webpage)
        if not question_text:
            question_text = self._search_regex(
                r"(?s)<div class='panel-heading'>\s*<div class='cwrap'><p>(.+?)</p>",
                webpage, 'question text', fatal=False)
            question_text = clean_html(question_text)
        if not question_text:
            question_text = ''

        answer_text = self._search_regex(
            r"(?s)<div class='panel-body'>\s*<div class='cwrap'><p>(.+?)</p>",
            webpage, 'answer text', fatal=False) or ''

        return question_text, answer_text

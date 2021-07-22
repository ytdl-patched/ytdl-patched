# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    smuggle_url,
    unescapeHTML,
)


class GorinLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gorin\.jp/live/(?P<id>[A-Za-z0-9_-]+)'
    _TESTS = [{
        'url': 'https://gorin.jp/live/BSBWSBLTEAM9----------GP--000500--/',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        rdet = self._search_regex(
            r'data-json="(.+?)"', webpage, 'details', group=1)
        rdet = unescapeHTML(rdet)
        details = self._parse_json(rdet, video_id)
        live = details['live']

        # all uses this account
        p_id = '4774017240001'
        r_id = live['video_id']
        bc_url = smuggle_url(
            self.BRIGHTCOVE_URL_TEMPLATE % (p_id, r_id),
            {'geo_countries': ['JP']})

        return {
            '_type': 'url_transparent',
            'title': live['title'],
            'url': bc_url,
            'ie_key': 'BrightcoveNew',
        }


class GorinVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gorin\.jp/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://gorin.jp/video/6264589782001/',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        rdet = self._search_regex(
            r'data-json="(.+?)"', webpage, 'details', group=1)
        rdet = unescapeHTML(rdet)
        details = self._parse_json(rdet, video_id)

        # all uses this account
        p_id = '4774017240001'
        r_id = details.get('video_id') or video_id
        bc_url = smuggle_url(
            self.BRIGHTCOVE_URL_TEMPLATE % (p_id, r_id),
            {'geo_countries': ['JP']})

        return {
            '_type': 'url_transparent',
            'url': bc_url,
            'ie_key': 'BrightcoveNew',
        }

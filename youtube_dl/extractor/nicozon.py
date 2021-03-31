# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from .niconico import NiconicoIE
from ..utils import (
    ExtractorError,
    lowercase_escape,
)


class NicozonIE(InfoExtractor):
    IE_NAME = 'nicozon'
    _VALID_URL = r'(?:https?://www\.nicozon\.net/downloader\.html\?video_id=|nicozon:(?:%s)?)(?P<id>(?:[a-z]{2})?[0-9]+)' % NiconicoIE._VALID_URL[0:-27]
    IE10_USERAGENT = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)'
    _WORKING = False  # WIP

    def _real_extract(self, url):
        try:
            import yaml
        except ImportError as ex:
            raise ExtractorError('Please install pyyaml and try again.', expected=True, cause=ex)

        video_id = self._match_id(url)
        url = 'http://www.nicozon.net/downloader.html?video_id=%s&eco=1' % video_id
        _headers = {
            'User-Agent': self.IE10_USERAGENT,
        }

        niconico_thumb_watch_js = self._download_webpage(
            'http://ext.nicovideo.jp/thumb_watch/%s?w=1&h=1&n=1' % video_id, video_id, headers=_headers,
            note='Fetching niconico old player')
        nicozon_video_url = self._download_webpage(
            'http://www.nicozon.net/mp4/%s' % video_id, video_id, headers=_headers,
            note='Fetching video URL').strip()

        # data set for Nicovideo.MiniPlayer is mostly valid as YAML, so it can be parsed as below
        niconico_video_data = yaml.safe_load(self._search_regex(r'(?s)Nicovideo\.Video\(({.+})\);', niconico_thumb_watch_js, 'niconico info data', group=1).replace('\t', ''))
        niconico_player_data = yaml.safe_load(self._search_regex(r'(?s)video,\s*({.+}),\s*\'', niconico_thumb_watch_js, 'niconico info data', group=1).replace('\t', ''))

        tap_url = 'http://ext.nicovideo.jp/thumb_watch/' + video_id + '?w=1&h=1&n=1'
        self._download_webpage(tap_url, video_id, note='Tapping thumb_watch URL 1', headers=_headers, fatal=False)

        tap_url = 'http://ext.nicovideo.jp/thumb_watch?as3=1&v=' + video_id + '&k=' + niconico_player_data.get('thumbPlayKey', 'undefined') + '&accessFromHash=' + niconico_player_data.get('accessFromHash', 'undefined') + '&accessFromDomain=' + niconico_player_data.get('accessFromDomain', 'undefined')
        self._download_webpage(tap_url, video_id, note='Tapping thumb_watch URL 2', headers=_headers, fatal=False)

        if nicozon_video_url.endswith('low'):
            nicozon_video_url = nicozon_video_url[0:-3]

        _headers['Referer'] = 'http://smile-ccm12.nicovideo.jp/'

        formats = [{
            'format_id': 'flv',
            'url': nicozon_video_url.replace('/smile?v=', '/smile?m='),
            'ext': 'flv',
            'http_headers': _headers,
        }, {
            'format_id': 'economy',
            'url': nicozon_video_url + 'low',
            'ext': 'mp4',
            'http_headers': _headers,
        }, {
            'format_id': 'high',
            'url': nicozon_video_url,
            'ext': 'mp4',
            'http_headers': _headers,
        }]

        return {
            'id': video_id,
            'title': lowercase_escape(niconico_video_data.get('title')),
            'description': lowercase_escape(niconico_video_data.get('description')),
            'formats': formats,
        }

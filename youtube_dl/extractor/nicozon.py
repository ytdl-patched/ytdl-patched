# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from .niconico import NiconicoIE
from ..utils import (
    lowercase_escape,
    try_get,
)
from ..compat import (
    compat_parse_qs,
    compat_urllib_parse,
    compat_str,
)


class NicozonIE(InfoExtractor):
    IE_NAME = 'nicozon'
    _VALID_URL = r'(?:https?://www\.nicozon\.net/downloader\.html\?video_id=|nicozon:(?:%s)?)(?P<id>(?:[a-z]{2})?[0-9]+)' % NiconicoIE._URL_BEFORE_ID_PART
    IE10_USERAGENT = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)'
    _WORKING = False  # WIP
    _FEATURE_DEPENDENCY = ('yaml', )

    def _real_extract(self, url):
        # TODO: dig into SWF file if it's possible
        # NOTE: SWF: http://ext.nicovideo.jp/swf/player/thumbwatch.swf?ts=1556178770
        # NOTE: SWF is ActionScript 3.0, which Ruffle cannot support
        import yaml

        video_id = self._match_id(url)
        _headers = {'User-Agent': self.IE10_USERAGENT}

        niconico_thumb_watch_js = self._download_webpage(
            'http://ext.nicovideo.jp/thumb_watch/%s?thumb_mode=html&redirect=1' % video_id, video_id, headers=_headers,
            note='Fetching niconico old player')

        # data set for Nicovideo.MiniPlayer is mostly valid as YAML, so it can be parsed as below
        niconico_video_data = yaml.safe_load(self._search_regex(r'(?s)Nicovideo\.Video\(({.+})\);', niconico_thumb_watch_js, 'niconico info data', group=1).replace('\t', ''))
        niconico_player_data = yaml.safe_load(self._search_regex(r'(?s)video,\s*({.+}),\s*\'', niconico_thumb_watch_js, 'niconico info data', group=1).replace('\t', ''))

        tap_url = 'http://ext.nicovideo.jp/thumb_watch?as3=1&v=' + video_id + '&k=' + niconico_player_data.get('thumbPlayKey', 'undefined')
        thumb_watch_data = self._download_webpage(tap_url, video_id, note='Tapping thumb_watch URL', headers=_headers, fatal=False)
        twd_parsed = compat_parse_qs(thumb_watch_data)

        video_url = twd_parsed['url'][0]
        if video_url.endswith('low'):
            video_url = video_url[0:-3]

        url_parsed = compat_urllib_parse.urlparse(video_url)

        video_tag = try_get(
            compat_parse_qs(url_parsed.query),
            (lambda x: x['v'][0],
             lambda x: x['m'][0],),
            compat_str)

        _headers['Referer'] = compat_urllib_parse.urlunparse(url_parsed._replace(
            path='/', params='', query='', fragment=''))

        formats = [{
            'format_id': 'flv',
            'url': compat_urllib_parse.urlunparse(url_parsed._replace(query='m=%s' % video_tag)),
            'ext': 'flv',
            'http_headers': _headers,
        }, {
            'format_id': 'economy',
            'url': compat_urllib_parse.urlunparse(url_parsed._replace(query='v=%slow' % video_tag)),
            'ext': 'mp4',
            'http_headers': _headers,
        }, {
            'format_id': 'high',
            'url': compat_urllib_parse.urlunparse(url_parsed._replace(query='v=%s' % video_tag)),
            'ext': 'mp4',
            'http_headers': _headers,
        }]

        return {
            'id': video_id,
            'title': lowercase_escape(niconico_video_data.get('title')),
            'description': lowercase_escape(niconico_video_data.get('description')),
            'formats': formats,
        }

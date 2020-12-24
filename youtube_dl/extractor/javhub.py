# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    decode_base,
    encode_base,
    scalar_to_bytes,
)


class JavhubIE(InfoExtractor):
    IE_NAME = 'javhub'
    _VALID_URL = r'https://(?:ja\.)?javhub\.net/play/(?P<id>[^/]+)'

    B58_TABLE_1 = '23456789ABCDEFGHJKLNMPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz1'
    B58_TABLE_2 = '789ABCDEFGHJKLNMPQRSTUVWX23456YZabcdefghijkmnopqrstuvwxyz1'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data_src = self._search_regex(r'data-src="([^\"]+)"(?:>| data-track)', webpage, 'data-src')
        data_track = self._search_regex(r'data-track="([^\"]+)">', webpage, 'data-track', fatal=False)

        playapi_post = encode_base(decode_base(data_src, self.B58_TABLE_2), self.B58_TABLE_1).encode('utf8')
        if data_track:
            webvtt_url = scalar_to_bytes(decode_base(data_track, self.B58_TABLE_2)).decode('utf8')
        else:
            webvtt_url = None

        playapi_response = self._download_json(
            'https://ja.javhub.net/playapi', video_id,
            data=b'data=%s' % playapi_post, headers={'Referer': url})
        mp4_url = playapi_response.get('playurl')
        if not mp4_url:
            raise ExtractorError('Server returned invalid data')
        mp4_url = scalar_to_bytes(decode_base(mp4_url, self.B58_TABLE_2)).decode('utf8')

        result = self._search_json_ld(webpage, video_id)
        title = self._search_regex(r'<h5[^>]+?>(.+)</h5>', webpage, 'title', default=None)
        if not title and result.get('title'):
            title = result['title']
        if not title:
            title = self._html_extract_title(webpage, 'html title', default=None, fatal=False)

        if title:
            title = re.sub(r'^(?:無料動画|Watch Free Jav)\s+', '', title)

        result.update({
            'id': video_id,
            'title': title,
            'formats': [{
                'url': mp4_url,
                'protocol': 'http',
                'ext': determine_ext(mp4_url),
                'http_headers': {
                    'Referer': url,
                },
            }],
        })
        if webvtt_url:
            result.update({
                'subtitles': {
                    # unknown language
                    'xx': [{
                        'url': webvtt_url,
                        'ext': determine_ext(webvtt_url),
                    }]
                },
            })
        return result

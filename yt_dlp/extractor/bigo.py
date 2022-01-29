# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import ExtractorError


class BigoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bigo\.tv/(?:[a-z]{2,}/)?(?P<id>[^/]+)'
    # Note: I would like to provide some real test, but Bigo is a live streaming
    # site, and a test would require that the broadcaster is live at the moment.
    # So, I don't have a good way to provide a real test here.
    _TESTS = [{
        'url': 'https://www.bigo.tv/th/Tarlerm1304',
        'only_matching': True,
    }, {
        'url': 'https://bigo.tv/115976881',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)

        info_raw = self._download_json(
            'https://bigo.tv/studio/getInternalStudioInfo',
            user_id, form_params={'siteId': user_id})

        if info_raw.get('code'):
            raise ExtractorError(
                f'{info_raw["msg"]} (code {info_raw["code"]})', expected=True)
        info = info_raw.get('data') or {}

        if not info.get('alive'):
            raise ExtractorError('This user is offline.', expected=True)

        # formats = self._extract_m3u8_formats(
        #     info.get('hls_src'), user_id, ext='mp4')
        formats = [{
            'url': info.get('hls_src'),
            'ext': 'mp4',
            'protocol': 'm3u8',
            'is_live': True,
        }]

        return {
            'id': info.get('roomId') or user_id,
            'title': info.get('roomTopic'),
            'formats': formats,
            'thumbnail': info.get('snapshot'),
            'uploader': info.get('nick_name'),
            'uploader_id': user_id,
            'is_live': True,
        }

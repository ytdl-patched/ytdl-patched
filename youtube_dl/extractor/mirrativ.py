from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)


class MirrativIE(InfoExtractor):
    IE_NAME = 'mirrativ'
    # https://www.mirrativ.com/live/b2vcu4w2L_E5btV0bM7bdQ
    _VALID_URL = r'https?://(?:www.)?mirrativ\.com/live/(?P<id>[^/?#&]+)'
    LIVE_API_URL = 'https://www.mirrativ.com/api/live/live?live_id=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://www.mirrativ.com/live/%s' % video_id, video_id)
        live_response = self._download_json(self.LIVE_API_URL % video_id, video_id)
        # self.to_screen(live_response)

        hls_url = None
        is_live = False
        if live_response.get('archive_url_hls'):
            hls_url = live_response['archive_url_hls']
        elif live_response.get('streaming_url_hls'):
            hls_url = live_response['streaming_url_hls']
            is_live = True
        else:
            raise ExtractorError('no formats found')

        formats = self._extract_m3u8_formats(
            hls_url, video_id,
            ext='mp4', entry_protocol='m3u8_native',
            m3u8_id='hls', live=is_live)

        title = self._og_search_title(webpage, default=None) or self._search_regex(
            r'<title>\s*(.+?) - Mirrativ\s*</title>', webpage) or live_response.get('title')
        description = live_response.get('description')
        thumbnail = live_response.get('image_url')

        owner = live_response.get('owner', {})
        uploader = owner.get('name')
        uploader_id = owner.get('user_id')

        return {
            'id': video_id,
            'title': title,
            'is_live': is_live,
            'description': description,
            'formats': formats,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'uploader_id': uploader_id,
        }

from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import ExtractorError


class MirrativBaseIE(InfoExtractor):
    def assert_error(self, response):
        error_message = response.get('status', {}).get('error')
        if error_message:
            raise ExtractorError('Mirrativ says: %s' % error_message, expected=True)


class MirrativIE(MirrativBaseIE):
    IE_NAME = 'mirrativ'
    _VALID_URL = r'https?://(?:www.)?mirrativ\.com/live/(?P<id>[^/?#&]+)'
    LIVE_API_URL = 'https://www.mirrativ.com/api/live/live?live_id=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://www.mirrativ.com/live/%s' % video_id, video_id)
        live_response = self._download_json(self.LIVE_API_URL % video_id, video_id)
        self.assert_error(live_response)

        hls_url = None
        is_live = False
        if live_response.get('archive_url_hls'):
            hls_url = live_response['archive_url_hls']
        elif live_response.get('streaming_url_hls'):
            hls_url = live_response['streaming_url_hls']
            is_live = True
        else:
            raise ExtractorError('Live has ended, and has no archive saved', expected=True)

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


class MirrativUserIE(MirrativBaseIE):
    IE_NAME = 'mirrativ:user'
    _VALID_URL = r'https?://(?:www.)?mirrativ\.com/user/(?P<id>\d+)'
    LIVE_HISTORY_API_URL = 'https://www.mirrativ.com/api/live/live_history?user_id=%s&page=%d'
    USER_INFO_API_URL = 'https://www.mirrativ.com/api/user/profile?user_id=%s'

    def _real_extract(self, url):
        user_id = self._match_id(url)
        user_info = self._download_json(
            self.USER_INFO_API_URL % user_id, user_id,
            note='Downloading user info', fatal=False)
        self.assert_error(user_info)

        if user_info:
            uploader, description = user_info.get('name'), user_info.get('description')
        else:
            uploader, description = [None] * 2

        entries = []
        page = 1
        while page is not None:
            api_response = self._download_json(
                self.LIVE_HISTORY_API_URL % (user_id, page), user_id,
                note='Downloading page %d' % page)
            self.assert_error(api_response)
            lives = api_response.get('lives')
            if not lives:
                break
            for live in lives:
                live_id = live.get('live_id')
                url = 'https://www.mirrativ.com/live/%s' % live_id
                entries.append(self.url_result(url, 'Mirrativ', live_id, live.get('title')))
            page = api_response.get('next_page')

        return self.playlist_result(entries, user_id, uploader, description)

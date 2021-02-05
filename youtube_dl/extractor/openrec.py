# coding: utf-8
from __future__ import unicode_literals, with_statement

from .common import InfoExtractor
from ..utils import unified_strdate


class OpenRecBaseIE(InfoExtractor):
    pass


class OpenRecIE(OpenRecBaseIE):
    IE_NAME = 'openrec'
    _VALID_URL = r'https?://(?:www\.)?openrec\.tv/live/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.openrec.tv/live/2p8v31qe4zy',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://www.openrec.tv/live/%s' % video_id, video_id)

        window_stores = self._parse_json(
            self._search_regex(r'(?m)window\.stores\s*=\s*(\{.+?\});$', webpage, 'window.stores'), video_id)
        movie_store = window_stores['moviePageStore']['movieStore']

        title = movie_store['title']
        description = movie_store['introduction']
        thumbnail = movie_store['thumbnailUrl']
        uploader = movie_store['channel']['name']
        uploader_id = movie_store['channel']['id']
        upload_date = unified_strdate(movie_store['createdAt'])

        m3u8_playlists = movie_store['media']
        formats = []
        for (name, m3u8_url) in m3u8_playlists.items():
            if not m3u8_url:
                continue
            fmt_list = self._extract_m3u8_formats(
                m3u8_url, video_id, ext='mp4', entry_protocol='m3u8',
                m3u8_id='hls-%s' % name, live=True)
            formats.extend(fmt_list)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'upload_date': upload_date,
            'is_live': True,
        }


class OpenRecCaptureIE(OpenRecBaseIE):
    IE_NAME = 'openrec:capture'
    _VALID_URL = r'https?://(?:www\.)?openrec\.tv/capture/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.openrec.tv/capture/l9nk2x4gn14',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://www.openrec.tv/capture/%s' % video_id, video_id)

        window_stores = self._parse_json(
            self._search_regex(r'(?m)window\.stores\s*=\s*(\{.+?\});$', webpage, 'window.stores'), video_id)
        movie_store = window_stores['moviePageStore']['movieStore']
        capture_data = window_stores['capturePlayPageStore']['capture']
        channel_info = window_stores['capturePlayPageStore']['movie']['channel']

        title = capture_data['title']
        thumbnail = movie_store['thumbnailUrl']
        uploader = channel_info['name']
        uploader_id = channel_info['id']
        upload_date = unified_strdate(capture_data['createdAt'])

        m3u8_url = capture_data['source']
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, ext='mp4', entry_protocol='m3u8',
            m3u8_id='hls')

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'upload_date': upload_date,
        }

# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    urlencode_postdata,
    random_user_agent,
    ExtractorError,
)

import re


class TwitCastingIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?twitcasting\.tv/(?P<uploader_id>[^/]+)/(?:movie|twplayer)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://twitcasting.tv/ivetesangalo/movie/2357609',
        'md5': '745243cad58c4681dc752490f7540d7f',
        'info_dict': {
            'id': '2357609',
            'ext': 'mp4',
            'title': 'Live #2357609',
            'uploader_id': 'ivetesangalo',
            'description': "Moi! I'm live on TwitCasting from my iPhone.",
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://twitcasting.tv/mttbernardini/movie/3689740',
        'info_dict': {
            'id': '3689740',
            'ext': 'mp4',
            'title': 'Live playing something #3689740',
            'uploader_id': 'mttbernardini',
            'description': "I'm live on TwitCasting from my iPad. password: abc (Santa Marinella/Lazio, Italia)",
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {
            'skip_download': True,
            'videopassword': 'abc',
        },
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        uploader_id = mobj.group('uploader_id')

        video_password = self._downloader.params.get('videopassword')
        request_data = None
        if video_password:
            request_data = urlencode_postdata({
                'password': video_password,
            })

        def download_pages():
            actual_url = 'https://twitcasting.tv/%s/movie/%s' % (uploader_id, video_id)
            for lang in (
                    ('JPN1', 'ja-JP,ja;q=0.8,en-US;q=0.5,en;q=0.3'),
                    ('JPN2', 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7'),
                    ('ENG1', 'en-US,en;q=0.5'),):
                for ua in (
                        ('default', random_user_agent()),
                        ('mobile chrome', 'Mozilla/5.0 (Linux; Android 5.1; N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.136 Mobile Safari/537.36'),
                        ('mobile firefox', 'Mozilla/5.0 (Android 5.1; Mobile; rv:68.0) Gecko/68.0 Firefox/68.0'),):
                    headers = {
                        'Accept-Language': lang[1],
                        'User-Agent': ua[1]
                    }
                    yield self._download_webpage(
                        actual_url, video_id, data=request_data, headers=headers,
                        note='Downloading page: %s %s' % (lang[0], ua[0]))

        title, m3u8_url, thumbnail, description = [None] * 4

        for webpage in download_pages():
            title = title or self._html_search_regex(
                (r'(?s)<[^>]+id=["\']movietitle[^>]+>(.+?)</',
                 r'(?sm)<[^>]+id=["\']movietitle[^>]+>.*<a[^>]+>(.+?)</'),
                webpage, 'title', default=None) or self._html_search_meta(
                'twitter:title', webpage)

            m3u8_url = m3u8_url or self._search_regex(
                (r'data-movie-url=(["\'])(?P<url>(?:(?!\1).)+)\1',
                 r'(["\'])(?P<url>http.+?\.m3u8.*?)\1',
                 r'(["\'])(?P<url>/.+?\.m3u8.*?)\1'),
                webpage, 'm3u8 url', group='url', fatal=False)

            if m3u8_url and m3u8_url[0] == '/':
                m3u8_url = 'https://twitcasting.tv%s' % m3u8_url

            thumbnail = thumbnail or self._og_search_thumbnail(webpage)
            description = description or self._og_search_description(
                webpage, default=None) or self._html_search_meta(
                'twitter:description', webpage)

            if title and m3u8_url and thumbnail and description:
                break

        if not title:
            raise ExtractorError('Failed to extract title', expected=False)
        if not m3u8_url:
            raise ExtractorError('Failed to extract m3u8 url', expected=False)

        m3u8_url = m3u8_url.replace(r'\/', '/')
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, ext='mp4', entry_protocol='m3u8_native',
            m3u8_id='hls')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader_id': uploader_id,
            'formats': formats,
            'is_live': True,
        }

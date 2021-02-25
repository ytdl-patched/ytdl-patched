# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    sanitized_Request,
    ExtractorError,
)
from ..compat import (
    compat_str,
)

try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote


class TokyoMotionBaseIE(InfoExtractor):

    def _download_page(self, url, video_id, note=None):
        # This fails
        # return self._download_webpage(url, video_id)
        # Use ones in generic extractor
        request = sanitized_Request(url)
        request.add_header('Accept-Encoding', '*')
        full_response = self._request_webpage(request, video_id, note=note)
        return self._webpage_read_content(full_response, url, video_id)

    @staticmethod
    def _int_id(url):
        if '_VALID_URL_RE' not in TokyoMotionIE.__dict__:
            TokyoMotionIE._VALID_URL_RE = re.compile(TokyoMotionIE._VALID_URL)
        m = TokyoMotionIE._VALID_URL_RE.match(url)
        return int(compat_str(m.group('id')))

    @staticmethod
    def _extract_video_urls(variant, webpage):
        return ('https://www.%smotion.net%s' % (variant, quote(frg.group()))
                for frg in re.finditer(r'/video/(?P<id>\d+)/[^#?&"\']+', webpage))

    def _do_paging(self, variant, user_id):
        index = 1
        all_matches = []
        while True:
            newurl = self.USER_VIDEOS_FULL_URL % (variant, user_id, index)
            webpage = self._download_page(newurl, user_id, note='Downloading page %d' % index)
            all_matches.extend(self._extract_video_urls(variant, webpage))
            index = index + 1
            if ('videos?page=%d"' % index) not in webpage and ('&page=%d"' % index) not in webpage:
                break
        return (self.url_result(url) for url in sorted(set(all_matches), key=self._int_id))


class TokyoMotionPlaylistBaseIE(TokyoMotionBaseIE):

    def _real_extract(self, url):
        user_id = self._match_id(url)
        variant = self._VALID_URL_RE.match(url).group('variant')
        matches = self._do_paging(variant, user_id)
        return self.playlist_result(matches, user_id, self.TITLE % user_id)


class TokyoMotionIE(TokyoMotionBaseIE):
    IE_NAME = 'tokyomotion'
    _VALID_URL = r'(?P<url>https?://(?:www\.)?(?P<variant>tokyo|osaka)motion\.net/video/(?P<id>\d+)/.+)'
    _TEST = {
        'url': 'https://www.tokyomotion.net/video/915034/%E9%80%86%E3%81%95',
        'info_dict': {
            'id': '915034',
            'ext': 'mp4',
            'title': '逆さ',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = self._VALID_URL_RE.match(url).group('url')
        variant = self._VALID_URL_RE.match(url).group('variant')
        webpage = self._download_page(url, video_id)

        title = self._og_search_title(webpage, default=None)

        entries = self._parse_html5_media_entries(url, webpage, video_id, m3u8_id='hls')
        if not entries:
            raise ExtractorError('Private video', expected=True)
        entry = entries[0]

        for fmt in entry['formats']:
            fmt['external_downloader'] = 'ffmpeg'

        self._sort_formats(entry['formats'])
        entry.update({
            'id': video_id,
            'title': title,
            'age_limit': 18,
            'series': 'TokyoMotion' if variant == 'tokyo' else 'OsakaMotion',
        })
        return entry


class TokyoMotionCorruptedUrlIE(TokyoMotionBaseIE):
    IE_NAME = 'tokyomotion:corrupted'
    _VALID_URL = r'https?://(?:www\.)?(?:tokyo|osaka)motion\.net/video/(?P<id>\d+)/?$'
    IE_DESC = False

    def _real_extract(self, url):
        self.to_screen('Given URL looks corrupted, trying to repair')
        without_hash = url.split('#')[0]
        repaired = without_hash + 'a' if without_hash.endswith('/') else '/a'
        return self.url_result(repaired)


class TokyoMotionUserIE(TokyoMotionPlaylistBaseIE):
    IE_NAME = 'tokyomotion:user'
    _VALID_URL = r'https?://(?:www\.)?(?P<variant>tokyo|osaka)motion\.net/user/(?P<id>[^/]+)(?:/videos)?'
    _TEST = {}
    USER_VIDEOS_FULL_URL = 'https://www.%smotion.net/user/%s/videos?page=%d'
    TITLE = 'Uploads from %s'


class TokyoMotionUserFavsIE(TokyoMotionPlaylistBaseIE):
    IE_NAME = 'tokyomotion:user:favs'
    _VALID_URL = r'https?://(?:www\.)?(?P<variant>tokyo|osaka)motion\.net/user/(?P<id>[^/]+)/favorite/videos'
    _TEST = {}
    USER_VIDEOS_FULL_URL = 'https://www.%smotion.net/user/%s/favorite/videos?page=%d'
    TITLE = 'Favorites from %s'


class TokyoMotionSearchesIE(TokyoMotionPlaylistBaseIE):
    IE_NAME = 'tokyomotion:searches'
    _VALID_URL = r'https?://(?:www\.)?(?P<variant>tokyo|osaka)motion\.net/search\?search_query=(?P<id>[^/&]+)(?:&search_type=videos)?(?:&page=\d+)?'
    _TEST = {}
    USER_VIDEOS_FULL_URL = 'https://www.%smotion.net/search?search_query=%s&search_type=videos&page=%d'
    TITLE = 'Search results for %s'


class TokyoMotionScannerIE(TokyoMotionBaseIE):
    IE_DESC = False  # Do not list
    IE_NAME = 'tokyomotion:scanner'
    _VALID_URL = r'tmscan:https?://(?:www\.)?(?P<variant>tokyo|osaka)motion\.net/(?P<id>.*)'
    _TEST = {}

    def _real_extract(self, url):
        user_id = self._match_id(url) or ''
        variant = self._VALID_URL_RE.match(url).group('variant')
        webpage = self._download_page(url[7:], user_id)
        matches = self._extract_video_urls(variant, webpage)
        playlist = (self.url_result(url) for url in sorted(set(matches), key=self._int_id))
        return self.playlist_result(playlist, user_id, 'Scanned results for %s' % url)

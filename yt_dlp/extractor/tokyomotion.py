# coding: utf-8
from __future__ import unicode_literals

import re
import itertools

from .common import InfoExtractor
from ..utils import (
    sanitized_Request,
    ExtractorError,
    try_get,
)
from ..compat import (
    compat_str,
    compat_urllib_parse_quote,
)


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
        m = TokyoMotionIE._match_valid_url(url)
        assert m
        return int(compat_str(m.group('id')))

    @staticmethod
    def _extract_video_urls(variant, webpage):
        return ('https://www.%smotion.net%s' % (variant, compat_urllib_parse_quote(frg.group()))
                for frg in re.finditer(r'/video/(?P<id>\d+)/[^#?&"\']+', webpage))

    def _do_paging(self, variant, user_id):
        for index in itertools.count(1):
            newurl = self.USER_VIDEOS_FULL_URL % (variant, user_id, index)
            webpage = self._download_page(newurl, user_id, note='Downloading page %d' % index)
            for url in self._extract_video_urls(variant, webpage):
                yield self.url_result(url)
            if ('videos?page=%d"' % (index + 1)) not in webpage and ('&page=%d"' % (index + 1)) not in webpage:
                break


class TokyoMotionPlaylistBaseIE(TokyoMotionBaseIE):
    def _real_extract(self, url):
        variant, user_id = self._match_valid_url(url).group('variant', 'id')
        matches = self._do_paging(variant, user_id)
        return self.playlist_result(matches, user_id, self.TITLE % user_id)


class TokyoMotionIE(TokyoMotionBaseIE):
    IE_NAME = 'tokyomotion'
    _VALID_URL = r'https?://(?:www\.)?(?P<variant>tokyo|osaka)motion\.net/video/(?P<id>\d+)(?P<excess>/[^#\?]+)?'
    _TESTS = [{
        'url': 'https://www.tokyomotion.net/video/915034/%E9%80%86%E3%81%95',
        'info_dict': {
            'id': '915034',
            'ext': 'mp4',
            'title': '逆さ',
        }
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        url, variant, video_id, excess = mobj.group(0, 'variant', 'id', 'excess')
        if not excess:
            # fix URL silently
            url = url.split('#')[0]
            if not url.endswith('/'):
                url += '/'
            url += 'a'

        webpage = self._download_page(url, video_id)

        title = self._og_search_title(webpage, default=None)

        entry = try_get(
            webpage,
            lambda x: self._parse_html5_media_entries(url, x, video_id, m3u8_id='hls')[0],
            dict)
        if not entry:
            raise ExtractorError('Private video', expected=True)

        for fmt in entry['formats']:
            fmt['external_downloader'] = 'ffmpeg'
            if fmt['format_id'] == 'HD':
                fmt['preference'] = fmt['quality'] = 1
            else:
                fmt['preference'] = fmt['quality'] = -1

        self._sort_formats(entry['formats'])
        entry.update({
            'id': video_id,
            'title': title,
            'age_limit': 18,
            'series': 'TokyoMotion' if variant == 'tokyo' else 'OsakaMotion',
        })
        return entry


class TokyoMotionUserIE(TokyoMotionPlaylistBaseIE):
    IE_NAME = 'tokyomotion:user'
    _VALID_URL = r'https?://(?:www\.)?(?P<variant>tokyo|osaka)motion\.net/user/(?P<id>[^/]+)(?:/videos)?'
    _TESTS = []
    USER_VIDEOS_FULL_URL = 'https://www.%smotion.net/user/%s/videos?page=%d'
    TITLE = 'Uploads from %s'


class TokyoMotionUserFavsIE(TokyoMotionPlaylistBaseIE):
    IE_NAME = 'tokyomotion:user:favs'
    _VALID_URL = r'https?://(?:www\.)?(?P<variant>tokyo|osaka)motion\.net/user/(?P<id>[^/]+)/favorite/videos'
    _TESTS = []
    USER_VIDEOS_FULL_URL = 'https://www.%smotion.net/user/%s/favorite/videos?page=%d'
    TITLE = 'Favorites from %s'


class TokyoMotionSearchesIE(TokyoMotionPlaylistBaseIE):
    IE_NAME = 'tokyomotion:searches'
    _VALID_URL = r'https?://(?:www\.)?(?P<variant>tokyo|osaka)motion\.net/search\?search_query=(?P<id>[^/&]+)(?:&search_type=videos)?(?:&page=\d+)?'
    _TESTS = []
    USER_VIDEOS_FULL_URL = 'https://www.%smotion.net/search?search_query=%s&search_type=videos&page=%d'
    TITLE = 'Search results for %s'


class TokyoMotionScannerIE(TokyoMotionBaseIE):
    IE_DESC = False  # Do not list
    IE_NAME = 'tokyomotion:scanner'
    _VALID_URL = r'tmscan:https?://(?:www\.)?(?P<variant>tokyo|osaka)motion\.net/(?P<id>.*)'
    _TESTS = []

    def _real_extract(self, url):
        variant, user_id = self._match_valid_url(url).groups()
        webpage = self._download_page(url[7:], user_id)
        matches = self._extract_video_urls(variant, webpage)
        return self.playlist_result(
            (self.url_result(url) for url in matches),
            user_id, 'Scanned results for %s' % url)

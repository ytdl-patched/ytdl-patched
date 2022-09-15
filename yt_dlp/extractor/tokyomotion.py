# coding: utf-8
from __future__ import unicode_literals

import re
import functools
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    try_get,
)


class TokyoMotionBaseIE(InfoExtractor):
    _COMMON_HEADERS = {
        'Accept-Encoding': '*',
    }

    @staticmethod
    def _extract_video_urls(variant, webpage):
        return ('https://www.%smotion.net%s' % (variant, urllib.parse.quote(frg.group()))
                for frg in re.finditer(r'/video/(?P<id>\d+)/[^#?&"\']+', webpage))

    def _do_paging(self, variant, user_id, index):
        index += 1
        newurl = self._PAGING_BASE_TEMPLATE % (variant, user_id, index)
        webpage = self._download_webpage(newurl, user_id, headers=self._COMMON_HEADERS, note='Downloading page %d' % index)

        yield from [self.url_result(url) for url in self._extract_video_urls(variant, webpage)][::2]


class TokyoMotionPlaylistBaseIE(TokyoMotionBaseIE):
    def _real_extract(self, url):
        user_id = self._match_id(url)
        matches = OnDemandPagedList(functools.partial(self._do_paging, self._VARIANT, user_id), 18)
        return self.playlist_result(matches, user_id, self._TITLE_TEMPLATE % user_id)


class UnvariantedMotionIE(TokyoMotionBaseIE):
    IE_NAME = '%smotion'
    _VALID_URL = r'https?://(?:www\.)?%smotion\.net/video/(?P<id>\d+)(?P<excess>/[^#\?]+)?'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        url, video_id, excess = mobj.group(0, 'id', 'excess')
        if not excess:
            # fix URL silently
            url = url.split('#')[0]
            if not url.endswith('/'):
                url += '/'
            url += 'a'

        webpage = self._download_webpage(url, video_id, headers=self._COMMON_HEADERS)
        title = self._og_search_title(webpage, default=None)

        entry = try_get(
            webpage,
            lambda x: self._parse_html5_media_entries(url, x, video_id, m3u8_id='hls')[0],
            dict)
        if not entry:
            raise ExtractorError('This is a private video.', expected=True)

        for fmt in entry['formats']:
            # TODO: maybe Range can be used again
            fmt['external_downloader'] = 'ffmpeg'
            fmt['preference'] = 1 if fmt['format_id'] == 'HD' else -1

        self._sort_formats(entry['formats'], ('preference', ))
        entry.update({
            'id': video_id,
            'title': title,
            'age_limit': 18,
        })
        return entry


class UnvariantedMotionUserIE(TokyoMotionPlaylistBaseIE):
    IE_NAME = '%smotion:user'
    _VALID_URL = r'https?://(?:www\.)?%smotion\.net/user/(?P<id>[^/]+)(?:/videos)?'
    _PAGING_BASE_TEMPLATE = 'https://www.%smotion.net/user/%s/videos?page=%d'
    _TITLE_TEMPLATE = 'Uploads from %s'


class UnvariantedMotionUserFavsIE(TokyoMotionPlaylistBaseIE):
    IE_NAME = '%smotion:user:favs'
    _VALID_URL = r'https?://(?:www\.)?%smotion\.net/user/(?P<id>[^/]+)/favorite/videos'
    _PAGING_BASE_TEMPLATE = 'https://www.%smotion.net/user/%s/favorite/videos?page=%d'
    _TITLE_TEMPLATE = 'Favorites from %s'


class UnvariantedMotionSearchesIE(TokyoMotionPlaylistBaseIE):
    IE_NAME = '%smotion:searches'
    _VALID_URL = r'https?://(?:www\.)?%smotion\.net/search\?search_query=(?P<id>[^/&]+)(?:&search_type=videos)?(?:&page=\d+)?'
    _PAGING_BASE_TEMPLATE = 'https://www.%smotion.net/search?search_query=%s&search_type=videos&page=%d'
    _TITLE_TEMPLATE = 'Search results for %s'


class TokyoMotionIE(UnvariantedMotionIE):
    _VARIANT = 'tokyo'


class TokyoMotionUserIE(UnvariantedMotionUserIE):
    _VARIANT = 'tokyo'


class TokyoMotionUserFavsIE(UnvariantedMotionUserFavsIE):
    _VARIANT = 'tokyo'


class TokyoMotionSearchesIE(UnvariantedMotionSearchesIE):
    _VARIANT = 'tokyo'


class OsakaMotionIE(UnvariantedMotionIE):
    _VARIANT = 'osaka'


class OsakaMotionUserIE(UnvariantedMotionUserIE):
    _VARIANT = 'osaka'


class OsakaMotionUserFavsIE(UnvariantedMotionUserFavsIE):
    _VARIANT = 'osaka'


class OsakaMotionSearchesIE(UnvariantedMotionSearchesIE):
    _VARIANT = 'osaka'


class TokyoMotionScannerIE(TokyoMotionBaseIE):
    IE_DESC = False  # Do not list
    IE_NAME = '%smotion:scanner'
    _VARIANT = 'tokyo'
    _VALID_URL = r'tmscan:https?://(?:www\.)?%smotion\.net/(?P<id>.*)'
    _TESTS = []

    def _real_extract(self, url):
        user_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url[7:], user_id, headers=self._COMMON_HEADERS)
        matches = self._extract_video_urls(self._VARIANT, webpage)
        return self.playlist_result(
            (self.url_result(url) for url in matches),
            user_id, 'Scanned results for %s' % url)


for k, v in list(locals().items()):
    if not isinstance(v, type):
        continue
    if not getattr(v, '_VARIANT', None):
        continue
    v.IE_NAME = v.IE_NAME % v._VARIANT
    v._VALID_URL = v._VALID_URL % v._VARIANT

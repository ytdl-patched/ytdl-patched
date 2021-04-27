# coding: utf-8
from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    float_or_none,
    get_element_by_class,
    get_element_by_id,
    parse_duration,
    str_to_int,
    unified_timestamp,
    urlencode_postdata,
    try_get,
    urljoin,
)
from ..compat import compat_str


class TwitCastingBaseIE(InfoExtractor):
    pass


class TwitCastingIE(TwitCastingBaseIE):
    _VALID_URL = r'https?://(?:[^/]+\.)?twitcasting\.tv/(?P<uploader_id>[^/]+)/(?:movie|twplayer)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://twitcasting.tv/ivetesangalo/movie/2357609',
        'md5': '745243cad58c4681dc752490f7540d7f',
        'info_dict': {
            'id': '2357609',
            'ext': 'mp4',
            'title': 'Live #2357609',
            'uploader_id': 'ivetesangalo',
            'description': 'Twitter Oficial da cantora brasileira Ivete Sangalo.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20110822',
            'timestamp': 1314010824,
            'duration': 32,
            'view_count': int,
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
            'description': 'Salve, io sono Matto (ma con la e). Questa è la mia presentazione, in quanto sono letteralmente matto (nel senso di strano), con qualcosa in più.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20120212',
            'timestamp': 1329028024,
            'duration': 681,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
            'videopassword': 'abc',
        },
    }]

    def _real_extract(self, url):
        uploader_id, video_id = re.match(self._VALID_URL, url).groups()

        video_password = self._downloader.params.get('videopassword')
        request_data = None
        if video_password:
            request_data = urlencode_postdata({
                'password': video_password,
            })
        webpage = self._download_webpage(
            url, video_id, data=request_data,
            headers={'Origin': 'https://twitcasting.tv'})

        title = try_get(
            webpage,
            (lambda x: clean_html(get_element_by_id('movietitle', x)),
             lambda x: self._html_search_meta(['og:title', 'twitter:title'], x, fatal=False)),
            compat_str)
        if not title:
            raise ExtractorError('Failed to extract title')

        video_js_data = try_get(
            webpage,
            lambda x: self._parse_json(self._search_regex(
                r"data-movie-playlist='([^']+?)'",
                x, 'movie playlist', default=None), video_id)["2"][0], dict) or {}
        m3u8_url = try_get(
            webpage,
            (lambda x: self._search_regex(
                r'data-movie-url=(["\'])(?P<url>(?:(?!\1).)+)\1',
                x, 'm3u8 url', group='url', default=None),
             lambda x: video_js_data['source']['url'],
             lambda x: 'https://twitcasting.tv/%s/metastream.m3u8' % uploader_id
                if 'data-status="online"' in x else None),
            compat_str)

        # use `m3u8` entry_protocol until EXT-X-MAP is properly supported by `m3u8_native` entry_protocol
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, 'mp4', m3u8_id='hls')
        self._sort_formats(formats)

        thumbnail = video_js_data.get('thumbnailUrl') or self._og_search_thumbnail(webpage)
        description = clean_html(get_element_by_id(
            'authorcomment', webpage)) or self._html_search_meta(
            ['description', 'og:description', 'twitter:description'], webpage)
        duration = float_or_none(video_js_data.get(
            'duration'), 1000) or parse_duration(clean_html(
                get_element_by_class('tw-player-duration-time', webpage)))
        view_count = str_to_int(self._search_regex(
            r'Total\s*:\s*([\d,]+)\s*Views', webpage, 'views', None))
        timestamp = unified_timestamp(self._search_regex(
            r'data-toggle="true"[^>]+datetime="([^"]+)"',
            webpage, 'datetime', None))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'uploader_id': uploader_id,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
            'is_live': True,
        }


class TwitCastingUserIE(TwitCastingBaseIE):
    _VALID_URL = r'https?://(?:[^/]+\.)?twitcasting\.tv/(?P<id>[^/]+)(?:/([a-zA-Z-_][^/]*)?)*$'
    _TESTS = [{
        'url': 'https://twitcasting.tv/ivetesangalo',
        'only_matching': True,
    }, {
        'url': 'https://twitcasting.tv/mttbernardini/',
        'only_matching': True,
    }, {
        'url': 'https://twitcasting.tv/noriyukicas',
        'only_matching': True,
    }, {
        'url': 'https://twitcasting.tv/lockedlesmi/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        uploader_id = self._match_id(url)
        webpage = self._download_webpage(url, uploader_id, note='Looking for current live')

        current_live = self._search_regex(
            (r'data-type="movie" data-id="(\d+)">',
             r'tw-sound-flag-open-link" data-id="(\d+)" style=',),
            webpage, 'current live ID', default=None)
        if current_live:
            self._downloader.report_warning('Redirecting to current live on user %s' % uploader_id)
            return self.url_result('https://twitcasting.tv/%s/movie/%s' % (uploader_id, current_live))

        next_url = 'https://twitcasting.tv/%s/show/' % uploader_id
        urls = []
        for index in itertools.count(1):
            webpage = self._download_webpage(next_url, uploader_id, note='Downloading page %d' % index)
            for match in re.finditer(r'''(?isx)
                <a\s+class="tw-movie-thumbnail"\s*href="(?P<url>/[^/]+/movie/\d+)"\s*>
                .+?</a>
            ''', webpage):
                if not re.search(r'<span\s+class="tw-movie-thumbnail-badge"\s*data-status="recorded">', match.group(0)):
                    continue
                video_full_url = urljoin(url, match.group('url'))
                urls.append(self.url_result(video_full_url))

            next_url = self._search_regex(
                r'<a href="(/%s/show/%d-\d+)">%d</a>' % (re.escape(uploader_id), index, index + 1),
                webpage, 'next url', default=None)
            if next_url:
                next_url = urljoin(url, next_url)
            else:
                break

        return self.playlist_result(urls, uploader_id, 'Live archive from %s' % uploader_id)

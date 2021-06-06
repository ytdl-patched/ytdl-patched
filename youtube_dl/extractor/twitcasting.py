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
    qualities,
)
from ..compat import compat_str
from ..websocket import HAVE_WEBSOCKET  # WebSocket itself is optional


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
    }, {
        'note': 'archive is split in 2 parts',
        'url': 'https://twitcasting.tv/loft_heaven/movie/685979292',
        'info_dict': {
            'id': '685979292',
            'ext': 'mp4',
            'title': '南波一海のhear_here “ナタリー望月哲さんに聞く編集と「渋谷系狂騒曲」”',
            'duration': 6964.599334,
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
            (lambda x: self._html_search_meta(['og:title', 'twitter:title'], x, fatal=False)),
            compat_str)
        if not title:
            raise ExtractorError('Failed to extract title')

        video_js_data = try_get(
            webpage,
            lambda x: self._parse_json(self._search_regex(
                r"data-movie-playlist='([^']+?)'",
                x, 'movie playlist', default=None), video_id)["2"], list)

        stream_server_data = self._download_json(
            'https://twitcasting.tv/streamserver.php?target=%s&mode=client' % uploader_id, video_id,
            'Downloading live info', fatal=False)

        is_live = 'data-status="online"' in webpage

        def find_dmu(x):
            data_movie_url = self._search_regex(
                r'data-movie-url=(["\'])(?P<url>(?:(?!\1).)+)\1',
                x, 'm3u8 url', group='url', default=None)
            if data_movie_url:
                return [data_movie_url]

        m3u8_urls = try_get(
            webpage,
            (find_dmu,
             lambda x: [y['source']['url'] for y in video_js_data]
                if video_js_data else None,
             lambda x: ['https://twitcasting.tv/%s/metastream.m3u8' % uploader_id]
                if is_live else None),
            list)

        if is_live:
            # use `m3u8` entry_protocol until EXT-X-MAP is properly supported by `m3u8_native` entry_protocol
            m3u8_url = m3u8_urls[0]
            formats = self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', m3u8_id='hls',
                headers={
                    'Accept': '*/*',
                    'Origin': 'https://twitcasting.tv',
                    'Referer': 'https://twitcasting.tv/',
                })

            if stream_server_data and HAVE_WEBSOCKET:
                qq = qualities(['base', 'mobilesource', 'main'])
                for mode, ws_url in stream_server_data['llfmp4']['streams'].items():
                    formats.append({
                        'url': ws_url,
                        'format_id': 'ws-%s' % mode,
                        'ext': 'mp4',
                        'preference': -100,
                        'quality': qq(mode),
                        'format_note': 'video timestamp have jitter',
                        # TwitCasting simply sends moof atom directly over WS
                        'protocol': 'frag_websocket',
                    })

            self._sort_formats(formats)
        else:
            # This reduces the download of m3u8 playlist (2 -> 1)
            formats = [{
                'url': m3u8_url,
                'format_id': 'hls-%d' % num,
                'ext': 'mp4',
                'protocol': 'm3u8',
                'http_headers': {
                    'Accept': '*/*',
                    'Origin': 'https://twitcasting.tv',
                    'Referer': 'https://twitcasting.tv/',
                },
                'input_params': ['-re'],
            } for (num, m3u8_url) in enumerate(m3u8_urls)]

            url_count = len(m3u8_urls)
            if url_count > 1:
                self.report_warning('This archive got split in %d parts; to download each split, please use "-f hls-0".."-f hls-%d" option.' % (url_count, url_count - 1))
                formats.append({
                    'format_id': 'all',
                    'url': 'serial:',
                    'protocol': 'serial',
                    'items': list(formats),
                    'ext': 'mp4',
                    'format_note': '使うのは自己責任で',
                })
                formats.reverse()

        thumbnail = try_get(
            video_js_data,
            (lambda x: x[0].get('thumbnailUrl'),
             lambda x: self._og_search_thumbnail(webpage)),
            compat_str)
        description = clean_html(get_element_by_id(
            'authorcomment', webpage)) or self._html_search_meta(
            ['description', 'og:description', 'twitter:description'], webpage)
        duration = try_get(
            video_js_data,
            (lambda x: sum(float_or_none(y.get('duration')) for y in x) / 1000,
             lambda x: parse_duration(clean_html(
                 get_element_by_class('tw-player-duration-time', webpage)))),
            float)
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
            'uploader': uploader_id,
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

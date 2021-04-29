# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import ExtractorError, clean_html, int_or_none, try_get
from ..compat import compat_etree_fromstring, compat_str


class DamtomoIE(InfoExtractor):
    IE_NAME = 'clubdam:damtomo'
    _VALID_URL = r'https?://(www\.)?clubdam\.com/app/damtomo/(?:SP/)?karaokeMovie/StreamingDkm\.do\?karaokeMovieId=(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.clubdam.com/app/damtomo/karaokeMovie/StreamingDkm.do?karaokeMovieId=2414316',
        'info_dict': {
            'id': '2414316',
            'uploader': 'Ｋドロン',
            'uploader_id': 'ODk5NTQwMzQ',
            'song_title': 'Get Wild',
            'song_artist': 'TM NETWORK(TMN)',
            'upload_date': '20201226',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage, handle = self._download_webpage_handle(
            'https://www.clubdam.com/app/damtomo/karaokeMovie/StreamingDkm.do?karaokeMovieId=%s' % video_id, video_id,
            encoding='sjis')

        if handle.url == 'https://www.clubdam.com/sorry/':
            raise ExtractorError('You are rate-limited. Try again later.', expected=True)
        if '<h2>予期せぬエラーが発生しました。</h2>' in webpage:
            raise ExtractorError('There is a error in server-side. Try again later.', expected=True)

        # NOTE: there is excessive amount of spaces and line breaks, so ignore spaces around these part
        description = self._search_regex(r'(?m)<div id="public_comment">\s*<p>\s*([^<]*?)\s*</p>', webpage, 'description', default=None)
        uploader_id = self._search_regex(r'<a href="https://www\.clubdam\.com/app/damtomo/member/info/Profile\.do\?damtomoId=([^"]+)"', webpage, 'uploader_id', default=None)

        # cleaner way to extract information in HTML
        # example content: https://gist.github.com/nao20010128nao/1d419cc9ca3177be134094addf28ab51
        data_dict = {g.group(2): clean_html(g.group(3), True) for g in re.finditer(r'(?s)<(p|div)\s+class="([^" ]+?)">(.+?)</\1>', webpage)}
        data_dict = {k: re.sub(r'\s+', ' ', v) for k, v in data_dict.items() if v}
        # print(json.dumps(data_dict))

        # since videos do not have title, name the video like '%(song_title)s-%(song_artist)s-%(uploader)s' for convenience
        data_dict['user_name'] = re.sub(r'\s*さん', '', data_dict['user_name'])
        title = '%(song_title)s-%(song_artist)s-%(user_name)s' % data_dict

        stream_xml = self._download_webpage(
            'https://www.clubdam.com/app/damtomo/karaokeMovie/GetStreamingDkmUrlXML.do?movieSelectFlg=2&karaokeMovieId=%s' % video_id, video_id,
            note='Requesting stream information', encoding='sjis')
        try:
            stream_tree = compat_etree_fromstring(stream_xml)
            m3u8_url = try_get(stream_tree, lambda x: x.find(
                './/d:streamingUrl',
                {'d': 'https://www.clubdam.com/app/damtomo/karaokeMovie/GetStreamingDkmUrlXML'}).text.strip(), compat_str)
            if not m3u8_url or not isinstance(m3u8_url, compat_str):
                raise ExtractorError('There is no streaming URL')
        except ValueError:  # Python <= 2, ValueError: multi-byte encodings are not supported
            m3u8_url = self._search_regex(r'<streamingUrl>\s*(.+?)\s*</streamingUrl>', stream_xml, 'm3u8 url')
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id,
            ext='mp4', entry_protocol='m3u8_native', m3u8_id='hls')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'uploader_id': uploader_id,
            'description': description,
            'formats': formats,
            'uploader': data_dict['user_name'],
            'upload_date': try_get(data_dict, lambda x: self._search_regex(r'(\d\d\d\d/\d\d/\d\d)', x['date'], 'upload_date', default=None).replace('/', ''), compat_str),
            'view_count': int_or_none(self._search_regex(r'(\d+)', data_dict['audience'], 'view_count', default=None)),
            'like_count': int_or_none(self._search_regex(r'(\d+)', data_dict['nice'], 'like_count', default=None)),
            'song_title': data_dict['song_title'],
            'song_artist': data_dict['song_artist'],
        }

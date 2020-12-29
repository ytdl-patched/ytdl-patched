# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import ExtractorError, clean_html, int_or_none
from ..compat import compat_etree_fromstring


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
        webpage = self._download_webpage(
            'https://www.clubdam.com/app/damtomo/karaokeMovie/StreamingDkm.do?karaokeMovieId=%s' % video_id, video_id,
            encoding='sjis')

        # NOTE: there is excessive amount of spaces and line breaks, so ignore spaces around these part
        description = self._search_regex(r'(?m)<div id="public_comment">\s*<p>\s*([^<]*?)\s*</p>', webpage, video_id)

        uploaders = re.search(r'<a href="https://www\.clubdam\.com/app/damtomo/member/info/Profile\.do\?damtomoId=([^"]+)">\s*([^<]+?)\s*</a>さん', webpage)
        if uploaders:
            uploader_id, uploader = uploaders.groups()
        else:
            self.report_warning('Unable to extract uploader')
            uploader_id, uploader = None, None

        # cleaner way to extract information in HTML
        # example content: https://gist.github.com/nao20010128nao/1d419cc9ca3177be134094addf28ab51
        data_dict = {g.group(2): clean_html(g.group(3), True) for g in re.finditer(r'(?s)<(p|div)\s+class="([^" ]+?)">(.+?)</\1>', webpage)}
        data_dict = {k: re.sub(r'\s+', ' ', v) for k, v in data_dict.items() if v}
        # print(json.dumps(data_dict))

        # since videos do not have title, name the video like '%(song_title)s-%(song_artist)s-%(uploader)s' for convenience
        if data_dict:
            extra_data = {}
            extra_data['uploader'] = uploader
            extra_data['upload_date'] = re.sub(r'^.+?(\d\d\d\d)/(\d\d)/(\d\d)', r'\g<1>\g<2>\g<3>', data_dict['date'])
            extra_data['view_count'] = int_or_none(re.sub(r'^.+?(\d+)$', r'\g<1>', data_dict['audience']))
            extra_data['like_count'] = int_or_none(re.sub(r'^.+?(\d+)$', r'\g<1>', data_dict['nice']))
            extra_data['song_title'] = data_dict['song_title']
            extra_data['song_artist'] = data_dict['song_artist']
            title = '%(song_title)s-%(song_artist)s-%(uploader)s' % extra_data
        else:
            extra_data = {}
            title = uploader or ''

        stream_xml = self._download_webpage(
            'https://www.clubdam.com/app/damtomo/karaokeMovie/GetStreamingDkmUrlXML.do?movieSelectFlg=2&karaokeMovieId=%s' % video_id, video_id,
            note='Requesting stream information', encoding='sjis')
        stream_tree = compat_etree_fromstring(stream_xml)
        m3u8_url = stream_tree.find(
            './/d:streamingUrl',
            {'d': 'https://www.clubdam.com/app/damtomo/karaokeMovie/GetStreamingDkmUrlXML'}).text
        if not m3u8_url:
            raise ExtractorError('There is no streaming URL')
        m3u8_url = m3u8_url.strip()
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id,
            ext='mp4', entry_protocol='m3u8_native', m3u8_id='hls')
        self._sort_formats(formats)

        result = {
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'description': description,
            'formats': formats,
        }
        result.update(extra_data)
        return result

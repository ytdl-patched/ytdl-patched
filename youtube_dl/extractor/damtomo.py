# coding: utf-8
from __future__ import unicode_literals
import re

from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none
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

        song_info = re.search(r'''(?isx)
        <div\s+id="info">\s*
            <p\s+class="song_title">\s*
                <a\s+href="https://www\.clubdam\.com/app/damtomo/leaf/SongLeaf\.do\?contentsId=\d+">\s*
                    (?P<song_title>[^<]+?)\s*
                </a>\s*
            </p>\s*
            <p\s+class="song_artist">\s*
                <a\s+href="https://www\.clubdam\.com/app/damtomo/leaf/ArtistLeaf\.do\?artistCode=\d+&exclude=\d+">\s*
                    (?P<song_artist>[^<]+?)\s*
                </a>\s*
            </p>\s*

            <div\s+class="etc\s+clearfix">\s*
                <p\s+class="date">\s*
                    撮影日：(?P<upload_date>\d{4}/\d\d/\d\d)\s*
                </p>\s*
                <p\s+class="audience">\s*
                    再生回数：(?P<view_count>\d+)\s*
                </p>\s*
                <p\s+class="nice">\s*
                    ナイス数：(?P<like_count>\d+)\s*
                </p>\s*
            </div>
        ''', webpage)

        # since videos do not have title, name the video like '%(song_title)s-%(song_artist)s-%(uploader)s' for convenience
        if song_info:
            extra_data = song_info.groupdict()
            extra_data['uploader'] = uploader
            extra_data['upload_date'] = re.sub(r'/', '', extra_data['upload_date'])
            extra_data['view_count'] = int_or_none(extra_data['view_count']) or extra_data['view_count']
            extra_data['like_count'] = int_or_none(extra_data['like_count']) or extra_data['like_count']
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

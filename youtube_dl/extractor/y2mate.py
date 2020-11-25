# coding: utf-8
from __future__ import unicode_literals

import re

from ..compat import compat_urllib_parse_urlencode
from ..utils import ExtractorError
from .common import InfoExtractor
from .youtube import YoutubeIE


class Y2mateIE(InfoExtractor):
    _VALID_URL = r'(?x)^(?:y2(?:mate)?:|https?:\/\/(?:www\.)y2mate\.com\/youtube\/)%s' % re.sub(r'^\(\?x\)\^', '', YoutubeIE._VALID_URL)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._download_webpage('https://www.y2mate.com/youtube/%s' % video_id, video_id)
        request_data = {
            'url': 'https://www.youtube.com/watch?v=%s' % video_id,
            'q_auto': '1',
            'ajax': '1'
        }
        size_specs = self._download_json('https://www.y2mate.com/mates/analyze/ajax', video_id,
                                         note='Fetching size specs', errnote='This video is unavailable', data=compat_urllib_parse_urlencode(request_data).encode('utf-8'),
                                         headers={'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
        if size_specs.get('status') != 'success':
            raise ExtractorError('Server responded with status %s' % size_specs.get('status'))
        size_specs = size_specs['result']
        title = self._search_regex(r'<b>(.+?)<\/b>', size_specs, 'video title', group=1)
        request_id = self._search_regex(r'var k__id\s*=\s*(["\'])(.+?)\1', size_specs, 'request ID', group=2)
        formats = []
        # video    , mp3, audio
        video_table, _, audio_table = re.findall(r'<table\s*.+?>(.+?)</table>', size_specs)

        for rows in re.finditer(r'''(?x)<tr>\s*
                    <td>.+?(\d+p).+?<\/td>\s* # resolution name
                    <td>(.*?\s*[kMG]?B)<\/td>\s* # estimate size
                    <td\s*.+?>.+?(?:data-ftype="(.+?)".+?)?(?:data-fquality="(.+?)".+?)?<\/td>\s* # download button
                <\/tr>''', video_table):
            format_name, estimate_size, format_ext, request_format = rows.groups()
            request_data = {
                'type': 'youtube',
                '_id': request_id,
                'v_id': video_id,
                'ajax': '1',
                'token': '',
                'ftype': format_ext,
                'fquality': request_format,
            }
            url_data = self._download_json('https://www.y2mate.com/mates/convert', video_id,
                                           note='Fetching infomation for %s' % format_name, data=compat_urllib_parse_urlencode(request_data).encode('utf-8'),
                                           headers={'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
            if url_data.get('status') != 'success':
                self.report_warning('Server responded with status %s' % url_data.get('status'))
            url = self._search_regex(r'<a\s+(?:[a-zA-Z-_]+=\".+?\"\s+)*href=\"(https?://.+?)\"(?:\s+[a-zA-Z-_]+=\".+?\")*', url_data['result'],
                                     video_id, 'Download url for %s' % format_name, group=1)
            formats.append({
                'format_id': '%s-%s' % (format_name, format_ext),
                'resolution': format_name,
                'size': estimate_size,
                'ext': format_ext,
                'url': url,
                'vcodec': 'unknown',
                'acodec': 'unknown',
            })

        for rows in re.finditer(r'''(?x)<tr>\s*
                    <td>.+?(\d+[kMG]?bps).+?<\/td>\s* # resolution name
                    <td>(.*?\s*[kMG]?B)<\/td>\s* # estimate size
                    <td\s*.+?>.+?(?:data-ftype="(.+?)".+?)?(?:data-fquality="(.+?)".+?)?<\/td>\s* # download button
                <\/tr>''', audio_table):
            format_name, estimate_size, format_ext, request_format = rows.groups()
            request_data = {
                'type': 'youtube',
                '_id': request_id,
                'v_id': video_id,
                'ajax': '1',
                'token': '',
                'ftype': format_ext,
                'fquality': request_format,
            }
            url_data = self._download_json('https://www.y2mate.com/mates/convert', video_id,
                                           note='Fetching infomation for %s' % format_name, data=compat_urllib_parse_urlencode(request_data).encode('utf-8'),
                                           headers={'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
            if url_data.get('status') != 'success':
                self.report_warning('Server responded with status %s' % url_data.get('status'))
            url = self._search_regex(r'<a\s+(?:[a-zA-Z-_]+=\".+?\"\s+)*href=\"(https?://.+?)\"(?:\s+[a-zA-Z-_]+=\".+?\")*', url_data['result'],
                                     video_id, 'Download url for %s' % format_name, group=1)
            formats.append({
                'format_id': '%s-%s' % (format_name, format_ext),
                'resolution': format_name,
                'size': estimate_size,
                'ext': format_ext,
                'url': url,
                'vcodec': 'none',
                'acodec': 'unknown',
            })

        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }

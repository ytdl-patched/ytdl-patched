# coding: utf-8
from __future__ import unicode_literals

import re
import time

from .common import InfoExtractor
from ..utils import determine_ext, int_or_none


class TktubeIE(InfoExtractor):
    IE_NAME = 'tktube'
    _VALID_URL = r'https?://(?:www\.)?tktube\.com/videos/(?P<id>\d+/[^/?#&]+)'
    _WORKING = False

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = 'https://www.tktube.com/videos/%s/' % video_id
        webpage = self._download_webpage(url, video_id)

        title = self._search_regex(
            (r'(?m)<div class="headline">\s*<h1>(.+?)</h1>\s*</div>',
             r'<title>(.+?)</title>',
             r'<meta property="og:title" content="(.+?)"',), webpage, 'title')
        description = self._og_search_description(webpage)

        mobj = re.search(r'<a href="https://www\.tktube\.com/members/(\d+)/">\s*(\S+?)\s*</a>', webpage)
        if mobj:
            uploader_id, uploader = mobj.groups()
        else:
            self.report_warning('Failed to extract uploader info')
            uploader_id, uploader = None, None

        # self._download_webpage('https://www.tktube.com/player/kt_player.js?v=5.2.0', video_id)
        # self._download_webpage('https://www.tktube.com/static/js/main.min.js?v=7.2', video_id)

        data_dict = {g.group(1): g.group(2) for g in re.finditer(r"(\S+?):\s*'(.+?)'", webpage)}
        formats = []
        for k, v in data_dict.items():
            if k.startswith('video_'):
                if '.mp4' not in v:
                    continue
                # remove first 'function/0/' and add some params
                video_url = '%s?rnd=%d' % (v[11:], int(time.time() * 1000))
                format_id = data_dict['%s_text' % k]
                width, height = None, int_or_none(format_id[:-1])
                if height:
                    width = height // 16 * 9
                formats.append({
                    'format_id': format_id,
                    'url': video_url,
                    'protocol': 'http',
                    'ext': determine_ext(video_url),
                    'width': width,
                    'height': height,
                    'http_headers': {
                        'Referer': url,
                        'Accept': '*/*',
                        'Accept-Encoding': 'identity;q=1, *;q=0',
                    },
                })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'description': description,
            'formats': formats,
        }

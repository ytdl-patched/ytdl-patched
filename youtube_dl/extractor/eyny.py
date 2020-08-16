# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)


class EynyBaseIE(InfoExtractor):
    IE_DESC = False  # Do not list


class EynyIE(EynyBaseIE):
    IE_NAME = 'eyny'
    _VALID_URL = r'https?:\/\/(?:www\.)?eyny\.com\/\d+\/watch\?v=(?P<id>[^#?&]+)(?:&[^&]+)*'
    _TEST = {}
    _TITLE_REGEX = re.compile(r'(?ms)<title>(.+) -  Free Videos \& Sex Movies - XXX Tube - EYNY<\/title>')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._TITLE_REGEX.search(webpage).group(1)

        entries = self._parse_html5_media_entries(url, webpage, video_id, m3u8_id='hls')
        if not entries:
            raise ExtractorError('Private video', expected=True)
        entry = entries[0]
        self._sort_formats(entry['formats'])
        entry.update({
            'id': video_id,
            'title': title,
            'age_limit': 18,
        })
        return entry

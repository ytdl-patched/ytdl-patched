# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    try_get,
    ExtractorError,
)


class EvoLoadBaseIE(InfoExtractor):
    IE_DESC = False  # Do not list


class EvoLoadIE(EvoLoadBaseIE):
    IE_NAME = 'evoload'
    # https://evoload.io/v/58AtgpYn5tAKEp
    _VALID_URL = r'https?://evoload\.io/[ev]/(?P<id>[a-zA-Z0-9]+)/?'
    _TEST = {}
    TITLE_RE = (
        r'<h3\s+class="kt-subheader__title">\s*(.+)\s*</h3>',
        r'<title>(?:Evoload|EvoLOAD.io) - Play\s(.+)\s*</title>'
    )
    VIDEO_URL = 'https://evoload.io/v/%s/'
    EMBED_URL = 'https://evoload.io/e/%s/'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage_video = self._download_webpage(self.VIDEO_URL % video_id, video_id, note='Downloading video page')
        webpage_embed = self._download_webpage(self.EMBED_URL % video_id, video_id, note='Downloading embed page')

        title = try_get(self.TITLE_RE, (
            lambda x: self._search_regex(x, webpage_video, 'video title'),
            lambda x: self._search_regex(x, webpage_embed, 'video title'),
        ), None)
        if not title:
            raise ExtractorError('Failed to extract video title')

        entry = self._parse_html5_media_entries(url, webpage_embed, video_id, m3u8_id='hls')[0]
        self._sort_formats(entry['formats'])
        entry.update({
            'id': video_id,
            'title': title,
            'age_limit': 18,
        })
        return entry

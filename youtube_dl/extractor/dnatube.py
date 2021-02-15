# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class DnaTubeBaseIE(InfoExtractor):
    pass


class DnaTubePlaylistBaseIE(DnaTubeBaseIE):
    pass


class DnaTubeIE(DnaTubeBaseIE):
    IE_NAME = 'dnatube'
    _VALID_URL = r'https?://(www\.)?dnatube\.com/video/(?P<id>\d+)/(?:[^/]+)/?'
    _TEST = {}

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._og_search_title(webpage, default=None)

        entries = self._parse_html5_media_entries(url, webpage, video_id, m3u8_id='hls')
        entry = entries[0]
        self._sort_formats(entry['formats'])
        entry.update({
            'id': video_id,
            'title': title,
        })
        return entry

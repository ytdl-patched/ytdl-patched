from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
)


class DisneyChrisIE(InfoExtractor):
    IE_NAME = 'disneychris'
    _VALID_URL = r'https?://(?:www\.)?disneychris\.com/(?P<id>a-day-at-disneyland|15-disneyland-soundtracks/.+?)\.html'

    def _real_extract(self, url):
        long_id = self._match_id(url)
        video_id = long_id.rsplit('/', 1)[-1]
        webpage = self._download_webpage(url, video_id)

        title = next(
            (x.group(2) for x in re.finditer(r'href="/(.+?)\.html">(.+?)</a>', webpage) if x.group(1) == long_id),
            None) or self._html_extract_title(webpage, 'playlist title', default=None)

        return self.playlist_result(self.extract_article_sections(webpage, video_id), video_id, title)

    def extract_article_sections(self, webpage, base_id):
        for idx, x in enumerate(re.finditer(r'(?s)<td style="text-align: center;">(.+?)</td>', webpage)):
            content = x.group(1)

            title = self._html_search_regex(r'class="ch\d{2}Ttl[AB]">(.+?)\s*&nbsp;<span', content, 'title', fatal=False)

            audio_url = self._search_regex(r'class="amazingaudioplayer-source" data-src="(.+\.mp3)"', content, 'audio url', fatal=False)
            if not title or not audio_url:
                continue

            track_number, title = re.search(r'^(\d+)\s*-\s*(.+)', title).groups()

            yield {
                'id': '%s-%d' % (base_id, idx),
                'title': title,
                'description': self._html_search_regex(r'class="ch\d{2}TrkC">(.+?)</div>', content, 'description', fatal=False),
                'url': audio_url,
                'ext': determine_ext(audio_url, 'mp3'),
                'vcodec': 'none',
                'acodec': 'mp3',
                'track_number': int_or_none(track_number),
            }

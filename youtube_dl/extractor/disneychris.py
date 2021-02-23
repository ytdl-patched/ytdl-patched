from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
)


class DisneyChrisBaseIE(InfoExtractor):
    def extract_article_sections(self, webpage, base_id):
        sections = []
        for idx, x in enumerate(re.finditer(r'(?s)<td style="text-align: center;">(.+?)</td>', webpage)):
            content = x.group(1)

            title = self._search_regex(r'class="ch\d{2}Ttl[AB]">(.+?)\s*&nbsp;<span', content, 'title', group=1, default=False)
            title = clean_html(title)

            description = self._search_regex(r'class="ch\d{2}TrkC">(.+?)</div>', content, 'description', group=1, default=None)
            description = clean_html(description)

            audio_url = self._search_regex(r'class="amazingaudioplayer-source" data-src="(.+\.mp3)"', content, 'audio url', group=1, default=False)
            if not title or not audio_url:
                continue

            title = re.sub(r'^\d+\s*-\s*', '', title)

            sections.append({
                'id': '%s-%d' % (base_id, idx),
                'title': title,
                'description': description,
                'url': audio_url,
                'ext': determine_ext(audio_url, 'mp3'),
                'vcodec': 'none',
                'acodec': 'mp3',
            })

        return sections


class DisneyChrisIE(DisneyChrisBaseIE):
    IE_NAME = 'disneychris'
    _VALID_URL = r'https?://(?:www\.)?disneychris\.com/(?P<id>a-day-at-disneyland|15-disneyland-soundtracks/.+?)\.html'

    def _real_extract(self, url):
        long_id = self._match_id(url)
        video_id = long_id.split('/')[-1]
        webpage = self._download_webpage(url, video_id)
        sections = self.extract_article_sections(webpage, video_id)

        title = None
        for section in re.finditer(r'href="/(.+?)\.html">(.+?)</a>', webpage):
            if section.group(1) == long_id:
                title = section.group(2)
                break
        else:
            title = self._search_regex(r'<title>(.+?)</title>', webpage, 'playlist title', group=1)

        return self.playlist_result(sections, video_id, title)

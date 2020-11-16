# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class ShareVideosIE(InfoExtractor):
    IE_NAME = 'sharevideos'
    _VALID_URL = r'https?://(?:embed\.)?share-videos\.se/auto/(?:embed|video)/(?P<id>\d+)\?uid=(?P<uid>\d+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        uid = self._VALID_URL_RE.match(url).group('uid')
        webpage = self._download_webpage('https://embed.share-videos.se/auto/embed/%s?uid=%s' % (video_id, uid), video_id)

        title = self._og_search_title(webpage, default=None)
        if not title:
            video_webpage = self._download_webpage(
                'https://share-videos.se/auto/video/%s?uid=%s' % (video_id, uid),
                video_id)
            title = self._og_search_title(video_webpage, default=None)
        if not title:
            tags = self._download_json(
                'https://search.share-videos.se/json/movie_tag?svid=%s&site=sv' % video_id,
                video_id, note='Giving it a better name', fatal=None)
            if tags and isinstance(tags, (list, tuple)):
                title = ' '.join(tags)
        if not title:
            self.report_warning('There is no title in this video', video_id)

        entries = self._parse_html5_media_entries(url, webpage, video_id, m3u8_id='hls')
        entry = entries[0]
        self._sort_formats(entry['formats'])
        entry.update({
            'id': video_id,
            'title': title,
        })
        return entry

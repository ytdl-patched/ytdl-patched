from ..utils import KNOWN_EXTENSIONS, determine_ext, mimetype2ext, try_get
from .common import InfoExtractor


class ShareVideosEmbedIE(InfoExtractor):
    IE_NAME = 'sharevideos'
    _VALID_URL = r'https?://(?:embed\.)?share-videos\.se/auto/(?:embed|video)/(?P<id>\d+)\?uid=(?P<uid>\d+)'
    _EMBED_REGEX = [r'<iframe[^>]+?\bsrc\s*=\s*(["\'])(?P<url>(?:https?:)?//embed\.share-videos\.se/auto/embed/\d+\?.*?\buid=\d+.*?)\1']
    TEST = {
        'url': 'http://share-videos.se/auto/video/83645793?uid=13',
        'md5': 'b68d276de422ab07ee1d49388103f457',
        'info_dict': {
            'id': '83645793',
            'title': 'Lock up and get excited',
            'ext': 'mp4'
        },
        'skip': 'TODO: fix nested playlists processing in tests',
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id, uid = mobj.group('id', 'uid')
        webpage = self._download_webpage(f'https://embed.share-videos.se/auto/embed/{video_id}?uid={uid}', video_id)

        title = self._html_extract_title(webpage, 'video title', default=None)
        if not title:
            video_webpage = self._download_webpage(
                f'https://share-videos.se/auto/video/{video_id}?uid={uid}',
                video_id)
            title = self._html_extract_title(video_webpage, 'video title', default=None)
        if not title:
            tags = self._download_json(
                'https://search.share-videos.se/json/movie_tag?svid=%s&site=sv' % video_id,
                video_id, note='Giving it a better name', fatal=None)
            if tags and isinstance(tags, (list, tuple)):
                title = ' '.join(tags)
        if not title:
            self.report_warning('There is no title candidate for this video', video_id)

        def extract_mp4_url(x):
            src = self._search_regex(r'random_file\.push\("(.+)"\);', webpage, 'video url')
            src_type = self._search_regex(r'player.src\({type: \'(.+);\',', webpage, 'video type', fatal=False, default='video/mp4')
            ext = mimetype2ext(src_type) or determine_ext(src).lower()
            return {
                'formats': [{
                    'url': src,
                    'ext': ext if ext in KNOWN_EXTENSIONS else 'mp4',
                }]
            }

        entry = try_get(webpage, (
            lambda x: self._parse_html5_media_entries(url, webpage, video_id, m3u8_id='hls')[0],
            extract_mp4_url,
        ), None)
        self._sort_formats(entry['formats'])
        entry.update({
            'id': video_id,
            'title': title,
        })
        return entry

from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
)


class MixchIE(InfoExtractor):
    IE_NAME = 'mixch'
    # allow omitting last /live in the URL, though it's likely uncommon
    _VALID_URL = r'https?://(?:www\.)?mixch\.tv/u/(?P<id>\d+)'

    TESTS = [{
        'url': 'https://mixch.tv/u/16137876/live',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = 'https://mixch.tv/u/%s/live' % video_id
        webpage = self._download_webpage(url, video_id)

        initial_js_state = self._parse_json(self._search_regex(
            r'(?m)^\s*window\.__INITIAL_JS_STATE__\s*=\s*(\{.+?\});\s*$', webpage, 'initial JS state'), video_id)
        if not initial_js_state.get('liveInfo'):
            raise ExtractorError('Live has ended.', expected=True)

        title = traverse_obj(initial_js_state, ('liveInfo', 'title'))
        comment_count = traverse_obj(initial_js_state, ('liveInfo', 'comments'))
        view_count = traverse_obj(initial_js_state, ('liveInfo', 'visitor'))
        timestamp = traverse_obj(initial_js_state, ('liveInfo', 'created'))
        uploader = traverse_obj(initial_js_state, ('broadcasterInfo', 'name'))

        # the service does not provide alternative resolutions
        hls_url = traverse_obj(initial_js_state, ('liveInfo', 'hls')) or 'https://d1hd0ww6piyb43.cloudfront.net/hls/torte_%s.m3u8' % video_id

        return {
            'id': video_id,
            'title': title,
            'comment_count': comment_count,
            'view_count': view_count,
            'timestamp': timestamp,
            'uploader': uploader,
            'uploader_id': video_id,
            'formats': [{
                'format_id': 'hls',
                'url': hls_url,
                'protocol': 'm3u8',
                'ext': 'mp4',
            }],
            'is_live': True,
            'webpage_url': url,
        }

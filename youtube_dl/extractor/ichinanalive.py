# coding: utf-8
from __future__ import unicode_literals
import json

from .common import InfoExtractor
from ..utils import ExtractorError, try_get
from ..compat import compat_str


# the real service name of this extractor is "17live",
#   but identifiers cannot start with numbers.
# class name of this extractor is taken from official pronounce in Japanese,
#   so it will be replace as: "1"="ichi", "7"="nana", "live"=as-is .
class IchinanaLiveIE(InfoExtractor):
    IE_NAME = '17live'
    _VALID_URL = r'https?://(?:www\.)?17\.live/live/(?P<id>\d+)'
    # downloading works, but no information being extracted!
    _WORKING = False

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = 'https://17.live/live/%s' % video_id
        # self._download_webpage(url, video_id)

        alive_data = self._download_json(
            'https://api-dsa.17app.co/api/v1/lives/%s/viewers/alive' % video_id, video_id,
            headers={'Referer': url}, data=json.dumps({'liveStreamID': video_id}).encode('utf-8'))

        video_urls = try_get(alive_data, lambda x: x['rtmpUrls'], list)
        if not video_urls:
            raise ExtractorError('unable to extract live URL information')
        formats = []
        for data in video_urls:
            for (name, value) in data.items():
                if not isinstance(value, compat_str):
                    continue
                if not value.startswith('http'):
                    continue
                preference = 0.0
                if 'web' in name:
                    preference -= 0.25
                if 'High' in name:
                    preference += 1.0
                if 'Low' in name:
                    preference -= 0.5
                formats.append({
                    'format_id': name,
                    'url': value,
                    'preference': preference,
                    # 'ffmpeg' protocol is added by ytdl-patched, same as 'm3u8'
                    'protocol': 'ffmpeg',
                    'http_headers': {'Referer': url},
                    'ext': 'mp4',
                    'vcodec': 'h264',
                    'acodec': 'aac',
                })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_id,
            'formats': formats,
            'is_live': True,
            # TODO: implement information extraction
            # TODO: add minimum conversion
        }

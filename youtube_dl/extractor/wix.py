from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    unescapeHTML,
)


class WixIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<user>[a-z0-9]+)\.wixsite\.com/(?P<id>[a-zA-Z0-9/-]+)'
    _TEST = {}

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_tags = self._parse_html5_media_entries(url, webpage, video_id, m3u8_id='hls')
        wix_video_tags = self._parse_wix_video_entries(webpage, video_id)
        result = []
        result.extend(video_tags)
        result.extend(wix_video_tags)
        return self.playlist_result(result)

    def _parse_wix_video_entries(self, webpage, video_id):
        result = []
        for tag in re.compile(r'<wix-video\s+(?:\s*[a-zA-Z-]="[^"]*")*data-video-info="([^"]*)"(?:\s*[a-zA-Z-]="[^"]*")*').finditer(webpage):
            json = self._parse_json(unescapeHTML(tag.group(1)), video_id)
            # staticVU + videoId + "/" + quality + "/" + videoFormat + "/file." + videoFormat
            staticVU = json.get('staticVideoUrl')
            videoId = json.get('videoId')
            videoFormat = json.get('videoFormat')
            qualities = json.get('qualities')
            videoWidth = int_or_none(json.get('videoWidth'))
            videoHeight = int_or_none(json.get('videoHeight'))
            formats = []
            for quality in qualities:
                fmt_name = quality.get('quality')
                height = None
                width = None
                if fmt_name:
                    height = int_or_none(fmt_name[:-1])
                if height:
                    width = height * videoWidth / videoHeight
                formats.append({
                    'url': '%s%s/%s/%s/file.%s' % (staticVU, videoId, quality, videoFormat, videoFormat),
                    'ext': videoFormat,
                    'format_id': fmt_name,
                    'filesize': int_or_none(quality.get('size')),
                    'height': height or 0,
                    'width': width or 0,
                })
            result.append({
                'id': videoId,
                'title': videoId,
                'formats': formats
            })
        return result

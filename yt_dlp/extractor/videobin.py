# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
)


class VideobinBaseIE(InfoExtractor):
    IE_DESC = False  # Do not list


class VideobinIE(VideobinBaseIE):
    IE_NAME = 'videobin'
    _VALID_URL = r'https?:\/\/(?:www\.)?videobin\.co/(?P<id>[a-z0-9]{10,})'
    _TEST = {}
    _URL_REGEX = re.compile(r'(?ms)sources:\s*(\[\s*"[^"]+"\s*(?:,\s*"[^"]*"\s*)*])\s*,')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = 'Watch mp4'

        entries = self._parse_json(self._URL_REGEX.search(webpage).group(1), video_id)
        if not entries:
            raise ExtractorError('Video is unavailable for some reasons', expected=True)
        entry = {
            'formats': []
        }
        for url in entries:
            entry['formats'] += self._media_formats(url, 'video', video_id)
        self._sort_formats(entry['formats'])
        entry.update({
            'id': video_id,
            'title': title,
        })
        return entry

    def _media_formats(self, full_url, cur_media_type, video_id):
        ext = determine_ext(full_url)
        if ext == 'm3u8':
            formats = self._extract_m3u8_formats(
                full_url, video_id, ext='mp4', fatal=False)
        elif ext == 'mpd':
            formats = self._extract_mpd_formats(
                full_url, video_id, fatal=False)
        else:
            formats = [{
                'url': full_url,
                'vcodec': 'none' if cur_media_type == 'audio' else None,
            }]
        return formats

# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj
from ..compat import compat_str


class SkebIE(InfoExtractor):
    _VALID_URL = r'https?://skeb\.jp/@[^/]+/works/(?P<id>\d+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        nuxt_data = self._search_nuxt_data(webpage, video_id)

        title = nuxt_data.get('title')
        descripion = nuxt_data.get('description')
        reply = nuxt_data.get('thanks')
        uploader = traverse_obj(nuxt_data, ('creator', 'name'))
        uploader_id = traverse_obj(nuxt_data, ('creator', 'screen_name'))
        age_limit = 18 if nuxt_data.get('nsfw') else 0

        parent = {
            'title': title,
            'descripion': descripion,
            'reply': reply,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'age_limit': age_limit,
        }

        entries = []
        for item in nuxt_data.get('previews') or []:
            subs = None
            if item.get('vtt_url'):
                subs = {
                    'jpn': [{
                        'url': item.get('vtt_url'),
                        'ext': 'vtt',
                    }]
                }
            entries.append({
                'id': compat_str(item.get('id')),
                'url': item.get('url'),
                'thumbnail': item.get('poster_url'),
                'subtitles': subs,
                'width': traverse_obj(item, ('information', 'width')),
                'height': traverse_obj(item, ('information', 'height')),
                'duration': traverse_obj(item, ('information', 'duration')),
                'filesize': traverse_obj(item, ('information', 'byte_size')),
                'fps': traverse_obj(item, ('information', 'frame_rate')),
                'ext': traverse_obj(item, ('information', 'extension')),
            })

        if not entries:
            raise ExtractorError('No attachment found in this commission.', expected=True)
        elif len(entries) == 1:
            entries[0].update(parent)
            return entries[0]
        else:
            parent.update({
                '_type': 'multi_video',
                'entries': entries,
            })
            return parent

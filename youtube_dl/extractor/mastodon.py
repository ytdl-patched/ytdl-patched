from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import clean_html


class MastodonBaseIE(InfoExtractor):

    @classmethod
    def suitable(cls, url):
        # should be filtered at generic.py and pass to mastodon extractors
        #   ... or prefix "mastodon:" by hand
        return (url.startswith('mastodon:') or url.startswith('mstdn:') or url.startswith('mtdn:')) and re.match(cls._VALID_URL, url)


class MastodonIE(MastodonBaseIE):
    IE_NAME = 'mastodon'
    _VALID_URL = r'(?:(?:mastodon|mstdn|mtdn):)?https?://(?P<domain>[a-zA-Z0-9._-]+?)/@(?P<username>[a-zA-Z0-9_-]+?)/(?P<id>\d+)'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        domain = mobj.group('domain')
        username = mobj.group('username')
        video_id = mobj.group('id')

        url = 'https://%s/@%s/%s' % (domain, username, video_id)

        api_response = self._download_json('https://%s/api/v1/statuses/%s' % (domain, video_id), video_id)

        formats = []
        thumbnail, description = None, None
        for atch in api_response.get('media_attachments', []):
            if atch.get('type') != 'video':
                continue
            meta = atch.get('meta')
            if not meta:
                continue
            thumbnail = meta.get('preview_url')
            description = atch.get('description')
            formats.append({
                'format_id': atch.get('id'),
                'protocol': 'http',
                'url': atch.get('url'),
                'fps': meta.get('fps'),
                'width': meta.get('width'),
                'height': meta.get('height'),
                'duration': meta.get('duration'),
            })
            break

        account, uploader, uploader_id = api_response.get('account'), None, None
        if account:
            uploader, uploader_id = account.get('username'), account.get('id')

        return {
            'id': video_id,
            'title': clean_html(api_response.get('content')),
            'description': description,
            'formats': formats,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'uploader_id': uploader_id,
        }


class MastodonUserIE(MastodonBaseIE):
    IE_NAME = 'mastodon:user'

    def _real_extract(self, url):
        # WIP
        pass

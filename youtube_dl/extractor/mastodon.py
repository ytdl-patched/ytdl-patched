from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import ExtractorError, clean_html


class MastodonBaseIE(InfoExtractor):

    def _test_mastodon_instance(self, hostname, video_id):
        # TODO: make hostname white(allow)llist
        if hostname in []:
            return True

        # HELP: more cases needed
        if hostname in ['medium.com']:
            return False

        # self.report_warning('Testing if %s is a Mastodon instance because it is not listed in either instances.social or joinmastodon.org.' % hostname)

        try:
            # try /api/v1/instance
            api_request_instance = self._download_json(
                'https://%s/api/v1/instance' % hostname, video_id,
                note='Testing Mastodon API /api/v1/instance')
            if api_request_instance.get('uri') != hostname:
                return False
            if not api_request_instance.get('title'):
                return False

            # try /api/v1/directory
            api_request_directory = self._download_json(
                'https://%s/api/v1/directory' % hostname, video_id,
                note='Testing Mastodon API /api/v1/directory')
            if not isinstance(api_request_directory, (tuple, list)):
                return False
        except (IOError, ExtractorError):
            return False

        # this is probably mastodon instance
        return True


class MastodonIE(MastodonBaseIE):
    IE_NAME = 'mastodon'
    _VALID_URL = r'(?:(?:mastodon|mstdn|mtdn):)?https?://(?P<domain>[a-zA-Z0-9._-]+?)/@(?P<username>[a-zA-Z0-9_-]+?)/(?P<id>\d+)'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        domain = mobj.group('domain')
        username = mobj.group('username')
        video_id = mobj.group('id')

        if not self._test_mastodon_instance(domain, video_id):
            return self.url_result(url, ie='Generic')

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

        account, uploader_id = api_response.get('account'), None
        if account:
            uploader_id = account.get('id')

        return {
            'id': video_id,
            'title': clean_html(api_response.get('content')),
            'description': description,
            'formats': formats,
            'thumbnail': thumbnail,
            'uploader': username,
            'uploader_id': uploader_id,
        }


class MastodonUserIE(MastodonBaseIE):
    IE_NAME = 'mastodon:user'

    def _real_extract(self, url):
        # WIP
        pass

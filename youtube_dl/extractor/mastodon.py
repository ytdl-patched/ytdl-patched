from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import ExtractorError, clean_html

known_valid_instances = []


class MastodonBaseIE(InfoExtractor):

    def _test_mastodon_instance(self, hostname):
        # TODO: make hostname white(allow)list
        if hostname in []:
            return True
        if hostname in known_valid_instances:
            return True

        # HELP: more cases needed
        if hostname in ['medium.com']:
            return False

        # self.report_warning('Testing if %s is a Mastodon instance because it is not listed in either instances.social or joinmastodon.org.' % hostname)

        try:
            # try /api/v1/instance
            api_request_instance = self._download_json(
                'https://%s/api/v1/instance' % hostname, hostname,
                note='Testing Mastodon API /api/v1/instance')
            if api_request_instance.get('uri') != hostname:
                return False
            if not api_request_instance.get('title'):
                return False

            # try /api/v1/directory
            api_request_directory = self._download_json(
                'https://%s/api/v1/directory' % hostname, hostname,
                note='Testing Mastodon API /api/v1/directory')
            if not isinstance(api_request_directory, (tuple, list)):
                return False
        except (IOError, ExtractorError):
            return False

        # this is probably mastodon instance
        known_valid_instances.append(hostname)
        return True


class MastodonIE(MastodonBaseIE):
    IE_NAME = 'mastodon'
    _VALID_URL = r'(?P<prefix>(?:mastodon|mstdn|mtdn):)?https?://(?P<domain>[a-zA-Z0-9._-]+)/@(?P<username>[a-zA-Z0-9_-]+)/(?P<id>\d+)'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        prefix = mobj.group('prefix')
        domain = mobj.group('domain')
        username = mobj.group('username')
        video_id = mobj.group('id')

        if not prefix and not self._test_mastodon_instance(domain):
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
    _VALID_URL = r'(?P<prefix>(?:mastodon|mstdn|mtdn):)?https?://(?P<domain>[a-zA-Z0-9._-]+)/@(?P<id>[a-zA-Z0-9_-]+)/?(?:\?.*)?'
    _TESTS = [{
        'url': 'https://mstdn.jp/@kris57',
        'info_dict': {
            'title': 'Toots from @kris57@mstdn.jp',
            'id': 'kris57',
        },
        'playlist_mincount': 261,
    }, {
        'url': 'https://pawoo.net/@iriomote_yamaneko',
        'info_dict': {
            'title': 'Toots from @iriomote_yamaneko@pawoo.net',
            'id': 'iriomote_yamaneko',
        },
        'playlist_mincount': 80500,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        prefix = mobj.group('prefix')
        domain = mobj.group('domain')
        user_id = mobj.group('id')

        if not prefix and not self._test_mastodon_instance(domain):
            return self.url_result(url, ie='Generic')

        # FIXME: filter toots with video or youtube attached
        # TODO: replace to api calls if possible
        results = []
        index = 1
        next_url = 'https://%s/@%s' % (domain, user_id)
        while True:
            webpage = self._download_webpage(next_url, user_id, note='Downloading page %d' % index)
            for matches in re.finditer(r'(?isx)<a class=(["\'])(?:.*?\s+)*status__relative-time(?:\s+.*)*\1\s+(?:rel=(["\'])noopener\2)?\s+href=(["\'])(https://%s/@%s/(\d+))\3>'
                                       % (re.escape(domain), re.escape(user_id)), webpage):
                _, _, _, url, video_id = matches.groups()
                results.append(self.url_result(url, id=video_id))
            next_url = self._search_regex(
                # other instances may have different tags
                # r'<div\s+class=(["\'])entry\1>.*?<a\s+class=(["\'])(?:.*\s+)*load-more(?:\s+.*)*\2\s+href=(["\'])(.+)\3>.+</a></div>\s*</div>',
                r'class=\"load-more load-gap\" href=\"([^\"]+)\">.+<\/a><\/div>\s*<\/div>',
                webpage, 'next cursor url', default=None, fatal=False)
            if not next_url:
                break
            index += 1
        return self.playlist_result(results, user_id, 'Toots from @%s@%s' % (user_id, domain))

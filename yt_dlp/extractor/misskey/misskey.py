# coding: utf-8
from __future__ import unicode_literals

import re

from .instances import instances
from ..common import InfoExtractor
from ...utils import ExtractorError, determine_ext, mimetype2ext, preferredencoding, traverse_obj, unified_timestamp
from ...compat import compat_str


known_valid_instances = set()


class MisskeyBaseIE(InfoExtractor):

    @classmethod
    def suitable(cls, url):
        mobj = re.match(cls._VALID_URL, url)
        if not mobj:
            return False
        prefix = mobj.group('prefix')
        hostname = mobj.group('domain')
        return cls._test_mastodon_instance(None, hostname, True, prefix)

    @staticmethod
    def _test_mastodon_instance(ie, hostname, skip, prefix):
        hostname = hostname.encode('idna')
        if not isinstance(hostname, compat_str):
            hostname = hostname.decode(preferredencoding())

        if hostname in instances:
            return True
        if hostname in known_valid_instances:
            return True

        # HELP: more cases needed
        if hostname in ['medium.com', 'lbry.tv']:
            return False

        # continue anyway if "misskey:" is added to URL
        if prefix:
            return True
        # without --check-misskey-instance,
        #   skip further instance check
        if skip:
            return False

        ie.report_warning('Testing if %s is a Misskey instance because it is not listed in either instances.social or joinmastodon.org.' % hostname)

        try:
            # try /api/stats
            api_request_stats = ie._download_json(
                'https://%s/api/stats' % hostname, hostname,
                note='Testing Misskey API /api/stats', data='{}')
            if not isinstance(api_request_stats.get('usersCount'), int):
                return False
            if not isinstance(api_request_stats.get('instances'), int):
                return False

            # try /api/server-info
            api_request_serverinfo = ie._download_json(
                'https://%s/api/server-info' % hostname, hostname,
                note='Testing Misskey API /api/server-info', data='{}')
            if not traverse_obj(api_request_serverinfo, ('cpu', 'model'), expected_type=compat_str):
                return False
            if not traverse_obj(api_request_serverinfo, ('cpu', 'cores'), expected_type=int):
                return False
        except (IOError, ExtractorError):
            return False

        # this is probably misskey instance
        known_valid_instances.add(hostname)
        return True


class MisskeyIE(MisskeyBaseIE):
    IE_NAME = 'misskey'
    _VALID_URL = r'(?P<prefix>(?:misskey|msky|msk):)?https?://(?P<domain>[a-zA-Z0-9._-]+)/notes/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'note': 'embed video',
        'url': 'https://misskey.io/notes/8pp0c7gsbm',
        'info_dict': {
            'id': '8pp0c7gsbm',
            'title': 'Misskeyダウンローダーのテストケース',
            'timestamp': 1629529895,
            'uploader': 'nao20010128',
            'uploader_id': '8pp040sbza',
            'visibility': 'public',
            'age_limit': 0,
        },
    }, {
        'note': 'embed video with YouTube',
        'url': 'https://misskey.io/notes/8pp0di8s4t',
        # we have to port mfm-js in Node.js to mimick embed URL extraction
        # https://github.com/misskey-dev/misskey/blob/develop/src/misc/extract-url-from-mfm.ts
        # https://github.com/misskey-dev/misskey/blob/develop/src/client/ui/chat/note.vue
        'only_matching': True,
    }, {
        'note': 'no video',
        'url': 'https://misskey.io/notes/8pp04mprzx',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        domain = mobj.group('domain')
        video_id = mobj.group('id')

        api_response = self._download_json(
            'https://%s/api/notes/show' % domain, video_id,
            # building POST payload without using json module
            data=('{"noteId":"%s"}' % video_id).encode())

        title = api_response.get('text')
        timestamp = unified_timestamp(api_response.get('createdAt'))
        uploader = traverse_obj(api_response, ('user', 'name'), ('user', 'username'), expected_type=compat_str)
        uploader_id = traverse_obj(api_response, ('userId', ), ('user', 'id'), expected_type=compat_str)
        visibility = api_response.get('visibility')

        thumbnail = traverse_obj(api_response, ('files', 0, 'thumbnailUrl'), expected_type=compat_str)
        age_limit = 18 if traverse_obj(api_response, ('files', 0, 'isSensitive'), expected_type=bool) else 0

        formats = []
        for file in api_response.get('files') or []:
            mimetype = file.get('type')
            if not mimetype or not mimetype.startswith('video/'):
                continue
            formats.append({
                'format_id': file.get('id'),
                'url': file.get('url'),
                'ext': mimetype2ext(mimetype) or determine_ext(file.get('name')),
                'filesize': file.get('size'),
            })

        # must be here to prevent circular import
        from .complement import _COMPLEMENTS
        complements = [x() for x in _COMPLEMENTS if re.match(x._INSTANCE_RE, domain)]
        if complements:
            self.to_screen('%d complement(s) found, running them to get more formats' % len(complements))
            for cmpl in complements:
                try:
                    formats.extend(cmpl._extract_formats(self, video_id, api_response))
                except ExtractorError as ex:
                    self.report_warning('Error occured in complement "%s": %s' % (cmpl, ex))

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'timestamp': timestamp,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'visibility': visibility,
            'thumbnail': thumbnail,
            'age_limit': age_limit,
            'formats': formats,
        }


class MisskeyUserIE(MisskeyBaseIE):
    IE_NAME = 'misskey:user'
    _VALID_URL = r'(?P<prefix>(?:misskey|msky|msk):)?https?://(?P<domain>[a-zA-Z0-9._-]+)/@(?P<id>[a-zA-Z0-9_-]+)/?(?:\?.*)?$'
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
        domain = mobj.group('domain')
        user_id = mobj.group('id')

        # TODO: imcomplete
        return domain, user_id

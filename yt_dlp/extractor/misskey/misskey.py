# coding: utf-8
from __future__ import unicode_literals
import itertools
import json

import re

from .instances import instances
from ..common import InfoExtractor
from ...utils import (
    ExtractorError,
    determine_ext,
    mimetype2ext,
    preferredencoding,
    smuggle_url,
    traverse_obj,
    unified_timestamp
)
from ...compat import compat_str


known_valid_instances = set()


class MisskeyBaseIE(InfoExtractor):

    @classmethod
    def suitable(cls, url):
        mobj = re.match(cls._VALID_URL, url)
        if not mobj:
            return False
        prefix = mobj.group('prefix')
        hostname = mobj.group('instance')
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
    _VALID_URL = r'(?P<prefix>(?:misskey|msky|msk):)?https?://(?P<instance>[a-zA-Z0-9._-]+)/notes/(?P<id>[a-zA-Z0-9]+)'
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
        # https://github.com/misskey-dev/mfm.js/blob/develop/src/internal/parser.pegjs
        'only_matching': True,
    }, {
        'note': 'no video',
        'url': 'https://misskey.io/notes/8pp04mprzx',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        instance = mobj.group('instance')
        video_id = mobj.group('id')

        api_response = self._download_json(
            'https://%s/api/notes/show' % instance, video_id,
            # building POST payload without using json module
            data=('{"noteId":"%s"}' % video_id).encode())

        title = api_response.get('text')
        timestamp = unified_timestamp(api_response.get('createdAt'))
        uploader = traverse_obj(api_response, ('user', 'name'), ('user', 'username'), expected_type=compat_str)
        uploader_id = traverse_obj(api_response, ('userId', ), ('user', 'id'), expected_type=compat_str)
        visibility = api_response.get('visibility')

        thumbnail = traverse_obj(api_response, ('files', 0, 'thumbnailUrl'), expected_type=compat_str)
        age_limit = 18 if traverse_obj(api_response, ('files', 0, 'isSensitive'), expected_type=bool) else 0

        from .complement import _COMPLEMENTS
        complements = [x() for x in _COMPLEMENTS if re.match(x._INSTANCE_RE, instance)]

        files = []
        for idx, file in enumerate(api_response.get('files') or []):
            formats = []
            mimetype = file.get('type')
            if not mimetype or (not mimetype.startswith('video/') and not mimetype.startswith('audio/')):
                continue
            formats.append({
                'format_id': file.get('id'),
                'url': file.get('url'),
                'ext': mimetype2ext(mimetype) or determine_ext(file.get('name')),
                'filesize': file.get('size'),
            })

            # must be here to prevent circular import
            if complements:
                self.to_screen('%d complement(s) found, running them to get more formats' % len(complements))
                for cmpl in complements:
                    try:
                        formats.extend(cmpl._extract_formats(self, video_id, file))
                    except ExtractorError as ex:
                        self.report_warning('Error occured in complement "%s": %s' % (cmpl, ex))

            self._sort_formats(formats)

            files.append({
                'id': '%s-%d' % (video_id, idx),
                'title': title,
                'formats': formats,
            })

        base = {
            'id': video_id,
            'title': title,
            'timestamp': timestamp,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'visibility': visibility,
            'thumbnail': thumbnail,
            'age_limit': age_limit,
        }
        if not files:
            raise ExtractorError('This note does not have any media file.', expected=True)
        elif len(files) == 1:
            files[0].update(base)
            return files[0]
        else:
            base.update({
                '_type': 'multi_video',
                'entries': files,
            })
            return base


class MisskeyUserIE(MisskeyBaseIE):
    IE_NAME = 'misskey:user'
    _VALID_URL = r'(?P<prefix>(?:misskey|msky|msk):)?https?://(?P<instance>[a-zA-Z0-9._-]+)/@(?P<id>[a-zA-Z0-9_-]+)(?:@(?P<instance2>[a-zA-Z0-9_.-]+))?'
    _TESTS = [{
        'note': 'refer to another instance',
        'url': 'https://misskey.io/@vitaone@misskey.dev',
        'playlist_mincount': 0,
    }, {
        'url': 'https://misskey.io/@kubaku@misskey.dev',
        'playlist_mincount': 1,
    }, {
        'url': 'https://misskey.dev/@kubaku',
        'playlist_mincount': 1,
    }]

    def _entries(self, instance, user_id):
        until_id = None
        for i in itertools.count(1):
            page = self._download_json(
                'https://%s/api/users/notes' % instance, user_id,
                note='Downloading page %d' % i, data=json.dumps({
                    'limit': 100,
                    'userId': user_id,
                    'withFiles': True,
                    **({'untilId': until_id} if until_id else {}),
                }).encode())
            yield from page
            until_id = traverse_obj(page, (-1, 'id'))
            if not until_id:
                break

    def _mapfilter_items_with_media(self, instance, entries):
        for item in entries:
            mimetypes = [x.get('type') for x in item.get('files') or [] if x]
            if any(x and (x.startswith('video/') or x.startswith('audio/')) for x in mimetypes):
                yield self.url_result(smuggle_url('https://%s/notes/%s' % (instance, item.get('id')), item))

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        instance = mobj.group('instance2') or mobj.group('instance')
        user_handle = mobj.group('id')

        user_info = self._download_json(
            'https://%s/api/users/show' % instance, user_handle,
            note='Fetching user info',
            # building POST payload without using json module
            data=('{"username":"%s"}' % user_handle).encode())
        user_id = user_info.get('id')
        uploader = user_info.get('name')
        uploader_id = user_info.get('username')
        description = user_info.get('description')

        entries = self._mapfilter_items_with_media(instance, self._entries(instance, user_id))

        return {
            '_type': 'playlist',
            'entries': entries,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'description': description,
        }

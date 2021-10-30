# coding: utf-8
from __future__ import unicode_literals

import itertools
import re


from .instances import instances
from ..common import InfoExtractor, SelfHostedInfoExtractor
from ..peertube.peertube import PeerTubeIE
from ...utils import ExtractorError, clean_html, preferredencoding, get_first_group


known_valid_instances = set()


class MastodonBaseIE(SelfHostedInfoExtractor):
    _SH_VALID_CONTENT_STRINGS = (
        ',"settings":{"known_fediverse":',  # Mastodon initial-state
        '<li><a href="https://docs.joinmastodon.org/">Documentation</a></li>',
        '<title>Pleroma</title>',
        '<noscript>To use Pleroma, please enable JavaScript.</noscript>',
        '<noscript>To use Soapbox, please enable JavaScript.</noscript>',
        'Alternatively, try one of the <a href="https://apps.gab.com">native apps</a> for Gab Social for your platform.',
    )
    _SH_VALID_CONTENT_SOFTWARES = ('mastodon', 'mastodon', 'pleroma', 'pleroma', 'pleroma', 'gab')
    _SH_VALID_CONTENT_REGEXES = (
        # double quotes on Mastodon, single quotes on Gab Social
        r'<script id=[\'"]initial-state[\'"] type=[\'"]application/json[\'"]>{"meta":{"streaming_api_base_url":"wss://',
    )

    @classmethod
    def suitable(cls, url):
        mobj = cls._match_valid_url(url)
        if not mobj:
            return False
        prefix = mobj.group('prefix')
        hostname = get_first_group(mobj, 'domain_1', 'domain_2', 'domain')
        return cls._test_mastodon_instance(None, hostname, True, prefix)

    @staticmethod
    def _test_mastodon_instance(ie, hostname, skip, prefix):
        if isinstance(hostname, bytes):
            hostname = hostname.decode(preferredencoding())
        hostname = hostname.encode('idna').decode('utf-8')

        if hostname in instances:
            return True
        if hostname in known_valid_instances:
            return True

        # HELP: more cases needed
        if hostname in ['medium.com', 'lbry.tv']:
            return False

        # continue anyway if "mastodon:" is added to URL
        if prefix:
            return True
        # without --check-mastodon-instance,
        #   skip further instance check
        if skip:
            return False

        ie.report_warning('Testing if %s is a Mastodon instance because it is not listed in either instances.social, joinmastodon.org, the-federation.info or fediverse.observer.' % hostname)

        try:
            # try /api/v1/instance
            api_request_instance = ie._download_json(
                'https://%s/api/v1/instance' % hostname, hostname,
                note='Testing Mastodon API /api/v1/instance')
            if api_request_instance.get('uri') != hostname:
                return False
            if not api_request_instance.get('title'):
                return False

            # try /api/v1/directory
            api_request_directory = ie._download_json(
                'https://%s/api/v1/directory' % hostname, hostname,
                note='Testing Mastodon API /api/v1/directory')
            if not isinstance(api_request_directory, (tuple, list)):
                return False
        except (IOError, ExtractorError):
            return False

        # this is probably mastodon instance
        known_valid_instances.add(hostname)
        return True

    @staticmethod
    def _is_probe_enabled(ydl):
        return ydl.params.get('check_mastodon_instance', False)

    @classmethod
    def _probe_selfhosted_service(cls, ie: InfoExtractor, url, hostname):
        prefix = ie._search_regex(
            # (MastodonIE._VALID_URL,
            #  MastodonUserIE._VALID_URL,
            #  MastodonUserNumericIE._VALID_URL),
            cls._VALID_URL,
            url, 'mastodon test', group='prefix', default=None)
        return MastodonIE._test_mastodon_instance(ie, hostname, False, prefix)

    def _determine_instance_software(self, host, webpage=None):
        if webpage:
            for i, string in enumerate(self._SH_VALID_CONTENT_STRINGS):
                if string in webpage:
                    return self._SH_VALID_CONTENT_SOFTWARES[i]
            if any(s in webpage for s in PeerTubeIE._SH_VALID_CONTENT_STRINGS):
                return 'peertube'

        nodeinfo_href = self._download_json(
            f'https://{host}/.well-known/nodeinfo', host, 'Downloading instance nodeinfo link')

        nodeinfo = self._download_json(
            nodeinfo_href['links'][-1]['href'], host, 'Downloading instance nodeinfo')

        return nodeinfo['software']['name']


class MastodonIE(MastodonBaseIE):
    # NOTE: currently, compatible self-hosted products like Gab Social requires probing for each instances.
    # TODO: include all these compatible products into instance list
    IE_NAME = 'mastodon'
    _VALID_URL = r'''(?x)
        (?P<prefix>(?:mastodon|mstdn|mtdn):)?
        (?:
            # URL with or without prefix
            https?://(?P<domain_1>[^/\s]+)/
            (?:
                # mastodon
                @(?P<username_1>[a-zA-Z0-9_-]+)
                |web/statuses
                # gab social
                |(?P<username_2>[a-zA-Z0-9_-]+)/posts
                # mastodon legacy (?)
                |users/(?P<username_3>[a-zA-Z0-9_-]+)/statuses
                # pleroma
                |notice
                # pleroma (OStatus standard?) - https://git.pleroma.social/pleroma/pleroma/-/blob/e9859b68fcb9c38b2ec27a45ffe0921e8d78b5e1/lib/pleroma/web/router.ex#L607
                |objects
                |activities
            )/
        # haruhi-dl compatible: "mastodon:example.com:blablabla"
        |(?P<domain_2>[^:\s]+)(?P<short_form>:))
        (?P<id>[0-9a-zA-Z-]+)
    '''

    @classmethod
    def suitable(cls, url):
        mobj = cls._match_valid_url(url)
        if not mobj:
            return False
        prefix, is_short = mobj.group('prefix', 'short_form')
        if is_short and prefix:
            return True
        return super(MastodonIE, cls).suitable(url)

    _TESTS = [{
        'note': 'embed video without NSFW',
        'url': 'https://mstdn.jp/@nao20010128nao/105395495018076252',
        'info_dict': {
            'id': '105395495018076252',
            'title': 'てすや\nhttps://www.youtube.com/watch?v=jx0fBBkaF1w',
            'uploader': 'nao20010128nao',
            'uploader_id': 'nao20010128nao',
            'age_limit': 0,
        },
    }, {
        'note': 'embed video with NSFW',
        'url': 'https://mstdn.jp/@nao20010128nao/105395503690401921',
        'info_dict': {
            'id': '105395503690401921',
            'title': 'Mastodonダウンローダーのテストケース用なので別に注意要素無いよ',
            'uploader': 'nao20010128nao',
            'uploader_id': 'nao20010128nao',
            'age_limit': 18,
        },
    }, {
        'note': 'uploader_id not present in URL',
        'url': 'https://mstdn.jp/web/statuses/105395503690401921',
        'info_dict': {
            'id': '105395503690401921',
            'title': 'Mastodonダウンローダーのテストケース用なので別に注意要素無いよ',
            'uploader': 'nao20010128nao',
            'uploader_id': 'nao20010128nao',
            'age_limit': 18,
        },
    }, {
        'note': 'has YouTube as card',
        'url': 'https://mstdn.jp/@vaporeon/105389634797745542',
        'add_ie': ['Youtube'],
        'info_dict': {},
    }, {
        'note': 'has radiko as card',
        'url': 'https://mstdn.jp/@vaporeon/105389280534065010',
        'only_matching': True,
    }, {
        'url': 'https://pawoo.net/@iriomote_yamaneko/105370643258491818',
        'only_matching': True,
    }, {
        'note': 'uploader_id has only one character',
        'url': 'https://mstdn.kemono-friends.info/@m/103997543924688111',
        'info_dict': {
            'id': '103997543924688111',
            'uploader_id': 'm',
        },
    }, {
        'note': 'short form, compatible with haruhi-dl\'s usage',
        'url': 'mastodon:mstdn.jp:105395495018076252',
        'info_dict': {
            'id': '105395495018076252',
            'title': 'てすや\nhttps://www.youtube.com/watch?v=jx0fBBkaF1w',
            'uploader': 'nao20010128nao',
            'uploader_id': 'nao20010128nao',
            'age_limit': 0,
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        domain = get_first_group(mobj, 'domain_1', 'domain_2')
        uploader_id = get_first_group(mobj, 'username_1', 'username_2', 'username_3')

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

        account, uploader = api_response.get('account'), None
        if account:
            uploader = account.get('display_name')
            uploader_id = uploader_id or account.get('username')

        age_limit = 18 if api_response.get('sensitive') else 0

        card = api_response.get('card')
        if not formats and card:
            return self.url_result(card.get('url'))

        return {
            'id': video_id,
            'title': clean_html(api_response.get('content')),
            'description': description,
            'formats': formats,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'age_limit': age_limit,
        }


class MastodonUserIE(MastodonBaseIE):
    IE_NAME = 'mastodon:user'
    _VALID_URL = r'(?P<prefix>(?:mastodon|mstdn|mtdn):)?https?://(?P<domain>[a-zA-Z0-9._-]+)/@(?P<id>[a-zA-Z0-9_-]+)/?(?:\?.*)?$'
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

    def _entries(self, domain, user_id):
        # FIXME: filter toots with video or youtube attached
        # TODO: replace to api calls if possible
        next_url = 'https://%s/@%s' % (domain, user_id)
        for index in itertools.count(1):
            webpage = self._download_webpage(next_url, user_id, note='Downloading page %d' % index)
            for matches in re.finditer(r'(?x)<a class=(["\'])(?:.*?\s+)*status__relative-time(?:\s+.*)*\1\s+(?:rel=(["\'])noopener\2)?\s+href=(["\'])(https://%s/@%s/(\d+))\3>'
                                       % (re.escape(domain), re.escape(user_id)), webpage):
                _, _, _, url, video_id = matches.groups()
                yield self.url_result(url, id=video_id)
            next_url = self._search_regex(
                # other instances may have different tags
                # r'<div\s+class=(["\'])entry\1>.*?<a\s+class=(["\'])(?:.*\s+)*load-more(?:\s+.*)*\2\s+href=(["\'])(.+)\3>.+</a></div>\s*</div>',
                r'class=\"load-more load-gap\" href=\"([^\"]+)\">.+<\/a><\/div>\s*<\/div>',
                webpage, 'next cursor url', default=None, fatal=False)
            if not next_url:
                break

    def _real_extract(self, url):
        domain, user_id = self._match_valid_url(url).group('domain', 'id')

        entries = self._entries(domain, user_id)
        return self.playlist_result(entries, user_id, 'Toots from @%s@%s' % (user_id, domain))


class MastodonUserNumericIE(MastodonBaseIE):
    IE_NAME = 'mastodon:user:numeric_id'
    _VALID_URL = r'(?P<prefix>(?:mastodon|mstdn|mtdn):)?https?://(?P<domain>[a-zA-Z0-9._-]+)/web/accounts/(?P<id>\d+)/?'
    _TESTS = [{
        'url': 'https://mstdn.jp/web/accounts/330076',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        prefix, domain, user_id = self._match_valid_url(url).group('prefix', 'domain', 'id')

        if not prefix and not self._test_mastodon_instance(domain):
            return self.url_result(url, ie='Generic')

        api_response = self._download_json('https://%s/api/v1/accounts/%s' % (domain, user_id), user_id)
        username = api_response.get('username')
        return self.url_result('https://%s/@%s' % (domain, username), video_id=username)

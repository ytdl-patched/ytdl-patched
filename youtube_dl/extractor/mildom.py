# coding: utf-8
from __future__ import unicode_literals

from datetime import datetime
import itertools
import json
import base64

from .common import InfoExtractor
from ..utils import (
    std_headers,
    update_url_query,
    try_get,
)
from ..compat import compat_str


class MildomBaseIE(InfoExtractor):
    _GUEST_ID = None
    _DISPATCHER_CONFIG = None

    def _call_api(self, url, video_id, query={}, note='Downloading JSON metadata', init=False):
        url = update_url_query(url, self._common_queries(query, init=init))
        return self._download_json(url, video_id, note=note)['body']

    def _common_queries(self, query={}, init=False):
        dc = self._fetch_dispatcher_config()
        r = {
            'timestamp': self.iso_timestamp(),
            '__guest_id': '' if init else self.guest_id(),
            '__location': dc['location'],
            '__country': dc['country'],
            '__cluster': dc['cluster'],
            '__platform': 'web',
            '__la': 'ja',
            '__pcv': 'v2.9.44',
            'sfr': 'pc',
            'accessToken': '',
        }
        r.update(query)
        return r

    def _fetch_dispatcher_config(self):
        if not self._DISPATCHER_CONFIG:
            tmp = self._download_json(
                'https://disp.mildom.com/serverListV2', 'initialization',
                note='Downloading dispatcher_config', data=json.dumps({
                    'protover': 0,
                    'data': base64.b64encode(json.dumps({
                        'fr': 'web',
                        'sfr': 'pc',
                        'devi': 'Windows',
                        'la': 'ja',
                        'gid': None,
                        'loc': '',
                        'clu': '',
                        'wh': '1919*810',  # don't google this magic number!
                        'rtm': self.iso_timestamp(),
                        'ua': std_headers['User-Agent'],
                    }).encode('utf8')).decode('utf8').replace('\n', ''),
                }).encode('utf8'))
            self._DISPATCHER_CONFIG = self._parse_json(base64.b64decode(tmp['data']), 'initialization')
        return self._DISPATCHER_CONFIG

    @staticmethod
    def iso_timestamp():
        'new Date().toISOString()'
        return datetime.utcnow().isoformat()[0:-3] + 'Z'

    def guest_id(self):
        'getGuestId'
        if not self._GUEST_ID:
            self._GUEST_ID = try_get(
                self, (
                    lambda x: x._call_api(
                        'https://cloudac.mildom.com/nonolive/gappserv/guest/h5init', 'initialization',
                        note='Downloading guest token', init=True)['guest_id'] or None,
                    lambda x: x._get_cookies('https://www.mildom.com').get('gid').value,
                    lambda x: x._get_cookies('https://m.mildom.com').get('gid').value,
                ), compat_str) or ''
        return self._GUEST_ID


class MildomIE(MildomBaseIE):
    IE_NAME = 'mildom'
    IE_DESC = 'Record ongoing live by specific user in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)?mildom\.com/(?P<id>\d+)'

    def _real_extract(self, url):
        user_id = self._match_id(url)
        url = 'https://www.mildom.com/%s' % user_id

        webpage = self._download_webpage(url, user_id)

        enterstudio = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/live/enterstudio', user_id,
            note='Downloading live metadata', query={'user_id': user_id})
        video_id = enterstudio.get('log_id') or user_id

        # e.g. Minecraft
        title = try_get(
            enterstudio, (
                lambda x: self._html_search_meta('twitter:description', webpage),
                lambda x: x['anchor_intro'],
            ), compat_str)
        # e.g. me playing Minecraft
        description = try_get(
            enterstudio, (
                lambda x: x['intro'],
                lambda x: x['live_intro'],
            ), compat_str)
        # e.g. Donald F. McDonald
        uploader = try_get(
            enterstudio, (
                lambda x: self._html_search_meta('twitter:title', webpage),
                lambda x: x['loginname'],
            ), compat_str)

        servers = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/live/liveserver', video_id,
            note='Downloading live server list', query={
                'user_id': user_id,
                'live_server_type': 'hls',
            })

        m3u8_url = servers['stream_server'] + '/%s_master.m3u8' % user_id
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', headers={
            'Referer': 'https://www.mildom.com/',
            'Origin': 'https://www.mildom.com',
        }, note='Downloading m3u8 information')
        for fmt in formats:
            fmt.setdefault('http_headers', {}).update({
                'Referer': 'https://www.mildom.com/',
                'Origin': 'https://www.mildom.com',
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader': uploader,
            'uploader_id': user_id,
            'formats': formats,
            'is_live': True,
        }


class MildomVodIE(MildomBaseIE):
    IE_NAME = 'mildom:vod'
    IE_DESC = 'Download a VOD in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)?mildom\.com/playback/(?P<user_id>\d+)/(?P<id>(?P=user_id)-[a-zA-Z0-9]+)'

    def _real_extract(self, url):
        m = self._valid_url_re().match(url)
        user_id, video_id = m.group('user_id'), m.group('id')
        url = 'https://www.mildom.com/playback/%s/%s' % (user_id, video_id)

        webpage = self._download_webpage(url, video_id)

        autoplay = self._call_api(
            'https://cloudac.mildom.com/nonolive/videocontent/playback/getPlaybackDetail', video_id,
            note='Downloading playback metadata', query={
                'v_id': video_id,
            })['playback']

        # e.g. Minecraft
        title = try_get(
            autoplay, (
                lambda x: self._html_search_meta('og:description', webpage),
                lambda x: x['title'],
            ), compat_str)
        # e.g. me playing Minecraft
        description = try_get(
            autoplay, (
                lambda x: x['video_intro'],
            ), compat_str)
        # e.g. Donald F. McDonald
        uploader = try_get(
            autoplay, (
                lambda x: x['author_info']['login_name'],
            ), compat_str)

        formats = [{
            'url': autoplay['audio_url'],
            'format_id': 'audio',
            'protocol': 'm3u8_native',
            'vcodec': 'none',
            'acodec': 'aac',
        }]
        for fmt in autoplay['video_link']:
            formats.append({
                'format_id': 'video-%s' % fmt['name'],
                'url': fmt['url'],
                'protocol': 'm3u8_native',
                'width': fmt['level'] * autoplay['video_width'] // autoplay['video_height'],
                'height': fmt['level'],
                'vcodec': 'h264',
                'acodec': 'aac',
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader': uploader,
            'uploader_id': user_id,
            'formats': formats,
        }


# User's ongoing live can be done via MildomIE, so this is only for VODs
class MildomUserVodIE(MildomBaseIE):
    IE_NAME = 'mildom:user:vod'
    IE_DESC = 'Download all VODs from specific user in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)?mildom\.com/profile/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.mildom.com/profile/10093333',
        'info_dict': {
            'id': '10093333',
            'title': 'Uploads from ねこばたけ',
        },
        'playlist_mincount': 351,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)

        self._downloader.report_warning('To download ongoing live, please use "https://www.mildom.com/%s" instead. This will list up VODs belonging to user.' % user_id)

        profile = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/user/profileV2', user_id,
            query={'user_id': user_id}, note='Downloading user profile')['user_info']

        results = []
        for page in itertools.count(1):
            reply = self._call_api(
                'https://cloudac.mildom.com/nonolive/videocontent/profile/playbackList',
                user_id, note='Downloading page %d' % page, query={
                    'user_id': user_id,
                    'page': page,
                    'limit': '30',
                })
            if not reply:
                break
            results.extend(
                self.url_result('https://www.mildom.com/playback/%s/%s' % (user_id, x['v_id']), ie=MildomVodIE.ie_key())
                for x in reply)
        return self.playlist_result(results, user_id, 'Uploads from %s' % profile['loginname'])

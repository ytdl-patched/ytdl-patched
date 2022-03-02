# coding: utf-8
from __future__ import unicode_literals

import base64
from datetime import datetime
import itertools
import json

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    std_headers,
    traverse_obj,
    update_url_query,
    random_uuidv4,
    try_get,
    float_or_none,
    dict_get
)
from ..compat import (
    compat_str,
)


class MildomBaseIE(InfoExtractor):
    _GUEST_ID = None
    _DISPATCHER_CONFIG = None

    def _call_api(self, url, video_id, query=None, note='Downloading JSON metadata', init=False):
        query = query or {}
        if query:
            query['__platform'] = 'web'
        url = update_url_query(url, self._common_queries(query, init=init))
        content = self._download_json(url, video_id, note=note)
        if content['code'] == 0:
            return content['body']
        else:
            self.raise_no_formats(
                f'Video not found or premium content. {content["code"]} - {content["message"]}',
                expected=True)

    def _common_queries(self, query={}, init=False):
        dc = self._fetch_dispatcher_config()
        r = {
            'timestamp': self.iso_timestamp(),
            '__guest_id': '' if init else self.guest_id(),
            '__location': dc['location'],
            '__country': dc['country'],
            '__cluster': dc['cluster'],
            '__platform': 'web',
            '__la': self.lang_code(),
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
                        'wh': '1919*810',
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
        if self._GUEST_ID:
            return self._GUEST_ID
        self._GUEST_ID = try_get(
            self, (
                lambda x: x._call_api(
                    'https://cloudac.mildom.com/nonolive/gappserv/guest/h5init', 'initialization',
                    note='Downloading guest token', init=True)['guest_id'] or None,
                lambda x: x._get_cookies('https://www.mildom.com').get('gid').value,
                lambda x: x._get_cookies('https://m.mildom.com').get('gid').value,
            ), compat_str) or ''
        return self._GUEST_ID

    def lang_code(self):
        'getCurrentLangCode'
        return 'ja'


class MildomIE(MildomBaseIE):
    IE_NAME = 'mildom'
    IE_DESC = 'Record ongoing live by specific user in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/(?P<id>\d+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = f'https://www.mildom.com/{video_id}'

        webpage = self._download_webpage(url, video_id)

        enterstudio = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/live/enterstudio', video_id,
            note='Downloading live metadata', query={'user_id': video_id})
        result_video_id = enterstudio.get('log_id', video_id)

        title = try_get(
            enterstudio, (
                lambda x: self._html_search_meta('twitter:description', webpage),
                lambda x: x['anchor_intro'],
            ), compat_str)
        description = traverse_obj(enterstudio, 'intro', 'live_intro', expected_type=compat_str)
        uploader = try_get(
            enterstudio, (
                lambda x: self._html_search_meta('twitter:title', webpage),
                lambda x: x['loginname'],
            ), compat_str)

        servers = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/live/liveserver', result_video_id,
            note='Downloading live server list', query={
                'user_id': video_id,
                'live_server_type': 'hls',
            })

        stream_query = self._common_queries({
            'streamReqId': random_uuidv4(),
            'is_lhls': '0',
        })
        m3u8_url = update_url_query(servers['stream_server'] + f'/{video_id}_master.m3u8', stream_query)
        formats = self._extract_m3u8_formats(m3u8_url, result_video_id, 'mp4', headers={
            'Referer': 'https://www.mildom.com/',
            'Origin': 'https://www.mildom.com',
        })

        del stream_query['streamReqId'], stream_query['timestamp']
        for fmt in formats:
            fmt.setdefault('http_headers', {})['Referer'] = 'https://www.mildom.com/'

        self._sort_formats(formats)

        return {
            'id': result_video_id,
            'title': title,
            'description': description,
            'timestamp': float_or_none(enterstudio.get('live_start_ms'), scale=1000),
            'uploader': uploader,
            'uploader_id': video_id,
            'formats': formats,
            'is_live': True,
        }


class MildomVodIE(MildomBaseIE):
    IE_NAME = 'mildom:vod'
    IE_DESC = 'VOD in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/playback/(?P<user_id>\d+)/(?P<id>(?P=user_id)-[a-zA-Z0-9]+-?[0-9]*)'
    _TESTS = [{
        'url': 'https://www.mildom.com/playback/10882672/10882672-1597662269',
        'info_dict': {
            'id': '10882672-1597662269',
            'ext': 'mp4',
            'title': '始めてのミルダム配信じゃぃ！',
            'thumbnail': r're:^https?://.*\.(png|jpg)$',
            'upload_date': '20200817',
            'duration': 4138.37,
            'description': 'ゲームをしたくて！',
            'timestamp': 1597662269.0,
            'uploader_id': '10882672',
            'uploader': 'kson組長(けいそん)',
        },
    }, {
        'url': 'https://www.mildom.com/playback/10882672/10882672-1597758589870-477',
        'info_dict': {
            'id': '10882672-1597758589870-477',
            'ext': 'mp4',
            'title': '【kson】感染メイズ！麻酔銃で無双する',
            'thumbnail': r're:^https?://.*\.(png|jpg)$',
            'timestamp': 1597759093.0,
            'uploader': 'kson組長(けいそん)',
            'duration': 4302.58,
            'uploader_id': '10882672',
            'description': 'このステージ絶対乗り越えたい',
            'upload_date': '20200818',
        },
    }, {
        'url': 'https://www.mildom.com/playback/10882672/10882672-buha9td2lrn97fk2jme0',
        'info_dict': {
            'id': '10882672-buha9td2lrn97fk2jme0',
            'ext': 'mp4',
            'title': '【kson組長】CART RACER!!!',
            'thumbnail': r're:^https?://.*\.(png|jpg)$',
            'uploader_id': '10882672',
            'uploader': 'kson組長(けいそん)',
            'upload_date': '20201104',
            'timestamp': 1604494797.0,
            'duration': 4657.25,
            'description': 'WTF',
        },
    }]

    def _real_extract(self, url):
        user_id, video_id = self._match_valid_url(url).group('user_id', 'id')
        url = f'https://www.mildom.com/playback/{user_id}/{video_id}'

        webpage = self._download_webpage(url, video_id)

        autoplay = self._call_api(
            'https://cloudac.mildom.com/nonolive/videocontent/playback/getPlaybackDetail', video_id,
            note='Downloading playback metadata', query={
                'v_id': video_id,
            })['playback']

        title = self._html_search_meta(('og:description', 'description'), webpage, fatal=False) or autoplay.get('title')
        description = traverse_obj(autoplay, 'video_intro')
        uploader = traverse_obj(autoplay, ('author_info', 'login_name'))

        formats = [{
            'url': autoplay['audio_url'],
            'format_id': 'audio',
            'protocol': 'm3u8_native',
            'vcodec': 'none',
            'acodec': 'aac',
            'ext': 'm4a'
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
                'ext': 'mp4'
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'timestamp': float_or_none(autoplay.get('publish_time'), scale=1000),
            'duration': float_or_none(autoplay.get('video_length'), scale=1000),
            'thumbnail': dict_get(autoplay, ('upload_pic', 'video_pic')),
            'uploader': uploader,
            'uploader_id': user_id,
            'formats': formats,
        }


class MildomClipIE(MildomBaseIE):
    IE_NAME = 'mildom:clip'
    IE_DESC = 'Clip in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/clip/(?P<id>(?P<user_id>\d+)-[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://www.mildom.com/clip/10042245-63921673e7b147ebb0806d42b5ba5ce9',
        'info_dict': {
            'id': '10042245-63921673e7b147ebb0806d42b5ba5ce9',
            'title': '全然違ったよ',
            'timestamp': 1619181890,
            'duration': 59,
            'thumbnail': r're:https?://.+',
            'uploader': 'ざきんぽ',
            'uploader_id': '10042245',
        },
    }, {
        'url': 'https://www.mildom.com/clip/10111524-ebf4036e5aa8411c99fb3a1ae0902864',
        'info_dict': {
            'id': '10111524-ebf4036e5aa8411c99fb3a1ae0902864',
            'title': 'かっこいい',
            'timestamp': 1621094003,
            'duration': 59,
            'thumbnail': r're:https?://.+',
            'uploader': '(ルーキー',
            'uploader_id': '10111524',
        },
    }, {
        'url': 'https://www.mildom.com/clip/10660174-2c539e6e277c4aaeb4b1fbe8d22cb902',
        'info_dict': {
            'id': '10660174-2c539e6e277c4aaeb4b1fbe8d22cb902',
            'title': 'あ',
            'timestamp': 1614769431,
            'duration': 31,
            'thumbnail': r're:https?://.+',
            'uploader': 'ドルゴルスレンギーン＝ダグワドルジ',
            'uploader_id': '10660174',
        },
    }]

    def _real_extract(self, url):
        user_id, video_id = self._match_valid_url(url).group('user_id', 'id')
        url = f'https://www.mildom.com/clip/{video_id}'

        webpage = self._download_webpage(url, video_id)

        clip_detail = self._call_api(
            'https://cloudac-cf-jp.mildom.com/nonolive/videocontent/clip/detail', video_id,
            note='Downloading playback metadata', query={
                'clip_id': video_id,
            })

        return {
            'id': video_id,
            'title': self._html_search_meta(
                ('og:description', 'description'), webpage, fatal=False) or clip_detail.get('title'),
            'timestamp': float_or_none(clip_detail.get('create_time')),
            'duration': float_or_none(clip_detail.get('length')),
            'thumbnail': clip_detail.get('cover'),
            'uploader': traverse_obj(clip_detail, ('user_info', 'loginname')),
            'uploader_id': user_id,
            'formats': [{
                'url': clip_detail.get('url'),
                'ext': determine_ext(clip_detail.get('url'), 'mp4'),
            }],
        }


class MildomUserVodIE(MildomBaseIE):
    IE_NAME = 'mildom:user:vod'
    IE_DESC = 'Download all VODs from specific user in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/profile/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.mildom.com/profile/10093333',
        'info_dict': {
            'id': '10093333',
            'title': 'Uploads from ねこばたけ',
        },
        'playlist_mincount': 351,
    }, {
        'url': 'https://www.mildom.com/profile/10882672',
        'info_dict': {
            'id': '10882672',
            'title': 'Uploads from kson組長(けいそん)',
        },
        'playlist_mincount': 191,
    }]

    def _entries(self, user_id):
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
            for x in reply:
                yield self.url_result('https://www.mildom.com/playback/%s/%s' % (user_id, x['v_id']))

    def _real_extract(self, url):
        user_id = self._match_id(url)
        self.to_screen('This will download all VODs belonging to user. To download ongoing live video, use "https://www.mildom.com/%s" instead' % user_id)

        profile = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/user/profileV2', user_id,
            query={'user_id': user_id}, note='Downloading user profile')['user_info']

        return self.playlist_result(
            self._entries(user_id), user_id, 'Uploads from %s' % profile['loginname'])

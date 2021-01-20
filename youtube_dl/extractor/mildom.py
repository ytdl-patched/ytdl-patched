# coding: utf-8
from __future__ import unicode_literals

from datetime import datetime
import json
import base64

from .common import InfoExtractor
from ..utils import (
    ExtractorError, std_headers,
    update_url_query,
    random_uuidv4,
    try_get,
)
from ..compat import (
    compat_urlparse,
    compat_urllib_parse_urlencode,
    compat_str,
)


class MildomBaseIE(InfoExtractor):
    _GUEST_ID = None
    _DISPATCHER_CONFIG = None

    def _call_api(self, url, video_id, query={}, note='Downloading JSON metadata', init=False):
        url = update_url_query(url, self._common_queries(query, init=init))
        return self._download_json(url, video_id, note=note)

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
            try:
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
            except ExtractorError:
                self._DISPATCHER_CONFIG = self._download_json(
                    'https://bookish-octo-barnacle.vercel.app/api/dispatcher_config', 'initialization',
                    note='Downloading dispatcher_config fallback')
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
                    note='Downloading guest token', init=True)['body']['guest_id'] or None,
                lambda x: x._get_cookies('https://www.mildom.com').get('gid').value,
                lambda x: x._get_cookies('https://m.mildom.com').get('gid').value,
            ), compat_str) or ''
        return self._GUEST_ID

    def lang_code(self):
        'getCurrentLangCode'
        return 'ja'


class MildomIE(InfoExtractor):
    IE_NAME = 'mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/(?P<id>\d+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = 'https://www.mildom.com/%s' % video_id

        webpage = self._download_webpage(url, video_id)

        enterstudio = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/live/enterstudio', video_id,
            note='Downloading live metadata', query={'user_id': video_id})

        # e.g. Minecraft
        title = try_get(
            enterstudio, (
                lambda x: self._html_search_meta('twitter:description', webpage),
                lambda x: x['body']['anchor_intro'],
            ), compat_str)
        # e.g. recording gameplay for my YouTube
        description = try_get(
            enterstudio, (
                lambda x: x['body']['intro'],
                lambda x: x['body']['live_intro'],
            ), compat_str)
        # e.g. @imagDonaldTrump
        uploader = try_get(
            enterstudio, (
                lambda x: self._html_search_meta('twitter:title', webpage),
                lambda x: x['body']['loginname'],
            ), compat_str)

        servers = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/live/liveserver', video_id,
            note='Downloading live server list', query={
                'user_id': video_id,
                'live_server_type': 'hls',
            })

        stream_query = self._common_queries({
            'streamReqId': random_uuidv4(),
            'is_lhls': '0',
        })
        m3u8_url = update_url_query(servers['body']['stream_server'] + '/%s_master.m3u8' % video_id, stream_query)
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', headers={
            'Referer': 'https://www.mildom.com/',
            'Origin': 'https://www.mildom.com',
        }, note='Downloading m3u8 information')
        del stream_query['streamReqId'], stream_query['timestamp']
        for fmt in formats:
            parsed = compat_urlparse.urlparse(fmt['url'])
            parsed = parsed._replace(
                netloc='bookish-octo-barnacle.vercel.app',
                query=compat_urllib_parse_urlencode(stream_query, True),
                path='/api' + parsed.path)
            fmt['url'] = compat_urlparse.urlunparse(parsed)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader': uploader,
            'uploader_id': video_id,
            'formats': formats,
            'is_live': True,
        }

# VOD: https://cloudac.mildom.com/nonolive/gappserv/live/enterstudio?timestamp=2021-01-20T05:12:57.292Z&__guest_id=pc-gp-64d28d40-5c49-4314-bb15-3743fa57779a&__location=Japan%7CTokyo&__country=&__cluster=aws_japan&__platform=web&__la=ja&sfr=pc&accessToken=&user_id=10317530
# m3u8: https://d3ooprpqd2179o.cloudfront.net/vod/jp/10317530/10317530-c03qultaks9btgbruo10/origin/raw/10317530-c03qultaks9btgbruo10_raw.m3u8?timestamp=2021-01-20T05:32:42.670Z&__guest_id=pc-gp-64d28d40-5c49-4314-bb15-3743fa57779a&__location=Japan|Tokyo&__country=Japan&__cluster=aws_japan&__platform=web&__la=ja&__pcv=v2.9.46&sfr=pc&accessToken=&streamReqId=75eda67c-63e5-4325-8bde-438e306547e2&is_lhls=0

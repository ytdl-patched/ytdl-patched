# coding: utf-8
from __future__ import unicode_literals

from datetime import datetime
import json
import base64

from .common import InfoExtractor
from ..utils import (
    std_headers,
    update_url_query,
    random_uuidv4,
)
from ..compat import (
    compat_urlparse,
    compat_urllib_parse_urlencode,
)


class MildomIE(InfoExtractor):
    IE_NAME = 'mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/(?P<id>\d+)'
    _WORKING = False
    _GUEST_ID = None
    _DISPATCHER_CONFIG = None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = 'https://www.mildom.com/%s' % video_id

        self._download_webpage(url, video_id)
        servers_url = update_url_query('https://cloudac.mildom.com/nonolive/gappserv/live/liveserver', self._common_queries({
            'user_id': video_id,
            'live_server_type': 'hls',
        }))
        servers = self._download_json(servers_url, video_id, note='Downloading live server list')

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
            'title': 'ad hoc title',
            'formats': formats,
            'is_live': True,
        }

    def _common_queries(self, headers={}, init=False):
        r = {
            'timestamp': self.iso_timestamp(),
            '__guest_id': '' if init else self.guest_id(),
            '__location': self.location(),
            '__country': self.country(),
            '__cluster': self.cluster(),
            '__platform': "web",
            '__la': self.lang_code(),
            '__pcv': "v2.9.44",
            'sfr': "pc",
            'accessToken': self.access_token(),
        }
        r.update(headers)
        return r

    def _fetch_dispatcher_config(self):
        if not self._DISPATCHER_CONFIG:
            tmp = self._download_json(
                'https://disp.mildom.com/serverListV2', 'initialization',
                note='Downloading dispatcher_config', data=json.dumps({
                    'protover': 0,
                    'data': base64.b64encode(json.dumps({
                        "fr": "web",
                        "sfr": "pc",
                        "devi": "Windows",
                        "la": "ja",
                        "gid": None,
                        "loc": "",
                        "clu": "",
                        "wh": "1919*810",  # don't google this magic number!
                        "rtm": self.iso_timestamp(),
                        "ua": std_headers['User-Agent'],
                    }).encode('utf8')).decode('utf8').replace('\n', ''),
                }).encode('utf8'))
            self._DISPATCHER_CONFIG = json.loads(base64.b64decode(tmp['data']))
        return self._DISPATCHER_CONFIG

    @staticmethod
    def iso_timestamp():
        "new Date().toISOString()"
        return datetime.utcnow().isoformat()[0:-3] + 'Z'

    def guest_id(self):
        "getGuestId"
        if self._get_cookies('https://www.mildom.com').get('gid'):
            return self._get_cookies('https://www.mildom.com').get('gid').value
        if self._GUEST_ID:
            return self._GUEST_ID
        h5init_url = update_url_query('https://cloudac.mildom.com/nonolive/gappserv/guest/h5init', self._common_queries(init=True))
        self._GUEST_ID = self._download_json(
            h5init_url, 'initialization',
            note='Downloading guest token')['body']['guest_id']
        if self._GUEST_ID:
            return self._GUEST_ID
        else:
            return self.guest_id()

    def location(self):
        "getLocation"
        return self._fetch_dispatcher_config()['location']

    def cluster(self):
        "getCluster"
        return self._fetch_dispatcher_config()['cluster']

    def country(self):
        "getCountry"
        return self._fetch_dispatcher_config()['country']

    def lang_code(self):
        "getCurrentLangCode"
        return 'ja'

    def access_token(self):
        return ''

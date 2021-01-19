# coding: utf-8
from __future__ import unicode_literals

from datetime import datetime
from .common import InfoExtractor
from ..utils import (
    update_url_query,
    random_uuidv4,
)
from ..compat import (
    compat_urlparse,
    compat_urllib_parse_urlencode,
)


# pretty-printed main.js https://gist.githubusercontent.com/nao20010128nao/128d4e7ead01042f90655d4ae81e9f49/raw/cb800c51840ce5ba47a3068c8474e46134e10d69/mildom.js
class MildomIE(InfoExtractor):
    IE_NAME = 'mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/(?P<id>\d+)'
    _WORKING = False
    _GUEST_ID = None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = 'https://www.mildom.com/%s' % video_id

        self._download_webpage(url, video_id)
        servers_url = update_url_query('https://cloudac.mildom.com/nonolive/gappserv/live/liveserver', {
            'timestamp': self.iso_timestamp(),
            '__guest_id': self.guest_id(),
            '__location': self.location(),
            '__country': self.country(),
            '__cluster': self.cluster(),
            '__platform': "web",
            '__la': self.lang_code(),
            '__pcv': "v2.9.44",
            'sfr': "pc",
            'accessToken': self.access_token(),
            'user_id': video_id,
            'live_server_type': 'hls',
        })
        servers = self._download_json(servers_url, video_id, note='Downloading live server list')

        stream_query = {
            'timestamp': self.iso_timestamp(),
            '__guest_id': self.guest_id(),
            '__location': self.location(),
            '__country': self.country(),
            '__cluster': self.cluster(),
            '__platform': "web",
            '__la': self.lang_code(),
            '__pcv': "v2.9.44",
            'sfr': "pc",
            'accessToken': self.access_token(),
            'streamReqId': random_uuidv4(),
            'is_lhls': '0',
        }
        m3u8_url = update_url_query(servers['body']['stream_server'] + '/%s_master.m3u8' % video_id, stream_query)
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', headers={
            'Referer': 'https://www.mildom.com/',
            'Origin': 'https://www.mildom.com',
        }, note='Downloading m3u8 information')
        del stream_query['streamReqId']
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
        }
    # content of getHttpCommonParams for reference:
    # timestamp: new Date().toISOString(),
    # __guest_id: r.a.getGuestId(),
    # __location: r.a.getLocation(),
    # __country: r.a.getCountry(),
    # __cluster: r.a.getCluster(),
    # __platform: "web",
    # __la: u.getCurrentLangCode(),
    # __pcv: "v2.9.44",
    # sfr: "pc",
    # accessToken: r.a.getAccessToken(),

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
        h5init_url = update_url_query('https://cloudac.mildom.com/nonolive/gappserv/guest/h5init', {
            'timestamp': self.iso_timestamp(),
            '__guest_id': '',
            '__location': self.location(),
            '__country': self.country(),
            '__cluster': self.cluster(),
            '__platform': "web",
            '__la': self.lang_code(),
            '__pcv': "v2.9.44",
            'sfr': "pc",
            'accessToken': self.access_token(),
        })
        self._GUEST_ID = self._download_json(
            h5init_url, 'initialization',
            note='Downloading guest token')['body']['guest_id']
        if self._GUEST_ID:
            return self._GUEST_ID
        else:
            return self.guest_id()

    def location(self):
        "getLocation"
        # requires LocalStorage or current IP address. returning constant for now
        return 'Japan|Tokyo'

    def cluster(self):
        "getCluster"
        # requires LocalStorage. returning constant for now
        return 'aws_japan'

    def country(self):
        "getCountry"
        # requires LocalStorage or current IP address. returning constant for now
        return 'Japan'

    def lang_code(self):
        "getCurrentLangCode"
        # requires LocalStorage or user preference(?). returning constant for now
        return 'ja'

    def access_token(self):
        "getCurrentLangCode"
        # requires LocalStorage. returning constant for now
        return ''

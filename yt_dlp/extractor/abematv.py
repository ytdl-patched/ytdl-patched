# https://docs.python.org/ja/3/library/urllib.request.html
# https://github.com/python/cpython/blob/f4c03484da59049eb62a9bf7777b963e2267d187/Lib/urllib/request.py#L510
# https://gist.github.com/zhenyi2697/5252805
# https://github.com/streamlink/streamlink/blob/master/src/streamlink/plugins/abematv.py#L39

import io
import json
import time
import hashlib
import hmac
import struct
from base64 import urlsafe_b64encode
from binascii import unhexlify

from .common import InfoExtractor
from ..aes import aes_ecb_decrypt
from ..compat import compat_urllib_response, compat_urllib_parse_urlparse
from ..utils import (
    ExtractorError,
    random_uuidv4,
    request_to_url,
    update_url_query,
    traverse_obj,
    YoutubeDLExtractorHandler,
    intlist_to_bytes,
    bytes_to_intlist,
)


class AbemaLicenseHandler(YoutubeDLExtractorHandler):
    STRTABLE = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    HKEY = b'3AF0298C219469522A313570E8583005A642E73EDD58E3EA2FB7339D3DF1597E'
    _MEDIATOKEN_API = 'https://api.abema.io/v1/media/token'
    _LICENSE_API = 'https://license.abema.io/abematv-hls'

    def __init__(self, ie: 'AbemaTVIE'):
        # the protcol that this should really handle is 'abematv-license://'
        # abematv_license_open is just a placeholder for development purposes
        # ref. https://github.com/python/cpython/blob/f4c03484da59049eb62a9bf7777b963e2267d187/Lib/urllib/request.py#L510
        setattr(self, 'abematv-license_open', getattr(self, 'abematv_license_open'))
        self.ie = ie

    def _get_videokey_from_ticket(self, ticket):
        media_token_response = self.ie._download_json(
            self._MEDIATOKEN_API, None, note='Fetching media token',
            query={
                "osName": "android",
                "osVersion": "6.0.1",
                "osLang": "ja_JP",
                "osTimezone": "Asia/Tokyo",
                "appId": "tv.abema",
                "appVersion": "3.27.1"
            },
            headers={"Authorization": "Bearer " + self.ie._USERTOKEN})

        license_response = self.ie._download_json(
            self._LICENSE_API, None, note='Requesting playback license',
            query={"t": media_token_response['token']},
            data=json.dumps({
                "kv": "a",
                "lt": ticket
            }).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
            })
        cid = license_response['cid']
        k = license_response['k']

        res = sum([self.STRTABLE.find(k[i]) * (58 ** (len(k) - 1 - i))
                  for i in range(len(k))])
        encvideokey = bytes_to_intlist(struct.pack('>QQ', res >> 64, res & 0xffffffffffffffff))

        # HKEY:
        # RC4KEY = unhexlify('DB98A8E7CECA3424D975280F90BD03EE')
        # RC4DATA = unhexlify(b'D4B718BBBA9CFB7D0192A58F9E2D146A'
        #                     b'FC5DB29E4352DE05FC4CF2C1005804BB')
        # rc4 = ARC4.new(RC4KEY)
        # HKEY = rc4.decrypt(RC4DATA)
        h = hmac.new(
            unhexlify(self.HKEY),
            (cid + self.ie._DEVICE_ID).encode("utf-8"),
            digestmod=hashlib.sha256)
        enckey = bytes_to_intlist(h.digest())

        return intlist_to_bytes(aes_ecb_decrypt(encvideokey, enckey))

    def abematv_license_open(self, url):
        url = request_to_url(url)
        ticket = compat_urllib_parse_urlparse(url).netloc
        response_data = self._get_videokey_from_ticket(ticket)
        return compat_urllib_response.addinfourl(io.BytesIO(response_data), headers={
            'Content-Length': len(response_data),
        }, url=url, code=200)


class AbemaTVIE(InfoExtractor):
    _VALID_URL = r'https?://abema\.tv/(?P<type>now-on-air|video/episode|channels/.+?/slots)/(?P<id>[^?]+)'
    _USERTOKEN = None
    _DEVICE_ID = None

    SECRETKEY = (b'v+Gjs=25Aw5erR!J8ZuvRrCx*rGswhB&qdHd_SYerEWdU&a?3DzN9B'
                 b'Rbp5KwY4hEmcj5#fykMjJ=AuWz5GSMY-d@H7DMEh3M@9n2G552Us$$'
                 b'k9cD=3TxwWe86!x#Zyhe')

    def _generate_aks(self, deviceid):
        deviceid = deviceid.encode('utf-8')
        # plus 1 hour and drop minute and secs
        # for python3 : floor division
        ts_1hour = (int(time.time()) + 60 * 60) // 3600 * 3600
        time_struct = time.gmtime(ts_1hour)
        ts_1hour_str = str(ts_1hour).encode('utf-8')

        h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
        h.update(self.SECRETKEY)
        tmp = h.digest()
        for i in range(time_struct.tm_mon):
            h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
            h.update(tmp)
            tmp = h.digest()
        h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
        h.update(urlsafe_b64encode(tmp).rstrip(b'=') + deviceid)
        tmp = h.digest()
        for i in range(time_struct.tm_mday % 5):
            h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
            h.update(tmp)
            tmp = h.digest()

        h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
        h.update(urlsafe_b64encode(tmp).rstrip(b'=') + ts_1hour_str)
        tmp = h.digest()

        for i in range(time_struct.tm_hour % 5):  # utc hour
            h = hmac.new(self.SECRETKEY, digestmod=hashlib.sha256)
            h.update(tmp)
            tmp = h.digest()

        return urlsafe_b64encode(tmp).rstrip(b'=').decode('utf-8')

    def _is_playable(self, vtype, vid):
        if vtype == 'episode':
            api_response = self._download_json(
                f'https://api.abema.io/v1/video/programs/{vid}', vid,
                headers={
                    'Authorization': 'Bearer ' + self._USERTOKEN
                })
            ondemand_types = traverse_obj(api_response, ('terms', ..., 'onDemandType'), default=[])
            return 3 in ondemand_types
        elif vtype == 'slots':
            api_response = self._download_json(
                f'https://api.abema.io/v1/media/slots/{vid}', vid,
                headers={
                    'Authorization': 'Bearer ' + self._USERTOKEN
                })
            return traverse_obj(api_response, ('slot', 'flags', 'timeshiftFree'), default=False)

    def _get_device_token(self):
        if self._USERTOKEN:
            return

        self._DEVICE_ID = random_uuidv4()
        aks = self._generate_aks(self._DEVICE_ID)
        user_data = self._download_json(
            'https://api.abema.io/v1/users', None, note='Authorizing',
            data=json.dumps({
                'deviceId': self._DEVICE_ID,
                'applicationKeySecret': aks,
            }).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
            })
        self._USERTOKEN = user_data['token']

        self._downloader.remove_opener(AbemaLicenseHandler)
        self._downloader.add_opener(AbemaLicenseHandler(self))

    def _real_extract(self, url):
        # starting download using infojson from this extractor is undefined behavior,
        # and never be fixed in the future; you must trigger downloads by directly specifing URL.
        # (unless there's a way to hook before downloading by extractor)
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        self._get_device_token()

        video_type = video_type.split('/')[-1]
        is_live, m3u8_url = False, None
        if video_type == 'now-on-air':
            is_live = True
            channel_url = 'https://api.abema.io/v1/channels'
            if video_id == 'news-global':
                channel_url = update_url_query(channel_url, {'division': '1'})
            onair_channels = self._download_json(channel_url, video_id)
            for ch in onair_channels['channels']:
                if video_id == ch['id']:
                    m3u8_url = ch['playback']['hls']
                    break
            else:
                raise ExtractorError(f'Cannot find on-air {video_id} channel.', expected=True)
        elif video_type == 'episode':
            if not self._is_playable('episode', video_id):
                # ignore --allow-unplayable-formats, fuck it
                raise ExtractorError("Premium stream can't be played.", expected=True)
            m3u8_url = f'https://vod-abematv.akamaized.net/program/{video_id}/playlist.m3u8'
        elif video_type == 'slots':
            if not self._is_playable('slots', video_id):
                # ignore --allow-unplayable-formats, fuck it
                raise ExtractorError("Premium stream can't be played.", expected=True)
            m3u8_url = f'https://vod-abematv.akamaized.net/slot/{video_id}/playlist.m3u8'
        else:
            raise ExtractorError('Unreachable')

        if is_live:
            self.report_warning("This is a livestream; yt-dlp doesn't support downloading natively, but FFmpeg cannot handle m3u8 manifests from AbemaTV")
            self.report_warning('Please consider using Streamlink to download these streams (https://github.com/streamlink/streamlink)')
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, ext='mp4', live=is_live)

        return {
            'id': video_id,
            'title': 'hello',
            'formats': formats,
            'is_live': is_live,
        }

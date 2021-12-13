from __future__ import division, unicode_literals

import json
import threading
import time

from .common import FileDownloader
from ..downloader import get_suitable_downloader
from ..extractor.niconico import NiconicoIE
from .external import FFmpegFD
from ..utils import (
    str_or_none,
    std_headers,
    to_str,
    DownloadError,
    try_get,
)
from ..compat import compat_str
from ..websocket import (
    WebSocket,
    HAVE_WEBSOCKET,
)


class NiconicoDmcFD(FileDownloader):
    """
    Performs niconico DMC request and download the video \n
    Note that this FD very differs from upstream one
    """

    def real_download(self, filename, info_dict):
        nie: NiconicoIE = self.ydl.get_info_extractor(NiconicoIE.ie_key())

        video_id = info_dict['video_id']
        session_api_data = info_dict['session_api_data']

        session_response = nie._download_json(
            info_dict['url'], video_id,
            query={'_format': 'json'},
            headers={'Content-Type': 'application/json'},
            note='Downloading JSON metadata for %s' % info_dict['format_id'],
            data=json.dumps(info_dict['dmc_data']).encode())

        # get heartbeat info
        heartbeat_url = f"{session_api_data['urls'][0]['url']}/{session_response['data']['session']['id']}?_format=json&_method=PUT"
        heartbeat_data = json.dumps(session_response['data']).encode()
        # interval, convert milliseconds to seconds, then halve to make a buffer.
        heartbeat_interval = session_api_data['heartbeatLifetime'] / 8000

        new_info_dict = info_dict.copy()
        new_info_dict.update({
            'url': session_response['data']['session']['content_uri'],
            'protocol': info_dict['expected_protocol'],
            'heartbeat_url': heartbeat_url,
            'heartbeat_data': heartbeat_data,
            'heartbeat_interval': heartbeat_interval,
        })

        if info_dict['extract_m3u8']:
            try:
                m3u8_format = nie._extract_m3u8_formats(
                    new_info_dict['url'], video_id, ext='mp4', entry_protocol='m3u8_native', note=False)[0]
            except BaseException:
                new_info_dict['protocol'] = 'm3u8'
            else:
                del m3u8_format['format_id'], m3u8_format['protocol']
                new_info_dict.update(m3u8_format)

        return get_suitable_downloader(new_info_dict, params=self.params)(self.ydl, self.params).download(filename, new_info_dict)


class NiconicoLiveFD(FileDownloader):
    """ Downloads niconico live without being stopped """

    def real_download(self, filename, info_dict):
        if not HAVE_WEBSOCKET:  # this is unreachable because this is checked at Extractor
            raise DownloadError('Install websockets or websocket_client package via pip, or install websockat program')

        video_id = info_dict['video_id']
        ws_url = info_dict['url']
        cookies = info_dict.get('cookies')
        live_quality = info_dict.get('live_quality', 'high')
        live_latency = info_dict.get('live_latency', 'high')
        dl = FFmpegFD(self.ydl, self.params or {})
        self.to_screen('[%s] %s: Fetching HLS playlist info via WebSocket' % ('niconico:live', video_id))

        new_info_dict = info_dict.copy()
        new_info_dict.update({
            'url': None,
            'protocol': 'live_ffmpeg',
        })
        lock = threading.Lock()
        lock.acquire()

        def communicate_ws(reconnect):
            with WebSocket(ws_url, {
                'Cookie': str_or_none(cookies) or '',
                'Origin': 'https://live2.nicovideo.jp',
                'Accept': '*/*',
                'User-Agent': std_headers['User-Agent'],
            }) as ws:
                if self.ydl.params.get('verbose', False):
                    self.to_screen('[debug] Sending HLS server request')
                ws.send(json.dumps({
                    "type": "startWatching",
                    "data": {
                        "stream": {
                            "quality": live_quality,
                            "protocol": "hls+fmp4",
                            "latency": live_latency,
                            "chasePlay": False
                        },
                        "room": {
                            "protocol": "webSocket",
                            "commentable": True
                        },
                        "reconnect": reconnect,
                    }
                }))

                while True:
                    recv = to_str(ws.recv()).strip()
                    if not recv:
                        continue
                    data = json.loads(recv)
                    if not data or not isinstance(data, dict):
                        continue
                    if data.get('type') == 'stream' and not new_info_dict.get('url'):
                        new_info_dict['url'] = data['data']['uri']
                        lock.release()
                    elif data.get('type') == 'ping':
                        # pong back
                        ws.send(r'{"type":"pong"}')
                        ws.send(r'{"type":"keepSeat"}')
                    elif data.get('type') == 'disconnect':
                        print(data)
                        return True
                    elif data.get('type') == 'error':
                        print(data)
                        message = try_get(data, lambda x: x["body"]["code"], compat_str) or recv
                        return DownloadError(message)
                    elif self.ydl.params.get('verbose', False):
                        if len(recv) > 100:
                            recv = recv[:100] + '...'
                        self.to_screen('[debug] Server said: %s' % recv)

        def ws_main():
            reconnect = False
            while True:
                try:
                    ret = communicate_ws(reconnect)
                    if ret is True:
                        return
                    if isinstance(ret, BaseException):
                        new_info_dict['error'] = ret
                        lock.release()
                        return
                except BaseException as e:
                    self.to_screen('[%s] %s: Connection error occured, reconnecting after 10 seconds: %s' % ('niconico:live', video_id, str_or_none(e)))
                    time.sleep(10)
                    continue
                finally:
                    reconnect = True

        thread = threading.Thread(target=ws_main, daemon=True)
        thread.start()

        lock.acquire(True)
        err = new_info_dict.get('error')
        if isinstance(err, BaseException):
            raise err
        return dl.download(filename, new_info_dict)

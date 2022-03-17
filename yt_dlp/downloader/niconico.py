from __future__ import division, unicode_literals

import json
import threading
import time

from .common import FileDownloader
from ..downloader import get_suitable_downloader
from ..extractor.niconico import NiconicoIE
from .external import FFmpegFD
from ..utils import (
    sanitized_Request,
    str_or_none,
    std_headers,
    DownloadError,
    try_get,
)
from ..compat import compat_str
from ..websocket import (
    WebSocket,
    HAVE_WEBSOCKET,
)


class NiconicoDmcFD(FileDownloader):
    """ Downloading niconico douga from DMC with heartbeat """

    FD_NAME = 'niconico_dmc'

    def real_download(self, filename, info_dict):
        self.to_screen('[%s] Downloading from DMC' % self.FD_NAME)

        ie: NiconicoIE = self.ydl.get_info_extractor(NiconicoIE.ie_key())
        info_dict, heartbeat_info_dict = ie._get_heartbeat_info(info_dict)

        fd = get_suitable_downloader(info_dict, params=self.params)(self.ydl, self.params)

        success = download_complete = False
        timer = [None]
        heartbeat_lock = threading.Lock()
        heartbeat_url = heartbeat_info_dict['url']
        heartbeat_data = heartbeat_info_dict['data'].encode()
        heartbeat_interval = heartbeat_info_dict.get('interval', 30)

        request = sanitized_Request(heartbeat_url, heartbeat_data)

        def heartbeat():
            try:
                self.ydl.urlopen(request).read()
            except Exception:
                self.to_screen('[%s] Heartbeat failed' % self.FD_NAME)

            with heartbeat_lock:
                if not download_complete:
                    timer[0] = threading.Timer(heartbeat_interval, heartbeat)
                    timer[0].start()

        heartbeat_info_dict['ping']()
        self.to_screen('[%s] Heartbeat with %d second interval ...' % (self.FD_NAME, heartbeat_interval))
        try:
            heartbeat()
            success = fd.real_download(filename, info_dict)
        finally:
            if heartbeat_lock:
                with heartbeat_lock:
                    timer[0].cancel()
                    download_complete = True
            return success


class NiconicoLiveFD(FileDownloader):
    """ Downloads niconico live without being stopped """

    def real_download(self, filename, info_dict):
        if not HAVE_WEBSOCKET:  # this is unreachable because this is checked at Extractor
            raise DownloadError('Install websockets or websocket_client package via pip, or install websockat program')

        video_id = info_dict['video_id']
        ws_url = info_dict['url']
        ws_extractor = info_dict['ws']
        cookies = info_dict.get('cookies')
        live_quality = info_dict.get('live_quality', 'high')
        live_latency = info_dict.get('live_latency', 'high')
        dl = FFmpegFD(self.ydl, self.params or {})

        new_info_dict = info_dict.copy()
        new_info_dict.update({
            'protocol': 'live_ffmpeg',
        })

        def communicate_ws(reconnect):
            if reconnect:
                ws = WebSocket(ws_url, {
                    'Cookie': str_or_none(cookies) or '',
                    'Origin': 'https://live2.nicovideo.jp',
                    'Accept': '*/*',
                    'User-Agent': std_headers['User-Agent'],
                })
                if self.ydl.params.get('verbose', False):
                    self.to_screen('[debug] Sending startWatching request')
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
                        "reconnect": True,
                    }
                }))
            else:
                ws = ws_extractor
            with ws:
                while True:
                    recv = ws.recv()
                    if not recv:
                        continue
                    data = json.loads(recv)
                    if not data or not isinstance(data, dict):
                        continue
                    if data.get('type') == 'ping':
                        # pong back
                        ws.send(r'{"type":"pong"}')
                        ws.send(r'{"type":"keepSeat"}')
                    elif data.get('type') == 'disconnect':
                        self.write_debug(data)
                        return True
                    elif data.get('type') == 'error':
                        self.write_debug(data)
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
                except BaseException as e:
                    self.to_screen('[%s] %s: Connection error occured, reconnecting after 10 seconds: %s' % ('niconico:live', video_id, str_or_none(e)))
                    time.sleep(10)
                    continue
                finally:
                    reconnect = True

        thread = threading.Thread(target=ws_main, daemon=True)
        thread.start()

        return dl.download(filename, new_info_dict)

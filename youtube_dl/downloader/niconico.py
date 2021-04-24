from __future__ import division, unicode_literals

import json
import threading
import time

from .external import FFmpegFD
from .common import FileDownloader
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


class NiconicoLiveFD(FileDownloader):
    """ Downloads niconico live without being stopped """

    def real_download(self, filename, info_dict):
        if not HAVE_WEBSOCKET:  # this is unreachable because this is checked at Extractor
            raise DownloadError('Install websockets or websocket_client package via pip, or install websockat program')

        video_id = info_dict['video_id']
        ws_url = info_dict['url']
        cookies = info_dict.get('cookies')
        dl = FFmpegFD(self.ydl, self.params or {})
        self.to_screen('[%s] %s: Fetching HLS playlist info via WebSocket' % ('niconico:live', video_id))

        new_info_dict = {}
        new_info_dict.update(info_dict)
        new_info_dict.update({
            'url': None,
            'protocol': 'ffmpeg',
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
                            "quality": "high",
                            "protocol": "hls",
                            "latency": "high",
                            "chasePlay": False
                        },
                        "room": {
                            "protocol": "webSocket",
                            "commentable": True
                        },
                        "reconnect": reconnect
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

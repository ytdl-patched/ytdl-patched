from __future__ import division, unicode_literals

import json
import threading

from .external import FFmpegFD
from .common import FileDownloader
from ..utils import (
    str_or_none,
    std_headers,
    to_str,
    DownloadError,
)
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

        def communicate_ws():
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
                        "reconnect": False
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
                        break
                    elif self.ydl.params.get('verbose', False):
                        if len(recv) > 100:
                            recv = recv[:100] + '...'
                        self.to_screen('[debug] Server said: %s' % recv)

        thread = threading.Thread(target=communicate_ws, daemon=True)
        thread.start()

        lock.acquire(True)
        return dl.download(filename, new_info_dict)

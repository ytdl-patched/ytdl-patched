from __future__ import division, unicode_literals

import threading

from .common import FileDownloader
from .external import FFmpegFD


class FC2LiveFD(FileDownloader):
    """ Downloads FC2 live without being stopped """

    def real_download(self, filename, info_dict):
        ws = info_dict['ws']
        dl = FFmpegFD(self.ydl, self.params or {})

        heartbeat_lock = threading.Lock()
        heartbeat_state = [None, 1]

        def heartbeat():
            try:
                heartbeat_state[1] += 1
                ws.send('{"name":"heartbeat","arguments":{},"id":%d}' % heartbeat_state[1])
            except Exception:
                self.to_screen('[fc2:live] Heartbeat failed')

            with heartbeat_lock:
                heartbeat_state[0] = threading.Timer(30, heartbeat)
                heartbeat_state[0]._daemonic = True
                heartbeat_state[0].start()

        heartbeat()

        new_info_dict = info_dict.copy()
        new_info_dict.update({
            'ws': None,
            'protocol': 'live_ffmpeg',
        })
        return dl.download(filename, new_info_dict)
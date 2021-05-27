from __future__ import division, unicode_literals

import threading
import os
import signal

from .common import FileDownloader
from .external import FFmpegFD
from ..compat import compat_str
from ..websocket import WebSocket


class LiveStreamSinkBaseFD(FileDownloader):
    """ Just a sink to ffmpeg for downloading fragments """

    FD_NAME = 'youtube_live_chat_replay'

    def real_download(self, filename, info_dict):
        new_infodict = {}
        new_infodict.update(info_dict)
        new_infodict['url'] = '-'

        def call_conn(proc, stdin):
            try:
                self.real_connection(stdin, info_dict)
            finally:
                stdin.flush()
                stdin.close()
                os.kill(os.getpid(), signal.SIGINT)

        class FFmpegStdinFD(FFmpegFD):
            def on_process_started(self, proc, stdin):
                thread = threading.Thread(target=call_conn, daemon=True, args=(proc, stdin))
                thread.start()

        return FFmpegStdinFD(self.ydl, self.params or {}).download(filename, new_infodict)

    def real_connection(self, sink, info_dict):
        """
        Override this in subclasses.
        Blocking operations are allowed.
        Just return the function if the stream have finished.
        """


class WebSocketFragmentFD(LiveStreamSinkBaseFD):
    def real_connection(self, sink, info_dict):
        with WebSocket(info_dict['url'], info_dict.get('http_headers', {})) as ws:
            while True:
                recv = ws.recv()
                if isinstance(recv, compat_str):
                    recv = recv.encode('utf8')
                sink.write(recv)

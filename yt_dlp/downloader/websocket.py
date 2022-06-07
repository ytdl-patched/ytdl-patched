import contextlib
import os
import signal
import threading

from .common import FileDownloader
from .external import FFmpegFD
from ..compat import asyncio
from ..dependencies import websockets


class AsyncSinkFD(FileDownloader):
    async def connect(self, stdin, info_dict):
        try:
            await self.real_connection(stdin, info_dict)
        except OSError:
            pass
        finally:
            with contextlib.suppress(OSError):
                stdin.flush()
                stdin.close()
            os.kill(os.getpid(), signal.SIGINT)

    async def real_connection(self, sink, info_dict):
        """ Override this in subclasses """
        raise NotImplementedError('This method must be implemented by subclasses')


class FFmpegSinkFD(AsyncSinkFD):
    """ A sink to ffmpeg for downloading fragments in any form """

    def real_download(self, filename, info_dict):
        info_copy = info_dict.copy()
        info_copy['url'] = '-'
        connect = self.connect

        class FFmpegStdinFD(FFmpegFD):
            @classmethod
            def get_basename(cls):
                return FFmpegFD.get_basename()

            def on_process_started(self, proc, stdin):
                thread = threading.Thread(target=asyncio.run, daemon=True, args=(connect(stdin, info_dict), ))
                thread.start()

        return FFmpegStdinFD(self.ydl, self.params or {}).download(filename, info_copy)


class FileSinkFD(AsyncSinkFD):
    """ A sink to a file for downloading fragments in any form """
    def real_download(self, filename, info_dict):
        tempname = self.temp_name(filename)
        try:
            with open(tempname, 'wb') as w:
                asyncio.run(self.connect(w, info_dict))
        finally:
            self.ydl.replace(tempname, filename)
        return True


class WebSocketFragmentFD(FFmpegSinkFD):
    async def real_connection(self, sink, info_dict):
        async with websockets.connect(info_dict['url'], extra_headers=info_dict.get('http_headers', {})) as ws:
            while True:
                recv = await ws.recv()
                if isinstance(recv, str):
                    recv = recv.encode('utf8')
                sink.write(recv)

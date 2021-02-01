from __future__ import unicode_literals

import asyncio
import websockets


class WebSocketsWrapper():
    "Wraps websockets module to use in non-async scopes"

    def __init__(self, url, headers=None) -> None:
        self.impl = websockets.connect(url, extra_headers=headers)

    def send(self, *args):
        async def _send():
            await self.impl.send(*args)
        asyncio.run(_send)

    def recv(self, *args):
        async def _recv():
            await self.impl.recv(*args)
        asyncio.run(_recv)

    def close(self):
        async def _close():
            await self.impl.close()
        asyncio.run(_close)

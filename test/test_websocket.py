#!/usr/bin/env python

from __future__ import unicode_literals, with_statement

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_dl.websocket import (
    HAVE_WEBSOCKET,
    HAVE_WS_WEBSOCKET_CLIENT,
    HAVE_WS_WEBSOCKETS,
    HAVE_WS_WEBSOCAT,

    WebSocketClientWrapper,
    WebSocketsWrapper,
    WebsocatWrapper,
)

import logging
logger = logging.getLogger('websockets')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


@unittest.skipUnless(HAVE_WEBSOCKET, 'websocket not available')
class TestWebSocket(unittest.TestCase):
    @staticmethod
    def __kraken(impl):
        with impl('wss://ws.kraken.com/') as ws:
            ws.send('{"event":"subscribe", "subscription":{"name":"trade"}, "pair":["XBT/USD","XRP/USD"]}')
            for _ in range(5):
                print(ws.recv())

    @staticmethod
    def __echo(impl, url):
        with impl(url) as ws:
            for i in range(5):
                text = 'Hello World %d' % i
                ws.send(text)
                recv = ws.recv()
                print(recv, type(recv))
                assert text == recv

    @unittest.skipUnless(HAVE_WS_WEBSOCKET_CLIENT, 'websocket_client not installed')
    def test_websocket_client_echo(self):
        self.__echo(WebSocketClientWrapper, 'ws://echo.websocket.org')
        self.__echo(WebSocketClientWrapper, 'wss://echo.websocket.org')

    @unittest.skipUnless(HAVE_WS_WEBSOCKETS, 'websockets not installed')
    def test_websockets_echo(self):
        self.__echo(WebSocketsWrapper, 'ws://echo.websocket.org')
        self.__echo(WebSocketsWrapper, 'wss://echo.websocket.org')

    @unittest.skipUnless(HAVE_WS_WEBSOCAT, 'websocat not installed')
    def test_websocat_echo(self):
        self.__echo(WebsocatWrapper, 'ws://echo.websocket.org')
        self.__echo(WebsocatWrapper, 'wss://echo.websocket.org')

    @unittest.skipUnless(HAVE_WS_WEBSOCKET_CLIENT, 'websocket_client not installed')
    def test_websocket_client_kraken(self):
        self.__kraken(WebSocketClientWrapper)

    @unittest.skipUnless(HAVE_WS_WEBSOCKETS, 'websockets not installed')
    def test_websockets_kraken(self):
        self.__kraken(WebSocketsWrapper)

    @unittest.skipUnless(HAVE_WS_WEBSOCAT, 'websocat not installed')
    def test_websocat_kraken(self):
        self.__kraken(WebsocatWrapper)


if __name__ == '__main__':
    unittest.main()

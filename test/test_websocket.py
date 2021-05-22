#!/usr/bin/env python

from __future__ import unicode_literals, with_statement

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.websocket import (
    HAVE_WEBSOCKET,
    HAVE_WS_WEBSOCKET_CLIENT,
    HAVE_WS_WEBSOCKETS,
    HAVE_WS_WEBSOCAT,
    HAVE_WS_NODEJS_WEBSOCKET_WRAPPER,
    HAVE_WS_NODEJS_WS_WRAPPER,

    WebSocketClientWrapper,
    WebSocketsWrapper,
    WebsocatWrapper,
    NodeJsWebsocketWrapper,
    NodeJsWsWrapper,
)

import logging
logger = logging.getLogger('websockets')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


@unittest.skipUnless(HAVE_WEBSOCKET, 'websocket not available')
class TestWebSocket(unittest.TestCase):

    @staticmethod
    def _kraken(impl):
        with impl('wss://ws.kraken.com/') as ws:
            ws.send('{"event":"subscribe", "subscription":{"name":"trade"}, "pair":["XBT/USD","XRP/USD"]}')
            for _ in range(5):
                print(ws.recv())

    @staticmethod
    def _echo(impl, url):
        with impl(url) as ws:
            for i in range(5):
                text = 'Hello World %d' % i
                ws.send(text)
                recv = ws.recv()
                print(recv, type(recv))
                assert text == recv


for testsuite in ('kraken', 'echo'):
    for available, impl, name in (
        (HAVE_WS_WEBSOCKET_CLIENT, WebSocketClientWrapper, 'websocket_client'),
        (HAVE_WS_WEBSOCKETS, WebSocketsWrapper, 'websockets'),
        (HAVE_WS_WEBSOCAT, WebsocatWrapper, 'websocat'),
        (HAVE_WS_NODEJS_WEBSOCKET_WRAPPER, NodeJsWebsocketWrapper, 'nodejs_websocket'),
        (HAVE_WS_NODEJS_WS_WRAPPER, NodeJsWsWrapper, 'nodejs_ws'),
    ):

        def create_function(testsuite, impl, available, name):
            @unittest.skipUnless(available, '%s not installed' % name)
            def _runtest(self):
                if testsuite == 'kraken':
                    self._kraken(impl)
                elif testsuite == 'echo':
                    self._echo(impl, 'ws://echo.websocket.org')
                    self._echo(impl, 'wss://echo.websocket.org')

            return _runtest

        setattr(TestWebSocket, '_'.join(['test', name, testsuite]), create_function(testsuite, impl, available, name))

if __name__ == '__main__':
    unittest.main()

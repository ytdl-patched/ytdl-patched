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
    @unittest.skipUnless(HAVE_WS_WEBSOCKET_CLIENT, 'websocket_client not installed')
    def test_websocket_client(self):
        with WebSocketClientWrapper('wss://ws.kraken.com/') as ws:
            ws.send('{"event":"subscribe", "subscription":{"name":"trade"}, "pair":["XBT/USD","XRP/USD"]}')
            for _ in range(5):
                print(ws.recv())

    @unittest.skipUnless(HAVE_WS_WEBSOCKETS, 'websockets not installed')
    def test_websockets(self):
        with WebSocketsWrapper('wss://ws.kraken.com/') as ws:
            ws.send('{"event":"subscribe", "subscription":{"name":"trade"}, "pair":["XBT/USD","XRP/USD"]}')
            for _ in range(5):
                print(ws.recv())

    @unittest.skipUnless(HAVE_WS_WEBSOCAT, 'websocat not installed')
    def test_websocat(self):
        with WebsocatWrapper('wss://ws.kraken.com/') as ws:
            ws.send('{"event":"subscribe", "subscription":{"name":"trade"}, "pair":["XBT/USD","XRP/USD"]}')
            for _ in range(5):
                print(ws.recv())


if __name__ == '__main__':
    unittest.main()

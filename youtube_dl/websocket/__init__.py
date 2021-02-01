from __future__ import unicode_literals

HAVE_WEBSOCKET = False
WebSocket = None

# WebSocket: (URI, header={'Accept': 'nothing', 'X-Magic-Number': '42'})->WebSocket
# only send, recv, close are guaranteed to exist

try:
    from websocket import create_connection, WebSocket

    def _enter(self):
        return self

    def _exit(self, type, value, traceback):
        self.close()

    WebSocket.__enter__ = _enter
    WebSocket.__exit__ = _exit

    def WebSocket(url, headers={}):
        r = create_connection(url, headers=['%s: %s' % kv for kv in headers.items()])
        return r

    HAVE_WEBSOCKET = True
except (ImportError, ValueError, SyntaxError):
    try:
        from .websockets import WebSocketsWrapper as WebSocket
        HAVE_WEBSOCKET = True
    except (ImportError, ValueError, SyntaxError):
        try:
            from .websocat import WebsocatWrapper, AVAILABLE

            if AVAILABLE:
                WebSocket = WebsocatWrapper
                HAVE_WEBSOCKET = True
        except (ImportError, ValueError, SyntaxError):
            pass

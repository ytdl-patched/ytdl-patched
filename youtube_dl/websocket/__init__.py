from __future__ import unicode_literals

HAVE_WEBSOCKET = False
WebSocket = None

# WebSocket: (URI, header={'Accept': 'nothing', 'X-Magic-Number': '42'})->WebSocket
# only send, recv, close are guaranteed to exist

try:
    from .websockets import WebSocketsWrapper as WebSocket
    HAVE_WEBSOCKET = True
except (ImportError, ValueError):
    try:
        from websocket import create_connection

        def WebSocket(url, headers={}):
            return create_connection(url, headers=['%s: %s' % kv for kv in headers.items()])

        HAVE_WEBSOCKET = True
    except (ImportError, ValueError):
        try:
            from .websocat import WebsocatWrapper, AVAILABLE

            if AVAILABLE:
                WebSocket = WebsocatWrapper
                HAVE_WEBSOCKET = True
        except (ImportError, ValueError):
            pass

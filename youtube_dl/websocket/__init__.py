from __future__ import unicode_literals

HAVE_WEBSOCKET = False
WebSocket = None

# WebSocket: (URI, header={'Accept': 'nothing', 'X-Magic-Number': '42'})->WebSocket
# only send, recv, close are guaranteed to exist

HAVE_WS_WEBSOCKET_CLIENT, HAVE_WS_WEBSOCKETS, HAVE_WS_WEBSOCAT, HAVE_WS_NODEJS_WS_WRAPPER, HAVE_WS_NODEJS_WEBSOCKET_WRAPPER = (False, ) * 5

try:
    from websocket import create_connection, WebSocket

    def _enter(self):
        return self

    def _exit(self, type, value, traceback):
        self.close()

    WebSocket.__enter__ = _enter
    WebSocket.__exit__ = _exit

    def WebSocketClientWrapper(url, headers={}):
        return create_connection(url, headers=['%s: %s' % kv for kv in headers.items()])

    HAVE_WS_WEBSOCKET_CLIENT = True
    HAVE_WEBSOCKET = True
except (ImportError, ValueError, SyntaxError):
    WebSocketClientWrapper = None

try:
    from .websockets import WebSocketsWrapper
    HAVE_WS_WEBSOCKETS = True
    HAVE_WEBSOCKET = True
except (ImportError, ValueError, SyntaxError):
    WebSocketsWrapper = None

try:
    from .websocat import AVAILABLE

    if AVAILABLE:
        from .websocat import WebsocatWrapper
        HAVE_WS_WEBSOCAT = True
        HAVE_WEBSOCKET = True
    else:
        WebsocatWrapper = None
except (ImportError, ValueError, SyntaxError):
    WebsocatWrapper = None

try:
    from .nodejs import NPM_IS_SANE

    if NPM_IS_SANE:
        from .nodejs import HAVE_NODEJS_WEBSOCKET_WRAPPER, HAVE_NODEJS_WS_WRAPPER

        if HAVE_NODEJS_WEBSOCKET_WRAPPER:
            from .nodejs import NodeJsWebsocketWrapper
            HAVE_WS_NODEJS_WEBSOCKET_WRAPPER = True
            HAVE_WEBSOCKET = True
        else:
            NodeJsWebsocketWrapper = None

        if HAVE_NODEJS_WS_WRAPPER:
            from .nodejs import NodeJsWsWrapper
            HAVE_WS_NODEJS_WS_WRAPPER = True
            HAVE_WEBSOCKET = True
        else:
            NodeJsWsWrapper = None
    else:
        NodeJsWebsocketWrapper, NodeJsWsWrapper = None, None
except (ImportError, ValueError, SyntaxError):
    NodeJsWebsocketWrapper, NodeJsWsWrapper = None, None

WebSocket = WebSocketClientWrapper or WebSocketsWrapper or WebsocatWrapper or NodeJsWebsocketWrapper or NodeJsWsWrapper

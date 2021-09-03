import base64
import json
import os
import sys
from typing import List
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.utils import (
    sanitized_Request,
    update_Request,
    urljoin,
)
from yt_dlp.compat import (
    compat_urllib_request,
)
from yt_dlp.rpc.job import (
    JSONRPC_ID_KEY,
    REQTYPE_APPEND_ARGS,
    REQTYPE_ARGUMENTS,
    REQTYPE_CLEAR_ARGS,
    REQTYPE_GET_ARGS,
    REQTYPE_RESET_ARGS
)


class RpcClientBase():
    def get_server_version(self):
        pass

    def queue_arguments(self, arguments: List[str], rpc_id: JSONRPC_ID_KEY = None):
        pass

    def queue_append_persistent_arg(self, arguments: List[str]):
        pass

    def queue_reset_args(self):
        pass

    def queue_clear_args(self):
        pass

    def queue_get_args(self, rpc_id: JSONRPC_ID_KEY):
        pass

    def poll_responses(self):
        pass

    def shutdown(self):
        pass


class HttpRpcClient(RpcClientBase):
    def __init__(self, url: str, username: str, password: str) -> None:
        super().__init__()
        self.url = url
        if username and password:
            self.auth = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode()
        else:
            self.auth = None

    def _send_request(self, ep, data):
        request = sanitized_Request(urljoin(self.url, ep), data=data)
        if self.auth:
            request = update_Request(request, headers={
                'Authorization': f'Basic {self.auth}'
            })
        response = json.load(compat_urllib_request.urlopen(request))
        return response

    def get_server_version(self):
        return self._send_request('/version', None)

    def queue_arguments(self, arguments: List[str], rpc_id: JSONRPC_ID_KEY = None):
        return self._send_request('/enqueue', json.dumps({
            'id': rpc_id,
            'data': {
                'key': REQTYPE_ARGUMENTS,
                'args': {'args': arguments, }
            }
        }).encode())

    def queue_append_persistent_arg(self, arguments: List[str]):
        return self._send_request('/enqueue', json.dumps({
            'id': None,
            'data': {
                'key': REQTYPE_APPEND_ARGS,
                'args': {'args': arguments, }
            }
        }).encode())

    def queue_reset_args(self):
        return self._send_request('/enqueue', json.dumps({
            'id': None,
            'data': {
                'key': REQTYPE_RESET_ARGS,
                'args': {}
            }
        }).encode())

    def queue_clear_args(self):
        return self._send_request('/enqueue', json.dumps({
            'id': None,
            'data': {
                'key': REQTYPE_CLEAR_ARGS,
                'args': {}
            }
        }).encode())

    def queue_get_args(self, rpc_id: JSONRPC_ID_KEY):
        return self._send_request('/enqueue', json.dumps({
            'id': rpc_id,
            'data': {
                'key': REQTYPE_GET_ARGS,
                'args': {}
            }
        }).encode())

    def poll_responses(self):
        # server don't care POST body
        return self._send_request('/response', b'heloooo').encode()

    def shutdown(self):
        # server don't care POST body
        return self._send_request('/shutdown', b'byeeeeee').encode()


def run_loop(listen_address, username, password):
    pass

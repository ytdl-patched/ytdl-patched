import json
import os
import sys
from typing import List
from yt_dlp.rpc.job import JSONRPC_ID_KEY

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.utils import (
    sanitized_Request,
    urljoin,
)
from yt_dlp.compat import (
    compat_urllib_request,
)


class RpcClientBase():
    def get_server_version(self):
        pass


class HttpRpcClient(RpcClientBase):
    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url

    def _send_request(self, ep, data):
        request = sanitized_Request(urljoin(self.url, ep), data=data)
        response = json.load(compat_urllib_request.urlopen(request))
        return response

    def get_server_version(self):
        return self._send_request('/version', None)

    def queue_arguments(self, arguments: List[str], rpc_id: JSONRPC_ID_KEY = None):
        request = sanitized_Request(urljoin(self.url, '/enqueue'))
        response = json.load(compat_urllib_request.urlopen(request))
        return response

    def queue_append_persistent_arg(self, arguments: List[str]):
        request = sanitized_Request(urljoin(self.url, '/enqueue'))
        response = json.load(compat_urllib_request.urlopen(request))
        return response

    def queue_reset_args(self, arguments: List[str]):
        request = sanitized_Request(urljoin(self.url, '/enqueue'))
        response = json.load(compat_urllib_request.urlopen(request))
        return response

    def queue_clear_args(self, arguments: List[str]):
        request = sanitized_Request(urljoin(self.url, '/enqueue'))
        response = json.load(compat_urllib_request.urlopen(request))
        return response

    def queue_get_args(self, arguments: List[str], rpc_id: JSONRPC_ID_KEY):
        request = sanitized_Request(urljoin(self.url, '/enqueue'))
        response = json.load(compat_urllib_request.urlopen(request))
        return response

    def poll_responses(self):
        request = sanitized_Request(urljoin(self.url, '/responses'))
        response = json.load(compat_urllib_request.urlopen(request))
        return response

    def shutdown(self):
        request = sanitized_Request(urljoin(self.url, '/shutdown'))
        response = json.load(compat_urllib_request.urlopen(request))
        return response


def run_loop(listen_address, username, password):
    pass

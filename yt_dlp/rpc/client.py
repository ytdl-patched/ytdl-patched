import base64
import json
import random
import shlex
import sys
from typing import List, Optional

from .job import (
    JSONRPC_ID_KEY,
    REQTYPE_APPEND_ARGS,
    REQTYPE_ARGUMENTS,
    REQTYPE_CLEAR_ARGS,
    REQTYPE_GET_ARGS,
    REQTYPE_RESET_ARGS
)
from ..utils import (
    sanitized_Request,
    update_Request,
    urljoin,
)
from ..compat import (
    compat_urllib_request,
)
from ..version import __version__


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

        # test if auth works (/version has no side-effect on server state)
        self._send_request('/version', b'versiooooooooooon')

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


def show_help(client: RpcClientBase, args: List[str], rpc_id: JSONRPC_ID_KEY):
    print('!help - Show help (this message)')
    print('!getargs - Get persistent arguments')
    print('!appendargs - Append persistent arguments')
    print('!resetargs - Reset persistent arguments')
    print('!clearargs - Clear persistent arguments')
    print('!response - Get received response. Responses are only shown once')
    print('If command starts with none of the above, it will be treated as one-shot arguments (such as URLs, options)')
    print('If you want to distinguish requests, you should append RPC_ID=<blablabla> before arguments')


def cmd_get_args(client: RpcClientBase, args: List[str], rpc_id: JSONRPC_ID_KEY):
    key = ''.join(random.choices('abcdef0123456789', k=5)) if rpc_id is None else rpc_id
    client.queue_get_args(key)
    print(f'Enqueued getArgs with ID {key}')


def cmd_append_args(client: RpcClientBase, args: List[str], rpc_id: JSONRPC_ID_KEY):
    client.queue_append_persistent_arg(args)
    print('Enqueued appendArgs')


def cmd_reset_args(client: RpcClientBase, args: List[str], rpc_id: JSONRPC_ID_KEY):
    client.queue_reset_args(args)
    print('Enqueued resetArgs')


def cmd_clear_args(client: RpcClientBase, args: List[str], rpc_id: JSONRPC_ID_KEY):
    client.queue_clear_args(args)
    print('Enqueued clearArgs')


def cmd_response(client: RpcClientBase, args: List[str], rpc_id: JSONRPC_ID_KEY):
    client.poll_responses()
    print('Enqueued clearArgs')


def cmd_shutdown(client: RpcClientBase, args: List[str], rpc_id: JSONRPC_ID_KEY):
    client.shutdown()
    print('Goodbye.')
    try:
        cmd = input('Do you want to continue? [y/N] ').strip().lower()
    except EOFError:
        cmd = 'n'
    if cmd != 'y':
        sys.exit(0)


_COMMANDS = {
    '!help': show_help,
    '!getargs': cmd_get_args,
    '!appendargs': cmd_append_args,
    '!resetargs': cmd_reset_args,
    '!clearargs': cmd_clear_args,
    '!response': cmd_response,
    '!shutdown': cmd_shutdown,
}


def run_loop(server_addr: str, username: Optional[str], password: Optional[str]):
    if server_addr.startswith('https://') or server_addr.startswith('http://'):
        client = HttpRpcClient(server_addr, username, password)
    else:
        raise NotImplementedError(f'Address {server_addr} not supported')

    print(f'ytdl-patched {__version__} RPC Client')
    remote_version = client.get_server_version()
    print(f'Connected to {server_addr}')
    print(f'Server: {remote_version["brand"]} {remote_version["version"]}')
    while True:
        try:
            cmd = input('>>> ')
        except EOFError:
            break
        args = shlex.split(cmd, posix=True)
        if not args:
            # nothing is input
            continue

        rpc_id: JSONRPC_ID_KEY = None
        if args[0].startswith('RPC_ID='):
            rpc_id = args[0][7:]
            args = args[1:]
        func = _COMMANDS.get(args[0])
        if func:
            func(client, args[1:], rpc_id)
        else:
            client.queue_arguments(args, rpc_id)
            print('Enqueued:', repr(args))


def run_unattended(server_addr: str, username: Optional[str], password: Optional[str], args: List[str], key: JSONRPC_ID_KEY):
    pass

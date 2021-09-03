import json
import base64

from queue import Empty, Queue
from typing import Dict, List, Optional
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Lock, Thread
from .job import JSONRPC_ID_KEY, AppendArgsJob, ArgumentsJob, ClearArgsJob, GetArgsJob, JobBase, ResetArgsJob, create_job_from_json
from .. import _read_ytdl_opts
from ..utils import ExistingVideoReached, MaxDownloadsReached, RejectedVideoReached
from ..compat import compat_urllib_parse_urlparse
from ..version import __version__
from ..YoutubeDL import YoutubeDL

_TAIL_OF_QUEUE = object()


class RpcServerBase():

    def start_server(self, job_queue: Queue[JobBase]):
        pass

    def respond(self, response_id: JSONRPC_ID_KEY, data):
        pass

    def stop_server(self):
        pass


class HttpRpcServer(RpcServerBase):

    def __init__(self, listen: str, users: Dict[str, str] = None) -> None:
        self.listen = listen
        self.users = users
        self.responses = []
        self.response_lock = Lock()
        self.server: Optional[HTTPServer] = None

    def start_server(self, job_queue: Queue[JobBase]):
        hrs = self

        class Handler(BaseHTTPRequestHandler):
            def __init__(self, *args):
                BaseHTTPRequestHandler.__init__(self, *args)

            def do_GET(self):
                parsed_path = compat_urllib_parse_urlparse(self.path)
                if parsed_path.path == '/version':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'brand': 'ytdl-patched',
                        'version': __version__,
                    }).encode('utf-8'))
                else:
                    # respond with 418 I'm a teapot
                    self.send_response(418)
                    self.end_headers()
                return

            def handle_auth(self):
                if not hrs.users:
                    # pass auth since no account is set
                    return True
                auth_header = self.headers.get('Authorization')
                if not auth_header:
                    return False
                auth_header = str(auth_header)
                if not auth_header.startswith('Basic '):
                    return False
                req_u, req_p = base64.b64decode(auth_header[6:].strip()).decode('utf-8').split(':')
                okay = False
                for user, pwd in hrs.users.items():
                    if user == req_u and pwd == req_p:
                        okay = True
                return okay

            def do_POST(self):
                if not self.handle_auth():
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b'{"error":"Authentication failed."}')
                    return

                parsed_path = compat_urllib_parse_urlparse(self.path)
                if parsed_path.path == '/enqueue':
                    if self.headers.get('Content-Type') != 'application/json':
                        self.send_response(403)
                        self.end_headers()
                        self.wfile.write(b'{"error":"You must upload JSON for POST payload."}')
                        return
                    post_data = json.load(self.rfile)
                    job = create_job_from_json(post_data)
                    job_queue.put(job)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'{"response":"Enqueued"}')
                elif parsed_path.path == '/shutdown':
                    job_queue.put(_TAIL_OF_QUEUE)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'{"response":"Goodbye"}')
                    hrs.stop_server()
                elif parsed_path.path == '/responses':
                    with hrs.response_lock:
                        response_data = json.dumps({'response': hrs.responses})
                        hrs.responses.clear()
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(response_data.encode('utf-8'))
                else:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b'{"error":"Unknown endpoint"}')

        try:
            from http.server import ThreadingHTTPServer
            server = ThreadingHTTPServer((), Handler)
        except ImportError:
            server = HTTPServer((), Handler)
        self.server = server
        self.queue = job_queue
        Thread(target=lambda: server.serve_forever(), daemon=True).start()

    def respond(self, response_id: JSONRPC_ID_KEY, data):
        if response_id is None:
            # this does not check for key reuse; key management is responsible for clients
            return
        with self.response_lock:
            self.responses.append({
                'id': response_id,
                'response': data,
            })

    def stop_server(self):
        if self.server:
            self.server.shutdown()
            queue = getattr(self, 'queue', None)
            if isinstance(queue, Queue):
                queue.put(_TAIL_OF_QUEUE)
            try:
                delattr(self, 'queue')
            except AttributeError:
                pass
        self.server = None


def _queue_to_iter(q: Queue[JobBase]):
    while True:
        try:
            ent = q.get(True, 1)
        except Empty:
            pass
        if ent is _TAIL_OF_QUEUE:
            break
        yield ent


def run_server(init_args: List[str], server: RpcServerBase):
    init_args = list(init_args)
    curr_opts = init_args
    queue = Queue()
    try:
        server.start_server(queue)
        for job in _queue_to_iter(queue):
            if isinstance(job, ArgumentsJob):
                ydl_opts, all_urls, opts, _ = _read_ytdl_opts(curr_opts + job.args)
                with YoutubeDL(ydl_opts) as ydl:
                    err = None
                    try:
                        if opts.load_info_filename is not None:
                            ydl.report_warning('--load-info-json is disabled because of security concerns, returning it as failure.')
                            retcode = 120
                        else:
                            retcode = ydl.download(all_urls)
                    except (MaxDownloadsReached, ExistingVideoReached, RejectedVideoReached):
                        ydl.to_screen('Aborting remaining downloads')
                        retcode = 101
                    except BaseException as ex:
                        ydl.to_screen('An error occurred')
                        retcode = 109
                        err = '%s' % ex
                    server.respond(job.job_id, {'retcode': retcode, 'err': err})
            elif isinstance(job, AppendArgsJob):
                curr_opts = curr_opts + job.args
            elif isinstance(job, ResetArgsJob):
                curr_opts = init_args
            elif isinstance(job, ClearArgsJob):
                curr_opts = []
            elif isinstance(job, GetArgsJob):
                server.respond(job.job_id, list(curr_opts))
    finally:
        server.stop_server()

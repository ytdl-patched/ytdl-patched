from queue import Empty, Queue
from typing import List
from .job import JSONRPC_ID_KEY, AppendArgsJob, ArgumentsJob, ClearArgsJob, GetArgsJob, JobBase, ResetArgsJob
from .. import _read_ytdl_opts
from ..utils import ExistingVideoReached, MaxDownloadsReached, RejectedVideoReached
from ..YoutubeDL import YoutubeDL

_TAIL_OF_QUEUE = object()


class RpcServerBase():

    def start_server(self, job_queue: Queue[JobBase]):
        pass

    def respond(self, response_id: JSONRPC_ID_KEY, data):
        pass

    def stop_server(self):
        pass


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
                        retcode = 101
                        err = '%s' % ex
                    server.respond(job.job_id, {'retcode': retcode, 'err': err})
            elif isinstance(job, AppendArgsJob):
                curr_opts = curr_opts + job.args
            elif isinstance(job, ResetArgsJob):
                curr_opts = init_args
            elif isinstance(job, ClearArgsJob):
                curr_opts = []
            elif isinstance(job, GetArgsJob):
                server.respond(job.job_id, init_args)
    finally:
        server.stop_server()

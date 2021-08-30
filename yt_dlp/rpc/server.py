from queue import Empty, Queue
from .job import JobBase


_TAIL_OF_QUEUE = object()


class RpcServerBase():

    def start_server(self, job_queue: Queue[JobBase]):
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


def run_server(server: RpcServerBase):
    queue = Queue()
    try:
        server.start_server(queue)
        for job in _queue_to_iter(queue):
            pass
    finally:
        server.stop_server()

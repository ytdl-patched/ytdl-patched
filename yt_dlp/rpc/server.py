from queue import Queue
from .job import JobBase


class RpcServerBase():

    def start_server(self, job_queue: Queue[JobBase]):
        pass

    def stop_server(self):
        pass


def run_server(server: RpcServerBase):
    pass

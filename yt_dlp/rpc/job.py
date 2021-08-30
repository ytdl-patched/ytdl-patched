from typing import List


class JobBase():
    pass


class ArgumentsJob(JobBase):
    """
    Oneshot arguments job.
    """
    def __init__(self, args: List[str]) -> None:
        self.args: List[str] = args


class AppendArgsJob(JobBase):
    """
    Persistent arguments job.
    """
    def __init__(self, args: List[str]) -> None:
        self.args: List[str] = args


class ResetArgsJob(JobBase):
    """
    Reset persistent arguments to when the server is started.
    """


class ClearArgsJob(JobBase):
    """
    Clear persistent arguments to zero length, meaning no options will be set.
    """

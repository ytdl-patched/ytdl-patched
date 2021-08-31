from typing import Dict, List, Type, Union


JSONRPC_ID_KEY = Union[float, int, str, None]


class JobBase():
    job_id: Union[float, int, str, None]


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


class GetArgsJob(JobBase):
    """
    Responds with current presistent argument value as of the job is handled.
    """


_REQTYPE_TO_CLASS: Dict[str, Type[JobBase]] = {
    'arguments': ArgumentsJob,
    'appendArgs': AppendArgsJob,
    'resetArgs': ResetArgsJob,
    'clearArgs': ClearArgsJob,
    'getArgs': GetArgsJob,
}


def create_job_from_json(obj):
    job_id = obj.get('id')
    content = obj.get('data')
    if not isinstance(content, dict):
        return None
    reqtype = content.get('type')
    args = content.get('args') or {}
    job = _REQTYPE_TO_CLASS[reqtype](**args)
    job.job_id = job_id
    return job

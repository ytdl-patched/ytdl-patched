from typing import Dict, List, Type, Union


JSONRPC_ID_KEY = Union[float, int, str, None]


class JobBase:
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


REQTYPE_ARGUMENTS = 'arguments'
REQTYPE_APPEND_ARGS = 'appendArgs'
REQTYPE_RESET_ARGS = 'resetArgs'
REQTYPE_CLEAR_ARGS = 'clearArgs'
REQTYPE_GET_ARGS = 'getArgs'


_REQTYPE_TO_CLASS: Dict[str, Type[JobBase]] = {
    REQTYPE_ARGUMENTS: ArgumentsJob,
    REQTYPE_APPEND_ARGS: AppendArgsJob,
    REQTYPE_RESET_ARGS: ResetArgsJob,
    REQTYPE_CLEAR_ARGS: ClearArgsJob,
    REQTYPE_GET_ARGS: GetArgsJob,
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

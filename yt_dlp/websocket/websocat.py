from __future__ import unicode_literals

from ..utils import check_executable
from ..compat import compat_str
from subprocess import Popen, PIPE


class WebsocatWrapper():
    "Wraps websocat command to use in non-async scopes"

    def __init__(self, url, headers={}):
        self.proc = Popen(
            ['websocat', '-t', *('-H=%s: %s' % kv for kv in headers.items()), url],
            stdout=PIPE, stdin=PIPE, stderr=PIPE)

    def __read_stderr(func):
        def cback(self, *args):
            try:
                return func(self, *args)
            except BaseException as ex:
                e = Exception()
                if self.proc:
                    e.msg = self.proc.stderr.read()
                e.cause = ex
                raise e
        return cback

    @__read_stderr
    def send(self, data):
        if isinstance(data, compat_str):
            data = data.encode('utf-8')
        self.proc.stdin.write(data)
        self.proc.stdin.write(b'\n')
        self.proc.stdin.flush()

    @__read_stderr
    def recv(self):
        while True:
            ret = self.proc.stdout.readline()
            if isinstance(ret, bytes):
                ret = ret.decode('utf-8')
            ret = ret.strip()
            if ret:
                return ret

    @__read_stderr
    def close(self):
        self.proc.kill()
        self.proc.terminate()
        self.proc = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


AVAILABLE = bool(check_executable('websocat', ['-h']))

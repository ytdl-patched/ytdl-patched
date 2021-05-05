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

    def send(self, data):
        if isinstance(data, compat_str):
            data = data.encode('utf-8')
        self.proc.stdin.write(data)
        self.proc.stdin.write(b'\n')
        self.proc.stdin.flush()

    def recv(self):
        ret = self.proc.stdout.readline()
        if isinstance(ret, bytes):
            ret = ret.decode('utf-8')
        return ret.strip()

    def close(self):
        self.proc.kill()
        self.proc.terminate()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


AVAILABLE = bool(check_executable('websocat', ['-h']))

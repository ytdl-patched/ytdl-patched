from __future__ import unicode_literals

from ..utils import check_executable
from subprocess import Popen, PIPE


class WebsocatWrapper():
    "Wraps websocat module to use in non-async scopes"

    def __init__(self, url, headers={}) -> None:
        self.proc = Popen(
            'websocat', '-t', *['-H=%s: %s' % kv for kv in headers.items()], url,
            stdout=PIPE, stdin=PIPE, stderr=PIPE, encoding='utf8', text=True)
        self.buffers = []

    def send(self, data):
        out, err = self.proc.communicate(data)
        out, err = out.strip(), err.strip()
        if err:
            raise IOError('websocat says: %s' % err)
        self.buffers.extend(out.splitlines())

    def recv(self):
        if (self.buffers):
            ret, bf = self.buffers[-1], self.buffers[:-1]
            self.buffers = bf
            return ret
        out, err = self.proc.communicate()
        out, err = out.strip(), err.strip()
        if err:
            raise IOError('websocat says: %s' % err)
        if out:
            out = out.splitlines()
            ret, bf = out[-1], out[:-1]
            self.buffers.append(bf)
            return ret
        else:
            return False

    def close(self):
        self.proc.kill()


AVAILABLE = bool(check_executable('websockat', ['-h']))

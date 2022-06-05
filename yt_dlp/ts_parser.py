import functools
import itertools

from typing import Union
from io import RawIOBase
from threading import Lock


# writer is fast
class PipedIO(RawIOBase):
    def __init__(self) -> None:
        super().__init__()
        # assumption: self.offset < len(self.buffers[0])
        self.buffers = []
        self.offset = 0
        self._lock = Lock()

    def lock(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            with self._lock:
                if self.buffers is None:
                    raise OSError('This pipe has already been closed')
                return func(self, *args, **kwargs)
        return wrapper

    @lock
    def close(self) -> None:
        self.buffers[:] = []
        self.buffers = None

    @lock
    def read(self, size: int = None) -> bytes:
        if not self.buffers:
            return b''
        if size in (None, -1):
            # read all from buffers
            buf = b''.join(itertools.chain([self.buffers[0][self.offset:]], self.buffers[1:]))
            # evict all of the buffer queue
            self.buffers = []
            self.offset = 0
            return buf

        buf = b''
        while self.buffers and len(buf) < size:
            current_piece = self.buffers[0]
            piece_len = len(current_piece)
            max_read = min(size - len(buf), piece_len - self.offset)
            # advance the cursor by it can read at most
            buf += current_piece[self.offset:self.offset + max_read]
            self.offset += max_read
            # evict the piece if it reached to the end
            if self.offset == piece_len:
                self.buffers = self.buffers[1:]
                self.offset = 0

        return buf

    # locking here will deadlock
    def readall(self) -> bytes:
        return self.read()

    @lock
    def write(self, b: Union[bytes, bytearray]) -> int:
        if not isinstance(b, bytes):
            b = bytes(b)
        self.buffers.append(b)
        return len(b)


class TSStreamParser():
    pass

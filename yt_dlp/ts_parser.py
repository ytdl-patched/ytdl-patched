import functools
import itertools
import struct

from typing import Union
from io import BytesIO, RawIOBase
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


class LengthLimiter(RawIOBase):
    def __init__(self, r: RawIOBase, size: int):
        super().__init__()
        self.r = r
        self.remaining = size

    def read(self, sz: int = None) -> bytes:
        if sz in (-1, None):
            sz = self.remaining
        sz = min(sz, self.remaining)
        ret = self.r.read(sz)
        if ret:
            self.remaining -= len(ret)
        return ret

    def readall(self) -> bytes:
        ret = self.read(self.remaining)
        if ret:
            self.remaining -= len(ret)
        return ret

    def readable(self) -> bool:
        return bool(self.remaining)


def read_harder(r, size):
    retry = 0
    buf = b''
    while len(buf) < size and retry < 3:
        ret = r.read(size - len(buf))
        if not ret:
            retry += 1
            continue
        retry = 0
        buf += ret

    return buf


def pack_be32(value: int) -> bytes:
    return struct.pack('>I', value)


class MP4StreamParser():
    # https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/box.js#L13-L40
    _CONTAINER_BOXES = ('moov', 'trak', 'edts', 'mdia', 'minf', 'dinf', 'stbl', 'mvex', 'moof', 'traf', 'vttc', 'tref', 'iref', 'mfra', 'meco', 'hnti', 'hinf', 'strk', 'strd', 'sinf', 'rinf', 'schi', 'trgr', 'udta', 'iprp', 'ipco')

    def parse_boxes(self, r: RawIOBase):
        while True:
            size_b = read_harder(r, 4)
            if not size_b:
                break
            type_b = r.read(4)
            # 00 00 00 20 is big-endian
            box_size = struct.unpack('>I', size_b)[0]
            type_s = type_b.decode()
            if type_s in self._CONTAINER_BOXES:
                immbox = self.parse_boxes(LengthLimiter(r, box_size - 8))
                yield (type_s, b'')
                yield from immbox
                yield (None, type_s)
                continue
            # subtract by 8
            full_body = read_harder(r, box_size - 8)
            yield (type_s, full_body)

    def write_boxes(self, w: RawIOBase, box_iter):
        stack = [
            (None, w),  # parent box, IO
        ]
        for btype, content in box_iter:
            if btype in self._CONTAINER_BOXES:
                bio = BytesIO()
                stack.append((btype, bio))
                continue
            elif btype is None:
                assert stack[-1][0] == content
                btype, bio = stack.pop()
                content = bio.getvalue()

            wt = stack[-1][1]
            wt.write(pack_be32(len(content) + 8))
            wt.write(btype.encode()[:4])
            wt.write(content)

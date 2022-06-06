import struct
import os
import sys

from io import BytesIO, RawIOBase


if sys.platform in ('linux', 'darwin', 'aix', 'aix5', 'aix7'):
    def set_nonblocking(fd):
        os.set_blocking(fd, False)
elif sys.platform in ('win32', 'cygwin'):
    # https://stackoverflow.com/questions/34504970/non-blocking-read-on-os-pipe-on-windows
    import msvcrt
    from ctypes import windll, byref, WinError
    from ctypes.wintypes import HANDLE, DWORD, POINTER, BOOL

    LPDWORD = POINTER(DWORD)
    PIPE_NOWAIT = DWORD(0x00000001)

    SetNamedPipeHandleState = windll.kernel32.SetNamedPipeHandleState
    SetNamedPipeHandleState.argtypes = [HANDLE, LPDWORD, LPDWORD, LPDWORD]
    SetNamedPipeHandleState.restype = BOOL

    def set_nonblocking(fd):
        """ pipefd is a integer as returned by os.pipe """

        h = msvcrt.get_osfhandle(fd)

        res = SetNamedPipeHandleState(h, byref(PIPE_NOWAIT), None, None)
        if res == 0:
            raise WinError()
else:
    def set_nonblocking(fd):
        pass


# system's pipe
class PipedIO(RawIOBase):
    def __init__(self):
        r, w = os.pipe()
        set_nonblocking(r)
        set_nonblocking(w)
        self._r = open(r, 'rb', 0)
        self._w = open(w, 'wb', 0)
        self.read = self._r.read
        self.readinto = self._r.readinto
        self.write = self._w.write
        self.flush = self._w.flush

    def close(self):
        self._r.close()
        try:
            # to close BufferedWriter part, not the pipe itself
            self._w.close()
        except BaseException:
            pass


class LengthLimiter(RawIOBase):
    def __init__(self, r: RawIOBase, size: int):
        super().__init__()
        self.r = r
        self.remaining = size

    def read(self, sz: int = None) -> bytes:
        if self.remaining == 0:
            return b''
        if sz in (-1, None):
            sz = self.remaining
        sz = min(sz, self.remaining)
        ret = self.r.read(sz)
        if ret:
            self.remaining -= len(ret)
        return ret

    def readall(self) -> bytes:
        if self.remaining == 0:
            return b''
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


# https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/box.js#L13-L40
MP4_CONTAINER_BOXES = ('moov', 'trak', 'edts', 'mdia', 'minf', 'dinf', 'stbl', 'mvex', 'moof', 'traf', 'vttc', 'tref', 'iref', 'mfra', 'meco', 'hnti', 'hinf', 'strk', 'strd', 'sinf', 'rinf', 'schi', 'trgr', 'udta', 'iprp', 'ipco')


def parse_mp4_boxes(r: RawIOBase):
    while True:
        size_b = read_harder(r, 4)
        if not size_b:
            break
        type_b = r.read(4)
        # 00 00 00 20 is big-endian
        box_size = struct.unpack('>I', size_b)[0]
        type_s = type_b.decode()
        if type_s in MP4_CONTAINER_BOXES:
            immbox = parse_mp4_boxes(LengthLimiter(r, box_size - 8))
            yield (type_s, b'')
            yield from immbox
            yield (None, type_s)
            continue
        # subtract by 8
        full_body = read_harder(r, box_size - 8)
        yield (type_s, full_body)


def write_mp4_boxes(w: RawIOBase, box_iter):
    stack = [
        (None, w),  # parent box, IO
    ]
    for btype, content in box_iter:
        if btype in MP4_CONTAINER_BOXES:
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

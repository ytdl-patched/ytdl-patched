#!/usr/bin/env python

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import functools

from yt_dlp.ts_parser import (
    PipedIO,
)


class TestPipedIO(unittest.TestCase):
    pass


def _test_readwrite_length(impl, self):
    with impl() as pipe:
        iteration = 123
        length = iteration * (iteration - 1) // 2
        for i in range(iteration):
            pipe.write(bytes([i] * i))
        self.assertEqual(len(pipe.read()), length)


def _test_readwrite_content(impl, self):
    with impl() as pipe:
        iteration = 123
        expected = b''
        for i in range(iteration):
            data = bytes([i] * i)
            pipe.write(data)
            expected += data
        self.assertEqual(pipe.read(), expected)


def _test_close(impl, self):
    pipe = impl()
    pipe.write(b'some random data')
    pipe.close()

    try:
        pipe.write(b'this is not written')
        raise AssertionError('The pipe has not closed properly')
    except (OSError, ValueError):
        # okay
        pass


pipes = (PipedIO, )
funcs = (_test_readwrite_length, _test_readwrite_content, _test_close)


def _test_fn(func, clz):
    @functools.wraps(func)
    def g(self):
        func(clz, self)

    return g


for pp in pipes:
    for fn in funcs:
        setattr(TestPipedIO, f'{fn.__name__[1:]}_{pp.__name__}', _test_fn(fn, pp))

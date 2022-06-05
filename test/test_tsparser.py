#!/usr/bin/env python

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.ts_parser import (
    PipedIO,
)


class TestPipedIO(unittest.TestCase):
    def test_readwrite_length(self):
        pipe = PipedIO()
        iteration = 123
        length = iteration * (iteration - 1) // 2
        for i in range(iteration):
            pipe.write(bytes([i] * i))
        self.assertEqual(len(pipe.read()), length)

    def test_readwrite_content(self):
        pipe = PipedIO()
        iteration = 123
        expected = b''
        for i in range(iteration):
            data = bytes([i] * i)
            pipe.write(data)
            expected += data
        self.assertEqual(pipe.read(), expected)

    def test_close(self):
        pipe = PipedIO()
        pipe.write(b'some random data')
        pipe.close()

        try:
            pipe.write(b'this is not written')
            raise AssertionError('The pipe has not closed properly')
        except OSError:
            # okay
            pass

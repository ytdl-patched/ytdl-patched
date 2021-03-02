# coding: utf-8
from __future__ import unicode_literals

from PyInstaller import __main__

import zlib
import zopfli
import os

try:
    iterations = int(os.environ['ZOPFLI_ITERATIONS'])
except BaseException:
    iterations = 30


def zlib_compress(data, level=-1):
    c = zopfli.ZopfliCompressor(zopfli.ZOPFLI_FORMAT_ZLIB, iterations=iterations)
    return c.compress(data) + c.flush()


zlib.compress = zlib_compress

__main__.run()

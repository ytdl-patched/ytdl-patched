# coding: utf-8
from __future__ import unicode_literals

from PyInstaller import __main__

import zlib
import zopfli


def zlib_compress(data, level=-1):
    c = zopfli.ZopfliCompressor(zopfli.ZOPFLI_FORMAT_ZLIB, iterations=30)
    return c.compress(data) + c.flush()


zlib.compress = zlib_compress

__main__.run()

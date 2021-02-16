# coding: utf-8
from __future__ import unicode_literals

from PyInstaller import __main__

import zlib
import zopfli.zlib


def zlib_compress(data, level=-1):
    return zopfli.zlib.compress(data, numiterations=30)


zlib.compress = zlib_compress

__main__.run()

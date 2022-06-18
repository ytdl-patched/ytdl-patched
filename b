#!/bin/sh
exec "${PYTHON:-python3}" -bb -Werror -Xdev ./ytdl.py "$@"

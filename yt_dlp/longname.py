# coding: utf-8
from __future__ import unicode_literals

import re

from typing import Union

from os import PathLike, fsdecode, remove, rename, sep, stat, utime, unlink, makedirs, replace
from os.path import exists, isfile, getsize, normpath, join, basename, dirname, isabs
from .compat import compat_str
from .utils import (
    sanitize_open,
    get_filesystem_encoding,
)

# this file is to escape long file names in following manner:
# 1. split each path segment in 255-N bytes (N=byte length of DEFAULT_DELIMITER below)
# 2. prepend DEFAULT_DELIMITER, and then path segments are split within filesystem limit,
#      with a marker on each split chunks

FS_LENGTH_LIMIT = 255  # length limit from filesystem
DEFAULT_DELIMITER = "~~"

# http://hg.openjdk.java.net/jdk8u/jdk8u/jdk/file/dc4322602480/src/share/classes/java/lang/Character.java
# Constants from JDK
MIN_HIGH_SURROGATE = 0xD800
MAX_HIGH_SURROGATE = 0xDBFF
MIN_LOW_SURROGATE = 0xDC00
MAX_LOW_SURROGATE = 0xDFFF


def split_longname(input, encoding=get_filesystem_encoding()):
    # type: (Union[bytes, compat_str, PathLike], compat_str) -> bytes
    if PathLike and isinstance(input, PathLike):
        input = fsdecode(input)

    was_bytes = isinstance(input, bytes)
    if was_bytes:
        input = input.decode(encoding)

    result = split_longname_str(input, encoding)

    if was_bytes:
        result = result.encode(encoding)
    return result


def combine_longname(input, encoding=get_filesystem_encoding()):
    # type: (Union[bytes, compat_str, PathLike], compat_str) -> bytes
    if PathLike and isinstance(input, PathLike):
        input = fsdecode(input)

    was_bytes = isinstance(input, bytes)
    if was_bytes:
        input = input.decode(encoding)

    result = combine_longname_str(input, encoding)

    if was_bytes:
        result = result.encode(encoding)
    return result


def split_longname_str(input, encoding=get_filesystem_encoding()):
    # type: (compat_str, compat_str) -> compat_str
    # https://docs.python.org/3/library/codecs.html
    chunks = re.split(r'[\\/]', input)
    result = []
    if encoding in ('utf_8', 'U8', 'UTF', 'utf8', 'cp65001'):
        # fast(er) path: UTF-8
        CHUNK_LENGTH = FS_LENGTH_LIMIT - 2
        for chunk in chunks:
            if utf8_byte_length_all_chr(chunk) <= FS_LENGTH_LIMIT:
                result.append(chunk)
                continue
            current_split, current_length = '', 0

            for chr in chunk:
                chrlen = utf8_byte_length(chr)
                print(current_split)
                if current_length + chrlen > CHUNK_LENGTH:
                    if current_split:
                        result.append(current_split + DEFAULT_DELIMITER)
                    current_split, current_length = '', 0
                current_split += chr
                current_length += chrlen

            if current_split:
                result.append(current_split)
    elif encoding in ('utf_16', 'U16', 'utf16', 'utf_16_be', 'UTF-16BE', 'utf_16_le', 'UTF-16LE'):
        # fast path: UTF-16 ANY Endian
        CHUNK_LENGTH = FS_LENGTH_LIMIT - 4
        for chunk in chunks:
            if len(chunk) * 2 <= FS_LENGTH_LIMIT:
                result.append(chunk)
                continue
            current_split, current_length = '', 0

            for chr in chunk:
                chrord = ord(chr)
                chrlen = 2
                if chrord >= MIN_HIGH_SURROGATE and chrord < (MAX_HIGH_SURROGATE + 1):
                    chrlen = 4
                elif chrord >= MIN_LOW_SURROGATE and chrord < (MAX_LOW_SURROGATE + 1):
                    chrlen = 0  # same reason as UTF-8 does

                if current_length + chrlen > CHUNK_LENGTH:
                    if current_split:
                        result.append(current_split + DEFAULT_DELIMITER)
                    current_split, current_length = '', 0
                current_split += chr
                current_length += chrlen

            if current_split:
                result.append(current_split)
    elif encoding in ('utf_32', 'U32', 'utf32', 'utf_32_be', 'UTF-32BE', 'utf_32_le', 'UTF-32LE'):
        # (very) fast path: UTF-32 ANY Endian
        CHUNK_LENGTH = FS_LENGTH_LIMIT - 8
        for chunk in chunks:
            chunk_len = len(chunk)
            if chunk_len * 4 <= FS_LENGTH_LIMIT:
                result.append(chunk)
                continue

            for i in range(0, chunk_len, 4):
                if chunk_len < i + 4:
                    result.append(chunk[i:i + 4] + DEFAULT_DELIMITER)
                else:
                    result.append(chunk[i:i + 4])
    else:
        # slow path: encode each charaters
        # any encoding with header/marking will break this (like UTF-16 with BOM, or 'idna')
        CHUNK_LENGTH = FS_LENGTH_LIMIT - len(DEFAULT_DELIMITER.encode(encoding))
        for chunk in chunks:
            if len(chunk.encode(encoding)) <= FS_LENGTH_LIMIT:
                result.append(chunk)
                continue
            current_split, current_length = '', 0

            for chr in chunk:
                chrlen = len(chr.encode(encoding))
                if current_length + chrlen > CHUNK_LENGTH:
                    if current_split:
                        result.append(current_split + DEFAULT_DELIMITER)
                    current_split, current_length = '', 0
                current_split += chr
                current_length += chrlen

            if current_split:
                result.append(current_split)

    return sep.join(result)


def combine_longname_str(input, encoding=get_filesystem_encoding()):
    # type: (compat_str, compat_str) -> str
    result = []
    for part in re.split(r'[\\/]', input):
        if result and result[-1].endswith(DEFAULT_DELIMITER):
            result[-1] = result[-1][:-2] + part
        else:
            result.append(part)
    return sep.join(result)


def utf8_byte_length(chr):
    "Calculates byte length in UTF-8 without encode/decode"
    # type: (Union[compat_str, int]) -> int
    if isinstance(chr, compat_str):
        chr = ord(chr[0])

    if chr <= 0x7F:
        return 1
    if chr <= 0x7FF:
        return 2
    # refer to Character.isHighSurrogate from Java
    if chr >= MIN_HIGH_SURROGATE and chr < (MAX_HIGH_SURROGATE + 1):
        return 4  # HIGH+LOW, low should be added later without cost
    if chr >= MIN_LOW_SURROGATE and chr < (MAX_LOW_SURROGATE + 1):
        return 0  # length for this is already accounted at high surrogate

    return 3


def utf8_byte_length_all_chr(string):
    "Calculates byte length in UTF-8 without encode/decode"
    # type: (compat_str) -> int
    result = 0
    for chr in string:
        chr = ord(chr[0])
        if chr <= 0x7F:
            result += 1
        elif chr <= 0x7FF:
            result += 2
        # refer to Character.isHighSurrogate from Java
        elif chr >= MIN_HIGH_SURROGATE and chr < (MAX_HIGH_SURROGATE + 1):
            result += 4  # HIGH+LOW, low should be added later without cost
        elif chr >= MIN_LOW_SURROGATE and chr < (MAX_LOW_SURROGATE + 1):
            result += 0  # length for this is already accounted at high surrogate
        else:
            result += 3
    return result


def ensure_directory(filename):
    split = split_longname(filename, get_filesystem_encoding())
    if split != filename:
        try:
            makedirs(normpath(join(split, '..')))
        except FileExistsError:
            pass
    return split


def escaped_open(filename, open_mode, **kwargs):
    "open() that escapes long names"
    split = ensure_directory(filename)
    return open(split, open_mode, **kwargs)


def escaped_sanitize_open(filename, open_mode):
    "sanitized_open() that escapes long names"
    split = ensure_directory(filename)
    a, b = sanitize_open(split, open_mode)
    b = combine_longname(b)
    return a, b


def escaped_stat(path, *args, **kwargs):
    "os.stat() that escapes long names"
    return stat(split_longname(path, get_filesystem_encoding()), *args, **kwargs)


def escaped_unlink(path, *args, **kwargs):
    "os.unlink() that escapes long names"
    unlink(split_longname(path, get_filesystem_encoding()), *args, **kwargs)


def escaped_path_isfile(path):
    "os.path.isfile() that escapes long names"
    return isfile(split_longname(path, get_filesystem_encoding()))


def escaped_path_exists(path):
    "os.path.exists() that escapes long names"
    return exists(split_longname(path, get_filesystem_encoding()))


def escaped_path_getsize(filename):
    "os.path.getsize() that escapes long names"
    return getsize(split_longname(filename, get_filesystem_encoding()))


def escaped_utime(path, *args, **kwargs):
    "os.utime() that escapes long names"
    utime(split_longname(path, get_filesystem_encoding()), *args, **kwargs)


def escaped_rename(src, dst, *args, **kwargs):
    "os.rename() that escapes long names"
    dst = ensure_directory(dst)
    rename(
        split_longname(src, get_filesystem_encoding()),
        dst, *args, **kwargs)


def escaped_replace(src, dst, *args, **kwargs):
    "os.replace() that escapes long names"
    dst = ensure_directory(dst)
    replace(
        split_longname(src, get_filesystem_encoding()),
        dst, *args, **kwargs)


def escaped_remove(path, *args, **kwargs):
    "os.remove() that escapes long names"
    remove(split_longname(path, get_filesystem_encoding()), *args, **kwargs)


def escaped_basename(path):
    "os.path.basename() that escapes long names"
    return basename(split_longname(path, get_filesystem_encoding()))


def escaped_dirname(path):
    "os.path.dirname() that escapes long names"
    return dirname(split_longname(path, get_filesystem_encoding()))


def escaped_isabs(path):
    "os.path.isabs() that escapes long names"
    return isabs(split_longname(path, get_filesystem_encoding()))

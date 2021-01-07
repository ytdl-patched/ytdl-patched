# coding: utf-8
from __future__ import unicode_literals

import re

from os import pathsep
from .compat import compat_str
try:
    from typing import Union
except ImportError:
    pass

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


def split_longname_bytes(input, encoding):
    # type: (bytes, compat_str) -> bytes
    return split_longname_str(input.decode(encoding)).encode(encoding)


def combine_longname_bytes(input, encoding):
    # type: (bytes, compat_str) -> bytes
    return combine_longname_bytes(input.decode(encoding)).encode(encoding)


def split_longname_str(input, encoding):
    # type: (compat_str, compat_str) -> compat_str
    # https://docs.python.org/3/library/codecs.html
    chunks = re.split(r'[\\/]', input)
    result = []
    if encoding in ('utf_8', 'U8', 'UTF', 'utf8', 'cp65001'):
        # fast(er) path: UTF-8
        CHUNK_LENGTH = FS_LENGTH_LIMIT - 2
        for chunk in chunks:
            if utf8_byte_length_all_chr(chunk) < FS_LENGTH_LIMIT:
                result.append(chunk)
                continue
            current_split, current_length = '', 0

            for chr in chunk:
                chrlen = utf8_byte_length(chr)
                if current_length + chrlen > CHUNK_LENGTH:
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
            if len(chunk) * 2 < FS_LENGTH_LIMIT:
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
            if chunk_len * 4 < FS_LENGTH_LIMIT:
                result.append(chunk)
                continue

            for i in range(0, chunk_len, 4):
                if chunk_len < i + 4:
                    result.append(chunk[i:i + 4] + DEFAULT_DELIMITER)
                else:
                    result.append(chunk[i:i + 4])
    else:
        # slow path: decode each charaters
        # any encoding with header/marking will break this (like UTF-16 with BOM, or 'idna')
        CHUNK_LENGTH = FS_LENGTH_LIMIT - len(DEFAULT_DELIMITER.encode(encoding))
        for chunk in chunks:
            if len(chunk.encode(encoding)) < FS_LENGTH_LIMIT:
                result.append(chunk)
                continue
            current_split, current_length = '', 0

            for chr in chunk:
                chrlen = len(chr.encode(encoding))
                if current_length + chrlen > CHUNK_LENGTH:
                    result.append(current_split + DEFAULT_DELIMITER)
                    current_split, current_length = '', 0
                current_split += chr
                current_length += chrlen

            if current_split:
                result.append(current_split)

    return pathsep.join(result)


def combine_longname_str(input, encoding):
    # type: (compat_str, compat_str) -> str
    result = ''
    for m in re.split(r'[\\/]', input):
        part = m.group(0)
        if result.endswith(DEFAULT_DELIMITER):
            result = result[:-2] + part
        else:
            result += part
            result += pathsep
    return result[:-1]


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


def utf8_byte_length_all_chr(chr):
    "Calculates byte length in UTF-8 without encode/decode"
    # type: (compat_str) -> int
    result = 0
    for chr in compat_str:
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

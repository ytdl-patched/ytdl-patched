#!/bin/bash
set -x
for I in "$@"; do
  wget https://github.com/ytdl-patched/ytdl-patched/raw/ytdlp/"$I" -O "$I"
done

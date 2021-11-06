#!/bin/bash
set -x
for I in "$@"; do
  wget https://github.com/yt-dlp/yt-dlp/raw/master/"$I" -O "$I"
done

#!/bin/bash
set -xe
# https://unix.stackexchange.com/questions/89275/how-to-create-ico-file-with-more-than-one-image
convert -background transparent "$1" -define icon:auto-resize=16,32,48,64,128,192,256 "${1%%.*}.ico"

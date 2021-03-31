#!/bin/bash

# Keep this list in sync with the `offlinetest` target in Makefile
DOWNLOAD_TESTS="age_restriction|download|iqiyi_sdk_interpreter|socks|subtitles|write_annotations|youtube_lists|youtube_signature|websocket"

test_set=""
multiprocess_args=""

case "$YTDL_TEST_SET" in
    core)
        test_set="-I test_($DOWNLOAD_TESTS)\.py"
    ;;
    download)
        test_set="-I test_(?!$DOWNLOAD_TESTS).+\.py"
        # disable multiprocessing for IronPython tests
        if [ "x$PYTHON_HAS_MULTIPROCESSING" != "xno" ] ; then
            multiprocess_args="--processes=4 --process-timeout=540"
        fi
    ;;
    *)
        # break
    ;;
esac

nosetests test --verbose $test_set $multiprocess_args

from __future__ import division, unicode_literals

import os
import sys
from subprocess import Popen, PIPE

from .external import FFmpegFD
from .dash import DashSegmentsFD
from ..compat import compat_str
from ..longname import split_longname
from ..postprocessor.ffmpeg import EXT_TO_OUT_FORMATS, FFmpegPostProcessor
from ..utils import (
    encodeArgument,
    encodeFilename,
)


class ImageFragmentFD(DashSegmentsFD):
    """ Downloads series of images as a video """

    FD_NAME = 'image_fragment'


class ImageSeriesFD(FFmpegFD):
    """ Downloads series of images as a video """

    FD_NAME = 'image_series'

    def __init__(self, ydl, params):
        super().__init__(ydl, params)
        self._IFFD = ImageFragmentFD(ydl, {**params, 'skip_unavailable_fragments': True})

    def _call_downloader(self, tmpfilename, info_dict):
        filename = self.undo_temp_name(tmpfilename)
        images_filename = filename + '.images'
        segment_result, _ = self._IFFD.download(images_filename, info_dict)
        if not segment_result:
            return False

        # convert to video using ffmpeg
        ffpp = FFmpegPostProcessor(downloader=self)
        if not ffpp.available:
            self.report_error('ffmpeg could not be found. Please install')
            return False
        ffpp.check_version()

        if self.ydl.params.get('escape_long_names', False):
            tmpfilename = split_longname(tmpfilename)

        args = [ffpp.executable, '-y']

        for log_level in ('quiet', 'verbose'):
            if self.params.get(log_level, False):
                args += ['-loglevel', log_level]
                break
        if not self.params.get('verbose'):
            args += ['-hide_banner']

        args += info_dict.get('_ffmpeg_args', [])

        args += ['-f', 'image2pipe']

        if 'frame_count' in info_dict and 'duration' in info_dict:
            framerate_string = '%f/%f' % (info_dict['frame_count'], info_dict['duration'])
        else:
            framerate_string = compat_str(info_dict.get('fps'))
        args += ['-r', framerate_string]

        args += self._configuration_args(('_i1', '_i')) + [
            '-i', ffpp._ffmpeg_filename_argument(images_filename)]

        args += ['-c:v', 'libx265']

        if self.params.get('test', False):
            args += ['-fs', compat_str(self._TEST_FILE_SIZE)]

        ext = info_dict['ext']
        args += [
            '-f', EXT_TO_OUT_FORMATS.get(ext, ext),
            '-crf', framerate_string,
            '-pix_fmt', 'yuv420p']

        args += self._configuration_args(('_o1', '_o', ''))

        args = [encodeArgument(opt) for opt in args]
        args.append(encodeFilename(ffpp._ffmpeg_filename_argument(tmpfilename), True))
        self._debug_cmd(args)

        proc = Popen(args, stdin=PIPE)
        try:
            retval = -1
            retval = proc.wait()
        except BaseException as e:
            # subprocces.run would send the SIGKILL signal to ffmpeg and the
            # mp4 file couldn't be played, but if we ask ffmpeg to quit it
            # produces a file that is playable (this is mostly useful for live
            # streams). Note that Windows is not affected and produces playable
            # files (see https://github.com/ytdl-org/youtube-dl/issues/8300).
            if isinstance(e, KeyboardInterrupt) and sys.platform != 'win32':
                proc.communicate_or_kill(b'q')
            else:
                proc.kill()
                proc.wait()
                raise
        if retval == 0:
            os.remove(images_filename)
        return retval

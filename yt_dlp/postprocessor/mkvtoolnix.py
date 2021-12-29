from __future__ import unicode_literals
import itertools

import os
import re
import subprocess

from .common import PostProcessor

from ..utils import (
    _get_exe_version_output,
    determine_ext,
    encodeArgument,
    encodeFilename,
    Popen,
    PostProcessingError,
    shell_quote,
    variadic,
)


class MkvToolNixPostProcessorError(PostProcessingError):
    def __init__(self, msg=None, retval=None):
        super().__init__(msg=msg)
        self.retval = retval


class MkvToolNixPostProcessor(PostProcessor):
    _EXECUTABLE = ''

    def __init__(self, downloader=None):
        PostProcessor.__init__(self, downloader)
        self._PROGRESS_LABEL = self.pp_key()
        self._determine_executables()

    def _determine_executables(self):
        self._path = {}
        self._version = None
        self._accepted_formats = ()

        def get_executable_version(path, prog):
            out = _get_exe_version_output(path, ['--version'])
            regexs = [
                r'v((?:\d+\.)+\d)'
            ]
            ver = next((mobj.group(1) for mobj in filter(None, (re.match(regex, out) for regex in regexs))), None)
            self._version = ver
            if prog != 'mkvmerge' or not out:
                return

            # get list of supported formats
            out = _get_exe_version_output(path, ['--list-types'])
            self._accepted_formats = tuple(ext for mobj in re.finditer(r'\[(.+?)\]', out) for ext in mobj.group(1).split())

        ex = self._EXECUTABLE
        location = self.get_param(f'{ex}_location')
        if not location:
            mtn = self.get_param('mkvtoolnix_location')
            if mtn:
                location = os.path.join(self.get_param('mkvtoolnix_location'), self._EXECUTABLE)

        if not location:
            self._path = ex
        else:
            if not os.path.exists(location):
                self.report_warning(
                    '{self._BINARY_NAME}-location %s does not exist! '
                    'Continuing without {self._BINARY_NAME}.' % (location),
                    only_once=True)
                return
            elif os.path.isdir(location):
                dirname, basename = location, None
            else:
                basename = os.path.splitext(os.path.basename(location))[0]
                basename = ex if basename.startswith(ex) else None
                dirname = os.path.dirname(os.path.abspath(location))

            self._path = location if basename else os.path.join(dirname, ex)

        get_executable_version(self._path, ex)

    @property
    def available(self):
        return bool(self._path)

    def run_binary(self, input_path_opts, output_path_opts, *, expected_retcodes=(0,), info_dict=None):
        cmd = [encodeFilename(self._path, True), encodeArgument('-y')]

        oldest_mtime = min(
            self._downloader.stat(path).st_mtime for path, _ in input_path_opts if path)

        if len(output_path_opts) != 1:
            raise MkvToolNixPostProcessorError('Number of output file must be exactly one file.')

        def make_args(file, args, name, number):
            keys = ['_%s%d' % (name, number), '_%s' % name]
            if name == 'i' and self._accepted_formats:
                ext = determine_ext(file, None)
                if ext and ext not in self._accepted_formats:
                    raise MkvToolNixPostProcessorError(f'Format {ext} is not supprted for input. Use ffmpeg to do this post processing.')
            if name == 'o':
                ext = determine_ext(file, None)
                if ext in ('webm', 'webmv', 'webma'):
                    args.append('--webm')
                elif ext not in ('mka', 'mks', 'mkv', 'mk3d'):
                    raise MkvToolNixPostProcessorError(f'Format {ext} is not supprted for output. Use ffmpeg to do this post processing.')
                args.append('-o')
                if number == 1:
                    keys.append('')
            args += self._configuration_args(self._EXECUTABLE, keys)
            return (
                [encodeArgument(arg) for arg in args] + [file])

        for arg_type, path_opts in (('o', output_path_opts), ('i', input_path_opts)):
            cmd += itertools.chain.from_iterable(
                make_args(path, list(opts), arg_type, i + 1)
                for i, (path, opts) in enumerate(path_opts) if path)

        self.write_debug('program command line: %s' % shell_quote(cmd))

        p = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        stderr = p.communicate_or_kill()[1]
        retval = p.returncode

        if isinstance(stderr, bytes):
            stderr = stderr.decode('utf-8', 'replace')

        if retval not in variadic(expected_retcodes):
            stderr = stderr.strip()
            self.write_debug(stderr)
            raise MkvToolNixPostProcessorError(stderr.split('\n')[-1], retval)

        for out_path, _ in output_path_opts:
            if out_path:
                self.try_utime(out_path, oldest_mtime, oldest_mtime)
        return stderr

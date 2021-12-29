from __future__ import unicode_literals

import os
import re

from .common import PostProcessor

from ..utils import (
    _get_exe_version_output,
    PostProcessingError,
)


class MkvToolNixPostProcessorError(PostProcessingError):
    def __init__(self, msg=None, retval=None):
        super().__init__(msg=msg)
        self.retval = retval


class MkvToolNixPostProcessor(PostProcessor):
    _EXECUTABLES = ''

    def __init__(self, downloader=None):
        PostProcessor.__init__(self, downloader)
        self._PROGRESS_LABEL = self.pp_key()
        self._determine_executables()

    def _determine_executables(self):
        self._paths = {}
        self._versions = {}
        self._accepted_formats = ()

        def get_executable_version(path, prog):
            out = _get_exe_version_output(path, ['--version'])
            regexs = [
                r'v((?:\d+\.)+\d)'
            ]
            ver = next((mobj.group(1) for mobj in filter(None, (re.match(regex, out) for regex in regexs))), None)
            self._versions[prog] = ver
            if prog != 'mkvmerge' or not out:
                return

            # get list of supported formats
            out = _get_exe_version_output(path, ['--list-types'])
            self._accepted_formats = tuple(ext for mobj in re.finditer(r'\[(.+?)\]', out) for ext in mobj.group(1).split())

        for ex in self._EXECUTABLES:
            location = self.get_param(f'{ex}_location')
            if not location:
                mtn = self.get_param('mkvtoolnix_location')
                if mtn:
                    location = os.path.join(self.get_param('mkvtoolnix_location'), self._EXECUTABLES)

            if not location:
                self._paths[ex] = ex
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

                self._paths[ex] = os.path.join(dirname, ex)
                if basename:
                    self._paths[basename] = location

            get_executable_version(self._paths[ex], ex)

    @property
    def available(self):
        return bool(self._paths)

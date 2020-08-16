# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    sanitized_Request,
    ExtractorError,
)
from ..compat import (
    compat_str,
)

class ViewSourceIE(InfoExtractor):
    IE_DESC = False  # Do not list
    IE_NAME = 'tokyomotion:scanner'
    _VALID_URL = r'view-source:.*'
    _TEST = {}
    def _real_extract(self, url):
        if url.startswith('view-source:'):
            # remove "view-source:"
            return self.url_result(url[:url.index(':')])
        else:
            raise ExtractorError('Not a view-source: URL', expected=True)

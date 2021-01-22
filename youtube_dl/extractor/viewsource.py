# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
import re


class ViewSourceIE(InfoExtractor):
    IE_DESC = False  # Do not list
    _VALID_URL = r'^view-source:'

    def _real_extract(self, url):
        self._downloader.report_warning('URL is pasted with "view-source:" appended')
        url = re.sub(self._VALID_URL, '', url)
        return self.url_result(url)

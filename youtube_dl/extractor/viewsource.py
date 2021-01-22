# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class ViewSourceIE(InfoExtractor):
    IE_DESC = False  # Do not list
    IE_NAME = 'view-source'
    _VALID_URL = r'^view-source:'
    _TEST = {}

    def _real_extract(self, url):
        if url.startswith('view-source:'):
            self._downloader.report_warning('URL is pasted with "view-source:" appended')
            url = url[url.index(':') + 1:]
        return self.url_result(url)

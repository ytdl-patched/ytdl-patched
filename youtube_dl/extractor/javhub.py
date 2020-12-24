# coding: utf-8
from __future__ import unicode_literals

import re
import itertools

from .common import InfoExtractor
from ..compat import (
    compat_urllib_parse_urlparse,
)
from ..utils import (
    int_or_none,
    mimetype2ext,
    url_or_none,
    urljoin,
)


class JavhubIE(InfoExtractor):
    # https://gist.github.com/nao20010128nao/ea66c03691fc253e4182deb350560cad
    IE_NAME = 'javhub'
    _VALID_URL = r'https://(?:ja\.)?javhub\.net/play/(?P<id>[^/]+)'

    B58_TABLE_1 = '23456789ABCDEFGHJKLNMPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz1'
    B58_TABLE_2 = '789ABCDEFGHJKLNMPQRSTUVWX23456YZabcdefghijkmnopqrstuvwxyz1'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data_src = self._search_regex(r'data-src="([\"]+)"(?:>| data-track)', webpage, 'data-src')
        data_track = self._search_regex(r'data-track="([\"]+)">', webpage, 'data-track', fatal=False)

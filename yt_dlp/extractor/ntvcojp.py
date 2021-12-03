# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    js_to_json,
    smuggle_url,
)


class NTVCoJpCUIE(InfoExtractor):
    IE_NAME = 'cu.ntv.co.jp'
    IE_DESC = 'Nippon Television Network'
    _VALID_URL = r'https?://cu\.ntv\.co\.jp/(?!program)(?P<id>[^/?&#]+)'
    _TEST = {
        'url': 'https://cu.ntv.co.jp/televiva-chill-gohan_181031/',
        'info_dict': {
            'id': '5978891207001',
            'ext': 'mp4',
            'title': '桜エビと炒り卵がポイント！ 「中華風 エビチリおにぎり」──『美虎』五十嵐美幸',
            'upload_date': '20181213',
            'description': 'md5:1985b51a9abc285df0104d982a325f2a',
            'uploader_id': '3855502814001',
            'timestamp': 1544669941,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'
    _NUXT_TEMPLATE = r'(?s)window\s*\.\s*__NUXT__\s*=\s*\(\s*function\s*\([^)]+?\)\s*{\s*return\s*{.*%s'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        player_config = self._parse_json(self._search_regex(
            (self._NUXT_TEMPLATE % r'{\s*player\s*:\s*({.+?})\s*,',
             r'(?s)PLAYER_CONFIG\s*=\s*({.+?})'),
            webpage, 'player config'), display_id, js_to_json)
        video_id = player_config.get('videoId')
        if video_id is None:
            video_id = self._search_regex(
                self._NUXT_TEMPLATE % r'video_id\s*:\s*"(\d+)"\s*,',
                webpage, 'video_id')
        account_id = player_config.get('account') or '3855502814001'
        title = self._og_search_title(webpage, fatal=False)
        if title:
            title = title.split('(', 1)[0]
        if not title:
            title = self._html_search_regex(r'<h1[^>]+class="title"[^>]*>([^<]+)', webpage, 'title').strip()
        return {
            '_type': 'url_transparent',
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': self._html_search_meta(['description', 'og:description'], webpage),
            'url': smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % (account_id, video_id), {'geo_countries': ['JP']}),
            'ie_key': 'BrightcoveNew',
        }

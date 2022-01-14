# coding: utf-8
from __future__ import unicode_literals

import re
import urllib.parse

from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    ExtractorError,
    float_or_none,
    js_to_json,
    parse_qs,
    try_get,
)


class PandoraTVIE(InfoExtractor):
    IE_NAME = 'pandora.tv'
    IE_DESC = '판도라TV'
    _VALID_URL = r'''(?x)
                        https?://
                            (?:
                                (?:www\.)?pandora\.tv/view/(?P<user_id>[^/]+)/(?P<id>\d+)|  # new format
                                (?:.+?\.)?channel\.pandora\.tv/channel/video\.ptv\?|        # old format
                                m\.pandora\.tv/?\?                                          # mobile
                            )
                    '''
    _TESTS = [{
        'url': 'http://jp.channel.pandora.tv/channel/video.ptv?c1=&prgid=53294230&ch_userid=mikakim&ref=main&lot=cate_01_2',
        'info_dict': {
            'id': '53294230',
            'ext': 'flv',
            'title': '頭を撫でてくれる？',
            'description': '頭を撫でてくれる？',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 39,
            'upload_date': '20151218',
            'uploader': 'カワイイ動物まとめ',
            'uploader_id': 'mikakim',
            'view_count': int,
            'like_count': int,
        }
    }, {
        'url': 'http://channel.pandora.tv/channel/video.ptv?ch_userid=gogoucc&prgid=54721744',
        'info_dict': {
            'id': '54721744',
            'ext': 'flv',
            'title': '[HD] JAPAN COUNTDOWN 170423',
            'description': '[HD] JAPAN COUNTDOWN 170423',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1704.9,
            'upload_date': '20170423',
            'uploader': 'GOGO_UCC',
            'uploader_id': 'gogoucc',
            'view_count': int,
            'like_count': int,
        },
        'params': {
            # Test metadata only
            'skip_download': True,
        },
    }, {
        'url': 'http://www.pandora.tv/view/mikakim/53294230#36797454_new',
        'only_matching': True,
    }, {
        'url': 'http://m.pandora.tv/?c=view&ch_userid=mikakim&prgid=54600346',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        user_id = mobj.group('user_id')
        video_id = mobj.group('id')

        if not user_id or not video_id:
            qs = parse_qs(url)
            video_id = qs.get('prgid', [None])[0]
            user_id = qs.get('ch_userid', [None])[0]
            if not all(f for f in (video_id, user_id)):
                raise ExtractorError('Invalid URL', expected=True)

        webpage = self._download_webpage(f'http://www.pandora.tv/view/{user_id}/{video_id}', video_id)
        variables = {x.group(1): js_to_json(x.group(2)) for x in re.finditer(r'(?m)var\s+(\S+)\s*=\s*(.+?);$', webpage)}
        variables = {k: self._parse_json(v, video_id, fatal=False) for k, v in variables.items()}
        print(variables)

        data = self._download_json(
            'http://www.pandora.tv/external/getExternalApi/getVodUrl/', video_id,
            form_params={
                'userid': user_id,
                'prgid': video_id,
                'fid': variables['strFid'],
                'resolType': variables['strResolType'],
                'resolArr': variables['strResolArr'][0],
                'vodStr': variables['nVodSvr'],
                'resol': variables['nCurResol'],
                'runtime': variables['runtime'],
                'tvbox': 'false',
                'defResol': 'true',
                'embed': 'false',
            })
        if not data.get('result'):
            raise ExtractorError('Failed to request video URL')

        return {
            'id': video_id,
            'title': urllib.parse.unquote(variables['strTitle']),
            'description': self._html_search_meta((
                'og:description', 'twitter:description', 'description', 'twitter:card'), webpage, 'description'),
            'thumbnail': variables.get('thumbnail'),
            'duration': float_or_none(variables.get('runtime'), 1000),
            'upload_date': variables['fid'].split('/')[-1][:8] if isinstance(variables.get('fid'), compat_str) else None,
            'uploader': variables.get('strChUserNick'),
            'uploader_id': variables.get('strChUserId'),
            'channel': variables.get('strChUserId'),
            'channel_id': variables.get('strChName'),
            'view_count': try_get(webpage, lambda x: int(re.search(r'id="prgViewCount">\s*([0-9,]+)\s*</', x).group(1).replace(',', ''))),

            'url': data.get('src'),
            'height': variables['nCurResol'],
        }

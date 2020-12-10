# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    try_get,
    ExtractorError,
)
from ..compat import (
    compat_str,
)


class PixivSketchBaseIE(InfoExtractor):
    pass


class PixivSketchIE(PixivSketchBaseIE):
    IE_NAME = 'pixiv:sketch'
    # https://sketch.pixiv.net/@kotaru_taruto/lives/3404565243464976376
    _VALID_URL = r'https?://sketch\.pixiv\.net/@(?P<uploader_id>[a-zA-Z0-9_-]+)/lives/(?P<id>\d+)/?'
    _TEST = {}
    API_JSON_URL = 'https://sketch.pixiv.net/api/lives/%s.json'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        uploader_id_url = compat_str(self._VALID_URL_RE.match(url).group('uploader_id'))
        data = self._download_json(self.API_JSON_URL % video_id, video_id, headers={
            'Referer': url,
            'X-Requested-With': url,
        })['data']

        if not data or not data['is_broadcasting']:
            raise ExtractorError('This live is offline. Use https://sketch.pixiv.net/%s for ongoing live.' % uploader_id_url, expected=True)

        formats = self._extract_m3u8_formats(
            data['owner']['hls_movie']['url'], video_id, ext='mp4',
            entry_protocol='m3u8_native', m3u8_id='hls')
        self._sort_formats(formats)

        title = data['name']
        uploader = try_get(data, (
            lambda x: x['user']['name'],
            lambda x: x['owner']['user']['name'],
        ), None)
        uploader_id = try_get(data, (
            lambda x: x['user']['unique_name'],
            lambda x: x['owner']['user']['unique_name'],
        ), None) or uploader_id_url
        uploader_id_numeric = try_get(data, (
            lambda x: compat_str(x['user']['id']),
            lambda x: compat_str(x['owner']['user']['id']),
        ), None)
        uploader_pixiv_id = try_get(data, (
            lambda x: compat_str(x['user']['pixiv_user_id']),
            lambda x: compat_str(x['owner']['user']['pixiv_user_id']),
        ), None)
        if data['is_r18']:
            age_limit = 18
        elif data['is_r15']:
            age_limit = 15
        else:
            age_limit = 0

        return {
            'formats': formats,
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'uploader_id_numeric': uploader_id_numeric,
            'uploader_pixiv_id': uploader_pixiv_id,
            'age_limit': age_limit,
            'is_live': True
            # 'raw': data,
        }


class PixivSketchUserIE(PixivSketchBaseIE):
    IE_NAME = 'pixiv:sketch:user'
    # https://sketch.pixiv.net/@kotaru_taruto
    _VALID_URL = r'https?://sketch\.pixiv\.net/@(?P<id>[a-zA-Z0-9_-]+)/?'
    API_JSON_URL = 'https://sketch.pixiv.net/api/lives/users/@%s.json'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(self.API_JSON_URL % video_id, video_id, headers={
            'Referer': url,
            'X-Requested-With': url,
        })['data']

        if not data:
            try:
                self._download_json('https://sketch.pixiv.net/api/users/current.json', video_id, headers={
                    'Referer': url,
                    'X-Requested-With': url,
                }, note='Investigating reason of download failure')['data']
            except ExtractorError as cause:
                if cause.cause.code == 401:
                    # without login, it throws 401
                    raise ExtractorError('Please log in, or use live URL like https://sketch.pixiv.net/@%s/1234567890' % video_id,
                                         expected=True, cause=cause.cause)
                else:
                    raise
            else:
                raise ExtractorError('This user is offline', expected=True)
        if not data['is_broadcasting']:
            raise ExtractorError('This user is offline', expected=True)

        live_id = data['id']
        return self.url_result('https://sketch.pixiv.net/@%s/lives/%s' % (video_id, live_id))

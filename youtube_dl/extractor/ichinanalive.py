# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import ExtractorError, str_or_none, unified_strdate
from ..compat import compat_str


# the real service name of this extractor is "17live",
#   but identifiers cannot start with numbers.
# class name of this extractor is taken from official pronounce in Japanese,
#   so it will be replace as: "1"="ichi", "7"="nana", "live"=as-is .
class IchinanaLiveIE(InfoExtractor):
    IE_NAME = '17live'
    _VALID_URL = r'https?://(?:www\.)?17\.live/(?:live|profile/r)/(?P<id>\d+)'
    _TEST = {
        'url': 'https://17.live/live/580309',
        'only_matching': True,
    }

    @classmethod
    def suitable(cls, url):
        return not IchinanaLiveClipIE.suitable(url) and super(IchinanaLiveIE, cls).suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = 'https://17.live/live/%s' % video_id
        # self._download_webpage(url, video_id)

        # this endpoint sometimes return code 420, which is not defined
        enter = self._download_json(
            'https://api-dsa.17app.co/api/v1/lives/%s/enter' % video_id, video_id,
            headers={'Referer': url}, fatal=False, expected_status=lambda x: True,
            data=b'\0')
        if enter and enter.get('message') == 'ended':
            raise ExtractorError('This live has ended.', expected=True)

        view_data = self._download_json(
            'https://api-dsa.17app.co/api/v1/lives/%s' % video_id, video_id,
            headers={'Referer': url})

        user_info = view_data.get('userInfo')
        uploader = None
        if user_info:
            uploader = user_info.get('displayName') or user_info.get('openID')
        like_count = view_data.get('receivedLikeCount')
        view_count = view_data.get('viewerCount')
        thumbnail = view_data.get('coverPhoto')
        description = view_data.get('caption')
        upload_date = unified_strdate(str_or_none(view_data.get('beginTime')))

        video_urls = view_data.get('rtmpUrls')
        if not video_urls:
            raise ExtractorError('unable to extract live URL information')
        formats = []
        # it used to select an item with .provider == 5,
        # but js code seems to select the first element
        for (name, value) in video_urls[0].items():
            if not isinstance(value, compat_str):
                continue
            if not value.startswith('http'):
                continue
            preference = 0.0
            if 'web' in name:
                preference -= 0.25
            if 'High' in name:
                preference += 1.0
            if 'Low' in name:
                preference -= 0.5
            formats.append({
                'format_id': name,
                'url': value,
                'preference': preference,
                # 'ffmpeg' protocol is added by ytdl-patched, same as 'm3u8'
                'protocol': 'ffmpeg',
                'http_headers': {'Referer': url},
                'ext': 'mp4',
                'vcodec': 'h264',
                'acodec': 'aac',
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': uploader or video_id,
            'formats': formats,
            'is_live': True,
            'uploader': uploader,
            'uploader_id': video_id,
            'like_count': like_count,
            'view_count': view_count,
            'thumbnail': thumbnail,
            'description': description,
            'upload_date': upload_date,
        }


class IchinanaLiveClipIE(InfoExtractor):
    IE_NAME = '17live:clip'
    _VALID_URL = r'https?://(?:www\.)?17\.live/profile/r/(?P<uploader_id>\d+)/clip/(?P<id>[^/]+)'
    _TEST = {
        'url': 'https://17.live/profile/r/1789280/clip/1bHQSK8KUieruFXaCH4A4upCzlN',
        'info_dict': {
            'id': '1bHQSK8KUieruFXaCH4A4upCzlN',
            'title': 'マチコ先生🦋Class💋',
            'description': 'マチ戦隊　第一次　バスターコール\n総額200万coin！\n動画制作@うぉーかー🌱Walker🎫',
            'uploader_id': '1789280',
        },
    }

    def _real_extract(self, url):
        m = self._valid_url_re().match(url)
        uploader_id, video_id = m.group('uploader_id'), m.group('id')
        url = 'https://17.live/profile/r/%s/clip/%s' % (uploader_id, video_id)

        view_data = self._download_json(
            'https://api-dsa.17app.co/api/v1/clips/%s/view' % video_id, video_id,
            headers={'Referer': url}, data=b'\0')

        like_count = view_data.get('likeCount')
        view_count = view_data.get('viewCount')
        thumbnail = view_data.get('imageURL')
        duration = view_data.get('duration')
        description = view_data.get('caption')
        upload_date = unified_strdate(str_or_none(view_data.get('createdAt')))

        user_info = self._download_json(
            'https://api-dsa.17app.co/api/v1/clips/%s/view' % video_id, video_id,
            headers={'Referer': url}, fatal=False)
        uploader = None
        if user_info:
            uploader = user_info.get('displayName') or user_info.get('openID')

        formats = []
        if view_data.get('videoURL'):
            formats.append({
                'url': view_data['videoURL'],
                'preference': -1,
            })
        if view_data.get('transcodeURL'):
            formats.append({
                'url': view_data['transcodeURL'],
                'preference': -1,
            })
        if view_data.get('srcVideoURL'):
            # highest quality
            formats.append({
                'url': view_data['srcVideoURL'],
                'preference': 1,
            })

        for fmt in formats:
            fmt.update({
                'ext': 'mp4',
                'protocol': 'https',
                'vcodec': 'h264',
                'acodec': 'aac',
                'http_headers': {'Referer': url},
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': uploader or video_id,
            'formats': formats,
            'uploader': uploader,
            'uploader_id': video_id,
            'like_count': like_count,
            'view_count': view_count,
            'thumbnail': thumbnail,
            'duration': duration,
            'description': description,
            'upload_date': upload_date,
        }

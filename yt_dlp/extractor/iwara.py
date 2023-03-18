import functools
import re
import urllib.parse
import hashlib

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    mimetype2ext,
    traverse_obj,
    unified_timestamp,
    urljoin,
)


class IwaraBaseIE(InfoExtractor):
    _BASE_REGEX = r'(?P<base_url>https?://(?:www\.|ecchi\.)?iwara\.tv)'

    def _extract_playlist(self, base_url, webpage):
        for path in re.findall(r'class="title">\s*<a[^<]+href="(/videos/[^"]+)', webpage):
            yield self.url_result(urljoin(base_url, path))


class IwaraIE(InfoExtractor):
    IE_NAME = 'iwara'
    _VALID_URL = r'https?://(?:www\.|ecchi\.)?iwara\.tv/video/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        # this video cannot be played because of migration
        'only_matching': True,
        'url': 'https://www.iwara.tv/video/k2ayoueezfkx6gvq',
        'info_dict': {
            'id': 'k2ayoueezfkx6gvq',
            'ext': 'mp4',
            'age_limit': 18,
            'title': 'Defeat of Irybelda - アイリベルダの敗北',
            'description': 'md5:70278abebe706647a8b4cb04cf23e0d3',
            'uploader': 'Inwerwm',
            'uploader_id': 'inwerwm',
            'tags': 'count:1',
            'like_count': 6133,
            'view_count': 1050343,
            'comment_count': 1,
            'timestamp': 1677843869,
            'modified_timestamp': 1679056362,
        },
    }, {
        'url': 'https://iwara.tv/video/1ywe1sbkqwumpdxz5/',
        'md5': '20691ce1473ec2766c0788e14c60ce66',
        'info_dict': {
            'id': '1ywe1sbkqwumpdxz5',
            'ext': 'mp4',
            'age_limit': 18,
            'title': 'Aponia 阿波尼亚SEX  Party Tonight 手动脱衣 大奶 裸腿',
            'description': 'md5:0c4c310f2e0592d68b9f771d348329ca',
            'uploader': '龙也zZZ',
            'uploader_id': 'user792540',
            'tags': [
                'uncategorized'
            ],
            'like_count': 1809,
            'view_count': 25156,
            'comment_count': 1,
            'timestamp': 1678732213,
            'modified_timestamp': 1679110271,
        },
    }]

    def _extract_formats(self, video_id, fileurl):
        up = urllib.parse.urlparse(fileurl)
        q = urllib.parse.parse_qs(up.query)
        paths = up.path.split('/')
        # https://github.com/yt-dlp/yt-dlp/issues/6549#issuecomment-1473771047
        x_version = hashlib.sha1('_'.join((paths[-1], q['expires'][0], '5nFp9kmbNnHdAFhaqMvt')).encode()).hexdigest()

        files = self._download_json(fileurl, video_id, headers={'X-Version': x_version})
        for fmt in files:
            yield traverse_obj(fmt, {
                'format_id': 'name',
                'url': ('src', ('view', 'download'), {lambda x: self._proto_relative_url(x, 'https:')}),
                'ext': ('type', {mimetype2ext}),
                'preference': ('name', {lambda x: int(x) if x.isdigit() else 1e4}),
                'height': ('name', {lambda x: int(x)}),
            }, get_all=False)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_json(f'http://api.iwara.tv/video/{video_id}', video_id)

        return {
            'id': video_id,
            'age_limit': 18 if video_data.get('rating') == 'ecchi' else 0,  # ecchi is 'sexy' in Japanese
            **traverse_obj(video_data, {
                'title': 'title',
                'description': 'body',
                'uploader': ('user', 'name'),
                'uploader_id': ('user', 'username'),
                'tags': ('tags', ..., 'id'),
                'like_count': 'numLikes',
                'view_count': 'numViews',
                'comment_count': 'numComments',
                'timestamp': ('createdAt', {unified_timestamp}),
                'modified_timestamp': ('updatedAt', {unified_timestamp}),
                'thumbnail': (
                    'file', 'id', {str},
                    {lambda x: f'https://files.iwara.tv/image/thumbnail/{x}/thumbnail-00.jpg'}),
            }),
            'formats': list(self._extract_formats(video_id, video_data.get('fileUrl'))),
        }


class IwaraUserIE(IwaraBaseIE):
    _VALID_URL = fr'{IwaraBaseIE._BASE_REGEX}/profile/(?P<id>[^/?#&]+)'
    IE_NAME = 'iwara:user'
    _PER_PAGE = 32

    _TESTS = [{
        'url': 'https://iwara.tv/profile/user792540/videos',
        'info_dict': {
            'id': 'user792540',
        },
        'playlist_mincount': 80,
    }, {
        'url': 'https://iwara.tv/profile/theblackbirdcalls/videos',
        'info_dict': {
            'id': 'theblackbirdcalls',
        },
        'playlist_mincount': 723,
    }, {
        'url': 'https://iwara.tv/profile/user792540',
        'only_matching': True,
    }, {
        'url': 'https://iwara.tv/profile/theblackbirdcalls',
        'only_matching': True,
    }]

    def _entries(self, playlist_id, user_id, page):
        videos = self._download_json(
            'https://api.iwara.tv/videos', playlist_id,
            note=f'Downloading page {page}',
            query={
                'page': page,
                'sort': 'date',
                'user': user_id,
                'limit': self._PER_PAGE,
            })
        yield from (
            self.url_result(f'https://iwara.tv/video/{x}')
            for x in traverse_obj(videos, ('results', ..., 'id')))

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        user_info = self._download_json(
            f'https://api.iwara.tv/profile/{playlist_id}', playlist_id,
            note='Requesting user info')
        user_id = traverse_obj(user_info, ('user', 'id'))

        return self.playlist_result(
            OnDemandPagedList(
                functools.partial(self._entries, playlist_id, user_id),
                self._PER_PAGE),
            playlist_id, traverse_obj(user_info, ('user', 'name')))

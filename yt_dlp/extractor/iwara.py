import itertools
import re
import urllib.parse
import hashlib

from .common import InfoExtractor
from ..utils import (
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
            }),
            'formats': list(self._extract_formats(video_id, video_data.get('fileUrl'))),
        }


class IwaraUserIE(IwaraBaseIE):
    _VALID_URL = fr'{IwaraBaseIE._BASE_REGEX}/users/(?P<id>[^/?#&]+)'
    IE_NAME = 'iwara:user'

    _TESTS = [{
        'note': 'number of all videos page is just 1 page. less than 40 videos',
        'url': 'https://ecchi.iwara.tv/users/infinityyukarip',
        'info_dict': {
            'id': 'infinityyukarip',
        },
        'playlist_mincount': 39,
    }, {
        'note': 'no even all videos page. probably less than 10 videos',
        'url': 'https://ecchi.iwara.tv/users/mmd-quintet',
        'info_dict': {
            'id': 'mmd-quintet',
        },
        'playlist_mincount': 6,
    }, {
        'note': 'has paging. more than 40 videos',
        'url': 'https://ecchi.iwara.tv/users/theblackbirdcalls',
        'info_dict': {
            'id': 'theblackbirdcalls',
        },
        'playlist_mincount': 420,
    }, {
        'note': 'foreign chars in URL. there must be foreign characters in URL',
        'url': 'https://ecchi.iwara.tv/users/ぶた丼',
        'info_dict': {
            'id': 'ぶた丼',
        },
        'playlist_mincount': 170,
    }]

    def _entries(self, playlist_id, base_url):
        webpage = self._download_webpage(
            f'{base_url}/users/{playlist_id}', playlist_id)
        videos_url = self._search_regex(r'<a href="(/users/[^/]+/videos)(?:\?[^"]+)?">', webpage, 'all videos url', default=None)
        if not videos_url:
            yield from self._extract_playlist(base_url, webpage)
            return

        videos_url = urljoin(base_url, videos_url)

        for n in itertools.count(1):
            page = self._download_webpage(
                videos_url, playlist_id, note=f'Downloading playlist page {n}',
                query={'page': str(n - 1)} if n > 1 else {})
            yield from self._extract_playlist(
                base_url, page)

            if f'page={n}' not in page:
                break

    def _real_extract(self, url):
        playlist_id, base_url = self._match_valid_url(url).group('id', 'base_url')
        playlist_id = urllib.parse.unquote(playlist_id)

        return self.playlist_result(
            self._entries(playlist_id, base_url), playlist_id)


class IwaraUser2IE(InfoExtractor):
    IE_NAME = 'iwara:user2'
    _VALID_URL = r'https?://(?:www\.|ecchi\.)?iwara\.tv/users/(?P<id>[^/?&#]+)/videos'
    IE_DESC = False  # do not list this
    _TESTS = [{
        'note': 'number of all videos page is just 1 page',
        'url': 'https://ecchi.iwara.tv/users/infinityyukarip/videos',
        'info_dict': {},
        'add_ie': [IwaraUserIE.ie_key()],
    }, {
        'note': 'no even all videos page',
        'url': 'https://ecchi.iwara.tv/users/mmd-quintet/videos',
        'info_dict': {},
        'add_ie': [IwaraUserIE.ie_key()],
    }, {
        'note': 'has paging',
        'url': 'https://ecchi.iwara.tv/users/theblackbirdcalls/videos',
        'info_dict': {},
        'add_ie': [IwaraUserIE.ie_key()],
    }, {
        'note': 'foreign chars in URL',
        'url': 'https://ecchi.iwara.tv/users/ぶた丼/videos',
        'info_dict': {},
        'add_ie': [IwaraUserIE.ie_key()],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, note='Repairing URL')
        videos_url = self._search_regex(r'<a href="(/users/.+?)"(?: title=".+?")? class="username">', webpage, 'user page url')
        videos_url = urljoin(url, videos_url)
        return self.url_result(videos_url, ie=IwaraUserIE.ie_key())


class IwaraPlaylistIE(InfoExtractor):
    IE_NAME = 'iwara:playlist'
    _VALID_URL = r'https?://(?:www\.|ecchi\.)?iwara\.tv/playlist/(?P<id>[a-zA-Z0-9-]+)'
    _TESTS = [{
        'url': 'https://ecchi.iwara.tv/playlist/best-enf',
        'info_dict': {
            'title': 'Best enf',
            'uploader_id': 'Jared98112',
            'id': 'best-enf',
        },
        'playlist_mincount': 50,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'uploader_id': self._html_search_regex(
                r'<div class="[^"]*views-field-name">\s*<span class="field-content">\s*<h2>(.*?)</h2>',
                webpage, 'uploader_id'),
            'title': self._html_search_regex(
                (r'<h1 class="title"[^>]*?>(.*?)</h1>',
                 r'<title>(.*?)\s+\|\s*Iwara'), webpage, 'title'),
            'entries': (self.url_result(urljoin(url, u))
                        for u in re.findall(
                            r'<h3 class="title">\s*<a href="([^"]+)">', webpage)),
        }

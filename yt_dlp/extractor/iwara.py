import itertools
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    mimetype2ext,
    remove_end,
    strip_or_none,
    unified_strdate,
    url_or_none,
    urljoin,
)


class IwaraIE(InfoExtractor):
    IE_NAME = 'iwara'
    _VALID_URL = r'https?://(?:www\.|ecchi\.)?iwara\.tv/videos/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'http://iwara.tv/videos/amVwUl1EHpAD9RD',
        # md5 is unstable
        'info_dict': {
            'id': 'amVwUl1EHpAD9RD',
            'ext': 'mp4',
            'title': '【MMD R-18】ガールフレンド carry_me_off',
            'age_limit': 18,
            'thumbnail': 'https://i.iwara.tv/sites/default/files/videos/thumbnails/7951/thumbnail-7951_0001.png',
            'uploader': 'Reimu丨Action',
            'upload_date': '20150828',
            'description': 'md5:1d4905ce48c66c9299c617f08e106e0f',
        },
    }, {
        'url': 'http://ecchi.iwara.tv/videos/Vb4yf2yZspkzkBO',
        'md5': '7e5f1f359cd51a027ba4a7b7710a50f0',
        'info_dict': {
            'id': '0B1LvuHnL-sRFNXB1WHNqbGw4SXc',
            'ext': 'mp4',
            'title': '[3D Hentai] Kyonyu × Genkai × Emaki Shinobi Girls.mp4',
            'age_limit': 18,
        },
        'add_ie': ['GoogleDrive'],
    }, {
        'url': 'http://www.iwara.tv/videos/nawkaumd6ilezzgq',
        # md5 is unstable
        'info_dict': {
            'id': '6liAP9s2Ojc',
            'ext': 'mp4',
            'age_limit': 18,
            'title': '[MMD] Do It Again Ver.2 [1080p 60FPS] (Motion,Camera,Wav+DL)',
            'description': 'md5:590c12c0df1443d833fbebe05da8c47a',
            'upload_date': '20160910',
            'uploader': 'aMMDsork',
            'uploader_id': 'UCVOFyOSCyFkXTYYHITtqB7A',
        },
        'add_ie': ['Youtube'],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage, urlh = self._download_webpage_handle(url, video_id)

        hostname = urllib.parse.urlparse(urlh.geturl()).hostname
        # ecchi is 'sexy' in Japanese
        age_limit = 18 if hostname.split('.')[0] == 'ecchi' else 0

        video_data = self._download_json('http://www.iwara.tv/api/video/%s' % video_id, video_id)

        if not video_data:
            iframe_url = self._html_search_regex(
                r'<iframe[^>]+src=([\'"])(?P<url>[^\'"]+)\1',
                webpage, 'iframe URL', group='url')
            return {
                '_type': 'url_transparent',
                'url': iframe_url,
                'age_limit': age_limit,
            }

        title = remove_end(self._html_extract_title(webpage), ' | Iwara')

        thumbnail = self._html_search_regex(
            r'poster=[\'"]([^\'"]+)', webpage, 'thumbnail', default=None)

        uploader = self._html_search_regex(
            r'class="username">([^<]+)', webpage, 'uploader', fatal=False)

        upload_date = unified_strdate(self._html_search_regex(
            r'作成日:([^\s]+)', webpage, 'upload_date', fatal=False))

        description = strip_or_none(self._search_regex(
            r'<p>(.+?(?=</div))', webpage, 'description', fatal=False,
            flags=re.DOTALL))

        formats = []
        for a_format in video_data:
            format_uri = url_or_none(a_format.get('uri'))
            if not format_uri:
                continue
            format_id = a_format.get('resolution')
            height = int_or_none(self._search_regex(
                r'(\d+)p', format_id, 'height', default=None))
            formats.append({
                'url': self._proto_relative_url(format_uri, 'https:'),
                'format_id': format_id,
                'ext': mimetype2ext(a_format.get('mime')) or 'mp4',
                'height': height,
                'quality': 1 if format_id == 'Source' else 0,
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'age_limit': age_limit,
            'formats': formats,
            'thumbnail': self._proto_relative_url(thumbnail, 'https:'),
            'uploader': uploader,
            'upload_date': upload_date,
            'description': description,
        }


class IwaraUserIE(InfoExtractor):
    IE_NAME = 'iwara:user'
    _VALID_URL = r'https?://(?:www\.|ecchi\.)?iwara\.tv/users/(?P<id>[^/?&#]+)'
    _TESTS = [{
        # cond: videos < 40
        'note': 'number of all videos page is just 1 page',
        'url': 'https://ecchi.iwara.tv/users/infinityyukarip',
        'info_dict': {
            'title': 'Uploaded videos from Infinity_YukariP',
            'id': 'infinityyukarip',
            'uploader': 'Infinity_YukariP',
            'uploader_id': 'infinityyukarip',
        },
        'playlist_mincount': 39,
    }, {
        # cond: videos < 10?
        'note': 'no even all videos page',
        'url': 'https://ecchi.iwara.tv/users/mmd-quintet',
        'info_dict': {
            'title': 'Uploaded videos from mmd quintet',
            'id': 'mmd-quintet',
            'uploader': 'mmd quintet',
            'uploader_id': 'mmd-quintet',
        },
        'playlist_mincount': 6,
    }, {
        # cond: videos > 40
        'note': 'has paging',
        'url': 'https://ecchi.iwara.tv/users/theblackbirdcalls',
        'info_dict': {
            'title': 'Uploaded videos from TheBlackbirdCalls',
            'id': 'theblackbirdcalls',
            'uploader': 'TheBlackbirdCalls',
            'uploader_id': 'theblackbirdcalls',
        },
        'playlist_mincount': 420,
    }, {
        # cond: foreign chars in URL
        'note': 'foreign chars in URL',
        'url': 'https://ecchi.iwara.tv/users/ぶた丼',
        'info_dict': {
            'title': 'Uploaded videos from ぶた丼',
            'id': 'ぶた丼',
            'uploader': 'ぶた丼',
            'uploader_id': 'ぶた丼',
        },
        'playlist_mincount': 170,
    }]

    @classmethod
    def suitable(cls, url):
        return super(IwaraUserIE, cls).suitable(url) and not IwaraUser2IE.suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        videos_url = self._search_regex(r'<a href="(/users/[^/]+/videos)">', webpage, 'all videos url', default=None)

        uploader = self._search_regex(r'<h2>([^<]+?)</h2>', webpage, 'uploader name', default=video_id)
        title = 'Uploaded videos from %s' % uploader

        if not videos_url:
            webpages = [webpage]
        else:
            videos_base_url = urljoin(url, videos_url)

            def do_paging():
                for i in itertools.count():
                    if i == 0:
                        videos_page_url = videos_base_url
                    else:
                        videos_page_url = urljoin(videos_base_url, '?page=%d' % i)
                    videos_webpage = self._download_webpage(videos_page_url, video_id, note='Downloading video list %d' % (i + 1))
                    yield videos_webpage
                    if not '?page=%d' % (i + 1) in videos_webpage:
                        break

            webpages = do_paging()

        results = (
            self.url_result(urljoin(url, x.group(1)))
            for page in webpages
            for x in re.finditer(r'<a href="(/videos/[^"]+)">', page))

        return {
            '_type': 'playlist',
            'entries': results,
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'uploader_id': video_id,
        }


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

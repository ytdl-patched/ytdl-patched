from __future__ import unicode_literals

import itertools
import json

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    clean_html,
    float_or_none,
    int_or_none,
    parse_qs,
    smuggle_url,
    unsmuggle_url,
    time_millis,
    traverse_obj,
)


class HANMIE(InfoExtractor):
    IE_DESC = False
    _VALID_URL = r'https?://(?P<host>(?:www\.)?(?:members\.)?han' \
        r'ime\.tv)/videos/hentai/(?P<id>[a-zA-Z0-9-]+$)'
    _TESTS = [{
        'url': 'https://h' 'a' 'n' 'i' 'm' 'e.tv/videos/hentai/enjo-kouhai-1',
        'md5': 'a3a08ac2180ed75ee731aff92d16f447',
        'info_dict': {
            'id': 'enjo-kouhai-1',
            'ext': 'mp4',
            'title': 'Enjo Kouhai 1',
            'age_limit': 18,
            'upload_date': '20200130',
            'description': 'md5:81b00795abd5ffa50a2e463ea321886e',
            'timestamp': 1580398865,
        }
    }, {
        'url': 'https://h' 'a' 'n' 'i' 'm' 'e.tv/videos/hentai/enjo-kouhai-2',
        'md5': '5fad67745e1ba911c041031d9e1ce2a7',
        'info_dict': {
            'id': 'enjo-kouhai-2',
            'ext': 'mp4',
            'title': 'Enjo Kouhai 2',
            'age_limit': 18,
            'upload_date': '20200228',
            'description': 'md5:5277f19882544683e698b91f9e2634e3',
            'timestamp': 1582850492,
        }
    }, {
        'url': 'https://h' 'a' 'n' 'i' 'm' 'e.tv/videos/hentai/enjo-kouhai-3',
        'md5': 'a3a08ac2180ed75ee731aff92d16f447',
        'info_dict': {
            'id': 'enjo-kouhai-3',
            'ext': 'mp4',
            'title': 'Enjo Kouhai 3',
            'age_limit': 18,
            'upload_date': '20200326',
            'timestamp': 1585237316,
            'description': 'md5:0d67e22b89a5f7e1ca079d974019d08d',
        }
    }, {
        'url': 'https://h' 'a' 'n' 'i' 'm' 'e.tv/videos/hentai/chizuru-chan-kaihatsu-nikki-1',
        'md5': 'b54b00535369c8cc0ad344cbef3429f5',
        'info_dict': {
            'id': 'chizuru-chan-kaihatsu-nikki-1',
            'ext': 'mp4',
            'title': 'Chizuru-chan Kaihatsu Nikki 1',
            'age_limit': 18,
            'upload_date': '20210930',
            'timestamp': 1633016879,
            'description': 'A serious honor student "Chizuru Shiina" was shunned by her classmates due to her being a teacher\'s pet, but none of that mattered whenever she ran into her favorite teacher that she so deeply admired...',
        }
    }, {
        'url': 'https://h' 'a' 'n' 'i' 'm' 'e.tv/videos/hentai/chizuru-chan-kaihatsu-nikki-2',
        'md5': 'b54b00535369c8cc0ad344cbef3429f5',
        'info_dict': {
            'id': 'chizuru-chan-kaihatsu-nikki-2',
            'ext': 'mp4',
            'title': 'Chizuru-chan Kaihatsu Nikki 2',
            'age_limit': 18,
            'upload_date': '20210930',
            'timestamp': 1633016880,
            'description': 'A serious honor student "Chizuru Shiina" was shunned by her classmates due to her being a teacher\'s pet, but none of that mattered whenever she ran into her favorite teacher that she so deeply admired...',
        }
    }, {
        'url': 'https://h' 'a' 'n' 'i' 'm' 'e.tv/videos/hentai/kutsujoku-2-ep-2',
        'info_dict': {
            'series': 'Kutsujoku 2',
            'episode_number': 2,
        }
    }, {
        'url': 'https://h' 'a' 'n' 'i' 'm' 'e.tv/videos/hentai/doukyuusei-2-ep-7',
        'info_dict': {
            'series': 'Doukyuusei 2',
            'episode_number': 7,
        }
    }]

    @classmethod
    def suitable(cls, url):
        return super(HANMIE, cls).suitable(url) and not HANMPLIE.suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        json_data = self._html_search_regex(r'window\.__NUXT__=(\{.+?});\s*<\/script>', webpage, 'json data')
        json_data = self._parse_json(json_data, video_id)['state']['data']['video']

        formats = []
        streams = traverse_obj(json_data, ('videos_manifest', 'servers', ..., 'streams', ...))
        for stream in streams or []:
            url = stream['url']
            if not url:
                continue
            formats.append({
                'format_id': f'{stream["slug"]}-{stream["id"]}-{stream["server_id"]}',
                'url': url,
                'width': int_or_none(stream['width']),
                'height': int_or_none(stream['height']),
                'ext': 'mp4',
                'protocol': 'm3u8_native',
                'filesize_approx': float_or_none(stream.get('filesize_mbs'), invscale=1000 ** 2),
                'duration': float_or_none(stream.get('duration_in_ms'), 1000),
            })

        hentai_video = traverse_obj(json_data, 'hentai_video')

        title = traverse_obj(hentai_video, 'name', default=video_id)
        series_and_episode = self._search_regex(
            r'(?i)^(.+?)(?:[\s-]*Ep(?:\.|isode)?)?[\s-]*(\d+)$', title, 'series and episode', default=(None, None),
            fatal=False, group=(1, 2))

        release_date = traverse_obj(hentai_video, 'released_at')
        if release_date:
            release_date = release_date[:10].replace('-', '')

        self._sort_formats(formats)
        return {
            'id': video_id,
            'formats': formats,
            'description': clean_html(traverse_obj(hentai_video, 'description')),
            'creator': traverse_obj(hentai_video, 'brand'),
            'title': title,
            'alt_title': traverse_obj(hentai_video, ('titles', ..., 'title'), get_all=False),
            'tags': traverse_obj(hentai_video, ('hentai_tags', ..., 'text')),
            'release_date': release_date,
            'thumbnails': [{
                'url': traverse_obj(hentai_video, 'poster_url'),
                'id': 'poster',
            }, {
                'url': traverse_obj(hentai_video, 'cover_url'),
                'id': 'cover',
            }],

            'series': series_and_episode[0],
            'episode_number': int_or_none(series_and_episode[1]),

            'timestamp': traverse_obj(hentai_video, 'released_at_unix'),
            'view_count': traverse_obj(hentai_video, 'views'),
            'like_count': traverse_obj(hentai_video, 'likes'),
            'dislike_count': traverse_obj(hentai_video, 'dislikes'),
            'age_limit': 18,
        }


class HANMPLIE(InfoExtractor):
    IE_DESC = False
    _VALID_URL = r'https?://(?P<host>(?:www\.)?(?:members\.)?han' \
        r'ime\.tv)/videos/hentai/(?P<vid>[a-zA-Z0-9-]+?)\?playlist_id=(?P<id>[a-zA-Z0-9-]+)'

    def _entries(self, url, host, playlist_id):
        for page_num in itertools.count(1):
            page_data = self._download_json(
                'https://hw.h' 'a' 'n' 'i' 'm' 'e.tv/api/v8/playlist_hentai_videos', playlist_id,
                note='Downloading page %d' % page_num,
                query={
                    'playlist_id': playlist_id,
                    '__order': 'sequence,DESC',
                    '__offset': str(24 * (page_num - 1)),
                    '__count': '24',
                    'personalized': '0',
                }, headers={
                    'X-Signature': 'null',
                    'X-Signature-Version': 'web2',
                    'X-Time': str(int(time_millis() / 1000)),
                    'X-Token': 'null',
                })
            if page_num == 1:
                # yield page_data only once to extract more data in _real_extract
                yield page_data
            videos = page_data['fapi']['data']
            if not videos:
                break
            for vid in videos:
                yield self.url_result(
                    f'https://{host}/videos/hentai/{vid["slug"]}',
                    video_id=vid["slug"], video_title=vid.get('name'))

    def _real_extract(self, url):
        host, video_id, playlist_id = self._match_valid_url(url).group('host', 'vid', 'id')

        if self.get_param('noplaylist'):
            self.to_screen('Downloading just video %s because of --no-playlist' % video_id)
            return self.url_result(f'https://{host}/videos/hentai/{video_id}', ie=HANMIE.ie_key(), video_id=video_id)
        # self.to_screen('Downloading playlist %s; add --no-playlist to just download video %s' % (playlist_id, video_id))

        entries = self._entries(url, host, playlist_id)
        playlist_info = next(entries)['playlist']
        return self.playlist_result(
            entries, playlist_id, playlist_title=playlist_info['title'])


class HANMALLIE(InfoExtractor):
    IE_DESC = False
    _VALID_URL = r'han' \
        'ime-all'

    def _entries(self):
        for i in itertools.count(0):
            page = self._download_json(
                'https://search.htv-services.com/', 'h' 'a' 'n' 'i' 'm' 'e-all',
                note=f'Downloading page {i}', data=json.dumps({
                    'blacklist': [],
                    'brands': [],
                    'order_by': 'created_at_unix',
                    'ordering': 'desc',
                    'page': i,
                    'search_text': '',
                    'tags': [],
                    'tags_mode': 'AND',
                }).encode('utf-8'), headers={
                    'Content-Type': 'application/json;charset=utf-8',
                    'Accept': 'application/json, text/plain, */*',
                    'Origin': 'https://h' 'a' 'n' 'i' 'm' 'e.tv',
                })
            hits = self._parse_json(page['hits'], 'h' 'a' 'n' 'i' 'm' 'e-all')
            if not hits:
                break
            yield from (self.url_result('https://h' 'a' 'n' 'i' 'm' 'e.tv/videos/hentai/%s' % x['slug']) for x in hits)

    def _real_extract(self, url):
        return self.playlist_result(self._entries())


class GANMIE(InfoExtractor):
    IE_DESC = False
    _VALID_URL = r'https?://gog' 'oan' \
        r'ime\.be/watch/(?P<id>[^/]+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        json_ld = self._search_json_ld(webpage, video_id)

        embed_vids = self._search_regex(
            (r'(?x)"embedUrl": "(https?://vids[^"]+?)",',
             r'(?x)data-embed="(https?://vids[^"]+?)"'),
            webpage, 'embed player url')
        if not embed_vids:
            raise ExtractorError('Boomer moment')
        embed_vids = smuggle_url(embed_vids, {
            'referrer': url,
        })

        json_ld.update({
            '_type': 'url_transparent',
            'url': embed_vids,
            'ie_key': VDSIE.ie_key(),
        })

        return json_ld


class VDSIE(InfoExtractor):
    IE_DESC = False
    _VALID_URL = r'https?://vidst' \
        r'ream\.pro/e/(?P<id>[^/?]+)'

    def _real_extract(self, url):
        url, data = unsmuggle_url(url)
        video_id = self._match_id(url)
        referrer = traverse_obj(data, 'referrer', expected_type=compat_str)
        request_header = {}
        if referrer:
            request_header['Referer'] = referrer
        origin_domain = traverse_obj(parse_qs(url), ('domain', 0))

        webpage = self._download_webpage(
            url, video_id, headers=request_header)
        title = self._html_extract_title(webpage, video_id)
        skey = self._search_regex(
            r'window\.skey\s*=\s*(["\'])(?P<skey>[a-zA-Z0-9]+?)\1', webpage, 'skey',
            group='skey')

        info_response = self._download_json(
            f'https://v' 'idst' f'ream.pro/info/{video_id}', video_id,
            query={
                'domain': origin_domain,
                'skey': skey,
            }, headers={
                'Accept': 'application/json, text/javascript',
                'Referer': url,
                'X-Requested-With': 'XMLHttpRequest',
            })
        if not info_response.get('success'):
            raise ExtractorError('There was an error in info request')

        formats = []
        for fm in traverse_obj(info_response, ('media', 'sources', ..., 'file'), default=[]):
            formats.extend(self._extract_m3u8_formats(fm, video_id, ext='mp4'))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }

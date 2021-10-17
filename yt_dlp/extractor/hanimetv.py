from __future__ import unicode_literals

import itertools
from .common import InfoExtractor
from ..utils import (
    int_or_none,
    smuggle_url,
    traverse_obj,
    unsmuggle_url,
)


class HanimetvIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<host>(?:www\.)?(?:members\.)?hanime\.tv)/videos/hentai/(?P<id>[a-zA-Z0-9-]+$)'
    _TESTS = [{
        'url': 'https://hanime.tv/videos/hentai/enjo-kouhai-1',
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
        'url': 'https://hanime.tv/videos/hentai/enjo-kouhai-2',
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
        'url': 'https://hanime.tv/videos/hentai/enjo-kouhai-3',
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
        'url': 'https://hanime.tv/videos/hentai/chizuru-chan-kaihatsu-nikki-1',
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
        'url': 'https://hanime.tv/videos/hentai/chizuru-chan-kaihatsu-nikki-2',
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
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        url, json_data = unsmuggle_url(url)
        if not json_data:
            webpage = self._download_webpage(url, video_id)
            json_data = self._html_search_regex(r'window\.__NUXT__=(\{.+?});\s*<\/script>', webpage, 'json data')
            json_data = self._parse_json(json_data, video_id)['state']['data']['video']

        formats = []
        streams = traverse_obj(json_data, ('videos_manifest', 'servers', ..., 'streams', ...))
        for stream in streams:
            url = stream['url']
            if not url:
                continue
            formats.append({
                'format_id': '%s-%d-%d' % (stream['slug'], stream['id'], stream['server_id']),
                'url': url,
                'width': int_or_none(stream['width']),
                'height': int_or_none(stream['height']),
                'ext': 'mp4',
                'protocol': 'm3u8',
            })

        title = traverse_obj(json_data, ('hentai_video', 'name'), default=video_id)

        alt_title = traverse_obj(json_data, ('hentai_video', 'titles', ..., 'title'), get_all=False)
        description = traverse_obj(json_data, ('hentai_video', 'description'))
        publisher = traverse_obj(json_data, ('hentai_video', 'brand'))
        tags = traverse_obj(json_data, ('hentai_video', 'hentai_tags', ..., 'text'))
        release_date = traverse_obj(json_data, ('hentai_video', 'released_at'))
        if release_date:
            release_date = release_date[:10].replace('-', '')

        self._sort_formats(formats)
        return {
            'id': video_id,
            'formats': formats,
            'description': description,
            'creator': publisher,
            'title': title,
            'alt_title': alt_title,
            'tags': tags,
            'release_date': release_date,
            'timestamp': traverse_obj(json_data, ('hentai_video', 'released_at_unix')),
            'view_count': traverse_obj(json_data, ('hentai_video', 'views')),
            'like_count': traverse_obj(json_data, ('hentai_video', 'likes')),
            'dislike_count': traverse_obj(json_data, ('hentai_video', 'dislikes')),
            'age_limit': 18,
        }


class HanimetvPlaylistIE(InfoExtractor):
    # NOTE: there must be a better way to do the same
    _VALID_URL = r'https?://(?P<host>(?:www\.)?(?:members\.)?hanime\.tv)/videos/hentai/(?P<vid>.+?)\?playlist_id=(?P<id>[a-zA-Z0-9-]+)'

    def _entries(self, url, host, playlist_id):
        page_url = url
        for page_num in itertools.count(1):
            webpage = self._download_webpage(page_url, playlist_id, note=f'Downloading page {page_num}')

            json_data = self._html_search_regex(r'window\.__NUXT__=(.+?);<\/script>', webpage, 'json data')
            json_data = self._parse_json(json_data, playlist_id)['state']['data']['video']

            curr_vid_url = smuggle_url(f'https://{host}/videos/hentai/' + json_data['hentai_video']['slug'], json_data)
            yield self.url_result(curr_vid_url, ie=HanimetvIE.ie_key())

            next_vid_id = traverse_obj(json_data, ('next_hentai_video', 'slug'))
            if not next_vid_id:
                break

            page_url = f'https://{host}/videos/hentai/{next_vid_id}?playlist_id={playlist_id}'

    def _real_extract(self, url):
        host, playlist_id = self._match_valid_url(url).group('host', 'id')
        return self.playlist_result(self._entries(url, host, playlist_id), playlist_id)

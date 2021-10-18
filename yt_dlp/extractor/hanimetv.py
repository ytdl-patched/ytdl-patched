from __future__ import unicode_literals

import itertools
from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    time_millis,
    traverse_obj,
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

    @classmethod
    def suitable(cls, url):
        return super(HanimetvIE, cls).suitable(url) and not HanimetvPlaylistIE.suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)

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
        series_and_episode = self._search_regex(
            r'^(.+)[\s-](\d+)$', title, 'series and episode', default=(None, None),
            fatal=False, group=(1, 2))

        alt_title = traverse_obj(json_data, ('hentai_video', 'titles', ..., 'title'), get_all=False)
        description = clean_html(traverse_obj(json_data, ('hentai_video', 'description')))
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

            'series': series_and_episode[0],
            'episode_number': int_or_none(series_and_episode[1]),

            'timestamp': traverse_obj(json_data, ('hentai_video', 'released_at_unix')),
            'view_count': traverse_obj(json_data, ('hentai_video', 'views')),
            'like_count': traverse_obj(json_data, ('hentai_video', 'likes')),
            'dislike_count': traverse_obj(json_data, ('hentai_video', 'dislikes')),
            'age_limit': 18,
        }


class HanimetvPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<host>(?:www\.)?(?:members\.)?hanime\.tv)/videos/hentai/(?P<vid>[a-zA-Z0-9-]+?)\?playlist_id=(?P<id>[a-zA-Z0-9-]+)'

    def _entries(self, url, host, playlist_id):
        for page_num in itertools.count(1):
            page_data = self._download_json(
                'https://hw.hanime.tv/api/v8/playlist_hentai_videos', playlist_id,
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
            return self.url_result(f'https://{host}/videos/hentai/{video_id}', ie=HanimetvIE.ie_key(), video_id=video_id)
        # self.to_screen('Downloading playlist %s; add --no-playlist to just download video %s' % (playlist_id, video_id))

        entries = self._entries(url, host, playlist_id)
        playlist_info = next(entries)['playlist']
        return self.playlist_result(
            entries, playlist_id, playlist_title=playlist_info['title'])

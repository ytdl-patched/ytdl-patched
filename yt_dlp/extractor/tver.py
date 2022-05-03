from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    smuggle_url,
    str_or_none,
    traverse_obj,
    try_get,
)


class TVerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tver\.jp/(?:(?P<type>lp|corner|series|episodes?|feature|tokyo2020/video)/)+(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'skip': 'videos are only available for 7 days',
        'url': 'https://tver.jp/episodes/ephss8yveb',
        'info_dict': {
            'title': '#44　料理と値段と店主にびっくり　オモてなしすぎウマい店　2時間SP',
            'description': 'md5:66985373a66fed8ad3cd595a3cfebb13',
        },
        'add_ie': ['BrightcoveNew'],
    }, {
        'skip': 'videos are only available for 7 days',
        'url': 'https://tver.jp/lp/episodes/ep6f16g26p',
        'info_dict': {
            # sorry but this is "correct"
            'title': '4月11日(月)23時06分 ~ 放送予定',
            'description': 'md5:4029cc5f4b1e8090dfc5b7bd2bc5cd0b',
        },
        'add_ie': ['BrightcoveNew'],
    }, {
        'skip': 'videos are only available for 7 days',
        'url': 'https://tver.jp/episodes/ep83nf3w4p',
        'info_dict': {
            "title": "家事ヤロウ!!! 売り場席巻のチーズSP＆財前直見×森泉親子の脱東京暮らし密着！",
            "description": "【毎週火曜 よる7時00分放送　※一部地域を除く】\n\n今スーパーの売り場を席巻中の話題のチーズを紹介！家事ヤロウ3人が売れまくっているチーズでアレンジ飯！爆売れ中のブッラータチーズのフルーツ添え、カロリーオフのチーズで敢えての背徳チーズケーキなど。\nさらに財前直見＆森泉・森パメラ親子の脱東京暮らし完全密着！各々が作る激ウマ料理も大公開！",
            "series": "家事ヤロウ!!!",
            "episode": "売り場席巻のチーズSP＆財前直見×森泉親子の脱東京暮らし密着！",
            "alt_title": "売り場席巻のチーズSP＆財前直見×森泉親子の脱東京暮らし密着！",
            "channel": "テレビ朝日",
            "onair_label": "5月3日(火)放送分",
            "ext_title": "家事ヤロウ!!! 売り場席巻のチーズSP＆財前直見×森泉親子の脱東京暮らし密着！ テレビ朝日 5月3日(火)放送分",
        },
        'add_ie': ['BrightcoveNew'],
    }, {
        'url': 'https://tver.jp/corner/f0103888',
        'only_matching': True,
    }, {
        'url': 'https://tver.jp/lp/f0033031',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'
    _PLATFORM_UID = None
    _PLATFORM_TOKEN = None

    def _real_initialize(self):
        create_response = self._download_json(
            'https://platform-api.tver.jp/v2/api/platform_users/browser/create', None,
            note='Creating session', data=b'device_type=pc', headers={
                'Origin': 'https://s.tver.jp',
                'Referer': 'https://s.tver.jp/',
                'Content-Type': 'application/x-www-form-urlencoded',
            })
        self._PLATFORM_UID = traverse_obj(create_response, ('result', 'platform_uid'))
        self._PLATFORM_TOKEN = traverse_obj(create_response, ('result', 'platform_token'))

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        if video_type not in {'series', 'episodes'}:
            webpage = self._download_webpage(url, video_id, note='Resolving to new URL')
            video_id = self._match_id(self._search_regex(
                (r'canonical"\s*href="(https?://tver\.jp/[^"]+)"', r'&link=(https?://tver\.jp/[^?&]+)[?&]'),
                webpage, 'url regex'))
        video_info = self._download_json(
            f'https://statics.tver.jp/content/episode/{video_id}.json', video_id,
            query={'v': '5'}, headers={
                'Origin': 'https://tver.jp',
                'Referer': 'https://tver.jp/',
            })
        p_id = video_info['video']['accountID']
        r_id = traverse_obj(video_info, ('video', ('videoRefID', 'videoID')), get_all=False)
        if not r_id:
            raise ExtractorError('Failed to extract reference ID for Brightcove')
        if not r_id.isdigit():
            r_id = f'ref:{r_id}'

        additional_info = self._download_json(
            f'https://platform-api.tver.jp/service/api/v1/callEpisode/{video_id}?require_data=mylist,later[epefy106ur],good[epefy106ur],resume[epefy106ur]',
            video_id, fatal=False,
            query={
                'platform_uid': self._PLATFORM_UID,
                'platform_token': self._PLATFORM_TOKEN,
            }, headers={
                'x-tver-platform-type': 'web'
            })

        additional_content_info = traverse_obj(
            additional_info, ('result', 'episode', 'content'),
            get_all=False) or {}
        content_episode = try_get(additional_content_info, lambda x: str_or_none(x.get('title')).rstrip())
        content_series = str_or_none(additional_content_info.get('seriesTitle'))
        content_title = (
            ' '.join(filter(None, [content_series, content_episode])).rstrip()
            or str_or_none(video_info.get('title')))
        content_provider = str_or_none(additional_content_info.get('productionProviderName'))
        content_onair_label = str_or_none(additional_content_info.get('broadcastDateLabel'))

        return {
            '_type': 'url_transparent',
            # standard title: series + episode
            'title': content_title,
            'series': content_series,
            'episode': content_episode,
            'alt_title': content_episode,
            'channel': content_provider,
            # broadcast date or year
            'onair_label': content_onair_label,
            # an another title which is considered "full title" for some viewers
            'ext_title': ' '.join([content_title, content_provider, content_onair_label]),
            'description': str_or_none(video_info.get('description')),
            'url': smuggle_url(
                self.BRIGHTCOVE_URL_TEMPLATE % (p_id, r_id), {'geo_countries': ['JP']}),
            'ie_key': 'BrightcoveNew',
        }

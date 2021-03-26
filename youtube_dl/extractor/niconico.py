# coding: utf-8
from __future__ import unicode_literals

import datetime
import functools
import json
import math
import re
try:
    import dateutil.parser
    HAVE_DATEUTIL = True
except (ImportError, SyntaxError):
    # dateutil is optional
    HAVE_DATEUTIL = False

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    dict_get,
    ExtractorError,
    float_or_none,
    InAdvancePagedList,
    int_or_none,
    parse_duration,
    parse_iso8601,
    remove_start,
    try_get,
    unescapeHTML,
    unified_timestamp,
    urlencode_postdata,
    to_str,
    std_headers,
)
from ..websocket import (
    WebSocket,
    HAVE_WEBSOCKET,
)


class NiconicoIE(InfoExtractor):
    IE_NAME = 'niconico'
    IE_DESC = 'ニコニコ動画'

    _TESTS = [{
        'url': 'http://www.nicovideo.jp/watch/sm22312215',
        'md5': 'd1a75c0823e2f629128c43e1212760f9',
        'info_dict': {
            'id': 'sm22312215',
            'ext': 'mp4',
            'title': 'Big Buck Bunny',
            'thumbnail': r're:https?://.*',
            'uploader': 'takuya0301',
            'uploader_id': '2698420',
            'upload_date': '20131123',
            'timestamp': int,  # timestamp is unstable
            'description': '(c) copyright 2008, Blender Foundation / www.bigbuckbunny.org',
            'duration': 33,
            'view_count': int,
            'comment_count': int,
        },
        'skip': 'Requires an account',
    }, {
        # File downloaded with and without credentials are different, so omit
        # the md5 field
        'url': 'http://www.nicovideo.jp/watch/nm14296458',
        'info_dict': {
            'id': 'nm14296458',
            'ext': 'swf',
            'title': '【鏡音リン】Dance on media【オリジナル】take2!',
            'description': 'md5:689f066d74610b3b22e0f1739add0f58',
            'thumbnail': r're:https?://.*',
            'uploader': 'りょうた',
            'uploader_id': '18822557',
            'upload_date': '20110429',
            'timestamp': 1304065916,
            'duration': 209,
        },
        'skip': 'Requires an account',
    }, {
        # 'video exists but is marked as "deleted"
        # md5 is unstable
        'url': 'http://www.nicovideo.jp/watch/sm10000',
        'info_dict': {
            'id': 'sm10000',
            'ext': 'unknown_video',
            'description': 'deleted',
            'title': 'ドラえもんエターナル第3話「決戦第3新東京市」＜前編＞',
            'thumbnail': r're:https?://.*',
            'upload_date': '20071224',
            'timestamp': int,  # timestamp field has different value if logged in
            'duration': 304,
            'view_count': int,
        },
        'skip': 'Requires an account',
    }, {
        'url': 'http://www.nicovideo.jp/watch/so22543406',
        'info_dict': {
            'id': '1388129933',
            'ext': 'mp4',
            'title': '【第1回】RADIOアニメロミックス ラブライブ！～のぞえりRadio Garden～',
            'description': 'md5:b27d224bb0ff53d3c8269e9f8b561cf1',
            'thumbnail': r're:https?://.*',
            'timestamp': 1388851200,
            'upload_date': '20140104',
            'uploader': 'アニメロチャンネル',
            'uploader_id': '312',
        },
        'skip': 'The viewing period of the video you were searching for has expired.',
    }, {
        # video not available via `getflv`; "old" HTML5 video
        'url': 'http://www.nicovideo.jp/watch/sm1151009',
        'md5': '8fa81c364eb619d4085354eab075598a',
        'info_dict': {
            'id': 'sm1151009',
            'ext': 'mp4',
            'title': 'マスターシステム本体内蔵のスペハリのメインテーマ（ＰＳＧ版）',
            'description': 'md5:6ee077e0581ff5019773e2e714cdd0b7',
            'thumbnail': r're:https?://.*',
            'duration': 184,
            'timestamp': 1190868283,
            'upload_date': '20070927',
            'uploader': 'denden2',
            'uploader_id': '1392194',
            'view_count': int,
            'comment_count': int,
        },
        'skip': 'Requires an account',
    }, {
        # "New" HTML5 video
        # md5 is unstable
        'url': 'http://www.nicovideo.jp/watch/sm31464864',
        'info_dict': {
            'id': 'sm31464864',
            'ext': 'mp4',
            'title': '新作TVアニメ「戦姫絶唱シンフォギアAXZ」PV 最高画質',
            'description': 'md5:e52974af9a96e739196b2c1ca72b5feb',
            'timestamp': 1498514060,
            'upload_date': '20170626',
            'uploader': 'ゲスト',
            'uploader_id': '40826363',
            'thumbnail': r're:https?://.*',
            'duration': 198,
            'view_count': int,
            'comment_count': int,
        },
        'skip': 'Requires an account',
    }, {
        # Video without owner
        'url': 'http://www.nicovideo.jp/watch/sm18238488',
        'md5': 'd265680a1f92bdcbbd2a507fc9e78a9e',
        'info_dict': {
            'id': 'sm18238488',
            'ext': 'mp4',
            'title': '【実写版】ミュータントタートルズ',
            'description': 'md5:15df8988e47a86f9e978af2064bf6d8e',
            'timestamp': 1341160408,
            'upload_date': '20120701',
            'uploader': None,
            'uploader_id': None,
            'thumbnail': r're:https?://.*',
            'duration': 5271,
            'view_count': int,
            'comment_count': int,
        },
        'skip': 'Requires an account',
    }, {
        'url': 'http://sp.nicovideo.jp/watch/sm28964488?ss_pos=1&cp_in=wt_tg',
        'only_matching': True,
    }]

    _VALID_URL = r'https?://(?:(?:www\.|secure\.|sp\.)?nicovideo\.jp/watch|nico\.ms)/(?P<id>(?:[a-z]{2})?[0-9]+)'
    _NETRC_MACHINE = 'niconico'

    def _real_initialize(self):
        self._login()

    def _login(self):
        username, password = self._get_login_info()
        # No authentication to be performed
        if not username:
            return True

        # Log in
        login_ok = True
        login_form_strs = {
            'mail_tel': username,
            'password': password,
        }
        urlh = self._request_webpage(
            'https://account.nicovideo.jp/api/v1/login', None,
            note='Logging in', errnote='Unable to log in',
            data=urlencode_postdata(login_form_strs))
        if urlh is False:
            login_ok = False
        else:
            parts = compat_urllib_parse_urlparse(urlh.geturl())
            if compat_parse_qs(parts.query).get('message', [None])[0] == 'cant_login':
                login_ok = False
        if not login_ok:
            self._downloader.report_warning('unable to log in: bad username or password')
        return login_ok

    def _extract_format_for_quality(self, api_data, video_id, audio_quality, video_quality):
        def yesno(boolean):
            return 'yes' if boolean else 'no'

        def extract_video_quality(video_quality):
            try:
                # Example: 480p | 0.9M
                r = re.match(r'^.*\| ([0-9]*\.?[0-9]*[MK])', video_quality)
                if r is None:
                    # Maybe conditionally throw depending on the settings?
                    return 0

                vbr_with_unit = r.group(1)
                unit = vbr_with_unit[-1]
                video_bitrate = float(vbr_with_unit[:-1])

                if unit == 'M':
                    video_bitrate *= 1000000
                elif unit == 'K':
                    video_bitrate *= 1000

                return video_bitrate
            except BaseException:
                # Should at least log or something here
                return 0

        session_api_data = api_data['media']['delivery']['movie']['session']

        format_id = '-'.join(map(lambda s: remove_start(s['id'], 'archive_'), [video_quality, audio_quality]))

        session_response = self._download_json(
            session_api_data['urls'][0]['url'], video_id,
            query={'_format': 'json'},
            headers={'Content-Type': 'application/json'},
            note='Downloading JSON metadata for %s' % format_id,
            data=json.dumps({
                'session': {
                    'client_info': {
                        'player_id': session_api_data['playerId'],
                    },
                    'content_auth': {
                        'auth_type': session_api_data['authTypes'][session_api_data['protocols'][0]],
                        'content_key_timeout': session_api_data['contentKeyTimeout'],
                        'service_id': 'nicovideo',
                        'service_user_id': session_api_data['serviceUserId']
                    },
                    'content_id': session_api_data['contentId'],
                    'content_src_id_sets': [{
                        'content_src_ids': [{
                            'src_id_to_mux': {
                                'audio_src_ids': [audio_quality['id']],
                                'video_src_ids': [video_quality['id']],
                            }
                        }]
                    }],
                    'content_type': 'movie',
                    'content_uri': '',
                    'keep_method': {
                        'heartbeat': {
                            'lifetime': session_api_data['heartbeatLifetime']
                        }
                    },
                    'priority': session_api_data['priority'],
                    'protocol': {
                        'name': 'http',
                        'parameters': {
                            'http_parameters': {
                                'parameters': {
                                    'http_output_download_parameters': {
                                        'use_ssl': yesno(session_api_data['urls'][0]['isSsl']),
                                        'use_well_known_port': yesno(session_api_data['urls'][0]['isWellKnownPort']),
                                    }
                                }
                            }
                        }
                    },
                    'recipe_id': session_api_data['recipeId'],
                    'session_operation_auth': {
                        'session_operation_auth_by_signature': {
                            'signature': session_api_data['signature'],
                            'token': session_api_data['token'],
                        }
                    },
                    'timing_constraint': 'unlimited'
                }
            }).encode())

        # get heartbeat info
        heartbeat_url = session_api_data['urls'][0]['url'] + '/' + session_response['data']['session']['id'] + '?_format=json&_method=PUT'
        heartbeat_data = json.dumps(session_response['data']).encode()
        # interval, convert milliseconds to seconds, then halve to make a buffer.
        heartbeat_interval = session_api_data['heartbeatLifetime'] / 8000

        resolution = video_quality['metadata'].get('resolution', {})
        vid_quality = video_quality['metadata'].get('bitrate')
        is_low = 'low' in video_quality['id']

        return {
            'url': session_response['data']['session']['content_uri'],
            'format_id': format_id,
            'format_note': 'DMC ' + video_quality['metadata']['label'],
            'ext': 'mp4',  # Session API are used in HTML5, which always serves mp4
            'acodec': 'aac',
            'vcodec': 'h264',  # As far as I'm aware DMC videos can only serve h264/aac combinations
            'abr': float_or_none(audio_quality.get('bitrate'), 1000),
            # So this is kind of a hack; sometimes, the bitrate is incorrectly reported as 0kbs. If this is the case,
            # extract it from the rest of the metadata we have available
            'vbr': float_or_none(vid_quality if vid_quality > 0 else extract_video_quality(video_quality['metadata'].get('label')), 1000),
            'height': resolution.get('height'),
            'width': resolution.get('width'),
            'quality': -2 if is_low else None,
            'heartbeat_url': heartbeat_url,
            'heartbeat_data': heartbeat_data,
            'heartbeat_interval': heartbeat_interval,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Get video webpage. We are not actually interested in it for normal
        # cases, but need the cookies in order to be able to download the
        # info webpage
        webpage, handle = self._download_webpage_handle(
            'http://www.nicovideo.jp/watch/' + video_id, video_id)
        if video_id.startswith('so'):
            video_id = self._match_id(handle.geturl())

        api_data = self._parse_json(self._html_search_regex(
            'data-api-data="([^"]+)"', webpage,
            'API data', default='{}'), video_id)

        if True:
            # keep this section indented for mergeability
            formats = []

            def get_video_info(items):
                return dict_get(api_data['video'], items)

            # dmc_info = api_data['video'].get('dmcInfo')
            quality_info = api_data['media']['delivery']['movie']
            if quality_info:  # "New" HTML5 videos
                for audio_quality in quality_info['audios']:
                    for video_quality in quality_info['videos']:
                        if not audio_quality['isAvailable'] or not video_quality['isAvailable']:
                            continue
                        formats.append(self._extract_format_for_quality(
                            api_data, video_id, audio_quality, video_quality))

                self._sort_formats(formats)

        # Start extracting information
        title = (
            get_video_info(['originalTitle', 'title'])
            or self._og_search_title(webpage, default=None)
            or self._html_search_regex(
                r'<span[^>]+class="videoHeaderTitle"[^>]*>([^<]+)</span>',
                webpage, 'video title'))

        watch_api_data_string = self._html_search_regex(
            r'<div[^>]+id="watchAPIDataContainer"[^>]+>([^<]+)</div>',
            webpage, 'watch api data', default=None)
        watch_api_data = self._parse_json(watch_api_data_string, video_id) if watch_api_data_string else {}
        video_detail = watch_api_data.get('videoDetail', {})

        thumbnail = (
            self._html_search_regex(r'<meta property="og:image" content="([^"]+)">', webpage, 'thumbnail data', default=None)
            or api_data['video'].get('largeThumbnailURL')
            or api_data['video'].get('thumbnailURL')
            or get_video_info(['largeThumbnailURL', 'thumbnail_url', 'thumbnailURL'])
            or self._html_search_meta('image', webpage, 'thumbnail', default=None))

        match = self._html_search_meta('datePublished', webpage, 'date published', default=None)
        if match:
            timestamp = parse_iso8601(match.replace('+', ':00+'))
        else:
            date = api_data['video']['registeredAt']
            # FIXME see animelover1984/youtube-dl
            if HAVE_DATEUTIL:
                timestamp = math.floor(dateutil.parser.parse(date).timestamp())
            else:
                timestamp = None

        view_count = int_or_none(api_data['video']['count'].get('view'))

        description = (
            api_data['video'].get('description')
            # this cannot be checked before the JSON API check as on community videos the description is simply "community"
            or get_video_info('description'))

        if not timestamp:
            timestamp = (parse_iso8601(get_video_info('first_retrieve'))
                         or unified_timestamp(get_video_info('postedDateTime')))
        if not timestamp:
            match = self._html_search_meta('datePublished', webpage, 'date published', default=None)
            if match:
                timestamp = parse_iso8601(match.replace('+', ':00+'))
        if not timestamp and video_detail.get('postedAt'):
            timestamp = parse_iso8601(
                video_detail['postedAt'].replace('/', '-'),
                delimiter=' ', timezone=datetime.timedelta(hours=9))

        comment_count = (
            api_data['video']['count'].get('comment')
            or try_get(api_data, lambda x: x['thread']['commentCount']))
        if not comment_count:
            match = self._html_search_regex(
                r'>Comments: <strong[^>]*>([^<]+)</strong>',
                webpage, 'comment count', default=None)
            if match:
                comment_count = int_or_none(match.replace(',', ''))

        duration = (
            parse_duration(
                get_video_info('length')
                or self._html_search_meta('video:duration', webpage, 'video duration', default=None))
            or video_detail.get('length')
            or get_video_info('duration'))

        webpage_url = get_video_info('watch_url') or url

        # Note: cannot use api_data.get('owner', {}) because owner may be set to "null"
        # in the JSON, which will cause None to be returned instead of {}.
        owner = try_get(api_data, lambda x: x['owner'], dict) or {}
        uploader_id = get_video_info(['ch_id', 'user_id']) or owner.get('id')
        uploader = get_video_info(['ch_name', 'user_nickname']) or owner.get('nickname')

        tags = api_data['video'].get('tags') or []
        genre = get_video_info('genre')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'description': description,
            'uploader': uploader,
            'timestamp': timestamp,
            'uploader_id': uploader_id,
            'view_count': view_count,
            'tags': tags,
            'genre': genre,
            'comment_count': comment_count,
            'duration': duration,
            'webpage_url': webpage_url,
        }


class NiconicoPlaylistBaseIE(InfoExtractor):
    _PAGE_SIZE = 100

    _API_HEADERS = {
        'X-Frontend-ID': '6',
        'X-Frontend-Version': '0',
        'X-Niconico-Language': 'en-us'
    }

    def _call_api(self, list_id, resource, query):
        "Implement this in child class"
        pass

    def _parse_owner(self, item):
        owner = item.get('owner') or {}
        if owner:
            return {
                'uploader': owner.get('name'),
                'uploader_id': owner.get('id'),
            }
        return {}

    def _fetch_page(self, list_id, page):
        page += 1
        items = self._call_api(list_id, 'page %d' % page, {
            'page': page,
            'pageSize': self._PAGE_SIZE,
        })['items']
        for video in items:
            # this is needed to support both mylist and user
            video = video.get('video', video) or {}
            video_id = video.get('id')
            if not video_id:
                continue
            count = video.get('count') or {}
            get_count = lambda x: int_or_none(count.get(x))
            info = {
                '_type': 'url',
                'id': video_id,
                'title': video.get('title'),
                'url': 'https://www.nicovideo.jp/watch/' + video_id,
                'description': video.get('shortDescription'),
                'duration': int_or_none(video.get('duration')),
                'view_count': get_count('view'),
                'comment_count': get_count('comment'),
                'ie_key': NiconicoIE.ie_key(),
            }
            info.update(self._parse_owner(video))
            yield info


class NiconicoPlaylistIE(NiconicoPlaylistBaseIE):
    IE_NAME = 'niconico:playlist'
    _VALID_URL = r'https?://(?:(?:www\.|sp\.)?nicovideo\.jp|nico\.ms)/(?:user/\d+/)?(?:my/)?mylist/(?P<id>\d+)'

    _TESTS = [{
        'url': 'http://www.nicovideo.jp/mylist/27411728',
        'info_dict': {
            'id': '27411728',
            'title': 'AKB48のオールナイトニッポン',
            'description': 'md5:d89694c5ded4b6c693dea2db6e41aa08',
            'uploader': 'のっく',
            'uploader_id': '805442',
        },
        'playlist_mincount': 225,
    }, {
        'url': 'https://www.nicovideo.jp/user/805442/mylist/27411728',
        'only_matching': True,
    }]

    def _call_api(self, list_id, resource, query):
        return self._download_json(
            'https://nvapi.nicovideo.jp/v2/mylists/' + list_id, list_id,
            'Downloading %s JSON metatdata' % resource, query=query,
            headers=self._API_HEADERS)['data']['mylist']

    def _real_extract(self, url):
        list_id = self._match_id(url)
        mylist = self._call_api(list_id, 'list', {
            'pageSize': 1,
        })
        entries = InAdvancePagedList(
            functools.partial(self._fetch_page, list_id),
            math.ceil(mylist['totalItemCount'] / self._PAGE_SIZE),
            self._PAGE_SIZE)
        result = self.playlist_result(
            entries, list_id, mylist.get('name'), mylist.get('description'))
        result.update(self._parse_owner(mylist))
        return result


class NiconicoUserIE(NiconicoPlaylistBaseIE):
    IE_NAME = 'niconico:user'
    _VALID_URL = r'https?://(?:(?:www\.|sp\.)?nicovideo\.jp|nico\.ms)/user/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.nicovideo.jp/user/17988631',
        'info_dict': {
            'id': '17988631',
            'title': 'USAGE',
        },
        'playlist_mincount': 37,  # as of 2021/01/13
    }, {
        'url': 'https://www.nicovideo.jp/user/805442/',
        'only_matching': True,
    }, {
        'url': 'https://nico.ms/user/805442/',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return super(NiconicoUserIE, cls).suitable(url) and not NiconicoPlaylistIE.suitable(url)

    def _call_api(self, list_id, resource, query):
        return self._download_json(
            'https://nvapi.nicovideo.jp/v1/users/%s/videos' % list_id, list_id,
            'Downloading %s JSON metatdata' % resource, query=query,
            headers=self._API_HEADERS)['data']

    def _real_extract(self, url):
        list_id = self._match_id(url)

        user_webpage = self._download_webpage('https://www.nicovideo.jp/user/%s' % list_id, list_id)
        user_info = self._search_regex(r'<div id="js-initial-userpage-data" .+? data-initial-data="(.+)?"', user_webpage, 'user info', default={})
        user_info = unescapeHTML(user_info)
        user_info = self._parse_json(user_info, list_id)
        user_info = try_get(user_info, lambda x: x['userDetails']['userDetails']['user'], dict) or {}

        mylist = self._call_api(list_id, 'list', {
            'pageSize': 1,
        })
        entries = InAdvancePagedList(
            functools.partial(self._fetch_page, list_id),
            math.ceil(mylist['totalCount'] / self._PAGE_SIZE),
            self._PAGE_SIZE)
        result = self.playlist_result(
            entries, list_id, user_info.get('nickname'), user_info.get('strippedDescription'))
        result.update(self._parse_owner(mylist))
        return result


# cannot use NiconicoPlaylistBaseIE because /series/ has different structure than others
class NiconicoSeriesIE(InfoExtractor):
    IE_NAME = 'niconico:series'
    _VALID_URL = r'https?://(?:(?:www\.|sp\.)?nicovideo\.jp|nico\.ms)/series/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.nicovideo.jp/series/110226',
        'info_dict': {
            'id': '110226',
            'title': 'ご立派ァ！のシリーズ',
        },
        'playlist_mincount': 10,  # as of 2021/03/17
    }, {
        'url': 'https://www.nicovideo.jp/series/12312/',
        'info_dict': {
            'id': '12312',
            'title': 'バトルスピリッツ　お勧めカード紹介(調整中)',
        },
        'playlist_mincount': 97,  # as of 2021/03/17
    }, {
        'url': 'https://nico.ms/series/203559',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        list_id = self._match_id(url)
        webpage = self._download_webpage('https://www.nicovideo.jp/series/%s' % list_id, list_id)

        title = self._search_regex(
            (r'<title>「(.+)（全',
             r'<div class="TwitterShareButton"\s+data-text="(.+)\s+https:'),
            webpage, 'title', fatal=False)
        if title:
            title = unescapeHTML(title)
        playlist = []
        for match in re.finditer(r'<a href="/watch/([a-z0-9]+)" data-href="/watch/\1', webpage):
            playlist.append(self.url_result('https://www.nicovideo.jp/watch/%s' % match.group(1)))
        return self.playlist_result(playlist, list_id, title)


class NiconicoLiveIE(InfoExtractor):
    IE_NAME = 'niconico:live'
    IE_DESC = 'ニコニコ生放送'
    _VALID_URL = r'https?://(?:sp\.)?live2?\.nicovideo\.jp/watch/(?P<id>lv\d+)'

    def _real_extract(self, url):
        if not HAVE_WEBSOCKET:
            raise ExtractorError('Install websockets or websocket_client package via pip, or install websockat program', expected=True)

        video_id = self._match_id(url)
        webpage = self._download_webpage('https://live2.nicovideo.jp/watch/%s' % video_id, video_id)

        embedded_data = self._search_regex(r'<script\s+id="embedded-data"\s*data-props="(.+?)"', webpage, 'embedded data')
        embedded_data = unescapeHTML(embedded_data)
        embedded_data = self._parse_json(embedded_data, video_id)

        ws_url = embedded_data['site']['relive']['webSocketUrl']
        if not ws_url:
            raise ExtractorError('the live hasn\'t started yet or already ended', expected=True)

        self.to_screen('%s: Fetching HLS playlist info via WebSocket' % video_id)
        with WebSocket(ws_url, {
            'Cookie': str(self._get_cookies('https://live2.nicovideo.jp/'))[12:],
            'Origin': 'https://live2.nicovideo.jp',
            'Accept': '*/*',
            'User-Agent': std_headers['User-Agent'],
        }) as ws:
            if self._downloader.params.get('verbose', False):
                self.to_screen('[debug] Sending HLS server request')
            ws.send(r'{"type":"startWatching","data":{"stream":{"quality":"high","protocol":"hls","latency":"high","chasePlay":false},"room":{"protocol":"webSocket","commentable":true},"reconnect":false}}')

            while True:
                recv = to_str(ws.recv()).strip()
                if not recv:
                    continue
                data = self._parse_json(recv, video_id, fatal=False)
                if not data or not isinstance(data, dict):
                    continue
                if data.get('type') == 'stream':
                    if self._downloader.params.get('verbose', False):
                        self.to_screen('[debug] Goodbye.')
                    playlist_data = data
                    break
                elif self._downloader.params.get('verbose', False):
                    if len(recv) > 100:
                        recv = recv[:100] + '...'
                    self.to_screen('[debug] Server said: %s' % recv)

        if not playlist_data:
            raise ExtractorError('Unable to fetch HLS playlist info via WebSocket')
        hls_url = playlist_data['data']['uri']

        title = self._html_search_meta(('og:title', 'twitter:title'), webpage, 'live title', fatal=False)
        formats = self._extract_m3u8_formats(
            hls_url, video_id, ext='mp4', m3u8_id='hls', live=True)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'is_live': True,
        }

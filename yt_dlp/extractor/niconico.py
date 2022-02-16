# coding: utf-8
from __future__ import unicode_literals

import functools
import itertools
import re
import json
import datetime

from .common import InfoExtractor, SearchInfoExtractor
from ..compat import (
    compat_str,
    compat_parse_qs,
    compat_urllib_parse_urlparse,
    compat_HTTPError,
)
from ..neonippori import (
    load_comments,
    convert_niconico_json_to_xml,
)
from ..utils import (
    ExtractorError,
    clean_html,
    float_or_none,
    int_or_none,
    parse_duration,
    parse_iso8601,
    remove_start,
    std_headers,
    str_or_none,
    time_millis,
    traverse_obj,
    try_get,
    unescapeHTML,
    update_url_query,
    urlencode_postdata,
)
from ..websocket import WebSocket


class NiconicoBaseIE(InfoExtractor):
    _API_HEADERS = {
        'X-Frontend-ID': '6',
        'X-Frontend-Version': '0',
        'X-Niconico-Language': 'en-us',
        'Referer': 'https://www.nicovideo.jp/',
        'Origin': 'https://www.nicovideo.jp',
    }

    _KNOWN_PLAYER_SIZE = {
        '16:9': (640, 360),
        '4:3': (480, 360),
    }

    def _parse_player_size(self, spec):
        if not spec:
            return 640, 360
        if spec in self._KNOWN_PLAYER_SIZE:
            return self._KNOWN_PLAYER_SIZE[spec]
        if 'x' in spec:
            w, h = tuple(int_or_none(x) for x in spec.split('x'))
            if w and h:
                return w, h
        return 640, 360


class NiconicoIE(NiconicoBaseIE):
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
    }, {
        'note': 'a video that is only served as an ENCRYPTED HLS.',
        'url': 'https://www.nicovideo.jp/watch/so38016254',
        'only_matching': True,
    }, {
        'url': 'nico:sm25182253',
        'only_matching': True,
    }, {
        'url': 'niconico:sm25182253',
        'only_matching': True,
    }, {
        'url': 'nicovideo:sm25182253',
        'only_matching': True,
    }]

    _URL_BEFORE_ID_PART = r'(?:https?://(?:(?:www\.|secure\.|sp\.)?nicovideo\.jp/watch|nico\.ms)/|nico(?:nico|video)?:)'
    _VALID_URL = r'%s(?P<id>(?P<alphabet>[a-z]{2})?[0-9]+)' % _URL_BEFORE_ID_PART
    _NETRC_MACHINE = 'niconico'
    _COMMENT_API_ENDPOINTS = (
        'https://nvcomment.nicovideo.jp/legacy/api.json',
        'https://nmsg.nicovideo.jp/api.json',)

    @classmethod
    def suitable(cls, url):
        m = cls._match_valid_url(url)
        if not m:
            return False
        if m.group('alphabet') == 'lv':
            # niconico:live should take place
            return False
        # The only case that 'id_alphabet' never matches is channel-belonging video (which usually starts with 'so'),
        # but in this case NiconicoIE can handle it
        return True

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
        self._request_webpage(
            'https://account.nicovideo.jp/login', None,
            note='Acquiring Login session')
        urlh = self._request_webpage(
            'https://account.nicovideo.jp/login/redirector?show_button_twitter=1&site=niconico&show_button_facebook=1', None,
            note='Logging in', errnote='Unable to log in',
            data=urlencode_postdata(login_form_strs),
            headers={
                'Referer': 'https://account.nicovideo.jp/login',
                'Content-Type': 'application/x-www-form-urlencoded',
            })
        if urlh is False:
            login_ok = False
        else:
            parts = compat_urllib_parse_urlparse(urlh.geturl())
            if compat_parse_qs(parts.query).get('message', [None])[0] == 'cant_login':
                login_ok = False
        if not login_ok:
            self.report_warning('unable to log in: bad username or password')
        return login_ok

    def _extract_format_for_quality(
            self, api_data, video_id,
            audio_quality, video_quality,
            dmc_protocol, segment_duration=6000):
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

        format_id = '-'.join(
            [remove_start(s['id'], 'archive_') for s in (video_quality, audio_quality)] + [dmc_protocol])

        extract_m3u8 = False
        if dmc_protocol == 'http':
            protocol = 'http'
            protocol_parameters = {
                'http_output_download_parameters': {
                    'use_ssl': yesno(session_api_data['urls'][0]['isSsl']),
                    'use_well_known_port': yesno(session_api_data['urls'][0]['isWellKnownPort']),
                }
            }
        elif dmc_protocol == 'hls':
            protocol = 'm3u8'
            parsed_token = self._parse_json(session_api_data['token'], video_id)
            encryption = traverse_obj(api_data, ('media', 'delivery', 'encryption'))
            protocol_parameters = {
                'hls_parameters': {
                    'segment_duration': segment_duration,
                    'transfer_preset': '',
                    'use_ssl': yesno(session_api_data['urls'][0]['isSsl']),
                    'use_well_known_port': yesno(session_api_data['urls'][0]['isWellKnownPort']),
                }
            }
            if 'hls_encryption' in parsed_token and encryption:
                protocol_parameters['hls_parameters']['encryption'] = {
                    parsed_token['hls_encryption']: {
                        'encrypted_key': encryption['encryptedKey'],
                        'key_uri': encryption['keyUri'],
                    }
                }
            else:
                protocol = 'm3u8_native'
                extract_m3u8 = True
        else:
            self.report_warning(f'Unknown protocol "{dmc_protocol}" found. Please let us know about this with video ID "{video_id}"')
            self.report_warning("Don't be panic. If the download works, this is mostly harmless.")
            return None

        if True:  # indent this for mergeability
            dmc_data = {
                'session': {
                    'client_info': {
                        'player_id': session_api_data['playerId'],
                    },
                    'content_auth': {
                        'auth_type': session_api_data['authTypes'][dmc_protocol],
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
                                'parameters': protocol_parameters
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
            }

        resolution = video_quality['metadata'].get('resolution', {})
        vid_quality = video_quality['metadata'].get('bitrate')
        is_low = 'low' in video_quality['id']

        return {
            'url': session_api_data['urls'][0]['url'],
            'format_id': format_id,
            'format_note': 'DMC ' + video_quality['metadata']['label'] + ' ' + dmc_protocol.upper(),
            'ext': 'mp4',  # Session API are used in HTML5, which always serves mp4
            'acodec': 'aac',
            'vcodec': 'h264',  # As far as I'm aware DMC videos can only serve h264/aac combinations
            'abr': float_or_none(audio_quality['metadata'].get('bitrate'), 1000),
            # So this is kind of a hack; sometimes, the bitrate is incorrectly reported as 0kbs. If this is the case,
            # extract it from the rest of the metadata we have available
            'vbr': float_or_none(vid_quality if vid_quality > 0 else extract_video_quality(video_quality['metadata'].get('label')), 1000),
            'height': resolution.get('height'),
            'width': resolution.get('width'),
            'quality': -2 if is_low else None,
            'protocol': 'niconico_dmc',
            'expected_protocol': protocol,
            'session_api_data': session_api_data,
            'dmc_data': dmc_data,
            'video_id': video_id,
            'extract_m3u8': extract_m3u8,
            # re-extract when you once got 403 error; happens when -N is used
            'unrecoverable_http_error': (403, ),
            'http_headers': {
                'Origin': 'https://www.nicovideo.jp',
                'Referer': 'https://www.nicovideo.jp/watch/' + video_id,
            }
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Get video webpage. We are not actually interested in it for normal
        # cases, but need the cookies in order to be able to download the
        # info webpage
        try:
            webpage, handle = self._download_webpage_handle(
                'http://www.nicovideo.jp/watch/' + video_id, video_id)
            if video_id.startswith('so'):
                video_id = self._match_id(handle.geturl())

            api_data = self._parse_json(self._html_search_regex(
                'data-api-data="([^"]+)"', webpage,
                'API data', default='{}'), video_id)
        except ExtractorError as e:
            try:
                api_data = self._download_json(
                    'https://www.nicovideo.jp/api/watch/v3/%s?_frontendId=6&_frontendVersion=0&actionTrackId=AAAAAAAAAA_%d' % (video_id, time_millis()), video_id,
                    note='Downloading API JSON', errnote='Unable to fetch data')['data']
            except (ExtractorError, KeyError):
                if not isinstance(e.cause, compat_HTTPError):
                    raise e
                else:
                    e = e.cause
                webpage = e.read().decode('utf-8', 'replace')
                error_msg = self._html_search_regex(
                    r'(?s)<section\s+class="(?:(?:ErrorMessage|WatchExceptionPage-message)\s*)+">(.+?)</section>',
                    webpage, 'error reason', group=1, default=None)
                if not error_msg:
                    raise e
                else:
                    error_msg = re.sub(r'\s+', ' ', error_msg)
                    raise ExtractorError(error_msg, expected=True)

        formats = []

        def get_video_info(items):
            return traverse_obj(api_data, ('video', items))

        # --extractor-args niconico:segment_duration=TIME
        # TIME is in milliseconds. should not be changed unless you're an experienced NicoNico investigator
        segment_duration = try_get(self._configuration_arg('segment_duration'), lambda x: int(x[0])) or 6000
        quality_info = api_data['media']['delivery']['movie']
        session_api_data = quality_info['session']
        for (audio_quality, video_quality, protocol) in itertools.product(quality_info['audios'], quality_info['videos'], session_api_data['protocols']):
            if not audio_quality['isAvailable'] or not video_quality['isAvailable']:
                continue
            fmt = self._extract_format_for_quality(
                api_data, video_id,
                audio_quality, video_quality,
                protocol, segment_duration)
            if fmt:
                formats.append(fmt)

        self._sort_formats(formats)

        all_formats_available = all(
            traverse_obj([quality_info['audios'], quality_info['videos']], (..., ..., 'isAvailable')))

        # Start extracting information
        title = (
            get_video_info(['originalTitle', 'title'])
            or self._og_search_title(webpage, default=None))

        thumbnail = traverse_obj(api_data, ('video', 'thumbnail', 'url'))
        if not thumbnail:
            thumbnail = self._html_search_meta(('image', 'og:image'), webpage, 'thumbnail', default=None)

        view_count = int_or_none(api_data['video']['count'].get('view'))

        description = get_video_info('description')

        timestamp = parse_iso8601(get_video_info('registeredAt'))
        if not timestamp:
            match = self._html_search_meta('video:release_date', webpage, 'date published', default=None)
            if match:
                timestamp = parse_iso8601(match)

        comment_count = traverse_obj(
            api_data,
            ('video', 'count', 'comment'),
            expected_type=int)

        duration = (
            parse_duration(self._html_search_meta('video:duration', webpage, 'video duration', default=None))
            or get_video_info('duration'))

        if url.startswith('http://') or url.startswith('https://'):
            webpage_url = url
        else:
            webpage_url = 'https://www.nicovideo.jp/watch/%s' % video_id

        uploader_id = traverse_obj(api_data, ('owner', 'id'))
        uploader = traverse_obj(api_data, ('owner', 'nickname'))

        # attempt to extract tags in 3 ways
        # you have to request Japanese pages to get tags;
        # NN seems to drop tags data when it's English
        tags = None
        if webpage:
            # use og:video:tag (not logged in)
            og_video_tags = re.finditer(r'<meta\s+property="og:video:tag"\s*content="(.*?)">', webpage)
            tags = list(filter(bool, (clean_html(x.group(1)) for x in og_video_tags)))
            if not tags:
                # use keywords and split with comma (not logged in)
                kwds = self._html_search_meta('keywords', webpage, default=None)
                if kwds:
                    tags = [x for x in kwds.split(',') if x]
        if not tags:
            # find it in json (logged in)
            tags = traverse_obj(api_data, ('tag', 'items', ..., 'name'))

        genre = traverse_obj(api_data, ('genre', 'label'), ('genre', 'key'))

        tracking_id = traverse_obj(api_data, ('media', 'delivery', 'trackingId'))
        if tracking_id:
            tracking_url = update_url_query('https://nvapi.nicovideo.jp/v1/2ab0cbaa/watch', {'t': tracking_id})
            watch_request_response = self._download_json(
                tracking_url, video_id,
                note='Acquiring permission for downloading video', fatal=False,
                headers=self._API_HEADERS)
            if traverse_obj(watch_request_response, ('meta', 'status')) != 200:
                self.report_warning('Failed to acquire permission for playing video. Video download may fail.')

        subtitles = None
        if self._downloader.params.get('getcomments', False) or self._downloader.params.get('writesubtitles', False):
            player_size = try_get(self._configuration_arg('player_size'), lambda x: x[0], compat_str)
            w, h = self._parse_player_size(player_size)

            comment_user_key = traverse_obj(api_data, ('comment', 'keys', 'userKey'))
            user_id_str = session_api_data.get('serviceUserId')

            thread_ids = [x for x in traverse_obj(api_data, ('comment', 'threads')) if x['isActive']]
            raw_danmaku = self._extract_all_comments(video_id, thread_ids, 0, user_id_str, comment_user_key)
            if raw_danmaku:
                raw_danmaku = json.dumps(raw_danmaku)
                danmaku = load_comments(raw_danmaku, 'NiconicoJson', w, h, report_warning=self.report_warning)
                xml_danmaku = convert_niconico_json_to_xml(raw_danmaku)

                subtitles = {
                    'jpn': [{
                        'ext': 'json',
                        'data': raw_danmaku,
                    }, {
                        'ext': 'xml',
                        'data': xml_danmaku,
                    }, {
                        'ext': 'ass',
                        'data': danmaku
                    }],
                }
            else:
                self.report_warning('Failed to get comments. Skipping, but make sure to report it as bugs!')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'all_formats_available': all_formats_available,
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
            'subtitles': subtitles,
        }

    def _extract_all_comments(self, video_id, threads, language_id, user_id, user_key):
        if user_id and user_key:
            # authenticate as an user
            auth_data = {
                'user_id': user_id,
                'userkey': user_key,
            }
        else:
            # user_id field with empty string is still needed
            auth_data = {'user_id': ''}

        # Request Start
        post_data = [{'ping': {'content': 'rs:0'}}]
        for i, thread in enumerate(threads):
            thread_id = thread['id']
            thread_fork = thread['fork']
            # Post Start (2N)
            post_data.append({'ping': {'content': f'ps:{i * 2}'}})
            post_data.append({'thread': {
                'fork': thread_fork,
                'language': language_id,
                'nicoru': 3,
                'scores': 1,
                'thread': thread_id,
                'version': '20090904',
                'with_global': 1,
                **auth_data,
            }})
            # Post Final (2N)
            post_data.append({'ping': {'content': f'pf:{i * 2}'}})

            # Post Start (2N+1)
            post_data.append({'ping': {'content': f'ps:{i * 2 + 1}'}})
            post_data.append({'thread_leaves': {
                # format is '<bottom of minute range>-<top of minute range>:<comments per minute>,<total last comments'
                # unfortunately NND limits (deletes?) comment returns this way, so you're only able to grab the last 1000 per language
                'content': '0-999999:999999,999999,nicoru:999999',
                'fork': thread_fork,
                'language': language_id,
                'nicoru': 3,
                'scores': 1,
                'thread': thread_id,
                **auth_data,
            }})
            # Post Final (2N+1)
            post_data.append({'ping': {'content': f'pf:{i * 2 + 1}'}})
        # Request Final
        post_data.append({'ping': {'content': 'rf:0'}})

        for api_url in self._COMMENT_API_ENDPOINTS:
            try:
                return self._download_json(
                    api_url, video_id,
                    headers={
                        'Referer': 'https://www.nicovideo.jp/watch/%s' % video_id,
                        'Origin': 'https://www.nicovideo.jp',
                        'Content-Type': 'text/plain;charset=UTF-8',
                    },
                    data=json.dumps(post_data).encode(),
                    note='Downloading comments (%s)' % ('jp', 'en', 'cn')[language_id])
            except ExtractorError as e:
                self.report_warning(f'Failed to access endpoint {api_url} .\n{e}')
        return None


class NiconicoPlaylistBaseIE(NiconicoBaseIE):
    _PAGE_SIZE = 100

    _API_HEADERS = {
        'X-Frontend-ID': '6',
        'X-Frontend-Version': '0',
        'X-Niconico-Language': 'en-us'
    }

    def _call_api(self, list_id, resource, query):
        "Implement this in child class"
        pass

    @staticmethod
    def _parse_owner(item):
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
            video = traverse_obj(video, ('video',), (), expected_type=dict)
            video_id = video.get('id')
            if not video_id:
                continue
            count = video.get('count') or {}
            get_count = lambda x: int_or_none(count.get(x))
            yield {
                '_type': 'url',
                'id': video_id,
                'title': video.get('title'),
                'url': 'https://www.nicovideo.jp/watch/' + video_id,
                'description': video.get('shortDescription'),
                'duration': int_or_none(video.get('duration')),
                'view_count': get_count('view'),
                'comment_count': get_count('comment'),
                'ie_key': NiconicoIE.ie_key(),
                **self._parse_owner(video),
            }

    def _entries(self, pagefunc):
        NO_ENTRY = object()
        for i in itertools.count(0):
            r = pagefunc(i)
            n = next(r, NO_ENTRY)
            if n is NO_ENTRY:
                break
            yield n
            yield from r


class NiconicoPlaylistIE(NiconicoPlaylistBaseIE):
    IE_NAME = 'niconico:playlist'
    _VALID_URL = r'https?://(?:(?:www\.|sp\.)?nicovideo\.jp|nico\.ms)/(?:user/\d+/)?(?:my/)?mylist/(?:#/)?(?P<id>\d+)'

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
    }, {
        'url': 'https://www.nicovideo.jp/my/mylist/#/68048635',
        'only_matching': True,
    }]

    def _call_api(self, list_id, resource, query):
        return self._download_json(
            'https://nvapi.nicovideo.jp/v2/mylists/' + list_id, list_id,
            'Downloading %s' % resource, query=query,
            headers=self._API_HEADERS)['data']['mylist']

    def _real_extract(self, url):
        list_id = self._match_id(url)
        mylist = self._call_api(list_id, 'list', {
            'pageSize': 1,
        })
        entries = self._entries(functools.partial(self._fetch_page, list_id))
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
        'url': 'https://www.nicovideo.jp/user/1050860/video',
        'info_dict': {
            'id': '1050860',
            'title': '花たんとかユリカとか✿',
        },
        'playlist_mincount': 165,  # as of 2021/04/04
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
            'Downloading %s' % resource, query=query,
            headers=self._API_HEADERS)['data']

    def _real_extract(self, url):
        list_id = self._match_id(url)

        user_webpage = self._download_webpage('https://www.nicovideo.jp/user/%s' % list_id, list_id)
        user_info = self._search_regex(r'<div id="js-initial-userpage-data" .+? data-initial-data="(.+)?"', user_webpage, 'user info', default={})
        user_info = unescapeHTML(user_info)
        user_info = self._parse_json(user_info, list_id)
        user_info = traverse_obj(user_info, ('userDetails', 'userDetails', 'user')) or {}

        mylist = self._call_api(list_id, 'list', {
            'pageSize': 1,
        })
        entries = self._entries(functools.partial(self._fetch_page, list_id))
        result = self.playlist_result(
            entries, list_id, user_info.get('nickname'), user_info.get('strippedDescription'))
        result.update(self._parse_owner(mylist))
        return result


# cannot use NiconicoPlaylistBaseIE because /series/ has different structure than others
class NiconicoSeriesIE(NiconicoBaseIE):
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
        for match in re.finditer(r'href="/watch/([a-z0-9]+)" data-href="/watch/\1', webpage):
            playlist.append(self.url_result('https://www.nicovideo.jp/watch/%s' % match.group(1), video_id=match.group(1)))
        return self.playlist_result(playlist, list_id, title)


class NiconicoHistoryIE(NiconicoPlaylistBaseIE):
    IE_NAME = 'niconico:history'
    IE_DESC = 'NicoNico user history. Requires cookies.'
    # actual url of history page is "https://www.nicovideo.jp/my/history/video", but /video is omitted to widen matches
    _VALID_URL = r'https?://(?:www\.|sp\.)?nicovideo\.jp/my/history'

    _TESTS = [{
        'note': 'PC page, with /video',
        'url': 'https://www.nicovideo.jp/my/history/video',
        'only_matching': True,
    }, {
        'note': 'PC page, without /video',
        'url': 'https://www.nicovideo.jp/my/history',
        'only_matching': True,
    }, {
        'note': 'mobile page, with /video',
        'url': 'https://sp.nicovideo.jp/my/history/video',
        'only_matching': True,
    }, {
        'note': 'mobile page, without /video',
        'url': 'https://sp.nicovideo.jp/my/history',
        'only_matching': True,
    }]

    def _call_api(self, list_id, resource, query):
        return self._download_json(
            'https://nvapi.nicovideo.jp/v1/users/me/watch/history', 'history',
            'Downloading %s' % resource, query=query,
            headers=self._API_HEADERS)['data']

    def _real_extract(self, url):
        list_id = 'history'
        mylist = self._call_api(list_id, 'list', {
            'pageSize': 1,
        })
        entries = self._entries(functools.partial(self._fetch_page, list_id))
        result = self.playlist_result(entries, list_id)
        result.update(self._parse_owner(mylist))
        return result


class NicovideoSearchBaseIE(InfoExtractor):
    _SEARCH_TYPE = 'search'

    def _entries(self, url, item_id, query=None, note='Downloading page %(page)s'):
        query = query or {}
        pages = [query['page']] if 'page' in query else itertools.count(1)
        for page_num in pages:
            query['page'] = str(page_num)
            webpage = self._download_webpage(url, item_id, query=query, note=note % {'page': page_num})
            results = re.findall(r'(?<=data-video-id=)["\']?(?P<videoid>.*?)(?=["\'])', webpage)
            for item in results:
                yield self.url_result(f'http://www.nicovideo.jp/watch/{item}', 'Niconico', item)
            if not results:
                break

    def _search_results(self, query):
        return self._entries(
            self._proto_relative_url(f'//www.nicovideo.jp/{self._SEARCH_TYPE}/{query}'), query)


class NicovideoSearchIE(NicovideoSearchBaseIE, SearchInfoExtractor):
    IE_DESC = 'Nico video search'
    IE_NAME = 'nicovideo:search'
    _SEARCH_KEY = 'nicosearch'


class NicovideoSearchURLIE(NicovideoSearchBaseIE):
    IE_NAME = f'{NicovideoSearchIE.IE_NAME}_url'
    IE_DESC = 'Nico video search URLs'
    _VALID_URL = r'https?://(?:www\.)?nicovideo\.jp/search/(?P<id>[^?#&]+)?'
    _TESTS = [{
        'url': 'http://www.nicovideo.jp/search/sm9',
        'info_dict': {
            'id': 'sm9',
            'title': 'sm9'
        },
        'playlist_mincount': 40,
    }, {
        'url': 'https://www.nicovideo.jp/search/sm9?sort=h&order=d&end=2020-12-31&start=2020-01-01',
        'info_dict': {
            'id': 'sm9',
            'title': 'sm9'
        },
        'playlist_count': 31,
    }]

    def _real_extract(self, url):
        query = self._match_id(url)
        return self.playlist_result(self._entries(url, query), query, query)


class NicovideoSearchDateIE(NicovideoSearchBaseIE, SearchInfoExtractor):
    IE_DESC = 'Nico video search, newest first'
    IE_NAME = f'{NicovideoSearchIE.IE_NAME}:date'
    _SEARCH_KEY = 'nicosearchdate'
    _TESTS = [{
        'url': 'nicosearchdateall:a',
        'info_dict': {
            'id': 'a',
            'title': 'a'
        },
        'playlist_mincount': 1610,
    }]

    _START_DATE = datetime.date(2007, 1, 1)
    _RESULTS_PER_PAGE = 32
    _MAX_PAGES = 50

    def _entries(self, url, item_id, start_date=None, end_date=None):
        start_date, end_date = start_date or self._START_DATE, end_date or datetime.datetime.now().date()

        # If the last page has a full page of videos, we need to break down the query interval further
        last_page_len = len(list(self._get_entries_for_date(
            url, item_id, start_date, end_date, self._MAX_PAGES,
            note=f'Checking number of videos from {start_date} to {end_date}')))
        if (last_page_len == self._RESULTS_PER_PAGE and start_date != end_date):
            midpoint = start_date + ((end_date - start_date) // 2)
            yield from self._entries(url, item_id, midpoint, end_date)
            yield from self._entries(url, item_id, start_date, midpoint)
        else:
            self.to_screen(f'{item_id}: Downloading results from {start_date} to {end_date}')
            yield from self._get_entries_for_date(
                url, item_id, start_date, end_date, note='    Downloading page %(page)s')

    def _get_entries_for_date(self, url, item_id, start_date, end_date=None, page_num=None, note=None):
        query = {
            'start': str(start_date),
            'end': str(end_date or start_date),
            'sort': 'f',
            'order': 'd',
        }
        if page_num:
            query['page'] = str(page_num)

        yield from super()._entries(url, item_id, query=query, note=note)


class NicovideoTagURLIE(NicovideoSearchBaseIE):
    IE_NAME = 'niconico:tag'
    IE_DESC = 'NicoNico video tag URLs'
    _SEARCH_TYPE = 'tag'
    _VALID_URL = r'https?://(?:www\.)?nicovideo\.jp/tag/(?P<id>[^?#&]+)?'
    _TESTS = [{
        'url': 'https://www.nicovideo.jp/tag/%E3%83%89%E3%82%AD%E3%83%A5%E3%83%A1%E3%83%B3%E3%82%BF%E3%83%AA%E3%83%BC%E6%B7%AB%E5%A4%A2',
        'info_dict': {
            'id': 'ドキュメンタリー淫夢',
            'title': 'ドキュメンタリー淫夢'
        },
        'playlist_mincount': 400,
    }]

    def _real_extract(self, url):
        query = self._match_id(url)
        return self.playlist_result(self._entries(url, query), query, query)


class NiconicoLiveIE(NiconicoBaseIE):
    IE_NAME = 'niconico:live'
    IE_DESC = 'ニコニコ生放送'
    _VALID_URL = r'(?:https?://(?:sp\.)?live2?\.nicovideo\.jp/(?:watch|gate)/|nico(?:nico|video)?:)(?P<id>lv\d+)'
    _FEATURE_DEPENDENCY = ('websocket', )

    _KNOWN_LATENCY = ('high', 'low')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle('https://live2.nicovideo.jp/watch/%s' % video_id, video_id)

        embedded_data = self._search_regex(r'<script\s+id="embedded-data"\s*data-props="(.+?)"', webpage, 'embedded data')
        embedded_data = unescapeHTML(embedded_data)
        embedded_data = self._parse_json(embedded_data, video_id)

        ws_url = embedded_data['site']['relive']['webSocketUrl']
        if not ws_url:
            raise ExtractorError('the live hasn\'t started yet or already ended', expected=True)
        ws_url = update_url_query(ws_url, {
            'frontend_id': '9',
        })

        cookies = try_get(urlh.geturl(), self._get_cookie_header)
        latency = try_get(self._configuration_arg('latency'), lambda x: x[0])
        if latency not in self._KNOWN_LATENCY:
            latency = 'high'

        ws = WebSocket(ws_url, {
            'Cookie': str_or_none(cookies) or '',
            'Origin': 'https://live2.nicovideo.jp',
            'Accept': '*/*',
            'User-Agent': std_headers['User-Agent'],
        })

        self.write_debug('[debug] Sending HLS server request')
        ws.send(json.dumps({
            "type": "startWatching",
            "data": {
                "stream": {
                    "quality": 'abr',
                    "protocol": "hls+fmp4",
                    "latency": latency,
                    "chasePlay": False
                },
                "room": {
                    "protocol": "webSocket",
                    "commentable": True
                },
                "reconnect": False,
            }
        }))

        while True:
            recv = ws.recv()
            if not recv:
                continue
            data = json.loads(recv)
            if not data or not isinstance(data, dict):
                continue
            if data.get('type') == 'stream':
                m3u8_url = data['data']['uri']
                qualities = data['data']['availableQualities']
                break
            elif data.get('type') == 'disconnect':
                self.write_debug(recv)
                raise ExtractorError('Disconnected at middle of extraction')
            elif data.get('type') == 'error':
                self.write_debug(recv)
                message = try_get(data, lambda x: x["body"]["code"], compat_str) or recv
                raise ExtractorError(message)
            elif self.get_param('verbose', False):
                if len(recv) > 100:
                    recv = recv[:100] + '...'
                self.to_screen('[debug] Server said: %s' % recv)

        title = try_get(
            None,
            (lambda x: embedded_data['program']['title'],
             lambda x: self._html_search_meta(('og:title', 'twitter:title'), webpage, 'live title', fatal=False)),
            compat_str)

        formats = self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4', live=True)
        self._sort_formats(formats)
        for fmt, q in zip(formats, reversed(qualities[1:])):
            fmt.update({
                'format_id': q,
                'protocol': 'niconico_live',
                'ws': ws,
                'video_id': video_id,
                'cookies': cookies,
                'live_latency': latency,
            })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'is_live': True,
        }

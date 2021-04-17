# coding: utf-8
from __future__ import unicode_literals, with_statement

import hashlib
import re
import itertools

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urllib_request,
    compat_urlparse,
    compat_str,
)
from ..utils import (
    ExtractorError,
    sanitized_Request, try_get,
    urlencode_postdata,
    to_str,
    std_headers,
)
from ..websocket import (
    WebSocket,
    HAVE_WEBSOCKET,
)


class FC2BaseIE(InfoExtractor):
    _NETRC_MACHINE = 'fc2'

    def _login(self):
        username, password = self._get_login_info()
        if username is None or password is None:
            return False

        # Log in
        login_form_strs = {
            'email': username,
            'password': password,
            'done': 'video',
            'Submit': ' Login ',
        }

        login_data = urlencode_postdata(login_form_strs)
        request = sanitized_Request(
            'https://secure.id.fc2.com/index.php?mode=login&switch_language=en', login_data)

        login_results = self._download_webpage(request, None, note='Logging in', errnote='Unable to log in')
        if 'login=done' not in login_results:
            self.report_warning('unable to log in: bad username or password')
            return False

        # this is also needed
        login_redir = sanitized_Request('http://secure.id.fc2.com/?login=done')
        self._download_webpage(
            login_redir, None, note='Login redirect', errnote='Login redirect failed')

        return True


class FC2IE(FC2BaseIE):
    _VALID_URL = r'^(?:https?://video\.fc2\.com/(?:[^/]+/)*content/|fc2:)(?P<id>[^/]+)'
    IE_NAME = 'fc2'
    _TESTS = [{
        'url': 'http://video.fc2.com/en/content/20121103kUan1KHs',
        'info_dict': {
            'id': '20121103kUan1KHs',
            'ext': 'flv',
            'title': 'Boxing again with Puff',
        },
    }, {
        'url': 'http://video.fc2.com/en/content/20150125cEva0hDn/',
        'info_dict': {
            'id': '20150125cEva0hDn',
            'ext': 'mp4',
        },
        'params': {
            'username': 'ytdl@yt-dl.org',
            'password': '(snip)',
        },
        'skip': 'requires actual password',
    }, {
        'url': 'http://video.fc2.com/en/a/content/20130926eZpARwsF',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._login()
        webpage = None
        if not url.startswith('fc2:'):
            webpage = self._download_webpage(url, video_id)
            self._downloader.cookiejar.clear_session_cookies()  # must clear
            self._login()

        title = None
        thumbnail = None
        if webpage is not None:
            title = self._search_regex(
                r'<h2\s+(?:[a-zA-Z_-]+="[^"]+"\s+)*class="videoCnt_title"(?:[a-zA-Z_-]+="[^"]+"\s+)*>([^<]+)</h2>', webpage, 'Extracting title', video_id)
            thumbnail = self._og_search_thumbnail(webpage)
        refer = url.replace('/content/', '/a/content/') if '/a/content/' not in url else url

        mimi = hashlib.md5((video_id + '_gGddgPfeaf_gzyr').encode('utf-8')).hexdigest()

        formats = []

        info_url = (
            'http://video.fc2.com/ginfo.php?mimi={1:s}&href={2:s}&v={0:s}&fversion=WIN%2011%2C6%2C602%2C180&from=2&otag=0&upid={0:s}&tk=null&'.
            format(video_id, mimi, compat_urllib_request.quote(refer, safe=b'').replace('.', '%2E')))

        info_webpage = self._download_webpage(
            info_url, video_id, note='Downloading flv info page')
        info = compat_urlparse.parse_qs(info_webpage)

        mid = try_get(info, (lambda x: x['mid'][0], lambda x: x['amp;mid'][0]), compat_str)
        if 'err_code' not in info and 'filepath' in info and mid:
            # flv download is not available if err_code is present
            video_url = info['filepath'][0] + '?mid=' + mid
            formats.append({
                'format_id': 'flv',
                'url': video_url,
                'ext': 'flv',
                'protocol': 'http',
            })

        title_info = info.get('title')
        if title_info:
            title = title_info[0]

        info_data = self._download_json(
            'https://video.fc2.com/api/v3/videoplaylist/%s?sh=1&fs=0' % video_id, video_id,
            note='Downloading m3u8 playlist info')
        playlists = info_data.get('playlist') or {}
        for (name, m3u8_url) in playlists.items():
            # m3u8_url may be either HLS playlist or direct MP4 download,
            #  but ffmpeg accepts both
            # so use m3u8 rather than http or m3u8_native
            formats.append({
                'format_id': 'hls-%s' % name,
                'url': 'https://video.fc2.com%s' % m3u8_url,
                'ext': 'mp4',
                'protocol': 'm3u8',
            })

        if not formats:
            raise ExtractorError('Cannot download file. Are you logged in?')

        if not title:
            title = 'FC2 video %s' % video_id

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
        }


class FC2EmbedIE(InfoExtractor):
    _VALID_URL = r'https?://video\.fc2\.com/flv2\.swf\?(?P<query>.+)'
    IE_NAME = 'fc2:embed'

    _TEST = {
        'url': 'http://video.fc2.com/flv2.swf?t=201404182936758512407645&i=20130316kwishtfitaknmcgd76kjd864hso93htfjcnaogz629mcgfs6rbfk0hsycma7shkf85937cbchfygd74&i=201403223kCqB3Ez&d=2625&sj=11&lang=ja&rel=1&from=11&cmt=1&tk=TlRBM09EQTNNekU9&tl=プリズン･ブレイク%20S1-01%20マイケル%20【吹替】',
        'info_dict': {
            'id': '201403223kCqB3Ez',
            'ext': 'flv',
            'title': 'プリズン･ブレイク S1-01 マイケル 【吹替】',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        query = compat_parse_qs(mobj.group('query'))

        video_id = query['i'][-1]
        title = query.get('tl', ['FC2 video %s' % video_id])[0]

        sj = query.get('sj', [None])[0]
        thumbnail = None
        if sj:
            # See thumbnailImagePath() in ServerConst.as of flv2.swf
            thumbnail = 'http://video%s-thumbnail.fc2.com/up/pic/%s.jpg' % (
                sj, '/'.join((video_id[:6], video_id[6:8], video_id[-2], video_id[-1], video_id)))

        return {
            '_type': 'url_transparent',
            'ie_key': FC2IE.ie_key(),
            'url': 'fc2:%s' % video_id,
            'title': title,
            'thumbnail': thumbnail,
        }


class FC2UserIE(FC2BaseIE):
    _VALID_URL = r'^https?://video\.fc2\.com/(?P<extra>(?:[^/]+/)*)account/(?P<id>\d+)'
    IE_NAME = 'fc2:user'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        extra = mobj.group('extra') or ''
        user_id = mobj.group('id')
        self._login()

        results = []
        uploader_name = None
        for page in itertools.count(1):
            webpage = self._download_webpage(
                'https://video.fc2.com/%saccount/%s/content?page=%d' % (extra, user_id, page), user_id,
                note='Downloading page %d' % page)
            uploader_name = uploader_name or self._search_regex(r'<span\s+class="memberName">(.+?)</span>', webpage, 'uploader name', fatal=False, group=1)
            videos = [self.url_result(x.group(1)) for x in re.finditer(r'<a\s+href="(https://video\.fc2\.com/(?:[^/]+/)*content/\d{8}[a-zA-Z0-9]+)"\s*class="c-boxList-111_video_ttl"', webpage)]
            if not videos:
                break
            results.extend(videos)

        return self.playlist_result(results, user_id, uploader_name)


class FC2LiveIE(InfoExtractor):
    _VALID_URL = r'^https?://live\.fc2\.com/(?P<id>\d+)'
    IE_NAME = 'fc2:live'
    _WORKING = False

    # TODO: split this extractor into separate file
    def _real_extract(self, url):
        if not HAVE_WEBSOCKET:
            raise ExtractorError('Install websockets or websocket_client package via pip, or install websockat program', expected=True)
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://live.fc2.com/%s/' % video_id, video_id)

        # self._download_json(
        #     'https://live.fc2.com/api/userInfo.php', video_id, note='Downloading userInfo.php',
        #     data=b'', headers={'X-Requested-With': 'XMLHttpRequest'})
        # self._download_json(
        #     'https://live.fc2.com/contents/userlist.php', video_id, note='Downloading userlist.php',
        #     data=('page=0&channel=%s' % video_id).encode('utf-8'), headers={'X-Requested-With': 'XMLHttpRequest'})
        # self._download_json(
        #     'https://live.fc2.com/api/memberApi.php', video_id, note='Downloading memberApi.php',
        #     data=('channel=1&profile=1&user=1&streamid=%s' % video_id).encode('utf-8'), headers={'X-Requested-With': 'XMLHttpRequest'})
        # self._download_json(
        #     'https://live.fc2.com/api/favoriteManager.php', video_id, note='Downloading favoriteManager.php',
        #     data=('id=%s&mode=check&token=' % video_id).encode('utf-8'), headers={'X-Requested-With': 'XMLHttpRequest'})
        # self._download_json(
        #     'https://live.fc2.com/api/profileInfo.php', video_id, note='Downloading profileInfo.php',
        #     data=('mode=get&userid=%s' % video_id).encode('utf-8'), headers={'X-Requested-With': 'XMLHttpRequest'})
        # self._download_json(
        #     'https://live.fc2.com/api/videoRecList.php', video_id, note='Downloading videoRecList.php',
        #     data=('userid=%s&isadult=0&publish=0&per_page=10&page=1' % video_id).encode('utf-8'), headers={'X-Requested-With': 'XMLHttpRequest'})

        post_dict = {
            'channel_id': video_id,
            'mode': 'play',
            'orz': '',
            'channel_version': '33fe385c-5eed-4e15-bb04-a6b5ae438d8e',
            'client_version': '2.0.0\n [1]',
            'client_type': 'pc',
            'client_app': 'browser_hls',
            'ipv6': '',
        }
        self._set_cookie('live.fc2.com', 'js-player_size', '1')

        # https://live.fc2.com/js/playerVersion/version.txt?0.0674203108942784

        control_server = self._download_json(
            'https://live.fc2.com/api/getControlServer.php', video_id, note='Downloading ControlServer data',
            data=urlencode_postdata(post_dict), headers={'X-Requested-With': 'XMLHttpRequest'})
        post_dict['orz'] = control_server['orz']
        self._set_cookie('live.fc2.com', 'l_ortkn', control_server['orz_raw'])

        ws_url = control_server['url'] + '?control_token=' + control_server['control_token']
        playlist_data = None

        self.to_screen('%s: Fetching HLS playlist info via WebSocket' % video_id)
        with WebSocket(ws_url, {
            'Cookie': str(self._get_cookies('https://live.fc2.com/'))[12:],
            'Origin': 'https://live.fc2.com',
            'Accept': '*/*',
            'User-Agent': std_headers['User-Agent'],
        }) as ws:
            if self._downloader.params.get('verbose', False):
                self.to_screen('[debug] Sending HLS server request')
            ws.send(r'{"name":"get_hls_information","arguments":{},"id":1}')

            while True:
                recv = to_str(ws.recv()).strip()
                if not recv:
                    continue
                data = self._parse_json(recv, video_id, fatal=False)
                if not data or not isinstance(data, dict):
                    continue
                if data.get('name') == '_response_' and data.get('id') == 1:
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
        arguments = playlist_data['arguments']
        playlists = arguments['playlists']
        hls_url = None

        for pl in playlists:
            if pl.get('status') == 0 and 'master_playlist' in pl.get('url'):
                hls_url = pl.get('url')
                break

        if not hls_url:
            raise ExtractorError('Unable to find HLS playlist')

        title = try_get(
            webpage,
            (lambda x: self._html_search_meta(('og:title', 'twitter:title'), x, 'live title', fatal=False).strip('\u3000 ')[1:-1],
             lambda x: self._search_regex((r'<title>[\u3000:space:]*\[(.+?)\]\s*-\s*[^-]+?</title>', r'<p class="c-ctbName">(.+?)</p>'), x, 'live title'),
             ), compat_str)
        description = self._html_search_meta(
            ('description', 'og:description', 'twitter:description'),
            webpage, 'live description', fatal=False)
        formats = self._extract_m3u8_formats(
            hls_url, video_id, ext='mp4', m3u8_id='hls', live=True,
            headers={
                'Origin': 'https://live.fc2.com',
                'Referer': url,
            })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
        }

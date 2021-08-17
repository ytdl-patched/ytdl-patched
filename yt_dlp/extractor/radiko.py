# coding: utf-8
from __future__ import unicode_literals

import re
import base64

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    update_url_query,
    clean_html,
    unified_timestamp,
    time_millis,
)
from ..compat import compat_urllib_parse


class RadikoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radiko\.jp/#!/ts/(?P<station>[A-Z-]+)/(?P<id>\d+)'
    _FULL_KEY = None
    _AUTH_CACHE = ()

    _TESTS = [{
        # QRR (文化放送) station provides <desc>
        'url': 'https://radiko.jp/#!/ts/QRR/20210425101300',
        'only_matching': True,
    }, {
        # FMT (TOKYO FM) station does not provide <desc>
        'url': 'https://radiko.jp/#!/ts/FMT/20210810150000',
        'only_matching': True,
    }, {
        'url': 'https://radiko.jp/#!/ts/JOAK-FM/20210509090000',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        m = self._valid_url_re().match(url)
        station = m.group('station')
        video_id = m.group('id')
        vid_int = unified_timestamp(video_id, False)

        auth_token, area_id = self._auth_client()

        station_program = self._download_xml(
            'https://radiko.jp/v3/program/station/weekly/%s.xml' % station, video_id,
            note='Downloading radio program for %s station' % station)

        prog = None
        for p in station_program.findall('.//prog'):
            ft_str, to_str = p.attrib['ft'], p.attrib['to']
            ft = unified_timestamp(ft_str, False)
            to = unified_timestamp(to_str, False)
            if ft <= vid_int and vid_int < to:
                prog = p
                break
        if not prog:
            raise ExtractorError('Cannot identify radio program to download!')
        assert ft, to

        title = prog.find('title').text
        description = clean_html(prog.find('info').text)
        station_name = station_program.find('.//name').text

        m3u8_playlist_data = self._download_xml(
            'https://radiko.jp/v3/station/stream/pc_html5/%s.xml' % station, video_id,
            note='Downloading m3u8 information')
        m3u8_urls = m3u8_playlist_data.findall('.//url')

        formats = []
        found = set()
        for url_tag in m3u8_urls:
            pcu = url_tag.find('playlist_create_url')
            url_attrib = url_tag.attrib
            playlist_url = update_url_query(pcu.text, {
                'station_id': station,
                'start_at': ft_str,  # begin time of the radio
                'ft': ft_str,  # same as start_id
                'end_at': to_str,  # end time of the radio
                'to': to_str,  # same as end_at
                'seek': video_id,
                'l': '15',
                'lsid': '77d0678df93a1034659c14d6fc89f018',
                'type': 'b',
            })
            if playlist_url in found:
                continue
            else:
                found.add(playlist_url)

            time_to_skip = vid_int - ft
            try:
                subformats = self._extract_m3u8_formats(
                    playlist_url, video_id, ext='mp4', entry_protocol='m3u8',
                    live=True, fatal=False, m3u8_id=None,
                    headers={
                        'X-Radiko-AreaId': area_id,
                        'X-Radiko-AuthToken': auth_token,
                    })
                for sf in subformats:
                    domain = sf['format_id'] = compat_urllib_parse.urlparse(sf['url']).netloc
                    if re.match(r'^[cf]-radiko\.smartstream\.ne\.jp$', domain):
                        sf['preference'] = -100  # they probably goes to different station
                    if url_attrib['timefree'] == '1' and time_to_skip:
                        # sf['format_note'] = 'timefree'
                        sf['start_time'] = time_to_skip
                formats.extend(subformats)
            except ExtractorError:
                pass

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader': station_name,
            'uploader_id': station,
            'formats': formats,
            # we have to mark this live since they behave as if it's a live
            'is_live': True,
        }

    def _auth_client(self):
        if self._AUTH_CACHE:
            return self._AUTH_CACHE

        auth1_handle = self._download_webpage_handle(
            'https://radiko.jp/v2/api/auth1', None, 'Authenticating (1)',
            headers={
                'x-radiko-app': 'pc_html5',
                'x-radiko-app-version': '0.0.1',
                'x-radiko-device': 'pc',
                'x-radiko-user': 'dummy_user',
            })[1]  # response body is completely useless
        auth1_header = auth1_handle.info()

        auth_token = auth1_header['X-Radiko-AuthToken']
        kl = int(auth1_header['X-Radiko-KeyLength'])
        ko = int(auth1_header['X-Radiko-KeyOffset'])
        raw_partial_key = self._extract_full_key()[ko:ko + kl]
        partial_key = base64.b64encode(raw_partial_key).decode()

        area_id = self._download_webpage(
            'https://radiko.jp/v2/api/auth2', None, 'Authenticating (2)',
            headers={
                'x-radiko-device': 'pc',
                'x-radiko-user': 'dummy_user',
                'x-radiko-authtoken': auth_token,
                'x-radiko-partialkey': partial_key,
            }).split(',')[0]

        self._AUTH_CACHE = (auth_token, area_id)
        return self._AUTH_CACHE

    def _extract_full_key(self):
        if self._FULL_KEY:
            return self._FULL_KEY

        jscode = self._download_webpage(
            'https://radiko.jp/apps/js/playerCommon.js?_=%d' % time_millis(), None,
            note='Downloading player js code')
        full_key = self._search_regex(
            (r"RadikoJSPlayer\([^,]*,\s*(['\"])pc_html5\1,\s*(['\"])(?P<fullkey>[0-9a-f]+)\2,\s*{"),
            jscode, 'full key', fatal=False, group='fullkey')

        if full_key:
            full_key = full_key.encode()
        else:  # use full key ever known
            full_key = b'bcd151073c03b352e1ef2fd66c32209da9ca0afa'

        self._FULL_KEY = full_key
        return full_key

# coding: utf-8
from __future__ import unicode_literals

import re
import base64

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    update_url_query,
    clean_html,
)


class RadikoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www.)?radiko\.jp/#!/ts/(?P<station>[A-Z]+)/(?P<video_id>\d+)'
    _PARTIAL_KEY_BASE = b'bcd151073c03b352e1ef2fd66c32209da9ca0afa'

    _TESTS = [{
        'url': 'https://radiko.jp/#!/ts/QRR/20210425101300',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        m = self._valid_url_re().match(url)
        station = m.group('station')
        video_id = m.group('video_id')
        vid_int = int(video_id)

        auth1_handle = self._download_webpage_handle(
            'https://radiko.jp/v2/api/auth1', video_id, 'Authorizing (1)',
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
        raw_partial_key = self._PARTIAL_KEY_BASE[ko:ko + kl]
        partial_key = base64.b64encode(raw_partial_key).decode()

        area_id = self._download_webpage(
            'https://radiko.jp/v2/api/auth2', video_id, 'Authorizing (2)',
            headers={
                'x-radiko-device': 'pc',
                'x-radiko-user': 'dummy_user',
                'x-radiko-authtoken': auth_token,
                'x-radiko-partialkey': partial_key,
            }).split(',')[0]

        station_program = self._download_xml(
            'https://radiko.jp/v3/program/station/weekly/%s.xml' % station, video_id,
            note='Downloading radio program for %s station' % station)

        prog = None
        for p in station_program.findall('.//prog'):
            ft = int(p.attrib['ft'])
            to = int(p.attrib['to'])
            if ft < vid_int and vid_int < to:
                prog = p
                break
        if not prog:
            raise ExtractorError('Cannot identify program to download!')

        ft = prog.attrib['ft']
        to = prog.attrib['to']
        title = prog.find('title').text
        description = clean_html(prog.find('title').text)
        program_description = clean_html(prog.find('info').text)

        m3u8_playlist_data = self._download_webpage(
            'https://radiko.jp/v3/station/stream/pc_html5/%s.xml' % station, video_id,
            note='Downloading m3u8 information')
        m3u8_urls = [x.group(1) for x in re.finditer(r'<playlist_create_url>(.+?)</playlist_create_url>', m3u8_playlist_data)]

        formats = []
        for uuu in m3u8_urls:
            playlist_url = update_url_query(uuu, {
                'station_id': station,
                'start_at': ft,  # begin time of the radio
                'ft': ft,  # same as start_id
                'end_at': to,  # end time of the radio
                'to': to,  # same as end_at
                'seek': video_id,
                'l': '15',
                'lsid': '77d0678df93a1034659c14d6fc89f018',
                'type': 'b',
            })
            try:
                formats.extend(self._extract_m3u8_formats(
                    playlist_url, video_id, ext='mp4', entry_protocol='m3u8',
                    live=True, fatal=False,
                    headers={
                        'X-Radiko-AreaId': area_id,
                        'X-Radiko-AuthToken': auth_token,
                    }))
            except ExtractorError:
                pass

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'program_description': program_description,
            'formats': formats,
            'is_live': True,
        }

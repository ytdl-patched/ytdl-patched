# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    smuggle_url,
    try_get,
    unsmuggle_url,
)

from datetime import datetime
import itertools


class VoicyBaseIE(InfoExtractor):
    # every queries are assumed to be a playlist
    def _extract_from_playlist_data(self, value):
        voice_id = compat_str(value['PlaylistId'])
        upload_date = datetime.strptime(value['Published'], "%Y-%m-%dT%H:%M:%SZ").strftime('%Y%m%d')
        items = [self._extract_single_article(voice_id, voice_data, index) for index, voice_data in enumerate(value['VoiceData'], start=1)]
        result = self.playlist_result(items)
        result.update({
            'id': voice_id,
            'title': compat_str(value['PlaylistName']),
            'uploader': value['SpeakerName'],
            'uploader_id': compat_str(value['SpeakerId']),
            'channel': value['ChannelName'],
            'channel_id': compat_str(value['ChannelId']),
            'upload_date': upload_date,
        })
        return result

    # NOTE: "article" in voicy = "track" in CDs = "chapter" in DVDs
    def _extract_single_article(self, voice_id, entry, index=None):
        formats = self._extract_m3u8_formats(
            entry['VoiceHlsFile'], voice_id, ext='m4a', entry_protocol='m3u8_native',
            m3u8_id='hls', note=None if index is None else 'Downloading information for track %d' % index)
        formats.append({
            'url': entry['VoiceFile'],
            'format_id': 'mp3',
            'ext': 'mp3',
            'vcodec': 'none',
            'acodec': 'mp3',
        })
        self._sort_formats(formats)
        return {
            'id': compat_str(entry['ArticleId']),
            'title': entry['ArticleTitle'],
            'description': entry['MediaName'],
            'voice_id': compat_str(entry['VoiceId']),
            'chapter_id': compat_str(entry['ChapterId']),
            'formats': formats,
        }

    def _call_api(self, url, video_id, **kwargs):
        response = self._download_json(url, video_id, **kwargs)
        if response['Status'] != 0:
            message = try_get(
                response,
                (lambda x: x['Value']['Error']['Message'],
                 lambda x: 'There was a error in the response: %d' % x['Status'],
                 lambda x: 'There was a error in the response'),
                compat_str)
            raise ExtractorError(message, expected=False)
        return response['Value']


class VoicyIE(VoicyBaseIE):
    IE_NAME = 'voicy'
    _VALID_URL = r'https?://voicy\.jp/channel/(?P<channel_id>\d+)/(?P<id>\d+)'
    ARTICLE_LIST_API_URL = 'https://vmw.api.voicy.jp/articles_list?channel_id=%s&pid=%s'
    _TESTS = [{
        'note': 'chomado wa iizo (iitowaittenai)',
        'url': 'https://voicy.jp/channel/1253/122754',
        'info_dict': {
            'id': '122754',
            'title': '1/21(木)声日記：ついに原稿終わった！！',
            'uploader': 'ちょまど@ ITエンジニアなオタク',
            'uploader_id': '7339',
        },
        'playlist_mincount': 9,
    }]

    # every queries are assumed to be a playlist
    def _real_extract(self, url):
        voice_id = self._match_id(url)
        channel_id = compat_str(self._VALID_URL_RE.match(url).group('channel_id'))
        url, article_list = unsmuggle_url(url)
        if not article_list:
            article_list = self._call_api(self.ARTICLE_LIST_API_URL % (channel_id, voice_id), voice_id)
        return self._extract_from_playlist_data(article_list)


class VoicyChannelIE(VoicyBaseIE):
    IE_NAME = 'voicy:channel'
    _VALID_URL = r'https?://voicy\.jp/channel/(?P<id>\d+)'
    PROGRAM_LIST_API_URL = 'https://vmw.api.voicy.jp/program_list/all?channel_id=%s&limit=20&public_type=3%s'
    _TESTS = [{
        'note': 'chomado wa iizo (iitowaittenai)',
        'url': 'https://voicy.jp/channel/1253/',
        'info_dict': {
            'id': '7339',
            'title': 'ゆるふわ日常ラジオ #ちょまラジ',
            'uploader': 'ちょまど@ ITエンジニアなオタク',
            'uploader_id': '7339',
        },
        'playlist_mincount': 54,
    }]

    @classmethod
    def suitable(cls, url):
        return not VoicyIE.suitable(url) and super(VoicyChannelIE, cls).suitable(url)

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        articles = []
        pager = ''
        for count in itertools.count(1):
            article_list = self._call_api(self.PROGRAM_LIST_API_URL % (channel_id, pager), channel_id, note='Paging #%d' % count)
            playlist_data = article_list['PlaylistData']
            if not playlist_data:
                break
            articles.extend(playlist_data)
            last = playlist_data[-1]
            pager = '&pid=%d&p_date=%s&play_count=%s' % (last['PlaylistId'], last['Published'], last['PlayCount'])

        title = try_get(
            articles[0],
            (lambda x: x['ChannelName'],
             lambda x: 'Uploaded from ' % x['SpeakerName'],
             lambda x: 'Channel ID: %s' % channel_id), compat_str)

        urls = [smuggle_url('https://voicy.jp/channel/%s/%d' % (channel_id, value['PlaylistId']), value) for value in articles]
        playlist = [self.url_result(url_, VoicyIE.ie_key()) for url_ in urls]
        result = self.playlist_result(playlist)
        result.update({
            'id': channel_id,
            'title': title,
            'channel': channel_id,
            'channel_id': channel_id,
        })
        return result

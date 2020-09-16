from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
)
from datetime import datetime


class VoicyBaseIE(InfoExtractor):
    # every queries are assumed to be a playlist
    def _extract_from_playlist_data(self, value):
        voice_id = compat_str(value['PlaylistId'])
        upload_date = datetime.strptime(value['Published'], "%Y-%m-%dT%H:%M:%SZ").strftime('%Y%m%d')
        items = [self._extract_single_article(voice_id, voice_data) for voice_data in value['VoiceData']]
        result = self.playlist_result(items)
        result.update({
            'title': compat_str(value['PlaylistName']),
            'uploader': value['SpeakerName'],
            'uploader_id': compat_str(value['SpeakerId']),
            'channel': value['ChannelName'],
            'channel_id': compat_str(value['ChannelId']),
            'playlist_title': value['PlaylistName'],
            'playlist_id': voice_id,
            'upload_date': upload_date,
        })
        return result

    # NOTE: "article" in voicy = "track" in CDs = "chapter" in DVDs
    def _extract_single_article(self, voice_id, entry):
        formats = self._extract_m3u8_formats(
            entry['VoiceHlsFile'], voice_id, ext='m4a', entry_protocol='m3u8_native',
            m3u8_id='hls')
        self._sort_formats(formats)
        return {
            'id': compat_str(entry['ArticleId']),
            'title': entry['ArticleTitle'],
            'description': entry['MediaName'],
            'voice_id': compat_str(entry['VoiceId']),
            'chapter_id': compat_str(entry['ChapterId']),
            'formats': formats,
        }


class VoicyIE(VoicyBaseIE):
    IE_NAME = 'voicy'
    _VALID_URL = r'https?://voicy\.jp/channel/(?P<channel_id>\d+)/(?P<id>\d+)/?'
    ARTICLE_LIST_API_URL = 'https://vmw.api.voicy.jp/articles_list?channel_id=%s&pid=%s'
    _TESTS = []

    # every queries are assumed to be a playlist
    def _real_extract(self, url):
        voice_id = self._match_id(url)
        channel_id = compat_str(self._VALID_URL_RE.match(url).group('channel_id'))
        self._download_webpage(url, voice_id)
        article_list = self._download_json(self.ARTICLE_LIST_API_URL % (channel_id, voice_id), voice_id)

        if article_list['Status'] != 0:
            raise ExtractorError('There is a problem in the status: %d' % article_list['Status'], expected=False)

        value = article_list['Value']
        return self._extract_from_playlist_data(value)


class VoicyChannelIE(VoicyBaseIE):
    IE_NAME = 'voicy:channel'
    _VALID_URL = r'https?://voicy\.jp/channel/(?P<id>\d+)/?'
    PROGRAM_LIST_API_URL = 'https://vmw.api.voicy.jp/program_list?channel_id=%s&limit=20&sort=1&flagPlayedPlaylist=1&public_type=3%s'
    _TESTS = []

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        self.report_warning('Looks like article id part is missing. This will download all articles.', channel_id)
        self._download_webpage(url, channel_id)
        articles = []
        pager = ''
        count = 1
        while True:
            article_list = self._download_json(self.PROGRAM_LIST_API_URL % (channel_id, pager), channel_id, 'Paging #%d' % count)
            if article_list['Status'] != 0:
                raise ExtractorError('There is a problem in the status: %d' % article_list['Status'], expected=False)
            playlist_data = article_list['Value']['PlaylistData']
            if not playlist_data:
                break
            articles.extend(playlist_data)
            last = playlist_data[-1]
            pager = '&pid=%d&p_date=%s&play_count=%s' % (last['PlaylistId'], last['Published'], last['PlayCount'])
            count += 1

        playlist = [self._extract_from_playlist_data(value) for value in articles]
        result = self.playlist_result(playlist)
        result.update({
            'channel': channel_id,
            'channel_id': channel_id,
            'playlist_title': 'Channel ID: %s' % channel_id,
            'playlist_id': channel_id,
        })
        return result

from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
)
from datetime import datetime


class VoicyIE(InfoExtractor):
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
            raise ExtractorError('There is a problem in the status: %d' % article_list['Status'], expected=True)

        value = article_list['Value']

        upload_date = datetime.strptime(value['Published'], "%Y-%m-%dT%H:%M:%SZ").strftime('%Y%m%d')
        items = [self._extract_single_article(voice_id, voice_data) for voice_data in value['VoiceData']]
        result = self.playlist_result(items)
        result.update({
            'title': compat_str(value['PlaylistName']),
            'uploader': compat_str(value['SpeakerName']),
            'uploader_id': compat_str(value['SpeakerId']),
            'channel': compat_str(value['ChannelName']),
            'channel_id': compat_str(value['ChannelId']),
            'playlist_title': compat_str(value['PlaylistName']),
            'playlist_id': compat_str(value['PlaylistId']),
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
            'title': compat_str(entry['ArticleTitle']),
            'description': compat_str(entry['MediaName']),
            'voice_id': compat_str(entry['VoiceId']),
            'chapter_id': compat_str(entry['ChapterId']),
            'formats': formats,
        }

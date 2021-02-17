# coding: utf-8
from __future__ import unicode_literals

import re

from ..compat import (
    compat_urllib_parse_urlencode,
    compat_str,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_filesize,
    str_or_none,
    urlencode_postdata,
)
from .common import InfoExtractor
# keep it sync with extractors.py
from .youtube import (
    YoutubeIE,
    YoutubeFavouritesIE,
    YoutubeHistoryIE,
    YoutubeTabIE,
    YoutubePlaylistIE,
    YoutubeRecommendedIE,
    YoutubeSearchDateIE,
    YoutubeSearchIE,
    # YoutubeSearchURLIE,
    YoutubeSubscriptionsIE,
    YoutubeTruncatedIDIE,
    YoutubeTruncatedURLIE,
    YoutubeYtBeIE,
    YoutubeYtUserIE,
    YoutubeWatchLaterIE,
)


class Y2mateBaseIE(InfoExtractor):
    BASE_IE = InfoExtractor
    PREFIXES = ('y2:', 'y2mate:')

    @classmethod
    def remove_prefix(cls, url):
        for pfx in cls.PREFIXES:
            if not url.startswith(pfx):
                continue
            return url[len(pfx):]
        return url

    @classmethod
    def suitable(cls, url):
        for pfx in cls.PREFIXES:
            if not url.startswith(pfx):
                continue
            return cls.BASE_IE.suitable(url[len(pfx):])
        return False


class Y2mateIE(Y2mateBaseIE):
    BASE_IE = YoutubeIE
    IE_NAME = 'y2mate'

    def _real_extract(self, url):
        video_id = self.BASE_IE._match_id(self.remove_prefix(url))
        self._download_webpage('https://www.y2mate.com/youtube/%s' % video_id, video_id)
        common_headers = {'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        request_data = urlencode_postdata({
            'url': 'https://www.youtube.com/watch?v=%s' % video_id,
            'q_auto': '1',
            'ajax': '1'
        })
        size_specs = self._download_json(
            'https://www.y2mate.com/mates/analyze/ajax', video_id,
            note='Fetching size specs', errnote='This video is unavailable', data=request_data,
            headers=common_headers)
        if size_specs.get('status') != 'success':
            raise ExtractorError('Server responded with status %s' % size_specs.get('status'))
        size_specs = size_specs['result']
        title = self._search_regex(r'<b>(.+?)</b>', size_specs, 'video title', group=1)
        request_id = self._search_regex(r'var k__id\s*=\s*(["\'])(.+?)\1', size_specs, 'request ID', group=2)
        formats = []
        # video    , mp3, audio
        video_table, _, audio_table = re.findall(r'<table\s*.+?>(.+?)</table>', size_specs)

        for rows in re.finditer(r'''(?x)<tr>\s*
                    <td>.+?(\d+p).+?</td>\s* # resolution name
                    <td>(.*?\s*[kMG]?B)</td>\s* # estimate size
                    <td\s*.+?>.+?(?:data-ftype="(.+?)".+?)?(?:data-fquality="(.+?)".+?)?</td>\s* # download button
                </tr>''', video_table):
            format_name, estimate_size, format_ext, request_format = rows.groups()
            estimate_size = re.sub(r'\s*([kMG])B', r'\1iB', estimate_size)
            request_data = urlencode_postdata({
                'type': 'youtube',
                '_id': request_id,
                'v_id': video_id,
                'ajax': '1',
                'token': '',
                'ftype': format_ext,
                'fquality': request_format,
            })
            video_url = None
            for i in range(5):
                url_data = self._download_json(
                    'https://www.y2mate.com/mates/convert', video_id,
                    note='Fetching infomation for %s (%d of 5)' % (format_name, i + 1), data=request_data,
                    headers=common_headers)
                if url_data.get('status') != 'success':
                    self.report_warning('Server responded with status %s' % url_data.get('status'))
                    continue
                video_url = self._search_regex(
                    r'<a\s+(?:[a-zA-Z-_]+=\".+?\"\s+)*href=\"(https?://.+?)\"(?:\s+[a-zA-Z-_]+=\".+?\")*', url_data['result'],
                    'Download url for %s' % format_name, group=1, default=None)
                if video_url:
                    break
                video_url = None

            if not video_url:
                continue

            formats.append({
                'format_id': '%s-%s' % (format_name, format_ext),
                'resolution': format_name,
                'filesize_approx': parse_filesize(estimate_size),
                'ext': format_ext,
                'url': video_url,
                'vcodec': 'unknown',
                'acodec': 'unknown',
                'preference': int_or_none(self._search_regex(r'(\d+)p?', format_name, 'video size', group=1, default=None)),
            })

        for rows in re.finditer(r'''(?x)<tr>\s*
                    <td>.+?(\d+[kMG]?bps).+?</td>\s* # resolution name
                    <td>(.*?\s*[kMG]?B)</td>\s* # estimate size
                    <td\s*.+?>.+?(?:data-ftype="(.+?)".+?)?(?:data-fquality="(.+?)".+?)?</td>\s* # download button
                </tr>''', audio_table):
            format_name, estimate_size, format_ext, request_format = rows.groups()
            estimate_size = re.sub(r'\s*([kMG])B', r'\1iB', estimate_size)
            request_data = {
                'type': 'youtube',
                '_id': request_id,
                'v_id': video_id,
                'ajax': '1',
                'token': '',
                'ftype': format_ext,
                'fquality': request_format,
            }
            video_url = None
            for i in range(5):
                url_data = self._download_json(
                    'https://www.y2mate.com/mates/convert', video_id,
                    note='Fetching infomation for %s (%d of 5)' % (format_name, i + 1), data=compat_urllib_parse_urlencode(request_data).encode('utf-8'),
                    headers=common_headers)
                if url_data.get('status') != 'success':
                    self.report_warning('Server responded with status %s' % url_data.get('status'))
                    continue
                video_url = self._search_regex(
                    r'<a\s+(?:[a-zA-Z-_]+=\".+?\"\s+)*href=\"(https?://.+?)\"(?:\s+[a-zA-Z-_]+=\".+?\")*', url_data['result'],
                    'Download url for %s' % format_name, group=1, default=None)
                if video_url:
                    break
                video_url = None

            if not video_url:
                continue

            formats.append({
                'format_id': '%s-%s' % (format_name, format_ext),
                'resolution': format_name,
                'filesize_approx': parse_filesize(estimate_size),
                'ext': format_ext,
                'url': video_url,
                'vcodec': 'none',
                'acodec': 'unknown',
                'preference': -1,
            })

        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }


def _convert_result(ret):
    if not isinstance(ret, dict):
        return ret

    type = str_or_none(ret.get('_type')) or ''
    if type == 'playlist':
        ret['entries'] = [_convert_result(x) for x in ret['entries']]
    elif type.startswith('url'):
        ret['url'] = 'y2:' + ret['url']

    if 'ie_key' in ret:
        ret['ie_key'] = 'Y2mate' + ret['ie_key'][7:]

    return ret


def ___real_extract(self, url):
    url = self.remove_prefix(url)
    try:  # Pythpn 2.x
        real_extract_func = self.BASE_IE._real_extract.__func__
    except (TypeError, AttributeError):
        real_extract_func = self.BASE_IE._real_extract
    ret = real_extract_func(self, url)
    return _convert_result(ret)


for value in (
    YoutubeFavouritesIE,
    YoutubeHistoryIE,
    YoutubeTabIE,
    YoutubePlaylistIE,
    YoutubeRecommendedIE,
    YoutubeSearchDateIE,
    YoutubeSearchIE,
    YoutubeSubscriptionsIE,
    YoutubeTruncatedIDIE,
    YoutubeTruncatedURLIE,
    YoutubeYtBeIE,
    YoutubeYtUserIE,
    YoutubeWatchLaterIE,
):
    key = value.__name__
    clazz_name = 'Y2mate' + key[7:]
    clazz_dict = {
        'BASE_IE': value,
        '_real_extract': ___real_extract,
    }
    if hasattr(value, 'IE_NAME') and isinstance(value.IE_NAME, compat_str):
        clazz_dict['IE_NAME'] = 'y2mate' + value.IE_NAME[7:]
    if hasattr(value, '_VALID_URL'):
        clazz_dict['_VALID_URL'] = value._VALID_URL

    globals()[clazz_name] = type(clazz_name, (Y2mateBaseIE, value), clazz_dict)

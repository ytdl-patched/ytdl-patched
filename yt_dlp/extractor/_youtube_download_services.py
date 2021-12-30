# automating YouTube downloading services to download deleted videos
import re

from ..compat import compat_urllib_parse_urlencode, compat_str
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_filesize,
    parse_qs,
    urlencode_postdata,
    try_get,
)
from .common import InfoExtractor
from .youtube import YoutubeIE


class CustomPrefixedBaseIE(InfoExtractor):
    BASE_IE = InfoExtractor
    PREFIXES = ()

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


# Y2Mate
class Y2mateIE(CustomPrefixedBaseIE):
    BASE_IE = YoutubeIE
    IE_NAME = 'y2mate'
    PREFIXES = ('y2:', 'y2mate:')
    RUSH_PREFIXES = ('y2r:', 'y2mater:', 'y2materush:')

    def _real_extract(self, url):
        mode = try_get(self._configuration_arg('mode'), lambda x: x[0], compat_str)
        if not mode:
            # backward compatibility
            for p in self.RUSH_PREFIXES:
                if url.startswith(p):
                    mode = 'rush'
                    break
        if not mode:
            mode = 'normal'

        if mode == 'rush':
            self.report_warning('Please run again without rush mode')
            return self._real_extract_rush(url)
        else:
            return self._real_extract_normal(url)

    def _real_extract_normal(self, url):
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
        retries = self._downloader.params.get('extractor_retries', 3)
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
            for i in range(retries):
                url_data = self._download_json(
                    'https://www.y2mate.com/mates/convert', video_id,
                    note='Fetching infomation for %s (%d of %d)' % (format_name, i + 1, retries), data=request_data,
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

            if not video_url or 'app.y2mate.com' in video_url:
                continue

            preference = int_or_none(self._search_regex(r'(\d+)p?', format_name, 'video size', group=1, default=None))
            formats.append({
                'format_id': '%s-%s' % (format_name, format_ext),
                'resolution': format_name,
                'filesize_approx': parse_filesize(estimate_size),
                'ext': format_ext,
                'url': video_url,
                'vcodec': 'unknown',
                'acodec': 'unknown',
                'preference': preference,
                'quality': preference,
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
            for i in range(retries):
                url_data = self._download_json(
                    'https://www.y2mate.com/mates/convert', video_id,
                    note='Fetching infomation for %s (%d of %d)' % (format_name, i + 1, retries), data=compat_urllib_parse_urlencode(request_data).encode('utf-8'),
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

            if not video_url or 'app.y2mate.com' in video_url:
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
                'quality': -1,
            })

        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }

    def _real_extract_rush(self, url):
        video_id = self.BASE_IE._match_id(self.remove_prefix(url))
        info_data = self._download_json('https://bookish-octo-barnacle.vercel.app/api/y2mate/youtube?id=%s' % video_id, video_id)

        for fmt in info_data['formats']:
            estimate_size = fmt['filesize_str']
            estimate_size = re.sub(r'\s*([kMG])B', r'\1iB', estimate_size)
            fmt['filesize_approx'] = parse_filesize(estimate_size)
            del fmt['filesize_str']

        self._sort_formats(info_data['formats'])
        return info_data


# ClipConverter
class ClipConverterIE(CustomPrefixedBaseIE):
    BASE_IE = YoutubeIE
    PREFIXES = ('cc:', 'clipconverter:')

    def _real_extract(self, url):
        video_id = self.BASE_IE._match_id(self.remove_prefix(url))
        post_data = {
            'mediaurl': f"https://www.youtube.com/watch?v={video_id}",
            'service': 'YouTube',
            'ref': '',
            'lang': 'en',
            'client_urlmap': 'none',
            'addon_urlmap': '',
            'cookie': '',
            'addon_cookie': '',
            'addon_title': '',
            'ablock': '1',
            'clientside': '1',
            'addon_page': 'none',
            'addon_browser': '',
            'addon_version': '',
            'filetype': 'MP4',
            'format': '',
            'audiovol': '0',
            'audiochannel': '2',
            'audiobr': '128'
        }
        response = self._download_json(
            'https://www.clipconverter.cc/check.php', video_id, note='Requesting for extraction',
            data=urlencode_postdata(post_data),
            headers={
                'Origin': 'https://www.clipconverter.cc',
                'Referer': 'https://www.clipconverter.cc/2/',
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded',
            })

        formats = []
        for fmt in response.get('url') or []:
            text = fmt.get('text')
            heightp = self._search_regex(r'(\d+p)', text, 'resolution', default='unknown_size')
            fps = self._search_regex(r'(\d+)fps', text, 'framerate', default=None)
            formats.append({
                'format_id': f'{heightp}-{fmt.get("filetype")}',
                'url': fmt.get('url'),
                'filesize': int_or_none(fmt.get('size')),
                'height': int_or_none(heightp[:-1]),
                'ext': try_get(fmt, lambda x: x['filetype'].lower()),
                'fps': int_or_none(fps),
            })

        # convert mode isn't implemented yet; this is just Download mode
        if not formats:
            raise ExtractorError(parse_qs(response['redirect'])['errorstr'][0], expected=True)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': response.get('filename') or response.get('id3title'),
            'uploader': response.get('channel') or response.get('id3artist'),
            'category': response.get('category'),
            'formats': formats,
        }

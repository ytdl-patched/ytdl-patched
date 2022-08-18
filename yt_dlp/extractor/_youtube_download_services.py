# automating YouTube downloading services to download deleted videos
import re

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
    _VALID_URL = r'(?P<id>)'

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

    def _real_extract(self, url):
        video_id = self.BASE_IE._match_id(self.remove_prefix(url))
        self._download_webpage(f'https://www.y2mate.com/youtube/{video_id}', video_id)
        common_headers = {'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        anazylze = self._download_json(
            'https://www.y2mate.com/mates/analyze/ajax', video_id,
            note='Fetching size specs', errnote='This video is unavailable', headers=common_headers,
            form_params={
                'url': f'https://www.youtube.com/watch?v={video_id}',
                'q_auto': '1',
                'ajax': '1'
            })
        if anazylze.get('status') != 'success':
            raise ExtractorError(f'Server responded with status {anazylze.get("status")}')
        size_specs = anazylze['result']
        title = self._search_regex(r'<b>(.+?)</b>', size_specs, 'video title', group=1)
        request_id = self._search_regex(r'var k__id\s*=\s*(["\'])(.+?)\1', size_specs, 'request ID', group=2)
        tables = re.findall(r'<table\s*.+?>(.+?)</table>', size_specs)

        formats = [x for tbl in (tables[0], tables[-1]) for x in self._find_formats(request_id, video_id, common_headers, tbl)]
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }

    def _find_formats(self, request_id, video_id, headers, table):
        for rows in re.finditer(r'''(?x)<tr>\s*
                    <td>.*?(\d+p|\d+[kMG]?bps).*?</td>\s* # resolution name or kbps
                    <td>(.*?\s*[kMG]?B)</td>\s* # estimate size
                    <td\s*.+?>.+?(?:data-ftype="(.+?)".+?)?(?:data-fquality="(.+?)".+?)?</td>\s* # download button
                </tr>''', table):
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
            for retry in self.RetryManager(fatal=False):
                try:
                    url_data = self._download_json(
                        'https://www.y2mate.com/mates/convert', video_id,
                        note=f'Fetching infomation for {format_name} ({format_ext})', data=request_data,
                        headers=headers)
                except ExtractorError as e:
                    retry.error = e
                    continue
                if url_data.get('status') != 'success':
                    retry.error = ExtractorError(f'Server responded with status {url_data.get("status")}', expected=True)
                    continue
                try:
                    video_url = self._search_regex(
                        r'<a\s+(?:[a-zA-Z-_]+=\".+?\"\s+)*href=\"(https?://.+?)\"(?:\s+[a-zA-Z-_]+=\".+?\")*', url_data['result'],
                        f'Download url for {format_name}', group=1, default=None)
                except ExtractorError as e:
                    retry.error = e
                    continue

            if not video_url or 'app.y2mate.com' in video_url:
                continue

            yield {
                'format_id': f'{format_name}-{format_ext}',
                'filesize_approx': parse_filesize(estimate_size),
                'ext': format_ext,
                'url': video_url,
                'acodec': 'unknown',

                **({
                    # audio
                    'vcodec': 'none',
                    'abr': int_or_none(parse_filesize(format_name[:-2]), scale=1000),
                } if format_name.endswith('bps') else {
                    # video
                    'vcodec': 'unknown',
                    'height': int_or_none(format_name[:-1]),
                    'resolution': format_name,
                }),
            }


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
            form_params=post_data,
            headers={
                'Origin': 'https://www.clipconverter.cc',
                'Referer': 'https://www.clipconverter.cc/2/',
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded',
            })

        formats = []
        for fmt in response.get('url') or []:
            text = fmt.get('text')
            resol = self._search_regex(r'(\d+p)', text, 'resolution', default=None)
            fps = self._search_regex(r'(\d+)fps', text, 'framerate', default=None)
            filetype = try_get(fmt, lambda x: x['filetype'])
            height = int_or_none(resol[:-1]) if resol else None
            is_vonly = filetype == 'webm' or (height and height > 1080)
            formats.append({
                'format_id': f'{resol}-{filetype}',
                'url': fmt.get('url'),
                'filesize': int_or_none(fmt.get('size')),
                'resolution': resol,
                'height': height,
                'ext': filetype.lower() if filetype else None,
                'fps': int_or_none(fps),
                'acodec': 'none' if is_vonly else None,
                'quality': -10 if is_vonly else None
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


# Combined
class YtAlternateIE(CustomPrefixedBaseIE):
    BASE_IE = YoutubeIE
    PREFIXES = ('yta:', 'dig:', 'ytalternate:')
    # _CALL_IES = ('Y2mate', 'ClipConverter', 'Youtube')
    _CALL_IES = ('ClipConverter', 'Y2mate')

    def _real_extract(self, url):
        video_id = self.BASE_IE._match_id(self.remove_prefix(url))
        infodicts = []
        for exn in self._CALL_IES:
            try:
                dct = self._downloader.get_info_extractor(exn).extract(video_id)
                for fmt in dct['formats']:
                    fmt['format_note'] = exn
                infodicts.append(dct)
            except KeyboardInterrupt:
                raise
            except BaseException as ex:
                self.report_warning(f'{ex}')

        if not infodicts:
            raise ExtractorError('Extraction failed.', expected=True)
        return self._merge_video_infodicts(infodicts)

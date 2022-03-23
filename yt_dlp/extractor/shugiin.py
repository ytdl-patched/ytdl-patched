# coding: utf-8
from __future__ import unicode_literals

import re

from ..utils import (
    clean_html,
    float_or_none,
    int_or_none
)

from .common import InfoExtractor


def _parse_japanese_date(text):
    if not text:
        return None
    ERA_TABLE = {
        '明治': 1868,
        '大正': 1912,
        '昭和': 1926,
        '平成': 1989,
        '令和': 2019,
    }
    ERA_RE = '|'.join(map(re.escape, ERA_TABLE.keys()))
    mobj = re.search(rf'({ERA_RE})?(\d+)年(\d+)月(\d+)日', re.sub(r'[\s\u3000]+', '', text))
    if not mobj:
        return None
    era, year, month, day = mobj.groups()
    year, month, day = map(int, (year, month, day))
    if era:
        # example input: 令和5年3月34日
        # even though each era have their end, don't check here
        year += ERA_TABLE[era]
    return '%04d%02d%02d' % (year, month, day)


def _parse_japanese_duration(text):
    if not text:
        return None
    mobj = re.search(r'(?:(\d+)日間?)?(?:(\d+)時間?)?(?:(\d+)分)?(?:(\d+)秒)?', re.sub(r'[\s\u3000]+', '', text))
    if not mobj:
        return None
    days, hours, mins, secs = map(int_or_none, mobj.groups())

    duration = 0
    if secs:
        duration += float(secs)
    if mins:
        duration += float(mins) * 60
    if hours:
        duration += float(hours) * 60 * 60
    if days:
        duration += float(days) * 24 * 60 * 60
    return duration


def _get_last(iter):
    obj = None
    for o in iter:
        obj = o
    return obj


class ShugiinItvLiveIE(InfoExtractor):
    # not implemented
    pass


class ShugiinItvVodIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?shugiintv\.go\.jp/(?P<lang>jp|en)/index\.php\?ex=VL(?:\&[^=]+=[^&]*)*\&deli_id=(?P<id>\d+)'
    IE_DESC = '衆議院インターネット審議中継 (ビデオライブラリ)'
    _TESTS = [{
        'url': '',
        'info_dict': {
            'id': '53846',
            'title': 'ウクライナ大統領国会演説（オンライン）',
            'release_date': '20220323',
            'chapters': 'count:4',
        }
    }]

    def _real_extract(self, url):
        lang, video_id = self._match_valid_url(url).group('lang', 'id')
        force_japanese = self._configuration_arg('force_japanese', default=False)
        if lang == 'jp' or force_japanese:
            return self._extract_japanese(video_id)
        else:
            return self._extract_english(video_id)

    def _extract_japanese(self, video_id):
        webpage = self._download_webpage(
            f'https://www.shugiintv.go.jp/jp/index.php?ex=VL&media_type=&deli_id={video_id}', video_id,
            encoding='euc-jp')

        m3u8_url = self._search_regex(
            r'id="vtag_src_base_vod"\s*value="(http.+?\.m3u8)"', webpage, 'm3u8 url')
        m3u8_url = re.sub(r'^http://', 'https://', m3u8_url)
        # I doubt there's also subtitles
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, ext='mp4')
        self._sort_formats(formats)

        title = self._html_search_regex(
            (r'<td\s+align="left">(.+)\s*\(\d+分\)',
             r'<TD.+?<IMG\s*src=".+?/spacer\.gif".+?height="15">(.+?)<IMG'), webpage, 'title', fatal=False)

        release_date = _parse_japanese_date(self._html_search_regex(
            r'開会日</td>\s*<td.+?/td>\s*<TD>(.+?)</TD>',
            webpage, 'title', fatal=False))

        # NOTE: chapters are sparse, because of how the website serves the video
        chapters = []
        for chp in re.finditer(r'<A\s+HREF=".+?php\?.+?&deli_id=\d+&time=([\d\.]+)"\s*class="play_vod">(?!<img)(.+)</[Aa]>', webpage):
            chapters.append({
                'title': clean_html(chp.group(2)).strip(),
                'start_time': float_or_none(chp.group(1).strip()),
            })
        # the exact duration of the last chapter is unknown! (we can get at most minutes of granularity)
        for idx, chp in enumerate(chapters[1:]):
            chapters[idx]['end_time'] = chapters[idx + 1]['start_time']

        last_tr = _get_last(re.finditer(r'(?s)<TR\s*class="s14_24">(.+?)</TR>', webpage))
        if last_tr and chapters:
            last_td = _get_last(re.finditer(r'<TD.+?</TD>', last_tr.group(0)))
            if last_td:
                chapters[-1]['end_time'] = chapters[-1]['start_time'] + _parse_japanese_duration(clean_html(last_td.group(0)))

        return {
            'id': video_id,
            'title': title,
            'release_date': release_date,
            'chapters': chapters,
            'formats': formats,
            'subtitles': subtitles,
        }

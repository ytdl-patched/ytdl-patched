from __future__ import unicode_literals

import re
from time import sleep

from .fragment import FragmentFD
from ..downloader import get_suitable_downloader
from ..extractor.youtube import YoutubeIE

from ..utils import (
    urljoin,
    time_millis,
)
from ..compat import compat_urlparse


class YoutubeDlFromStartDashFD(FragmentFD):
    """
    Download YouTube live from the start, to the end. For DASH formats.
    This currently does not handle downloading 2 streams at once.
    """

    FD_NAME = 'ytlivestartdash'

    @staticmethod
    def _manifest_fragments(ie: YoutubeIE, mpd_url, stream_number, fetch_span=5000):
        known_idx = 0
        prev_dl = time_millis()
        while True:
            fmts, _ = ie._extract_mpd_formats_and_subtitles(
                mpd_url, None, note=False, errnote=False, fatal=False)
            if not fmts:
                continue
            fmt_info = next(x for x in fmts if x['manifest_stream_number'] == stream_number)
            fragments = fmt_info['fragments']
            fragment_base_url = fmt_info.get('fragment_base_url')

            last_fragment = fragments[-1]
            last_url = last_fragment.get('url')
            if not last_url:
                assert fragment_base_url
                last_url = urljoin(fragment_base_url, last_fragment['path'])

            last_seq = int(re.search(r'/sq/(\d+)', last_url).group(1))
            for idx in range(known_idx, last_seq):
                seq = idx + 1
                yield {
                    'frag_index': seq,
                    'index': seq,
                    'url': re.sub(r'/sq/\d+', '/sq/%d' % seq, last_url),
                }
            if known_idx == last_seq:
                return
            known_idx = last_seq

            now_time = time_millis()
            if (now_time - prev_dl) < fetch_span:
                sleep((now_time - prev_dl) / 1e3)
            prev_dl = now_time

    def real_download(self, filename, info_dict):
        manifest_url = info_dict.get('manifest_url')
        if not manifest_url:
            self.report_error('URL to MPD manifest is not known; there is a problem in YoutubeIE code')

        stream_number = info_dict.get('manifest_stream_number', 0)
        yie: YoutubeIE = self.ydl.get_info_extractor(YoutubeIE.ie_key())

        real_downloader = get_suitable_downloader(
            info_dict, self.params, None, protocol='dash_frag_urls', to_stdout=(filename == '-'))

        ctx = {
            'filename': filename,
            'live': True,
        }

        if real_downloader:
            self._prepare_external_frag_download(ctx)
        else:
            self._prepare_and_start_frag_download(ctx, info_dict)

        fragments_to_download = self._manifest_fragments(yie, manifest_url, stream_number)

        if real_downloader:
            self.to_screen(
                '[%s] Fragment downloads will be delegated to %s' % (self.FD_NAME, real_downloader.get_basename()))
            info_copy = info_dict.copy()
            info_copy['fragments'] = fragments_to_download
            fd = real_downloader(self.ydl, self.params)
            return fd.real_download(filename, info_copy)

        return self.download_and_append_fragments(ctx, fragments_to_download, info_dict)


class YoutubeDlFromStartHlsFD(FragmentFD):
    """
    Download YouTube live from the start, to the end. For HLS formats.
    This currently does not handle downloading 2 streams at once.
    """

    FD_NAME = 'ytlivestarthls'

    @staticmethod
    def _manifest_fragments(ie: YoutubeIE, m3u8_url, fetch_span=5000):
        known_idx = -1
        prev_dl = time_millis()
        finale = False
        while True:
            playlist = ie._download_webpage(m3u8_url, None, False, False, False,)
            if not playlist:
                continue
            # get maximum number
            last_url = None
            for line in playlist.splitlines():
                line = line.strip()
                if line:
                    if not line.startswith('#'):
                        frag_url = (
                            line
                            if re.match(r'^https?://', line)
                            else compat_urlparse.urljoin(m3u8_url, line))
                        last_url = frag_url
                    elif line == '#EXT-X-ENDLIST':
                        finale = True
            last_seq = int(re.search(r'/sq/(\d+)/', last_url).group(1))
            for idx in range(known_idx, last_seq):
                seq = idx + 1
                yield {
                    'frag_index': seq + 1,
                    'index': seq,
                    'url': re.sub(r'/sq/\d+/', '/sq/%d/' % seq, frag_url),
                }
            known_idx = last_seq
            if finale:
                break

            now_time = time_millis()
            if (now_time - prev_dl) < fetch_span:
                sleep((now_time - prev_dl) / 1e3)
            prev_dl = time_millis()

    def real_download(self, filename, info_dict):
        manifest_url = info_dict.get('url')
        if not manifest_url:
            self.report_error('URL to m3u8 manifest is not known; there is a problem in YoutubeIE code')

        yie: YoutubeIE = self.ydl.get_info_extractor(YoutubeIE.ie_key())

        real_downloader = get_suitable_downloader(
            info_dict, self.params, None, protocol='dash_frag_urls', to_stdout=(filename == '-'))

        ctx = {
            'filename': filename,
            'live': True,
        }

        if real_downloader:
            self._prepare_external_frag_download(ctx)
        else:
            self._prepare_and_start_frag_download(ctx, info_dict)

        fragments_to_download = self._manifest_fragments(yie, manifest_url)

        if real_downloader:
            self.to_screen(
                '[%s] Fragment downloads will be delegated to %s' % (self.FD_NAME, real_downloader.get_basename()))
            info_copy = info_dict.copy()
            info_copy['fragments'] = fragments_to_download
            fd = real_downloader(self.ydl, self.params)
            return fd.real_download(filename, info_copy)

        return self.download_and_append_fragments(ctx, fragments_to_download, info_dict)

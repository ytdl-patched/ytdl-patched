from __future__ import division, unicode_literals

from .common import FileDownloader
from .external import FFmpegFD


class SerialFD(FileDownloader):
    """
    Download videos in the order and join later.
    Ensure all enclosed formats have same codec, resolution and fps.

    Keys for formats:
    - "url" -- Must be "serial:". or download will fail.
    - "items" -- List of formats to download and join. Must have more than one item
    """

    def real_download(self, filename, info_dict):
        from ..downloader import get_suitable_downloader
        if info_dict['url'] != 'serial:':
            self.report_error('"url" key must be "serial:". Please check extractor code.')
            return False

        items = info_dict['items']
        if not items:
            self.report_error('There is no item to download!')
            return False

        if len(items) == 1:
            return get_suitable_downloader(items[0])(self.ydl, self.params).download(filename, items[0])

        names_to_join = []
        for idx, entry in enumerate(items):
            self.to_screen('Downloading step %d' % idx)
            new_name = '%s_%d.%s' % (filename, idx, entry['ext'])
            result = get_suitable_downloader(entry)(self.ydl, self.params).download(new_name, entry)
            if not result:
                self.report_error('Download failed at step %d' % idx)
                return False
            names_to_join.append(new_name)

        txt_file = '%s.txt' % filename
        ffmpeg_request = {
            'protocol': 'live_ffmpeg',
            'url': txt_file,
            'ext': info_dict['ext'],
            'input_params': ['-f', 'concat', '-safe', '0'],
            'output_params': ['-movflags', '+faststart'],
        }
        try:
            with self.ydl.open(txt_file, 'wt') as w:
                w.write(''.join(f"file '{nmj}'\n" for nmj in names_to_join))
            ret = FFmpegFD(self.ydl, self.params).download(filename, ffmpeg_request)[0]

            if ret:
                for nmj in names_to_join:
                    try:
                        self.ydl.remove(nmj)
                    except (IOError, OSError):
                        pass

            return ret
        finally:
            try:
                self.ydl.remove(txt_file)
            except (IOError, OSError):
                pass


class FfmpegConcatFD(FileDownloader):
    """
    Use ffmpeg's concat demuxer to download in serial.

    Keys for formats:
    - "url" -- Must be "serial:". or download will fail.
    - "items" -- List of URL to download and join. Must have more than one item
    """

    def real_download(self, filename, info_dict):
        if info_dict['url'] != 'serial:':
            self.report_error('"url" key must be "serial:". Please check extractor code.')
            return False

        items = info_dict['items']
        if not items:
            self.report_error('There is no item to download!')
            return False

        urls = [(x if isinstance(x, str) else x['url']) for x in items]

        txt_file = '%s.txt' % filename
        ffmpeg_request = {
            'protocol': 'live_ffmpeg',
            'url': txt_file,
            'ext': info_dict['ext'],
            'input_params': ['-f', 'concat', '-safe', '0'],
            'output_params': ['-movflags', '+faststart'],
        }
        try:
            with self.ydl.open(txt_file, 'wt') as w:
                w.write(''.join(f"file '{nmj}'\n" for nmj in urls))
            return FFmpegFD(self.ydl, self.params).download(filename, ffmpeg_request)[0]
        finally:
            try:
                self.ydl.remove(txt_file)
            except (IOError, OSError):
                pass

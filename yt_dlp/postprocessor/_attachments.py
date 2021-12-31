import re
import time
import os

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..YoutubeDL import YoutubeDL


from ..utils import (
    int_or_none,
    timetuple_from_msec,
    format_bytes,
    to_str,
)
from ..minicurses import (
    MultilinePrinterBase,
    MultilineLogger,
    MultilinePrinter,
    QuietMultilinePrinter,
    BreaklineStatusPrinter
)


class RunsFFmpeg(object):
    @staticmethod
    def parse_ffmpeg_time_string(time_string):
        time = 0
        reg1 = re.match(r'((?P<H>\d\d?):)?((?P<M>\d\d?):)?(?P<S>\d\d?)(\.(?P<f>\d{1,3}))?', time_string)
        reg2 = re.match(r'\d+(?P<U>s|ms|us)', time_string)
        if reg1:
            if reg1.group('H') is not None:
                time += 3600 * int(reg1.group('H'))
            if reg1.group('M') is not None:
                time += 60 * int(reg1.group('M'))
            time += int(reg1.group('S'))
            if reg1.group('f') is not None:
                time += int(reg1.group('f')) / 1_000
        elif reg2:
            time = int(reg2.group('U'))
            if reg2.group('U') == 'ms':
                time /= 1_000
            elif reg2.group('U') == 'us':
                time /= 1_000_000
        return time

    @staticmethod
    def compute_prefix(match):
        if not match:
            return None
        res = int(match.group('E'))
        if match.group('f') is not None:
            res += int(match.group('f'))
        if match.group('U') is not None:
            if match.group('U') == 'g':
                res *= 1_000_000_000
            elif match.group('U') == 'm':
                res *= 1_000_000
            elif match.group('U') == 'k':
                res *= 1_000
        return res

    def read_ffmpeg_status(self, info_dict, proc, is_pp=False):
        if not info_dict:
            info_dict = {}
        stdout = proc.stdout
        if not stdout:
            self.write_debug('Gave up reading progress; stdout == None')
            return proc.wait()
        started, total_filesize, total_time_to_dl, dl_bytes_int = time.time(), 0, None, None

        total_filesize = 0
        for fmt in info_dict.get('requested_formats') or [info_dict]:
            if fmt.get('filepath'):
                # PPs are given this
                total_filesize += os.path.getsize(fmt['filepath'])
            elif fmt.get('filesize'):
                total_filesize += fmt['filesize']
            elif fmt.get('filesize_approx'):
                total_filesize += fmt['filesize_approx']

        duration = info_dict.get('duration')
        guessed_size = total_filesize

        status = {
            '__from_ffmpeg_native_status': True,
            'filename': info_dict.get('_filename'),
            'status': 'processing' if is_pp else 'downloading',
            'elapsed': 0,
            'total_bytes_estimate': total_filesize,
        }

        retval = None

        def _ffmpeg_progress_reader():
            nonlocal retval
            retval = proc.poll()
            result = {}
            while retval is None:
                progress_line = to_str(stdout.readline())
                try:
                    for mobj in re.finditer(r'(?P<key>\S+)=\s*(?P<value>\S+)', progress_line):
                        result[mobj.group('key')] = mobj.group('value')
                        if mobj.group('key') == 'progress':
                            yield result
                            result = {}
                finally:
                    retval = proc.poll()
                    status.update({'elapsed': time.time() - started})

        time_and_size, avg_len = [], 10

        for ffmpeg_prog_infos in _ffmpeg_progress_reader():
            speed = None if ffmpeg_prog_infos['speed'] == 'N/A' else float(ffmpeg_prog_infos['speed'][:-1])

            out_time = self.parse_ffmpeg_time_string(ffmpeg_prog_infos['out_time'])
            eta_seconds = None
            if speed and total_time_to_dl:
                eta_seconds = (total_time_to_dl - out_time) / speed
                if eta_seconds < 0:
                    eta_seconds = None
            if eta_seconds is None and total_filesize and dl_bytes_int:
                # dl_bytes_int : (total_filesize - dl_bytes_int) = status['elapsed'] : ETA
                eta_seconds = (total_filesize - dl_bytes_int) * status['elapsed'] / dl_bytes_int
                if eta_seconds < 0:
                    eta_seconds = None

            if duration and dl_bytes_int and out_time:
                guessed_size = dl_bytes_int * duration / out_time
            # reduce terminal flick caused by drastic estimation change
            if total_filesize and guessed_size and (abs(guessed_size - total_filesize) / total_filesize) > 0.1:
                guessed_size = total_filesize

            bitrate_str = re.match(r'(?P<E>\d+)(\.(?P<f>\d+))?(?P<U>g|m|k)?bits/s', ffmpeg_prog_infos['bitrate'])
            bitrate_int = self.compute_prefix(bitrate_str)

            dl_bytes_int = int_or_none(ffmpeg_prog_infos['total_size'], default=0)
            time_and_size.append((dl_bytes_int, time.time()))
            time_and_size = time_and_size[-avg_len:]
            if len(time_and_size) > 1:
                last, early = time_and_size[0], time_and_size[-1]
                average_speed = (early[0] - last[0]) / (early[1] - last[1])
            else:
                average_speed = None

            status.update({
                'processed_bytes': dl_bytes_int,
                'downloaded_bytes': dl_bytes_int,
                'speed': average_speed,
                'speed_rate': speed,
                'bitrate': None if bitrate_int is None else bitrate_int / 8,
                'eta': eta_seconds,
                'total_bytes_estimate': guessed_size,
            })
            self._hook_progress(status, info_dict)

        status.update({
            'status': 'finished',
            'processed_bytes': dl_bytes_int,
            'downloaded_bytes': dl_bytes_int,
            'total_bytes': dl_bytes_int,
        })
        self._hook_progress(status, info_dict)

        return retval


class ShowsProgress(object):
    _PROGRESS_LABEL = 'download'

    def __init__(self, ydl: 'YoutubeDL', params: dict = None) -> None:
        self._ydl = ydl
        self._params = params or {}
        self._multiline: MultilinePrinterBase = None

    def _enable_progress(self, add=True):
        self._prepare_multiline_status()
        if add:
            self.add_progress_hook(self.report_progress)

    @staticmethod
    def format_seconds(seconds):
        time = timetuple_from_msec(seconds * 1000)
        if time.hours > 99:
            return '--:--:--'
        if not time.hours:
            return '%02d:%02d' % time[1:-1]
        return '%02d:%02d:%02d' % time[:-1]

    @staticmethod
    def calc_percent(byte_counter, data_len):
        if data_len is None:
            return None
        return float(byte_counter) / float(data_len) * 100.0

    @staticmethod
    def format_percent(percent):
        if percent is None:
            return '---.-%'
        elif percent == 100:
            return '100%'
        return '%6s' % ('%3.1f%%' % percent)

    @staticmethod
    def calc_eta(start, now, total, current):
        if total is None:
            return None
        if now is None:
            now = time.time()
        dif = now - start
        if current == 0 or dif < 0.001:  # One millisecond
            return None
        rate = float(current) / dif
        return int((float(total) - float(current)) / rate)

    @staticmethod
    def format_eta(eta):
        if eta is None:
            return '--:--'
        return ShowsProgress.format_seconds(eta)

    @staticmethod
    def calc_speed(start, now, bytes):
        dif = now - start
        if bytes == 0 or dif < 0.001:  # One millisecond
            return None
        return float(bytes) / dif

    @staticmethod
    def format_speed(speed):
        if speed is None:
            return '%10s' % '---b/s'
        return '%10s' % ('%s/s' % format_bytes(speed))

    @staticmethod
    def format_speed_rate(rate):
        if rate is None:
            return '---x'
        return '%.1dx' % rate

    @staticmethod
    def format_retries(retries):
        return 'inf' if retries == float('inf') else '%.0f' % retries

    @staticmethod
    def best_block_size(elapsed_time, bytes):
        new_min = max(bytes / 2.0, 1.0)
        new_max = min(max(bytes * 2.0, 1.0), 4194304)  # Do not surpass 4 MB
        if elapsed_time < 0.001:
            return int(new_max)
        rate = bytes / elapsed_time
        if rate > new_max:
            return int(new_max)
        if rate < new_min:
            return int(new_min)
        return int(rate)

    @staticmethod
    def parse_bytes(bytestr):
        """Parse a string indicating a byte quantity into an integer."""
        matchobj = re.match(r'(?i)^(\d+(?:\.\d+)?)([kMGTPEZY]?)$', bytestr)
        if matchobj is None:
            return None
        number = float(matchobj.group(1))
        multiplier = 1024.0 ** 'bkmgtpezy'.index(matchobj.group(2).lower())
        return int(round(number * multiplier))

    def to_console_title(self, message):
        self._ydl.to_console_title(message)

    def _prepare_multiline_status(self, lines=1):
        if self._multiline:
            return
        elif self._params.get('noprogress'):
            self._multiline = QuietMultilinePrinter()
        elif self._ydl.params.get('logger'):
            self._multiline = MultilineLogger(self._ydl.params['logger'], lines)
        elif self._params.get('progress_with_newline'):
            self._multiline = BreaklineStatusPrinter(self._ydl._screen_file, lines)
        else:
            self._multiline = MultilinePrinter(self._ydl._screen_file, lines, not self._params.get('quiet'))
        self._multiline.allow_colors = self._multiline._HAVE_FULLCAP and not self._params.get('no_color')

    def _finish_multiline_status(self):
        if not self._multiline:
            return
        self._multiline.end()

    _progress_styles = {
        'downloaded_bytes': 'light blue',
        'percent': 'light blue',
        'eta': 'yellow',
        'speed': 'green',
        'elapsed': 'bold white',
        'total_bytes': '',
        'total_bytes_estimate': '',
    }

    def _report_progress_status(self, s, default_template):
        for name, style in self._progress_styles.items():
            name = f'_{name}_str'
            if name not in s:
                continue
            s[name] = self._format_progress(s[name], style)
        s['_default_template'] = default_template % s

        progress_dict = s.copy()
        progress_dict.pop('info_dict')
        progress_dict = {'info': s['info_dict'], 'progress': progress_dict, 'progress_label': self._PROGRESS_LABEL}

        progress_template = self._params.get('progress_template', {})
        self._multiline.print_at_line(self._ydl.evaluate_outtmpl(
            progress_template.get('download') or '[%(progress_label)s] %(progress._default_template)s',
            progress_dict), s.get('progress_idx') or 0)
        self.to_console_title(self._ydl.evaluate_outtmpl(
            progress_template.get('download-title') or 'yt-dlp %(progress._default_template)s',
            progress_dict))

    def _format_progress(self, *args, **kwargs):
        return self._ydl._format_text(
            self._multiline.stream, self._multiline.allow_colors, *args, **kwargs)

    def report_progress(self, s):
        if s['status'] == 'finished':
            if self._params.get('noprogress'):
                self.to_screen(f'[{self._PROGRESS_LABEL}] Download completed')
            msg_template = '100%%'
            if s.get('total_bytes') is not None:
                s['_total_bytes_str'] = format_bytes(s['total_bytes'])
                msg_template += ' of %(_total_bytes_str)s'
            if s.get('elapsed') is not None:
                s['_elapsed_str'] = self.format_seconds(s['elapsed'])
                msg_template += ' in %(_elapsed_str)s'
            if s.get('fragment_count') is not None:
                msg_template += ' (%(fragment_count)d fragments total)'
            s['_percent_str'] = self.format_percent(100)
            self._report_progress_status(s, msg_template)
            return

        if s['status'] not in ('downloading', 'processing'):
            return

        if s.get('eta') is not None:
            s['_eta_str'] = self.format_eta(s['eta'])
        else:
            s['_eta_str'] = 'Unknown'

        if s.get('total_bytes') and s.get('downloaded_bytes') is not None:
            s['_percent_str'] = self.format_percent(100 * s['downloaded_bytes'] / s['total_bytes'])
        elif s.get('total_bytes_estimate') and s.get('downloaded_bytes') is not None:
            s['_percent_str'] = self.format_percent(100 * s['downloaded_bytes'] / s['total_bytes_estimate'])
        else:
            if s.get('downloaded_bytes') == 0:
                s['_percent_str'] = self.format_percent(0)
            else:
                s['_percent_str'] = 'Unknown %'

        if s.get('speed_rate') is not None:
            s['_speed_str'] = self.format_speed_rate(s['speed_rate'])
        elif s.get('speed') is not None:
            s['_speed_str'] = self.format_speed(s['speed'])
        else:
            s['_speed_str'] = 'Unknown speed'

        if s.get('total_bytes') is not None:
            s['_total_bytes_str'] = format_bytes(s['total_bytes'])
            msg_template = '%(_percent_str)s of %(_total_bytes_str)s at %(_speed_str)s ETA %(_eta_str)s'
        elif s.get('total_bytes_estimate') is not None:
            s['_total_bytes_estimate_str'] = format_bytes(s['total_bytes_estimate'])
            msg_template = '%(_percent_str)s of ~%(_total_bytes_estimate_str)s at %(_speed_str)s ETA %(_eta_str)s'
        else:
            if s.get('downloaded_bytes') is not None:
                s['_downloaded_bytes_str'] = format_bytes(s['downloaded_bytes'])
                if s.get('elapsed'):
                    s['_elapsed_str'] = self.format_seconds(s['elapsed'])
                    msg_template = '%(_downloaded_bytes_str)s at %(_speed_str)s (%(_elapsed_str)s)'
                else:
                    msg_template = '%(_downloaded_bytes_str)s at %(_speed_str)s'
                if s.get('fragment_count') is not None:
                    msg_template += ' (%(fragment_count)s fragments)'
            else:
                msg_template = '%(_percent_str)s % at %(_speed_str)s ETA %(_eta_str)s'

        if s.get('fragment_count') is not None and s.get('fragment_index') is not None:
            msg_template += ' (%(fragment_index)d fragments of %(fragment_count)d)'
        elif s.get('fragment_index') is not None:
            msg_template += ' (%(fragment_index)d fragments downloaded)'

        self._report_progress_status(s, msg_template)

import re
import shlex
import time
import os

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..YoutubeDL import YoutubeDL


from ..utils import (
    NUMBER_RE,
    Namespace,
    float_or_none,
    join_nonempty,
    int_or_none,
    remove_start,
    timetuple_from_msec,
    format_bytes,
    to_str,
    try_call,
)
from ..minicurses import (
    MultilinePrinterBase,
    MultilineLogger,
    MultilinePrinter,
    QuietMultilinePrinter,
    BreaklineStatusPrinter
)


def find_YoutubeDL(obj) -> 'YoutubeDL':
    from ..YoutubeDL import YoutubeDL

    if isinstance(obj, YoutubeDL):
        return obj

    for name in (
        '_ydl',  # ShowsProgress and cache
        'ydl',  # FileDownloader
        '_downloader',  # PostProcessor/InfoExtractor
    ):
        candidate = getattr(obj, name, None)
        if isinstance(candidate, YoutubeDL):
            if name != '_ydl':
                setattr(obj, '_ydl', candidate)
            return candidate


def getsize(o, filename):
    ydl = find_YoutubeDL(o)
    return ydl.getsize(filename) if ydl else os.path.getsize(filename)


class RunsFFmpeg(object):
    # https://kevinmccarthy.org/2016/07/25/streaming-subprocess-stdin-and-stdout-with-asyncio-in-python/

    def compute_total_filesize(self, info_dict, duration_to_track, duration):
        if not duration:
            return 0

        filesize = 0
        for fmt in info_dict.get('requested_formats') or [info_dict]:
            if fmt.get('filepath'):
                # PPs are given this
                filesize += getsize(self, fmt['filepath'])
            elif fmt.get('filesize'):
                filesize += int_or_none(fmt['filesize'])
            elif fmt.get('filesize_approx'):
                filesize += int_or_none(fmt['filesize_approx'])

        return filesize * duration_to_track // duration

    def compute_duration_to_track(self, info_dict, args):
        duration = info_dict.get('duration')
        if not duration:
            return 0, 0

        start_time, end_time = 0, duration
        for i, arg in enumerate(args):
            arg_timestamp, timestamp_seconds = re.match(r'(?P<at>-(?:ss|sseof|to))', arg), None
            if not arg_timestamp:
                continue
            if '=' in arg:
                # e.g. -ss=100
                timestamp_seconds = self.parse_ffmpeg_time_string(arg.split('=', 1)[1])
            elif arg_timestamp and i + 1 < len(args):
                timestamp_seconds = self.parse_ffmpeg_time_string(args[i + 1])

            if timestamp_seconds is not None:
                if arg_timestamp.group('at') == '-ss':
                    start_time = timestamp_seconds
                elif arg_timestamp.group('at') == '-sseof':
                    start_time = end_time - timestamp_seconds
                elif arg_timestamp.group('at') == '-to':
                    end_time = timestamp_seconds

        duration_to_track = end_time - start_time
        if duration_to_track >= 0:
            return duration_to_track, duration
        else:
            return 0, duration

    @staticmethod
    def compute_eta(ffmpeg_prog_infos: dict, duration_to_track, total=None, downloaded=None, elapsed=None):
        try:
            speed = float_or_none(ffmpeg_prog_infos['speed'][:-1])
            out_time_second = int_or_none(ffmpeg_prog_infos['out_time_us']) // 1_000_000
            return (duration_to_track - out_time_second) // speed
        except (TypeError, KeyError, ZeroDivisionError):
            pass

        if total and downloaded:
            # downloaded : (total - downloaded) = elapsed : ETA
            eta_seconds = (total - downloaded) * elapsed / downloaded
            if eta_seconds < 0:
                return eta_seconds

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
    def compute_bitrate(bitrate):
        match = re.match(r'(?P<E>\d+(?:\.\d+)?)(?P<U>g|m|k)?bits/s', bitrate)
        if not match:
            return None
        res = float(match.group('E'))
        if match.group('U') is not None:
            if match.group('U') == 'g':
                res *= 1_000_000_000
            elif match.group('U') == 'm':
                res *= 1_000_000
            elif match.group('U') == 'k':
                res *= 1_000
        return res

    @staticmethod
    def get_popen_args(popen):
        args = popen.args
        if isinstance(args, str):
            return shlex.split(args)
        else:
            return args or []

    def read_ffmpeg_status(self, info_dict, proc, is_pp=False):
        if not info_dict:
            info_dict = {}
        stdout = proc.stdout
        if not stdout:
            self.write_debug('Gave up reading progress; stdout == None')
            return proc.wait()
        started, dl_bytes_int = time.time(), None

        ffmpeg_args = self.get_popen_args(proc)
        duration_to_track, duration = self.compute_duration_to_track(info_dict, ffmpeg_args)
        total_filesize = self.compute_total_filesize(info_dict, duration_to_track, duration)

        guessed_size = total_filesize

        bytes_key = 'processed_bytes' if is_pp else 'downloaded_bytes'
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
            eta_seconds = self.compute_eta(ffmpeg_prog_infos, duration_to_track, total_filesize, dl_bytes_int, status['elapsed'])

            bitrate_int = self.compute_bitrate(ffmpeg_prog_infos['bitrate'])

            out_time_second = int_or_none(ffmpeg_prog_infos['out_time_us'], scale=1_000_000)
            try:
                dl_bytes_int = int_or_none(out_time_second / duration_to_track * total_filesize)
            except ZeroDivisionError:
                # Not using ffmpeg 'total_size' value primarily as it's imprecise and gives progress percentage over 100
                dl_bytes_int = int_or_none(ffmpeg_prog_infos['total_size'], default=0)

            if duration_to_track and dl_bytes_int and out_time:
                # only estimate the remaining part, keep the other intact
                guessed_size = dl_bytes_int + (dl_bytes_int * (duration_to_track - out_time) / out_time)
            # reduce terminal flick caused by drastic estimation change
            if total_filesize and guessed_size and (abs(guessed_size - total_filesize) / total_filesize) > 0.1:
                guessed_size = total_filesize

            time_and_size.append((dl_bytes_int, time.time()))
            time_and_size = time_and_size[-avg_len:]
            if len(time_and_size) > 1:
                last, early = time_and_size[0], time_and_size[-1]
                average_speed = (early[0] - last[0]) / (early[1] - last[1])
            else:
                average_speed = None

            status.update({
                bytes_key: dl_bytes_int,
                'speed': average_speed,
                'speed_rate': speed,
                'bitrate': None if bitrate_int is None else bitrate_int / 8,
                'eta': eta_seconds,
                'total_bytes_estimate': guessed_size,
            })
            self._hook_progress(status, info_dict)

        status.update({
            'status': 'finished',
            bytes_key: dl_bytes_int,
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
        if seconds is None:
            return ' Unknown'
        time = timetuple_from_msec(seconds * 1000)
        if time.hours > 99:
            return '--:--:--'
        if not time.hours:
            return '%02d:%02d' % time[1:-1]
        return '%02d:%02d:%02d' % time[:-1]

    @classmethod
    def format_eta(cls, seconds):
        return f'{remove_start(cls.format_seconds(seconds), "00:"):>8s}'

    @staticmethod
    def calc_percent(byte_counter, data_len):
        if data_len is None:
            return None
        return float(byte_counter) / float(data_len) * 100.0

    @staticmethod
    def format_percent(percent):
        return '  N/A%' if percent is None else f'{percent:>5.1f}%'

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
        return '%6s' % ('%.1dx' % rate)

    @staticmethod
    def format_retries(retries):
        return 'inf' if retries == float('inf') else int(retries)

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
        matchobj = re.match(rf'(?i)^({NUMBER_RE})([kMGTPEZY]?)$', bytestr)
        if matchobj is None:
            return None
        number = float(matchobj.group(1))
        multiplier = 1024.0 ** 'bkmgtpezy'.index(matchobj.group(2).lower())
        return int(round(number * multiplier))

    def to_console_title(self, message):
        self._ydl.to_console_title(message)

    def _prepare_multiline_status(self, lines=1):
        self._finish_multiline_status()
        if self._params.get('noprogress'):
            self._multiline = QuietMultilinePrinter()
        elif self._ydl.params.get('logger'):
            self._multiline = MultilineLogger(self._ydl.params['logger'], lines)
        elif self._params.get('progress_with_newline'):
            self._multiline = BreaklineStatusPrinter(self._ydl._out_files.screen, lines)
        else:
            self._multiline = MultilinePrinter(self._ydl._out_files.screen, lines, not self._params.get('quiet'))
        self._multiline.allow_colors = self._multiline._HAVE_FULLCAP and not self._params.get('no_color')

    def _finish_multiline_status(self):
        if not self._multiline:
            return
        self._multiline.end()

    ProgressStyles = Namespace(
        downloaded_bytes='light blue',
        percent='light blue',
        eta='yellow',
        speed='green',
        elapsed='bold white',
        total_bytes='',
        total_bytes_estimate='',
    )

    def _report_progress_status(self, s, default_template):
        for name, style in self.ProgressStyles.items_:
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
        def with_fields(*tups, default=''):
            for *fields, tmpl in tups:
                if all(s.get(f) is not None for f in fields):
                    return tmpl
            return default

        _formats_bytes = lambda k: f'{format_bytes(s.get(k)):>10s}'

        if s['status'] == 'finished':
            if self.params.get('noprogress'):
                self.to_screen('[download] Download completed')
            speed = try_call(lambda: s['total_bytes'] / s['elapsed'])
            s.update({
                'speed': speed,
                '_speed_str': self.format_speed(speed).strip(),
                '_total_bytes_str': _formats_bytes('total_bytes'),
                '_elapsed_str': self.format_seconds(s.get('elapsed')),
                '_percent_str': self.format_percent(100),
            })
            self._report_progress_status(s, join_nonempty(
                '100%%',
                with_fields(('total_bytes', 'of %(_total_bytes_str)s')),
                with_fields(('elapsed', 'in %(_elapsed_str)s')),
                with_fields(('speed', 'at %(_speed_str)s')),
                delim=' '))

        if s['status'] not in ('downloading', 'processing'):
            return

        downloaded_bytes = s.get('downloaded_bytes') or s.get('processed_bytes')

        s.update({
            '_eta_str': self.format_eta(s.get('eta')).strip(),
            '_speed_str': self.format_speed(s.get('speed')) if s.get('speed_rate') is None else self.format_speed_rate(s['speed_rate']),
            '_percent_str': self.format_percent(try_call(
                lambda: 100 * downloaded_bytes / s['total_bytes'],
                lambda: 100 * downloaded_bytes / s['total_bytes_estimate'],
                lambda: downloaded_bytes == 0 and 0)),
            '_total_bytes_str': _formats_bytes('total_bytes'),
            '_total_bytes_estimate_str': _formats_bytes('total_bytes_estimate'),
            '_downloaded_bytes_str': _formats_bytes('downloaded_bytes'),
            '_elapsed_str': self.format_seconds(s.get('elapsed')),
        })

        msg_template = with_fields(
            ('total_bytes', '%(_percent_str)s of %(_total_bytes_str)s at %(_speed_str)s ETA %(_eta_str)s'),
            ('total_bytes_estimate', '%(_percent_str)s of ~%(_total_bytes_estimate_str)s at %(_speed_str)s ETA %(_eta_str)s'),
            ('downloaded_bytes', 'elapsed', '%(_downloaded_bytes_str)s at %(_speed_str)s (%(_elapsed_str)s)'),
            ('downloaded_bytes', '%(_downloaded_bytes_str)s at %(_speed_str)s'),
            default='%(_percent_str)s at %(_speed_str)s ETA %(_eta_str)s')

        msg_template += with_fields(
            ('fragment_index', 'fragment_count', ' (%(fragment_index)d fragments of %(fragment_count)d)'),
            ('fragment_index', ' (%(fragment_index)d fragments downloaded)'))

        self._report_progress_status(s, msg_template)

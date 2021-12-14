import re
import time


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
        started, total_filesize, total_time_to_dl, dl_bytes_int = time.time(), 0, None, None
        if info_dict.get('duration'):
            # start_time, end_time, total_time_to_dl = started, None, info_dict['duration']

            # if start_time is not None and end_time is None:
            #     total_time_to_dl = total_time_to_dl - start_time
            # elif start_time is None and end_time is not None:
            #     total_time_to_dl = end_time
            # elif start_time is not None and end_time is not None:
            #     total_time_to_dl = end_time - start_time

            # if info_dict.get('filesize') is not None:
            #     total_filesize = info_dict['filesize'] * total_time_to_dl / info_dict['duration']
            # elif info_dict.get('filesize') is not None:
            #     total_filesize = info_dict['filesize_approx'] * total_time_to_dl / info_dict['duration']

            if info_dict.get('filesize') is not None:
                total_filesize = info_dict['filesize']
            elif info_dict.get('filesize_approx') is not None:
                total_filesize = info_dict['filesize_approx']

        status = {
            'filename': info_dict.get('_filename'),
            'status': 'processing' if is_pp else 'downloading',
            'total_bytes': total_filesize,
            'elapsed': 0,
        }

        progress_pattern = re.compile(
            r'(frame=\s*(?P<frame>\S+)\nfps=\s*(?P<fps>\S+)\nstream_0_0_q=\s*(?P<stream_0_0_q>\S+)\n)?bitrate=\s*(?P<bitrate>\S+)\ntotal_size=\s*(?P<total_size>\S+)\nout_time_us=\s*(?P<out_time_us>\S+)\nout_time_ms=\s*(?P<out_time_ms>\S+)\nout_time=\s*(?P<out_time>\S+)\ndup_frames=\s*(?P<dup_frames>\S+)\ndrop_frames=\s*(?P<drop_frames>\S+)\nspeed=\s*(?P<speed>\S+)\nprogress=\s*(?P<progress>\S+)')

        retval = proc.poll()
        ffmpeg_stdout_buffer = ''

        while retval is None:
            ffmpeg_stdout = proc.stdout.readline() if proc.stdout is not None else ''
            if ffmpeg_stdout:
                ffmpeg_stdout_buffer += ffmpeg_stdout
                ffmpeg_prog_infos = re.match(progress_pattern, ffmpeg_stdout_buffer)

                if ffmpeg_prog_infos:
                    # sys.stdout.write(ffpmeg_stdout_buffer)
                    ffmpeg_stdout = ''
                    speed = None if ffmpeg_prog_infos['speed'] == 'N/A' else float(ffmpeg_prog_infos['speed'][:-1])

                    eta_seconds = None
                    if speed and total_time_to_dl:
                        eta_seconds = (total_time_to_dl - self.parse_ffmpeg_time_string(
                            ffmpeg_prog_infos['out_time'])) / speed
                        if eta_seconds < 0:
                            eta_seconds = None
                    if eta_seconds is None and total_filesize and dl_bytes_int:
                        # dl_bytes_int : (total_filesize - dl_bytes_int) = status['elapsed'] : ETA
                        eta_seconds = (total_filesize - dl_bytes_int) * status['elapsed'] / dl_bytes_int
                        if eta_seconds < 0:
                            eta_seconds = None

                    bitrate_int = None
                    bitrate_str = re.match(r'(?P<E>\d+)(\.(?P<f>\d+))?(?P<U>g|m|k)?bits/s', ffmpeg_prog_infos['bitrate'])

                    if bitrate_str:
                        bitrate_int = self.compute_prefix(bitrate_str)
                    dl_bytes_str = re.match(r'\d+', ffmpeg_prog_infos['total_size'])
                    dl_bytes_int = int(ffmpeg_prog_infos['total_size']) if dl_bytes_str else 0

                    status.update({
                        'processed_bytes': dl_bytes_int,
                        'downloaded_bytes': dl_bytes_int,
                        'speed': bitrate_int / 8,
                        'eta': eta_seconds
                    })
                    self._hook_progress(status, info_dict)
                    ffmpeg_stdout_buffer = ''
            status.update({'elapsed': time.time() - started})
            retval = proc.poll()
        status.update({
            'status': 'finished',
            'processed_bytes': total_filesize,
            'downloaded_bytes': total_filesize,
        })
        self._hook_progress(status, info_dict)

        return retval

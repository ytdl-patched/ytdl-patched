from __future__ import division, unicode_literals

import time
import random
import threading
import errno

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..YoutubeDL import YoutubeDL

from ..utils import (
    decodeArgument,
    encodeFilename,
    error_to_compat_str,
    shell_quote,
    timeconvert,
    sanitized_Request,
)
from ..postprocessor._attachments import ShowsProgress


class FileDownloader(ShowsProgress):
    """File Downloader class.

    File downloader objects are the ones responsible of downloading the
    actual video file and writing it to disk.

    File downloaders accept a lot of parameters. In order not to saturate
    the object constructor with arguments, it receives a dictionary of
    options instead.

    Available options:

    verbose:            Print additional info to stdout.
    quiet:              Do not print messages to stdout.
    ratelimit:          Download speed limit, in bytes/sec.
    throttledratelimit: Assume the download is being throttled below this speed (bytes/sec)
    retries:            Number of times to retry for HTTP error 5xx
    file_access_retries:   Number of times to retry on file access error
    buffersize:         Size of download buffer in bytes.
    noresizebuffer:     Do not automatically resize the download buffer.
    continuedl:         Try to continue downloads if possible.
    noprogress:         Do not print the progress bar.
    nopart:             Do not use temporary .part files.
    updatetime:         Use the Last-modified header to set output file timestamps.
    test:               Download only first bytes to test the downloader.
    min_filesize:       Skip files smaller than this size
    max_filesize:       Skip files larger than this size
    xattr_set_filesize: Set ytdl.filesize user xattribute with expected size.
    external_downloader_args:  A dictionary of downloader keys (in lower case)
                        and a list of additional command-line arguments for the
                        executable. Use 'default' as the name for arguments to be
                        passed to all downloaders. For compatibility with youtube-dl,
                        a single list of args can also be used
    hls_use_mpegts:     Use the mpegts container for HLS videos.
    http_chunk_size:    Size of a chunk for chunk-based HTTP downloading. May be
                        useful for bypassing bandwidth throttling imposed by
                        a webserver (experimental)
    progress_template:  See YoutubeDL.py

    Subclasses of this one must re-define the real_download method.
    """

    _TEST_FILE_SIZE = 10241
    params = None

    def __init__(self, ydl, params):
        """Create a FileDownloader object with the given options."""
        ShowsProgress.__init__(self, ydl, params)
        self.ydl: 'YoutubeDL' = ydl
        self.params = params
        self._progress_hooks = []
        self._enable_progress()

    def to_screen(self, *args, **kargs):
        self.ydl.to_stdout(*args, quiet=self.params.get('quiet'), **kargs)

    def to_stderr(self, message):
        self.ydl.to_stderr(message)

    def trouble(self, *args, **kargs):
        self.ydl.trouble(*args, **kargs)

    def report_warning(self, *args, **kargs):
        self.ydl.report_warning(*args, **kargs)

    def report_error(self, *args, **kargs):
        self.ydl.report_error(*args, **kargs)

    def write_debug(self, *args, **kargs):
        self.ydl.write_debug(*args, **kargs)

    def slow_down(self, start_time, now, byte_counter):
        """Sleep if the download speed is over the rate limit."""
        rate_limit = self.params.get('ratelimit')
        if rate_limit is None or byte_counter == 0:
            return
        if now is None:
            now = time.time()
        elapsed = now - start_time
        if elapsed <= 0.0:
            return
        speed = float(byte_counter) / elapsed
        if speed > rate_limit:
            sleep_time = float(byte_counter) / rate_limit - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def temp_name(self, filename):
        """Returns a temporary filename for the given filename."""
        if self.params.get('nopart', False) or filename == '-' or \
                (self.ydl.exists(encodeFilename(filename)) and not self.ydl.isfile(encodeFilename(filename))):
            return filename
        return filename + '.part'

    def undo_temp_name(self, filename):
        if filename.endswith('.part'):
            return filename[:-len('.part')]
        return filename

    def ytdl_filename(self, filename):
        return filename + '.ytdl'

    def sanitize_open(self, filename, open_mode):
        file_access_retries = self.params.get('file_access_retries', 10)
        retry = 0
        while True:
            try:
                return self.ydl.sanitize_open(filename, open_mode)
            except (IOError, OSError) as err:
                retry = retry + 1
                if retry > file_access_retries or err.errno not in (errno.EACCES,):
                    raise
                self.to_screen(
                    '[download] Got file access error. Retrying (attempt %d of %s) ...'
                    % (retry, self.format_retries(file_access_retries)))
                time.sleep(0.01)

    def try_rename(self, old_filename, new_filename):
        if old_filename == new_filename:
            return
        try:
            self.ydl.replace(old_filename, new_filename)
        except (IOError, OSError) as err:
            self.report_error(f'unable to rename file: {err}')

    def try_utime(self, filename, last_modified_hdr):
        """Try to set the last-modified time of the given file."""
        if last_modified_hdr is None:
            return
        if not self.ydl.isfile(encodeFilename(filename)):
            return
        timestr = last_modified_hdr
        if timestr is None:
            return
        filetime = timeconvert(timestr)
        if filetime is None:
            return filetime
        # Ignore obviously invalid dates
        if filetime == 0:
            return
        try:
            self.ydl.utime(filename, (time.time(), filetime))
        except Exception:
            pass
        return filetime

    def report_destination(self, filename):
        """Report destination filename."""
        self.to_screen('[download] Destination: ' + filename)

    def report_resuming_byte(self, resume_len):
        """Report attempt to resume at given byte."""
        self.to_screen('[download] Resuming download at byte %s' % resume_len)

    def report_retry(self, err, count, retries):
        """Report retry in case of HTTP error 5xx"""
        self.to_screen(
            '[download] Got server HTTP error: %s. Retrying (attempt %d of %s) ...'
            % (error_to_compat_str(err), count, self.format_retries(retries)))

    def report_file_already_downloaded(self, *args, **kwargs):
        """Report file has already been fully downloaded."""
        return self.ydl.report_file_already_downloaded(*args, **kwargs)

    def report_unable_to_resume(self):
        """Report it was impossible to resume download."""
        self.to_screen('[download] Unable to resume')

    @staticmethod
    def supports_manifest(manifest):
        """ Whether the downloader can download the fragments from the manifest.
        Redefine in subclasses if needed. """
        pass

    def download(self, filename, info_dict, subtitle=False):
        """Download to a filename using the info from info_dict
        Return True on success and False otherwise
        """

        nooverwrites_and_exists = (
            not self.params.get('overwrites', True)
            and self.ydl.exists(encodeFilename(filename))
        )

        if not hasattr(filename, 'write'):
            continuedl_and_exists = (
                self.params.get('continuedl', True)
                and self.ydl.isfile(encodeFilename(filename))
                and not self.params.get('nopart', False)
            )

            # Check file already present
            if filename != '-' and (nooverwrites_and_exists or continuedl_and_exists):
                self.report_file_already_downloaded(filename)
                self._hook_progress({
                    'filename': filename,
                    'status': 'finished',
                    'total_bytes': self.ydl.getsize(encodeFilename(filename)),
                }, info_dict)
                self._finish_multiline_status()
                return True, False

        if subtitle is False:
            min_sleep_interval = self.params.get('sleep_interval')
            if min_sleep_interval:
                max_sleep_interval = self.params.get('max_sleep_interval', min_sleep_interval)
                sleep_interval = random.uniform(min_sleep_interval, max_sleep_interval)
                self.to_screen(
                    '[download] Sleeping %s seconds ...' % (
                        int(sleep_interval) if sleep_interval.is_integer()
                        else '%.2f' % sleep_interval))
                time.sleep(sleep_interval)
        else:
            sleep_interval_sub = 0
            if type(self.params.get('sleep_interval_subtitles')) is int:
                sleep_interval_sub = self.params.get('sleep_interval_subtitles')
            if sleep_interval_sub > 0:
                self.to_screen(
                    '[download] Sleeping %s seconds ...' % (
                        sleep_interval_sub))
                time.sleep(sleep_interval_sub)

        timer = [None]
        heartbeat_lock = None
        download_complete = False
        if 'heartbeat_url' in info_dict:
            heartbeat_lock = threading.Lock()

            heartbeat_url = info_dict['heartbeat_url']
            heartbeat_data = info_dict['heartbeat_data']
            heartbeat_interval = info_dict.get('heartbeat_interval', 30)
            self.to_screen('[download] Heartbeat with %s second interval...' % heartbeat_interval)

            request = sanitized_Request(heartbeat_url, heartbeat_data)

            def heartbeat():
                try:
                    self.ydl.urlopen(request).read()
                except Exception:
                    self.to_screen("[download] Heartbeat failed")

                with heartbeat_lock:
                    if not download_complete:
                        timer[0] = threading.Timer(heartbeat_interval, heartbeat)
                        timer[0].start()

            heartbeat()

        try:
            return self.real_download(filename, info_dict), True
        finally:
            self._finish_multiline_status()
            if heartbeat_lock:
                with heartbeat_lock:
                    timer[0].cancel()
                    download_complete = True

    def real_download(self, filename, info_dict):
        """Real download process. Redefine in subclasses."""
        raise NotImplementedError('This method must be implemented by subclasses')

    def _hook_progress(self, status, info_dict):
        if not self._progress_hooks:
            return
        status['info_dict'] = info_dict
        # youtube-dl passes the same status object to all the hooks.
        # Some third party scripts seems to be relying on this.
        # So keep this behavior if possible
        for ph in self._progress_hooks:
            ph(status)

    def add_progress_hook(self, ph):
        # See YoutubeDl.py (search for progress_hooks) for a description of
        # this interface
        self._progress_hooks.append(ph)

    def _debug_cmd(self, args, exe=None):
        if not self.params.get('verbose', False):
            return

        str_args = [decodeArgument(a) for a in args]

        if exe is None:
            exe = self.ydl.basename(str_args[0])

        self.write_debug('%s command line: %s' % (exe, shell_quote(str_args)))

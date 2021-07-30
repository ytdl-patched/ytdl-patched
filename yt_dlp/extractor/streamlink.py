# coding: utf-8
from __future__ import unicode_literals

import logging

try:
    import streamlink as _streamlink
    import streamlink.exceptions as _exc
    HAVE_STREAMLINK = True
except (ImportError, SyntaxError):
    # Streamlink is mandantory, when called
    HAVE_STREAMLINK = False

from ..utils import ExtractorError, determine_ext
from .common import InfoExtractor


class YtdlHandler(logging.Handler):
    def __init__(self, ie):
        super().__init__()
        self.ie = ie

    def emit(self, record):
        msg = self.format(record)
        self.ie.to_screen(msg)

    def __enter__(self):
        root_logger = logging.getLogger()
        ytdl_verbose = self.ie._downloader.params.get('verbose', False)
        self.orig_level = root_logger.level
        new_level = logging.DEBUG if ytdl_verbose else logging.INFO
        root_logger.addHandler(self)
        root_logger.setLevel(new_level)
        return self

    def __exit__(self, type, value, traceback):
        root_logger = logging.getLogger()
        root_logger.removeHandler(self)
        root_logger.setLevel(self.orig_level)


# Extractors in yt-dlp and ytdl-patched must take precedence over plugins in Streamlink
# ... but GenericIE
# so should be tested in "All extractors except Generic and Streamlink" -> Streamlink -> GenericIE
class StreamlinkIE(InfoExtractor):
    _IE_DESC = 'Streamlink integration. Requires Streamlink installed via pip'
    _TESTS = [{
        'url': 'https://abema.tv/now-on-air/abema-news',
        'only_matching': True,
    }]

    _STREAMLINK_INSTANCE = None

    @classmethod
    def _streamlink_instance(self):
        if not HAVE_STREAMLINK:
            return None
        if not self._STREAMLINK_INSTANCE:
            self._STREAMLINK_INSTANCE = _streamlink.Streamlink()
            # TODO: copy options from ytdl-patched here
            # https://github.com/streamlink/streamlink/blob/master/src/streamlink_cli/main.py#L742
            # https://github.com/streamlink/streamlink/blob/master/src/streamlink_cli/main.py#L691

        return self._STREAMLINK_INSTANCE

    @classmethod
    def suitable(cls, url):
        if not HAVE_STREAMLINK:
            return False

        streamlink = cls._streamlink_instance()
        forced = False
        if url.startswith('streamlink:'):
            url = url[11:]
            forced = True
        try:
            streamlink.resolve_url(url)
        except _exc.NoPluginError:
            return False

        if forced:
            # Steamlink is forced, omit IE checks
            return True

        from . import gen_extractor_classes
        for ie in gen_extractor_classes():
            # skip must-match extractor and StreamlinkIE itself
            if ie.ie_key() in (cls.ie_key(), 'Generic'):
                continue
            if ie.suitable(url):
                return False
        return True

    def _real_extract(self, url):
        if not HAVE_STREAMLINK:
            raise ExtractorError('Please install streamlink first via: pip install streamlink', expected=True)
        if url.startswith('streamlink:'):
            url = url[11:]

        retries = self.get_param('extractor_retries', 3)

        with YtdlHandler(self):
            streamlink = self._streamlink_instance()
            plugin = streamlink.resolve_url(url)

            streams = self._extract_with_retry(plugin, retries)
            title = plugin.get_title()
            if not streams:
                raise ExtractorError('Plugin returned no streams!', expected=True)

        formats = []
        for name, stream in streams.items():
            if name in ('best', 'worst', 'best-unfiltered', 'worst-unfiltered', ):
                # skip sorted formats, as it's done by YoutubeDL itself
                continue
            strm_url = stream.url
            ext = determine_ext(strm_url)
            if ext in ('m3u8', 'mpd'):
                ext = 'mp4'
            if not ext:
                ext = 'mp4'
            formats.append({
                'format_id': name,
                'url': strm_url,
                'ext': ext,
                'stream': stream,
                'protocol': 'streamlink',
                'quality': plugin.stream_weight(name),
            })

        return {
            'id': self._generic_id(url),
            'title': title or self._generic_title(url),
            'formats': formats,
            'webpage_url': url,
            'is_live': True,
        }

    def _extract_with_retry(self, plugin, retries):
        count = -1
        last_error = None
        while count < retries:
            count += 1
            if count:
                self.report_warning('%s. Retrying ...' % last_error)
            try:
                return plugin.streams()
            except BaseException as ex:
                last_error = ex
            if count >= retries:
                raise ExtractorError('Stream extraction failed.', expected=True, cause=last_error)
        return None

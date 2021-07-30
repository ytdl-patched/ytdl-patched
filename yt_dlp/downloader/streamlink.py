# coding: utf-8
from __future__ import unicode_literals

from itertools import chain
from functools import partial

from .websocket import FFmpegSinkFD


class StreamlinkFD(FFmpegSinkFD):
    """
    Special FileDownloader for Streamlink integration.
    Streamlink is required when it's being used.
    """

    async def real_connection(self, sink, info_dict):
        stream = info_dict['stream']
        self.read_stream(stream.open(), sink, b'')

    def read_stream(self, stream, output, prebuffer, chunk_size=8192):
        """
        Reads data from stream and then writes it to the output.
        Slimmed down from streamlink_cli.main.read_stream, to use ffmpeg as progress instead.
        """
        stream_iterator = chain(
            [prebuffer],
            iter(partial(stream.read, chunk_size), b"")
        )

        try:
            for data in stream_iterator:
                try:
                    output.write(data)
                except OSError as err:
                    self.report_error(f"Error when writing to output: {err}, exiting")
                    break
        except OSError as err:
            raise Exception(f"Error when reading from stream: {err}, exiting", err)
        finally:
            stream.close()
            self.to_screen("Stream ended")

from .common import PostProcessor
from ..utils import prepend_extension

from ..ts_parser import (
    # write_mp4_boxes,
    parse_mp4_boxes,
    # pack_be32,
    # pack_be64,
    unpack_ver_flags,
    unpack_be32,
    unpack_be64,
)


class MP4TimestampFixupPP(PostProcessor):
    def __init__(self, downloader=None):
        super().__init__(downloader)

    def analyze_mp4(filepath):
        """ returns (baseMediaDecodeTime offset, sample duration cutoff) """
        smallest_bmdt, known_sdur = float('inf'), set()
        with open(filepath, 'rb') as r:
            for btype, content in parse_mp4_boxes(r):
                if btype == 'tfdt':
                    version, _ = unpack_ver_flags(content[0:4])
                    # baseMediaDecodeTime always comes to the first
                    if version == 0:
                        bmdt = unpack_be32(content[4:8])
                    else:
                        bmdt = unpack_be64(content[4:12])
                    if bmdt == 0:
                        continue
                    smallest_bmdt = min(bmdt, smallest_bmdt)
                elif btype == 'tfhd':
                    version, flags = unpack_ver_flags(content[0:4])
                    if not flags & 0x08:
                        # this box does not contain "sample duration"
                        continue
                    # https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/box.js#L203-L209
                    # https://github.com/gpac/mp4box.js/blob/4e1bc23724d2603754971abc00c2bd5aede7be60/src/parsing/tfhd.js
                    sdur_start = 8  # header + track id
                    if flags & 0x01:
                        sdur_start += 8
                    if flags & 0x02:
                        sdur_start += 4
                    # the next 4 bytes are "sample duration"
                    sample_dur = unpack_be32(content[sdur_start:sdur_start + 4])
                    known_sdur.add(sample_dur)

    def run(self, information):
        filename = information['filepath']
        temp_filename = prepend_extension(filename, 'temp')

        # self.to_screen(f'{msg} of "{filename}"')
        # self.run_ffmpeg(filename, temp_filename, options)

        self._downloader.replace(temp_filename, filename)

        return [], information

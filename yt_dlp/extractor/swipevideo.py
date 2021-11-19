import re
from .common import InfoExtractor
from ..utils import determine_ext, number_of_digits


class SwipeVideoIE(InfoExtractor):
    # SwipeVideoo can only be embedded
    _VALID_URL = r'swipevideo:(?P<id>[0-9a-zA-Z]+)'
    _TESTS = [{
        'url': 'swipevideo:3027850cf6',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        base_url = f'https://mercury-prod-cdn-cont.azureedge.net/{video_id}'
        info_data = self._download_json(f'{base_url}/info.json', video_id)

        title = info_data.get('title')
        pattern = info_data.get('pattern') or '\\${src}/%d.jpg'
        duration = info_data.get('duration')
        frames = info_data.get('frame')
        # we'll feed ffmpeg framerate with fraction instead
        # (e.g. -r '5490/183.019')
        approx_framerate = frames / duration

        formats = []
        srcsets = info_data.get('srcset') or []
        secset_digits = number_of_digits(len(srcsets))
        for idx, srcset in enumerate(srcsets):
            resolved_pattern = re.sub(r'\\?\${src}', srcset, pattern)
            images = [dict(
                url=f'{base_url}/{resolved_pattern % (x + 1)}') for x in range(frames)]
            formats.append({
                'format_id': f'%0{secset_digits}d-%s' % (idx, srcset),
                'protocol': 'image_series',
                'vcodec': 'jpg',
                'acodec': 'none',
                # FileDownloader is resposible for converting to this format
                'ext': 'mp4',
                'url': images[0]['url'],
                'fragments': images,
                'duration': duration,
                'frame_count': frames,
                'fps': approx_framerate,
                'format_note': f'Angle {idx + 1}',
                'preference': -idx,
                'fragment_base_url': base_url,
            })

        audio_path = info_data.get('audio')
        if audio_path:
            formats.append({
                'format_id': 'audio',
                'url': f'{base_url}/{audio_path}',
                'vcodec': 'none',
                'acodec': None,
                'ext': determine_ext(audio_path),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'duration': duration,
            'fps': approx_framerate,
            'formats': formats,
        }

from __future__ import unicode_literals

from .common import InfoExtractor


class HelloNewDreamIE(InfoExtractor):
    _VALID_URL = r'https?://anatafor\.hello-new-dream\.jp/share/\?uid=(?P<id>([0-9]{4})([0-9]{2})([0-9]{2})([0-9]{4})([a-z0-9]+))'
    # https://anatafor.hello-new-dream.jp/data/2020/09/15/2225/48psv3dypxg9b35mbwx1/udata.json
    UDATA_API_URL = 'https://anatafor.hello-new-dream.jp/data/%s/%s/%s/%s/%s/udata.json'
    MIX_MP3_URL = 'https://anatafor.hello-new-dream.jp/data/%s/%s/%s/%s/%s/mix.mp3'
    _TESTS = []

    def _real_extract(self, url):
        song_id = self._match_id(url)
        groups = self._VALID_URL_RE.match(url).groups()[1:]
        udata = self._download_json(self.UDATA_API_URL % groups, song_id)

        # https://anatafor.hello-new-dream.jp/data/2020/09/15/0249/leillvlfe9f1w8v5mek5/mix.mp3
        mp3_url = self.MIX_MP3_URL % groups
        formats = [{
            'url': mp3_url,
            'format_id': 'mp3',
            'ext': 'mp3',
            'vcodec': 'none',
        }]

        return {
            'id': song_id,
            'display_id': song_id,
            'title': '%s %s' % (udata['name_1'], udata['name_2']),
            'formats': formats,
            'description': '%s %s' % (udata['dream_1'], udata['dream_2']),
        }

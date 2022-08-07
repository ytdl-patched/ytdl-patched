from .common import InfoExtractor


class WhatIsMyIpIE(InfoExtractor):
    _VALID_URL = r'(?:what-is-)?(?:my-)?ip'
    _TESTS = [{
        'url': 'what-is-my-ip',
        'only_matching': True,
    }, {
        'url': 'my-ip',
        'only_matching': True,
    }, {
        'url': 'ip',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        amznaws = self._download_webpage('https://checkip.amazonaws.com', None, note=False, fatal=False).strip()
        self.to_screen(amznaws)

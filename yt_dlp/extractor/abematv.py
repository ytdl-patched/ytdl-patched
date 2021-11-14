# https://docs.python.org/ja/3/library/urllib.request.html
# https://github.com/python/cpython/blob/f4c03484da59049eb62a9bf7777b963e2267d187/Lib/urllib/request.py#L510
# https://gist.github.com/zhenyi2697/5252805

from .common import InfoExtractor
from ..compat import compat_urllib_request


class AbemaLicenseHandler(compat_urllib_request.BaseHandler):
    STRTABLE = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    HKEY = b'3AF0298C219469522A313570E8583005A642E73EDD58E3EA2FB7339D3DF1597E'
    _MEDIATOKEN_API = 'https://api.abema.io/v1/media/token'
    _LICENSE_API = 'https://license.abema.io/abematv-hls'

    def __init__(self, ie: 'AbemaTVIE'):
        # the protcol that this should handle is "abematv-license://"
        # abematv_license_open is just a placeholder for development purposes
        # ref. https://github.com/python/cpython/blob/f4c03484da59049eb62a9bf7777b963e2267d187/Lib/urllib/request.py#L510
        setattr(self, 'abematv-license_open', getattr(self, 'abematv_license_open'))

    def abematv_license_open(self, url):
        pass


class AbemaTVIE(InfoExtractor):
    pass

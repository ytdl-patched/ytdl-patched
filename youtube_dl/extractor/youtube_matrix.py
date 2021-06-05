# coding: utf-8
from __future__ import unicode_literals

from ..compat import compat_str
from ..utils import str_or_none
from .y2mate import Y2mateIE, Y2mateRushingIE

# keep it sync with extractors.py
from .youtube import (
    YoutubeFavouritesIE,
    YoutubeHistoryIE,
    YoutubeTabIE,
    YoutubePlaylistIE,
    YoutubeRecommendedIE,
    YoutubeSearchDateIE,
    YoutubeSearchIE,
    # YoutubeSearchURLIE,
    YoutubeSubscriptionsIE,
    YoutubeTruncatedIDIE,
    YoutubeTruncatedURLIE,
    YoutubeYtBeIE,
    YoutubeYtUserIE,
    YoutubeWatchLaterIE,
)


ytie = (
    YoutubeFavouritesIE,
    YoutubeHistoryIE,
    YoutubeTabIE,
    YoutubePlaylistIE,
    YoutubeRecommendedIE,
    YoutubeSearchDateIE,
    YoutubeSearchIE,
    YoutubeSubscriptionsIE,
    YoutubeTruncatedIDIE,
    YoutubeTruncatedURLIE,
    YoutubeYtBeIE,
    YoutubeYtUserIE,
    YoutubeWatchLaterIE,
)


def _convert_result(ret, prefix):
    if not isinstance(ret, dict):
        return ret

    type = str_or_none(ret.get('_type')) or ''
    if type == 'playlist':
        ret['entries'] = [_convert_result(x, prefix) for x in ret['entries']]
    elif type.startswith('url'):
        ret['url'] = prefix + ret['url']

    if 'ie_key' in ret:
        del ret['ie_key']

    return ret


def _convert_test_only_matching(test, prefix):
    return {
        'url': prefix + test['url'],
        'only_matching': True,
    }


def ___real_extract(self, url):
    url = self.remove_prefix(url)
    try:  # Python 2.x
        real_extract_func = self.BASE_IE._real_extract.__func__
    except (TypeError, AttributeError):
        real_extract_func = self.BASE_IE._real_extract
    ret = real_extract_func(self, url)
    return _convert_result(ret, self.PREFIXES[0])


for base_ie in (Y2mateIE, Y2mateRushingIE):
    for value in ytie:
        key = value.__name__
        obj = value()
        clazz_name = str(base_ie.__name__[:-2] + key[7:])
        clazz_dict = {
            'BASE_IE': value,
            '_real_extract': ___real_extract,
        }

        if hasattr(value, '_TEST') and isinstance(getattr(value, '_TEST'), dict):
            clazz_dict['_TEST'] = _convert_test_only_matching(obj._TEST, base_ie.PREFIXES[0])
        if hasattr(value, '_TESTS') and isinstance(getattr(value, '_TESTS'), list):
            clazz_dict['_TESTS'] = [_convert_test_only_matching(x, base_ie.PREFIXES[0]) for x in obj._TESTS]

        if hasattr(value, 'IE_NAME'):
            ie_name = obj.IE_NAME
            if not isinstance(value.IE_NAME, compat_str):
                ie_name = '%s' % ie_name
            if ie_name.startswith('youtube:'):
                ie_name = base_ie.IE_NAME + ie_name[7:]
            elif ie_name == key[:-2]:
                ie_name = clazz_name[:-2]
            else:
                ie_name = base_ie.IE_NAME + ':' + ie_name
            clazz_dict['IE_NAME'] = ie_name

        if hasattr(value, '_VALID_URL'):
            clazz_dict['_VALID_URL'] = value._VALID_URL

        globals()[clazz_name] = type(clazz_name, (base_ie, value), clazz_dict)

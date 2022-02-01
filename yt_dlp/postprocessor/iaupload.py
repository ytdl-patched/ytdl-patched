from __future__ import unicode_literals

import subprocess
import re
import optparse

from .exec import ExecPP
from ..options import instantiate_parser
from ..utils import (
    encodeArgument,
    PostProcessingError,
)


def _dict_from_options_callback(
        option, opt_str, value, parser,
        allowed_keys=r'[\w-]+', delimiter=':', default_key=None, process=None, multiple_keys=True,
        process_key=str.lower, append=False):

    out_dict = dict(getattr(parser.values, option.dest))
    multiple_args = not isinstance(value, str)
    if multiple_keys:
        allowed_keys = r'(%s)(,(%s))*' % (allowed_keys, allowed_keys)
    mobj = re.match(
        r'(?i)(?P<keys>%s)%s(?P<val>.*)$' % (allowed_keys, delimiter),
        value[0] if multiple_args else value)
    if mobj is not None:
        keys, val = mobj.group('keys').split(','), mobj.group('val')
        if multiple_args:
            val = [val, *value[1:]]
    elif default_key is not None:
        keys, val = [default_key], value
    else:
        raise optparse.OptionValueError(
            'wrong %s formatting; it should be %s, not "%s"' % (opt_str, option.metavar, value))
    try:
        keys = map(process_key, keys) if process_key else keys
        val = process(val) if process else val
    except Exception as err:
        raise optparse.OptionValueError(f'wrong {opt_str} formatting; {err}')
    for key in keys:
        out_dict[key] = out_dict.get(key, []) + [val] if append else val
    setattr(parser.values, option.dest, out_dict)


iaup_options = instantiate_parser()
iaup_options.set_usage('[OPTIONS] IDENTIFIER FILE [FILE...]')

iaup_options.add_option(
    '-q', '--quiet',
    action='store_true', dest='quiet',
    help='Runs without output. Isolated from --quiet option from the outside')
iaup_options.add_option(
    '-d', '--debug',
    action='store_true', dest='debug',
    help='Runs in debug mode')

iaup_options.add_option(
    '-c', '--config',
    action='store_true', dest='config',
    help='Path to ia.ini. Defaults to where ia command searches')
iaup_options.add_option(
    '-u', '--username',
    dest='username', metavar='USERNAME',
    help='Login to Internet Archive with this account ID')
iaup_options.add_option(
    '-p', '--password',
    dest='password', metavar='PASSWORD',
    help='Account password for Internet Archive. If this option is left out, login will not be done')

iaup_options.add_option(
    '-r', '--remote-name',
    metavar='PATH', dest='remote_name',
    help='Path to remote directory or filename')
iaup_options.add_option(
    '-m', '--metadata',
    metavar='K:V', dest='metadata', default={},
    action='callback', callback=_dict_from_options_callback,
    callback_kwargs={'multiple_keys': False, 'process_key': None},
    help='Metadata to add')
iaup_options.add_option(
    '-H', '--header', '--headers',
    metavar='K:V', dest='headers', default={},
    action='callback', callback=_dict_from_options_callback,
    callback_kwargs={'multiple_keys': False, 'process_key': None},
    help='Header to add')
iaup_options.add_option(
    '-D', '--derive',
    action='store_true', dest='derive', default=False,
    help='Enables "derive" task on IA. derive task is not enabled by default')
iaup_options.add_option(
    '-n', '--no-derive',
    action='store_false', dest='derive', default=False,
    help='Disables "derive" task on IA.')
iaup_options.add_option(
    '-R', '--retries',
    metavar='RETRIES', dest='retries', default=10000,
    type=int, help='Number of retries on SlowDown or connection being disconnected.')
iaup_options.add_option(
    '-t', '--throttled-rate',
    metavar='RATE', dest='throttle', type=int,
    help=('Same as the option with same name on yt-dlp, but for upload in this time. '
          'Downloaded failure caused by this option will count for -R retries.'))
iaup_options.add_option(
    '-D', '--delete',
    action='store_true', dest='delete', default=False,
    help='Deletes files after all files are successfully uploaded.')
iaup_options.add_option(
    '-C', '--conflict-resolve',
    metavar='KIND:BEHAVIOR', dest='conflict_resolve',
    help=('Specifies how to avoid/torelate errors while uploading. '
          'Allowed values for KIND are: size_overflow, no_perm. '
          'Allowed values for BEHAVIOR are: rename_ident, error, skip.'))


class InternetArchiveUploadPP(ExecPP):
    # memo
    #  This item total number of bytes(666) is over the per item size limit of 1099511627776. Please contact info@archive.org for help fitting your data into the archive.
    def run(self, info):
        for tmpl in self.exec_cmd:
            cmd = self.parse_cmd(tmpl, info)
            self.to_screen('Executing command: %s' % cmd)
            retCode = subprocess.call(encodeArgument(cmd), shell=True)
            if retCode != 0:
                raise PostProcessingError('Command returned error code %d' % retCode)
        return [], info

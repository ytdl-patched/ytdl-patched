import functools
import inspect
import re

from ..utils import get_argcount, render_table
from .common import PostProcessor
from ..utils import Namespace, filter_dict


class MetapulatorPP(PostProcessor):
    """
    Metadata manuplator via commands
    """

    def run(self, info):
        for f in self._actions:
            next(filter(lambda x: 0, f(info)), None)
        return [], info

    def interpretter(self, inp, out):
        def f(info):
            data_to_parse = self._downloader.evaluate_outtmpl(template, info)
            self.write_debug(f'Searching for {out_re.pattern!r} in {template!r}')
            match = out_re.search(data_to_parse)
            if match is None:
                self.to_screen(f'Could not interpret {inp!r} as {out!r}')
                return
            for attribute, value in filter_dict(match.groupdict()).items():
                yield (attribute, info.get(attribute, MetadataParserPP.BACKLOG_UNSET))
                info[attribute] = value
                self.to_screen(f'Parsed {attribute} from {template!r}: {value!r}')

        template = self.field_to_template(inp)
        out_re = re.compile(self.format_to_regex(out))
        return f

    def replacer(self, field, search, replace):
        def f(info):
            nonlocal replace
            # let function have info_dict on invocation (for MetadataEditorAugment)
            if inspect.isfunction(replace) and get_argcount(replace) == 2:
                replace = self._functools_partial(replace, info)
            val = info.get(field)
            if val is None:
                self.to_screen(f'Video does not have a {field}')
                return
            elif not isinstance(val, str):
                self.report_warning(f'Cannot replace in field {field} since it is a {type(val).__name__}')
                return
            self.write_debug(f'Replacing all {search!r} in {field} with {replace!r}')
            yield (field, info.get(field, MetadataParserPP.BACKLOG_UNSET))
            info[field], n = search_re.subn(replace, val)
            if n:
                self.to_screen(f'Changed {field} to: {info[field]}')
            else:
                self.to_screen(f'Did not find {search!r} in {field}')

        search_re = re.compile(search)
        return f

    BACKLOG_UNSET = object()
    Actions = Namespace(INTERPRET=interpretter, REPLACE=replacer)


class MetapulatorCommand:
    COMMAND_NAME = False
    HELP = ''

    def run(self, pp: MetapulatorPP, info: dict, args: list) -> None:
        raise Exception('Override this method in child classes')


class PrintCommand(MetapulatorCommand):
    """
    Equivalent to --print option but in Metapulator
    """

    COMMAND_NAME = 'print'
    HELP = """\
Prints the content of metadata. You can use the same notation for --print
This accepts multiple queries at a time

Examples:
print title
print "%(subtitles.en.-1.ext)s"
print "%(id.3:7:-1)s" "%(formats.:.format_id)s"

Refer to https://github.com/yt-dlp/yt-dlp#output-template for the query details
"""

    def run(self, pp, info, args):
        info = info.copy()

        def format_tmpl(tmpl):
            mobj = re.match(r'\w+(=?)$', tmpl)
            if mobj and mobj.group(1):
                return f'{tmpl[:-1]} = %({tmpl[:-1]})r'
            elif mobj:
                return f'%({tmpl})s'
            return tmpl

        for tmpl in args:
            pp.to_screen(pp._downloader.evaluate_outtmpl(format_tmpl(tmpl), info))


class ChaptersCommand(MetapulatorCommand):
    """
    Command to manuplate and view chapters
    """

    COMMAND_NAME = 'chapters'
    HELP = """\
Manuplates or displays chapters for this video.
"""

    def run(self, pp, info, args):
        ydl = pp._downloader
        if not args or 'view'.startswith(args[0]):
            # view
            chap = info.get('chapters')
            if not chap:
                pp.to_screen('There are no chapters')
                return

            if not isinstance(chap, list):
                pp.report_warning('Extracted chapters are in unexpected structures. Fix extractor code')
                return

            cs = len(chap)
            pp.to_screen(f'There are {cs} chapters:' if cs > 1 else 'There is one chapter:')
            delim = ydl._format_out('\u2502', ydl.Styles.DELIM, '|', test_encoding=True)
            header_line = ydl._list_format_headers('INDEX', delim, 'START', 'END', delim, 'TITLE')

            table = [[
                ch.get('index'),  # INDEX
                delim,
                ch.get('start_time', 0),  # START
                ch.get('end_time',
                    ydl._format_out('???', ydl.Styles.SUPPRESS)),  # END
                delim,
                ch.get('index'),  # TITLE
            ] for ch in chap]
            tbl = render_table(
                header_line, table, hide_empty=True,
                delim=ydl._format_out('\u2500', ydl.Styles.DELIM, '-', test_encoding=True))
            pp.to_screen(tbl, False)
            return
        elif 'add'.startswith(args[0]):
            # add START END [TITLE]
            return
        elif 'insert'.startswith(args[0]):
            # insert INDEX START END [TITLE]
            return
        elif 'remove'.startswith(args[0]):
            # remove [idx:]INDEX[-INDEX_END]|[t:]TITLE_REGEX
            return
        elif 'sort'.startswith(args[0]):
            # sort
            return
        pp.to_screen(f'Unknown command: {args[0]!r}. Use "help {self.COMMAND_NAME}" to see help')

import json
import re
import shlex

from math import inf

from ..utils import parse_duration, render_table
from .common import PostProcessor


class MetapulatorPP(PostProcessor):
    """
    Metadata manuplator via commands
    """

    COMMANDS = {}  # command, object

    def __init__(self, downloader, manual=False, auto=None):
        super().__init__(downloader)
        self.COMMANDS = dict((x.COMMAND_NAME, x()) for x in CLASSES)
        self.manual = manual
        self.auto = auto

    def _yield_commands(self):
        yield from (self.auto or [])
        yield from (self.get_param('metapulator_auto') or [])
        if not (self.get_param('metapulator_manual') or self.manual):
            return
        self.to_screen('Metapulator REPL. Type "help" for help')
        while True:
            try:
                yield input('>>> ')
            except EOFError:
                self.to_screen('', prefix=False)
                break
            except KeyboardInterrupt:
                self.to_screen('', prefix=False)
                self.to_screen('Ctrl+C has pressed, continuing postprocessing')
                break

    def run(self, info):
        for f in self._yield_commands():
            if not f:
                continue
            try:
                self.execute_line(f, info)
            except Exit:
                break
        return [], info

    def find_command(self, cmd):
        if not cmd:
            return None
        for name, value in self.COMMANDS.items():
            # shortest match
            if name.startswith(cmd):
                return value
        return None

    def execute_line(self, line, info):
        args = shlex.split(line)
        cmd = self.find_command(args[0])
        if cmd is None:
            self._downloader.report_error(f'Command {args[0]!r} does not exist')
            return
        try:
            cmd.run(self, info, args[1:])
        except ShowHelp:
            self.print_help(cmd)

    def print_help(self, cmd):
        if isinstance(cmd, str):
            cmd = self.find_command(cmd)
        if not cmd:
            return
        self.to_screen(f'Help for {cmd.COMMAND_NAME!r}')
        self.to_screen(cmd.HELP, False)


class ShowHelp(Exception):
    pass


class Exit(Exception):
    pass


class MetapulatorCommand:
    COMMAND_NAME = False
    HELP = ''

    def run(self, pp: MetapulatorPP, info: dict, args: list) -> None:
        raise Exception('Override this method in child classes')


class ExitCommand(MetapulatorCommand):
    """
    Stops Metapulator
    """

    COMMAND_NAME = 'exit'
    HELP = "Stops Metapulator"

    def run(self, pp, info, args):
        raise Exit()


class PrintCommand(MetapulatorCommand):
    """
    Equivalent to --print option but in Metapulator
    """

    COMMAND_NAME = 'print'
    HELP = """\
Prints the content of metadata. You can use the same notation as --print
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
            pp.to_screen(pp._downloader.evaluate_outtmpl(format_tmpl(tmpl), info), prefix=False)


class ChaptersCommand(MetapulatorCommand):
    """
    Command to manuplate and view chapters
    """

    COMMAND_NAME = 'chapters'
    HELP = """\
Manuplates or displays chapters for this video.
Note that this command will not trim the video, but just change it on metadata.

Synopsis: chapters [view]
Show currently available chapters.

Synopsis: chapters add START END [TITLE]
Add a chapter, optionally with a title.
START and END are in seconds.

Synopsis: chapters insert INDEX START END [TITLE]
Insert a new chapter, optionally with a title.
START and END are in seconds.

Synopsis: chapters remove [idx:]INDEX[-INDEX_END]
Remove chapters by indices. Range is inclusive.

Synopsis: chapters remove [t:]TIME-RANGE
Remove chapters by duration. Range is inclusive.

Synopsis: chapters remove [re:]TITLE_REGEX
Remove chapters by title.

Synopsis: chapters sort
Sort chapters. It is highly recommended to run it before finishing manuplation.
"""

    def run(self, pp, info, args):
        ydl = pp._downloader

        def getchap():
            chap = info.get('chapters')
            if not isinstance(chap, list):
                pp.write_debug('setting the new chapter list')
                chap = info['chapters'] = []
            return chap

        if not args or 'view'.startswith(args[0]):
            # view
            chap = info.get('chapters')
            if not chap:
                pp.to_screen('There are no chapters')
                return

            if not isinstance(chap, list):
                pp.report_warning('Extracted chapters are in unexpected structure. Fix extractor code')
                return

            cs = len(chap)
            pp.to_screen(f'There are {cs} chapters:' if cs > 1 else 'There is one chapter:')
            delim = ydl._format_out('\u2502', ydl.Styles.DELIM, '|', test_encoding=True)
            header_line = ydl._list_format_headers('INDEX', delim, 'START', 'END', delim, 'TITLE')

            table = [[
                ch.get('index'),  # INDEX
                delim,
                ch.get('start_time', 0),  # START
                ch.get('end_time', ydl._format_out('???', ydl.Styles.SUPPRESS)),  # END
                delim,
                ch.get('title'),  # TITLE
            ] for ch in chap]
            tbl = render_table(
                header_line, table, hide_empty=True,
                delim=ydl._format_out('\u2500', ydl.Styles.DELIM, '-', test_encoding=True))
            pp.to_screen(tbl, False)
            return
        elif 'add'.startswith(args[0]):
            # add START END [TITLE]
            start, end, *title = args[1:]
            start, end = map(parse_duration, (start, end))
            title = title[0] if title else None
            getchap().append({
                'start_time': start,
                'end_time': end,
                'title': title,
            })
            pp.to_screen(f'Added chapter (start={start} end={end} title={title})')
            return
        elif 'insert'.startswith(args[0]):
            # insert INDEX START END [TITLE]
            index, start, end, *title = args[1:]
            index = int(index)
            start, end = map(parse_duration, (start, end))
            title = title[0] if title else None
            getchap().insert(index, {
                'start_time': start,
                'end_time': end,
                'title': title,
            })
            pp.to_screen(f'Added chapter at index {index} (start={start} end={end} title={title})')
            return
        elif 'remove'.startswith(args[0]):
            # remove [idx:]INDEX[-INDEX_END]|[t:]TIME-RANGE|[re:]TITLE_REGEX

            def find_mode():
                candidates = []
                mobj = re.fullmatch(r'(idx:)?(\d+)(?:-(\d+))?', args[1])
                if mobj:
                    pfx, s1, e1 = mobj.groups()

                    def selector(chap):
                        return s1 < chap[0] and chap[0] < e1

                    if pfx:
                        return selector
                    candidates.append(selector)

                mobj = re.fullmatch(r'(t:)?(\d+)(?:-(\d+))?', args[1])
                if mobj:
                    pfx, s2, e2 = mobj.groups()

                    def selector(chap):
                        chap = chap[1]
                        cs = chap.get('start_time') or 0
                        ce = chap.get('end_time')
                        if ce is None:
                            ce = inf
                        return (s2 < cs and cs < e2) or (s2 < ce and ce < e2)

                    if pfx:
                        return selector
                    candidates.append(selector)

                mobj = re.fullmatch(r'(re:)?(.+)', args[1])
                while mobj:
                    pfx, tre = mobj.groups()
                    try:
                        cre = re.compile(tre)
                    except re.error:
                        break

                    def selector(chap):
                        chap = chap[1]
                        return bool(re.match(cre, chap.get('title') or ''))

                    if pfx:
                        return selector
                    candidates.append(selector)
                    break

                return next(candidates, None)

            selector = find_mode()
            if not selector:
                pp.to_screen(f'Invalid selector: {args[1]}')
                return

            chap = getchap()
            chap[:] = map(lambda x: x[1], filter(selector, enumerate(chap)))

            return
        elif 'sort'.startswith(args[0]):
            # sort
            end = info.get('duration', None) or 0

            def _sort(x):
                return (
                    x.get('start_time') or 0,
                    x.get('end_time') or end,
                    x.get('index') or 0,
                    x.get('title') or '',)

            chap = getchap()
            chap.sort(key=_sort)

            for i, x in enumerate(chap):
                x['index'] = i

            pp.to_screen(f'Sorted {len(chap)} chapters')
            return
        pp.to_screen(f'Unknown command: {args[0]!r}. Use "help {self.COMMAND_NAME}" to see help')


class SetValueCommand(MetapulatorCommand):
    """
    Command to set a value to a key
    """

    COMMAND_NAME = 'setvalue'
    HELP = """\
Synopsis: setvalue KEY [TYPE] VALUE

Command to set a value to a key.

TYPE can be any of: "string", "int", "float" and "json"
Defaults to "string" if skipped.

For "int" and "float", the VALUE must be an interger or a decimal number.

For "json", the VALUE must be a valid JSON.
"""

    def run(self, pp, info, args):
        if len(args) not in (2, 3):
            raise ShowHelp()
        _type = 'string'
        if len(args) == 2:
            key, value_str = args
        elif len(args) == 3:
            key, _type, value_str = args
        _type = _type.lower()
        value = value_str
        if _type == 'int':
            value = int(value_str)
        elif _type == 'float':
            value = float(value_str)
        elif _type == 'json':
            value = json.loads(value_str)
        info[key] = value


class HelpCommand(MetapulatorCommand):
    """
    Command to show help
    """

    COMMAND_NAME = 'help'
    HELP = """\
Synopsis: help [COMMAND]

If COMMAND is not given, it shows all of the available commands.
"""

    def run(self, pp, info, args):
        if not args:
            pp.to_screen('All available commands:')
            pp.to_screen('\n'.join(sorted(pp.COMMANDS.keys())), False)
            return
        cmd = pp.find_command(args[0])
        if not cmd:
            pp.to_screen(f'Command {args[0]!r} not found')
            return
        pp.print_help(cmd)


CLASSES = (ExitCommand, PrintCommand, ChaptersCommand, SetValueCommand, HelpCommand)

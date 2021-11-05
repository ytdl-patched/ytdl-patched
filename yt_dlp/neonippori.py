# coding: utf-8
from __future__ import unicode_literals

# NeoNippori - Danmaku to ASS converter for "Unlicense"d applications

import io
import json
import math
import random
import re
import xml.dom.minidom
import xml.etree.ElementTree as ET
from .version import __version__


def noop(*a, **b):
    return


NICONICO_COLOR_MAPPINGS = {
    'red': 0xff0000,
    'pink': 0xff8080,
    'orange': 0xffcc00,
    'yellow': 0xffff00,
    'green': 0x00ff00,
    'cyan': 0x00ffff,
    'blue': 0x0000ff,
    'purple': 0xc000ff,
    'black': 0x000000,
    'niconicowhite': 0xcccc99,
    'white2': 0xcccc99,
    'truered': 0xcc0033,
    'red2': 0xcc0033,
    'passionorange': 0xff6600,
    'orange2': 0xff6600,
    'madyellow': 0x999900,
    'yellow2': 0x999900,
    'elementalgreen': 0x00cc66,
    'green2': 0x00cc66,
    'marineblue': 0x33ffcc,
    'blue2': 0x33ffcc,
    'nobleviolet': 0x6633cc,
    'purple2': 0x6633cc}


def process_mailstyle(mail, fontsize):
    pos = 0
    color = 0xffffff
    size = fontsize
    for mailstyle in str(mail).split():
        if mailstyle == 'ue':
            pos = 1
        elif mailstyle == 'shita':
            pos = 2
        elif mailstyle == 'big':
            size = fontsize * 1.44
        elif mailstyle == 'small':
            size = fontsize * 0.64
        elif mailstyle in NICONICO_COLOR_MAPPINGS:
            color = NICONICO_COLOR_MAPPINGS[mailstyle]
    return pos, color, size


def parse_comments_nnxml(f: str, fontsize: float, report_warning):
    """ (timeline, timestamp, no, comment, pos, color, size, height, width) """
    dom = xml.dom.minidom.parse(f)
    comment_element = dom.getElementsByTagName('chat')
    for comment in comment_element:
        try:
            c = str(comment.childNodes[0].wholeText)
            if c.startswith('/'):
                continue  # ignore advanced comments
            pos, color, size = process_mailstyle(comment.getAttribute('mail'), fontsize)
            yield (max(int(comment.getAttribute('vpos')), 0) * 0.01, int(comment.getAttribute('date')), int(comment.getAttribute('no')), c, pos, color, size, (c.count('\n') + 1) * size, maximum_line_length(c) * size)
        except (AssertionError, AttributeError, IndexError, TypeError, ValueError) as e:
            report_warning('Invalid comment: %s %s' % (e, comment.toxml()))
            continue


def parse_comments_nnjson(f: str, fontsize: float, report_warning):
    for comment_dom in json.loads(f):
        comment = None

        if 'chat' in comment_dom:
            comment = comment_dom['chat']
        elif 'content' in comment_dom:
            comment = comment_dom
        else:
            continue

        try:
            if 'deleted' in comment:
                continue

            c = comment['content']
            if c.startswith('/'):
                continue  # ignore advanced comments

            pos, color, size = process_mailstyle(comment.get('mail', ''), fontsize)
            yield (max(comment['vpos'], 0) * 0.01, comment['date'], comment.get('no', 0), c, pos, color, size, (c.count('\n') + 1) * size, maximum_line_length(c) * size)
        except (AssertionError, AttributeError, IndexError, TypeError, ValueError, KeyError) as e:
            report_warning('Invalid comment: %s %s' % (e, comment and json.dumps(comment)))
            continue


def _subelem(parent, tag, text: str = None, **extra: dict):
    extra = {k: str(v) for k, v in extra.items()}
    e = ET.SubElement(parent, tag, **extra)
    if text:
        e.text = text


def convert_niconico_json_to_xml(data: str) -> str:
    # https://github.com/Hayao-H/Niconicome/blob/master/Niconicome/Models/Domain/Niconico/Download/Comment/CommentConverter.cs
    # https://github.com/Hayao-H/Niconicome/blob/master/Niconicome/Models/Domain/Niconico/Net/Xml/Comment/Comment.cs
    packet = ET.Element("packet")
    for item in json.loads(data):
        if 'chat' in item or 'content' in item:
            comment = item.get('chat') or item
            if 'deleted' in comment:
                continue
            _subelem(
                packet, "chat",
                text=comment.get('content'),
                thread=comment.get('thread') or '',
                no=comment.get('no'),
                vpos=comment.get('vpos'),
                date=comment.get('date'),
                anonymity=comment.get('anonymity') or 0,
                user_id=comment.get('user_id'),
                mail=comment.get('mail'),
                premium=comment.get('premium') or 1,
            )
        elif 'thread' in item:
            thread = item.get('thread')
            _subelem(
                packet, "thread",
                resultcode=thread.get('resultcode') or 0,
                thread=thread.get('thread') or '',
                server_time=thread.get('server_time') or 0,
                last_res=thread.get('last_res') or 0,
                ticket=thread.get('ticket') or '',
                revision=thread.get('revision') or 0,
            )

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(packet, encoding='utf-8').decode('utf-8')


def process_comments(comments, f, width, height, bottomReserved, fontface, fontsize, alpha, duration_marquee, duration_still, report_warning):
    styleid = 'NeoNippori_%04x' % random.randint(0, 0xffff)
    write_ass_header(f, width, height, fontface, fontsize, alpha, styleid)
    rows = [[None] * (height - bottomReserved + 1) for i in range(4)]
    for i in comments:
        if isinstance(i[4], int):
            row = 0
            rowmax = height - bottomReserved - i[7]
            while row <= rowmax:
                freerows = test_free_rows(rows, i, row, width, height, bottomReserved, duration_marquee, duration_still)
                if freerows >= i[7]:
                    mark_comment_raw(rows, i, row)
                    write_comment(f, i, row, width, height, bottomReserved, fontsize, duration_marquee, duration_still, styleid)
                    break
                else:
                    row += freerows or 1
            else:
                row = find_alternative_row(rows, i, height, bottomReserved)
                mark_comment_raw(rows, i, row)
                write_comment(f, i, row, width, height, bottomReserved, fontsize, duration_marquee, duration_still, styleid)
        else:
            report_warning('Invalid comment: %r' % i[3])


def test_free_rows(rows, c, row, width, height, bottomReserved, duration_marquee, duration_still):
    res = 0
    rowmax = height - bottomReserved
    targetRow = None
    if c[4] in (1, 2):
        while row < rowmax and res < c[7]:
            if targetRow != rows[c[4]][row]:
                targetRow = rows[c[4]][row]
                if targetRow and targetRow[0] + duration_still > c[0]:
                    break
            row += 1
            res += 1
    else:
        try:
            thresholdTime = c[0] - duration_marquee * (1 - width / (c[8] + width))
        except ZeroDivisionError:
            thresholdTime = c[0] - duration_marquee
        while row < rowmax and res < c[7]:
            if targetRow != rows[c[4]][row]:
                targetRow = rows[c[4]][row]
                try:
                    if targetRow and (targetRow[0] > thresholdTime or targetRow[0] + targetRow[8] * duration_marquee / (targetRow[8] + width) > c[0]):
                        break
                except ZeroDivisionError:
                    pass
            row += 1
            res += 1
    return res


def find_alternative_row(rows, c, height, bottomReserved):
    res = 0
    for row in range(height - bottomReserved - math.ceil(c[7])):
        if not rows[c[4]][row]:
            return row
        elif rows[c[4]][row][0] < rows[c[4]][res][0]:
            res = row
    return res


def mark_comment_raw(rows, c, row):
    try:
        for i in range(row, row + math.ceil(c[7])):
            rows[c[4]][i] = c
    except IndexError:
        pass


def write_ass_header(f, width, height, fontface, fontsize, alpha, styleid):
    f.write(
        '''[Script Info]
; NeoNippori (ネオ日暮里) %(version)s
; Converted from Danmaku comments
; https://github.com/ytdl-patched/ytdl-patched/blob/ytdlp/yt_dlp/neonippori.py
Script Updated By: NeoNippori %(version)s (https://github.com/ytdl-patched/ytdl-patched/blob/ytdlp/yt_dlp/neonippori.py)
ScriptType: v4.00+
PlayResX: %(width)d
PlayResY: %(height)d
Aspect Ratio: %(width)d:%(height)d
Collisions: Normal
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: %(styleid)s, %(fontface)s, %(fontsize).0f, &H%(alpha)02XFFFFFF, &H%(alpha)02XFFFFFF, &H%(alpha)02X000000, &H%(alpha)02X000000, 0, 0, 0, 0, 100, 100, 0.00, 0.00, 1, %(outline).0f, 0, 7, 0, 0, 0, 0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
''' % {'width': width, 'height': height, 'fontface': fontface, 'fontsize': fontsize, 'alpha': 255 - round(alpha * 255), 'outline': max(fontsize / 25.0, 1), 'styleid': styleid, 'version': __version__}
    )


def write_comment(f, c, row, width, height, bottomReserved, fontsize, duration_marquee, duration_still, styleid):
    text = escape_ass_text(c[3])
    styles = []
    if c[4] == 1:
        styles.append('\\an8\\pos(%(halfwidth)d, %(row)d)' % {'halfwidth': width / 2, 'row': row})
        duration = duration_still
    elif c[4] == 2:
        styles.append('\\an2\\pos(%(halfwidth)d, %(row)d)' % {'halfwidth': width / 2, 'row': convert_type2(row, height, bottomReserved)})
        duration = duration_still
    elif c[4] == 3:
        styles.append('\\move(%(neglen)d, %(row)d, %(width)d, %(row)d)' % {'width': width, 'row': row, 'neglen': -math.ceil(c[8])})
        duration = duration_marquee
    else:
        styles.append('\\move(%(width)d, %(row)d, %(neglen)d, %(row)d)' % {'width': width, 'row': row, 'neglen': -math.ceil(c[8])})
        duration = duration_marquee
    if not (-1 < c[6] - fontsize < 1):
        styles.append('\\fs%.0f' % c[6])
    if c[5] != 0xffffff:
        styles.append('\\c&H%s&' % format_color(c[5]))
        if c[5] == 0x000000:
            styles.append('\\3c&HFFFFFF&')
    f.write('Dialogue: 2,%(start)s,%(end)s,%(styleid)s,,0000,0000,0000,,{%(styles)s}%(text)s\n' % {'start': format_timestamp(c[0]), 'end': format_timestamp(c[0] + duration), 'styles': ''.join(styles), 'text': text, 'styleid': styleid})


def escape_ass_text(s):
    def process_leading_blank(s):
        sstrip = s.strip(' ')
        slen = len(s)
        if slen == len(sstrip):
            return s
        else:
            llen = slen - len(s.lstrip(' '))
            rlen = slen - len(s.rstrip(' '))
            return ''.join(('\u2007' * llen, sstrip, '\u2007' * rlen))
    return '\\N'.join((process_leading_blank(i) or ' ' for i in str(s).replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}').split('\n')))


def maximum_line_length(s: str):
    return max(len(s) for s in s.split('\n'))  # May not be accurate


def format_timestamp(timestamp: float):
    timestamp = round(timestamp * 100.0)
    hour, minute = divmod(timestamp, 360000)
    minute, second = divmod(minute, 6000)
    second, centsecond = divmod(second, 100)
    return '%d:%02d:%02d.%02d' % (int(hour), int(minute), int(second), int(centsecond))


def format_color(color):
    if color == 0x000000:
        return '000000'
    elif color == 0xffffff:
        return 'FFFFFF'
    R = (color >> 16) & 0xff
    G = (color >> 8) & 0xff
    B = color & 0xff

    return '%02X%02X%02X' % (B, G, R)


def convert_type2(row, height, bottomReserved):
    return height - bottomReserved - row


def filter_badchars(f):
    return re.sub('[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f]', '\ufffd', f)


PROCESSORS = {
    'Niconico': parse_comments_nnxml,
    'NiconicoJson': parse_comments_nnjson,
}


def parse_comments(input_text, input_format, font_size=25.0, report_warning=noop):
    processor = PROCESSORS.get(input_format)
    if not processor:
        raise ValueError('Unknown comment file format: %s' % input_format)
    comments = list(processor(filter_badchars(input_text), font_size, report_warning))
    comments.sort()
    return comments


def load_comments(input_text, input_format, stage_width, stage_height, reserve_blank=0, font_face='sans-serif', font_size=25.0, text_opacity=1.0, duration_marquee=5.0, duration_still=5.0, report_warning=noop):
    comments = parse_comments(input_text, input_format, font_size, report_warning)
    with io.StringIO() as fo:
        process_comments(comments, fo, stage_width, stage_height, reserve_blank, font_face, font_size, text_opacity, duration_marquee, duration_still, report_warning)
        return fo.getvalue()


__all__ = [
    'load_comments',
    'convert_niconico_json_to_xml',
]

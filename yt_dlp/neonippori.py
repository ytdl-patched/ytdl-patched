# coding: utf-8
from __future__ import unicode_literals

# NeoNippori - Danmaku to ASS converter for "Unlicense"d applications

import io
import json
import math
import random
import re
import xml.dom.minidom
from typing import Dict, Tuple


def ensure_file_at_beggining(func):
    def decorator(f):
        f.seek(0)
        try:
            return func(f)
        finally:
            f.seek(0)
    return decorator


def ignore_eof_error(func):
    def decorator(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except EOFError:
            return None
    return decorator


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


def parse_comments_nnxml(f: str, fontsize: float, report_warning):
    dom = xml.dom.minidom.parse(f)
    comment_element = dom.getElementsByTagName('chat')
    for comment in comment_element:
        try:
            c = str(comment.childNodes[0].wholeText)
            if c.startswith('/'):
                continue  # ignore advanced comments
            pos = 0
            color = 0xffffff
            size = fontsize
            for mailstyle in str(comment.getAttribute('mail')).split():
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
            yield (max(int(comment.getAttribute('vpos')), 0) * 0.01, int(comment.getAttribute('date')), int(comment.getAttribute('no')), c, pos, color, size, (c.count('\n') + 1) * size, maximum_line_length(c) * size)
        except (AssertionError, AttributeError, IndexError, TypeError, ValueError):
            report_warning('Invalid comment: %s' % comment.toxml())
            continue


def parse_comments_nnjson(f: str, fontsize: float, report_warning):
    for comment_dom in json.load(f):
        comment = None

        if 'chat' in comment_dom:
            comment = comment_dom['chat']
        elif 'mail' in comment_dom:
            comment = comment_dom
        else:
            continue

        try:
            c = comment['content']

            pos = 0
            color = 0xffffff
            size = fontsize
            for mailstyle in comment['mail'].split():
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

            yield (max(comment['vpos'], 0) * 0.01, comment['date'], comment.get('no', 0), c, pos, color, size, (c.count('\n') + 1) * size, maximum_line_length(c) * size)
        except (AssertionError, AttributeError, IndexError, TypeError, ValueError, KeyError):
            report_warning('Invalid comment: %s' % (comment and json.dumps(comment)))
            continue


def parse_comments_bilibili(f: str, fontsize: float, report_warning):
    dom = xml.dom.minidom.parse(f)
    comment_element = dom.getElementsByTagName('d')
    for i, comment in enumerate(comment_element):
        try:
            p = str(comment.getAttribute('p')).split(',')
            assert len(p) >= 5
            assert p[1] in ('1', '4', '5', '6', '7', '8')
            if comment.childNodes.length <= 0:
                continue
            if p[1] in ('1', '4', '5', '6'):
                c = str(comment.childNodes[0].wholeText).replace('/n', '\n')
                size = int(p[2]) * fontsize / 25.0
                yield (float(p[0]), int(p[4]), i, c, {'1': 0, '4': 2, '5': 1, '6': 3}[p[1]], int(p[3]), size, (c.count('\n') + 1) * size, maximum_line_length(c) * size)
            elif p[1] == '7':  # positioned comment
                c = str(comment.childNodes[0].wholeText)
                yield (float(p[0]), int(p[4]), i, c, 'bilipos', int(p[3]), int(p[2]), 0, 0)
            elif p[1] == '8':
                pass  # ignore scripted comment
        except (AssertionError, AttributeError, IndexError, TypeError, ValueError):
            report_warning('Invalid comment: %s' % comment.toxml())
            continue


def parse_comments_bilibili2(f: str, fontsize: float, report_warning):
    dom = xml.dom.minidom.parse(f)
    comment_element = dom.getElementsByTagName('d')
    for i, comment in enumerate(comment_element):
        try:
            p = str(comment.getAttribute('p')).split(',')
            assert len(p) >= 7
            assert p[3] in ('1', '4', '5', '6', '7', '8')
            if comment.childNodes.length <= 0:
                continue
            time = float(p[2]) / 1000.0
            if p[3] in ('1', '4', '5', '6'):
                c = str(comment.childNodes[0].wholeText).replace('/n', '\n')
                size = int(p[4]) * fontsize / 25.0
                yield (time, int(p[6]), i, c, {'1': 0, '4': 2, '5': 1, '6': 3}[p[3]], int(p[5]), size, (c.count('\n') + 1) * size, maximum_line_length(c) * size)
            elif p[3] == '7':  # positioned comment
                c = str(comment.childNodes[0].wholeText)
                yield (time, int(p[6]), i, c, 'bilipos', int(p[5]), int(p[4]), 0, 0)
            elif p[3] == '8':
                pass  # ignore scripted comment
        except (AssertionError, AttributeError, IndexError, TypeError, ValueError):
            report_warning('Invalid comment: %s' % comment.toxml())
            continue


PROCESSORS = {
    'Niconico': parse_comments_nnxml,
    'NiconicoJson': parse_comments_nnjson,
    'Bilibili': parse_comments_bilibili,
    'Bilibili2': parse_comments_bilibili2,
}


def write_danmaku_positioned_bilibili(f, c, width, height, styleid, player_size=(672, 438), report_warning=noop):
    zoom_factor = calculate_zoom_factor(player_size, (width, height))

    def get_position(input_pos, is_height):
        is_height = int(is_height)  # True -> 1
        if isinstance(input_pos, int):
            return zoom_factor[0] * input_pos + zoom_factor[is_height + 1]
        elif isinstance(input_pos, float):
            if input_pos > 1:
                return zoom_factor[0] * input_pos + zoom_factor[is_height + 1]
            else:
                return player_size[is_height] * zoom_factor[0] * input_pos + zoom_factor[is_height + 1]
        else:
            input_pos = float(input_pos)
            return get_position(input_pos, is_height)

    try:
        comment_args = safe_list(json.loads(c[3]))
        text = escape_ass_text(str(comment_args[4]).replace('/n', '\n'))
        from_x = comment_args.get(0, 0)
        from_y = comment_args.get(1, 0)
        to_x = comment_args.get(7, from_x)
        to_y = comment_args.get(8, from_y)
        from_x = get_position(from_x, False)
        from_y = get_position(from_y, True)
        to_x = get_position(to_x, False)
        to_y = get_position(to_y, True)
        alpha = safe_list(str(comment_args.get(2, '1')).split('-'))
        from_alpha = float(alpha.get(0, 1))
        to_alpha = float(alpha.get(1, from_alpha))
        from_alpha = 255 - round(from_alpha * 255)
        to_alpha = 255 - round(to_alpha * 255)
        rotate_z = int(comment_args.get(5, 0))
        rotate_y = int(comment_args.get(6, 0))
        lifetime = float(comment_args.get(3, 4500))
        duration = int(comment_args.get(9, lifetime * 1000))
        delay = int(comment_args.get(10, 0))
        fontface = comment_args.get(12)
        isborder = comment_args.get(11, 'true')
        from_rotarg = convert_flash_rot(rotate_y, rotate_z, from_x, from_y, width, height)
        to_rotarg = convert_flash_rot(rotate_y, rotate_z, to_x, to_y, width, height)
        styles = ['\\org(%d, %d)' % (width / 2, height / 2)]
        if from_rotarg[0:2] == to_rotarg[0:2]:
            styles.append('\\pos(%.0f, %.0f)' % (from_rotarg[0:2]))
        else:
            styles.append('\\move(%.0f, %.0f, %.0f, %.0f, %.0f, %.0f)' % (from_rotarg[0:2] + to_rotarg[0:2] + (delay, delay + duration)))
        styles.append('\\frx%.0f\\fry%.0f\\frz%.0f\\fscx%.0f\\fscy%.0f' % (from_rotarg[2:7]))
        if (from_x, from_y) != (to_x, to_y):
            styles.append('\\t(%d, %d, ' % (delay, delay + duration))
            styles.append('\\frx%.0f\\fry%.0f\\frz%.0f\\fscx%.0f\\fscy%.0f' % (to_rotarg[2:7]))
            styles.append(')')
        if fontface:
            styles.append('\\fn%s' % escape_ass_text(fontface))
        styles.append('\\fs%.0f' % (c[6] * zoom_factor[0]))
        if c[5] != 0xffffff:
            styles.append('\\c&H%s&' % format_color(c[5]))
            if c[5] == 0x000000:
                styles.append('\\3c&HFFFFFF&')
        if from_alpha == to_alpha:
            styles.append('\\alpha&H%02X' % from_alpha)
        elif (from_alpha, to_alpha) == (255, 0):
            styles.append('\\fad(%.0f,0)' % (lifetime * 1000))
        elif (from_alpha, to_alpha) == (0, 255):
            styles.append('\\fad(0, %.0f)' % (lifetime * 1000))
        else:
            styles.append('\\fade(%(from_alpha)d, %(to_alpha)d, %(to_alpha)d, 0, %(end_time).0f, %(end_time).0f, %(end_time).0f)' % {'from_alpha': from_alpha, 'to_alpha': to_alpha, 'end_time': lifetime * 1000})
        if isborder == 'false':
            styles.append('\\bord0')
        f.write('Dialogue: -1,%(start)s,%(end)s,%(styleid)s,,0,0,0,,{%(styles)s}%(text)s\n' % {'start': format_timestamp(c[0]), 'end': format_timestamp(c[0] + lifetime), 'styles': ''.join(styles), 'text': text, 'styleid': styleid})
    except (IndexError, ValueError):
        try:
            report_warning('Invalid comment: %r' % c[3])
        except IndexError:
            report_warning('Invalid comment: %r' % c)


def calculate_zoom_factor_raw(source: Tuple[float, float], target: Tuple[float, float]) -> Tuple[float, float, float]:
    try:
        source_ratio = source[0] / source[1]
        target_ratio = target[0] / target[1]
        if target_ratio < source_ratio:  # narrower
            scale_factor = target[0] / source[0]
            return scale_factor, 0, (target[1] - target[0] / (source_ratio * 2))
        elif target_ratio > source_ratio:  # wider
            scale_factor = target[1] / source[1]
            return scale_factor, (target[0] - target[1] * source_ratio) / 2, 0
        else:
            return target[0] / source[0], 0, 0
    except ZeroDivisionError:
        return 1, 0, 0


ZOOM_FACTOR_CACHE: Dict[
    Tuple[Tuple[float, float], Tuple[float, float]],
    Tuple[float, float, float]
] = {}


def calculate_zoom_factor(source, target):
    k = (source, target)
    if k not in ZOOM_FACTOR_CACHE:
        ZOOM_FACTOR_CACHE[k] = calculate_zoom_factor_raw(source, target)
    return ZOOM_FACTOR_CACHE[k]


def cap_angle(deg):
    return 180 - ((180 - deg) % 360)


def convert_flash_rot(rotY, rotZ, X, Y, width, height, report_warning):
    rotY = cap_angle(rotY)
    rotZ = cap_angle(rotZ)
    if rotY in (90, -90):
        rotY -= 1
    if rotY == 0 or rotZ == 0:
        outX = 0
        outY = -rotY  # Positive value means clockwise in Flash
        outZ = -rotZ
        rotY *= math.pi / 180.0
        rotZ *= math.pi / 180.0
    else:
        rotY *= math.pi / 180.0
        rotZ *= math.pi / 180.0
        outY = math.atan2(-math.sin(rotY) * math.cos(rotZ), math.cos(rotY)) * 180 / math.pi
        outZ = math.atan2(-math.cos(rotY) * math.sin(rotZ), math.cos(rotZ)) * 180 / math.pi
        outX = math.asin(math.sin(rotY) * math.sin(rotZ)) * 180 / math.pi
    trX = (X * math.cos(rotZ) + Y * math.sin(rotZ)) / math.cos(rotY) + (1 - math.cos(rotZ) / math.cos(rotY)) * width / 2 - math.sin(rotZ) / math.cos(rotY) * height / 2
    trY = Y * math.cos(rotZ) - X * math.sin(rotZ) + math.sin(rotZ) * width / 2 + (1 - math.cos(rotZ)) * height / 2
    trZ = (trX - width / 2) * math.sin(rotY)
    FOV = width * math.tan(2 * math.pi / 9.0) / 2
    try:
        scaleXY = FOV / (FOV + trZ)
    except ZeroDivisionError:
        report_warning('Rotation makes object behind the camera: trZ == %.0f' % trZ)
        scaleXY = 1
    trX = (trX - width / 2) * scaleXY + width / 2
    trY = (trY - height / 2) * scaleXY + height / 2
    if scaleXY < 0:
        scaleXY = -scaleXY
        outX += 180
        outY += 180
        report_warning('Rotation makes object behind the camera: trZ == %.0f < %.0f' % (trZ, FOV))
    return (trX, trY, cap_angle(outX), cap_angle(outY), cap_angle(outZ), scaleXY * 100, scaleXY * 100)


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
        elif i[4] == 'bilipos':
            write_danmaku_positioned_bilibili(f, i, width, height, styleid, report_warning)
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
; Automatically generated by NeoNippori (ネオ日暮里)
; https://github.com/ytdl-patched/ytdl-patched/blob/ytdlp/yt_dlp/neonippori.py
Script Updated By: NeoNippori (https://github.com/ytdl-patched/ytdl-patched/blob/ytdlp/yt_dlp/neonippori.py)
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
''' % {'width': width, 'height': height, 'fontface': fontface, 'fontsize': fontsize, 'alpha': 255 - round(alpha * 255), 'outline': max(fontsize / 25.0, 1), 'styleid': styleid}
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


def clip_byte(x):
    return 255 if x > 255 else 0 if x < 0 else round(x)


def format_color(color, width=1280, height=576):
    if color == 0x000000:
        return '000000'
    elif color == 0xffffff:
        return 'FFFFFF'
    R = (color >> 16) & 0xff
    G = (color >> 8) & 0xff
    B = color & 0xff
    if width < 1280 and height < 576:
        return '%02X%02X%02X' % (B, G, R)
    else:  # VobSub always uses BT.601 colorspace, convert to BT.709
        return '%02X%02X%02X' % (
            clip_byte(R * 0.00956384088080656 + G * 0.03217254540203729 + B * 0.95826361371715607),
            clip_byte(R * -0.10493933142075390 + G * 1.17231478191855154 + B * -0.06737545049779757),
            clip_byte(R * 0.91348912373987645 + G * 0.07858536372532510 + B * 0.00792551253479842)
        )


def convert_type2(row, height, bottomReserved):
    return height - bottomReserved - row


def open_file(filename_or_file, *args, **kwargs):
    if isinstance(filename_or_file, bytes):
        filename_or_file = str(bytes(filename_or_file).decode('utf-8', 'replace'))
    if isinstance(filename_or_file, str):
        return open(filename_or_file, *args, **kwargs)
    else:
        return filename_or_file


def filter_badchars(f):
    return re.sub('[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f]', '\ufffd', f)


class safe_list(list):
    def get(self, index, default=None):
        try:
            return self[index]
        except IndexError:
            return default


def load_comments(input_text, input_format, stage_width, stage_height, reserve_blank=0, font_face='sans-serif', font_size=25.0, text_opacity=1.0, duration_marquee=5.0, duration_still=5.0, report_warning=noop):
    filters_regex = []
    comments = parse_comments(input_text, input_format, font_size, report_warning)
    with io.StringIO() as fo:
        process_comments(comments, fo, stage_width, stage_height, reserve_blank, font_face, font_size, text_opacity, duration_marquee, duration_still, filters_regex)
        return fo.getvalue()


def parse_comments(input_text, input_format, font_size=25.0, report_warning=noop):
    processor = PROCESSORS.get(input_format)
    if not processor:
        raise ValueError('Unknown comment file format: %s' % input_format)
    comments = list(processor(filter_badchars(input_text), font_size, report_warning))
    comments.sort()
    return comments


__all__ = [
    'load_comments',
]

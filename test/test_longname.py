#!/usr/bin/env python
# coding: utf-8
from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_dl.longname import (
    split_longname_str,
    combine_longname_str,
)


class TestLongName(unittest.TestCase):

    def test_split_utf8(self):
        self.assertEqual(
            split_longname_str('spade', 'utf8'),
            'spade'
        )
        self.assertEqual(
            split_longname_str('【妖怪ウォッチアニメ】第１３話「 コマさん 〜はじめてのファストフード編〜（#5）」「妖怪 口だけおんな」  「妖怪 ダンサーズ☆」「 じんめん犬シーズン2 犬脱走 Episode 2」-cL46Bl96_GQ.f137.mp4.part', 'utf8'),
            '【妖怪ウォッチアニメ】第１３話「 コマさん 〜はじめてのファストフード編〜（#5）」「妖怪 口だけおんな」  「妖怪 ダンサーズ☆」「 じんめん犬シーズン2 犬脱走 Episode 2」-cL46Bl96_GQ.f13~~/7.mp4.part'
        )

    def test_combine_utf8(self):
        self.assertEqual(
            combine_longname_str('spade', 'utf8'),
            'spade'
        )
        self.assertEqual(
            combine_longname_str('【妖怪ウォッチアニメ】第１３話「 コマさん 〜はじめてのファストフード編〜（#5）」「妖怪 口だけおんな」  「妖怪 ダンサーズ☆」「 じんめん犬シーズン2 犬脱走 Episode 2」-cL46Bl96_GQ.f13~~/7.mp4.part', 'utf8'),
            '【妖怪ウォッチアニメ】第１３話「 コマさん 〜はじめてのファストフード編〜（#5）」「妖怪 口だけおんな」  「妖怪 ダンサーズ☆」「 じんめん犬シーズン2 犬脱走 Episode 2」-cL46Bl96_GQ.f137.mp4.part'
        )

    def test_split_sjis(self):
        # In SJIS, it is in 255 bytes (!!)
        self.assertEqual(
            split_longname_str('【妖怪ウォッチアニメ】第１３話「 コマさん 〜はじめてのファストフード編〜（#5）」「妖怪 口だけおんな」  「妖怪 ダンサーズ☆」「 じんめん犬シーズン2 犬脱走 Episode 2」-cL46Bl96_GQ.f137.mp4.part', 'sjis'),
            '【妖怪ウォッチアニメ】第１３話「 コマさん 〜はじめてのファストフード編〜（#5）」「妖怪 口だけおんな」  「妖怪 ダンサーズ☆」「 じんめん犬シーズン2 犬脱走 Episode 2」-cL46Bl96_GQ.f137.mp4.part'
        )

    def test_resplit_identical(self):
        instr = '【妖怪ウォッチアニメ】第１３話「 コマさん 〜はじめてのファストフード編〜（#5）」「妖怪 口だけおんな」  「妖怪 ダンサーズ☆」「 じんめん犬シーズン2 犬脱走 Episode 2」-cL46Bl96_GQ.f13~~/7.mp4.part'
        self.assertEqual(split_longname_str(instr, 'utf8'), instr)

# coding: utf-8
from __future__ import unicode_literals
import PySimpleGUI as sg
# WIP

import sys
import threading
import json
import traceback

sys.path[:0] = ['.']

from yt_dlp import YoutubeDL

sg.theme('Dark Blue 3')

layout = [
    [sg.Text('Extractor Inspector')],
    [sg.Text('URL', size=(15, 1)), sg.InputText(tooltip='https://...', key='-TEXT-')],
    [sg.Submit(button_text='Run extractor', key='-RUN-')]
]

window = sg.Window('ytdl-patched', layout)


class InspectorLogger(object):
    def debug(self, msg):
        print(msg)

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)


ytdl = YoutubeDL({
    'verbose': True,
    'logger': InspectorLogger(),
})


def the_thread(window, url):
    try:
        response = json.dumps(ytdl.extract_info(url, download=False), indent=2)
    except BaseException:
        t, v, tb = sys.exc_info()
        response = ''.join(traceback.format_exception(t, v, tb))
    window.write_event_value('-EXTRACTOR-RESULT-', response)


while True:
    try:
        event, values = window.read()
    except InterruptedError:
        event, values = None, None

    if event is None:
        window.close()
        break

    if event == '-RUN-':
        threading.Thread(target=the_thread, args=(window, values['-TEXT-']), daemon=True).start()

    if event == '-EXTRACTOR-RESULT-':
        sg.popup(values['-EXTRACTOR-RESULT-'])

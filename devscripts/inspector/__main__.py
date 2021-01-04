# coding: utf-8
import PySimpleGUI as sg

import sys
import threading
import json
import traceback

sys.path[:0] = ['.']

from youtube_dl import YoutubeDL

sg.theme('Dark Blue 3')

layout = [
    [sg.Text('Extractor Inspector')],
    [sg.Text('URL', size=(15, 1)), sg.InputText('https://...', key='-TEXT-')],
    [sg.Submit(button_text='Run extractor', key='-RUN-')]
]

window = sg.Window('ytdl-patched', layout)


class InspectorLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

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
    event, values = window.read()

    if event is None:
        window.close()
        break

    if event == '-RUN-':
        threading.Thread(target=the_thread, args=(window, values['-TEXT-']), daemon=True).start()

    if event == '-EXTRACTOR-RESULT-':
        sg.popup(values['-EXTRACTOR-RESULT-'])

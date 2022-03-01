from __future__ import unicode_literals

import os
import shutil
import subprocess
import sys
import optparse
import datetime
import time

sys.path[:0] = ['.']

from yt_dlp.utils import check_executable

try:
    iterations = str(int(os.environ['ZOPFLI_ITERATIONS']))
except BaseException:
    iterations = '30'

parser = optparse.OptionParser(usage='%prog PYTHON')
options, args = parser.parse_args()
if len(args) != 1:
    parser.error('Expected python executable name for shebang')

PYTHON = args[0]

# 200001010101
date = datetime.datetime(year=2000, month=1, day=1, hour=1, minute=1, second=1)
modTime = time.mktime(date.timetuple())

try:
    shutil.rmtree('zip/')
except FileNotFoundError:
    pass
os.makedirs('zip/', exist_ok=True)

files = [(dir, file) for (dir, _, c) in os.walk('yt_dlp') for file in c if file.endswith('.py')]

for (dir, file) in files:
    joined = os.path.join(dir, file)
    dest = os.path.join('zip', joined)
    os.makedirs(os.path.join('zip', dir), exist_ok=True)
    shutil.copy(joined, dest)
    os.utime(dest, (modTime, modTime))

os.rename('zip/yt_dlp/__main__.py', 'zip/__main__.py')
files.remove(('yt_dlp', '__main__.py'))
files[:0] = [('', '__main__.py')]

all_paths = [os.path.join(dir, file) for (dir, file) in files]
if check_executable('7z', []):
    ret = subprocess.Popen(
        ['7z', 'a', '-mm=Deflate', '-mfb=258', '-mpass=15', '-mtc-', '../youtube-dl.zip'] + all_paths,
        cwd='zip/').wait()
elif check_executable('zip', ['-h']):
    ret = subprocess.Popen(
        ['zip', '-9', '../youtube-dl.zip'] + all_paths,
        cwd='zip/').wait()
else:
    raise Exception('Cannot find ZIP archiver')

if ret != 0:
    raise Exception('ZIP archiver returned error: %d' % ret)

if check_executable('advzip', []):
    subprocess.Popen(
        ['advzip', '-z', '-4', '-i', iterations, 'youtube-dl.zip']).wait()

shutil.rmtree('zip/')

with open('youtube-dl', 'wb') as ytdl:
    ytdl.write(b'#!%s\n' % PYTHON.encode('utf8'))
    with open('youtube-dl.zip', 'rb') as zip:
        ytdl.write(zip.read())

os.remove('youtube-dl.zip')

os.chmod('youtube-dl', 0o755)

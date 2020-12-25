import re
import sys
import subprocess
import os

infile, outfile = sys.argv[1:]

# usage: python3 devscripts/readme_for_cdn.py ../README.md to_be_converted.md


# git rev-parse --short master
sp = subprocess.Popen(
    ['git', 'rev-parse', '--short', 'master'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    cwd=os.path.dirname(os.path.abspath(__file__)))
out, err = sp.communicate()
out = out.decode().strip()

git_commit = ''
if re.match('[0-9a-f]+', out):
    git_commit = out

# https://vercel.com/docs/cli#commands/overview/unique-options

information_section = [
    '- current commit: [`%(git_commit)s`](https://github.com/nao20010128nao/ytdl-patched/commit/%(git_commit)s)' % {'git_commit': git_commit},
    '- [see list of supported sites](/supportedsites.html)',
]

release_tag = os.environ.get('GITHUB_RELEASE_TAG')
if release_tag:
    information_section.append('- [download ytdl-patched](https://github.com/nao20010128nao/ytdl-patched/releases/tag/%s)' % release_tag)
    information_section.append('  - [for Linux/macOS](https://github.com/nao20010128nao/ytdl-patched/releases/download/%s/youtube-dl)' % release_tag)
    information_section.append('  - [for Windows](https://github.com/nao20010128nao/ytdl-patched/releases/download/%s/youtube-dl-red.exe)' % release_tag)
    information_section.append('  - [for pip](https://github.com/nao20010128nao/ytdl-patched/releases/download/%s/youtube-dl.tar.gz)' % release_tag)
    information_section.append('  - or by Homebrew: `brew install nao20010128nao/my/ytdl-patched`')

MARKER_RE = r'(?m)^<!-- MARKER BEGIN -->[^\0]+<!-- MARKER END -->$'

NAVIGATE_TXT = """
# Information

%s
""" % ('\n'.join(information_section))

markdown = ''

with open(infile, 'r') as r:
    markdown = r.read()

if isinstance(markdown, bytes):
    markdown = markdown.decode('utf-8')

markdown = re.sub(MARKER_RE, NAVIGATE_TXT, markdown)

if sys.version_info < (3, ):
    markdown = markdown.encode('utf-8')

with open(outfile, 'w') as w:
    w.write(markdown)

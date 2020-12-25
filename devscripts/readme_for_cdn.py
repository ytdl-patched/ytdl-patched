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

# git rev-parse --short youtube-dl
sp = subprocess.Popen(
    ['git', 'rev-parse', '--short', 'youtube-dl'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    cwd=os.path.dirname(os.path.abspath(__file__)))
out, err = sp.communicate()
out = out.decode().strip()

git_upstream_commit = ''
if re.match('[0-9a-f]+', out):
    git_upstream_commit = out


MARKER_RE = r'(?m)^<!-- MARKER BEGIN -->[^\0]+<!-- MARKER END -->$'

NAVIGATE_TXT = """
# Information

- current commit: `%s`
- youtube-dl commit: `%s`
- [see list of supported sites](/supportedsites.html)

""" % (git_commit, git_upstream_commit)

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

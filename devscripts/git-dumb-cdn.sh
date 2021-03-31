#!/bin/bash
SERVICE="$1"

if ! command -v pandoc &> /dev/null ; then
  wget -O- https://github.com/jgm/pandoc/releases/download/2.13/pandoc-2.13-linux-amd64.tar.gz | \
      tar -xvzf - --strip-components 1
  export PATH="$PWD/bin/:$PATH"
fi

pdoc() {
  MD="$1"
  HTML="$2"
  TITLE="$3"
  pandoc "$MD" -f gfm-emoji --metadata title="$TITLE" -t html -s -o "$HTML"
}

set -xe

rm -rf public/ || true
git clone --bare https://github.com/nao20010128nao/ytdl-patched.git public/ || \
  git clone --bare https://bitbucket.org/nao20010128nao/ytdl-patched.git public/ || \
  git clone --bare https://forge.tedomum.net/nao20010128nao/ytdl-patched.git public/ || \
  git clone --bare https://gitlab.com/lesmi_the_goodness/ytdl-patched.git public/ || \
  git clone --bare https://gitea.com/nao20010128nao/ytdl-patched.git public/ || \
  git clone --bare https://git.sr.ht/~nao20010128nao/ytdl-patched public/

python devscripts/readme_for_cdn.py README.md README.cdn.md

cd public
pdoc ../README.cdn.md index.html "git clone https://ytdl-patched.${SERVICE}.app/"
tail -n+2 ../docs/supportedsites.md | pdoc - supportedsites.html "List of supported sites by ytdl-patched"
git remote rm origin
git branch -D gh-pages
git reflog expire --expire=now --all
git gc --aggressive --prune=now
mv objects/pack/pack-* . || true
find . -name 'pack-*.pack' -type f -exec bash -c 'git unpack-objects < "$1' _ {} \;
rm -rf pack-* objects/pack/
git update-server-info

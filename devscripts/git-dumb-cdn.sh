#!/bin/bash
SERVICE="$1"

if ! command -v pandoc &> /dev/null ; then
  wget -O- https://github.com/jgm/pandoc/releases/download/2.11.1.1/pandoc-2.11.1.1-linux-amd64.tar.gz | \
      tar -xvzf - --strip-components 1
  export PATH="$PWD/bin/:$PATH"
fi

set -xe

rm -rf public/ || true
git clone --bare https://github.com/nao20010128nao/ytdl-patched.git public/ || \
  git clone --bare https://bitbucket.org/nao20010128nao/ytdl-patched.git public/ || \
  git clone --bare https://forge.tedomum.net/nao20010128nao/ytdl-patched.git public/ || \
  git clone --bare https://gitlab.com/lesmi_the_goodness/ytdl-patched.git public/ || \
  git clone --bare https://gitea.com/nao20010128nao/ytdl-patched.git public/ || \
  git clone --bare https://git.sr.ht/~nao20010128nao/ytdl-patched public/

cd public
pandoc ../README.md -f gfm --metadata title="git clone https://ytdl-patched.${SERVICE}.app/" -t html -s -o index.html
git remote rm origin
git branch -D gh-pages
git reflog expire --expire=now --all
git gc --aggressive --prune=now
mv objects/pack/pack-* . || true
find . -name 'pack-*.pack' -type f -exec bash -c 'git unpack-objects < {}' \;
rm -rf pack-* objects/pack/
git update-server-info

#!/bin/bash
set -xe

rm -rf vercel/ || true
git clone --bare https://github.com/nao20010128nao/ytdl-patched.git vercel/ || \
  git clone --bare https://bitbucket.org/nao20010128nao/ytdl-patched.git vercel/ || \
  git clone --bare https://forge.tedomum.net/nao20010128nao/ytdl-patched.git vercel/ || \
  git clone --bare https://gitlab.com/lesmi_the_goodness/ytdl-patched.git vercel/ || \
  git clone --bare https://gitea.com/nao20010128nao/ytdl-patched.git vercel/ || \
  git clone --bare https://git.sr.ht/~nao20010128nao/ytdl-patched vercel/

cd vercel
git remote rm origin
git branch -D gh-pages
git reflog expire --expire=now --all
git gc --aggressive --prune=now
mv objects/pack/pack-* . || true
find . -name 'pack-*.pack' -type f -exec bash -c 'git unpack-objects < {}' \;
rm -rf pack-* objects/pack/
git update-server-info

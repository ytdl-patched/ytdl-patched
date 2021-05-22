#!/bin/bash
export __DIRNAME="$(basename "$(pwd)")"

if [[ "$__DIRNAME" == "vercel" ]] ; then
  cd ../../
fi

yum install -y wget tar gzip

./devscripts/git-dumb-cdn.sh vercel

if [[ "$__DIRNAME" == "vercel" ]] ; then
  cp -r public/* devscripts/vercel/
fi

#!/bin/bash
# an convenient script to easily trigger "Merge upstream" workflow
exec gh workflow run -R ytdl-patched/ytdl-patched merge.yml

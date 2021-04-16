#!/usr/bin/env python3
# coding: utf-8
from __future__ import unicode_literals

import sys
import re

# https://github.blog/changelog/2021-02-08-github-actions-skip-pull-request-and-push-workflows-with-skip-ci/
# https://docs.github.com/en/actions/guides/about-continuous-integration#skipping-workflow-runs
skips = [
    '[ci skip]', '[skip ci]',
    '[no ci]',
    '[skip actions]', '[actions skip]',
    'skip-checks: true', 'skip-checks:true']


compiled = [re.compile(re.escape(x)) for x in skips]
removed = 0


def count_removed(m):
    global removed
    removed += 1
    return ''


for file in sys.argv[1:]:
    with open(file, 'r') as f:
        content = f.read()
    for reg in compiled:
        content = re.sub(reg, count_removed, content)
    with open(file, 'w') as f:
        f.write(content)

print('%d occurrences removed' % removed)

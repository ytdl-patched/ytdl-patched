#!/usr/bin/env python3
# coding: utf-8
from __future__ import unicode_literals

import sys

# this script converts something like 2021.03.24 into 2021.3.24
print('.'.join(str(int(x)) for x in sys.argv[1].split('.')))

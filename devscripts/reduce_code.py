#!/usr/bin/env python
from __future__ import unicode_literals

# This script does the following using AST
# - removes test cases from InfoExtractor

import ast
import sys

paths = sys.argv[1:]

denylist = ['_TEST', '_TESTS']

for path in paths:
    print('Processing %s' % path)
    with open(path, 'r', encoding='utf-8') as r:
        code = r.read()
    expression = ast.parse(code)
    body = expression.body
    modified = False
    for stmt in body:
        if not isinstance(stmt, ast.ClassDef):
            continue
        print('  Found class %s' % stmt.name)
        remove = []
        for member in stmt.body:
            if not isinstance(member, ast.Assign):
                continue
            assign_name = member.targets[0].id
            if assign_name not in denylist:
                continue
            print('    Removing %s in %s' % (assign_name, stmt.name))
            remove.append(member)
        modified |= bool(remove)
        stmt.body = [x for x in stmt.body if x not in remove]
    cleaned_code = ast.unparse(expression)

    if not modified:
        print('  Nothing was modified, skipping')
        continue

    old_length = len(code)
    new_length = len(cleaned_code)
    percentage = 100.0 * (old_length - new_length) / old_length
    print('  %d chars -> %d chars, %.2f%% reduced' % (old_length, new_length, percentage))
    if new_length >= old_length:
        print('  New code gets bigger, skipping')
        continue
    with open(path, 'w', encoding='utf-8') as w:
        w.write(cleaned_code)

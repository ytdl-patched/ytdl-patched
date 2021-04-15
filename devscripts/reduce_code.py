#!/usr/bin/env python
from __future__ import unicode_literals

# This script does the following using AST
# - removes test cases from InfoExtractor
# - clean up regexes when inline flag (?x) is set

import ast
import sys
import re

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
            assign_value = member.value
            # TODO: support formatted string like YoutubeIE
            if assign_name == '_VALID_URL' and isinstance(assign_value, ast.Constant) and isinstance(assign_value.value, str):
                # clean up regexes
                regex_str = assign_value.value
                has_extended = re.search(r'\(\?[aiLmsux]*x[aiLmsux]*\)', regex_str)  # something like (?xxs) may match, but (?s) or (?i) won't
                if not has_extended:
                    continue
                # remove comments
                regex_str = re.sub(r'(?m)\s*#.+?$', '', regex_str)
                # remove spaces and indents
                regex_str = re.sub(r'\s+', '', regex_str)
                # remove x (EXTENDED) from all inline flags
                regex_str = re.sub(r'\(\?([aiLmsux]+)\)', lambda m: '(?%s)' % m.group(1).replace('x', ''), regex_str)
                regex_str = re.sub(r'\(\?\)', '', regex_str)
                # set it back, if it is smaller
                if len(assign_value.value) > len(regex_str):
                    print('    Cleaning up _VALID_URL in %s' % stmt.name)
                    assign_value.value = regex_str
                    modified = True
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

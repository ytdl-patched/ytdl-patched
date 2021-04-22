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


def cleanup_regex(regex_str: str):
    has_extended = re.search(r'\(\?[aiLmsux]*x[aiLmsux]*\)', regex_str)  # something like (?xxs) may match, but (?s) or (?i) won't
    if not has_extended:
        return regex_str
    # remove comments
    regex_str = re.sub(r'(?m)\s+#.+?$', '', regex_str)
    # remove spaces and indents
    regex_str = re.sub(r'\s+', '', regex_str)
    # remove x (EXTENDED) from all inline flags
    regex_str = re.sub(r'\(\?([aiLmsux]+)\)', lambda m: '(?%s)' % m.group(1).replace('x', ''), regex_str)
    regex_str = re.sub(r'\(\?\)', '', regex_str)

    return regex_str


def try_find_regex_constant(rhs):
    # simple assignment
    # _VALID_URL = r'https://example\.com/video/\d+'
    if isinstance(rhs, ast.Constant) and isinstance(rhs.value, str):
        return rhs

    # formatted regexes
    # _VALID_URL = r'https://example\.com/video/\d+'
    if isinstance(rhs, ast.BinOp) and isinstance(rhs.op, ast.Mod) and isinstance(rhs.left, ast.Constant) and isinstance(rhs.left.value, str):
        return rhs.left

    return None


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
            if assign_name == '_VALID_URL':
                regex_statement = try_find_regex_constant(assign_value)
                if not regex_statement:
                    continue
                # clean up regexes
                regex_str = cleanup_regex(regex_statement.value)
                # set it back, if it is smaller
                if len(regex_statement.value) > len(regex_str):
                    print('    Cleaning up _VALID_URL in %s' % stmt.name)
                    regex_statement.value = regex_str
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

#!/usr/bin/env python3
"""Corpus-scoped checks: properties no single file can violate on its own.

The artifact UUID is the motivating case -- `cp doc.md copy.md` duplicates it,
and both files remain individually valid. Only a repository-wide pass can see
it, which is why this runs in CI rather than in the parser.
"""
import re, sys, os, collections

def main(root):
    ids = collections.defaultdict(list)
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ('.git', '.cache', 'node_modules')]
        for f in files:
            if not f.endswith(('.md', '.tbl', '.canvas')): continue
            p = os.path.join(dirpath, f)
            try: t = open(p, encoding='utf-8').read()
            except Exception: continue
            m = re.search(r'^id:\s*(\S+)', t, re.M)
            if m: ids[m.group(1)].append(os.path.relpath(p, root))
    bad = {k: v for k, v in ids.items() if len(v) > 1}
    for k, v in sorted(bad.items()):
        print(f'DUPLICATE ARTIFACT ID {k}\n    ' + '\n    '.join(v))
    print(f'{len(ids)} identified artifact(s), {len(bad)} duplicate id(s)')
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else '.'))

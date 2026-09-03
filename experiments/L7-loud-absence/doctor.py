#!/usr/bin/env python3
"""`gws doctor` -- make git's fail-open silence loud.

A repository DECLARES capabilities in .gitattributes; git BINDS them only from
local config. Git resolves the gap silently. This does not.
"""
import subprocess, sys, re, os

def cfg(key):
    r = subprocess.run(['git','config','--get',key], capture_output=True, text=True)
    return r.stdout.strip() or None

def declared(path='.gitattributes'):
    out = []
    if not os.path.exists(path): return out
    for n, line in enumerate(open(path), 1):
        line = line.split('#')[0].strip()
        if not line: continue
        pat, *attrs = line.split()
        for a in attrs:
            m = re.fullmatch(r'(merge|diff|filter)=([\w.-]+)', a)
            if m and m.group(2) not in ('text','binary','union'):
                out.append((n, pat, m.group(1), m.group(2)))
    return out

def main():
    problems = []
    for n, pat, kind, name in declared():
        key = {'merge':f'merge.{name}.driver',
               'diff':f'diff.{name}.command',
               'filter':f'filter.{name}.smudge'}[kind]
        bound = cfg(key)
        status = 'BOUND' if bound else 'NOT BOUND'
        print(f'  .gitattributes:{n}  {pat:12s} {kind}={name:10s} -> {status}')
        if not bound:
            problems.append((pat, kind, name, key))
    # is this repo bare? then attributes are not consulted at ALL
    bare = subprocess.run(['git','rev-parse','--is-bare-repository'],
                          capture_output=True, text=True).stdout.strip() == 'true'
    if bare and declared():
        problems.append(('*','bare','-','attr.tree'))
        print('  ! BARE REPOSITORY: .gitattributes is not consulted at all here.')
    if not problems:
        print('  all declared capabilities are bound.'); return 0
    print()
    print(f'  REFUSING: {len(problems)} declared capability(ies) are not available.')
    for pat, kind, name, key in problems:
        if kind == 'bare':
            print(f'    - this repo is bare; set attr.tree=HEAD or merge in a worktree')
        else:
            print(f'    - {pat} declares {kind}={name}, but {key} is unset.')
            print(f'      git would SILENTLY fall back. Install the tool, or pass --force.')
    return 1

sys.exit(main())

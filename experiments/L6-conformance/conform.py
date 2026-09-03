#!/usr/bin/env python3
"""Conformance suite for the substrate's invariants, run against STOCK git.

A format passes only if it satisfies these under an unmodified `git` binary
with no drivers, no .gitattributes, and none of our tooling installed.
"""
import os, sys, subprocess, tempfile, shutil, hashlib

def sh(*a, cwd=None, check=False):
    r = subprocess.run(a, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode: raise SystemExit(f'{a}: {r.stderr}')
    return r

class Case:
    def __init__(s, name, base, ours, theirs, expect, evaluate=None):
        s.name, s.base, s.ours, s.theirs = name, base, ours, theirs
        s.expect = expect          # 'clean' | 'conflict'
        s.evaluate = evaluate      # fn(text) -> value, or None

def git_merge(base, ours, theirs, fn):
    d = tempfile.mkdtemp()
    try:
        sh('git','init','-q',d, check=True)
        for k,v in [('user.email','t@e'),('user.name','t')]: sh('git','config',k,v,cwd=d)
        p = os.path.join(d, fn)
        open(p,'w').write(base); sh('git','add','-A',cwd=d); sh('git','commit','-qm','b',cwd=d)
        sh('git','branch','-M','main',cwd=d)
        sh('git','checkout','-qb','x',cwd=d); open(p,'w').write(theirs)
        sh('git','commit','-qam','x',cwd=d)
        sh('git','checkout','-q','main',cwd=d); open(p,'w').write(ours)
        sh('git','commit','-qam','o',cwd=d)
        r = sh('git','merge','x','-m','m',cwd=d)
        return r.returncode, open(p).read()
    finally: shutil.rmtree(d)

def run(fmt_name, fn, parse, render, corpus, cases, break_ref=None):
    fails = []
    print(f'\n=== {fmt_name} ===')

    # I1a round-trip
    for i, doc in enumerate(corpus):
        if render(parse(doc)) != doc:
            fails.append(f'I1 round-trip failed on corpus[{i}]')
    print(f'  I1 round-trip      : {"PASS" if not fails else "FAIL"} ({len(corpus)} docs)')

    # I1b idempotence
    n0 = len(fails)
    for i, doc in enumerate(corpus):
        a = render(parse(doc)); b = render(parse(a))
        if a != b: fails.append(f'I1 idempotence failed on corpus[{i}]')
    print(f'  I1 idempotence     : {"PASS" if len(fails)==n0 else "FAIL"}')

    # I6 stock-git merge behaviour
    n0 = len(fails)
    for c in cases:
        rc, out = git_merge(c.base, c.ours, c.theirs, fn)
        got = 'conflict' if rc else 'clean'
        if got != c.expect:
            fails.append(f'I6 {c.name}: expected {c.expect}, got {got}')
        elif got == 'clean' and c.evaluate:
            v, want = c.evaluate(out)
            if v != want:
                fails.append(f'I6 {c.name}: SILENTLY WRONG -- merged clean but evaluated {v}, expected {want}')
        print(f'    {c.name:38s} {got:9s} {"ok" if got==c.expect else "MISMATCH"}')
    print(f'  I6 stock-git       : {"PASS" if len(fails)==n0 else "FAIL"}')

    # I3 loud failure
    if break_ref:
        ok = break_ref()
        print(f'  I3 loud failure    : {"PASS" if ok else "FAIL"}')
        if not ok: fails.append('I3 broken reference did not fail loudly')

    for f in fails: print('  !!', f)
    return fails

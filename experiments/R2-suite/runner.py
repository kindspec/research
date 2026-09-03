#!/usr/bin/env python3
"""Conformance runner. Executes the declarative cases against a reference
implementation, using a STOCK git binary for every merge."""
import os, sys, subprocess, tempfile, shutil, itertools, importlib
import cases as C

def sh(*a, cwd=None):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)

def git_merge(base, ours, theirs, fn='a.tbl'):
    d = tempfile.mkdtemp()
    try:
        sh('git','init','-q',d)
        for k,v in [('user.email','t@e'),('user.name','t')]: sh('git','config',k,v,cwd=d)
        p = os.path.join(d, fn)
        open(p,'w').write(base); sh('git','add','-A',cwd=d); sh('git','commit','-qm','b',cwd=d)
        sh('git','branch','-M','main',cwd=d)
        sh('git','checkout','-qb','x',cwd=d); open(p,'w').write(theirs); sh('git','commit','-qam','x',cwd=d)
        sh('git','checkout','-q','main',cwd=d); open(p,'w').write(ours); sh('git','commit','-qam','o',cwd=d)
        r = sh('git','merge','x','-m','m',cwd=d)
        return ('conflict' if r.returncode else 'clean'), open(p).read()
    finally: shutil.rmtree(d)

def git_merge_many(base, branches, order, fn='a.tbl'):
    d = tempfile.mkdtemp()
    try:
        sh('git','init','-q',d)
        for k,v in [('user.email','t@e'),('user.name','t')]: sh('git','config',k,v,cwd=d)
        p = os.path.join(d, fn)
        open(p,'w').write(base); sh('git','add','-A',cwd=d); sh('git','commit','-qm','b',cwd=d)
        sh('git','branch','-M','main',cwd=d)
        for i, b in enumerate(branches):
            sh('git','checkout','-q','main',cwd=d); sh('git','checkout','-qb',f'b{i}',cwd=d)
            open(p,'w').write(b); sh('git','commit','-qam',f'b{i}',cwd=d)
        sh('git','checkout','-q','main',cwd=d)
        for i in order:
            r = sh('git','merge',f'b{i}','-m','m',cwd=d)
            if r.returncode: return 'conflict', None
        return 'clean', open(p).read()
    finally: shutil.rmtree(d)

def run(impl, verbose=True):
    ref = importlib.import_module(impl)
    importlib.reload(ref)
    fails = []
    def check(cid, ok, detail=''):
        if not ok: fails.append(f'{cid}: {detail}')
        if verbose: print(f"  {'ok  ' if ok else 'FAIL'} {cid}{'' if ok else '   '+detail}")

    if verbose: print('-- parse')
    for cid, text, want in C.PARSE:
        try:
            ref.evaluate(text); got = None
        except ref.Malformed as e: got = str(e)
        except Exception as e: got = f'CRASH:{type(e).__name__}:{e}'
        if want is None: check(cid, got is None, f'expected accept, got {got!r}')
        else: check(cid, got is not None and want in got and not got.startswith('CRASH'),
                    f'expected refusal containing {want!r}, got {got!r}')

    if verbose: print('-- roundtrip')
    for cid, text in C.ROUNDTRIP:
        try:
            out = ref.render(ref.structure(text)); check(cid, out == text,
                f'{len(text)}B in, {len(out)}B out')
        except Exception as e: check(cid, False, f'{type(e).__name__}: {e}')

    if verbose: print('-- eval')
    for cid, text, want in C.EVAL:
        try:
            _, aggs = ref.evaluate(text)
            check(cid, all(aggs.get(k) == v for k, v in want.items()),
                  f'wanted {want}, got { {k: aggs.get(k) for k in want} }')
        except Exception as e: check(cid, False, f'{type(e).__name__}: {e}')

    if verbose: print('-- merge (stock git)')
    for cid, base, ours, theirs, want_status, want_vals in C.MERGE:
        status, merged = git_merge(base, ours, theirs)
        if status != want_status:
            check(cid, False, f'git said {status}, expected {want_status}'); continue
        if want_vals is None: check(cid, True); continue
        if want_vals == 'MUST_REFUSE':
            try:
                ref.evaluate(merged); check(cid, False, 'parser ACCEPTED a corrupt merge')
            except ref.Malformed: check(cid, True)
            except Exception as e: check(cid, False, f'crashed instead of refusing: {e}')
            continue
        try:
            _, aggs = ref.evaluate(merged)
            ok = all(aggs.get(k) == v for k, v in want_vals.items())
            check(cid, ok, f'SILENTLY WRONG: wanted {want_vals}, got { {k: aggs.get(k) for k in want_vals} }')
        except Exception as e: check(cid, False, f'{type(e).__name__}: {e}')

    if verbose: print('-- confluence')
    for cid, base, branches in C.CONFLUENCE:
        results = set()
        for order in itertools.permutations(range(len(branches))):
            st, merged = git_merge_many(base, branches, order)
            if st == 'conflict': results.add('conflict'); continue
            try:
                _, aggs = ref.evaluate(merged); results.add(tuple(sorted(aggs.items())))
            except Exception as e: results.add(f'err:{e}')
        check(cid, len(results) == 1, f'{len(results)} distinct outcomes across merge orders')
    return fails

if __name__ == '__main__':
    impl = sys.argv[1] if len(sys.argv) > 1 else 'ref_tbl'
    f = run(impl)
    print(f'\nTOTAL FAILURES: {len(f)}')
    sys.exit(1 if f else 0)

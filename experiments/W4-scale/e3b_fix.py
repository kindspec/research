#!/usr/bin/env python3
"""E3b: the cheapest fix for the closure-hash cost -- memoise it per build.

closure_hash() re-reads and re-hashes every file in an artifact's transitive
closure on EVERY resolve, and refs() re-reads the file again to find edges.
The fix is a per-build memo keyed by artifact path (the tree is immutable for
the duration of one build), which turns O(V*E) into O(V+E).
"""
import sys, os, time, json, statistics, shutil, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib')); sys.path.insert(0, HERE)
import gen, derive
import e3_derive as E

WORK = E.WORK
_open = open

_orig_ch = derive.closure_hash
_orig_refs = derive.refs


def memoised():
    hmemo, rmemo = {}, {}

    def refs(path):
        if path not in rmemo: rmemo[path] = _orig_refs(path)
        return rmemo[path]

    def ch(art, seen=None):
        if seen is None:
            if art in hmemo: return hmemo[art]
            v = _orig_ch(art, set())
            hmemo[art] = v
            return v
        return _orig_ch(art, seen)
    return ch, refs


def run(sizes):
    out = []
    for n in sizes:
        p = os.path.join(WORK, f'graph{n}')
        tbls, docs = E.build_repo(p, max(1, n // 2), n - max(1, n // 2))
        shutil.rmtree(os.path.join(p, derive.CACHE), ignore_errors=True)
        # baseline warm
        E.build_all(p, docs)
        t_base = statistics.median([E._t(lambda: E.build_all(p, docs)) for _ in range(3)])
        # memoised warm
        ch, rf = memoised()
        derive.closure_hash, derive.refs = ch, rf
        E.build_all(p, docs)
        ts = []
        for _ in range(3):
            ch, rf = memoised()
            derive.closure_hash, derive.refs = ch, rf
            ts.append(E._t(lambda: E.build_all(p, docs)))
        t_memo = statistics.median(ts)
        derive.closure_hash, derive.refs = _orig_ch, _orig_refs
        rec = dict(n=n, warm_baseline_s=t_base, warm_memo_s=t_memo, speedup=t_base / t_memo)
        out.append(rec); print('E3fix', json.dumps(rec), flush=True)
    return out


def chain(depths):
    out = []
    for d in depths:
        p = os.path.join(WORK, f'chain{d}')
        shutil.rmtree(p, ignore_errors=True); os.makedirs(p)
        for i in range(d):
            t = gen.tbl_text(20, seed=i)
            if i: t = f'use c{i-1:05d}.tbl#grand\n\n' + t
            _open(os.path.join(p, f'c{i:05d}.tbl'), 'w').write(t)
        # one doc per level -> a full build touches every prefix of the chain
        docs = []
        for i in range(d):
            dn = f'm{i:05d}.md'
            _open(os.path.join(p, dn), 'w').write(f'V {{{{ c{i:05d}.tbl#grand }}}}.\n')
            docs.append(dn)
        shutil.rmtree(os.path.join(p, derive.CACHE), ignore_errors=True)
        E.build_all(p, docs)
        t_base = statistics.median([E._t(lambda: E.build_all(p, docs)) for _ in range(3)])
        ts = []
        for _ in range(3):
            ch, rf = memoised()
            derive.closure_hash, derive.refs = ch, rf
            ts.append(E._t(lambda: E.build_all(p, docs)))
        derive.closure_hash, derive.refs = _orig_ch, _orig_refs
        rec = dict(depth=d, full_build_baseline_s=t_base, full_build_memo_s=statistics.median(ts),
                   speedup=t_base / statistics.median(ts))
        out.append(rec); print('E3chainfix', json.dumps(rec), flush=True)
    return out


if __name__ == '__main__':
    r = dict(sizes=run([100, 1000, 10000]), chain=chain([10, 25, 50, 100, 200]))
    json.dump(r, _open(os.path.join(HERE, 'out/e3b_fix.json'), 'w'), indent=1)

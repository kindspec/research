#!/usr/bin/env python3
"""E3c: proper DAG closure hash -- per-node memo + explicit cycle detection.

derive.closure_hash threads a shared `seen` set through the recursion, so a
node's returned value depends on WHICH nodes were already visited.  That makes
per-node memoisation unsound and forces an O(closure) walk per resolve.

Restructured:  H(a) = sha256(bytes(a) || sorted(H(d) for d in deps(a)))
which is memoisable per node -> O(V+E) for a whole build, and gives a place to
detect cycles loudly instead of silently returning ''.
"""
import sys, os, time, json, statistics, shutil, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib')); sys.path.insert(0, HERE)
import gen, derive
import e3_derive as E

_open = open
_orig_ch, _orig_refs = derive.closure_hash, derive.refs


class Cycle(Exception): pass


def make_dag_hash():
    memo, stack = {}, []
    rmemo = {}

    def refs(path):
        if path not in rmemo: rmemo[path] = _orig_refs(path)
        return rmemo[path]

    def H(art, seen=None):
        if art in memo: return memo[art]
        if art in stack:
            raise Cycle('reference cycle: ' + ' -> '.join(stack[stack.index(art):] + [art]))
        stack.append(art)
        try:
            d = hashlib.sha256(_open(art, 'rb').read()).hexdigest()
            deps = sorted({dep for dep, _ in refs(art) if os.path.exists(dep)})
            for dep in deps:
                d += H(dep)
            v = hashlib.sha256(d.encode()).hexdigest()[:12]
        finally:
            stack.pop()
        memo[art] = v
        return v
    return H, refs


def install():
    H, refs = make_dag_hash()
    derive.closure_hash, derive.refs = H, refs
    return H


def restore():
    derive.closure_hash, derive.refs = _orig_ch, _orig_refs


def chain(depths):
    out = []
    for d in depths:
        p = os.path.join(E.WORK, f'chainB{d}')
        shutil.rmtree(p, ignore_errors=True); os.makedirs(p)
        for i in range(d):
            t = gen.tbl_text(20, seed=i)
            if i: t = f'use c{i-1:05d}.tbl#grand\n\n' + t
            _open(os.path.join(p, f'c{i:05d}.tbl'), 'w').write(t)
        docs = []
        for i in range(d):
            dn = f'm{i:05d}.md'
            _open(os.path.join(p, dn), 'w').write(f'V {{{{ c{i:05d}.tbl#grand }}}}.\n')
            docs.append(dn)
        shutil.rmtree(os.path.join(p, derive.CACHE), ignore_errors=True)
        E.build_all(p, docs)                       # prime the on-disk cache
        t_base = statistics.median([E._t(lambda: E.build_all(p, docs)) for _ in range(3)])
        ts = []
        for _ in range(3):
            install(); ts.append(E._t(lambda: E.build_all(p, docs)))
        restore()
        rec = dict(depth=d, baseline_s=t_base, dag_s=statistics.median(ts),
                   speedup=t_base / statistics.median(ts))
        out.append(rec); print('E3dag', json.dumps(rec), flush=True)
    return out


def correctness():
    """Same invalidation behaviour, plus loud cycles."""
    p = os.path.join(E.WORK, 'dagcheck'); shutil.rmtree(p, ignore_errors=True); os.makedirs(p)
    cwd = os.getcwd(); os.chdir(p)
    res = {}
    try:
        for i in range(5):
            t = gen.tbl_text(20, seed=i)
            if i: t = f'use c{i-1}.tbl#grand\n\n' + t
            _open(f'c{i}.tbl', 'w').write(t)
        H = install()
        before = H('c4.tbl')
        with _open('c0.tbl', 'a') as f: f.write('\n')
        H2 = install()
        res['deep_edit_detected'] = H2('c4.tbl') != before
        # cycle
        _open('x.tbl', 'w').write('use y.tbl#grand\n\n' + gen.tbl_text(5, seed=1))
        _open('y.tbl', 'w').write('use x.tbl#grand\n\n' + gen.tbl_text(5, seed=2))
        H3 = install()
        try:
            H3('x.tbl'); res['cycle_error'] = None
        except Cycle as e:
            res['cycle_error'] = str(e)
        _open('s.tbl', 'w').write('use s.tbl#grand\n\n' + gen.tbl_text(5, seed=3))
        H4 = install()
        try:
            H4('s.tbl'); res['self_error'] = None
        except Cycle as e:
            res['self_error'] = str(e)
        restore()
        # what the SHIPPED engine does on the same inputs
        res['shipped_cycle_result'] = _orig_ch('x.tbl')
        res['shipped_self_result'] = _orig_ch('s.tbl')
    finally:
        os.chdir(cwd)
    print('E3dagcheck', json.dumps(res), flush=True)
    return res


if __name__ == '__main__':
    r = dict(correctness=correctness(), chain=chain([10, 25, 50, 100, 200, 400]))
    json.dump(r, _open(os.path.join(HERE, 'out/e3c_dag.json'), 'w'), indent=1)

#!/usr/bin/env python3
"""E3: the derivation graph at scale.

Builds repos of N artifacts with realistic cross-references, then measures
cold / warm / incremental build, the per-resolve closure-hash cost, deep
chains, wide fan-in and cycle handling against experiments/L5-derivation.
"""
import sys, os, time, json, statistics, shutil, random, builtins, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib')); sys.path.insert(0, HERE)
import gen, derive, tbl

WORK = os.environ.get('W4WORK', '/home/cam/.local/state/scratch/claude-1000/w4')

# ---- instrumentation: count file opens and bytes hashed inside the engine
STAT = {'opens': 0, 'bytes': 0, 'closure_calls': 0, 'closure_s': 0.0}
_open = builtins.open


def counting_open(*a, **k):
    STAT['opens'] += 1
    return _open(*a, **k)


_ch = derive.closure_hash


def timed_closure(art, seen=None):
    if seen is None:
        STAT['closure_calls'] += 1
        t0 = time.perf_counter()
        try:
            return _ch(art, seen)
        finally:
            STAT['closure_s'] += time.perf_counter() - t0
    return _ch(art, seen)


def instrument(on):
    derive.open = counting_open if on else _open
    tbl_mod = sys.modules['tbl']
    derive.closure_hash = timed_closure if on else _ch


def reset():
    STAT.update(opens=0, bytes=0, closure_calls=0, closure_s=0.0)


def build_repo(path, n_tbl, n_doc, rows=20, refs_per_doc=3, tbl_chain_frac=0.3, seed=1):
    shutil.rmtree(path, ignore_errors=True); os.makedirs(path)
    rng = random.Random(seed)
    tbls = [f't{i:05d}.tbl' for i in range(n_tbl)]
    for i, t in enumerate(tbls):
        txt = gen.tbl_text(rows, seed=i)
        # some tables reference other tables (dependency edge the engine
        # discovers; the prototype evaluator cannot RESOLVE one -- see report)
        if i > 0 and rng.random() < tbl_chain_frac:
            dep = tbls[rng.randrange(i)]
            txt = f'use {dep}#grand\n\n' + txt
        _open(os.path.join(path, t), 'w').write(txt)
    docs = []
    for j in range(n_doc):
        d = f'd{j:05d}.md'
        body = gen.doc_text(1000 + j, nblocks=12)
        for _ in range(refs_per_doc):
            body += f'\nTotal is {{{{ {rng.choice(tbls)}#grand }}}} this period.\n'
        _open(os.path.join(path, d), 'w').write(body)
        docs.append(d)
    return tbls, docs


def build_all(path, docs):
    st = {'hit': 0, 'miss': 0}
    cwd = os.getcwd(); os.chdir(path)
    try:
        for d in docs:
            derive.render(d, st)
    finally:
        os.chdir(cwd)
    return st


def run_sizes(sizes):
    out = []
    for n in sizes:
        n_tbl = max(1, n // 2); n_doc = n - n_tbl
        p = os.path.join(WORK, f'graph{n}')
        tbls, docs = build_repo(p, n_tbl, n_doc)
        shutil.rmtree(os.path.join(p, derive.CACHE), ignore_errors=True)
        instrument(True); reset()
        t0 = time.perf_counter(); st_cold = build_all(p, docs); t_cold = time.perf_counter() - t0
        cold = dict(STAT)
        reset()
        t0 = time.perf_counter(); st_warm = build_all(p, docs); t_warm = time.perf_counter() - t0
        warm = dict(STAT)
        # incremental: touch ONE leaf table
        leaf = tbls[0]
        with _open(os.path.join(p, leaf), 'a') as f:
            f.write('\n')
        reset()
        t0 = time.perf_counter(); st_inc = build_all(p, docs); t_inc = time.perf_counter() - t0
        inc = dict(STAT)
        instrument(False)
        rec = dict(n=n, tables=n_tbl, docs=n_doc,
                   cold_s=t_cold, warm_s=t_warm, incremental_s=t_inc,
                   cold_miss=st_cold['miss'], cold_hit=st_cold['hit'],
                   warm_miss=st_warm['miss'], warm_hit=st_warm['hit'],
                   inc_miss=st_inc['miss'], inc_hit=st_inc['hit'],
                   cold_opens=cold['opens'], warm_opens=warm['opens'],
                   warm_closure_s=warm['closure_s'], warm_closure_calls=warm['closure_calls'],
                   warm_closure_pct=100 * warm['closure_s'] / t_warm,
                   cold_closure_pct=100 * cold['closure_s'] / t_cold,
                   opens_per_resolve=warm['opens'] / max(1, st_warm['hit'] + st_warm['miss']))
        out.append(rec); print('E3size', json.dumps(rec), flush=True)
    return out


def deep_chain(depths):
    out = []
    for d in depths:
        p = os.path.join(WORK, f'chain{d}')
        shutil.rmtree(p, ignore_errors=True); os.makedirs(p)
        for i in range(d):
            txt = gen.tbl_text(20, seed=i)
            if i:
                txt = f'use c{i-1:05d}.tbl#grand\n\n' + txt
            _open(os.path.join(p, f'c{i:05d}.tbl'), 'w').write(txt)
        _open(os.path.join(p, 'tip.md'), 'w').write(
            f'Tip is {{{{ c{d-1:05d}.tbl#grand }}}} today.\n')
        cwd = os.getcwd(); os.chdir(p)
        try:
            shutil.rmtree(derive.CACHE, ignore_errors=True)
            instrument(True); reset()
            st = {'hit': 0, 'miss': 0}
            t0 = time.perf_counter(); derive.render('tip.md', st); t_cold = time.perf_counter() - t0
            c1 = dict(STAT); reset()
            t0 = time.perf_counter(); derive.render('tip.md', st); t_warm = time.perf_counter() - t0
            c2 = dict(STAT)
            # closure hash of the tip alone
            reset()
            t_ch = statistics.median([_t(lambda: _ch(f'c{d-1:05d}.tbl')) for _ in range(5)])
            instrument(False)
        finally:
            os.chdir(cwd)
        rec = dict(depth=d, tip_cold_s=t_cold, tip_warm_s=t_warm,
                   closure_hash_s=t_ch, opens_cold=c1['opens'], opens_warm=c2['opens'])
        out.append(rec); print('E3chain', json.dumps(rec), flush=True)
    return out


def _t(f):
    t0 = time.perf_counter(); f(); return time.perf_counter() - t0


def fan_in(widths):
    out = []
    for w in widths:
        p = os.path.join(WORK, f'fan{w}')
        shutil.rmtree(p, ignore_errors=True); os.makedirs(p)
        _open(os.path.join(p, 'hub.tbl'), 'w').write(gen.tbl_text(200, seed=9))
        docs = []
        for j in range(w):
            d = f'f{j:05d}.md'
            _open(os.path.join(p, d), 'w').write(
                'Value {{ hub.tbl#grand }} recorded.\n')
            docs.append(d)
        shutil.rmtree(os.path.join(p, derive.CACHE), ignore_errors=True)
        instrument(True); reset()
        t0 = time.perf_counter(); s1 = build_all(p, docs); t_cold = time.perf_counter() - t0
        c1 = dict(STAT); reset()
        t0 = time.perf_counter(); s2 = build_all(p, docs); t_warm = time.perf_counter() - t0
        c2 = dict(STAT)
        # invalidate the hub -> every dependant must rebuild
        with _open(os.path.join(p, 'hub.tbl'), 'a') as f: f.write('\n')
        reset()
        t0 = time.perf_counter(); s3 = build_all(p, docs); t_inv = time.perf_counter() - t0
        c3 = dict(STAT)
        instrument(False)
        rec = dict(fanin=w, cold_s=t_cold, warm_s=t_warm, after_hub_edit_s=t_inv,
                   cold_miss=s1['miss'], warm_hit=s2['hit'] - s1['hit'],
                   inv_miss=s3['miss'] - s1['miss'], warm_opens=c2['opens'],
                   inv_opens=c3['opens'])
        out.append(rec); print('E3fan', json.dumps(rec), flush=True)
    return out


def cycles():
    p = os.path.join(WORK, 'cycle'); shutil.rmtree(p, ignore_errors=True); os.makedirs(p)
    res = {}
    for k, (a_dep, b_dep) in {'2cycle': ('b.tbl', 'a.tbl')}.items():
        _open(os.path.join(p, 'a.tbl'), 'w').write(f'use {a_dep}#grand\n\n' + gen.tbl_text(20, seed=1))
        _open(os.path.join(p, 'b.tbl'), 'w').write(f'use {b_dep}#grand\n\n' + gen.tbl_text(20, seed=2))
    cwd = os.getcwd(); os.chdir(p)
    try:
        t0 = time.perf_counter()
        try:
            h1 = _ch('a.tbl'); err = None
        except Exception as e:
            h1 = None; err = f'{type(e).__name__}: {e}'
        res['cycle2_s'] = time.perf_counter() - t0
        res['cycle2_hash'] = h1
        res['cycle2_error'] = err
        # long cycle: 100 artifacts in a ring
        for i in range(100):
            _open(f'r{i:03d}.tbl', 'w').write(f'use r{(i+1)%100:03d}.tbl#grand\n\n' + gen.tbl_text(20, seed=i))
        t0 = time.perf_counter()
        try:
            h2 = _ch('r000.tbl'); err2 = None
        except Exception as e:
            h2 = None; err2 = f'{type(e).__name__}: {e}'
        res['cycle100_s'] = time.perf_counter() - t0
        res['cycle100_hash'] = h2
        res['cycle100_error'] = err2
        # does a change on the far side of the ring change the near hash?
        before = _ch('r000.tbl')
        with _open('r050.tbl', 'a') as f: f.write('\n')
        after = _ch('r000.tbl')
        res['ring_far_edit_detected'] = before != after
        # self-reference
        _open('s.tbl', 'w').write('use s.tbl#grand\n\n' + gen.tbl_text(20, seed=3))
        t0 = time.perf_counter()
        try:
            res['self_hash'] = _ch('s.tbl'); res['self_error'] = None
        except Exception as e:
            res['self_hash'] = None; res['self_error'] = f'{type(e).__name__}: {e}'
        res['self_s'] = time.perf_counter() - t0
    finally:
        os.chdir(cwd)
    print('E3cycle', json.dumps(res), flush=True)
    return res


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    os.makedirs(WORK, exist_ok=True)
    r = {}
    if which in ('all', 'size'): r['sizes'] = run_sizes([100, 1000, 10000])
    if which in ('all', 'chain'): r['chain'] = deep_chain([1, 10, 25, 50, 100, 200])
    if which in ('all', 'fan'): r['fanin'] = fan_in([10, 100, 1000])
    if which in ('all', 'cycle'): r['cycles'] = cycles()
    json.dump(r, _open(os.path.join(HERE, f'out/e3_{which}.json'), 'w'), indent=1)

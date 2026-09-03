#!/usr/bin/env python3
"""E2: markdown corpora at scale; block boundary parse + round-trip;
and the O(n^2) similarity block merge curve, with a measured fix."""
import sys, os, time, json, statistics, difflib, shutil, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib')); sys.path.insert(0, HERE)
import gen, blocks, bmerge2

WORK = os.environ.get('W4WORK', '/home/cam/.local/state/scratch/claude-1000/w4')


def med(f, reps=5):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); r = f(); ts.append(time.perf_counter() - t0)
    return statistics.median(ts), r


# ------------------------------------------------------------ corpora
def corpora(counts):
    out = []
    for c in counts:
        d = os.path.join(WORK, f'corp{c}')
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        texts = []
        for i in range(c):
            t = gen.doc_text(i, nblocks=40)
            texts.append(t)
            open(os.path.join(d, f'doc{i:05d}.md'), 'w').write(t)
        tot = sum(len(t.encode()) for t in texts)

        def parse_all():
            return sum(len(blocks.parse(t)) for t in texts)
        t_parse, nb = med(parse_all, 3)

        def rt_all():
            ok = 0
            for t in texts:
                if blocks.render(blocks.parse(t)) == t: ok += 1
            return ok
        t_rt, ok = med(rt_all, 3)
        rec = dict(docs=c, total_mb=tot / 2**20, blocks=nb, parse_s=t_parse,
                   roundtrip_s=t_rt, roundtrip_exact=ok,
                   mb_per_s=(tot / 2**20) / t_parse, us_per_block=1e6 * t_parse / nb)
        out.append(rec); print('E2corpus', json.dumps(rec), flush=True)
    return out


def bigdocs(lines_list):
    out = []
    for nl in lines_list:
        t = gen.doc_lines(nl)
        t_parse, b = med(lambda: blocks.parse(t), 3)
        t_rt, ok = med(lambda: blocks.render(blocks.parse(t)) == t, 3)
        rec = dict(target_lines=nl, actual_lines=t.count('\n'), mb=len(t.encode()) / 2**20,
                   blocks=len(b), parse_s=t_parse, roundtrip_s=t_rt, exact=ok)
        out.append(rec); print('E2bigdoc', json.dumps(rec), flush=True)
    return out


# ------------------------------------------------------------ block merge
def variants(text, nedits, seed):
    """Edit nedits blocks, insert one, delete one."""
    rng = random.Random(seed)
    bs = blocks.parse(text)
    raws = [r for _, r in bs]
    idx = rng.sample(range(2, len(raws) - 2), min(nedits, len(raws) - 4))
    for i in idx:
        raws[i] = raws[i].rstrip() + f' Amended by {seed}.\n\n'
    raws.insert(len(raws) // 3, f'A brand new paragraph added by side {seed}.\n\n')
    return ''.join(raws)


def merge_curve(nblocks_list, edit_fracs):
    out = []
    for nb in nblocks_list:
        base = gen.doc_text(1, nblocks=nb)
        nreal = len(blocks.parse(base))
        for ef in edit_fracs:
            k = max(1, int(nreal * ef))
            if k * nreal > 3_000_000:
                print('E2merge SKIP (predicted %d ratio() calls > budget)' % (k * nreal), flush=True)
                continue
            o = variants(base, k, 2)
            t = variants(base, k, 3)
            calls = [0]
            orig = difflib.SequenceMatcher

            class Counting(orig):
                def ratio(self):
                    calls[0] += 1
                    return orig.ratio(self)
            bmerge2.difflib.SequenceMatcher = Counting
            t0 = time.perf_counter(); s, c = bmerge2.m3(base, o, t); el = time.perf_counter() - t0
            bmerge2.difflib.SequenceMatcher = orig
            rec = dict(blocks=nreal, edit_frac=ef, edited=k, merge_s=el,
                       ratio_calls=calls[0], conflicts=len(c), out_bytes=len(s))
            out.append(rec); print('E2merge', json.dumps(rec), flush=True)
            if el > 120:
                print('  (stopping this size: over 120s)', flush=True)
                break
    return out


# ------------------------------------------------------------ the fix
def match_fast(base, side, thresh=0.5):
    """Same semantics as bmerge2.match, with sound pruning.

    ratio = 2M/(la+lb) and M <= min(la,lb), so ratio > t implies
    min/max > t/(2-t).  For t=0.5 that is min/max > 1/3 -- a SOUND bucket
    bound, no false negatives.  Then difflib's own real_quick_ratio /
    quick_ratio upper bounds before the real ratio.
    """
    bd = dict(base); used = set(); m = {}
    for n, raw in side:
        if n in bd and n not in used:
            m[n] = n; used.add(n)
    lo = thresh / (2 - thresh)
    cand = [(len(braw.strip()), bn, braw.strip()) for bn, braw in base]
    cand.sort()
    lens = [c[0] for c in cand]
    import bisect
    for n, raw in side:
        if n in m: continue
        r = raw.strip(); lr = len(r)
        best, score = None, thresh
        i0 = bisect.bisect_left(lens, lr * lo)
        i1 = bisect.bisect_right(lens, lr / lo if lo else 1e18)
        sm = difflib.SequenceMatcher(None, '', r)   # seq2 fixed -> b2j built once
        for k in range(i0, i1):
            _, bn, braw = cand[k]
            if bn in used: continue
            sm.set_seq1(braw)
            if sm.real_quick_ratio() <= score or sm.quick_ratio() <= score:
                continue
            v = sm.ratio()
            if v > score: best, score = bn, v
        if best: m[n] = best; used.add(best)
    return m


def fix_bench(nblocks_list, ef=0.1):
    out = []
    for nb in nblocks_list:
        base = gen.doc_text(1, nblocks=nb)
        B = blocks.parse(base)
        k = max(1, int(len(B) * ef))
        o = variants(base, k, 2)
        O = blocks.parse(o)
        t_old, m_old = med(lambda: bmerge2.match(B, O), 1)
        t_new, m_new = med(lambda: match_fast(B, O), 1)
        rec = dict(blocks=len(B), edited=k, old_s=t_old, new_s=t_new,
                   speedup=t_old / t_new if t_new else None, identical=m_old == m_new,
                   n_matched=len(m_new))
        out.append(rec); print('E2fix', json.dumps(rec), flush=True)
    return out


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    os.makedirs(WORK, exist_ok=True)
    res = {}
    if which in ('all', 'corp'): res['corpora'] = corpora([100, 1000, 10000])
    if which in ('all', 'big'): res['bigdocs'] = bigdocs([10000, 100000])
    if which in ('all', 'merge'):
        res['merge'] = merge_curve([50, 100, 250, 500, 1000, 2000, 4000, 8000, 16000], [0.02, 0.1, 0.5])
    if which in ('all', 'fix'): res['fix'] = fix_bench([100, 500, 1000, 2000, 4000, 8000])
    json.dump(res, open(os.path.join(HERE, f'out/e2_{which}.json'), 'w'), indent=1)

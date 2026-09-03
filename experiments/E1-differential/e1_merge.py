#!/usr/bin/env python3
"""Merge E1 shard results.

    e1.py '<glob>' --shard=0/8 --out=out/s0.json
    ...                                          (8 agents, disjoint)
    e1_merge.py out/s*.json [--out=out/merged.json]

Every counter sums, because `pick_files` puts each workbook in exactly one
shard. The two counters that are SET SIZES rather than tallies --
`distinct.workbooks-contributing` and `distinct.sheets-contributing` -- are
recomputed from the unioned member lists each shard writes, so they stay right
even if someone runs overlapping shards by mistake. Samples concatenate up to
the same per-key cap.

Shards are refused if their `expand_sum` or `mutate` settings disagree: merging
a --expand-sum shard into a baseline one would report a number that describes
no run.
"""
import sys, json, glob, collections

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from e1 import report

SETKEYS = {'distinct.workbooks-contributing': 'wb',
           'distinct.sheets-contributing': 'sheet'}
CAP = 40


def merge(paths):
    cnt = collections.Counter()
    sets = {'wb': set(), 'sheet': set()}
    samples = collections.defaultdict(list)
    metas = []
    for p in paths:
        d = json.load(open(p))
        m = d.get('meta') or {}
        metas.append((p, m))
        for k, v in d['counts'].items():
            if k in SETKEYS: continue
            cnt[k] += v
        for s in sets: sets[s].update(d.get(s) or [])
        for k, v in (d.get('samples') or {}).items():
            samples[k] += v[:max(0, CAP - len(samples[k]))]
    opts = {(m.get('expand_sum'), m.get('mutate')) for _, m in metas}
    if len(opts) > 1:
        raise SystemExit('refusing to merge shards run with different settings: %s'
                         % sorted(str(o) for o in opts))
    # A duplicate shard DOUBLES every tally while the set-valued counters stay
    # right, so the headline denominator moves and nothing says so. The shard id
    # was printed and a careful reader could have caught it; nothing refused it.
    # A merge OUTPUT carries `shards` (plural) rather than `shard`. Feeding one
    # back into a glob double-counts every tally -- which is exactly what
    # happened the first time these guards were tested, because `out/*.json`
    # matched the previous `merged.json`. A guard that misses the case that
    # produced it is not a guard.
    merged_in = [p for p, m in metas if 'shards' in m]
    if merged_in:
        raise SystemExit('refusing to merge: %s is itself a merge output. Merging '
                         'it with its own inputs doubles every tally.'
                         % ', '.join(merged_in))
    ids = [str(m.get('shard') or '?') for _, m in metas]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise SystemExit('refusing to merge: shard id(s) %s appear more than once. '
                         'Every tally would double while the set-valued counters '
                         'stayed correct, so the headline would move silently.'
                         % ', '.join(dupes))
    # And an INCOMPLETE set is the same failure in the other direction: a
    # missing shard is a smaller denominator that still reports a percentage.
    parts = [i.split('/') for i in ids if '/' in i]
    if parts and len({p[1] for p in parts}) == 1:
        n = int(parts[0][1])
        have = {int(p[0]) for p in parts}
        missing = sorted(set(range(n)) - have)
        if missing:
            raise SystemExit('refusing to merge: shards %s of %d are missing. '
                             'A partial merge still prints a percentage.'
                             % (', '.join(map(str, missing)), n))
    for k, s in SETKEYS.items(): cnt[k] = len(sets[s])
    shards = sorted(str((m.get('shard') or '?')) for _, m in metas)
    return cnt, sets, samples, dict(shards=shards,
                                    files=sum(m.get('files') or 0 for _, m in metas),
                                    expand_sum=list(opts)[0][0],
                                    mutate=list(opts)[0][1])


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = ([a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--out=')] or [None])[0]
    paths = []
    for a in args: paths += sorted(glob.glob(a))
    if not paths: raise SystemExit('no shard files matched')
    cnt, sets, samples, meta = merge(paths)
    print('merged %d shard files: %s' % (len(paths), ' '.join(meta['shards'])))
    print('workbooks: %d   expand_sum=%s   mutate=%s'
          % (meta['files'], meta['expand_sum'], meta['mutate']))
    print()
    for k, v in sorted(cnt.items()): print('%-52s %8d' % (k, v))
    report(cnt)
    if out:
        json.dump({'meta': meta, 'counts': dict(cnt),
                   'wb': sorted(sets['wb']), 'sheet': sorted(sets['sheet']),
                   'samples': dict(samples)}, open(out, 'w'), indent=1, default=str)
        print('\nwrote', out)

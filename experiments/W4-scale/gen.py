#!/usr/bin/env python3
"""Generators for realistic .tbl / .csv / .md fixtures at scale."""
import random, os

REGIONS = ['north', 'south', 'east', 'west', 'central']
ITEMS = ['widget', 'gadget', 'sprocket', 'flange', 'bracket', 'gasket', 'coupler']

LIT = ['id', 'item', 'region', 'qty', 'unit', 'tax_rate']
COMP = [('total', 'qty * unit'), ('taxed', 'total * tax_rate'), ('net', 'total - taxed')]
AGGS = ['grand := sum(total)', 'nrows := count(id)', 'taxes := sum(taxed)']


def rowvals(i, rng):
    return [f'r_{i:08x}',
            f'{rng.choice(ITEMS)}-{i:06d}',
            rng.choice(REGIONS),
            str(rng.randint(1, 500)),
            f'{rng.uniform(0.5, 900):.2f}',
            f'{rng.choice([0.05, 0.07, 0.13, 0.0]):.2f}']


def tbl_text(n, seed=7, pad=True, ncols_extra=0):
    """Realistic .tbl: 6 literal cols + 3 computed + aggregates."""
    rng = random.Random(seed)
    extra = [f'x{j:03d}' for j in range(ncols_extra)]
    header = LIT + extra + [f'{n_} = {e}' for n_, e in COMP]
    align = ['---'] * len(LIT) + ['---'] * len(extra) + ['--:'] * len(COMP)
    body = []
    for i in range(n):
        v = rowvals(i, rng) + [f'{rng.randint(0,999)}' for _ in extra] + [''] * len(COMP)
        body.append(v)
    cells = [header, align] + body
    if pad:
        w = [0] * len(header)
        for r in cells:
            for j, c in enumerate(r):
                w[j] = max(w[j], len(c))
        lines = ['| ' + ' | '.join(c.ljust(w[j]) for j, c in enumerate(r)) + ' |' for r in cells]
    else:
        lines = ['| ' + ' | '.join(r) + ' |' for r in cells]
    return '\n'.join(lines) + '\n\n' + '\n'.join(AGGS) + '\n'


def csv_text(n, seed=7, with_id=True):
    rng = random.Random(seed)
    cols = (LIT if with_id else LIT[1:]) + [c for c, _ in COMP]
    out = [','.join(cols)]
    for i in range(n):
        v = rowvals(i, rng)
        if not with_id:
            v = v[1:]
        out.append(','.join(v + [''] * len(COMP)))
    return '\n'.join(out) + '\n'


WORDS = ('the quick brown fox jumps over a lazy dog while procurement totals '
         'were reconciled against plan and variance above five percent requires '
         'written justification from the responsible budget owner this quarter').split()


def doc_text(seed, nblocks=40, ref=None):
    """Realistic markdown doc: frontmatter, headings, prose (one sentence/line),
    lists, code fences."""
    rng = random.Random(seed)
    p = [f'---\nid: 01J{seed:08X}\ntitle: Document {seed}\n---\n']
    for b in range(nblocks):
        k = rng.random()
        if k < 0.15:
            p.append(f'{"#" * rng.randint(1,3)} Section {b} of doc {seed}\n')
        elif k < 0.72:
            sents = []
            for _ in range(rng.randint(2, 5)):
                sents.append(' '.join(rng.choice(WORDS) for _ in range(rng.randint(6, 16))).capitalize() + '.')
            p.append('\n'.join(sents) + '\n')
        elif k < 0.88:
            p.append('\n'.join(f'- {" ".join(rng.choice(WORDS) for _ in range(rng.randint(3,9)))}'
                               for _ in range(rng.randint(2, 6))) + '\n')
        else:
            p.append('```python\n' + '\n'.join(f'x{i} = {rng.randint(0,999)}' for i in range(rng.randint(2, 6))) + '\n```\n')
    if ref:
        p.append(f'Procurement totalled {{{{ {ref} }}}} against plan.\n')
    return '\n'.join(p)


def doc_lines(nlines, seed=3):
    """A single big document of ~nlines lines, one sentence per line."""
    rng = random.Random(seed)
    out = [f'---\nid: 01JBIG{seed}\ntitle: Big\n---\n']
    i = 0
    while i < nlines:
        if rng.random() < 0.08:
            out.append(f'## Section {i}\n')
            i += 2
            continue
        n = rng.randint(2, 6)
        out.append('\n'.join(' '.join(rng.choice(WORDS) for _ in range(rng.randint(6, 16))).capitalize() + '.'
                             for _ in range(n)) + '\n')
        i += n + 1
    return '\n'.join(out)

#!/usr/bin/env python3
"""D8: Head-to-head measurement of SUB-ARTIFACT IDENTITY strategies on real
markdown git history.

  STORED   : an id is materialised into the file at C_i; the author's real edit
             (C_i -> C_j) is applied via stock-git 3-way merge (= a rebase).
             Does the id survive, and unambiguously?
  COMPUTED : no id in the file. The reference stores
             (exact quote, prefix ctx, suffix ctx, char offset).
             At C_j we re-anchor: exact -> exact+context -> fuzzy (difflib).

Both arms are evaluated on the SAME (C_i, C_j, block) triples, so the rates are
directly comparable, and we can count DISAGREEMENTS (one of them is wrong).
"""
import subprocess, sys, os, re, difflib, random, json, tempfile, hashlib
from collections import Counter

FUZZ = 0.5          # git's rename-detection threshold, as used in L3
CTX  = 48           # chars of prefix/suffix context (Hypothes.is uses 32)

def git(repo, *a):
    return subprocess.run(['git','-C',repo,*a], capture_output=True, text=True).stdout

def blocks(text):
    """Boundary-only block parse (L3): blank-line separated, fences respected."""
    lines = text.splitlines(keepends=True)
    out, cur, fence = [], [], None
    for l in lines:
        s = l.strip()
        f = re.match(r'^(```|~~~)', s)
        if fence:
            cur.append(l)
            if f and s.startswith(fence): fence = None
            continue
        if f:
            if cur: out.append(cur); cur=[]
            fence = f.group(1); cur.append(l); continue
        if s == '':
            cur.append(l); out.append(cur); cur=[]; continue
        if s.startswith('#') and cur and ''.join(cur).strip():
            out.append(cur); cur=[]
        cur.append(l)
    if cur: out.append(cur)
    res, pos = [], 0
    for b in out:
        raw = ''.join(b); c = raw.strip()
        if c: res.append({'raw':raw,'content':c,'off':pos + raw.index(c[0]) if c[0] in raw else pos})
        pos += len(raw)
    return res

def anchor_of(text, blk):
    o = blk['off']; q = blk['content']
    return {'quote': q, 'prefix': text[max(0,o-CTX):o], 'suffix': text[o+len(q):o+len(q)+CTX],
            'pos': o, 'len': len(text)}

def reanchor(text, anc, cand):
    """Return (status, index_into_cand or None)."""
    q = anc['quote']
    hits = [i for i,b in enumerate(cand) if b['content'] == q]
    if len(hits) == 1: return 'EXACT', hits[0]
    if len(hits) > 1:
        # disambiguate with context, then with position
        scored = []
        for i in hits:
            o = cand[i]['off']
            pre = text[max(0,o-CTX):o]; suf = text[o+len(q):o+len(q)+CTX]
            s = (difflib.SequenceMatcher(None, pre, anc['prefix']).ratio() +
                 difflib.SequenceMatcher(None, suf, anc['suffix']).ratio())
            scored.append((s,i))
        scored.sort(reverse=True)
        if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.05:
            return 'AMBIGUOUS', scored[0][1]
        return 'EXACT_CTX', scored[0][1]
    # fuzzy
    best = []
    relpos = anc['pos']/max(1,anc['len'])
    for i,b in enumerate(cand):
        if abs(len(b['content'])-len(q)) > max(200, 3*len(q)): continue
        r = difflib.SequenceMatcher(None, q, b['content']).ratio()
        if r >= FUZZ:
            posbonus = 1 - abs(b['off']/max(1,len(text)) - relpos)
            best.append((r, posbonus, i))
    if not best: return 'ORPHAN', None
    best.sort(reverse=True)
    if len(best) > 1 and best[0][0]-best[1][0] < 0.05:
        return 'FUZZY_RISKY', best[0][2]
    return 'FUZZY', best[0][2]

MARK = re.compile(r'\s\^zz([0-9a-f]{6})\b')

def inject_ids(text, blks):
    """Materialise an Obsidian-style ^id at the end of each block."""
    out = []; last = 0; ids = []
    for n,b in enumerate(blks):
        i = text.index(b['content'], last)
        end = i + len(b['content'])
        bid = hashlib.sha1(f'{n}{b["content"][:20]}'.encode()).hexdigest()[:6]
        out.append(text[last:end]); out.append(f' ^zz{bid}')
        ids.append(bid); last = end
    out.append(text[last:])
    return ''.join(out), ids

def merge3(ours, base, theirs):
    with tempfile.TemporaryDirectory() as d:
        p = lambda n,c: (open(os.path.join(d,n),'w',encoding='utf-8').write(c), os.path.join(d,n))[1]
        a,b,c = p('o',ours), p('b',base), p('t',theirs)
        r = subprocess.run(['git','merge-file','-p','--diff3',a,b,c],capture_output=True,text=True)
        return r.stdout, r.returncode

def conflict_regions(txt):
    regs, start = [], None
    off = 0
    for line in txt.splitlines(keepends=True):
        if line.startswith('<<<<<<<'): start = off
        elif line.startswith('>>>>>>>') and start is not None:
            regs.append((start, off+len(line))); start=None
        off += len(line)
    return regs

def run(repo, pathglob, gap, sample_files=12, sample_blocks=25, seed=7):
    rnd = random.Random(seed)
    files = [f for f in git(repo,'ls-files',pathglob).split('\n') if f.endswith('.md')]
    rnd.shuffle(files); files = files[:sample_files]
    tally = Counter(); pairs = 0; agree=0; disagree=0; both=0
    examples = []
    for f in files:
        cs = [c for c in git(repo,'log','--format=%H','--reverse','--',f).split('\n') if c]
        if len(cs) < gap+1: continue
        for start in range(0, len(cs)-gap, max(1,(len(cs)-gap)//3 or 1)):
            ci, cj = cs[start], cs[start+gap]
            ti = git(repo,'show',f'{ci}:{f}'); tj = git(repo,'show',f'{cj}:{f}')
            if not ti or not tj or ti == tj: continue
            bi, bj = blocks(ti), blocks(tj)
            if len(bi) < 4: continue
            pairs += 1
            # ---- STORED arm: inject ids at C_i, 3-way merge the real edit ----
            ours, ids = inject_ids(ti, bi)
            merged, _ = merge3(ours, ti, tj)
            cregs = conflict_regions(merged)
            found = {}
            for m in MARK.finditer(merged):
                inc = any(s <= m.start() < e for s,e in cregs)
                found.setdefault(m.group(1), []).append(inc)
            # ---- sample blocks and evaluate both arms ----
            idx = list(range(len(bi))); rnd.shuffle(idx)
            for k in idx[:sample_blocks]:
                anc = anchor_of(ti, bi[k])
                if len(anc['quote']) < 20: continue
                st, hit = reanchor(tj, anc, bj)
                tally['C:'+st] += 1
                occ = found.get(ids[k], [])
                if not occ: sst='LOST'
                elif len(occ) > 1: sst='DUPLICATED'
                elif occ[0]: sst='CONFLICT'
                else: sst='SURVIVED'
                tally['S:'+sst] += 1
                tally[f'PAIR:{sst}/{st}'] += 1
    return tally, pairs

if __name__ == '__main__':
    repo, glob, gap = sys.argv[1], sys.argv[2], int(sys.argv[3])
    t, pairs = run(repo, glob, gap)
    print(f'\n=== {os.path.basename(repo)}  {glob}  gap={gap} commits   version-pairs={pairs} ===')
    tot = sum(v for k,v in t.items() if k.startswith('C:'))
    print(f'block-anchors evaluated: {tot}')
    print('  COMPUTED (quote+context+fuzzy, nothing in the file):')
    for k in ['EXACT','EXACT_CTX','FUZZY','FUZZY_RISKY','AMBIGUOUS','ORPHAN']:
        v=t['C:'+k]; print(f'    {k:<12} {v:6d}  {100*v/max(1,tot):5.1f}%')
    print('  STORED (^id written at C_i, real edit applied by stock 3-way merge):')
    for k in ['SURVIVED','CONFLICT','LOST','DUPLICATED']:
        v=t['S:'+k]; print(f'    {k:<12} {v:6d}  {100*v/max(1,tot):5.1f}%')
    print('  cross-tab (stored/computed), top 10:')
    for k,v in sorted(((k,v) for k,v in t.items() if k.startswith('PAIR:')), key=lambda x:-x[1])[:10]:
        print(f'    {k[5:]:<28} {v:6d}')

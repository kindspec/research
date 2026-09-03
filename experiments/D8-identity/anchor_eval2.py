#!/usr/bin/env python3
"""D8 v2: adds an INDEPENDENT ORACLE so we can separate
   'correctly refused to anchor' (loud, safe) from 'anchored to the wrong block'
   (silent-wrong, the failure this whole design is organised against).

Oracle = git-style LINE correspondence (difflib on the line sequence), a
different granularity and a different algorithm from the block-quote anchorer.
Blocks the oracle cannot confidently classify are EXCLUDED, and reported.
"""
import subprocess, sys, os, re, difflib, random, tempfile, hashlib
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anchor_eval import git, blocks, anchor_of, reanchor, inject_ids, merge3, conflict_regions, MARK, FUZZ

def line_oracle(ti, tj, bi, bj):
    li, lj = ti.splitlines(), tj.splitlines()
    sm = difflib.SequenceMatcher(None, li, lj, autojunk=False)
    m = {}
    for a,b,n in sm.get_matching_blocks():
        for k in range(n): m[a+k] = b+k
    # line index -> block index, both sides
    def lineidx(text, bl):
        idx = {}; 
        for n,b in enumerate(bl):
            s = text[:text.index(b['content'])].count('\n')
            e = s + b['content'].count('\n')
            for L in range(s,e+1): idx[L]=n
        return idx
    ii, jj = lineidx(ti,bi), lineidx(tj,bj)
    out = {}
    for n,b in enumerate(bi):
        mine = [L for L,bn in ii.items() if bn==n]
        if not mine: out[n]=('UNKNOWN',None); continue
        mapped = [m[L] for L in mine if L in m and li[L].strip()]
        nonblank = [L for L in mine if li[L].strip()]
        if not nonblank: out[n]=('UNKNOWN',None); continue
        frac = len(mapped)/len(nonblank)
        if frac >= 0.5:
            tgt = Counter(jj[L] for L in mapped if L in jj)
            out[n] = ('SURVIVED', tgt.most_common(1)[0][0]) if tgt else ('UNKNOWN',None)
        elif frac == 0.0:
            best = max((difflib.SequenceMatcher(None,b['content'],x['content']).ratio() for x in bj), default=0)
            out[n] = ('DELETED',None) if best < 0.3 else ('UNKNOWN',None)
        else:
            out[n] = ('UNKNOWN',None)
    return out

def run(repo, pathglob, gap, sample_files=14, sample_blocks=30, seed=7):
    rnd = random.Random(seed); t = Counter(); pairs=0; wrongs=[]
    files = [f for f in git(repo,'ls-files',pathglob).split('\n') if f.endswith('.md')]
    rnd.shuffle(files); files=files[:sample_files]
    for f in files:
        cs = [c for c in git(repo,'log','--format=%H','--reverse','--',f).split('\n') if c]
        if len(cs) < gap+1: continue
        for start in range(0, len(cs)-gap, max(1,(len(cs)-gap)//3 or 1)):
            ci,cj = cs[start], cs[start+gap]
            ti,tj = git(repo,'show',f'{ci}:{f}'), git(repo,'show',f'{cj}:{f}')
            if not ti or not tj or ti==tj: continue
            bi,bj = blocks(ti), blocks(tj)
            if len(bi)<4 or len(bj)<4: continue
            pairs+=1
            orc = line_oracle(ti,tj,bi,bj)
            ours, ids = inject_ids(ti,bi)
            merged,_ = merge3(ours, ti, tj); cregs = conflict_regions(merged)
            found={}
            for mm in MARK.finditer(merged):
                found.setdefault(mm.group(1),[]).append(any(s<=mm.start()<e for s,e in cregs))
            idx=list(range(len(bi))); rnd.shuffle(idx)
            for k in idx[:sample_blocks]:
                anc = anchor_of(ti,bi[k])
                if len(anc['quote'])<20: continue
                st,hit = reanchor(tj,anc,bj)
                truth,tgt = orc[k]
                t['ORACLE:'+truth]+=1
                if truth=='UNKNOWN': continue
                t['EV']+=1
                resolved = st not in ('ORPHAN',)
                if truth=='SURVIVED':
                    if not resolved: t['C:missed_loud']+=1
                    elif hit==tgt:   t['C:correct']+=1
                    else:
                        t['C:WRONG']+=1
                        if len(wrongs)<6: wrongs.append((f,st,anc['quote'][:70],bj[hit]['content'][:70]))
                else:  # DELETED -> the reference SHOULD break
                    if resolved: t['C:WRONG']+=1; t['C:wrong_on_deleted']+=1
                    else: t['C:correct']+=1
                # stored arm
                occ=found.get(ids[k],[])
                sst = 'LOST' if not occ else ('DUPLICATED' if len(occ)>1 else ('CONFLICT' if occ[0] else 'SURVIVED'))
                t['S:'+sst]+=1
                if truth=='SURVIVED' and sst=='SURVIVED': t['S:correct']+=1
                elif truth=='SURVIVED' and sst=='CONFLICT': t['S:loud']+=1
                elif truth=='DELETED' and sst in ('LOST','CONFLICT'): t['S:correct']+=1
                elif truth=='DELETED' and sst=='SURVIVED': t['S:WRONG']+=1
    return t,pairs,wrongs

if __name__=='__main__':
    repo,glob,gap = sys.argv[1],sys.argv[2],int(sys.argv[3])
    t,pairs,wrongs = run(repo,glob,gap)
    ev=t['EV']; tot=ev+t['ORACLE:UNKNOWN']
    print(f"\n### {os.path.basename(repo)} {glob} gap={gap}  pairs={pairs}  anchors={tot}  oracle-confident={ev} ({100*ev/max(1,tot):.0f}%)")
    print(f"  oracle: SURVIVED={t['ORACLE:SURVIVED']} DELETED={t['ORACLE:DELETED']} UNKNOWN={t['ORACLE:UNKNOWN']}")
    print(f"  COMPUTED anchoring (quote+ctx+fuzzy, nothing stored in the file):")
    print(f"     correct           {t['C:correct']:5d}  {100*t['C:correct']/max(1,ev):5.1f}%")
    print(f"     missed (LOUD)     {t['C:missed_loud']:5d}  {100*t['C:missed_loud']/max(1,ev):5.1f}%   <- refused; safe")
    print(f"     WRONG (SILENT)    {t['C:WRONG']:5d}  {100*t['C:WRONG']/max(1,ev):5.1f}%   (of which anchored to a deleted block's replacement: {t['C:wrong_on_deleted']})")
    print(f"  STORED ^id under stock-git 3-way merge (concurrent id-write + edit):")
    print(f"     correct           {t['S:correct']:5d}  {100*t['S:correct']/max(1,ev):5.1f}%")
    print(f"     conflict (LOUD)   {t['S:loud']:5d}  {100*t['S:loud']/max(1,ev):5.1f}%")
    print(f"     WRONG (SILENT)    {t['S:WRONG']:5d}  {100*t['S:WRONG']/max(1,ev):5.1f}%")
    for w in wrongs: print(f"     ex[{w[1]}] {w[2]!r}\n            -> {w[3]!r}")

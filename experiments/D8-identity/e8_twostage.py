#!/usr/bin/env python3
"""D8-E8: TWO-STAGE anchoring.  Stage 1 anchors the BLOCK (the unit whose
identity L3 already computes by similarity).  Stage 2 locates the span INSIDE
that block only.  If stage 1 refuses, stage 2 never runs -> the reference
orphans LOUDLY instead of landing somewhere plausible.
Compared head-to-head with the one-stage sliding-window anchorer of E7.
"""
import sys,os,re,difflib,random
from collections import Counter
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from anchor_eval import git, blocks, anchor_of
from anchor_eval2 import line_oracle
from anchor_eval3 import reanchor2, btype
from e7_span_anchor import spans_in, anchor as spananchor, find as find1, CTX

def find2(tj, bj, blkanc, spananc):
    st, bi_ = reanchor2(tj, blkanc, bj, hard=True)
    if bi_ is None: return 'BLOCK_'+st, None, None
    b = bj[bi_]; hay = b['content']; q = spananc['exact']
    hits=[m.start() for m in re.finditer(re.escape(q), hay)]
    if len(hits)==1: return 'SPAN_EXACT', bi_, b['off']+hits[0]
    if len(hits)>1:  return 'SPAN_AMBIG', bi_, None
    best=(0,None); L=len(q)
    for i in range(0, max(1,len(hay)-L+1)):
        r=difflib.SequenceMatcher(None,q,hay[i:i+L]).ratio()
        if r>best[0]: best=(r,i)
    if best[0]>=0.7: return 'SPAN_FUZZY', bi_, b['off']+best[1]
    return 'SPAN_ORPHAN', bi_, None

def run(repo,glob,gap,sf=14,sb=20,seed=3):
    rnd=random.Random(seed); t=Counter()
    files=[f for f in git(repo,'ls-files',glob).split('\n') if f.endswith('.md')]
    rnd.shuffle(files); files=files[:sf]
    for f in files:
        cs=[c for c in git(repo,'log','--format=%H','--reverse','--',f).split('\n') if c]
        if len(cs)<gap+1: continue
        for start in range(0,len(cs)-gap,max(1,(len(cs)-gap)//3 or 1)):
            ti,tj=git(repo,'show',f'{cs[start]}:{f}'),git(repo,'show',f'{cs[start+gap]}:{f}')
            if not ti or not tj or ti==tj: continue
            bi,bj=blocks(ti),blocks(tj)
            if len(bi)<4 or len(bj)<4: continue
            orc=line_oracle(ti,tj,bi,bj)
            idx=[k for k in range(len(bi)) if orc[k][0]!='UNKNOWN']; rnd.shuffle(idx)
            for k in idx[:sb]:
                truth,tgt=orc[k]; blkanc=anchor_of(ti,bi[k])
                for (s,e) in spans_in(bi[k],rnd):
                    sa=spananchor(ti,bi[k]['off'],s,e)
                    if len(sa['exact'])<25: continue
                    t['N']+=1
                    for lab, res in (('1stage', find1(tj,sa)), ('2stage', find2(tj,bj,blkanc,sa)[::2] if True else None)):
                        st,pos = (res[0],res[1]) if lab=='1stage' else (res[0],res[1])
                        if truth=='DELETED':
                            t[f'{lab}:'+('correct' if pos is None else 'WRONG')]+=1
                        else:
                            if pos is None: t[f'{lab}:loud']+=1
                            else:
                                tb=bj[tgt]; lo=tb['off']; hi=lo+len(tb['content'])
                                t[f'{lab}:'+('correct' if lo-2<=pos<=hi else 'WRONG')]+=1
    return t

for repo,glob in [('corpora/rust-book','src/*.md'),('corpora/obsidian-help','en/*.md')]:
    for gap in (5,25):
        t=run(repo,glob,gap); n=t['N']
        if n<40: continue
        print(f"\n### span anchoring, {os.path.basename(repo)} gap={gap}  spans={n}")
        print(f"{'':<10}{'correct':>10}{'loud refusal':>15}{'SILENT-WRONG':>15}")
        for lab in ('1stage','2stage'):
            print(f"{lab:<10}{100*t[lab+':correct']/n:9.1f}%{100*t[lab+':loud']/n:14.1f}%{100*t[lab+':WRONG']/n:14.2f}%  (n={t[lab+':WRONG']})")

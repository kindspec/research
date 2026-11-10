#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""What rowspec#284's key-order rule costs on the D0 replay corpus.

Counts the commits in which a row present in the commit and a parent changes
position relative to the other rows present in both, identified by the key
corpora.json names. A merge is reported both ways: reordered against every
parent, and against at least one.

    python3 reorder.py <dir holding iptv_full, cc_full and iso_full>

The first N commits of each history are read, N being the count D0 replayed.
Output of the run the issue quotes is in reorder-results.txt.
"""
import bisect, json, sys, csv
csv.field_size_limit(10**9)
sys.path.insert(0, "/home/cam/repos_kindspec/research/experiments/D0-dogfood")
from harness import Git, read_csv, natkeys
from rowspec.table import Malformed
C = sys.argv[1]
CORP = {
 "iptv-channels":  (f"{C}/iptv_full", "data/channels.csv", "id", 7008),
 "iptv-blocklist": (f"{C}/iptv_full", "data/blocklist.csv", "channel", 339),
 "country-codes":  (f"{C}/cc_full", "data/country-codes.csv", "ISO3166-1-Alpha-3", 74),
 "iso-3166":       (f"{C}/iso_full", "all/all.csv", "alpha-3", 25),
}
def moved(a, b):
    """rows that must move: common minus longest increasing subsequence."""
    pos = {k:i for i,k in enumerate(a)}
    tails=[]
    seq=[pos[k] for k in b if k in pos]
    for x in seq:
        i=bisect.bisect_left(tails,x)
        if i==len(tails): tails.append(x)
        else: tails[i]=x
    return len(seq)-len(tails), len(seq)
tot=hit=hit_all=0; out=[]
for name,(repo,path,nk,n) in CORP.items():
    g=Git(repo)
    revs=[x for x in g.run("rev-list","--full-history","--topo-order","--reverse","HEAD","--",path).split() if x][:n]
    assert len(revs)==n,(name,len(revs))
    pm={}
    for l in g.run("rev-list","--parents","HEAD").splitlines():
        p=l.split(); pm[p[0]]=p[1:]
    inset=set(revs)
    def nearest(c):
        while c is not None and c not in inset:
            ps=pm.get(c); c=ps[0] if ps else None
        return c
    cache={}; keys={}
    excl=0
    def load(r):
        if r in keys: return keys[r]
        sha=g.blob_sha(r,path)
        if sha in cache: keys[r]=cache[sha]; return keys[r]
        k=None
        if sha:
            try:
                h,rows,_=read_csv(g.blob(sha)); k=natkeys(h,rows,nk)
            except (Malformed,csv.Error): k=None
        cache[sha]=k; keys[r]=k; return k
    h=ha=0; ex=[]; big=0
    for r in revs:
        ps=[]
        for p in pm.get(r,[]):
            a=nearest(p)
            if a is not None and a not in ps: ps.append(a)
        k=load(r)
        if k is None: excl+=1; continue
        res=[]
        for p in ps:
            pk=load(p)
            if pk is None: continue
            s=set(k)&set(pk)
            ca=[x for x in pk if x in s]; cb=[x for x in k if x in s]
            if ca!=cb: res.append(moved(ca,cb))
            else: res.append(None)
        if res and any(x is not None for x in res):
            h+=1
            if all(x is not None for x in res): ha+=1
            m=max((x for x in res if x),key=lambda t:t[0])
            ex.append((r[:8],m[0],m[1]))
            if m[0]>=0.5*m[1]: big+=1
    tipk=load(revs[-1])
    srt=None if tipk is None else tipk==sorted(tipk)
    print(f"{name}: commits={n} excluded_unreadable={excl} reordered_any_parent={h} reordered_all_parents={ha} over_half_moved={big} tip_in_key_order={srt}",flush=True)
    print("  largest:",sorted(ex,key=lambda t:-t[1])[:6],"  median_moved:",(sorted(t[1] for t in ex)[len(ex)//2] if ex else 0),flush=True)
    tot+=n; hit+=h; hit_all+=ha
print(f"POOLED commits={tot} any_parent={hit} ({100*hit/tot:.2f}%) all_parents={hit_all} ({100*hit_all/tot:.2f}%)")

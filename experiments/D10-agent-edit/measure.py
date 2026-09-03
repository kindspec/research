import os,collections
def stats(path):
    lines=open(path).read().splitlines()
    c=collections.Counter(l.strip() for l in lines if l.strip())
    nonblank=[l for l in lines if l.strip()]
    uniq=sum(1 for l in nonblank if c[l.strip()]==1)
    dup_lines=sorted([l for l,n in c.items() if n>1], key=lambda s:-c[s])
    return len(nonblank), uniq, round(100*uniq/len(nonblank),1), len(open(path).read()), dup_lines[:4]
print(f"{'file':16s} {'lines':>5} {'uniq':>5} {'uniq%':>6} {'bytes':>6}  sample duplicated lines")
for f in sorted(os.listdir('.')):
    if f.startswith(('a_','b_','c_','d_')):
        n,u,p,b,d=stats(f); print(f"{f:16s} {n:5d} {u:5d} {p:6.1f} {b:6d}  {d}")

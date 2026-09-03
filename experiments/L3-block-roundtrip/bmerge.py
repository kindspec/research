import sys; sys.path.insert(0,'.')
from blocks import parse, render
def seq_merge(base, ours, theirs):
    res=[n for n in ours if not (n in base and n not in theirs)]
    for i,n in enumerate(theirs):
        if n in res or n in base: continue
        a=theirs[i-1] if i else None
        res.insert(res.index(a)+1 if a in res else len(res), n)
    return res
def m3(b,o,t):
    B,O,T=parse(b),parse(o),parse(t)
    db,do,dt=dict(B),dict(O),dict(T)
    names=seq_merge([n for n,_ in B],[n for n,_ in O],[n for n,_ in T])
    return ''.join((do.get(n) or dt.get(n) or db.get(n)) for n in names)
if __name__=='__main__':
    b,o,t=(open(p).read() for p in sys.argv[1:4]); sys.stdout.write(m3(b,o,t))

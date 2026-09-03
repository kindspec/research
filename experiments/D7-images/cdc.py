"""Content-defined chunking (Gear/FastCDC-style rolling hash) dedup measurement."""
import sys, os, hashlib, random
random.seed(0)
GEAR=[random.getrandbits(32) for _ in range(256)]
MIN, AVG, MAX = 2048, 8192, 65536
MASK = AVG-1
def chunks(buf):
    n=len(buf); i=0
    while i<n:
        end=min(i+MAX,n); h=0; j=i+MIN
        if j>=end:
            yield buf[i:end]; i=end; continue
        while j<end:
            h=((h<<1)+GEAR[buf[j]]) & 0xFFFFFFFF
            if not (h & MASK): break
            j+=1
        yield buf[i:j+1]; i=j+1
d,ext,single = sys.argv[1], sys.argv[2], int(sys.argv[3])
store=set(); stored=0; total=0
fixed=set(); fstored=0
for f in sorted(os.listdir(d)):
    if not f.endswith(ext): continue
    buf=open(os.path.join(d,f),'rb').read(); total+=len(buf)
    for c in chunks(buf):
        k=hashlib.sha256(c).digest()
        if k not in store: store.add(k); stored+=len(c)
    for off in range(0,len(buf),AVG):
        c=buf[off:off+AVG]; k=hashlib.sha256(c).digest()
        if k not in fixed: fixed.add(k); fstored+=len(c)
print("  CDC (gear, avg 8K)    = %d  (%.2fx)  unique_chunks=%d" % (stored, stored/single, len(store)))
print("  fixed-size 8K blocks  = %d  (%.2fx)" % (fstored, fstored/single))

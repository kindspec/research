"""Is the CELL a sane unit for a memoising engine, or does bookkeeping exceed compute?"""
import hashlib, time
N = 200_000
qty   = [i % 97 for i in range(N)]
price = [1.5 + (i % 13) for i in range(N)]

t0=time.perf_counter()
tot = [q*p for q,p in zip(qty,price)]                       # raw compute, whole column
t_col = time.perf_counter()-t0

t0=time.perf_counter()
cache={}
for q,p in zip(qty,price):                                   # per-CELL memo bookkeeping
    k = hashlib.sha256(f'mul|{q}|{p}'.encode()).digest()[:8]
    if k not in cache: cache[k] = q*p
t_cell = time.perf_counter()-t0

t0=time.perf_counter()                                       # per-COLUMN memo
k = hashlib.sha256(repr(qty).encode()+repr(price).encode()).digest()
_ = [q*p for q,p in zip(qty,price)]
t_colmemo = time.perf_counter()-t0

print(f"cells                       : {N:,}")
print(f"raw column compute          : {t_col*1000:8.1f} ms")
print(f"per-CELL memo bookkeeping   : {t_cell*1000:8.1f} ms   ({t_cell/t_col:5.1f}x the compute it protects)")
print(f"per-COLUMN memo bookkeeping : {t_colmemo*1000:8.1f} ms   ({t_colmemo/t_col:5.1f}x)")
print(f"distinct cached cell values : {len(cache):,}  of {N:,} cells  -> the memo table is mostly redundant")

#!/usr/bin/env python3
"""E1a: .tbl parse/evaluate time, memory, and size tax vs CSV, at scale."""
import sys, os, time, json, statistics, tracemalloc, gzip
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen, tbl

SIZES = [int(x) for x in (sys.argv[1:] or ['1000', '10000', '100000', '1000000'])]
REPS = 5


def med(f, reps):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); f(); ts.append(time.perf_counter() - t0)
    return statistics.median(ts), min(ts)


out = []
for n in SIZES:
    reps = REPS if n <= 100000 else 3
    t0 = time.perf_counter(); text = gen.tbl_text(n); tgen = time.perf_counter() - t0
    csv = gen.csv_text(n)
    csv_noid = gen.csv_text(n, with_id=False)
    unpad = gen.tbl_text(n, pad=False)
    b_tbl, b_csv, b_noid, b_unpad = len(text.encode()), len(csv.encode()), len(csv_noid.encode()), len(unpad.encode())
    p_med, p_min = med(lambda: tbl.parse(text), reps)
    e_med, e_min = med(lambda: tbl.evaluate(text), reps)
    tracemalloc.start()
    cols, formulas, rows, aggs = tbl.parse(text)
    peak_parse = tracemalloc.get_traced_memory()[1]
    del cols, formulas, rows, aggs
    tracemalloc.reset_peak()
    r, a = tbl.evaluate(text)
    peak_eval = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    del r, a
    rec = dict(n=n, gen_s=tgen, parse_med_s=p_med, parse_min_s=p_min,
               eval_med_s=e_med, eval_min_s=e_min,
               peak_parse_mb=peak_parse / 2**20, peak_eval_mb=peak_eval / 2**20,
               tbl_bytes=b_tbl, csv_bytes=b_csv, csv_noid_bytes=b_noid, unpad_bytes=b_unpad,
               tbl_gz=len(gzip.compress(text.encode(), 6)), csv_gz=len(gzip.compress(csv.encode(), 6)),
               pad_tax_pct=100 * (b_tbl - b_unpad) / b_unpad,
               id_tax_pct=100 * (b_csv - b_noid) / b_noid,
               vs_csv_pct=100 * (b_tbl - b_csv) / b_csv,
               vs_csv_noid_pct=100 * (b_tbl - b_noid) / b_noid,
               bytes_per_row=b_tbl / n)
    out.append(rec)
    print(json.dumps(rec), flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out/e1_table.json'), 'w'), indent=1)

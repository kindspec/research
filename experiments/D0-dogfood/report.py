"""Pool the ledgers and print each pre-registered threshold with its number."""
import json, os, statistics, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = ["iptv-channels", "iptv-blocklist", "country-codes", "iso-3166"]


def load(n):
    p = os.path.join(HERE, f"ledger-{n}.jsonl")
    return [json.loads(x) for x in open(p)] if os.path.exists(p) else []


def stats(L):
    n = len(L)
    ok = [r for r in L if r.get("outcome") == "ok"]
    excl = [r for r in L if r.get("outcome") == "excluded"]
    rf = [r for r in L if r.get("outcome") == "refused"]
    mdref = [r for r in ok if r.get("mdtbl") == "refused"] + rf
    mdref_faith = [r for r in ok if r.get("mdtbl") == "refused" or r.get("n_illegal_spec")] + rf
    mdref_impl = [r for r in ok if r.get("mdtbl") == "refused" or r.get("n_illegal_reference")] + rf
    csvref = [r for r in ok if r.get("csvmode") == "refused"] + rf
    wp = sum(r.get("witness_pairs", 0) for r in ok)
    wk = sum(r.get("witness_kept_id", 0) for r in ok)
    dl = [(r["md_diff_lines"], r["csv_diff_lines"]) for r in ok if r.get("csv_diff_lines")]
    db = [(r["md_diff_bytes"], r["csv_diff_bytes"]) for r in ok if r.get("csv_diff_bytes")]
    return dict(
        n=n, ok=len(ok), excluded=len(excl),
        md_refused=len(mdref), md_refused_faithful=len(mdref_faith),
        md_refused_reference_impl=len(mdref_impl), csv_refused=len(csvref),
        witness_pairs=wp, witness_kept=wk,
        id_on_diff_row=sum(r.get("id_on_different_row", 0) for r in ok),
        carried_by_key=sum(r.get("carried_by_key", 0) for r in ok),
        reminted=sum(r.get("reminted", 0) for r in ok),
        line_ratios=[m / c for m, c in dl], byte_ratios=[m / c for m, c in db],
        md_lines=sum(m for m, c in dl), csv_lines=sum(c for m, c in dl),
        md_bytes=sum(m for m, c in db), csv_bytes=sum(c for m, c in db),
        nfc=sum(r.get("canon_nfc_cells", 0) for r in ok),
        trim=sum(r.get("canon_trim_cells", 0) for r in ok),
        cells=sum(r.get("rows", 0) * r.get("cols", 0) for r in ok),
        crlf=sum(1 for r in ok if r.get("canon_crlf")),
        defects=Counter(
            {k: v for r in ok for k, v in (r.get("defects") or {}).items()}
        ),
        pipe_commits=sum(1 for r in ok if (r.get("defects") or {}).get("pipe-in-value")),
        ragged_commits=sum(1 for r in ok if (r.get("defects") or {}).get("field-count")),
    )


rows = {}
for nm in NAMES:
    L = load(nm)
    if L:
        rows[nm] = stats(L)

tot = Counter()
lr, br = [], []
for nm, s in rows.items():
    for k in ("n", "ok", "excluded", "md_refused", "md_refused_faithful",
              "md_refused_reference_impl", "csv_refused", "witness_pairs", "witness_kept",
              "id_on_diff_row", "carried_by_key", "reminted", "md_lines", "csv_lines",
              "md_bytes", "csv_bytes", "nfc", "trim", "cells", "crlf", "pipe_commits",
              "ragged_commits"):
        tot[k] += s[k]
    lr += s["line_ratios"]
    br += s["byte_ratios"]

print("=" * 78)
for nm, s in rows.items():
    print(f"{nm:16s} commits={s['n']:6d} excl={s['excluded']:3d} "
          f"mdtbl_refused={s['md_refused']:5d} ({s['md_refused']/s['n']:6.1%})  "
          f"faithful={s['md_refused_faithful']/s['n']:6.1%}  refimpl={s['md_refused_reference_impl']/s['n']:6.1%}  "
          f"csvmode={s['csv_refused']/s['n']:6.1%}")
    print(f"{'':16s} carriage={s['witness_kept']}/{s['witness_pairs']}="
          f"{(s['witness_kept']/s['witness_pairs'] if s['witness_pairs'] else 0):.4%} "
          f"id_on_diff_row={s['id_on_diff_row']} reminted={s['reminted']}")
    print(f"{'':16s} diff median line={statistics.median(s['line_ratios']) if s['line_ratios'] else None} "
          f"byte={statistics.median(s['byte_ratios']) if s['byte_ratios'] else None} "
          f"aggregate line={s['md_lines']}/{s['csv_lines']} byte={s['md_bytes']}/{s['csv_bytes']}")
    print(f"{'':16s} canon nfc={s['nfc']} trim={s['trim']} of {s['cells']} cells; "
          f"crlf commits={s['crlf']}; defects={dict(s['defects'])}")
print("=" * 78)
print("POOLED")
print(f"  commits {tot['n']}, excluded {tot['excluded']}")
print(f"  T1 refusal rate (.mdtbl, mangled col names) : {tot['md_refused']}/{tot['n']} = "
      f"{tot['md_refused']/tot['n']:.2%}   threshold >2% FAILS")
print(f"  T1 refusal rate (.mdtbl, names verbatim/SPEC): {tot['md_refused_faithful']}/{tot['n']} = "
      f"{tot['md_refused_faithful']/tot['n']:.2%}")
print(f"  T1 refusal rate (.mdtbl, reference impl idents): {tot['md_refused_reference_impl']}/{tot['n']} = "
      f"{tot['md_refused_reference_impl']/tot['n']:.2%}")
print(f"  T1 refusal rate (CSV mode, zero migration)  : {tot['csv_refused']}/{tot['n']} = "
      f"{tot['csv_refused']/tot['n']:.2%}")
print(f"  T2 row-id carriage : {tot['witness_kept']}/{tot['witness_pairs']} = "
      f"{tot['witness_kept']/tot['witness_pairs']:.3%}   threshold <95% FAILS")
print(f"     id landed on a substantially different row: {tot['id_on_diff_row']}")
print(f"  T3 diff size ratio (per-commit median): lines={statistics.median(lr):.4f} "
      f"bytes={statistics.median(br):.4f}   threshold >1.5x FAILS")
print(f"     p90 lines={sorted(lr)[int(len(lr)*.9)]:.3f} bytes={sorted(br)[int(len(br)*.9)]:.3f}; "
      f"aggregate lines={tot['md_lines']/tot['csv_lines']:.3f} bytes={tot['md_bytes']/tot['csv_bytes']:.3f}")
print(f"  T5 canon churn: NFC {tot['nfc']} cells, trim {tot['trim']} cells of {tot['cells']} "
      f"({(tot['nfc']+tot['trim'])/tot['cells']:.6%}); CRLF commits {tot['crlf']}/{tot['n']}")
print(f"     commits containing a value with '|': {tot['pipe_commits']}; ragged: {tot['ragged_commits']}")

mp = os.path.join(HERE, "merge-results.jsonl")
if os.path.exists(mp):
    M = [json.loads(x) for x in open(mp)]
    ok = [r for r in M if r.get("outcome") == "ok"]
    print(f"  T4 merges: {len(M)} replayed, {len(M)-len(ok)} excluded")
    c = Counter((r["mdtbl_merge"], r["csv_merge"]) for r in ok)
    print(f"     (.mdtbl, csv) outcomes: {dict(c)}")
    print(f"     oracle: {Counter(r['oracle'] for r in ok)}")
    print(f"     mdtbl silent-wrong: {sum(1 for r in ok if r.get('mdtbl_silent_wrong'))}")
    print(f"     csv   silent-wrong: {sum(1 for r in ok if r.get('csv_silent_wrong'))}")
    print(f"     mdtbl clean & invalid output: {sum(1 for r in ok if r.get('mdtbl_merge')=='clean' and r.get('mdtbl_valid') is False)}")
    print(f"     inputs already invalid: {sum(1 for r in ok if not all(r.get('inputs_valid',[True])))}")
    print(f"     line_faithful guard true: {sum(1 for r in ok if r.get('line_faithful'))}/{len(ok)}")
    over = [r for r in ok if r['mdtbl_merge']=='conflict' and r['csv_merge']=='clean']
    under = [r for r in ok if r['mdtbl_merge']=='clean' and r['csv_merge']=='conflict']
    print(f"     mdtbl conflicts where csv was clean: {len(over)}; reverse: {len(under)}")

print("-" * 78)
print("LARGEST REAL CHANGES (where locality matters most)")
allrec = []
for nm in NAMES:
    for r in load(nm):
        if r.get("csv_diff_lines"):
            allrec.append((r["csv_diff_lines"], r["md_diff_lines"], r["csv_diff_bytes"],
                           r["md_diff_bytes"], nm, r["rev"][:8], r.get("witness_added"),
                           r.get("witness_deleted"), r.get("rows")))
allrec.sort(reverse=True)
print(f"{'corpus':16s} {'rev':9s} {'csv_l':>7s} {'md_l':>7s} {'ratio':>6s} {'+row':>5s} {'-row':>5s} {'rows':>6s}")
for c, m, cb, mb, nm, rev, add, dele, nrows in allrec[:15]:
    print(f"{nm:16s} {rev:9s} {c:7d} {m:7d} {m/c:6.3f} {str(add):>5s} {str(dele):>5s} {str(nrows):>6s}")
resorts = [x for x in allrec if x[6] == 0 and x[7] == 0 and x[0] > 200]
print(f"pure re-sorts / mass rewrites with no row added or deleted, csv diff >200 lines: {len(resorts)}")
for c, m, cb, mb, nm, rev, a, d, nr in resorts[:6]:
    print(f"   {nm} {rev} csv {c} lines -> mdtbl {m} lines (x{m/c:.3f})")

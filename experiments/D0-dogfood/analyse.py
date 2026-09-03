import json, os, statistics, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    return [json.loads(l) for l in open(os.path.join(HERE, f"ledger-{name}.jsonl"))]


def summarise(name):
    L = load(name)
    n = len(L)
    ok = [r for r in L if r.get("outcome") == "ok"]
    excl = [r for r in L if r.get("outcome") == "excluded"]
    readfail = [r for r in L if r.get("outcome") == "refused"]
    md_ref = [r for r in ok if r.get("mdtbl") == "refused"] + readfail
    csv_ref = [r for r in ok if r.get("csvmode") == "refused"] + readfail
    faith_ref = [r for r in ok if r.get("mdtbl") == "refused" or r.get("n_illegal_spec")] + readfail
    ref_impl = [r for r in ok if r.get("mdtbl") == "refused" or r.get("n_illegal_reference")] + readfail

    wp = sum(r.get("witness_pairs", 0) for r in ok)
    wk = sum(r.get("witness_kept_id", 0) for r in ok)
    wrong = sum(r.get("id_on_different_row", 0) for r in ok)
    carried = sum(r.get("carried_by_key", 0) for r in ok)
    rem = sum(r.get("reminted", 0) for r in ok)

    dl = [(r["md_diff_lines"], r["csv_diff_lines"]) for r in ok
          if r.get("csv_diff_lines")]
    db = [(r["md_diff_bytes"], r["csv_diff_bytes"]) for r in ok
          if r.get("csv_diff_bytes")]
    rl = sorted(m / c for m, c in dl) if dl else []
    rb = sorted(m / c for m, c in db) if db else []

    nfc = sum(r.get("canon_nfc_cells", 0) for r in ok)
    trim = sum(r.get("canon_trim_cells", 0) for r in ok)
    crlf = sum(1 for r in ok if r.get("canon_crlf"))
    cells = sum(r.get("rows", 0) * r.get("cols", 0) for r in ok)

    reasons = Counter()
    for r in md_ref:
        reasons[(r.get("mdtbl_reason") or r.get("reason") or "?")[:60]] += 1
    creasons = Counter()
    for r in csv_ref:
        for x in (r.get("csvmode_reason") or [r.get("reason", "?")]):
            creasons[str(x)[:70]] += 1
    defects = Counter()
    for r in ok:
        for k, v in (r.get("defects") or {}).items():
            defects[k] += v

    out = {
        "corpus": name, "commits": n, "excluded": len(excl), "read_refused": len(readfail),
        "rows_last": ok[-1]["rows"] if ok else None,
        "cols_first_last": [ok[0]["cols"], ok[-1]["cols"]] if ok else None,
        "authors": None,
        "mdtbl_refused": len(md_ref), "mdtbl_refusal_rate": len(md_ref) / n,
        "mdtbl_refused_faithful_spec": len(faith_ref), "rate_faithful_spec": len(faith_ref) / n,
        "mdtbl_refused_reference_impl": len(ref_impl), "rate_reference_impl": len(ref_impl) / n,
        "csvmode_refused": len(csv_ref), "csvmode_refusal_rate": len(csv_ref) / n,
        "witness_pairs": wp, "witness_kept_id": wk,
        "carriage": wk / wp if wp else None,
        "id_on_different_row": wrong,
        "carried_by_key": carried, "reminted": rem,
        "diff_pairs": len(dl),
        "median_line_ratio": statistics.median(rl) if rl else None,
        "median_byte_ratio": statistics.median(rb) if rb else None,
        "p90_line_ratio": rl[int(len(rl) * 0.9)] if rl else None,
        "p90_byte_ratio": rb[int(len(rb) * 0.9)] if rb else None,
        "mdtbl_lines_total": sum(m for m, c in dl), "csv_lines_total": sum(c for m, c in dl),
        "canon_nfc_cells": nfc, "canon_trim_cells": trim, "cells_seen": cells,
        "commits_crlf": crlf,
        "md_refusal_reasons": reasons.most_common(8),
        "csv_refusal_reasons": creasons.most_common(8),
        "defects": dict(defects),
    }
    return out, L


if __name__ == "__main__":
    for nm in sys.argv[1:]:
        s, _ = summarise(nm)
        print(json.dumps(s, indent=1, default=str))

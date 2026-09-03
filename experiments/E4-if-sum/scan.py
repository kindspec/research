#!/usr/bin/env python3
"""E4 -- what shape do real IF and SUM formulas actually have?

E1 measured that 21,165 corpus cells translate to .mdtbl's surface but sit
outside SPEC 4.2, and that IF (12,643) and SUM (5,552) are 86% of them. That
says WHICH functions to add. It does not say what grammar they need -- whether
IF wants comparison operators only or AND/OR/ISBLANK too, whether its branches
return numbers or strings, and whether SUM is a horizontal same-row range (a
list of columns) or a vertical one (an aggregate, which .mdtbl already has by
another name).

This scans the raw <f> text and answers exactly that. Shared formulas are
expanded so a fill-down column counts once per cell, matching E1's weighting.

No third-party packages. OOXML via stdlib zipfile + ElementTree.
"""
import sys, os, re, glob, json, zipfile, collections
import xml.etree.ElementTree as ET

W3 = '/home/cam/repos_kindspec/working-git-backed-gws/experiments/W3-interop/tools'
sys.path.insert(0, W3)
from a1trans import NS, col2n, n2col, read_workbook, mask_strings, unmask

CNT = collections.Counter()
SAMP = collections.defaultdict(list)


def note(k, n=1):
    CNT[k] += n


def samp(k, v, cap=12):
    if len(SAMP[k]) < cap and v not in SAMP[k]:
        SAMP[k].append(v)


# ---- shared-formula expansion (same rule as E1) ---------------------------
A1 = re.compile(r"(\$?)([A-Z]{1,3})(\$?)([0-9]+)")


def shift(f, dr, dc):
    def one(m):
        cabs, cs, rabs, rs = m.group(1), m.group(2), m.group(3), m.group(4)
        c = col2n(cs) + (0 if cabs else dc)
        r = int(rs) + (0 if rabs else dr)
        if c < 1 or r < 1:
            return "#REF!"
        return f"{cabs}{n2col(c)}{rabs}{r}"
    body, lits = mask_strings(f)
    return unmask(A1.sub(one, body), lits)


def cell_rc(ref):
    m = A1.match(ref)
    return int(m.group(4)), col2n(m.group(2))


def formulas(z, target):
    """Yield (cellref, formula) for every formula cell, shared ones expanded."""
    root = ET.fromstring(z.read(target))
    masters = {}
    out = []
    for c in root.iter(f'{{{NS["m"]}}}c'):
        fe = c.find(f'{{{NS["m"]}}}f')
        if fe is None:
            continue
        ref = c.get("r")
        t, si = fe.get("t"), fe.get("si")
        txt = fe.text or ""
        if t == "array":
            note("skip.array")
            continue
        if t == "shared":
            if txt:
                masters[si] = (ref, txt)
                out.append((ref, txt))
            else:
                out.append((ref, si))          # resolve in a second pass
            continue
        out.append((ref, txt))
    res = []
    for ref, v in out:
        if v in masters:                        # v is a shared index
            mref, mtxt = masters[v]
            r0, c0 = cell_rc(mref)
            r1, c1 = cell_rc(ref)
            res.append((ref, shift(mtxt, r1 - r0, c1 - c0)))
            note("shared.expanded")
        else:
            res.append((ref, v))
    return res


# ---- argument splitting at paren depth 0 ----------------------------------
def split_args(s):
    out, depth, cur, i = [], 0, "", 0
    while i < len(s):
        ch = s[i]
        if ch == '"':
            j = i + 1
            while j < len(s) and s[j] != '"':
                j += 1
            cur += s[i:j + 1]
            i = j + 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
            i += 1
            continue
        cur += ch
        i += 1
    out.append(cur)
    return [a.strip() for a in out]


def calls(f, name):
    """Yield the argument string of every top-level `name(...)` in f."""
    for m in re.finditer(r"(?<![A-Z0-9_.])" + name + r"\s*\(", f, re.I):
        i = m.end()
        depth, start = 1, i
        while i < len(f) and depth:
            if f[i] == '"':
                i += 1
                while i < len(f) and f[i] != '"':
                    i += 1
            elif f[i] == "(":
                depth += 1
            elif f[i] == ")":
                depth -= 1
            i += 1
        yield f[start:i - 1]


RANGE = re.compile(r"^(?:'[^']+'|[A-Za-z0-9_]+)?!?\$?([A-Z]{1,3})\$?([0-9]+):"
                   r"(?:'[^']+'|[A-Za-z0-9_]+)?!?\$?([A-Z]{1,3})\$?([0-9]+)$")
SINGLE = re.compile(r"^(?:'[^']+'|[A-Za-z0-9_]+)?!?\$?[A-Z]{1,3}\$?[0-9]+$")
NUMLIT = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")
STRLIT = re.compile(r'^".*"$')
CMPOP = re.compile(r"(<=|>=|<>|=|<|>)")


def classify_sum_arg(a, row):
    m = RANGE.match(a)
    if m:
        c1, r1, c2, r2 = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
        if r1 == r2:
            return "row-range-same-row" if r1 == row else "row-range-other-row"
        if c1 == c2:
            return "col-range"
        return "rect-range"
    if SINGLE.match(a):
        return "single-ref"
    if NUMLIT.match(a):
        return "literal"
    return "expression"


def cond_shape(c):
    cu = c.upper()
    for fn in ("AND", "OR", "NOT", "ISBLANK", "ISERROR", "ISNA", "ISNUMBER",
               "ISTEXT", "COUNTIF", "SUMIF", "IF"):
        if re.search(r"(?<![A-Z0-9_])" + fn + r"\s*\(", cu):
            return "calls:" + fn
    parts = CMPOP.split(c)
    if len(parts) >= 3:
        op = [p for p in CMPOP.findall(c)]
        if len(op) > 1:
            return "multi-comparison"
        rhs = parts[2].strip()
        if NUMLIT.match(rhs):
            return "cmp-vs-number"
        if STRLIT.match(rhs):
            return "cmp-vs-string"
        if rhs == "":
            return "cmp-vs-empty"
        if SINGLE.match(rhs):
            return "cmp-vs-ref"
        return "cmp-vs-expression"
    return "bare"


def branch_shape(b):
    b = b.strip()
    if b == "":
        return "omitted"
    if STRLIT.match(b):
        return '"" (empty string)' if b == '""' else "string"
    if NUMLIT.match(b):
        return "number"
    if SINGLE.match(b):
        return "ref"
    if re.search(r"(?<![A-Z0-9_])IF\s*\(", b.upper()):
        return "nested-IF"
    if re.search(r"[A-Z]+\s*\(", b.upper()):
        return "other-call"
    return "arithmetic"


def process(path):
    try:
        z, sst, sheets, wb = read_workbook(path)
    except Exception:
        note("wb.bad")
        return
    note("wb.ok")
    for name, tgt in sheets:
        try:
            fs = formulas(z, tgt)
        except Exception:
            continue
        for ref, f in fs:
            if not f:
                continue
            note("formula-cells")
            row = cell_rc(ref)[0]
            fu = f.upper()
            if re.search(r"(?<![A-Z0-9_])SUM\s*\(", fu):
                note("has.SUM")
                for argstr in calls(f, "SUM"):
                    args = split_args(argstr)
                    note("SUM.calls")
                    note(f"SUM.arity.{min(len(args), 4)}")
                    for a in args:
                        k = classify_sum_arg(a, row)
                        note("SUM.arg." + k)
                        samp("SUM.arg." + k, a)
                    if len(args) == 1:
                        note("SUM.single-arg." + classify_sum_arg(args[0], row))
            if re.search(r"(?<![A-Z0-9_])IF\s*\(", fu):
                note("has.IF")
                for argstr in calls(f, "IF"):
                    args = split_args(argstr)
                    note("IF.calls")
                    note(f"IF.arity.{min(len(args), 4)}")
                    if len(args) >= 1:
                        s = cond_shape(args[0])
                        note("IF.cond." + s)
                        samp("IF.cond." + s, args[0])
                    for i, b in enumerate(args[1:3]):
                        s = branch_shape(b)
                        note(f"IF.branch{i + 1}." + s)
                        samp(f"IF.branch{i + 1}." + s, b)
                    if len(args) >= 3:
                        pair = tuple(sorted({branch_shape(args[1]),
                                             branch_shape(args[2])}))
                        note("IF.branchpair." + "|".join(pair))


def main(pats, limit=None, out="out/e4.json"):
    files = []
    for p in pats:
        files += sorted(glob.glob(p, recursive=True))
    if limit:
        files = files[:int(limit)]
    for i, p in enumerate(files):
        process(p)
        if i % 500 == 0:
            print(f"  {i}/{len(files)}", file=sys.stderr, flush=True)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    json.dump({"counts": dict(CNT), "samples": {k: v for k, v in SAMP.items()}},
              open(out, "w"), indent=1)
    for k, v in sorted(CNT.items(), key=lambda kv: -kv[1]):
        print(f"{v:9d}  {k}")


if __name__ == "__main__":
    main(sys.argv[1:-1] or ["**/*.xlsx"], None, sys.argv[-1])

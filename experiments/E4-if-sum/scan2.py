#!/usr/bin/env python3
"""What argument shapes do ROUND/ROUNDDOWN/INT/MIN/CEILING/AVERAGE actually take?

E5 leaves 8,417 corpus cells outside §4.2. Function-name frequency says which
names to consider; it does not say what grammar they need. E4 already made that
mistake once -- `SUM` looked like 5,552 cells of missing grammar and was 99.1%
a translator gap -- so measure the arguments before deciding anything.
"""
import sys, os, re, glob, json, collections
sys.path.insert(0, '/home/cam/repos_kindspec/working-git-backed-gws/experiments/W3-interop/tools')
from a1trans import NS, read_workbook
import xml.etree.ElementTree as ET

C = collections.Counter(); S = collections.defaultdict(set)
FNS = ("ROUND", "ROUNDDOWN", "ROUNDUP", "INT", "MIN", "MAX", "CEILING", "FLOOR", "AVERAGE")
NUM = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")
REF = re.compile(r"^\$?[A-Z]{1,3}\$?[0-9]+$")


def split_args(s):
    out, d, cur, i = [], 0, "", 0
    while i < len(s):
        ch = s[i]
        if ch == '"':
            j = i + 1
            while j < len(s) and s[j] != '"': j += 1
            cur += s[i:j+1]; i = j + 1; continue
        if ch == "(": d += 1
        elif ch == ")": d -= 1
        if ch == "," and d == 0: out.append(cur); cur = ""; i += 1; continue
        cur += ch; i += 1
    out.append(cur)
    return [a.strip() for a in out]


def calls(f, name):
    for m in re.finditer(r"(?<![A-Za-z0-9_.])" + name + r"\s*\(", f, re.I):
        i, d, start = m.end(), 1, m.end()
        while i < len(f) and d:
            if f[i] == '"':
                i += 1
                while i < len(f) and f[i] != '"': i += 1
            elif f[i] == "(": d += 1
            elif f[i] == ")": d -= 1
            i += 1
        yield f[start:i-1]


def kind(a):
    if NUM.match(a): return "literal"
    if REF.match(a): return "cellref"
    if re.search(r"[A-Z]+\s*\(", a.upper()): return "call"
    if re.search(r"[-+*/]", a): return "arithmetic"
    return "other"


for p in sorted(glob.glob(sys.argv[1], recursive=True))[: int(sys.argv[2]) if len(sys.argv) > 2 else None]:
    try: z, sst, sheets, wb = read_workbook(p)
    except Exception: continue
    for name, tgt in sheets:
        try: root = ET.fromstring(z.read(tgt))
        except Exception: continue
        for c in root.iter(f'{{{NS["m"]}}}c'):
            fe = c.find(f'{{{NS["m"]}}}f')
            if fe is None or not (fe.text or ""): continue
            f = fe.text
            for fn in FNS:
                if not re.search(r"(?<![A-Za-z0-9_.])" + fn + r"\s*\(", f, re.I): continue
                for argstr in calls(f, fn):
                    args = split_args(argstr)
                    C[f"{fn}.arity.{min(len(args),6)}"] += 1
                    C[f"{fn}.calls"] += 1
                    for i, a in enumerate(args[:2]):
                        C[f"{fn}.arg{i}.{kind(a)}"] += 1
                        if kind(a) == "literal" and i == 1:
                            S[f"{fn}.digits"].add(a)
for k, v in sorted(C.items(), key=lambda kv: (-kv[1], kv[0]))[:44]:
    print(f"{v:8d}  {k}")
print()
for k, v in sorted(S.items()):
    print(f"  {k}: {sorted(v)[:12]}")

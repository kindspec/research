"""
D11 experiment, revision 2.

Revision 1 contained a real bug, kept in tbl_v0_buggy.py as evidence:
the "unknown function" check was `re.match(r"^(\w+)\(", expr)` -- a PREFIX
check, not a recognizer. `sum(total) - median(qty)` starts with `sum(`, so
every policy including "strict" accepted it and then fell through to returning
the expression string. A spot check is not strictness. Strictness must be
total over the grammar.

Policies:
    P  permissive       skip any line you do not recognise
    S  strict-all       reject any line you do not recognise
    H  hybrid           reject unknown STRUCTURE + unknown PRAGMA,
                        ignore-and-preserve unknown ANNOTATION
    D  demand-driven    H, but an unknown construct is only fatal if it lies in
                        the derivation closure of a value actually requested.
                        Reads degrade to a partial view; WRITES are refused.
"""

import re
from decimal import Decimal

ROW = re.compile(r"^\s*\|(.*)\|\s*$")
BIND = re.compile(r"^\s*([A-Za-z_][\w-]*)\s*:=\s*(.+?)\s*$")
ANNOT = re.compile(r"^\s*%(\S*)\s*(.*)$")
PRAGMA = re.compile(r"^\s*!(\S*)\s*(.*)$")
SEP = re.compile(r"^\s*\|[-:| ]+\|\s*$")

KNOWN_FUNCS = {"sum", "count", "min", "max"}
KNOWN_PRAGMAS = set()
KNOWN_ANNOTS = set()

# total recognizer for the v1 expression language:
#   expr := term (('+'|'-') term)*
#   term := NUMBER | NAME | FUNC '(' NAME ')'
TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|(\w+)\s*\(\s*(\w+)\s*\)|(\w+)|([-+*/]))")


class Reject(Exception):
    pass


def recognize_expr(expr):
    """Fully tokenise. Return set of function names used. Raise on any residue."""
    used, pos = set(), 0
    while pos < len(expr):
        if expr[pos].isspace():
            pos += 1
            continue
        m = TOKEN.match(expr, pos)
        if not m or m.end() == pos:
            raise Reject(f"unrecognised at offset {pos} in {expr!r}")
        if m.group(2):
            used.add(m.group(2))
        pos = m.end()
    return used


def cells(line):
    return [c.strip() for c in ROW.match(line).group(1).split("|")]


def parse(text, policy):
    header, rows, binds, ignored, unknown = None, [], {}, [], {}
    for n, line in enumerate(text.splitlines(), 1):
        if SEP.match(line):
            continue
        if not line:
            continue                      # empty line: an explicit production
        if not line.strip():
            # whitespace-only but non-empty. NOT in the grammar.
            if policy == "P":
                ignored.append((n, line)); continue
            raise Reject(f"line {n}: whitespace-only line {line!r}")
        if ROW.match(line):
            c = cells(line)
            if header is None:
                header = c
            elif len(c) != len(header):
                if policy == "P":
                    ignored.append((n, line)); continue
                raise Reject(f"line {n}: row has {len(c)} cells, header has {len(header)}")
            else:
                rows.append(c)
            continue
        m = BIND.match(line)
        if m:
            name, expr = m.group(1), m.group(2)
            try:
                used = recognize_expr(expr)
            except Reject as e:
                if policy == "P":
                    ignored.append((n, line)); continue
                raise Reject(f"line {n}: {e}")
            bad = used - KNOWN_FUNCS
            if name in binds:
                if policy == "P":
                    binds[name] = expr; continue
                raise Reject(f"line {n}: duplicate binding {name}")
            if bad:
                if policy == "P":
                    ignored.append((n, line)); continue
                if policy == "D":
                    unknown[name] = f"line {n}: unknown function(s) {sorted(bad)}"
                    binds[name] = expr
                    continue
                raise Reject(f"line {n}: unknown function(s) {sorted(bad)}")
            binds[name] = expr
            continue
        m = ANNOT.match(line)
        if m:
            if not m.group(1):
                if policy == "P":
                    ignored.append((n, line)); continue
                raise Reject(f"line {n}: empty annotation key")
            if m.group(1) in KNOWN_ANNOTS:
                continue
            if policy == "S":
                raise Reject(f"line {n}: unknown annotation %{m.group(1)}")
            ignored.append((n, line))
            continue
        m = PRAGMA.match(line)
        if m:
            if m.group(1) in KNOWN_PRAGMAS:
                continue
            if policy == "P":
                ignored.append((n, line)); continue
            # S, H, D all reject: a pragma is declared evaluation-affecting.
            raise Reject(f"line {n}: unknown pragma !{m.group(1)}")
        if policy == "P":
            ignored.append((n, line)); continue
        raise Reject(f"line {n}: unrecognised line {line!r}")
    return header, rows, binds, ignored, unknown


def evaluate(header, rows, binds, unknown, want="grand"):
    if header is None:
        raise Reject("no header")
    names, formulas = [], {}
    for h in header:
        if "=" in h:
            nm, ex = h.split("=", 1)
            nm = nm.strip()
            recognize_expr(ex.strip())
            names.append(nm); formulas[nm] = ex.strip()
        else:
            names.append(h.strip())
    cols = {nm: [] for nm in names}
    for r in rows:
        env = {}
        for nm, v in zip(names, r):
            if nm in formulas:
                continue
            try:
                env[nm] = Decimal(v)
            except Exception:
                env[nm] = v
        for nm in names:
            if nm in formulas:
                env[nm] = eval(formulas[nm], {"__builtins__": {}}, env)  # harness only
            cols[nm].append(env[nm])
    out = {}
    for name, expr in binds.items():
        if name in unknown:
            if name == want:
                raise Reject(f"{want} depends on {unknown[name]}")
            out[name] = "<not understood>"
            continue
        toks = re.findall(r"(\w+)\s*\(\s*(\w+)\s*\)|(\d+(?:\.\d+)?)|(\w+)|([-+*/])", expr)
        # only v1 shapes reach here: NAME := FUNC(col) with optional +/- terms
        acc, op = Decimal(0), "+"
        for fn, arg, num, bare, sym in toks:
            if sym:
                op = sym; continue
            if fn:
                v = sum(cols[arg]) if fn == "sum" else Decimal(len(cols[arg]))
            elif num:
                v = Decimal(num)
            else:
                v = out.get(bare, Decimal(0))
            acc = acc + v if op == "+" else acc - v
        out[name] = acc
    return out


def run(text, policy, want="grand"):
    try:
        h, r, b, ig, unk = parse(text, policy)
        vals = evaluate(h, r, b, unk, want)
        return ("value", vals, [l for _, l in ig], unk)
    except Reject as e:
        return ("reject", str(e), [], {})
    except Exception as e:
        return ("crash", f"{type(e).__name__}: {e}", [], {})

"""
D11 experiment: three parser policies for a line-oriented `.tbl` format,
evaluated against a corpus of inputs that a v1 reader might meet over decades.

The format (v1):
    | id | item | qty | unit | total = qty * unit |     header, formulas inline
    | r_1 | widget | 10 | 12.00 | |                     rows
    grand := sum(total)                                  bindings
    %note anything                                       annotations (v1: comments)
    !strict-numbers                                      pragmas (evaluation-affecting)

Policies:
    P  permissive   skip any line you do not recognise            (Postel)
    S  strict       reject any line you do not recognise          (I7 as written)
    H  hybrid       reject unknown STRUCTURE and unknown PRAGMA,
                    ignore-and-preserve unknown ANNOTATION        (proposed)
"""

import re
from decimal import Decimal

ROW = re.compile(r"^\s*\|(.*)\|\s*$")
BIND = re.compile(r"^\s*([A-Za-z_][\w-]*)\s*:=\s*(.+?)\s*$")
ANNOT = re.compile(r"^\s*%(\S*)\s*(.*)$")
PRAGMA = re.compile(r"^\s*!(\S*)\s*(.*)$")
SEP = re.compile(r"^\s*\|[-:| ]+\|\s*$")

KNOWN_FUNCS = {"sum", "count", "min", "max"}
KNOWN_PRAGMAS = set()          # v1 defines none
KNOWN_ANNOTS = set()           # v1 gives no annotation any meaning


class Reject(Exception):
    pass


def cells(line):
    return [c.strip() for c in ROW.match(line).group(1).split("|")]


def parse(text, policy):
    """Return (header, rows, binds, ignored_lines). Raise Reject under S/H."""
    header, rows, binds, ignored = None, [], {}, []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if SEP.match(line):
            continue
        if ROW.match(line):
            c = cells(line)
            if header is None:
                header = c
            else:
                if len(c) != len(header):
                    if policy == "P":
                        ignored.append((n, line)); continue
                    raise Reject(f"line {n}: row has {len(c)} cells, header has {len(header)}")
                rows.append(c)
            continue
        m = BIND.match(line)
        if m:
            name, expr = m.group(1), m.group(2)
            fn = re.match(r"^(\w+)\(", expr)
            if fn and fn.group(1) not in KNOWN_FUNCS:
                if policy == "P":
                    ignored.append((n, line)); continue
                raise Reject(f"line {n}: unknown function {fn.group(1)}()")
            if name in binds:
                if policy == "P":
                    binds[name] = expr; continue          # last-wins
                raise Reject(f"line {n}: duplicate binding {name}")
            binds[name] = expr
            continue
        m = ANNOT.match(line)
        if m:
            key = m.group(1)
            if key in KNOWN_ANNOTS:
                continue
            if policy == "S":
                raise Reject(f"line {n}: unknown annotation %{key}")
            ignored.append((n, line))                      # P and H: ignore, preserve
            continue
        m = PRAGMA.match(line)
        if m:
            key = m.group(1)
            if key in KNOWN_PRAGMAS:
                continue
            if policy == "P":
                ignored.append((n, line)); continue
            raise Reject(f"line {n}: unknown pragma !{key}")   # S and H both reject
        # anything else at all (conflict markers land here)
        if policy == "P":
            ignored.append((n, line)); continue
        raise Reject(f"line {n}: unrecognised line {line!r}")
    return header, rows, binds, ignored


def evaluate(header, rows, binds):
    """Compute column formulas then bindings. Returns dict of name -> value."""
    if header is None:
        raise Reject("no header")
    names, formulas = [], {}
    for h in header:
        if "=" in h:
            nm, ex = h.split("=", 1)
            names.append(nm.strip()); formulas[nm.strip()] = ex.strip()
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
                env[nm] = eval(formulas[nm], {"__builtins__": {}}, env)  # test harness only
            cols[nm].append(env[nm])
    out = {}
    for name, expr in binds.items():
        fn = re.match(r"^(\w+)\((\w+)\)$", expr)
        if fn and fn.group(1) == "sum":
            out[name] = sum(cols[fn.group(2)])
        elif fn and fn.group(1) == "count":
            out[name] = len(cols[fn.group(2)])
        else:
            out[name] = expr
    return out


def run(text, policy):
    try:
        h, r, b, ig = parse(text, policy)
        return ("value", evaluate(h, r, b), [l for _, l in ig])
    except Reject as e:
        return ("reject", str(e), [])
    except Exception as e:
        return ("crash", f"{type(e).__name__}: {e}", [])

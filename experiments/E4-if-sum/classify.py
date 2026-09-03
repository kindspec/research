#!/usr/bin/env python3
"""Classify the NOTEVAL expressions by what grammar they would actually need.

Input is dump_noteval.py's output: every corpus cell that translates onto
.mdtbl's surface and then falls outside SPEC 4.2. The question is not "how many
say IF" -- E1 answered that -- but "what would 4.2 have to become to compute
them", which is a different and much less flattering number.
"""
import sys, json, re, collections

C = collections.Counter()
S = collections.defaultdict(list)


def note(k, n=1):
    C[k] += n


def samp(k, v, cap=10):
    if len(S[k]) < cap and v not in S[k]:
        S[k].append(v)


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


def call_args(f, name):
    for m in re.finditer(r"(?<![A-Za-z0-9_.])" + name + r"\s*\(", f, re.I):
        i, depth, start = m.end(), 1, m.end()
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


FUNCS = re.compile(r"(?<![A-Za-z0-9_.])([A-Z][A-Z0-9_.]*)\s*\(")
NUM = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")
STR = re.compile(r'^".*"$')
IDENT = re.compile(r"^[^\W]+$", re.UNICODE)
CMP = re.compile(r"(<=|>=|<>|!=|==|<|>|=)")
# 4.2's existing expr: names, unsigned decimal literals, + - * / ( ) and unary -.
ARITH_ONLY = re.compile(r"^[^\W\s]+(?:\s*[-+*/]\s*[^\W\s]+)*$", re.UNICODE)


def is_arith(e):
    """Does this already fit 4.2's expr (names, literals, + - * / parens)?"""
    e = e.strip()
    if not e:
        return False
    if FUNCS.search(e) or '"' in e or CMP.search(e):
        return False
    return bool(re.fullmatch(r"[\w\s.()+\-*/]+", e, re.UNICODE))


def fns(e):
    return set(FUNCS.findall(e.upper()))


def main(path):
    d = json.load(open(path))
    recs = d["samples"].get("NOTEVAL", [])
    note("noteval.records", len(recs))
    for r in recs:
        e = r.get("expr") or ""
        why = r.get("why", "?")
        f = fns(e)
        note("why." + why)

        # ---- SUM ---------------------------------------------------------
        if "SUM" in f:
            note("SUM.cells")
            args = None
            for a in call_args(e, "SUM"):
                args = split_args(a)
                break
            if args is None:
                note("SUM.unparsed")
            elif len(args) == 1 and is_arith(args[0]) and IDENT.match(args[0]):
                # SUM(col) -- a whole column. .mdtbl already spells this as a
                # DECLARATION `g := sum(col)`, not as a row formula.
                note("SUM.shape.whole-column-already-expressible")
                samp("SUM.shape.whole-column-already-expressible", e)
            elif all(is_arith(a) and a for a in args):
                # SUM(a, b, c) over named columns == a + b + c, which 4.2
                # ALREADY generates. This is a translator gap, not a grammar gap
                # -- except for blanks, which SUM skips and `+` does not.
                note("SUM.shape.plain-column-list")
                note(f"SUM.list.arity.{min(len(args), 5)}")
                samp("SUM.shape.plain-column-list", e)
            else:
                note("SUM.shape.needs-more")
                samp("SUM.shape.needs-more", e)
            if len(f - {"SUM"}) == 0 and "IF" not in f:
                note("SUM.only-blocker")

        # ---- IF ----------------------------------------------------------
        if "IF" in f:
            note("IF.cells")
            args = None
            for a in call_args(e, "IF"):
                args = split_args(a)
                break
            if args is None or len(args) < 2:
                note("IF.unparsed")
                continue
            cond = args[0]
            br = args[1:3]
            cf = fns(cond)
            if cf:
                note("IF.cond.calls-a-function")
                for x in sorted(cf):
                    note("IF.condfn." + x)
                samp("IF.cond.calls-a-function", e)
            elif len(CMP.findall(cond)) == 1:
                note("IF.cond.single-comparison")
                rhs = CMP.split(cond, 1)[2].strip()
                note("IF.condrhs." + ("number" if NUM.match(rhs)
                                      else "string" if STR.match(rhs)
                                      else "empty" if rhs == ""
                                      else "name" if IDENT.match(rhs)
                                      else "expression"))
            elif len(CMP.findall(cond)) > 1:
                note("IF.cond.multi-comparison")
            else:
                note("IF.cond.bare-truthiness")
                samp("IF.cond.bare-truthiness", e)

            kinds = []
            for b in br:
                b = b.strip()
                if b == "":
                    kinds.append("omitted")
                elif STR.match(b):
                    kinds.append("string")
                elif NUM.match(b):
                    kinds.append("number")
                elif "IF" in fns(b):
                    kinds.append("nested-IF")
                elif fns(b):
                    kinds.append("other-call")
                elif is_arith(b):
                    kinds.append("arith-or-name")
                else:
                    kinds.append("other")
            note("IF.branches." + "|".join(sorted(set(kinds))))

            # THE CHEAP SUBSET: numeric-only IF that a value model of
            # "number or #REF!" can represent with no new value type.
            numeric_branches = all(k in ("number", "arith-or-name") for k in kinds)
            simple_cond = (not cf) and len(CMP.findall(cond)) == 1
            if numeric_branches and simple_cond and len(args) == 3:
                note("IF.CHEAP.numeric-if-simple-comparison")
                samp("IF.CHEAP.numeric-if-simple-comparison", e)
            else:
                note("IF.EXPENSIVE")
                if not numeric_branches:
                    note("IF.expensive.because.non-numeric-branch")
                if cf:
                    note("IF.expensive.because.condition-calls-a-function")
                if len(CMP.findall(cond)) > 1:
                    note("IF.expensive.because.multi-comparison")
                if len(args) != 3:
                    note(f"IF.expensive.because.arity-{min(len(args), 5)}")

        if not f and "IF" not in f:
            note("no-function." + why)
            samp("no-function." + why, e)

    for k, v in sorted(C.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{v:8d}  {k}")
    json.dump({"counts": dict(C), "samples": dict(S)},
              open("out/classified.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1])

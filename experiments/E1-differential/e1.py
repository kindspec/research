#!/usr/bin/env python3
"""E1 -- differential evaluation: rowspec's evaluator vs Excel's own cached values.

For every formula cell in a real .xlsx that the W3 A1->named-column translator
calls mechanically translatable, build the smallest .mdtbl that isolates that
formula, run rowspec's evaluator on it, and compare the result against the
value Excel itself cached in the file.

THE EVALUABILITY GATE IS ROWSPEC'S OWN PARSER (SPEC 4.2), not Python's.
The first revision of this harness decided evaluability by walking a
`ast.parse` tree, which was defensible only while rowspec's evaluator itself
delegated to `ast.parse`. It no longer does -- 4.2 is a real grammar with a
real parser in `reference/rowspec/table.py` -- and the Python gate was wrong in
both directions. Most visibly: `IF(a="x",1,0)` is not valid Python at all
(`a="x"` reads as a keyword argument), so 10,959 cells were bucketed
`not-python:IF` and never evaluated. An expression is evaluable here iff
`rowspec.table._ast` accepts it, after the mechanical Excel-surface ->
4.2-surface rewrite in `to_rowspec_surface`.

No third-party packages. OOXML via stdlib zipfile + ElementTree.

Usage
  e1.py '<glob>' [more globs] [--out=PATH] [--limit=N]
                 [--shard=I/N] [--files=LIST.txt] [--expand-sum]
  e1_merge.py out/shard-*.json      # sum shards, print the report
"""
import sys, os, re, glob, json, math, zipfile, collections, decimal, traceback
import xml.etree.ElementTree as ET

W3 = '/home/cam/repos_kindspec/working-git-backed-gws/experiments/W3-interop/tools'
sys.path.insert(0, W3)
sys.path.insert(0, '/home/cam/repos_kindspec/rowspec/reference')

import a1trans
from a1trans import NS, col2n, n2col, to_r1c1, translate, read_workbook, REF, mask_strings, unmask
from corpus_run import layout
import rowspec.table as RT

# ---- MUTATION CONTROL -----------------------------------------------------
# The harness is only worth anything if it FAILS when the evaluator is wrong.
# E1_MUTATE injects a known defect into rowspec's evaluator and the whole run is
# repeated; agreement must collapse.
#
# The first two keys were `pyast.Add` / `pyast.Mult` while the evaluator
# delegated to `ast.parse`. It no longer does, so `RT.OPS[pyast.Add] = sub`
# installed a dead key called `Add` and `+` went on adding: the mutant ran the
# full differential, reported total agreement, and that reads as "the harness is
# sound" when it means "the mutation never fired". Every mutant below therefore
# asserts, before the run starts, that it actually changed an observable answer.
_MUT = os.environ.get('E1_MUTATE')
if _MUT:
    import operator as _op

    def _armed(cond, what):
        if not cond:
            raise SystemExit(
                f'E1_MUTATE={_MUT!r} did not arm: {what}. A mutant that cannot '
                f'fire reports a pass, which is the failure this control exists '
                f'to catch. Fix the mutant against the current evaluator.'
            )

    def _one(doc, col='zout'):
        """Evaluate a one-row doc and hand back the computed cell."""
        rows, aggs = RT.evaluate(doc)
        return rows[0].get(col)

    if _MUT == 'add-is-sub':
        _armed('+' in RT.OPS, "RT.OPS has no '+' key")
        RT.OPS['+'] = _op.sub
        _armed(RT.OPS['+'](2, 3) == -1, 'RT.OPS["+"] still adds')
        _armed(_one('| a | b | zout = a + b |\n| - | - | - |\n| 5 | 3 |  |\n') == 2.0,
               'a + b still adds through evaluate()')
    elif _MUT.startswith('mul-rel-'):
        # `split('-')[-1]` on 'mul-rel-1e-15' yields '15', not '1e-15', so the
        # mutant named for a 1-part-in-10^15 perturbation injected a FACTOR OF
        # 16 -- and both arm checks passed, because x16 is certainly "not 1.0".
        _e = float(_MUT[len('mul-rel-'):])
        _armed('*' in RT.OPS, "RT.OPS has no '*' key")
        RT.OPS['*'] = lambda a, b, _e=_e: a * b * (1 + _e)
        _armed(RT.OPS['*'](1.0, 1.0) != 1.0, 'RT.OPS["*"] is unchanged')
        _armed(_one('| a | b | zout = a * b |\n| - | - | - |\n| 1 | 1 |  |\n') != 1.0,
               'a * b is unperturbed through evaluate()')
        # A perturbation below `sigdigits_equal(., ., 15)`'s ~5e-15 relative
        # tolerance is ABSORBED: every affected cell moves from A.exact into
        # A.15sig, which report() counts as agreement. Such a mutant cannot
        # collapse the headline no matter how real the defect is, so it must
        # say so rather than appear to have passed.
        _armed(abs(_e) > 5e-15,
               f'a relative perturbation of {_e:g} is below the 15-significant-digit '
               f'tolerance the report already treats as agreement, so this mutant '
               f'CANNOT move the headline. Use a larger one, or measure A.exact '
               f'directly instead of the headline')
    elif _MUT == 'blank-is-zero':
        _armed(hasattr(RT, 'Name'), 'RT has no Name node type')
        _orig_ev = RT.ev
        _fired = []

        def _ev(node, env):
            if isinstance(node, RT.Name) and str(env.get(node.id, '')).strip() == '':
                _fired.append(1)
                return 0.0
            return _orig_ev(node, env)

        RT.ev = _ev
        _armed(_one('| id | a | zout = a |\n| -- | -- | -- |\n| r_1 |  |  |\n') == 0.0,
               'a blank operand did not become 0.0 through evaluate()')
        _armed(_fired, 'the blank-cell branch was never reached on a blank cell')
    elif _MUT == 'gate-refuses-if':
        # A COVERAGE defect, not an answer defect. It changes nothing any cell
        # evaluates to; it only shrinks what gets evaluated. Every other mutant
        # here perturbs answers, so a regression of this shape -- a parser that
        # quietly stops accepting a construct -- moved the headline by 0.0004
        # points and emptied the whole `if` sub-report without a word. That is
        # the dead-`pyast.Add`-key failure with a different subject.
        _orig_ast = RT._ast
        _fired = []

        def _ast_mut(expr, where):
            if re.search(r'(?<![A-Za-z0-9_])if\s*\(', expr):
                _fired.append(1)
                raise RT.Malformed(f'column {where!r}: refused by the coverage mutant')
            return _orig_ast(expr, where)

        RT._ast = _ast_mut
        try:
            _one('| a | zout = if(a > 0, 1, 0) |\n| - | - |\n| 5 |  |\n')
            _armed(False, 'an if() expression was still accepted by the parser')
        except RT.Malformed:
            pass
        _armed(_fired, 'the if-refusing branch was never reached')
        _armed(_one('| a | b | zout = a + b |\n| - | - | - |\n| 5 | 3 |  |\n') == 8.0,
               'a non-if expression was collaterally broken; this mutant must '
               'change COVERAGE only')
    elif _MUT == 'if-branches-swapped':
        # THE `if` MUTANT. `if` is the surface this rewrite opened up, so the
        # control has to exercise it specifically: a differential that could not
        # fail on `if` would report agreement on `if` no matter what rowspec did.
        _armed(hasattr(RT, 'truth'), 'RT has no truth()')
        _orig_truth = RT.truth
        _fired = []

        def _truth(c, env):
            _fired.append(1)
            return not _orig_truth(c, env)

        RT.truth = _truth
        _armed(_one('| a | zout = if(a > 0, 1, 0) |\n| - | - |\n| 5 |  |\n') == 0.0,
               'if() still selected the true branch on a true comparison')
        _armed(_one('| a | zout = if(a > 0, 1, 0) |\n| - | - |\n| -5 |  |\n') == 1.0,
               'if() still selected the false branch on a false comparison')
        _armed(_fired, 'truth() was never reached')
    elif _MUT == 'if-text-eq-always-true':
        # The other half of rule 10: `=` against a STRING literal, which is the
        # majority shape in the corpus (`IF(x="Y",1,0)`, `IF(x="",b,a)`).
        _armed(hasattr(RT, 'truth'), 'RT has no truth()')
        _orig_truth = RT.truth
        _fired = []

        def _truth(c, env):
            if getattr(c, 'kind', None) == 'str' and c.op == '=':
                _fired.append(1)
                RT._cell(c.lhs, env)   # keep #REF! propagation honest
                return True
            return _orig_truth(c, env)

        RT.truth = _truth
        _armed(_one('| a | zout = if(a = "Y", 1, 0) |\n| - | - |\n| N |  |\n') == 1.0,
               'a text equality that is false still evaluated false')
        _armed(_fired, 'the string-equality branch of truth() was never reached')
    else:
        raise SystemExit('unknown mutant ' + _MUT)

M = '{%s}' % NS['m']

# ------------------------------------------------------------------ raw cells
def raw_cells(z, sst, target):
    """Cells with the RAW <v> text. Deliberately no date-serial cooking: the
    differential must see exactly the double Excel stored."""
    root = ET.fromstring(z.read(target))
    cells = {}
    for c in root.iter(M + 'c'):
        ref = c.get('r')
        if not ref: continue
        t = c.get('t'); fe = c.find(M + 'f'); ve = c.find(M + 'v')
        raw = ve.text if ve is not None else None
        if t == 's' and raw is not None:
            try: val = sst[int(raw)]
            except (ValueError, IndexError): val = None
        elif t == 'inlineStr':
            ise = c.find(M + 'is')
            val = ''.join(x.text or '' for x in ise.iter(M + 't')) if ise is not None else None
            raw = val
        else:
            val = raw
        cells[ref] = dict(f=(fe.text if fe is not None else None),
                          ft=(fe.get('t') if fe is not None else None),
                          fref=fe.get('ref') if fe is not None else None,
                          fsi=fe.get('si') if fe is not None else None,
                          v=val, raw=raw, t=t, isdate=False)
    return cells

# -------------------------------------------------- shared-formula expansion
def shift_formula(f, dr, dc):
    """Shift every RELATIVE reference in an A1 formula by (dr, dc). This is how
    Excel materialises a <f t="shared"> group; without it every fill-down column
    but its master cell is invisible to the harness."""
    body, lits = mask_strings(f)
    def one(mm):
        out = ''
        if mm.group('sheet'): out += mm.group('sheet') + '!'
        def part(cabs, cs, rabs, rs):
            c = col2n(cs); r = int(rs)
            if not cabs: c += dc
            if not rabs: r += dr
            if c < 1 or r < 1: raise ValueError('shift off sheet')
            return ('$' if cabs else '') + n2col(c) + ('$' if rabs else '') + str(r)
        out += part(mm.group('c1'), mm.group('col1'), mm.group('r1'), mm.group('row1'))
        if mm.group('col2'):
            out += ':'
            if mm.group('sheet2'): out += mm.group('sheet2') + '!'
            out += part(mm.group('c2'), mm.group('col2'), mm.group('r2'), mm.group('row2'))
        return out
    return unmask(REF.sub(one, body), lits)

def expand_shared(cells):
    """Fill in f= for cells that carry only <f t='shared' si='n'/>. Returns
    (n_expanded, n_unresolved)."""
    masters = {}
    for ref, d in cells.items():
        if d['ft'] == 'shared' and d['fsi'] is not None and d['f']:
            masters[d['fsi']] = (ref, d['f'])
    exp = unres = 0
    for ref, d in cells.items():
        if d['ft'] == 'shared' and not d['f']:
            m = masters.get(d['fsi'])
            if not m: unres += 1; continue
            mr = re.match(r'([A-Z]+)(\d+)$', m[0]); tr = re.match(r'([A-Z]+)(\d+)$', ref)
            if not (mr and tr): unres += 1; continue
            try:
                d['f'] = shift_formula(m[1], int(tr.group(2)) - int(mr.group(2)),
                                       col2n(tr.group(1)) - col2n(mr.group(1)))
                d['shared_expanded'] = True
                exp += 1
            except Exception:
                unres += 1
    return exp, unres

# ------------------------------------------------------------ value plumbing
def exact_decimal(x):
    """Shortest text that reparses to the SAME double under rowspec's num()
    grammar ([-]DIGIT+[.DIGIT+]) -- no exponent, no separators."""
    r = repr(x)
    if 'e' not in r and 'E' not in r and 'inf' not in r and 'nan' not in r:
        return r
    if not math.isfinite(x): return None
    d = decimal.Decimal(x)
    s = format(d, 'f')
    return s if float(s) == x else None

def cell_literal(d):
    """The .mdtbl cell text for an input cell. Returns (text, kind)."""
    if d is None or d['v'] is None: return ('', 'blank')
    t = d['t']
    if t == 'e': return (str(d['v']), 'error')
    if t in ('s', 'str', 'inlineStr'): return (str(d['v']), 'text')
    if t == 'b': return ('1' if str(d['v']).strip() in ('1', 'TRUE', 'true') else '0', 'bool')
    s = str(d['v']).strip()
    if s == '': return ('', 'blank')
    try: x = float(s)
    except ValueError: return (s, 'text')
    lit = exact_decimal(x)
    if lit is None: return (s, 'text')
    return (lit, 'number')

# ================= EXCEL SURFACE -> SPEC 4.2 SURFACE =======================
# Everything in this section is a spelling change and nothing here is a
# semantic one. Where Excel has a construct 4.2 does not have, the construct is
# left alone so that rowspec's parser refuses it -- inventing syntax rowspec
# does not have would make the differential measure the harness.

_IF_CALL = re.compile(r'(?<![0-9A-Za-z_.])IF\(', re.I)
_IF_SPACED = re.compile(r'(?<![0-9A-Za-z_.])IF\s+\(', re.I)
_SUM_CALL = re.compile(r'(?<![0-9A-Za-z_.])SUM\(', re.I)


def _split_args(s):
    """Top-level comma split of a call's argument text, honouring nesting and
    string literals. Returns None if the text is unbalanced."""
    args, depth, cur, i = [], 0, [], 0
    while i < len(s):
        ch = s[i]
        if ch == '"':
            j = s.find('"', i + 1)
            if j < 0: return None
            cur.append(s[i:j + 1]); i = j + 1; continue
        if ch == '(': depth += 1
        elif ch == ')': depth -= 1
        elif ch == ',' and depth == 0:
            args.append(''.join(cur)); cur = []; i += 1; continue
        cur.append(ch); i += 1
    if depth: return None
    args.append(''.join(cur))
    return args


def _match_paren(s, open_at):
    """Index of the ')' closing the '(' at s[open_at], honouring strings."""
    depth, i = 0, open_at
    while i < len(s):
        ch = s[i]
        if ch == '"':
            j = s.find('"', i + 1)
            if j < 0: return -1
            i = j + 1; continue
        if ch == '(': depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0: return i
        i += 1
    return -1


def expand_sum(expr):
    """`SUM(a, b, c)` -> `(a+b+c)`, innermost first, repeatedly.

    E4 measured this admits 5,513 further corpus cells with NO grammar change:
    4.2 rule 11 is explicit that a row-wise `sum` is deliberately absent and
    that `a + b + c` already generates the shape. It is a TRANSLATOR step, so it
    lives behind --expand-sum and is never folded into the baseline.

    It is not semantics-preserving in one respect, and that respect is measured
    rather than hidden: `SUM` skips a blank operand and `+` does not (SPEC 8),
    so a rewritten cell with a blank operand lands in `Dref.blank` -- the same
    by-design bucket, out of the headline, as every other blank operand.

    Returns (expr, n_rewrites).
    """
    n = 0
    for _ in range(64):
        ms = list(_SUM_CALL.finditer(expr))
        if not ms: break
        m = ms[-1]                       # innermost-last: rewrite from the right
        op = m.end() - 1
        cl = _match_paren(expr, op)
        if cl < 0: break
        args = _split_args(expr[op + 1:cl])
        if args is None or any(a.strip() == '' for a in args): break
        expr = expr[:m.start()] + '(' + '+'.join('(%s)' % a.strip() for a in args) + ')' + expr[cl + 1:]
        n += 1
    return expr, n


def to_rowspec_surface(expr, do_sum):
    """Rewrite the translator's Excel-surface expression onto 4.2's surface.

    Returns (expr, info) where info records which rewrites fired.

      IF( -> if(   4.2 rule 4: function names are lower-case and matched
                   case-sensitively, and are recognised ONLY immediately before
                   `(` with no WSP. `IF (` with a space is therefore NOT
                   rewritten -- rowspec refuses it and so does this harness.
      SUM(a,b) -> (a+b)   only under --expand-sum.

    Deliberately NOT rewritten, because 4.2 has no such construct and pretending
    otherwise would measure the harness rather than rowspec:
      &  ^  %      refused operators (4.2 rule 1)
      unary +      `=+B2*C2`, the Lotus idiom; `factor = [ "-" ] primary`
      <> <= >= < > = are already 4.2's own spellings inside a `cond`, and are
                   already refused outside one -- no rewrite needed either way.
      1E+10 .5 5%  literal spellings 4.2's `literal` does not admit
      "a""b"       Excel's doubled quote; 4.2 rule 6 has no escape in a string
    """
    info = {}
    if _IF_SPACED.search(expr): info['if-spaced'] = True
    e2 = _IF_CALL.sub('if(', expr)
    if e2 != expr: info['if'] = True
    expr = e2
    if do_sum:
        expr, n = expand_sum(expr)
        if n: info['sum'] = n
    return expr, info


# ---------------------------------------------------- rowspec grammar filter
_WORDISH = ('name', 'num', 'call')


def rowspec_parse(expr):
    """The gate. Accepts iff rowspec's own 4.2 parser accepts.

    `_ast` rather than `_parse_expr` because `_ast` also carries the 4.1.10
    check that `#` is not a comment inside a formula, which is part of what the
    reference implementation accepts.
    """
    return RT._ast(expr, 'zout')


def noteval_label(expr, exc):
    """A stable bucket name for an expression the parser refused.

    Keeps E1's `Call:NAME` shape so the histogram stays comparable; the
    `not-python:*` buckets are gone, because the Python gate is gone.
    """
    for fn in re.findall(r'([A-Za-z_][\w.]*)\s*\(', expr):
        if fn != 'if':
            return 'Call:' + fn.upper()
    m = str(exc)
    if 'unary +' in m: return 'Op:unary-plus'
    for ch in '&^%':
        if ch in expr: return 'Op:' + ch
    if 'is not an operator of an expression' in m: return 'Op:comparison-outside-if'
    if '§9.24' in m: return 'Cmp:ident-on-rhs-of-eq'
    if 'compares numbers, never text' in m: return 'Cmp:text-on-rhs-of-order'
    if 'left of a comparison' in m: return 'Cmp:lhs-not-a-name'
    if "is not part of an expression" in m: return 'Tok:bad-character'
    if 'trailing input' in m: return 'Parse:trailing-input'
    if 'expected a value' in m:
        # `expr` does not generate `string`, so `if(c="x","PASS","FAIL")` is
        # refused by the GRAMMAR (4.2 rule 10's last paragraph). E4 measured
        # this as the largest single thing rule 10 does not do, so it gets its
        # own bucket rather than hiding inside a parse error.
        if re.search(r',\s*"', expr): return 'If:text-branch'
        return 'Parse:expected-a-value'
    if 'unclosed parenthesis' in m: return 'Parse:unclosed-paren'
    if "expected ','" in m or "expected ')'" in m or "expected '('" in m: return 'Parse:if-arity'
    if 'not a comment inside a formula' in m: return 'Tok:hash'
    return 'Parse:other'


def literal_shaped_names(names):
    """Column names 4.2 rule 7 makes unreachable from an operand position.

    E1 measured this as a rowspec BUG (`BUG.shadowed-column-name`): `ast.parse`
    read `1000_2999` as the number 10002999 and `1e3` as 1000.0. rowspec's own
    lexer is maximal-munch over ident characters and classifies `1000_2999` and
    `1e3` as NAMES, so that bug is gone. What remains is rule 7's stated cost --
    a name that is ENTIRELY `1*DIGIT [ "." 1*DIGIT ]` reads as a literal in an
    operand position -- which is by design and gets its own counter.
    """
    return [n for n in names if RT._LITERAL.match(n)]


def rename_emit(toks, ren):
    """Re-emit a lexed 4.2 expression with columns renamed to x0..xN.

    Token-level, because 4.2's AST has no unparser and Python's has no business
    here. A space is inserted only between two word-ish tokens, and NEVER
    between a function name and its `(`: rule 4 makes `if (` a refusal.
    """
    out, prev = [], None
    for k, v in toks:
        if k == 'str': t = '"' + v + '"'
        elif k == 'name': t = ren.get(v, v)
        else: t = v
        if prev in _WORDISH and k in _WORDISH: out.append(' ')
        out.append(t); prev = k
    return ''.join(out)


# --------------------------------------------- 40-digit decimal cross-check
def hp_eval(node, env):
    """Evaluate the SAME 4.2 tree on the SAME inputs in 40-digit decimal.

    This separates 'rowspec's IEEE doubles accumulated rounding' from 'the
    inputs or the semantics actually differ'. It mirrors `RT.ev` / `RT.truth`,
    lazy branch selection included; anything it cannot do raises and the caller
    records no high-precision opinion at all.
    """
    ctx = decimal.Context(prec=40)

    def cell(name):
        if name not in env: raise KeyError(name)
        return env[name]

    def number(name):
        v = cell(name)
        if str(v).strip() == '': raise KeyError(name)
        return decimal.Decimal(str(v).strip())

    def truth(c):
        if c.op in ('=', '<>'):
            if c.kind == 'str':
                eq = str(cell(c.lhs)).strip() == c.rhs
            else:
                eq = number(c.lhs) == decimal.Decimal(str(c.rhs))
            return eq if c.op == '=' else not eq
        a = number(c.lhs)
        b = decimal.Decimal(str(c.rhs)) if c.kind == 'num' else number(c.rhs)
        return {'<': a < b, '<=': a <= b, '>': a > b, '>=': a >= b}[c.op]

    def go(n):
        if isinstance(n, RT.Num): return decimal.Decimal(str(n.v))
        if isinstance(n, RT.Name): return number(n.id)
        if isinstance(n, RT.Neg): return -go(n.x)
        if isinstance(n, RT.If): return go(n.a) if truth(n.c) else go(n.b)
        a, b = go(n.l), go(n.r)
        if n.op == '+': return ctx.add(a, b)
        if n.op == '-': return ctx.subtract(a, b)
        if n.op == '*': return ctx.multiply(a, b)
        if b == 0: raise ZeroDivisionError
        return ctx.divide(a, b)
    return go(node)


# ------------------------------------------------------------- comparison
def as_float(s):
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError): return None

def sigdig(s):
    d = str(s).strip().lstrip('-').split('E')[0].split('e')[0].replace('.', '').lstrip('0')
    return len(d.rstrip('0')) if d else 0


def sigdigits_equal(a, b, nd):
    if a == b: return True
    if a == 0 or b == 0: return abs(a - b) < 10 ** -(nd + 6)
    return abs(a - b) <= abs(b) * (10.0 ** -(nd - 1)) * 0.5000001

# ------------------------------------------------------------------- driver
CNT = collections.Counter()
SEEN = collections.defaultdict(set)
DISAG = []
SAMPLE = collections.defaultdict(list)
OPT = dict(expand_sum=False)
# Per-cell mirrors. Every counter a cell contributes is also written under each
# active prefix, so the run reports the SUM-rewrite's contribution and the `if`
# surface's contribution separately without a second pass:
#   sumx.*  this cell's SUM(...) was rewritten by --expand-sum
#   if.*    this cell's 4.2 tree contains an `if`
#   ifstr.* this cell's `if` compares a column against a STRING literal
CUR = dict(sumx=False, hasif=False, ifstr=False)
_PREFIX = (('sumx', 'sumx.'), ('hasif', 'if.'), ('ifstr', 'ifstr.'))

def note(k, n=1):
    CNT[k] += n
    for flag, pre in _PREFIX:
        if CUR[flag]: CNT[pre + k] += n


def has_if(node):
    if isinstance(node, RT.If): return True
    if isinstance(node, RT.Neg): return has_if(node.x)
    if isinstance(node, RT.Bin): return has_if(node.l) or has_if(node.r)
    return False

def samp(k, rec, cap=40):
    if len(SAMPLE[k]) < cap: SAMPLE[k].append(rec)

def run_row_case(tree, src, hdr_inv, g, r, own_col, wbid, sheet, cell, a1):
    """Build a one-row .mdtbl isolating this formula and evaluate it."""
    names = RT.names_of(tree)
    lit_shaped = literal_shaped_names(names)
    if lit_shaped:
        # rule 7: reachable from a name position, unreachable from an operand
        # one, and the harness cannot rename a token whose kind depends on its
        # position. Counted, not guessed at.
        note('rule7.numeric-column-name-in-formula')
        samp('rule7.numeric-column-name-in-formula',
             dict(wb=wbid, sheet=sheet, cell=a1, names=lit_shaped))
        return None
    cols = []
    for nm in sorted(set(names)):
        cn = hdr_inv.get(nm)
        if cn is None: note('exc.name-not-a-column'); return None
        if cn == 'AMBIG': note('exc.duplicate-header-name'); return None
        if cn == own_col:
            note('exc.self-reference'); return None
        cols.append((nm, cn))
    if not cols: note('exc.no-column-referenced'); return None
    ren = {nm: 'x%d' % i for i, (nm, cn) in enumerate(cols)}
    try:
        newexpr = rename_emit(RT._lex(src, 'zout'), ren)
    except Exception:
        note('exc.relex-failed'); return None
    if any(ch in newexpr for ch in '|#\n') or ':=' in newexpr:
        note('exc.expr-unrepresentable'); return None
    # The rename must be a pure renaming: same shape, same column set. If
    # re-parsing does not agree, the case is dropped rather than guessed at.
    try:
        newtree = rowspec_parse(newexpr)
    except Exception:
        note('exc.rename-broke-the-parse'); return None
    if sorted(set(RT.names_of(newtree))) != sorted(ren[n] for n in sorted(set(names))):
        note('exc.rename-changed-the-names'); return None
    lits, kinds = [], []
    chained = False
    for nm, cn in cols:
        src = g.get(r, {}).get(cn)
        if src is not None and src.get('f'): chained = True
        lit, kind = cell_literal(src)
        if any(ch in lit for ch in '|\n'): note('exc.value-unrepresentable'); return None
        if kind == 'text':
            if lit != lit.strip(' \t'):
                # split_row trims ASCII space/tab, so the .mdtbl cannot carry a
                # value Excel compared with its padding intact.
                note('exc.text-would-be-trimmed'); return None
            if re.search(r'\s#', lit): note('exc.value-annotation-shaped'); return None
        lits.append(lit); kinds.append(kind)
    note('chain.' + ('depends-on-a-formula-cell' if chained else 'depends-only-on-literals'))
    hdr = [ren[nm] for nm, _ in cols] + ['zout = ' + newexpr]
    doc = ('| ' + ' | '.join(hdr) + ' |\n'
           + '| ' + ' | '.join(['---'] * len(hdr)) + ' |\n'
           + '| ' + ' | '.join(lits + ['']) + ' |\n')
    return doc, kinds, newtree, dict(zip([ren[nm] for nm, _ in cols], lits))


def evaluate_doc(doc, colname='zout'):
    """-> (status, value). status in ok / refused / crashed."""
    try:
        rows, aggs = RT.evaluate(doc)
    except RT.Malformed as e:
        return ('refused', str(e)[:200])
    except Exception as e:
        return ('crashed', type(e).__name__ + ': ' + str(e)[:150])
    if colname in aggs: return ('ok', aggs[colname])
    return ('ok', rows[0].get(colname) if rows else None)

def compare(exc_d, rs_status, rs_val, ctx, hp=None):
    """Classify one cell. ctx carries everything needed to reproduce."""
    et = exc_d['t']; ev_raw = exc_d['v']
    isref = isinstance(rs_val, str) and str(rs_val).startswith('#REF!')

    if et == 'e':                              # Excel itself cached an error
        note('cmp.excel-error')
        if rs_status == 'crashed':
            note('D.crash-where-excel-errors'); note('crash.' + str(rs_val).split(':')[0])
            samp('D.crash-where-excel-errors', ctx | {'excel': ev_raw, 'rs': rs_val}); return
        if rs_status == 'refused':
            note('A.refused-where-excel-errors'); samp('A.refused-where-excel-errors', ctx | {'excel': ev_raw, 'rs': rs_val}); return
        if isref:
            note('A.ref-where-excel-errors'); return
        note('D.value-where-excel-errors'); samp('D.value-where-excel-errors', ctx | {'excel': ev_raw, 'rs': rs_val}); return

    if rs_status == 'crashed':
        note('D.rowspec-crashed'); note('crash.' + str(rs_val).split(':')[0])
        samp('D.rowspec-crashed', ctx | {'excel': ev_raw, 'rs': rs_val}); return
    if rs_status == 'refused':
        note('D.rowspec-refused'); samp('D.rowspec-refused', ctx | {'excel': ev_raw, 'rs': rs_val}); return

    if et in ('s', 'str', 'inlineStr'):
        note('cmp.excel-text')
        if str(rs_val) == str(ev_raw): note('A.text-equal')
        else: note('D.text-differs'); samp('D.text-differs', ctx | {'excel': ev_raw, 'rs': rs_val})
        return
    if et == 'b':
        note('cmp.excel-bool'); note('D.excel-bool')
        samp('D.excel-bool', ctx | {'excel': ev_raw, 'rs': rs_val}); return

    ex = as_float(ev_raw)
    if ex is None:
        note('exc.excel-value-unparseable'); return
    note('cmp.numeric')
    if isref:
        ks = ctx.get('kinds') or []
        note('D.ref-where-excel-numeric')
        note('Dref.' + ('blank' if 'blank' in ks else 'text' if 'text' in ks else
                        'error' if 'error' in ks else 'other'))
        samp('D.ref-where-excel-numeric', ctx | {'excel': ev_raw, 'rs': rs_val}); return
    rv = as_float(rs_val)
    if rv is None:
        note('D.nonnumeric-where-excel-numeric'); samp('D.nonnumeric-where-excel-numeric', ctx | {'excel': ev_raw, 'rs': rs_val}); return
    if rv == ex:
        note('A.exact'); return
    if sigdigits_equal(rv, ex, 15):
        note('A.15sig')
        # WHY is it not bit-exact? If 40-digit decimal on the SAME inputs also
        # misses Excel's value, the loss is in the INPUTS Excel serialised, not
        # in rowspec's arithmetic.
        if hp is None: note('A15.no-hp')
        elif hp == ex: note('A15.hp-matches-excel-so-rowspec-float-is-the-cause')
        else: note('A15.hp-also-differs-so-the-inputs-are-the-cause')
        mx = max([sigdig(v) for v in (ctx.get('lits') or ['0'])] or [0])
        note('A15.max-input-sigdigits-' + ('15' if mx == 15 else '16plus' if mx > 15 else 'le14'))
        samp('A.15sig', ctx | {'excel': ev_raw, 'rs': rs_val, 'hp': hp}); return
    rec = ctx | {'excel': ev_raw, 'rs': rs_val, 'hp': hp, 'exsig': sigdig(ev_raw)}
    if hp is not None and not sigdigits_equal(hp, ex, 15) and sigdigits_equal(hp, rv, 15):
        # 40-digit decimal on the SAME inputs lands where rowspec landed, not
        # where Excel landed: the disagreement is NOT float rounding.
        note('D.semantic'); samp('D.semantic', rec); DISAG.append(rec | {'cls': 'D.semantic'}); return
    if hp is not None and sigdigits_equal(hp, ex, 15):
        note('D.float-accum'); samp('D.float-accum', rec); return
    note('D.differs'); samp('D.differs', rec)
    DISAG.append(rec | {'cls': 'D.differs'})

AGGRE = re.compile(r'^\s*(sum|count|min|max|avg)\s*\(\s*(\S+)\s*\)\s*$')

def run_agg_case(expr, hdr_inv, g, drange, wbid, sheet, cell, a1):
    m = AGGRE.match(expr)
    if not m: note('exc.agg-shape'); return None
    fn, nm = m.group(1), m.group(2)
    cn = hdr_inv.get(nm)
    if cn is None or cn == 'AMBIG': note('exc.agg-column'); return None
    r1, r2 = drange
    if r2 - r1 + 1 > 4000: note('exc.agg-too-tall'); return None
    lits = []
    for r in range(r1, r2 + 1):
        lit, kind = cell_literal(g.get(r, {}).get(cn))
        if any(ch in lit for ch in '|\n'): note('exc.value-unrepresentable'); return None
        lits.append(lit)
    if not lits: note('exc.agg-empty'); return None
    doc = ('| x0 |\n| --- |\n' + ''.join('| %s |\n' % L for L in lits)
           + '\nzout := %s(x0)\n' % fn)
    return doc, None, None, None

def table_ranges(z, tgt):
    """Data-row range of every real Excel Table (ListObject) on this sheet.
    The `layout` heuristic GUESSES the region; when the workbook states it, use
    the stated one, so the differential measures rowspec and not the guess."""
    out = {}
    rel = tgt.replace('xl/worksheets/', 'xl/worksheets/_rels/') + '.rels'
    if rel not in z.namelist(): return out
    try: rr = ET.fromstring(z.read(rel))
    except Exception: return out
    for r in rr:
        t = (r.get('Target') or '').replace('../', 'xl/')
        if '/tables/' not in t or t not in z.namelist(): continue
        try: te = ET.fromstring(z.read(t))
        except Exception: continue
        ref = te.get('ref') or ''
        m = re.fullmatch(r'([A-Z]+)(\d+):([A-Z]+)(\d+)', ref)
        if not m: continue
        hdr = (te.get('headerRowCount') or '1') != '0'
        tot = int(te.get('totalsRowCount') or 0)
        r1 = int(m.group(2)) + (1 if hdr else 0); r2 = int(m.group(4)) - tot
        out[te.get('name') or te.get('displayName')] = (r1, r2)
    return out


def process(path, wbid):
    z, sst, sheets, wb = read_workbook(path)
    a1trans.WB.clear(); a1trans._UNIQ_CACHE.clear()
    allc = {}
    for name, tgt in sheets:
        if tgt not in z.namelist(): continue
        cells = raw_cells(z, sst, tgt)
        e, u = expand_shared(cells)
        note('shared.expanded', e); note('shared.unresolved', u)
        allc[name] = cells
        L = layout(name, cells)
        if L is not None:
            L['tables'] = table_ranges(z, tgt)
            a1trans.WB[name] = L
    for sheet, cells in allc.items():
        L = a1trans.WB.get(sheet)
        if not L: continue
        g, hdr, hrow, drange = L['g'], L['hdr'], L['hrow'], L['drange']
        if hrow is None or not hdr:
            note('exc.no-header', sum(1 for d in cells.values() if d['f'])); continue
        inv = {}
        for c, nm in hdr.items(): inv[nm] = 'AMBIG' if nm in inv else c
        for r in sorted(g):
            if r <= hrow: continue
            for c, d in g[r].items():
                CUR['sumx'] = CUR['hasif'] = CUR['ifstr'] = False
                if not d['f']: continue
                note('formula-cells')
                if d['ft'] == 'array': note('exc.array-formula'); continue
                a1 = '%s%d' % (n2col(c), r)
                try:
                    verdict, expr, why = translate(d['f'], a1, sheet, hdr, drange, None)
                except Exception:
                    note('exc.translator-error'); continue
                note('verdict.' + verdict)
                if verdict not in ('CLEAN', 'CLEAN-WIDE', 'AGGREGATE'): continue
                note('translatable')
                if d['v'] is None: note('exc.no-cached-value'); continue
                ctx = dict(wb=wbid, sheet=sheet, cell=a1, f=d['f'][:120], expr=(expr or '')[:120],
                           verdict=verdict, shared=bool(d.get('shared_expanded')))
                if verdict == 'AGGREGATE':
                    dr = drange
                    tn = re.match(r"\s*(?:SUBTOTAL\s*\(\s*\d+\s*,\s*)?([A-Za-z_][\w.]*)\[", d['f'])
                    if tn:
                        tr = L.get('tables', {}).get(tn.group(1))
                        if tr: dr = tr; note('agg.table-range-used')
                        else: note('exc.agg-table-range-unknown'); continue
                    # NOT `EVALUABLE`: E1's published ladder counted that key for
                    # ROW formulas only (48,090) and reported the 215 aggregates
                    # beside it. Keeping the key's denominator identical is what
                    # makes the two runs comparable.
                    note('EVALUABLE.aggregate')
                    built = run_agg_case(expr, inv, g, dr, wbid, sheet, a1, d['f'])
                else:
                    # ---- THE GATE -------------------------------------------
                    rexpr, info = to_rowspec_surface(expr, OPT['expand_sum'])
                    if info.get('if'): note('surface.if-lowercased')
                    if info.get('if-spaced'): note('surface.if-with-space-not-rewritten')
                    if info.get('sum'):
                        note('surface.sum-expanded', 1)
                        CUR['sumx'] = True
                    ctx['rexpr'] = rexpr[:120]
                    try:
                        tree = rowspec_parse(rexpr)
                    except RT.Malformed as e:
                        lab = noteval_label(rexpr, e)
                        note('NOTEVAL'); note('noteval.' + lab.split(':')[0])
                        note('notevalfull.' + lab)
                        samp('NOTEVAL', ctx | {'why': lab, 'msg': str(e)[:160]}); continue
                    except Exception as e:
                        note('NOTEVAL'); note('noteval.ParserCrash')
                        note('notevalfull.ParserCrash:' + type(e).__name__)
                        samp('NOTEVAL', ctx | {'why': 'parser-crash', 'msg': repr(e)[:160]}); continue
                    if has_if(tree):
                        CUR['hasif'] = True
                        if RT.str_cmp_lhs(tree): CUR['ifstr'] = True
                    note('EVALUABLE')
                    built = run_row_case(tree, rexpr, inv, g, r, c, wbid, sheet, a1, d['f'])
                if built is None: continue
                doc, kinds, newtree, env = built
                st, val = evaluate_doc(doc)
                hp = None
                if env is not None and newtree is not None:
                    try: hp = float(hp_eval(newtree, env))
                    except Exception: hp = None
                note('compared')
                SEEN['wb'].add(wbid); SEEN['sheet'].add(wbid + '\x00' + sheet)
                compare(d, st, val, ctx | {'doc': doc, 'kinds': kinds,
                                          'lits': list((env or {}).values())}, hp)
    CUR['sumx'] = CUR['hasif'] = CUR['ifstr'] = False


# --------------------------------------------------------------- reporting
# Each mutant names the counter movement that PROVES it fired, checked against
# the run's own numbers by `check_mutation_signal`. `blank-is-zero` is the
# reason this exists: it perturbs which BUCKET a cell lands in rather than the
# answer, so measuring it on the headline made a real SPEC 8 violation look like
# an improvement -- 100.00% before, 100.00% after, with a LARGER denominator.
# A control has to be read on a metric it can actually move.
MUTATION_SIGNAL = {
    'add-is-sub': ('headline agreement falls', lambda b, m: m['headline'] < b['headline'] - 0.01),
    'blank-is-zero': (
        'Dref.blank collapses (NOT the headline -- this mutant raises it)',
        lambda b, m: m['Dref.blank'] < b['Dref.blank'] * 0.1,
    ),
    'if-branches-swapped': ('if-path agreement falls', lambda b, m: m['if_agree'] < b['if_agree'] * 0.9),
    'if-text-eq-always-true': ('string-comparison agreement falls', lambda b, m: m['ifstr_agree'] < b['ifstr_agree']),
    'gate-refuses-if': (
        'EVALUABLE falls and the if-report empties (a COVERAGE defect, invisible in the headline)',
        lambda b, m: m['EVALUABLE'] < b['EVALUABLE'] * 0.99 and m['if_compared'] == 0,
    ),
}


def signal_metrics(cnt):
    """The counters a mutation signal is read from."""
    g = cnt.get
    compared = g('compared', 0)
    agree = g('A.exact', 0) + g('A.15sig', 0) + g('A.ref-where-excel-errors', 0)
    denom = compared - g('Dref.blank', 0) - g('cmp.excel-text', 0)
    return {
        'headline': (agree / denom * 100) if denom else 0.0,
        'Dref.blank': g('Dref.blank', 0),
        'EVALUABLE': g('EVALUABLE', 0),
        'if_agree': g('if.A.exact', 0) + g('if.A.15sig', 0),
        'ifstr_agree': g('ifstr.A.exact', 0) + g('ifstr.A.15sig', 0),
        'if_compared': g('if.compared', 0),
    }


def check_mutation_signal(baseline_path, cnt, out=sys.stdout):
    """With E1_MUTATE set, assert the mutant moved the thing it claims to move."""
    if not _MUT:
        return True
    spec = MUTATION_SIGNAL.get(_MUT)
    if spec is None:
        print(f'  MUTATION CONTROL: no expected signal declared for {_MUT!r} -- '
              f'an undeclared mutant proves nothing', file=out)
        return False
    why, ok = spec
    try:
        base = signal_metrics(json.load(open(baseline_path))['counts'])
    except Exception as e:
        print(f'  MUTATION CONTROL: cannot read baseline {baseline_path}: {e}', file=out)
        return False
    got = signal_metrics(cnt)
    passed = ok(base, got)
    print(f'\n  MUTATION CONTROL [{_MUT}]  {"DETECTED" if passed else "*** NOT DETECTED ***"}',
          file=out)
    print(f'    expected: {why}', file=out)
    for k in ('headline', 'Dref.blank', 'EVALUABLE', 'if_agree', 'if_compared'):
        print(f'    {k:14} {base[k]:>12,.4f} -> {got[k]:>12,.4f}'
              if isinstance(base[k], float) else
              f'    {k:14} {base[k]:>12,} -> {got[k]:>12,}', file=out)
    return passed


def report(cnt, out=sys.stdout):
    """The headline, computed the same way E1 published it.

    The two BY-DESIGN classes stay in their own buckets and out of the
    denominator: `Dref.blank` (SPEC 8 -- a blank cell is not zero) and
    `cmp.excel-text` (SPEC 7 -- a computed column is arithmetic and cannot
    carry text).
    """
    g = cnt.get
    compared = g('compared', 0)
    agree = g('A.exact', 0) + g('A.15sig', 0) + g('A.ref-where-excel-errors', 0)
    bydesign = g('Dref.blank', 0) + g('cmp.excel-text', 0)
    denom = compared - bydesign
    p = lambda s: print(s, file=out)
    p('')
    p('  formula cells read                 %10d' % g('formula-cells', 0))
    p('  translatable                       %10d' % g('translatable', 0))
    p('  EVALUABLE (rowspec 4.2 parser)     %10d  (+%d aggregates)'
      % (g('EVALUABLE', 0), g('EVALUABLE.aggregate', 0)))
    p('  NOTEVAL   (parser refused)         %10d' % g('NOTEVAL', 0))
    p('  compared                           %10d' % compared)
    p('')
    p('  AGREEMENT                          %10d' % agree)
    p('    exact double equality            %10d' % g('A.exact', 0))
    p('    equal to 15 significant digits   %10d' % g('A.15sig', 0))
    p('    Excel errored, rowspec #REF!     %10d' % g('A.ref-where-excel-errors', 0))
    p('  BY DESIGN (out of the headline)    %10d' % bydesign)
    p('    blank operand   (Dref.blank)     %10d' % g('Dref.blank', 0))
    p('    text passthrough (cmp.excel-text)%10d' % g('cmp.excel-text', 0))
    p('  OTHER DISAGREEMENT                 %10d' % (denom - agree))
    for k in ('D.differs', 'D.semantic', 'D.float-accum', 'D.rowspec-refused',
              'D.rowspec-crashed', 'D.nonnumeric-where-excel-numeric',
              'D.value-where-excel-errors', 'D.crash-where-excel-errors',
              'D.excel-bool', 'Dref.text', 'Dref.error', 'Dref.other'):
        if g(k): p('    %-32s %10d' % (k, g(k)))
    if denom > 0:
        p('')
        p('  excluding the two by-design classes: %d / %d = %.2f%%'
          % (agree, denom, 100.0 * agree / denom))
    for pre, lab in (('if.', 'cells whose 4.2 tree contains an `if`'),
                     ('ifstr.', '... of those, comparing a column against a STRING')):
        if g(pre + 'compared'):
            p('')
            p('  %s' % lab)
            p('    EVALUABLE                        %10d' % g(pre + 'EVALUABLE', 0))
            p('    compared                         %10d' % g(pre + 'compared', 0))
            p('    agreement                        %10d'
              % (g(pre + 'A.exact', 0) + g(pre + 'A.15sig', 0) + g(pre + 'A.ref-where-excel-errors', 0)))
            p('    by design (blank/text)           %10d'
              % (g(pre + 'Dref.blank', 0) + g(pre + 'cmp.excel-text', 0)))
            p('    other disagreement               %10d'
              % (g(pre + 'compared', 0) - g(pre + 'Dref.blank', 0) - g(pre + 'cmp.excel-text', 0)
                 - g(pre + 'A.exact', 0) - g(pre + 'A.15sig', 0) - g(pre + 'A.ref-where-excel-errors', 0)))
    sx = g('sumx.compared', 0)
    if sx:
        p('')
        p('  --expand-sum attribution (cells whose SUM was rewritten)')
        p('    compared                         %10d' % sx)
        p('    agreement                        %10d'
          % (g('sumx.A.exact', 0) + g('sumx.A.15sig', 0) + g('sumx.A.ref-where-excel-errors', 0)))
        p('    by design (blank/text)           %10d'
          % (g('sumx.Dref.blank', 0) + g('sumx.cmp.excel-text', 0)))
        p('    EVALUABLE attributable           %10d' % g('sumx.EVALUABLE', 0))
        p('')
        p('    baseline-comparable (subtract the above):')
        p('      compared                       %10d' % (compared - sx))
        p('      EVALUABLE                      %10d' % (g('EVALUABLE', 0) - g('sumx.EVALUABLE', 0)))


# ------------------------------------------------------------------- main
def pick_files(pats, files_list, shard, limit):
    """Deterministic ordering, then a stride shard.

    Stride (`files[i::N]`) rather than a contiguous block: the corpus is sorted
    by directory, sizes are wildly uneven, and contiguous blocks put all the big
    workbooks in one shard. Every file lands in exactly one shard, so counters
    merge by summing and the contributing-workbook sets merge by union.
    """
    if files_list:
        files = [l.strip() for l in open(files_list) if l.strip()]
    else:
        files = []
        for p in pats: files += glob.glob(p, recursive=True)
    files = sorted(set(files))
    if limit: files = files[:limit]
    if shard:
        i, n = shard
        files = files[i::n]
    return files


def main(pats, limit=None, out='out/e1.json', shard=None, files_list=None):
    files = pick_files(pats, files_list, shard, limit)
    okc = badc = 0
    for i, p in enumerate(files):
        try:
            process(p, os.path.basename(os.path.dirname(p)) + '/' + os.path.basename(p)); okc += 1
        except Exception as e:
            badc += 1; note("wb.unreadable")
            if os.environ.get("E1DBG"): traceback.print_exc()
        if i % 250 == 0:
            print('  ..%d/%d wb  %d formula cells  %d compared' %
                  (i, len(files), CNT['formula-cells'], CNT['compared']), file=sys.stderr, flush=True)
    note('wb.ok', okc); note('wb.bad', badc)
    CNT['distinct.workbooks-contributing'] = len(SEEN['wb'])
    CNT['distinct.sheets-contributing'] = len(SEEN['sheet'])
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump({'meta': {'shard': ('%d/%d' % shard) if shard else None,
                        'files': len(files),
                        'expand_sum': OPT['expand_sum'],
                        'mutate': _MUT},
               'counts': dict(CNT),
               'wb': sorted(SEEN['wb']),
               'sheet': sorted(SEEN['sheet']),
               'samples': {k: v for k, v in SAMPLE.items()}},
              open(out, 'w'), indent=1, default=str)
    for k, v in sorted(CNT.items()): print('%-52s %8d' % (k, v))
    report(CNT)
    if _MUT:
        # A mutation run that does not say whether it was DETECTED has told you
        # nothing. `E1_BASELINE` names the unmutated run to compare against.
        base = os.environ.get('E1_BASELINE', 'out/full/merged.json')
        if not check_mutation_signal(base, CNT):
            print('\n  The mutation control did NOT detect this defect. Either the '
                  'mutant is wrong, or the differential cannot see this class of '
                  'failure -- and a differential that cannot fail reports '
                  'agreement.', file=sys.stdout)
            sys.exit(2)
    return CNT

if __name__ == '__main__':
    a = sys.argv[1:]
    lim = None; out = 'out/e1.json'; pats = []; shard = None; flist = None
    for x in a:
        if x.startswith('--limit='): lim = int(x.split('=')[1])
        elif x.startswith('--out='): out = x.split('=', 1)[1]
        elif x.startswith('--files='): flist = x.split('=', 1)[1]
        elif x.startswith('--shard='):
            i, n = x.split('=', 1)[1].split('/'); shard = (int(i), int(n))
            if not (0 <= shard[0] < shard[1]): raise SystemExit('--shard=I/N needs 0 <= I < N')
        elif x == '--expand-sum': OPT['expand_sum'] = True
        elif x.startswith('--'): raise SystemExit('unknown flag ' + x)
        else: pats.append(x)
    main(pats, lim, out, shard, flist)

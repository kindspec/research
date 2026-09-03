#!/usr/bin/env python3
"""Translate Excel A1 formulas into .tbl named-column formulas.

Classification (each formula gets exactly one verdict):
  CLEAN        every reference is a same-row, same-sheet, relative reference to a
               named column, and every function used is in the total/pure subset.
               -> emitted as a column formula in the header.
  AGGREGATE    a single cell whose refs are a whole-column range over exactly the
               data rows -> emitted as `name := fn(col)`.
  NEEDS-HUMAN  structurally translatable but the target semantics do not exist in
               .tbl, or a decision is required (external scalar -> parameter,
               lookup -> join, text/date function outside the subset).
  UNTRANSLATABLE  no mechanical translation exists at any price.
"""
import re, sys, json, zipfile, collections
import xml.etree.ElementTree as ET

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

# ---------- A1 <-> (col,row) ----------
def col2n(s):
    n=0
    for ch in s: n=n*26+ord(ch.upper())-64
    return n
def n2col(n):
    s=''
    while n: n,r=divmod(n-1,26); s=chr(65+r)+s
    return s

# a reference token: optional 'Sheet'! or Sheet! prefix, $?COL$?ROW, optional :ref
REF = re.compile(r"""
  (?:(?P<sheet>'[^']+'|[A-Za-z_][A-Za-z0-9_.]*)!)?
  (?P<c1>\$?)(?P<col1>[A-Z]{1,3})(?P<r1>\$?)(?P<row1>\d+)
  (?: : (?:(?P<sheet2>'[^']+'|[A-Za-z_][A-Za-z0-9_.]*)!)?
        (?P<c2>\$?)(?P<col2>[A-Z]{1,3})(?P<r2>\$?)(?P<row2>\d+) )?
""", re.X)
STR = re.compile(r'"(?:[^"]|"")*"')
FUNC = re.compile(r'([A-Z][A-Z0-9._]*)\s*\(')

def mask_strings(f):
    """Replace string literals with placeholders so refs inside them are not seen."""
    lits=[]
    def sub(m): lits.append(m.group(0)); return f'\x00{len(lits)-1}\x00'
    return STR.sub(sub, f), lits
def unmask(f, lits):
    return re.sub(r'\x00(\d+)\x00', lambda m: lits[int(m.group(1))], f)

def refs_of(formula):
    body,_=mask_strings(formula)
    return [m for m in REF.finditer(body)]

def to_r1c1(formula, cell):
    """Normalise a formula to R1C1 relative to `cell` (e.g. 'G3')."""
    m=re.match(r'([A-Z]+)(\d+)$', cell); bc, br = col2n(m.group(1)), int(m.group(2))
    body,lits=mask_strings(formula)
    def one(mm):
        out=''
        if mm.group('sheet'): out+=mm.group('sheet')+'!'
        def part(cabs,cs,rabs,rs):
            c=col2n(cs); r=int(rs)
            cc = f'C{c}' if cabs else (f'C[{c-bc}]' if c!=bc else 'C')
            rr = f'R{r}' if rabs else (f'R[{r-br}]' if r!=br else 'R')
            return rr+cc
        out+=part(mm.group('c1'),mm.group('col1'),mm.group('r1'),mm.group('row1'))
        if mm.group('col2'):
            out+=':'
            if mm.group('sheet2'): out+=mm.group('sheet2')+'!'
            out+=part(mm.group('c2'),mm.group('col2'),mm.group('r2'),mm.group('row2'))
        return out
    return unmask(REF.sub(one, body), lits)

# ---------- the .tbl formula subset ----------
PURE = {'IF','ROUND','ABS','MIN','MAX','SUM','AVERAGE','COUNT','TRUE','FALSE',
        'AND','OR','NOT','INT','MOD','SQRT','CEILING','FLOOR','ROUNDUP','ROUNDDOWN'}
AGG  = {'SUM':'sum','AVERAGE':'avg','COUNT':'count','MIN':'min','MAX':'max','COUNTA':'count'}
VOLATILE = {'NOW','TODAY','RAND','RANDBETWEEN','OFFSET','INDIRECT','CELL','INFO'}
LOOKUP   = {'VLOOKUP','HLOOKUP','XLOOKUP','INDEX','MATCH','LOOKUP'}
TEXTFN   = {'TEXT','CONCATENATE','LEFT','RIGHT','MID','TRIM','UPPER','LOWER','SUBSTITUTE','DATE','YEAR','MONTH','DAY','EOMONTH','DATEDIF'}
COND     = {'SUMIF','SUMIFS','COUNTIF','COUNTIFS','AVERAGEIF','AVERAGEIFS'}

import os
CEILING = os.environ.get('GWS_CEILING')=='1'   # allow ANY function; test ADDRESSING only

def _ambiguous(expr, headers):
    """Names in `expr` that more than one column of this header carries.

    A translation onto such a name does not resolve: the reader cannot tell
    which column was meant. `translate` used to return CLEAN for these, so
    "mechanically translatable" counted expressions that no evaluator can
    evaluate -- the differential caught them downstream as
    `exc.duplicate-header-name`, 5,994 cells from a single sheet, and the
    verdict upstream still said CLEAN.
    """
    if expr is None:
        return []
    seen, dup = set(), set()
    for n in headers.values():
        if n in seen:
            dup.add(n)
        seen.add(n)
    if not dup:
        return []
    used = set(re.findall(r'[^\W\d]\w*|\d[\w.]*', expr))
    return sorted(dup & used)


def translate(formula, cell, sheet, headers, data_rows, sheets_seen):
    """headers: {col_number: name} for this sheet. data_rows: (first,last) inclusive."""
    f = formula.replace('&gt;','>').replace('&lt;','<').replace('&amp;','&').replace('&quot;','"')
    m=re.match(r'([A-Z]+)(\d+)$', cell); bc,br = col2n(m.group(1)), int(m.group(2))
    # --- structured references (an Excel Table): the inverse of our own export ---
    SR_ROW = re.compile(r"[A-Za-z_][\w.]*\[(?:\[#This Row\],)?\[?([^\]\[]+)\]?\]")
    if '[' in f and re.search(r'[A-Za-z_][\w.]*\[', f):
        names=set(headers.values())
        g=f
        bad=[]
        def srsub(mm):
            nm=re.sub(r'\W','_',mm.group(1).strip())
            if nm in names: return nm
            bad.append(mm.group(0)); return mm.group(0)
        g2=re.sub(r"[A-Za-z_][\w.]*\[\[#This Row\],\[([^\]]+)\]\]", srsub, f)
        g2=re.sub(r"[A-Za-z_][\w.]*\[@\[?([^\]\[]+)\]?\]", srsub, g2)
        whole_col=re.findall(r"[A-Za-z_][\w.]*\[([^\]\[@#]+)\]", g2)
        if bad:
            return ('NEEDS-HUMAN', None, f'structured reference(s) {bad[:2]} name no column of this table')
        if whole_col:
            fn0=(FUNC.findall(g2.upper()) or [None])[0]
            base=fn0 and AGG.get(fn0.replace('SUBTOTAL','SUM'))
            m2=re.fullmatch(r'\s*SUBTOTAL\(\s*(\d+)\s*,\s*[A-Za-z_][\w.]*\[([^\]]+)\]\s*\)\s*', g2, re.I)
            SUB={109:'sum',9:'sum',101:'avg',1:'avg',103:'count',3:'count',105:'min',5:'min',104:'max',4:'max'}
            if m2 and int(m2.group(1)) in SUB:
                cn=re.sub(r'\W','_',m2.group(2).strip())
                if cn in names: return ('AGGREGATE', f'{SUB[int(m2.group(1))]}({cn})', 'totals row SUBTOTAL')
            m3=re.fullmatch(r'\s*([A-Z]+)\(\s*[A-Za-z_][\w.]*\[([^\]]+)\]\s*\)\s*', g2, re.I)
            if m3 and m3.group(1).upper() in AGG:
                cn=re.sub(r'\W','_',m3.group(2).strip())
                if cn in names: return ('AGGREGATE', f'{AGG[m3.group(1).upper()]}({cn})', 'whole-column aggregate')
            return ('NEEDS-HUMAN', None, f'whole-column structured reference {whole_col[:2]} is not a plain aggregate')
        if g2 != f:
            # every structured reference resolved to a named column of this table:
            # the formula IS already in named-column form.
            funcs2=set(FUNC.findall(g2.upper()))
            if funcs2 - (funcs2 if CEILING else PURE):
                return ('NEEDS-HUMAN', None, f'function(s) {sorted(funcs2-PURE)} not in the .tbl subset')
            amb = _ambiguous(g2, headers)
            if amb:
                return ('NEEDS-HUMAN', None,
                        f'name(s) {amb} are carried by more than one column of this header')
            return ('CLEAN', g2.strip(), '')
        f=g2
    funcs = set(FUNC.findall(f.upper()))
    body,lits = mask_strings(f)
    rs = list(REF.finditer(body))
    reasons=[]
    # --- hard blocks ---
    if funcs & VOLATILE:
        return ('UNTRANSLATABLE', None, f'volatile/dynamic-reference function {sorted(funcs & VOLATILE)}')
    if EXT:
        r = ext_translate(f, cell, sheet, headers, data_rows)
        if r is not None: return r
    for mm in rs:
        if mm.group('sheet'):
            return ('UNTRANSLATABLE', None, f"cross-sheet reference {mm.group(0)!r}: .tbl has no cross-sheet address")
    # --- aggregate shape: one whole-column range over exactly the data rows ---
    if len(rs)==1 and rs[0].group('col2') and rs[0].group(0)==body.strip().split('(',1)[-1].rstrip(')') if False else False:
        pass
    if len(rs)==1 and rs[0].group('col2'):
        mm=rs[0]
        c1,c2=col2n(mm.group('col1')),col2n(mm.group('col2'))
        r1,r2=int(mm.group('row1')),int(mm.group('row2'))
        fn=(FUNC.findall(f.upper()) or [None])[0]
        whole = re.fullmatch(r'\s*[A-Z]+\s*\(\s*'+re.escape(mm.group(0))+r'\s*\)\s*', body, re.I)
        if whole and fn in AGG and c1==c2 and (r1,r2)==data_rows and br not in range(r1,r2+1):
            name=headers.get(c1)
            if name: return ('AGGREGATE', f'{AGG[fn]}({name})', f'{fn} over the whole of column {name}')
            return ('NEEDS-HUMAN', None, 'aggregate over an unnamed column')
        if c1!=c2 and r1!=r2:
            return ('UNTRANSLATABLE', None, f'2-D range {mm.group(0)!r}: not a column')
    # --- per-row column formula: every ref must be same-row relative, same sheet ---
    if CEILING:
        LOOKUP_, COND_, TEXTFN_, PURE_ = set(), set(), set(), funcs
    else:
        LOOKUP_, COND_, TEXTFN_, PURE_ = LOOKUP, COND, TEXTFN, PURE
    if funcs & LOOKUP_:
        return ('NEEDS-HUMAN', None, f'{sorted(funcs & LOOKUP_)} is a JOIN; .tbl has no join vocabulary')
    if funcs & COND_:
        return ('NEEDS-HUMAN', None, f'{sorted(funcs & COND_)} is a filtered aggregate over other rows')
    if funcs & TEXTFN_:
        return ('NEEDS-HUMAN', None, f'{sorted(funcs & TEXTFN_)} outside the total/pure subset')
    unknown = funcs - PURE_
    if unknown:
        return ('NEEDS-HUMAN', None, f'function(s) {sorted(unknown)} not in the .tbl subset')
    if not rs:
        return ('NEEDS-HUMAN', None, 'constant formula, no references')
    out=body; widened=False
    for mm in reversed(rs):
        if mm.group('col2'):
            r1,r2=int(mm.group('row1')),int(mm.group('row2'))
            c1,c2=col2n(mm.group('col1')),col2n(mm.group('col2'))
            if r1!=br or r2!=br:
                return ('UNTRANSLATABLE', None,
                        f'range {mm.group(0)!r} spans rows other than this one; row order is not addressable')
            if c1!=c2:
                # a horizontal range in this row: expand to the list of column names.
                names=[headers.get(c) for c in range(min(c1,c2),max(c1,c2)+1)]
                if any(n is None for n in names):
                    return ('NEEDS-HUMAN', None,
                            f'horizontal range {mm.group(0)!r} covers a column with no header name')
                widened=True
                out=out[:mm.start()]+', '.join(names)+out[mm.end():]
                continue
        row=int(mm.group('row1'))
        if mm.group('r1')=='$' or row!=br:
            return ('UNTRANSLATABLE', None,
                    f'reference {mm.group(0)!r} is anchored to row {row}, not this row')
        c=col2n(mm.group('col1'))
        name=headers.get(c)
        if not name:
            return ('NEEDS-HUMAN', None, f'column {n2col(c)} has no header name')
        out=out[:mm.start()]+name+out[mm.end():]
    out=unmask(out,lits)
    if widened:
        return ('CLEAN-WIDE', out.strip(),
                'translates, but the source is WIDE: the row-wise range became an explicit '
                'column list, which the .tbl long/tidy rule says should have been a long table')
    amb = _ambiguous(out, headers)
    if amb:
        return ('NEEDS-HUMAN', None,
                f'name(s) {amb} are carried by more than one column of this header')
    return ('CLEAN', out.strip(), '')

# ---------- workbook reader ----------
def read_workbook(path):
    z=zipfile.ZipFile(path)
    wb=ET.fromstring(z.read('xl/workbook.xml'))
    rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rmap={r.get('Id'):r.get('Target') for r in rels}
    sst=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')):
            sst.append(''.join(t.text or '' for t in si.iter(f'{{{NS["m"]}}}t')))
    sheets=[]
    for sh in wb.iter(f'{{{NS["m"]}}}sheet'):
        tgt=rmap[sh.get(f'{{{NS["r"]}}}id')].lstrip('/')
        if not tgt.startswith('xl/'): tgt='xl/'+tgt
        sheets.append((sh.get('name'), tgt))
    return z, sst, sheets, wb

BUILTIN_DATE = set(range(14,23)) | set(range(45,48)) | {27,30,36,50,57}
def style_datemap(z):
    """style index -> True if its number format renders a DATE."""
    if 'xl/styles.xml' not in z.namelist(): return {}
    root=ET.fromstring(z.read('xl/styles.xml'))
    custom={}
    for nf in root.iter(f'{{{NS["m"]}}}numFmt'):
        code=nf.get('formatCode') or ''
        stripped=re.sub(r'"[^"]*"','',code); stripped=re.sub(r'\\.','',stripped)
        custom[int(nf.get('numFmtId'))]= bool(re.search(r'[ymdhs]', stripped, re.I)) and 'General' not in code
    out={}
    cx=root.find(f'{{{NS["m"]}}}cellXfs')
    if cx is None: return {}
    for i,xf in enumerate(cx):
        nid=int(xf.get('numFmtId') or 0)
        out[i]= custom.get(nid, nid in BUILTIN_DATE)
    return out

def serial_to_iso(v):
    import datetime
    try: f=float(v)
    except Exception: return None
    if f < 1 or f > 2958465: return None
    d=int(f)
    if d >= 60: d -= 1          # Excel's 1900 leap-year bug
    base=datetime.date(1899,12,31)
    try: dt=base+datetime.timedelta(days=d)
    except Exception: return None
    frac=f-int(f)
    if frac > 1e-9:
        secs=round(frac*86400)
        return f'{dt.isoformat()}T{secs//3600:02d}:{secs%3600//60:02d}:{secs%60:02d}'
    return dt.isoformat()

def sheet_cells(z, sst, target):
    root=ET.fromstring(z.read(target))
    dm=style_datemap(z)
    cells={}
    for c in root.iter(f'{{{NS["m"]}}}c'):
        ref=c.get('r'); t=c.get('t')
        fe=c.find(f'{{{NS["m"]}}}f'); ve=c.find(f'{{{NS["m"]}}}v')
        val=ve.text if ve is not None else None
        if t=='s' and val is not None: val=sst[int(val)]
        if t=='inlineStr':
            ise=c.find(f'{{{NS["m"]}}}is')
            if ise is not None: val=''.join(x.text or '' for x in ise.iter(f'{{{NS["m"]}}}t'))
        isdate=False
        if val is not None and t in (None,'n') and dm.get(int(c.get('s') or 0)):
            iso=serial_to_iso(val)
            if iso: val, isdate = iso, True
        cells[ref]=dict(isdate=isdate, f=(fe.text if fe is not None else None),
                        ft=(fe.get('t') if fe is not None else None),
                        fref=(fe.get('ref') if fe is not None else None),
                        v=val, t=t)
    return root, cells

# ===========================================================================
# EXTENDED GRAMMAR (X6-joins): filtered aggregates and cross-table lookup.
#   name := fn(col where pcol = "literal")
#   col  = lookup(other.tbl, keycol, valcol)
# Enabled with GWS_EXT=1 so that before/after run through the SAME code path.
# ===========================================================================
EXT = os.environ.get('GWS_EXT') == '1'
WB = {}                 # sheet name -> {'g':grid, 'hdr':{col:name}, 'drange':(r1,r2)}
STATS = None            # collections.Counter, set by the harness

def _S(k, n=1):
    if STATS is not None: STATS[k] += n

_UNIQ_CACHE = {}
def _is_key(sheet, col, r1, r2):
    """Would this column serve as a declared key: total and unique over the rows."""
    ck = (sheet, col, r1, r2)
    if ck in _UNIQ_CACHE: return _UNIQ_CACHE[ck]
    s = WB.get(sheet)
    if not s: _UNIQ_CACHE[ck] = None; return None
    g = s['g']; vals = []
    for r in range(r1, r2 + 1):
        d = g.get(r, {}).get(col)
        v = (d or {}).get('v')
        if v is None or str(v).strip() == '':
            continue                       # blank rows inside a range are common
        vals.append(str(v).strip())
    res = bool(vals) and len(set(vals)) == len(vals)
    _UNIQ_CACHE[ck] = res
    return res

EXTWB = re.compile(r"^\s*\[\d+\]|^\s*'\[\d+\]")
WHOLECOL = re.compile(r"""
   ^\s*(?:(?P<wb>\[\d+\]))?
   (?:(?P<sheet>'[^']+'|[A-Za-z_][A-Za-z0-9_.]*)!)?
   \$?(?P<col1>[A-Z]{1,3})\s*:\s*(?:(?:'[^']+'|[A-Za-z_][A-Za-z0-9_.]*)!)?\$?(?P<col2>[A-Z]{1,3})\s*$""", re.X)

def _parse_range(arg, cur_sheet):
    """Accepts A1 ranges AND whole-column ranges (Sheet!A:B), which are the
    dominant real VLOOKUP shape. Returns (sheet,c1,c2,r1,r2) with r1/r2 = None
    for a whole column, or ('EXTERNAL',) for a link to another workbook file."""
    a = arg.strip()
    if EXTWB.match(a) or a.startswith("'["): return ('EXTERNAL',)
    m = REF.fullmatch(a)
    if m:
        return _rng(m, cur_sheet)
    w = WHOLECOL.match(a)
    if w:
        sh = w.group('sheet'); sh = sh.strip("'") if sh else cur_sheet
        c1, c2 = col2n(w.group('col1')), col2n(w.group('col2'))
        return (sh, min(c1,c2), max(c1,c2), None, None)
    return None

def _rng(mm, cur_sheet):
    """A REF match -> (sheet, c1, c2, r1, r2) or None."""
    sh = mm.group('sheet')
    sh = sh.strip("'") if sh else cur_sheet
    c1 = col2n(mm.group('col1')); r1 = int(mm.group('row1'))
    if mm.group('col2'):
        c2 = col2n(mm.group('col2')); r2 = int(mm.group('row2'))
    else:
        c2, r2 = c1, r1
    return (sh, min(c1, c2), max(c1, c2), min(r1, r2), max(r1, r2))

def _colname(sheet, c):
    s = WB.get(sheet)
    return s['hdr'].get(c) if s else None

def _same_row_ref(mm, br, cur_sheet, headers):
    """A plain relative same-row single-cell ref -> its column name, else None."""
    if mm.group('sheet') or mm.group('col2'): return None
    if mm.group('r1') == '$': return None
    if int(mm.group('row1')) != br: return None
    return headers.get(col2n(mm.group('col1')))

def _tblname(sheet):
    return re.sub(r'\W', '_', sheet) + '.tbl'

_CMP = re.compile(r'^\s*(>=|<=|<>|>|<|=)')
_WILD = re.compile(r'[*?]')
_AGGIF = {'SUMIF':'sum','SUMIFS':'sum','COUNTIF':'count','COUNTIFS':'count',
          'AVERAGEIF':'avg','AVERAGEIFS':'avg','MINIFS':'min','MAXIFS':'max'}

def _split_args(s):
    """Top-level comma split, respecting parens and the string placeholders."""
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == '(': depth += 1
        elif ch == ')': depth -= 1
        if ch == ',' and depth == 0: out.append(cur); cur = ''
        else: cur += ch
    out.append(cur)
    return [a.strip() for a in out]

def ext_translate(f, cell, sheet, headers, data_rows):
    """Try the extended grammar. Returns (verdict, expr, why) or None to fall through."""
    if not EXT: return None
    m = re.match(r'([A-Z]+)(\d+)$', cell); bc, br = col2n(m.group(1)), int(m.group(2))
    body, lits = mask_strings(f)
    top = re.fullmatch(r'\s*([A-Z][A-Z0-9.]*)\s*\((.*)\)\s*', body, re.I)
    if not top: return None
    fn = top.group(1).upper()
    args = _split_args(top.group(2))
    lit = lambda a: unmask(a, lits)

    # ---------- filtered aggregate: SUMIF / COUNTIF / SUMIFS / ... ----------
    if fn in _AGGIF:
        _S('ifagg.total')
        inside = data_rows[0] <= br <= data_rows[1]
        if fn.endswith('IFS') and fn not in ('MINIFS','MAXIFS'):
            if len(args) < 3: return None
            sum_a, pairs = args[0], args[1:]
        elif fn in ('MINIFS','MAXIFS'):
            if len(args) < 3: return None
            sum_a, pairs = args[0], args[1:]
        elif fn == 'COUNTIF':
            if len(args) != 2: return None
            sum_a, pairs = args[0], args
        else:                                   # SUMIF / AVERAGEIF
            if len(args) < 2: return None
            sum_a = args[2] if len(args) > 2 else args[0]
            pairs = args[:2]
        if len(pairs) != 2:
            _S('ifagg.multi-predicate')
            return ('NEEDS-HUMAN', None,
                    f'{fn} with {len(pairs)//2} predicates: the grammar has one '
                    '`where col = "lit"` and no conjunction')
        crit_a, crit_v = pairs[0], pairs[1]
        cr = _parse_range(crit_a, sheet); sr = _parse_range(sum_a, sheet)
        if cr is None or sr is None:
            _S('ifagg.range-not-a-plain-ref'); return None
        if cr[0]=='EXTERNAL' or sr[0]=='EXTERNAL':
            _S('ifagg.external-workbook')
            return ('UNTRANSLATABLE', None, f'{fn} range is in another workbook file')
        if cr[0] != sheet or sr[0] != sheet:
            _S('ifagg.cross-sheet')
            return ('UNTRANSLATABLE', None,
                    f'{fn} over another sheet: the grammar aggregates over THIS table only')
        if cr[1] != cr[2] or sr[1] != sr[2]:
            _S('ifagg.horizontal-range')
            return ('UNTRANSLATABLE', None,
                    f'{fn} over a range spanning SEVERAL COLUMNS of one row: a wide-table '
                    'row-wise count, which has no long-form aggregate')
        pcol, scol = _colname(sheet, cr[1]), _colname(sheet, sr[1])
        if not pcol or not scol:
            _S('ifagg.unnamed-column')
            return ('NEEDS-HUMAN', None, f'{fn} over a column with no header name')
        # the criterion
        cv = crit_v.strip()
        smatch = re.fullmatch(r'\x00(\d+)\x00', cv)
        if smatch:
            s = lits[int(smatch.group(1))][1:-1]
            if _CMP.match(s):
                _S('ifagg.comparison-criterion')
                return ('NEEDS-HUMAN', None,
                        f'{fn} criterion {s!r} is a COMPARISON; the grammar has only `= "literal"`')
            if _WILD.search(s):
                _S('ifagg.wildcard-criterion')
                return ('NEEDS-HUMAN', None,
                        f'{fn} criterion {s!r} uses a WILDCARD; the grammar has only equality')
            if inside:
                _S('ifagg.grouped-literal')
                return ('NEEDS-HUMAN', None,
                        f'{fn} inside the data region is a PER-ROW group aggregate, '
                        'not a table scalar; the grammar has no group-by')
            _S('ifagg.CLEAN')
            return ('AGGREGATE-FILTER', f'{_AGGIF[fn]}({scol} where {pcol} = "{s}")', '')
        rm = REF.fullmatch(cv)
        if rm:
            nm = _same_row_ref(rm, br, sheet, headers)
            _S('ifagg.criterion-is-cell-ref')
            return ('NEEDS-HUMAN', None,
                    f'{fn} criterion is a CELL REFERENCE ({cv})'
                    + (f' = this row\'s {nm}' if nm else '')
                    + ': a per-row GROUP aggregate; the grammar has no group-by')
        if re.fullmatch(r'-?\d+(\.\d+)?', cv):
            _S('ifagg.numeric-literal-criterion')
            return ('NEEDS-HUMAN', None,
                    f'{fn} criterion is the number {cv}; the grammar quotes a string literal '
                    '(equality on a numeric column is unspecified)')
        _S('ifagg.computed-criterion')
        return ('NEEDS-HUMAN', None, f'{fn} criterion {cv!r} is a computed expression')

    # ---------- cross-table lookup ----------
    if fn in ('VLOOKUP', 'XLOOKUP', 'HLOOKUP'):
        _S('lk.total'); _S('lk.fn.' + fn)
        if fn == 'HLOOKUP':
            _S('lk.hlookup')
            return ('UNTRANSLATABLE', None, 'HLOOKUP indexes by ROW: a wide-table operation')
        if fn == 'VLOOKUP':
            if len(args) < 3: _S('lk.arity'); return None
            lv, ta, idx = args[0], args[1], args[2]
            approx = (len(args) < 4) or (args[3].strip().upper() not in ('FALSE','0'))
            if approx:
                _S('lk.approximate')
                return ('UNTRANSLATABLE', None,
                        'VLOOKUP is APPROXIMATE-match (4th arg TRUE/omitted): a range lookup '
                        'over sorted data, not a key lookup')
            if not re.fullmatch(r'\d+', idx.strip()):
                _S('lk.index-not-literal')
                return ('NEEDS-HUMAN', None, f'VLOOKUP column index {idx.strip()!r} is computed')
            k = int(idx.strip())
            tr = _parse_range(ta, sheet)
            if tr is None: _S('lk.table-not-a-range'); return None
            if tr[0] == 'EXTERNAL':
                _S('lk.external-workbook')
                return ('UNTRANSLATABLE', None,
                        'VLOOKUP target is a link to ANOTHER WORKBOOK FILE ([n]Sheet!...): '
                        'the referenced artifact is not in this migration')
            tsheet, c1, c2, r1, r2 = tr
            keycol_n, valcol_n = c1, c1 + k - 1
            if valcol_n > c2: _S('lk.index-out-of-range'); return ('NEEDS-HUMAN', None,
                'VLOOKUP column index falls outside the table range')
        else:                                    # XLOOKUP(lv, key_range, ret_range, ...)
            if len(args) < 3: _S('lk.arity'); return None
            lv = args[0]
            kr = _parse_range(args[1], sheet); vr = _parse_range(args[2], sheet)
            if kr is None or vr is None: _S('lk.table-not-a-range'); return None
            if kr[0]=='EXTERNAL' or vr[0]=='EXTERNAL':
                _S('lk.external-workbook')
                return ('UNTRANSLATABLE', None, 'XLOOKUP target is in another workbook file')
            if kr[0] != vr[0]: _S('lk.split-sheets'); return None
            tsheet = kr[0]
            r1 = None if kr[3] is None or vr[3] is None else min(kr[3], vr[3])
            r2 = None if kr[4] is None or vr[4] is None else max(kr[4], vr[4])
            keycol_n, valcol_n = kr[1], vr[1]
            c1, c2 = min(keycol_n, valcol_n), max(keycol_n, valcol_n)
        lvm = REF.fullmatch(lv.strip())
        if not lvm: _S('lk.key-not-a-ref'); return None
        kname = _same_row_ref(lvm, br, sheet, headers)
        if not kname:
            _S('lk.key-not-same-row')
            return ('UNTRANSLATABLE', None,
                    f'lookup key {lv.strip()!r} is not a same-row relative reference')
        if tsheet not in WB:
            _S('lk.target-unresolvable')
            return ('NEEDS-HUMAN', None, f'lookup target sheet {tsheet!r} not resolvable')
        tdr = WB[tsheet]['drange']
        if r1 is None or r2 is None: rr1, rr2 = tdr
        else:
            rr1, rr2 = max(r1, tdr[0]), (tdr[1] if r2 >= 1048570 else min(r2, tdr[1]))
        if rr2 < rr1: rr1, rr2 = tdr
        vname = _colname(tsheet, valcol_n)
        if not vname:
            _S('lk.value-column-unnamed')
            return ('NEEDS-HUMAN', None,
                    f'lookup returns column {n2col(valcol_n)} of {tsheet!r}, which has no header name')
        isk = _is_key(tsheet, keycol_n, rr1, rr2)
        if isk is not True:
            _S('lk.first-column-not-a-key')
            return ('NEEDS-HUMAN', None,
                    f'the looked-up column {n2col(keycol_n)} of {tsheet!r} is NOT unique over the '
                    'target rows, so it cannot be that table\'s declared key')
        _S('lk.CLEAN')
        return ('CLEAN-LOOKUP', f'lookup({_tblname(tsheet)}, {kname}, {vname})', '')

    # ---------- INDEX(ret, MATCH(key, keyrange, 0)) ----------
    if fn == 'INDEX':
        _S('lk.total'); _S('lk.fn.INDEX')
        if len(args) != 2: _S('lk.index-arity'); return None
        mm2 = re.fullmatch(r'\s*MATCH\s*\((.*)\)\s*', args[1], re.I)
        if not mm2: _S('lk.index-without-match'); return None
        margs = _split_args(mm2.group(1))
        if len(margs) < 2: _S('lk.index-arity'); return None
        if len(margs) < 3 or margs[2].strip() not in ('0',):
            _S('lk.match-not-exact')
            return ('UNTRANSLATABLE', None,
                    'MATCH type is not 0: an approximate/sorted match, not a key lookup')
        lvm = REF.fullmatch(margs[0].strip())
        rr = _parse_range(args[0], sheet); kk = _parse_range(margs[1], sheet)
        if not (rr and kk and lvm): _S('lk.index-shape'); return None
        if rr[0]=='EXTERNAL' or kk[0]=='EXTERNAL':
            _S('lk.external-workbook')
            return ('UNTRANSLATABLE', None, 'INDEX/MATCH target is in another workbook file')
        if rr[0] != kk[0]: _S('lk.split-sheets'); return None
        kname = _same_row_ref(lvm, br, sheet, headers)
        if not kname:
            _S('lk.key-not-same-row')
            return ('UNTRANSLATABLE', None, 'INDEX/MATCH key is not a same-row relative reference')
        tsheet = rr[0]
        if tsheet not in WB:
            _S('lk.target-unresolvable')
            return ('NEEDS-HUMAN', None, f'lookup target sheet {tsheet!r} not resolvable')
        if rr[1] != rr[2] or kk[1] != kk[2]:
            _S('lk.2d'); return ('UNTRANSLATABLE', None, 'INDEX/MATCH over a 2-D range')
        vname = _colname(tsheet, rr[1])
        if not vname:
            _S('lk.value-column-unnamed')
            return ('NEEDS-HUMAN', None, 'INDEX/MATCH return column has no header name')
        tdr = WB[tsheet]['drange']
        kr1 = tdr[0] if kk[3] is None else max(kk[3], tdr[0])
        kr2 = tdr[1] if (kk[4] is None or kk[4] >= 1048570) else min(kk[4], tdr[1])
        if kr2 < kr1: kr1, kr2 = tdr
        if _is_key(tsheet, kk[1], kr1, kr2) is not True:
            _S('lk.first-column-not-a-key')
            return ('NEEDS-HUMAN', None,
                    f'the matched column {n2col(kk[1])} of {tsheet!r} is not unique: not a key')
        _S('lk.CLEAN')
        return ('CLEAN-LOOKUP', f'lookup({_tblname(tsheet)}, {kname}, {vname})', '')
    return None

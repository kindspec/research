#!/usr/bin/env python3
"""CSV <-> .tbl import/export with a loud-failure report (I3/I7).

Import policy, by construction:
  - every non-fatal deviation is recorded in a REPORT, never silently applied
  - anything that could change a computed VALUE is a REJECT
  - anything that could only lose DECORATION is a WARN
"""
import csv, io, re, sys, json, hashlib, unicodedata, argparse

# ---------- diagnostics ----------
class Report:
    def __init__(self): self.items=[]
    def add(self, sev, code, where, msg): self.items.append((sev,code,where,msg))
    def rejects(self): return [i for i in self.items if i[0]=='REJECT']
    def dump(self, fh=sys.stderr):
        for s,c,w,m in self.items: print(f'{s:6} {c:22} {w:18} {m}', file=fh)
        print(f'-- {len(self.rejects())} REJECT, '
              f'{sum(1 for i in self.items if i[0]=="WARN")} WARN, '
              f'{sum(1 for i in self.items if i[0]=="NOTE")} NOTE', file=fh)

# ---------- decoding ----------
def decode(raw, rep):
    if raw.startswith(b'\xef\xbb\xbf'):
        rep.add('NOTE','bom-stripped','file','UTF-8 BOM stripped (C4: no BOM)'); raw=raw[3:]
    try:
        t = raw.decode('utf-8')
    except UnicodeDecodeError as e:
        rep.add('REJECT','not-utf8','file',f'byte {e.start}: {e.reason}; declare an encoding to import')
        return None
    if '\r\n' in t: rep.add('NOTE','crlf-normalised','file','CRLF -> LF (C4)')
    n = unicodedata.normalize('NFC', t)
    if n != t: rep.add('NOTE','nfc-normalised','file','NFD -> NFC (C4)')
    return n

# ---------- type / value inference ----------
DATE_PATS = [
 (r'^(\d{4})-(\d{2})-(\d{2})$','iso'),
 (r'^(\d{2})/(\d{2})/(\d{4})$','ambiguous-dmy-mdy'),
 (r'^(\d{4})/(\d{2})/(\d{2})$','iso-slash'),
 (r'^([A-Z][a-z]{2}) (\d{1,2}) (\d{4})$','mon-d-y'),
 (r'^(\d{1,2})-([A-Z][a-z]{2})-(\d{2})$','d-mon-yy'),
]
NUM_PLAIN   = re.compile(r'^-?\d+(\.\d+)?$')
NUM_THOU    = re.compile(r'^-?\d{1,3}(,\d{3})+(\.\d+)?$')
NUM_DECCOMMA= re.compile(r'^-?\d{1,3}(\.\d{3})+(,\d+)?$|^-?\d+,\d+$')
NUM_PAREN   = re.compile(r'^\(\s*[\d,]+(\.\d+)?\s*\)$')
NUM_SCI     = re.compile(r'^-?\d+(\.\d+)?[eE][+-]?\d+$')
LEADZERO    = re.compile(r'^0\d+$')
FORMULAISH  = re.compile(r'^[=+\-@]')

def classify(v, col, rowno, rep):
    """Return (kind, canonical_text). Ambiguity that could change a VALUE -> REJECT."""
    s = v
    if s == '': return ('empty','')
    if LEADZERO.fullmatch(s):
        rep.add('NOTE','leading-zero',f'{col}:{rowno}',f'{s!r} kept as text (leading zero is data)')
        return ('text', s)
    if NUM_PLAIN.fullmatch(s): return ('number', s)
    if NUM_SCI.fullmatch(s):
        rep.add('NOTE','sci-notation',f'{col}:{rowno}',f'{s!r} kept verbatim, parsed as number')
        return ('number', s)
    if NUM_THOU.fullmatch(s):
        rep.add('WARN','thousands-sep',f'{col}:{rowno}',f'{s!r} -> {s.replace(",","")} (grouping is presentation)')
        return ('number', s.replace(',',''))
    if NUM_DECCOMMA.fullmatch(s):
        rep.add('REJECT','decimal-comma',f'{col}:{rowno}',
                f'{s!r} is 1234.50 under de-DE and 1.23450 under en-US -- ambiguous VALUE, declare a locale')
        return ('reject', s)
    if NUM_PAREN.fullmatch(s):
        rep.add('WARN','accounting-negative',f'{col}:{rowno}',f'{s!r} -> -{s.strip("()").replace(",","")}')
        return ('number', '-'+s.strip('() ').replace(',',''))
    hits=[n for p,n in DATE_PATS if re.fullmatch(p,s)]
    if hits:
        if 'ambiguous-dmy-mdy' in hits:
            rep.add('REJECT','ambiguous-date',f'{col}:{rowno}',
                    f'{s!r} is 5 Jan under en-GB and 1 May under en-US -- declare a date order')
            return ('reject', s)
        rep.add('NOTE','date',f'{col}:{rowno}',f'{s!r} recognised as {hits[0]}, stored verbatim as text')
        return ('date', s)
    if s == '-':
        rep.add('WARN','excel-dash-null',f'{col}:{rowno}',"Excel '-' read as EMPTY, not the string '-'")
        return ('empty','')
    if FORMULAISH.match(s):
        rep.add('WARN','formula-looking-cell',f'{col}:{rowno}',
                f'{s!r} begins with =+-@; stored as literal text (a .tbl cell can never be a formula)')
        return ('text', s)
    return ('text', s)

# ---------- .tbl cell escaping ----------
def cell_ok(s, col, rowno, rep):
    if '\n' in s or '\r' in s:
        rep.add('REJECT','embedded-newline',f'{col}:{rowno}',
                'cell contains a newline; one-row-per-line is the merge invariant (I6) and cannot hold it')
        return False
    if '|' in s:
        rep.add('WARN','pipe-escaped',f'{col}:{rowno}','| escaped as \\|')
    return True
def esc(s): return s.replace('\\','\\\\').replace('|','\\|')
def unesc(s): return re.sub(r'\\(.)', r'\1', s)
def split_row(line):
    out, cur, i = [], '', 0
    line = line.strip()
    if line.startswith('|'): line = line[1:]
    if line.endswith('|'): line = line[:-1]
    while i < len(line):
        c = line[i]
        if c == '\\' and i+1 < len(line): cur += line[i:i+2]; i += 2; continue
        if c == '|': out.append(cur.strip()); cur=''; i+=1; continue
        cur += c; i += 1
    out.append(cur.strip())
    return [unesc(c) for c in out]

# ---------- row ids ----------
def mint(seed):
    return 'r_' + hashlib.blake2s(seed.encode(), digest_size=3).hexdigest()

# ---------- import ----------
def csv2tbl(raw, key=None, prev=None, formulas=None, aggs=None, name='src'):
    rep = Report()
    text = decode(raw, rep)
    if text is None: return None, rep
    rdr = csv.reader(io.StringIO(text))
    recs = list(rdr)
    if not recs: rep.add('REJECT','empty-file','file','no rows'); return None, rep
    header = [h.strip() for h in recs[0]]
    for h in header:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', h):
            rep.add('WARN','header-not-identifier',h,'renamed to a NFC identifier so it can appear in a formula')
    hdr = [re.sub(r'\W','_',h) or f'c{i}' for i,h in enumerate(header)]
    if len(set(hdr)) != len(hdr):
        rep.add('REJECT','duplicate-column','header',f'{hdr} -- a formula name would be ambiguous')
    rows=[]
    for n, r in enumerate(recs[1:], 2):
        if len(r) != len(hdr):
            rep.add('REJECT','ragged-row',f'row {n}',
                    f'{len(r)} fields, header has {len(hdr)} -- no defensible fill')
            continue
        d={}
        bad=False
        for c,v in zip(hdr,r):
            kind, val = classify(v.strip(), c, n, rep)
            if kind=='reject': bad=True
            if not cell_ok(val, c, n, rep): bad=True
            d[c]=val
        if not bad: rows.append(d)
    # ---- row identity ----
    rows, idrep = assign_ids(rows, hdr, key, prev, name)
    rep.items += idrep
    return render(hdr, rows, key, formulas or {}, aggs or {}), rep

def assign_ids(rows, hdr, key, prev, name):
    """prev: (cols, rows) already-parsed previous .tbl, or None."""
    rep=[]
    prev_by_key, prev_by_content, used = {}, {}, set()
    if prev:
        pcols, prows = prev
        for pr in prows:
            if key and key in pr: prev_by_key.setdefault(pr[key], pr['id'])
            sig = content_sig(pr, [c for c in pcols if c!='id'])
            prev_by_content.setdefault(sig, []).append(pr['id'])
    stats = dict(carried=0, by_key=0, by_content=0, minted=0)
    for i, r in enumerate(rows):
        rid=None
        if 'id' in r and r['id'].startswith('r_'):          # tier 0: id carriage
            rid = r['id']; stats['carried']+=1
        elif key and key in r and r[key] in prev_by_key:     # tier 1: declared natural key
            rid = prev_by_key[r[key]]; stats['by_key']+=1
        else:
            sig = content_sig(r, hdr)                        # tier 2: exact content match
            cands=[c for c in prev_by_content.get(sig,[]) if c not in used]
            if cands: rid=cands[0]; stats['by_content']+=1
        if rid is None or rid in used:
            base = r.get(key) if key and r.get(key) else content_sig(r,hdr)
            rid = mint(f'{name}\x00{base}\x00{i}')
            k=0
            while rid in used: k+=1; rid = mint(f'{name}\x00{base}\x00{i}\x00{k}')
            stats['minted']+=1
        used.add(rid); r['id']=rid
    rep.append(('NOTE','row-ids','identity',
        f"carried={stats['carried']} by_key={stats['by_key']} "
        f"by_content={stats['by_content']} minted={stats['minted']}"))
    if not key and not prev:
        rep.append(('WARN','no-natural-key','identity',
            'no key declared: ids are minted from content+position and are stable only '
            'while this .tbl is the source of truth (see re-import policy)'))
    return rows, rep

def content_sig(r, cols):
    return hashlib.blake2s('\x00'.join(r.get(c,'') for c in cols if c!='id').encode(),
                           digest_size=8).hexdigest()

def render(hdr, rows, key, formulas, aggs):
    cols = ['id'] + [c for c in hdr if c!='id'] + [c for c in formulas if c not in hdr]
    heads = ['id'] + [(f'{c} = {formulas[c]}' if c in formulas else c) for c in cols[1:]]
    widths = [max(len(h), *(len(esc(r.get(c,''))) for r in rows)) if rows else len(h)
              for h,c in zip(heads, cols)]
    def line(cells): return '| ' + ' | '.join(c.ljust(w) for c,w in zip(cells,widths)) + ' |'
    out=[line(heads), '| ' + ' | '.join('-'*w for w in widths) + ' |']
    for r in rows: out.append(line([esc(r.get(c,'')) for c in cols]))
    out.append('')
    if key: out.append(f'key   := {key}')
    for a,(fn,c) in aggs.items(): out.append(f'{a} := {fn}({c})')
    return '\n'.join(out).rstrip()+'\n'

# ---------- export ----------
def parse_tbl(text):
    lines=[l for l in text.splitlines()]
    tl=[l for l in lines if l.strip().startswith('|')]
    hdr=split_row(tl[0]); cols=[]; formulas={}
    for h in hdr:
        if '=' in h:
            n,e=h.split('=',1); cols.append(n.strip()); formulas[n.strip()]=e.strip()
        else: cols.append(h)
    rows=[dict(zip(cols, split_row(l))) for l in tl[2:]]
    aggs={}
    key=None
    for l in lines:
        m=re.match(r'\s*([^\s:=]+)\s*:=\s*(\w+)\(\s*([^\s()]+)\s*\)\s*$', l)
        if m: aggs[m.group(1)]=(m.group(2),m.group(3))
        m2=re.match(r'\s*key\s*:=\s*(\w+)\s*$', l)
        if m2: key=m2.group(1)
    return cols, formulas, rows, aggs, key

def tbl2csv(text, values=True, drop_id=False):
    import ast, operator
    cols, formulas, rows, aggs, key = parse_tbl(text)
    OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
    def ev(n,env):
        if isinstance(n,ast.Expression): return ev(n.body,env)
        if isinstance(n,ast.BinOp): return OPS[type(n.op)](ev(n.left,env),ev(n.right,env))
        if isinstance(n,ast.Constant): return n.value
        if isinstance(n,ast.Name): return float(env[n.id])
        raise ValueError
    out=io.StringIO(); w=csv.writer(out, lineterminator='\n')
    ocols=[c for c in cols if not (drop_id and c=='id')]
    w.writerow(ocols)
    for r in rows:
        for name,expr in formulas.items():
            if values:
                try: r[name]=('%g'%ev(ast.parse(expr,mode='eval'),r))
                except Exception: r[name]='#REF!'
        w.writerow([r.get(c,'') for c in ocols])
    return out.getvalue()

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('mode'); p.add_argument('file')
    p.add_argument('--key'); p.add_argument('--prev'); p.add_argument('--name',default='src')
    p.add_argument('--formula',action='append',default=[]); p.add_argument('--agg',action='append',default=[])
    p.add_argument('--drop-id',action='store_true')
    a=p.parse_args()
    if a.mode=='import':
        prev=None
        if a.prev:
            c,f,r,g,k=parse_tbl(open(a.prev).read()); prev=(c,r)
        fs=dict(x.split('=',1) for x in a.formula)
        gs={}
        for x in a.agg:
            n,rest=x.split('=',1); fn,col=rest.split('(',1); gs[n]=(fn,col.rstrip(')'))
        t,rep=csv2tbl(open(a.file,'rb').read(),key=a.key,prev=prev,formulas=fs,aggs=gs,name=a.name)
        rep.dump()
        if t is None or rep.rejects():
            print(f'\n== IMPORT REFUSED: {len(rep.rejects())} reject(s) ==',file=sys.stderr)
        if t: sys.stdout.write(t)
        sys.exit(1 if (t is None or rep.rejects()) else 0)
    else:
        sys.stdout.write(tbl2csv(open(a.file).read(), drop_id=a.drop_id))

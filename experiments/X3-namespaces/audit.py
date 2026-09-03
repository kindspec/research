#!/usr/bin/env python3
"""Mechanical namespace audit.

For EVERY namespace in EVERY format, construct a collision two ways -- two
branches each introducing a colliding binding, and a single file already
containing one -- then report what git does and what the parser does.

A namespace is SAFE if at least one of these holds:
  CO-LOCATED  all bindings sit on one line, so git sees the collision
  VALIDATED   the parser refuses the collision wherever it sits
Anything else is a silent-wrong generator.
"""
import os, subprocess, tempfile, shutil, sys

def sh(*a, cwd=None):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)

def git_collide(fn, base, ours, theirs):
    d = tempfile.mkdtemp()
    try:
        sh('git','init','-q',d)
        for k,v in [('user.email','t@e'),('user.name','t')]: sh('git','config',k,v,cwd=d)
        p = os.path.join(d, fn)
        open(p,'w').write(base); sh('git','add','-A',cwd=d); sh('git','commit','-qm','b',cwd=d)
        sh('git','branch','-M','main',cwd=d)
        sh('git','checkout','-qb','x',cwd=d); open(p,'w').write(theirs); sh('git','commit','-qam','x',cwd=d)
        sh('git','checkout','-q','main',cwd=d); open(p,'w').write(ours); sh('git','commit','-qam','o',cwd=d)
        r = sh('git','merge','x','-m','m',cwd=d)
        return ('CONFLICT' if r.returncode else 'clean'), open(p).read()
    finally: shutil.rmtree(d)

# ---- parsers under test -------------------------------------------------
import otbl
def parse_tbl(t):
    try: otbl.evaluate(t); return None
    except otbl.Malformed as e: return str(e)
    except Exception as e: return f'CRASH: {type(e).__name__}: {e}'

def parse_md(t):
    """Markdown as the design would validate it: reject duplicate bindings in
    any of its four scattered namespaces."""
    import re, io
    errs = []
    def dupes(kind, names):
        seen=set()
        for n in names:
            if n.lower() in seen: errs.append(f'duplicate {kind} {n!r}')
            seen.add(n.lower())
    dupes('link label', re.findall(r'^\[([^\]^]+)\]:', t, re.M))
    dupes('footnote label', re.findall(r'^\[\^([^\]]+)\]:', t, re.M))
    dupes('heading anchor', re.findall(r'^#{1,6}\s+.*\{#([\w-]+)\}', t, re.M))
    if t.startswith('---'):
        fm = t.split('---',2)[1]
        dupes('frontmatter key', re.findall(r'^(\w+):', fm, re.M))
    for marker in ('<<<<<<<','=======','>>>>>>>'):
        if any(l.startswith(marker) for l in t.splitlines()):
            errs.append('conflict marker'); break
    return '; '.join(errs) or None

def parse_canvas(t):
    import re
    nodes, errs = [], []
    layout, edges = [], []
    sec='body'
    for n,l in enumerate(t.splitlines(),1):
        s=l.strip()
        if not s or s.startswith('#'): continue
        if s=='@layout': sec='layout'; continue
        if sec=='layout':
            m=re.match(r'(\w+)\s*\{',s)
            if m: layout.append(m.group(1))
            continue
        m=re.match(r'node\s+(\w+)',s)
        if m: nodes.append(m.group(1)); continue
        m=re.match(r'edge\s+(\w+)\s*->\s*(\w+)',s)
        if m: edges.append((m.group(1),m.group(2)))
    seen=set()
    for x in nodes:
        if x in seen: errs.append(f'duplicate node {x!r}')
        seen.add(x)
    seen=set()
    for x in layout:
        if x in seen: errs.append(f'duplicate layout override {x!r}')
        seen.add(x)
        if x not in nodes: errs.append(f'layout override for unknown node {x!r}')
    for a,b in edges:
        for e in (a,b):
            if e not in nodes: errs.append(f'edge references unknown node {e!r}')
    return '; '.join(errs) or None

# ---- the namespace catalogue -------------------------------------------
TBL = """| id     | item     | qty | unit  | total = qty * unit |
| ------ | -------- | --: | ----: | -----------------: |
| r_0001 | widget   |  10 | 12.00 |                    |
| r_0002 | gadget   |  20 |  6.00 |                    |
| r_0003 | sprocket |   8 | 15.00 |                    |
| r_0004 | flange   |   5 | 24.00 |                    |

key   := id
grand := sum(total)
"""
def tbl_addcol(t, name, tag):
    L=[]
    for i,l in enumerate(t.splitlines()):
        if not l.startswith('|'): L.append(l)
        elif i==0: L.append(l+f' {name} |')
        elif i==1: L.append(l+' --- |')
        else: L.append(l+f' {tag}{i} |')
    return '\n'.join(L)+'\n'
def tbl_addagg(t, line, near_top):
    L=t.splitlines()
    i=L.index('key   := id')
    L.insert(i if near_top else len(L), line)
    return '\n'.join(L)+'\n'
def tbl_addrow(t, rid, tag, after):
    L=t.splitlines()
    i=[n for n,l in enumerate(L) if after in l][0]
    L.insert(i+1, f'| {rid} | {tag}      |   1 |  1.00 |                    |')
    return '\n'.join(L)+'\n'

MD = "---\ntitle: Doc\nid: 01J8\n---\n\n" + "".join(
    f"## Section {i}\n\nBody text for section {i}.\n\n" for i in range(1,11))
def md_at(t, sect, extra):
    return t.replace(f"Body text for section {sect}.", f"Body text for section {sect}.\n\n{extra}")

CANVAS = """node api  "API Gateway"
node auth "Auth Service"
node db   "Postgres"
edge api -> auth
edge auth -> db

@layout
"""
def canvas_add(t, line, near_top):
    L=t.splitlines()
    L.insert(1 if near_top else L.index('@layout'), line)
    return '\n'.join(L)+'\n'
def canvas_layout(t, line):
    return t.rstrip('\n')+'\n'+line+'\n'

CASES = [
 # (format, namespace, base, ours, theirs, parser)
 ('.tbl','column name', TBL,      tbl_addcol(TBL,'code','A'), tbl_addcol(TBL,'code','B'), parse_tbl),
 ('.tbl','aggregate name', TBL,   tbl_addagg(TBL,'subtotal := sum(qty)',True),
                             tbl_addagg(TBL,'subtotal := sum(total)',False), parse_tbl),
 ('.tbl','row id', TBL,           tbl_addrow(TBL,'r_0009','alpha','widget'),
                             tbl_addrow(TBL,'r_0009','beta','flange'), parse_tbl),
 ('.tbl','key declaration', TBL,  tbl_addagg(TBL,'key := item',True),
                             tbl_addagg(TBL,'key := qty',False), parse_tbl),
 ('.md','link label', MD,        md_at(MD,2,'See [x][api].\n\n[api]: https://A/'),
                             md_at(MD,9,'See [x][api].\n\n[api]: https://B/'), parse_md),
 ('.md','footnote label', MD,    md_at(MD,2,'Note.[^n]\n\n[^n]: first'),
                             md_at(MD,9,'Note.[^n]\n\n[^n]: second'), parse_md),
 ('.md','heading anchor', MD,    MD.replace('## Section 2','## Section 2 {#findings}'),
                             MD.replace('## Section 9','## Section 9 {#findings}'), parse_md),
 ('.md','frontmatter key', MD,   MD.replace('title: Doc','title: Doc\nauthor: A'),
                             MD.replace('id: 01J8','id: 01J8\nauthor: B'), parse_md),
 ('.canvas','node name', CANVAS,     canvas_add(CANVAS,'node cache "Redis A"',True),
                             canvas_add(CANVAS,'node cache "Redis B"',False), parse_canvas),
 ('.canvas','layout key', CANVAS,    canvas_layout(CANVAS,'db { below: auth }'),
                             canvas_layout(CANVAS,'db { below: api }'), parse_canvas),
 ('.canvas','dangling edge', CANVAS, CANVAS.replace('node db   "Postgres"','node store "Postgres"'),
                             CANVAS, parse_canvas),
]

if __name__ == '__main__':
    print(f"{'format':8} {'namespace':20} {'git merge':10} {'parser on merged result':38} verdict")
    print('-'*105)
    bad=0
    for fmt, ns, base, ours, theirs, parser in CASES:
        fn = {'.tbl':'a.tbl','.md':'a.md','.canvas':'a.canvas'}[fmt]
        status, merged = git_collide(fn, base, ours, theirs)
        perr = parser(merged)
        if status=='CONFLICT': verdict, note = 'SAFE', 'co-located: git refuses'
        elif perr:             verdict, note = 'SAFE', 'validated: parser refuses'
        else:                  verdict, note = 'SILENT-WRONG', 'neither'; bad+=1
        print(f"{fmt:8} {ns:20} {status:10} {(perr or '(accepted)')[:36]:38} {verdict}  {note}")
    print('-'*105)
    print(f"{bad} namespace(s) protected by NEITHER co-location nor validation")
    sys.exit(1 if bad else 0)

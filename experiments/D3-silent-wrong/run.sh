#!/bin/bash
# Catalogue of SILENT WRONG merges: git reports a clean auto-merge, the result is semantically wrong.
set -u
E="$(cd "$(dirname "$0")" && pwd)"
W="$E/work"; rm -rf "$W"; mkdir -p "$W"
GIT="git -c user.name=T -c user.email=t@e -c init.defaultBranch=main"

# case <name> <file> ; then writer functions base/a/b are heredocs supplied via files
newcase(){ NAME="$1"; D="$W/$NAME"; rm -rf "$D"; mkdir -p "$D"; cd "$D"; $GIT init -q .; }
commit_base(){ $GIT add -A >/dev/null; $GIT commit -qm base; $GIT checkout -qb B; }
switch_main(){ $GIT commit -qam b-side; $GIT checkout -q main; }
domerge(){ $GIT commit -qam a-side; echo "--- git merge B ---"; $GIT merge B 2>&1 | sed 's/^/    /'; MERGE_EXIT=${PIPESTATUS[0]}; echo "    (merge exit=$MERGE_EXIT)"; }
hdr(){ echo; echo "################################################################"; echo "# $*"; echo "################################################################"; }

################################################################
hdr "S1  CSV + A1 formulas: two row inserts, clean merge, WRONG TOTAL"
newcase s1
cat > sheet.csv <<'EOF'
item,qty,price,total
a,10,10,=B2*C2
b,10,10,=B3*C3
c,10,10,=B4*C4
d,10,10,=B5*C5
e,10,10,=B6*C6
f,10,10,=B7*C7
TOTAL,,,=SUM(D2:D7)
EOF
commit_base
# B inserts a row near the top and extends the SUM
python3 - <<'PY'
l=open('sheet.csv').read().split('\n')
l.insert(2,'new-b,10,10,=B3*C3')
t=[x.replace('=SUM(D2:D7)','=SUM(D2:D8)') for x in l]
open('sheet.csv','w').write('\n'.join(t))
PY
switch_main
python3 - <<'PY'
l=open('sheet.csv').read().split('\n')
l.insert(6,'new-a,10,10,=B7*C7')
t=[x.replace('=SUM(D2:D7)','=SUM(D2:D8)') for x in l]
open('sheet.csv','w').write('\n'.join(t))
PY
domerge
echo "--- merged sheet.csv ---"; sed 's/^/    /' sheet.csv
echo "--- rows: $(($(wc -l < sheet.csv)-1)) data+header lines"
echo -n "--- TOTAL cell evaluates to: "; python3 "$E/evalcsv.py" sheet.csv D9 2>/dev/null || python3 "$E/evalcsv.py" sheet.csv D8
echo "--- CORRECT answer (8 items x 100): 800"

################################################################
hdr "S2  CSV: column inserted on one side, row edited on other -> COLUMN SHEAR"
newcase s2
cat > t.csv <<'EOF'
id,name,salary
1,Alice,100
2,Bob,90
3,Carol,110
4,Dave,95
5,Eve,105
EOF
commit_base
# B adds a 'dept' column to every row
python3 - <<'PY'
import csv
r=list(csv.reader(open('t.csv')))
r[0].insert(2,'dept')
for i,row in enumerate(r[1:],1): row.insert(2,'Eng')
csv.writer(open('t.csv','w'),lineterminator='\n').writerows(r)
PY
switch_main
sed -i 's/^4,Dave,95/4,Dave,999/' t.csv
domerge
echo "--- merged t.csv ---"; sed 's/^/    /' t.csv
echo "--- column widths seen by a CSV parser:"
python3 -c "
import csv,collections
r=list(csv.reader(open('t.csv')))
print('   ',collections.Counter(len(x) for x in r))
for x in r: print('    ',x)
"

################################################################
hdr "S3  Markdown reference-style links: duplicate label, CLEAN merge, WRONG TARGET"
newcase s3
cat > doc.md <<'EOF'
# Report

See the [spec][1] for details.

Intro paragraph.

More text.

Conclusion.

[1]: https://example.com/original-spec
EOF
commit_base
python3 - <<'PY'
t=open('doc.md').read()
t=t.replace('More text.','More text. Also read the [appendix][2].')
t=t.rstrip()+'\n[2]: https://example.com/appendix-B\n'
open('doc.md','w').write(t)
PY
switch_main
python3 - <<'PY'
t=open('doc.md').read()
t=t.replace('Intro paragraph.','Intro paragraph. Compare the [old version][2].')
t=t.rstrip()+'\n[2]: https://example.com/version-1\n'
open('doc.md','w').write(t)
PY
domerge
echo "--- merged doc.md ---"; sed 's/^/    /' doc.md
echo "--- both [2] references now resolve to the SAME url (CommonMark: first definition wins):"
python3 - <<'PY'
import re
t=open('doc.md').read()
defs=re.findall(r'^\[(\d+)\]:\s*(\S+)',t,re.M)
print('    definitions:',defs)
seen={}
for k,v in defs: seen.setdefault(k,v)
for k,v in re.findall(r'\[([^\]]+)\]\[(\d+)\]',t):
    print(f'    link "{k}" -> {seen.get(v)}')
PY

################################################################
hdr "S4  Markdown numbered headings / TOC: clean merge, DUPLICATE SECTION NUMBERS"
newcase s4
cat > doc.md <<'EOF'
# Manual

## Contents
1. Setup
2. Usage
3. Reference

## 1. Setup
setup text

## 2. Usage
usage text

## 3. Reference
ref text
EOF
commit_base
python3 - <<'PY'
t=open('doc.md').read()
t=t.replace('## 2. Usage','## 2. Configuration\nconfig text\n\n## 3. Usage')
t=t.replace('## 3. Reference','## 4. Reference')
t=t.replace('1. Setup\n2. Usage\n3. Reference','1. Setup\n2. Configuration\n3. Usage\n4. Reference')
open('doc.md','w').write(t)
PY
switch_main
python3 - <<'PY'
t=open('doc.md').read()
t=t.replace('## 3. Reference\nref text','## 3. Troubleshooting\ntrouble text\n\n## 4. Reference\nref text')
t=t.replace('1. Setup\n2. Usage\n3. Reference','1. Setup\n2. Usage\n3. Troubleshooting\n4. Reference')
open('doc.md','w').write(t)
PY
domerge
echo "--- merged doc.md ---"; sed 's/^/    /' doc.md
echo "--- heading numbers present:"; grep -o '^## [0-9]*\.' doc.md | sed 's/^/    /'

################################################################
hdr "S5  JSON: concurrent array appends -> CLEAN merge, DUPLICATE ids"
newcase s5
cat > cfg.json <<'EOF'
{
  "users": [
    {"id": 1, "role": "admin"},
    {"id": 2, "role": "viewer"},
    {"id": 3, "role": "viewer"},
    {"id": 4, "role": "viewer"},
    {"id": 5, "role": "viewer"}
  ],
  "seats": 5
}
EOF
commit_base
python3 - <<'PY'
t=open('cfg.json').read()
t=t.replace('{"id": 1, "role": "admin"},','{"id": 1, "role": "admin"},\n    {"id": 6, "role": "viewer"},')
t=t.replace('"seats": 5','"seats": 6')
open('cfg.json','w').write(t)
PY
switch_main
python3 - <<'PY'
t=open('cfg.json').read()
t=t.replace('{"id": 5, "role": "viewer"}','{"id": 5, "role": "viewer"},\n    {"id": 6, "role": "editor"}')
t=t.replace('"seats": 5','"seats": 6')
open('cfg.json','w').write(t)
PY
domerge
echo "--- merged cfg.json ---"; sed 's/^/    /' cfg.json
python3 - <<'PY'
import json,collections
try:
    d=json.load(open('cfg.json'))
    ids=[u['id'] for u in d['users']]
    print('    parses OK. ids =',ids)
    print('    duplicate ids:',[k for k,v in collections.Counter(ids).items() if v>1])
    print('    len(users) =',len(d['users']),' but "seats" =',d['seats'],' <-- INVARIANT BROKEN')
except Exception as e: print('    parse error:',e)
PY

################################################################
hdr "S6  YAML: concurrent key add -> DUPLICATE KEY, parser silently takes the last"
newcase s6
cat > c.yaml <<'EOF'
name: svc
replicas: 2
image: app:1.0
port: 8080
env: prod
region: us-east
EOF
commit_base
python3 - <<'PY'
l=open('c.yaml').read().split('\n')
l.insert(1,'timeout: 30')
open('c.yaml','w').write('\n'.join(l))
PY
switch_main
python3 - <<'PY'
l=open('c.yaml').read().split('\n')
l.insert(6,'timeout: 90')
open('c.yaml','w').write('\n'.join(l))
PY
domerge
echo "--- merged c.yaml ---"; sed 's/^/    /' c.yaml
python3 - <<'PY'
import yaml
try:
    d=yaml.safe_load(open('c.yaml'))
    print('    pyyaml: parses OK, timeout =',d.get('timeout'),' (one of the two writers silently lost)')
except Exception as e: print('    pyyaml error:',e)
PY

################################################################
hdr "S7  YAML frontmatter: concurrent tag-list edits -> clean merge, wrong list"
newcase s7
cat > post.md <<'EOF'
---
title: Post
tags:
  - alpha
  - beta
  - gamma
  - delta
draft: false
---

Body.
EOF
commit_base
python3 - <<'PY'
t=open('post.md').read().replace('  - alpha','  - alpha\n  - NEW-FROM-B')
open('post.md','w').write(t)
PY
switch_main
python3 - <<'PY'
t=open('post.md').read().replace('  - delta','  - delta\n  - NEW-FROM-A')
t=t.replace('draft: false','draft: true')
open('post.md','w').write(t)
PY
domerge
echo "--- merged post.md ---"; sed 's/^/    /' post.md

################################################################
hdr "S8  SVG: concurrent <defs> additions -> DUPLICATE id, first-wins, WRONG COLOURS"
newcase s8
cat > d.svg <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">
  <defs>
  </defs>
  <rect id="r1" x="0" y="0" width="100" height="100" fill="#ccc"/>
  <rect id="r2" x="110" y="0" width="100" height="100" fill="#ccc"/>
  <rect id="r3" x="220" y="0" width="100" height="100" fill="#ccc"/>
  <g id="layer-annotations">
  </g>
</svg>
EOF
commit_base
python3 - <<'PY'
t=open('d.svg').read()
t=t.replace('  <defs>\n','  <defs>\n    <linearGradient id="grad1"><stop offset="0%" stop-color="red"/></linearGradient>\n')
t=t.replace('id="r1" x="0" y="0" width="100" height="100" fill="#ccc"','id="r1" x="0" y="0" width="100" height="100" fill="url(#grad1)"')
open('d.svg','w').write(t)
PY
switch_main
python3 - <<'PY'
t=open('d.svg').read()
t=t.replace('  </defs>','    <linearGradient id="grad1"><stop offset="0%" stop-color="blue"/></linearGradient>\n  </defs>')
t=t.replace('id="r3" x="220" y="0" width="100" height="100" fill="#ccc"','id="r3" x="220" y="0" width="100" height="100" fill="url(#grad1)"')
open('d.svg','w').write(t)
PY
domerge
echo "--- merged d.svg ---"; sed 's/^/    /' d.svg
python3 - <<'PY'
import xml.etree.ElementTree as ET, collections, re
t=open('d.svg').read()
try:
    ET.fromstring(t); print('    XML: well-formed (no conflict markers)')
except Exception as e: print('    XML error:',e); raise SystemExit
ids=re.findall(r'id="([^"]+)"',t)
dup=[k for k,v in collections.Counter(ids).items() if v>1]
print('    ids:',ids)
print('    DUPLICATE ids:',dup,'  <-- SVG requires unique ids; renderers resolve url(#..) to the FIRST')
print('    -> r1 (author B wanted red) and r3 (author A wanted blue) BOTH render red.')
PY

################################################################
hdr "S9  SVG: concurrent viewBox change vs. new geometry -> silently mis-scaled"
newcase s9
cat > v.svg <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="400" height="400">
  <rect x="10" y="10" width="20" height="20" fill="red"/>
  <line x1="0" y1="0" x2="100" y2="100" stroke="black"/>
  <text x="50" y="95" font-size="8">caption</text>
</svg>
EOF
commit_base
python3 - <<'PY'
t=open('v.svg').read().replace('viewBox="0 0 100 100"','viewBox="0 0 1000 1000"')
t=t.replace('<rect x="10" y="10" width="20" height="20"','<rect x="100" y="100" width="200" height="200"')
t=t.replace('x2="100" y2="100"','x2="1000" y2="1000"')
t=t.replace('x="50" y="95" font-size="8"','x="500" y="950" font-size="80"')
open('v.svg','w').write(t)
PY
switch_main
python3 - <<'PY'
t=open('v.svg').read().replace('  <text x="50" y="95" font-size="8">caption</text>',
  '  <text x="50" y="95" font-size="8">caption</text>\n  <circle cx="80" cy="20" r="10" fill="green"/>')
open('v.svg','w').write(t)
PY
domerge
echo "--- merged v.svg ---"; sed 's/^/    /' v.svg
echo "    -> viewBox is 0 0 1000 1000; the newly added circle uses cx=80 cy=20 r=10 in the OLD 100x100 space."
echo "    -> it renders at 8% of the intended position, effectively invisible. XML is valid; git said clean."

################################################################
hdr "S10  merge=union (the ONLY repo-portable custom-ish driver) on CSV -> DUPLICATED ROWS"
newcase s10
cat > u.csv <<'EOF'
id,name
1,Alice
2,Bob
EOF
printf 'u.csv merge=union\n' > .gitattributes
commit_base
printf '3,Carol\n' >> u.csv
switch_main
printf '3,Dave\n' >> u.csv
domerge
echo "--- merged u.csv (git reported CLEAN) ---"; sed 's/^/    /' u.csv
echo "    -> two different records now share id=3, and no marker anywhere."

################################################################
hdr "S11  CSV: row REORDER on one side, row EDIT on other -> lost edit + duplicate"
newcase s11
python3 -c "
import csv
rows=[['id','name','qty']]+[[str(i),'item%d'%i,str(i*10)] for i in range(1,9)]
csv.writer(open('r.csv','w'),lineterminator='\n').writerows(rows)"
commit_base
python3 - <<'PY'
import csv
r=list(csv.reader(open('r.csv')))
h,body=r[0],r[1:]
body.sort(key=lambda x:x[1],reverse=True)      # reorder
csv.writer(open('r.csv','w'),lineterminator='\n').writerows([h]+body)
PY
switch_main
sed -i 's/^4,item4,40/4,item4,4000/' r.csv
domerge
echo "--- merged r.csv ---"; sed 's/^/    /' r.csv
python3 - <<'PY'
import csv,collections
try:
    r=list(csv.reader(open('r.csv')))
except Exception as e: print('   ',e); raise SystemExit
ids=[x[0] for x in r[1:] if x]
print('    ids:',ids)
d=[k for k,v in collections.Counter(ids).items() if v>1]
print('    duplicates:',d)
q=dict((x[0],x[2]) for x in r[1:] if len(x)>2)
print('    qty for id=4 :',q.get('4'),' (the edit was 4000)')
PY

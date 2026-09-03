#!/bin/bash
set -u
E="$(cd "$(dirname "$0")" && pwd)"; W="$E/work2"; rm -rf "$W"; mkdir -p "$W"
GIT="git -c user.name=T -c user.email=t@e -c init.defaultBranch=main"
newcase(){ D="$W/$1"; rm -rf "$D"; mkdir -p "$D"; cd "$D"; $GIT init -q .; }
cb(){ $GIT add -A >/dev/null; $GIT commit -qm base; $GIT checkout -qb B; }
sw(){ $GIT commit -qam b; $GIT checkout -q main; }
dm(){ $GIT commit -qam a; echo "--- git merge B ---"; $GIT merge B 2>&1|sed 's/^/    /'; }
hdr(){ echo; echo "################ $*"; }

hdr "S1b CSV+A1, VARIED values: clean merge, per-row AND total both wrong"
newcase s1b
cat > s.csv <<'EOF'
item,qty,price,total
a,1,100,=B2*C2
b,2,100,=B3*C3
c,3,100,=B4*C4
d,4,100,=B5*C5
e,5,100,=B6*C6
f,6,100,=B7*C7
TOTAL,,,=SUM(D2:D7)
EOF
cb
python3 -c "
l=open('s.csv').read().rstrip().split('\n')
l.insert(2,'NEW-B,10,100,=B3*C3')
l=[x.replace('=SUM(D2:D7)','=SUM(D2:D8)') for x in l]
open('s.csv','w').write('\n'.join(l)+'\n')"
sw
python3 -c "
l=open('s.csv').read().rstrip().split('\n')
l.insert(6,'NEW-A,20,100,=B7*C7')
l=[x.replace('=SUM(D2:D7)','=SUM(D2:D8)') for x in l]
open('s.csv','w').write('\n'.join(l)+'\n')"
dm
echo "--- merged ---"; nl -ba s.csv | sed 's/^/    /'
echo "--- evaluated vs intended ---"
python3 - "$E" <<'PY'
import sys,csv,subprocess
sys.path.insert(0,sys.argv[1])
import importlib.util
spec=importlib.util.spec_from_file_location("ev",sys.argv[1]+"/evalcsv.py"); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
g=m.load('s.csv')
names=[r[0] for r in g[1:]]
tot=0
for i,r in enumerate(g[1:],2):
    if r[0]=='TOTAL': continue
    want=float(r[1])*float(r[2]); got=m.ev(g,r[3])
    tot+=want
    flag='   <-- WRONG' if abs(want-got)>1e-9 else ''
    print(f"    {r[0]:6} qty={r[1]:>3} price={r[2]:>4}  intended={want:8.0f}  computed={got:8.0f}{flag}")
print(f"    TOTAL  intended={tot:.0f}  computed={m.ev(g,g[-1][3]):.0f}   <-- WRONG")
PY

hdr "S12 Markdown: sorted link-definition block, concurrent inserts -> CLEAN, duplicate label"
newcase s12
cat > d.md <<'EOF'
# Guide

Read the [alpha][alpha] and [zeta][zeta] docs, plus the [api][api] reference.

[alpha]: https://ex.com/alpha
[beta]: https://ex.com/beta
[delta]: https://ex.com/delta
[gamma]: https://ex.com/gamma
[kappa]: https://ex.com/kappa
[omega]: https://ex.com/omega
[sigma]: https://ex.com/sigma
[theta]: https://ex.com/theta
[zeta]: https://ex.com/zeta
EOF
cb
sed -i '/^\[alpha\]:/a [api]: https://ex.com/api/v1' d.md
sw
sed -i '/^\[theta\]:/a [api]: https://ex.com/api/v2' d.md
dm
echo "--- merged ---"; sed 's/^/    /' d.md
python3 - <<'PY'
import re
t=open('d.md').read()
ds=re.findall(r'^\[([^\]]+)\]:\s*(\S+)',t,re.M)
seen={}
for k,v in ds: seen.setdefault(k,v)
print('    [api] defined',sum(1 for k,_ in ds if k=='api'),'times; CommonMark uses the FIRST ->',seen['api'])
print('    the other definition is silently dead. No marker, no warning.')
PY

hdr "S13 Markdown: concurrent edits turn a paragraph into a SETEXT HEADING"
newcase s13
cat > d.md <<'EOF'
# Notes

Alpha paragraph.

Beta paragraph.

Gamma paragraph.

Delta paragraph.

Epsilon paragraph.

Zeta paragraph.
EOF
cb
# B appends a thematic break + appendix at the very end
printf -- '\n---\n\n## Appendix\n\nAppendix text.\n' >> d.md
sw
# A appends a closing remark at the end
printf -- '\nClosing remark.\n' >> d.md
dm
echo "--- merged ---"; sed 's/^/    /' d.md
echo "--- rendered heading structure (markdown-it):"
node -e '
const fs=require("fs");const t=fs.readFileSync("d.md","utf8");
// minimal setext detection without deps
const L=t.split("\n");
for(let i=1;i<L.length;i++){
  if(/^-{3,}\s*$/.test(L[i]) && L[i-1].trim()!=="" && !/^#/.test(L[i-1]))
    console.log("    SETEXT H2 created from paragraph: \""+L[i-1].trim()+"\"  <-- was body text");
  if(/^-{3,}\s*$/.test(L[i]) && L[i-1].trim()==="") console.log("    thematic break (correct) at line "+(i+1));
}' 2>/dev/null || echo "    (node unavailable)"

hdr "S14 CSV FALSE CONFLICT: two writers edit DIFFERENT COLUMNS of the SAME row"
newcase s14
cat > f.csv <<'EOF'
id,name,email,phone,dept
1,Alice,a@x.com,555-0001,Eng
2,Bob,b@x.com,555-0002,Sales
3,Carol,c@x.com,555-0003,Eng
EOF
cb
sed -i 's/2,Bob,b@x.com,555-0002,Sales/2,Bob,b@x.com,555-9999,Sales/' f.csv
sw
sed -i 's/2,Bob,b@x.com,555-0002,Sales/2,Bob,bob@newdomain.com,555-0002,Sales/' f.csv
dm
echo "--- merged (git CONFLICTS; a cell-level merge would resolve cleanly and correctly) ---"
sed 's/^/    /' f.csv
echo "    correct cell-level result: 2,Bob,bob@newdomain.com,555-9999,Sales"

hdr "S15 JSON: rename a key on one side, add a reader of the old key on the other"
newcase s15
cat > c.json <<'EOF'
{
  "database": {"host": "db1", "port": 5432},
  "cache": {"host": "c1", "port": 6379},
  "features": {"a": true, "b": false},
  "logging": {"level": "info"},
  "limits": {"rps": 100}
}
EOF
cb
python3 -c "
t=open('c.json').read().replace('\"database\"','\"primary_db\"')
open('c.json','w').write(t)"
sw
python3 -c "
t=open('c.json').read().replace('\"limits\": {\"rps\": 100}','\"limits\": {\"rps\": 100},\n  \"replica_of\": \"database\"')
open('c.json','w').write(t)"
dm
echo "--- merged ---"; sed 's/^/    /' c.json
python3 -c "
import json
d=json.load(open('c.json'))
print('    parses OK. keys:',list(d))
print('    replica_of =',repr(d.get('replica_of')),'but there is no \"database\" key any more -> dangling reference, no error')"

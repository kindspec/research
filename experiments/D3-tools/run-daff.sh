#!/bin/bash
# What a REAL structured merge driver (daff) buys, on the exact cases plain git got wrong.
set -u
E="$(cd "$(dirname "$0")" && pwd)"; DAFF="$E/node_modules/.bin/daff"
W="$E/work"; rm -rf "$W"; mkdir -p "$W"
GIT="git -c user.name=T -c user.email=t@e -c init.defaultBranch=main"
echo "daff version: $($DAFF version 2>&1)"
mk(){ D="$W/$1"; rm -rf "$D"; mkdir -p "$D"; cd "$D"; $GIT init -q .
  printf 't.csv merge=daff\n' > .gitattributes
  $GIT config merge.daff.name "daff tabular merge"
  $GIT config merge.daff.driver "$DAFF merge --output %A %O %A %B"; }
cb(){ $GIT add -A>/dev/null; $GIT commit -qm base; $GIT checkout -qb B; }
sw(){ $GIT commit -qam b; $GIT checkout -q main; }
dm(){ $GIT commit -qam a; $GIT merge B 2>&1 | sed 's/^/    /'; }

echo; echo "############ D1: same row, different columns (git FALSE-CONFLICTS) ############"
mk d1
cat > t.csv <<'EOF'
id,name,email,phone,dept
1,Alice,a@x.com,555-0001,Eng
2,Bob,b@x.com,555-0002,Sales
3,Carol,c@x.com,555-0003,Eng
EOF
cb; sed -i 's/555-0002/555-9999/' t.csv; sw; sed -i 's/b@x.com/bob@new.com/' t.csv; dm
echo "--- result:"; sed 's/^/    /' t.csv

echo; echo "############ D2: column insert on one side + row edit on other (git FALSE-CONFLICTS) ############"
mk d2
cat > t.csv <<'EOF'
id,name,salary
1,Alice,100
2,Bob,90
3,Carol,110
EOF
cb
python3 -c "
import csv
r=list(csv.reader(open('t.csv'))); r[0].insert(2,'dept')
for x in r[1:]: x.insert(2,'Eng')
csv.writer(open('t.csv','w'),lineterminator='\n').writerows(r)"
sw; sed -i 's/^3,Carol,110/3,Carol,999/' t.csv; dm
echo "--- result:"; sed 's/^/    /' t.csv

echo; echo "############ D3: row reorder + row edit (git mangles badly) ############"
mk d3
python3 -c "
import csv
csv.writer(open('t.csv','w'),lineterminator='\n').writerows([['id','name','qty']]+[[str(i),'item%d'%i,str(i*10)] for i in range(1,9)])"
cb
python3 -c "
import csv
r=list(csv.reader(open('t.csv'))); h,b=r[0],r[1:]; b.sort(key=lambda x:x[1],reverse=True)
csv.writer(open('t.csv','w'),lineterminator='\n').writerows([h]+b)"
sw; sed -i 's/^4,item4,40/4,item4,4000/' t.csv; dm
echo "--- result:"; sed 's/^/    /' t.csv

echo; echo "############ D4: A REAL conflict — both edit the SAME cell ############"
mk d4
printf 'id,name,qty\n1,a,10\n2,b,20\n3,c,30\n' > t.csv
cb; sed -i 's/^2,b,20/2,b,222/' t.csv; sw; sed -i 's/^2,b,20/2,b,999/' t.csv; dm
echo "--- result (note daff's in-band conflict encoding, and whether CSV stays parseable):"
sed 's/^/    /' t.csv
python3 -c "
import csv,collections
r=list(csv.reader(open('t.csv')))
print('    csv parses OK; row widths:',collections.Counter(len(x) for x in r))
for x in r: print('     ',x)"
echo "--- git status:"; $GIT status --short | sed 's/^/    /'

echo; echo "############ D5: A1 FORMULAS — does a table merger help? ############"
mk d5
cat > t.csv <<'EOF'
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
l=open('t.csv').read().rstrip().split('\n'); l.insert(2,'NEW-B,10,100,=B3*C3')
open('t.csv','w').write('\n'.join(x.replace('=SUM(D2:D7)','=SUM(D2:D8)') for x in l)+'\n')"
sw
python3 -c "
l=open('t.csv').read().rstrip().split('\n'); l.insert(6,'NEW-A,20,100,=B7*C7')
open('t.csv','w').write('\n'.join(x.replace('=SUM(D2:D7)','=SUM(D2:D8)') for x in l)+'\n')"
dm
echo "--- result:"; nl -ba t.csv | sed 's/^/    /'
echo "--- evaluated:"
python3 - <<'PY'
import importlib.util,sys
spec=importlib.util.spec_from_file_location("ev","/home/cam/repos/working-git-backed-gws/experiments/D3-silent-wrong/evalcsv.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
g=m.load('t.csv'); tot=0
for r in g[1:]:
    if r[0]=='TOTAL': continue
    want=float(r[1])*float(r[2]); got=m.ev(g,r[3]); tot+=want
    print(f"    {r[0]:6} intended={want:8.0f} computed={got:8.0f}{'  <-- WRONG' if abs(want-got)>1e-9 else ''}")
print(f"    TOTAL intended={tot:.0f} computed={m.ev(g,g[-1][3]):.0f}")
PY

echo; echo "############ D6: daff's diff format (the 'highlighter') ############"
cd "$W/d2"; $GIT show main~1:t.csv > /tmp/_a.csv 2>/dev/null; $GIT show B:t.csv > /tmp/_b.csv
$DAFF diff /tmp/_a.csv /tmp/_b.csv | sed 's/^/    /'

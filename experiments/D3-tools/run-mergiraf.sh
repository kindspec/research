#!/bin/bash
set -u
E="$(cd "$(dirname "$0")" && pwd)"; MG="$E/mergiraf-install/bin/mergiraf"
W="$E/mgwork"; rm -rf "$W"; mkdir -p "$W"
GIT="git -c user.name=T -c user.email=t@e -c init.defaultBranch=main"
echo "mergiraf: $($MG --version)"
mk(){ D="$W/$1"; rm -rf "$D"; mkdir -p "$D"; cd "$D"; $GIT init -q .
  printf '%s\n' "$2" > .gitattributes
  $GIT config merge.mergiraf.name mergiraf
  $GIT config merge.mergiraf.driver "$MG merge --git %O %A %B -s %S -x %X -y %Y -p %P -l %L"
  $GIT config merge.conflictStyle diff3; }
cb(){ $GIT add -A>/dev/null; $GIT commit -qm base; $GIT checkout -qb B; }
sw(){ $GIT commit -qam b; $GIT checkout -q main; }
dm(){ $GIT commit -qam a; $GIT merge B 2>&1 | sed 's/^/    /'; }
hdr(){ echo; echo "############ $* ############"; }

hdr "M1 JSON: concurrent array inserts + counter (git = SILENT WRONG)"
mk m1 'cfg.json merge=mergiraf'
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
cb
python3 -c "
t=open('cfg.json').read()
t=t.replace('{\"id\": 1, \"role\": \"admin\"},','{\"id\": 1, \"role\": \"admin\"},\n    {\"id\": 6, \"role\": \"viewer\"},').replace('\"seats\": 5','\"seats\": 6')
open('cfg.json','w').write(t)"
sw
python3 -c "
t=open('cfg.json').read()
t=t.replace('{\"id\": 5, \"role\": \"viewer\"}','{\"id\": 5, \"role\": \"viewer\"},\n    {\"id\": 6, \"role\": \"editor\"}').replace('\"seats\": 5','\"seats\": 6')
open('cfg.json','w').write(t)"
dm
echo "--- result:"; sed 's/^/    /' cfg.json
python3 -c "
import json,collections
try:
  d=json.load(open('cfg.json')); ids=[u['id'] for u in d['users']]
  print('    parses; ids',ids,'dups',[k for k,v in collections.Counter(ids).items() if v>1],'seats',d['seats'])
except Exception as e: print('    does NOT parse:',e)"

hdr "M2 YAML: same key added twice (git = SILENT WRONG duplicate key)"
mk m2 'c.yaml merge=mergiraf'
printf 'name: svc\nreplicas: 2\nimage: app:1.0\nport: 8080\nenv: prod\nregion: us-east\n' > c.yaml
cb; python3 -c "
l=open('c.yaml').read().rstrip().split('\n'); l.insert(1,'timeout: 30'); open('c.yaml','w').write('\n'.join(l)+'\n')"
sw; python3 -c "
l=open('c.yaml').read().rstrip().split('\n'); l.insert(5,'timeout: 90'); open('c.yaml','w').write('\n'.join(l)+'\n')"
dm
echo "--- result:"; sed 's/^/    /' c.yaml

hdr "M3 Markdown: duplicate link-reference definition (git = SILENT WRONG)"
mk m3 'd.md merge=mergiraf'
cat > d.md <<'EOF'
# Guide

See [x][api].

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
cb; sed -i '/^\[alpha\]:/a [api]: https://ex.com/api/v1' d.md
sw; sed -i '/^\[theta\]:/a [api]: https://ex.com/api/v2' d.md
dm
echo "--- result:"; sed 's/^/    /' d.md

hdr "M4 SVG via the XML profile (needs a .gitattributes override; no SVG profile exists)"
mk m4 'd.svg merge=mergiraf'
cat > d.svg <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg">
  <defs>
  </defs>
  <rect id="r1" x="0" y="0" width="15" height="15" fill="#ccc"/>
  <rect id="r2" x="20" y="0" width="15" height="15" fill="#ccc"/>
  <rect id="r3" x="40" y="0" width="15" height="15" fill="#ccc"/>
</svg>
EOF
cb
python3 -c "
t=open('d.svg').read().replace('  <defs>\n','  <defs>\n    <linearGradient id=\"grad1\"><stop stop-color=\"red\"/></linearGradient>\n').replace('id=\"r1\" x=\"0\" y=\"0\" width=\"15\" height=\"15\" fill=\"#ccc\"','id=\"r1\" x=\"0\" y=\"0\" width=\"15\" height=\"15\" fill=\"url(#grad1)\"')
open('d.svg','w').write(t)"
sw
python3 -c "
t=open('d.svg').read().replace('  </defs>','    <linearGradient id=\"grad1\"><stop stop-color=\"blue\"/></linearGradient>\n  </defs>').replace('id=\"r3\" x=\"40\" y=\"0\" width=\"15\" height=\"15\" fill=\"#ccc\"','id=\"r3\" x=\"40\" y=\"0\" width=\"15\" height=\"15\" fill=\"url(#grad1)\"')
open('d.svg','w').write(t)"
dm
echo "--- result:"; sed 's/^/    /' d.svg
python3 -c "
import xml.etree.ElementTree as ET,re,collections
t=open('d.svg').read()
try:
  ET.fromstring(t); print('    XML well-formed')
  ids=re.findall(r'id=\"([^\"]+)\"',t)
  print('    ids',ids,'dups',[k for k,v in collections.Counter(ids).items() if v>1])
except Exception as e: print('    NOT well-formed:',e)"

hdr "M5 CSV: mergiraf has NO CSV profile — what happens?"
mk m5 't.csv merge=mergiraf'
printf 'id,name,email,phone\n1,a,a@x,1\n2,b,b@x,2\n3,c,c@x,3\n' > t.csv
cb; sed -i 's/^2,b,b@x,2/2,b,b@x,9999/' t.csv
sw; sed -i 's/^2,b,b@x,2/2,b,new@x,2/' t.csv
dm
echo "--- result:"; sed 's/^/    /' t.csv

hdr "M6 mergiraf on a file it cannot PARSE (broken JSON) — fallback behaviour"
mk m6 'cfg.json merge=mergiraf'
printf '{\n  "a": 1,\n  "b": 2,\n  "c": 3\n' > cfg.json   # missing closing brace = parse error
cb; sed -i 's/"a": 1/"a": 11/' cfg.json
sw; sed -i 's/"c": 3/"c": 33/' cfg.json
dm
echo "--- result:"; sed 's/^/    /' cfg.json

hdr "M7 markdown prose: two authors edit ADJACENT paragraphs (classic false conflict)"
mk m7 'p.md merge=mergiraf'
printf '# T\n\nAlpha paragraph one.\n\nBeta paragraph two.\n' > p.md
cb; sed -i 's/Alpha paragraph one./Alpha paragraph one, revised by B./' p.md
sw; sed -i 's/Beta paragraph two./Beta paragraph two, revised by A./' p.md
dm
echo "--- result:"; sed 's/^/    /' p.md

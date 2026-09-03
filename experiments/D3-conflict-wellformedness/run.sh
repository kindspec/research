#!/bin/bash
# Does a git-conflicted structured file still parse?
set -u
W="$(cd "$(dirname "$0")" && pwd)/work"; rm -rf "$W"; mkdir -p "$W"; cd "$W"
GIT="git -c user.name=T -c user.email=t@e -c init.defaultBranch=main"
$GIT init -q .

# ---------- seed all formats ----------
cat > data.csv <<'EOF'
id,name,dept,salary
1,Alice,Eng,100
2,Bob,Sales,90
3,Carol,Eng,110
EOF
cat > data.json <<'EOF'
{
  "team": "core",
  "members": [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
  ],
  "budget": 1000
}
EOF
cat > pic.svg <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
  <rect x="10" y="10" width="50" height="30" fill="red"/>
  <circle cx="120" cy="50" r="20" fill="blue"/>
  <text x="10" y="90">hello</text>
</svg>
EOF
cat > conf.yaml <<'EOF'
title: Report
author: Alice
tags:
  - a
  - b
draft: true
EOF
cat > post.md <<'EOF'
---
title: Report
author: Alice
---

# Heading

Body text here.
EOF
cat > sheet.fods <<'EOF'
<?xml version="1.0"?>
<office:document xmlns:office="urn:x" xmlns:table="urn:t">
 <table:table table:name="S1">
  <table:table-row><table:table-cell office:value="1"/></table:table-row>
  <table:table-row><table:table-cell office:value="2"/></table:table-row>
 </table:table>
</office:document>
EOF
$GIT add -A; $GIT commit -qm base

# ---------- branch A ----------
$GIT checkout -qb A
sed -i 's/2,Bob,Sales,90/2,Bob,Marketing,95/' data.csv
sed -i 's/"budget": 1000/"budget": 2000/' data.json
sed -i 's/fill="blue"/fill="green"/' pic.svg
sed -i 's/^author: Alice/author: Alice Smith/' conf.yaml
sed -i 's/^author: Alice/author: Alice Smith/' post.md
sed -i 's|office:value="2"|office:value="22"|' sheet.fods
$GIT commit -qam A

# ---------- branch main ----------
$GIT checkout -q main
sed -i 's/2,Bob,Sales,90/2,Bob,Support,80/' data.csv
sed -i 's/"budget": 1000/"budget": 3000/' data.json
sed -i 's/fill="blue"/fill="yellow"/' pic.svg
sed -i 's/^author: Alice/author: Alicia/' conf.yaml
sed -i 's/^author: Alice/author: Alicia/' post.md
sed -i 's|office:value="2"|office:value="99"|' sheet.fods
$GIT commit -qam M

echo "########## git merge A ##########"
$GIT merge A 2>&1
echo
echo "########## CONFLICTED FILES, VERBATIM ##########"
for f in data.csv data.json pic.svg conf.yaml post.md sheet.fods; do
  echo "----------------------------------------- $f"
  cat "$f"
done

echo
echo "########## DOES IT STILL PARSE? ##########"
p(){ printf '  %-12s %-22s : %s\n' "$1" "$2" "$3"; }

# CSV
out=$(python3 -c "
import csv,sys
rows=list(csv.reader(open('data.csv')))
print('parsed OK, %d rows, widths=%s' % (len(rows), sorted({len(r) for r in rows})))
" 2>&1) ; p data.csv "python csv" "$out"
out=$(python3 -c "
import pandas" 2>&1 >/dev/null && echo yes || echo "pandas absent")
# JSON
out=$(python3 -c "import json;json.load(open('data.json'));print('parsed OK')" 2>&1 | tail -1); p data.json "python json" "$out"
out=$(jq . data.json 2>&1 | tail -1); p data.json "jq" "$out"
# SVG / XML
out=$(python3 -c "
import xml.etree.ElementTree as ET
ET.parse('pic.svg'); print('parsed OK')" 2>&1 | tail -1); p pic.svg "ElementTree" "$out"
# YAML
out=$(python3 -c "
import yaml; yaml.safe_load(open('conf.yaml')); print('parsed OK')" 2>&1 | tail -1); p conf.yaml "pyyaml" "$out"
# MD frontmatter
out=$(python3 -c "
import yaml
t=open('post.md').read()
assert t.startswith('---')
fm=t.split('---',2)[1]
yaml.safe_load(fm); print('frontmatter parsed OK')" 2>&1 | tail -1); p post.md "frontmatter" "$out"
# FODS
out=$(python3 -c "
import xml.etree.ElementTree as ET
ET.parse('sheet.fods'); print('parsed OK')" 2>&1 | tail -1); p sheet.fods "ElementTree" "$out"

echo
echo "########## Same question under merge.conflictStyle=diff3 and zdiff3 ##########"
for style in diff3 zdiff3; do
  $GIT merge --abort 2>/dev/null
  $GIT -c merge.conflictStyle=$style merge A >/dev/null 2>&1
  echo "--- $style, data.json:"; cat data.json
  o=$(python3 -c "import json;json.load(open('data.json'));print('OK')" 2>&1|tail -1); echo "    parse: $o"
done
$GIT merge --abort 2>/dev/null

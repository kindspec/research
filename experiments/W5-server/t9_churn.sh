#!/bin/bash
# W5-T9: the server RE-RENDERS the file from its parsed model. How much
# whitespace churn does that inject into `git diff` / review / blame?
set -u
export GIT_CONFIG_NOSYSTEM=1 GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t \
       GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t GIT_CONFIG_GLOBAL=/dev/null
H=$(cd "$(dirname "$0")" && pwd); W=$H/work-t9; rm -rf "$W"; mkdir -p "$W"; cd "$W"
git init -q --bare srv.git; git init -q dev; cd dev
python3 - <<'PY'
# a self-consistent, tool-rendered table (header and data at the same widths)
ids=[f"r_{i:04d}" for i in range(1,41)]; items=[f"item{i}" for i in range(1,41)]
qtys=[f"{i*3}" for i in range(1,41)];    units=[f"{i*1.5:.2f}" for i in range(1,41)]
cols=["id","item","qty","unit"]; data=[ids,items,qtys,units]
w=[max(len(c),*(len(v) for v in col)) for c,col in zip(cols,data)]
def row(vals): return "| "+" | ".join(v.ljust(w[j]) if j<2 else v.rjust(w[j])
                                      for j,v in enumerate(vals))+" |"
sep="| "+" | ".join(("-"*w[j] if j<2 else "-"*(w[j]-1)+":") for j in range(4))+" |"
open('b.tbl','w').write(row(cols)+"\n"+sep+"\n"
    +"\n".join(row([data[j][i] for j in range(4)]) for i in range(40))
    +"\n\ngrand := sum(qty)\n")
PY
git add -A; git commit -qm base >/dev/null; git branch -M main; git push -q ../srv.git main
git checkout -q -b topic
python3 -c "
import re;p='b.tbl';s=open(p).read()
s2=re.sub(r'(?m)^(\\| r_0005 \\| *item5 *\\| *)15( \\|)', r'\\g<1>99\\g<2>', s)
assert s2!=s, 'theirs sed did not match'; open(p,'w').write(s2)"
git commit -qam 'theirs: r_0005 qty 15->99' >/dev/null; git push -q ../srv.git topic
git checkout -q main
python3 -c "
import re;p='b.tbl';s=open(p).read(); s2=re.sub(r'(?m)^(\\| r_0020 \\|.*\\| *)30\\.00( \\|)', r'\\g<1>31.00\\g<2>', s)
assert s2!=s, 'ours sed did not match'; open(p,'w').write(s2)"
git commit -qam 'ours: r_0020 unit 30.00->31.00' >/dev/null; git push -q ../srv.git main
cd "$W"
echo "40-row table. Each side changed exactly ONE cell, in different rows."
python3 "$H/gws_merge_server.py" merge --repo srv.git --into refs/heads/main --from refs/heads/topic | sed 's/^/  /'
echo "  parents of the merge: $(git -C srv.git rev-list --parents -n1 main | wc -w) (1 commit + 2 parents = 3)"
echo
echo "--- diff of the merge commit against its FIRST parent (ours) ---"
git -C srv.git diff --stat main^1 main -- b.tbl | sed 's/^/  /'
echo "  changed lines: $(git -C srv.git diff -U0 main^1 main -- b.tbl | grep -cE '^[+-][^+-]')"
echo "  (a perfect merge would change exactly 1 line: theirs' single cell)"
echo
echo "--- the actual changed lines ---"
git -C srv.git diff -U0 main^1 main -- b.tbl | grep -E '^[+-][^+-]' | head -20 | sed 's/^/  /'

echo
echo "=================================================================="
echo "### PART 2: a merge the SERVER actually re-renders (same-line conflict)"
echo "=================================================================="
cd "$W"; rm -rf srv2.git dev2; git init -q --bare srv2.git; git init -q dev2; cd dev2
python3 - <<'PY'
# a self-consistent, tool-rendered table (header and data at the same widths)
ids=[f"r_{i:04d}" for i in range(1,41)]; items=[f"item{i}" for i in range(1,41)]
qtys=[f"{i*3}" for i in range(1,41)];    units=[f"{i*1.5:.2f}" for i in range(1,41)]
cols=["id","item","qty","unit"]; data=[ids,items,qtys,units]
w=[max(len(c),*(len(v) for v in col)) for c,col in zip(cols,data)]
def row(vals): return "| "+" | ".join(v.ljust(w[j]) if j<2 else v.rjust(w[j])
                                      for j,v in enumerate(vals))+" |"
sep="| "+" | ".join(("-"*w[j] if j<2 else "-"*(w[j]-1)+":") for j in range(4))+" |"
open('b.tbl','w').write(row(cols)+"\n"+sep+"\n"
    +"\n".join(row([data[j][i] for j in range(4)]) for i in range(40))
    +"\n\ngrand := sum(qty)\n")
PY
git add -A; git commit -qm base >/dev/null; git branch -M main; git push -q ../srv2.git main
git checkout -q -b topic
python3 -c "
p='b.tbl';s=open(p).read();import re;s2=re.sub(r'(?m)^(\\| r_0007 \\| *item7 *\\| *)21( \\|)', r'\\g<1>77\\g<2>', s)
assert s2!=s; open(p,'w').write(s2)"
git commit -qam 'theirs: r_0007 QTY' >/dev/null; git push -q ../srv2.git topic
git checkout -q main
python3 -c "
import re;p='b.tbl';s=open(p).read();s2=re.sub(r'(?m)^(\\| r_0007 \\|.*\\| *)10\\.50( \\|)', r'\\g<1>99.50\\g<2>', s)
assert s2!=s; open(p,'w').write(s2)"
git commit -qam 'ours: r_0007 UNIT' >/dev/null; git push -q ../srv2.git main
cd "$W"
echo "Both sides edited DIFFERENT CELLS OF THE SAME LINE -> git conflicts,"
echo "the type-aware merger runs, and the file is re-rendered from the model."
python3 "$H/gws_merge_server.py" merge --repo srv2.git --into refs/heads/main --from refs/heads/topic | sed 's/^/  /'
echo
echo "--- diff of merge vs its first parent (ours) ---"
git -C srv2.git diff --stat main^1 main -- b.tbl | sed 's/^/  /'
echo "  changed lines: $(git -C srv2.git diff -U0 main^1 main -- b.tbl | grep -cE '^[+-][^+-]')"
echo "  (2 = one line replaced. >2 means the re-render churned unrelated lines.)"
git -C srv2.git diff -U0 main^1 main -- b.tbl | grep -E '^[+-][^+-]' | sed 's/^/  /'

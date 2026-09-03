#!/bin/bash
# W5-T8: idempotence.  The same merge request, issued 10 times.
set -u
export GIT_CONFIG_NOSYSTEM=1 GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t \
       GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t GIT_CONFIG_GLOBAL=/dev/null
H=$(cd "$(dirname "$0")" && pwd); W=$H/work-t8; rm -rf "$W"; mkdir -p "$W"; cd "$W"
git init -q --bare srv.git; git init -q dev; cd dev
printf '| id     | item | qty | unit |\n| ------ | ---- | --: | ---: |\n| r_0001 | a    |   1 |    5 |\n\ngrand := sum(qty)\n' > b.tbl
git add -A; git commit -qm base >/dev/null; git branch -M main; git push -q ../srv.git main
git checkout -q -b topic; sed -i 's/|   1 |/|  11 |/' b.tbl; git commit -qam t >/dev/null; git push -q ../srv.git topic
git checkout -q main; sed -i 's/|    5 |/|   50 |/' b.tbl; git commit -qam o >/dev/null; git push -q ../srv.git main
cd "$W"
echo "run  status          main"
for i in $(seq 1 10); do
  S=$(python3 "$H/gws_merge_server.py" merge --repo srv.git --into refs/heads/main --from refs/heads/topic | python3 -c 'import json,sys;print(json.load(sys.stdin)["status"])')
  printf "%3d  %-15s %s\n" "$i" "$S" "$(git -C srv.git rev-parse --short main)"
done
echo
echo "merge commits on main : $(git -C srv.git rev-list --merges --count main)  (must be 1)"
echo "total commits on main : $(git -C srv.git rev-list --count main)"
echo "b.tbl:"; git -C srv.git cat-file -p main:b.tbl | sed 's/^/  /'
echo "fsck: $(git -C srv.git fsck --strict 2>&1 | grep -c error) errors"

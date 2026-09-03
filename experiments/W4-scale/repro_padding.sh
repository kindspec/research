#!/bin/sh
# Minimal reproduction of the padding/locality defect. Run: sh repro_padding.sh
set -e
W=${1:-/tmp/padrepro}; rm -rf "$W"; mkdir -p "$W/pad" "$W/nopad"
mk() {  # $1=dir  $2=pad(1/0)
  cd "$W/$1"; git init -q -b main .
  python3 - "$2" <<'PY'
import sys
pad = sys.argv[1] == '1'
rows = [['r_%04d' % i, 'widget-%04d' % i, str(i % 9 + 1), '%.2f' % (i + 1)] for i in range(200)]
hdr = ['id', 'item', 'n', 'total = n * price']
al  = ['---', '---', '--:', '--:']
cells = [hdr, al] + [r for r in rows]
def render(cells, pad):
    if not pad: return '\n'.join('| ' + ' | '.join(r) + ' |' for r in cells) + '\n'
    w = [max(len(r[j]) for r in cells) for j in range(len(hdr))]
    return '\n'.join('| ' + ' | '.join(c.ljust(w[j]) for j, c in enumerate(r)) + ' |' for r in cells) + '\n'
open('data.tbl','w').write(render(cells, pad))
rows[100][2] = '1000'          # one cell: 9 -> 1000
open('edited.tbl','w').write(render([hdr, al] + rows, pad))
PY
  git add data.tbl; git commit -qm base; cp edited.tbl data.tbl
  printf '%s: ' "$1"; git diff --numstat -- data.tbl
  cd - >/dev/null
}
mk pad 1
mk nopad 0

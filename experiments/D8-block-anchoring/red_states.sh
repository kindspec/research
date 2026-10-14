#!/usr/bin/env bash
# Show that each check in scope.py can fail. Each case copies scope.py into a
# fresh temporary tree beside copies of ../D8-identity and arms.json, applies
# one mutation, confirms the mutation changed the file (BROKEN otherwise, never
# a pass), runs it, and passes only on the expected exit code and output.
#
# usage: ./red_states.sh CMSPEC_CLONE OBSIDIAN_HELP_CLONE
set -u
here=$(cd "$(dirname "$0")" && pwd)
cm=${1:?cmspec clone}
ob=${2:?obsidian-help clone}
fail=0

run_case() {  # name, python mutation (reads/writes s), args, want_exit, want_regex
    local name=$1 mut=$2 args=$3 want_exit=$4 want=$5 tmp out code before after
    tmp=$(mktemp -d)
    mkdir -p "$tmp/x/D8-block-anchoring" "$tmp/x/D8-block-definitions"
    cp -r "$here/../D8-identity" "$tmp/x/D8-identity"
    cp "$here/../D8-block-definitions/arms.json" "$tmp/x/D8-block-definitions/"
    cp "$here/scope.py" "$tmp/x/D8-block-anchoring/"
    before=$(sha256sum "$tmp/x/D8-block-anchoring/scope.py" | cut -c1-16)
    MUT="$mut" python3 - "$tmp/x/D8-block-anchoring/scope.py" <<'PY'
import os, sys
p = sys.argv[1]; s = open(p).read()
old, new = os.environ["MUT"].split("\n=>\n") if os.environ["MUT"] else ("", "")
if old:
    assert s.count(old) == 1, f"pattern matches {s.count(old)} times: {old!r}"
    s = s.replace(old, new)
open(p, "w").write(s)
PY
    after=$(sha256sum "$tmp/x/D8-block-anchoring/scope.py" | cut -c1-16)
    if [ -n "$mut" ] && [ "$before" = "$after" ]; then
        echo "BROKEN    $name: mutation did not change scope.py"; fail=1; rm -rf "$tmp"; return
    fi
    out=$(cd "$tmp" && eval python3 -I "$tmp/x/D8-block-anchoring/scope.py" "$args" 2>&1)
    code=$?
    if [ "$code" = "$want_exit" ] && grep -qE "$want" <<<"$out"; then
        echo "RED       $name: exit $code, matched /$want/"
    else
        echo "UNEXPECTED $name: exit $code (want $want_exit), /$want/ not matched"; fail=1
        tail -5 <<<"$out"
    fi
    rm -rf "$tmp"
}

run_case "missing clone" "" "--clone cmspec=/nonexistent --arm cmspec" 2 "clone does not exist"

run_case "resolve() drifts from reanchor2" \
'        if r >= FUZZ:
            cands.append((r, i))
=>
        if r >= FUZZ + 0.3:
            cands.append((r, i))' \
"--clone cmspec=$cm --arm cmspec" 1 "disagrees with D8's reanchor2"

run_case "oracle target off by one" \
'        return "correct" if hit == tgt else ("loud" if hit is None else "WRONG")
=>
        return "correct" if hit == (tgt + 1) else ("loud" if hit is None else "WRONG")' \
"--clone cmspec=$cm --arm cmspec" 0 "F    correct +0\.0% .*WRONG 100\.0%"

run_case "B stage 2 searches the whole file" \
'    sub = [n for n, y in enumerate(dj.leaves) if inside(y, scope_cands[h])]
=>
    sub = list(range(len(dj.leaves)))' \
"--clone obsidian-help=$ob --arm obsidian-help" 0 "obsidian-help +3020 +46 +1\.5%"

exit $fail

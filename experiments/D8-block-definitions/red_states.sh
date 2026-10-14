#!/usr/bin/env bash
# Every refusal measure.py makes -- each die() call site -- shown to fire, each
# for the reason it names.
#
#   experiments/D8-block-definitions/red_states.sh \
#     rust-book=PATH obsidian-help=PATH cmspec=PATH \
#     kubernetes-website=PATH cncf-toc=PATH site-policy=PATH > red-states.txt
#
# A case passes only when the exit code is the one expected AND stderr holds
# the expected message, so a case cannot pass on an earlier, unrelated refusal.
# The last case is the control: the unmodified run must exit 0.
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
M="$HERE/measure.py"
declare -A C
ARGS=()
for kv in "$@"; do C[${kv%%=*}]=${kv#*=}; ARGS+=(--clone "$kv"); done
for k in rust-book obsidian-help cmspec kubernetes-website cncf-toc site-policy; do
  [ -n "${C[$k]:-}" ] || { echo "red_states.sh: need $k=PATH" >&2; exit 64; }
done

S=$(mktemp -d); trap 'rm -rf "$S"' EXIT
fails=0

case_() {  # case_ <label> <want-exit> <want-stderr-substring> <cmd...>
  local label=$1 want=$2 msg=$3; shift 3
  set +e; "$@" > "$S/out" 2> "$S/err"; local rc=$?; set -e
  local ok=no
  if [ "$rc" -eq "$want" ] && { [ -z "$msg" ] || grep -qF -- "$msg" "$S/err"; }; then ok=yes; fi
  [ $ok = yes ] || fails=$((fails + 1))
  echo "== $label"
  echo "   exit=$rc (want $want)${msg:+, stderr has \"$msg\"} -> $([ $ok = yes ] && echo as-expected || echo UNEXPECTED)"
  { grep -v '^arm .* (pin)$' "$S/err" || true; } | head -2 | sed "s|$S|\$SCRATCH|g; s/^/   stderr| /"
}

with() {  # ARGS with one clone replaced: with KEY PATH
  local out=() k=$1 p=$2
  for kv in "${ARGS[@]}"; do
    if [ "$kv" = "$k=${C[$k]}" ]; then out+=("$k=$p"); else out+=("$kv"); fi
  done
  printf '%s\n' "${out[@]}"
}
run_with() { local k=$1 p=$2; shift 2; mapfile -t a < <(with "$k" "$p"); python3 -I "$M" "${a[@]}" "$@"; }

# a scratch repository: one commit, with whatever files the case needs
mkrepo() {  # mkrepo <dir> <file> <content>
  git -c init.defaultBranch=main init -q "$1"
  printf '%s' "$3" > "$1/$2"
  git -C "$1" -c user.name=t -c user.email=t@t add "$2"
  git -C "$1" -c user.name=t -c user.email=t@t commit -qm t
  git -C "$1" rev-parse HEAD
}
arms() {  # arms <file> <name> <pin> <pathspec>: a one-arm arms.json
  printf '{"arms": [{"name": "%s", "clone": "scratch", "pin": "%s", "pathspec": "%s"}]}\n' "$2" "$3" "$4" > "$1"
}

mkdir "$S/empty"
case_ "clone path is not a git work tree" 2 "not a git work tree" \
  run_with rust-book "$S/empty"
case_ "clone path does not exist" 2 "clone does not exist" \
  run_with rust-book "$S/nonexistent"
case_ "clone at the wrong commit" 2 "rust-book: HEAD is" \
  run_with rust-book "${C[obsidian-help]}"
case_ "no --clone for an arm" 2 "no --clone obsidian-help=PATH" \
  python3 -I "$M" --clone "rust-book=${C[rust-book]}"

git -c init.defaultBranch=main -c advice.detachedHead=false clone -q "${C[cmspec]}" "$S/dirty"
git -C "$S/dirty" -c advice.detachedHead=false checkout -q 3da939428d80f146f270cd1765e4ba462e96bb1b
f=$(git -C "$S/dirty" ls-files '*.md' | head -1)
printf 'an uncommitted edit\n' >> "$S/dirty/$f"
case_ "tracked file modified in the clone" 2 "cmspec: tracked files differ from HEAD" \
  run_with cmspec "$S/dirty"

P=$(mkrepo "$S/one" a.md $'# A heading\n\nOne paragraph of prose that is long enough to count.\n')
arms "$S/nomatch.json" one "$P" 'nomatch/*.md'
case_ "pathspec selects no .md file" 2 "selects no .md files" \
  python3 -I "$M" --arms "$S/nomatch.json" --clone "scratch=$S/one"
B=$(mkrepo "$S/blank" a.md $'\n\n')
arms "$S/blank.json" blank "$B" '*.md'
case_ "files read, no block found" 2 "found no block" \
  python3 -I "$M" --arms "$S/blank.json" --clone "scratch=$S/blank"
arms "$S/one.json" one "$P" '*.md'
case_ "arms without D8's three, so no validation" 2 "the validation step needs D8's three arms" \
  python3 -I "$M" --arms "$S/one.json" --clone "scratch=$S/one"

mkdir "$S/one/sub"
case_ "clone path is a subdirectory of a work tree" 2 "is inside a work tree rooted at" \
  python3 -I "$M" --arms "$S/one.json" --clone "scratch=$S/one/sub"
G=$(mkrepo "$S/gen" a.md $'---\nauto_generated: true\n---\n\nOne paragraph of prose that is long enough to count.\n')
arms "$S/gen.json" gen "$G" '*.md'
case_ "every selected file is generated" 2 "every selected file is generated or unreadable" \
  python3 -I "$M" --arms "$S/gen.json" --clone "scratch=$S/gen"
arms "$S/badspec.json" one "$P" ':(nosuchmagic)*.md'
case_ "git fails (ls-files on an invalid pathspec)" 2 "ls-files :(nosuchmagic)*.md: exit 128" \
  python3 -I "$M" --arms "$S/badspec.json" --clone "scratch=$S/one"
case_ "--clone without KEY=PATH" 2 "--clone wants KEY=PATH" \
  python3 -I "$M" --clone "rust-book"
case_ "--d8-dir without the D8 scripts" 2 "--d8-dir has no anchor_eval3.py" \
  python3 -I "$M" "${ARGS[@]}" --d8-dir "$S/empty"
case_ "--show names no definition" 2 "--show wants DEF:ARM, DEF one of a0, a1" \
  python3 -I "$M" "${ARGS[@]}" --show zz:rust-book

cp -r "$HERE/../D8-identity" "$S/d8"
before=$(sha256sum < "$S/d8/results-e4.txt")
sed -i '0,/ 2938 /s// 2939 /' "$S/d8/results-e4.txt"
after=$(sha256sum < "$S/d8/results-e4.txt")
if [ "$before" = "$after" ]; then
  echo "== validation against an altered results-e4.txt"
  echo "   BROKEN: the alteration did not apply"; fails=$((fails + 1))
else
  mapfile -t a < <(with rust-book "${C[rust-book]}")
  case_ "validation against an altered results-e4.txt" 1 "validation failed" \
    python3 -I "$M" "${a[@]}" --d8-dir "$S/d8"
fi

mkdir -p "$S/fake/markdown_it"
printf '__version__ = "0.0.0"\n' > "$S/fake/markdown_it/__init__.py"
case_ "parser is not markdown-it-py 3.0.0" 2 "this measurement is pinned to 3.0.0" \
  env PYTHONPATH="$S/fake" PYTHONDONTWRITEBYTECODE=1 python3 "$M" "${ARGS[@]}"

case_ "control: the unmodified run" 0 "" python3 -I "$M" "${ARGS[@]}"

echo
echo "unexpected: $fails"
[ "$fails" -eq 0 ]

# D8-block-anchoring: which node stage 1 of a quote anchor resolves

D8's two-stage quote anchor (`design-findings/D8-identity.md` §3.4 and §7.3)
finds a block first and the anchored span inside it second. Which block stage
1 looks for is part of kindspec/blockspec#4, "what is a block?".
`D8-block-definitions/` measured how unique each candidate unit is at one
tree. It did not measure edits ("What this does not measure"). This
experiment does: real file histories, D8's hardened resolver, and D8's
independent line oracle.

It also carries the measurements behind the two cases argued in blockspec#4,
under `cases/`.

    scope.py         the measurement: four ways to scope stage 1, graded by an oracle
    results.txt      scope.py's stdout over six arms
    red_states.sh    each check in scope.py, broken on purpose and shown to fail
    red-states.txt   red_states.sh's stdout
    probe.py         where markers and pipe tables land in the CommonMark tree
    probe.txt        probe.py's stdout
    cases/top-level/ the case for a top-level node, with a list as one block
    cases/leaf/      the case for a leaf node at any depth

## What scope.py measures

The anchored text is a **leaf** of at least 20 characters that sits inside a
top-level list or block quote. A leaf is a paragraph, heading, code block,
HTML block or table, at any depth. Outside a container, a leaf is its own
top-level node, and every scheme below is the same scheme. Inside one, they
differ:

| scheme | stage 1 resolves | then |
|---|---|---|
| B | the top-level node that contains the leaf; a list is one node | the leaf, searched only inside that node |
| D | the smallest list item that contains the leaf, or the top-level node when none does (a block quote) | the leaf, searched only inside that item |
| F | the leaf itself, among every leaf in the file | nothing |
| F+B | F; when F's exact match is ambiguous after context, B | |
| F+Bc | F; B only for an anchor whose leaf was already ambiguous in the version it was taken against | |

Every lookup uses D8's hard policy, `anchor_eval3.reanchor2(hard=True)`, with
one change. A candidate's suffix context is read from the end of its source
lines, not from `off + len(content)`, because a nested leaf's content has its
container prefixes removed and is not a substring of the file. For a
top-level node the two are the same. Every run checks that its copy and
`reanchor2` agree on every stage-1 B lookup and exits 1 if they do not; the
check ran 50,824 times without a difference (`results.txt`, last line).

Content follows `D8-block-definitions/measure.py`: a top-level node's source
lines, stripped; an item's lines with the marker and any `>` prefix removed
and each line left-stripped; a paragraph's inline source; a heading's `#`s
plus text; a fence's markup, info string and body; a table's lines, each
stripped.

**Truth** is D8's line oracle, `anchor_eval2.line_oracle`'s rule applied to
leaves. difflib maps the lines of the earlier version onto the later one. If at
least half of the leaf's non-blank lines survive, the target is the later leaf
that holds most of them. If none survive and no later leaf is 30% similar, the
leaf was deleted. Anything else is unknown and is not counted. An anchor is
**correct** when it resolves to the oracle's leaf, or refuses a deleted one;
**loud** when it refuses a leaf that survived; **WRONG** otherwise.

**Pairs** are D8's: up to 60 `.md` files per arm, shuffled with seed 7; for
each, up to three start commits along the file's own `git log`, each paired
with the version `gap` file-commits later; up to 30 anchors per pair. Files
holding PRE-REGISTRATION-2 §6.3's generated-file markers are skipped.

**At rest** resolves every eligible leaf of every file at the pin against its
own unchanged file. Anything but the leaf itself is a failure. A loud failure
here means an anchor that refuses before anyone has edited anything: two
copies of the same text that context does not separate.

**Stored size** is the length of the stage-1 quote each scheme keeps in the
sidecar, per anchor, at rest. This is D8 §7.3's `block.exact`.

## Arms

Six of `D8-block-definitions/arms.json`'s seven arms, at the same pins. Each
clone must be at its pin with no tracked changes, and a full clone, because
this walks file history. `k8s-l10n` is left out. It reads the same clone as
`k8s-en`, its edits are translations, and it holds more leaves than the other
six arms together: 180,848 against 110,049 at 40 characters or more, the
`f leaf` rows of `D8-block-definitions/results.txt`, "Summary, minlen=40".

    python3 -I scope.py \
      --clone rust-book=PATH --clone obsidian-help=PATH --clone cmspec=PATH \
      --clone kubernetes-website=PATH --clone cncf-toc=PATH \
      --clone site-policy=PATH > results.txt

    ./red_states.sh CMSPEC_PATH OBSIDIAN_HELP_PATH > red-states.txt

The parser is markdown-it-py 3.0.0, preset `commonmark` with GFM tables, as in
`D8-block-definitions/`. `scope.py` refuses any other version. Its output
holds counts only and quotes no corpus text. Two full runs gave the same
figures; the second added the F+Bc scheme and changed nothing else.

## Red states

`red_states.sh` copies `scope.py` into a temporary tree, applies one mutation,
confirms that the file's hash changed (it prints BROKEN otherwise, never a
pass), runs it, and passes the case only on the expected exit code and output:

| mutation | expected | what it shows |
|---|---|---|
| none, `--clone` to a missing path | exit 2 | a missing corpus is refused, not read as empty |
| `resolve()`'s fuzzy threshold raised by 0.3 | exit 1 | the agreement check with `reanchor2` fires |
| the oracle's target shifted by one leaf | every F anchor WRONG | the oracle and the classifier are live |
| B's stage 2 searches every leaf in the file, not the node stage 1 found | B's at-rest loud count on `obsidian-help` rises from 0 to 46, F's figure | B's advantage at rest comes from narrowing stage 2, not from the list being unique |

## cases/

The two cases argued in blockspec#4 measured with their own scripts. They are
committed as run, except that absolute paths to `D8-identity/` and the
working directory were replaced by paths relative to the script, and the clone
prefix was cut from the `repo=` lines of `edits.txt` and `edits2.txt`. Every
output was re-run from these copies at the pins. Each matched the case's own
output, apart from arm order in `edit-run.txt` and the `repo=` prefix:

    cases/top-level/edit_b_vs_d.py  a top-level list item anchored as (b), the list
                                    then the item, and as (d), the item; line oracle
    cases/top-level/rest.py         the same two, at rest
    cases/top-level/sizes.py        top-level list sizes
    cases/top-level/probe.py        marker placement and list splitting
    cases/leaf/edits.py             stage-1 exact-match counts, (b) list vs (f) leaf,
                                    obsidian-help, gaps 1, 5 and 25
    cases/leaf/edits2.py            stage-1 status under reanchor2, (b) vs (f); no oracle

Usage, with a clone at each pin:

    python3 -I cases/top-level/edit_b_vs_d.py NAME=REPO:PATHSPEC ...   # gaps 5 and 25
    python3 -I cases/top-level/rest.py NAME=REPO:PATHSPEC ...
    python3 -I cases/top-level/sizes.py NAME=REPO:PATHSPEC ...
    python3 -I cases/leaf/edits.py REPO PATHSPEC GAP MAXFILES
    python3 -I cases/leaf/edits2.py REPO PATHSPEC GAP MAXFILES

`edits2.py` reports stage-1 status (EXACT, FUZZY, refusals) and has no oracle,
so it cannot say which resolutions are right. `scope.py` grades the same
question with the oracle.

## What this does not measure

- **Stage 2.** No sub-leaf span is anchored. D8 §3.4 measured spans inside a
  block under D8's splitter.
- **A span that crosses leaves**, such as a selection over three bullets.
- **The disambiguator an anchor would need** for text that is already
  ambiguous when it is anchored. F+Bc shows what one choice of disambiguator
  does. It is not the only choice.
- **djot**, **Hugo shortcodes** and **Obsidian callouts**, for the reasons
  `D8-block-definitions/README.md` gives.

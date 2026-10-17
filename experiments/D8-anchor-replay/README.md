# D8-anchor-replay: blockspec's anchor resolver on real document history

blockspec adjudication 0003 §12 names, first among what would reverse its
anchor design, "A replay over real history that prices the refusals": the
resolver adds refusals (near-copy, refilled-gap, crowded-gap, twin and
context rules, and the alignment) whose rate on real edits is unknown. This
experiment is a harness for that replay. It runs real file histories against
the blockspec reference resolver and grades each resolution with D8's line
oracle.

    replay.py                  the measurement
    red_states.py              its grading broken four ways, on a fixture, each checked
    red-states.txt             red_states.py's stdout
    red_sweep.py               replay.py's grader and oracle broken six ways; red_states.py must fail each
    red-sweep.txt              red_sweep.py's stdout
    rehearsal-site-policy.txt  replay.py's stdout on the rehearsal arm

**Nothing here is a verdict.** The arms that would decide anything have not
been run. **The oracle cannot yet price the refusals 0003 names** (below),
so it cannot decide a bar on the refusal rate either: it gives a lower and
an upper bound. Only the rehearsal arm, `site-policy`, has been run.

## What replay.py measures

For each arm, each of 60 sampled files, and up to three sampled pairs of
versions GAP commits apart in that file's history (gaps 1, 5 and 25):

- every paragraph of the earlier version with at least 20 characters gets a
  comment on three words from its middle, made as blockspec `SPEC.md` §11.1
  creates one; a window whose span or `prefix + span + suffix` is not unique
  in the paragraph is passed over for the next nearest, and a paragraph with
  none gets no comment;
- the comment is resolved against the later version by the reference
  resolver (`blockspec.anchor.resolve`), with the earlier version as `base`;
- **truth** is D8's line oracle (`../D8-identity/anchor_eval2.py`,
  `line_oracle`'s rule), applied to paragraphs. difflib maps the earlier
  file's lines onto the later's, split as the reader splits them. If at
  least half of the paragraph's non-blank lines survive, its target is the
  later paragraph holding most of them. If none survive and no later
  paragraph is 30% similar, it was deleted. Anything else is unknown and is
  not counted.

A comment is graded against the oracle's target:

| truth | `correct` | `loud` | `WRONG` |
| --- | --- | --- | --- |
| the span occurs once in the target | resolves there, on that span | refused, `DETACHED` or `ORPHANED` | resolves anywhere else |
| the span is gone from the target, or the paragraph was deleted | loud | — | resolves |

A span that occurs more than once in the target is not counted. Each `loud`
is reported with its status and refusal reason.

Every comment that is not counted is reported too, by the resolver's
status, and the report gives two rates of refusing text that survived: the
lower counts only comments the oracle places; the upper also counts every
loud comment it does not place, as if its text had survived. Comments on a
version whose later version the profile refuses (`SPEC.md` §4) are counted
separately: each of them resolves `REFUSED(not-in-profile)`.

## What the oracle cannot see

- **An edited one-line paragraph, and a moved paragraph.** A one-line
  paragraph that is edited keeps none of its lines, and a later paragraph
  is at least 30% like it, so the oracle says unknown. difflib's matching
  does not follow moves either. On site-policy almost every paragraph is one
  line, so most edits are not counted: at gap 5, all 103 `crowded-gap`
  refusals and 275 of the `EDITED` resolutions are among the comments not
  counted (`rehearsal-site-policy.txt`). The lower rate is then a rate over
  paragraphs that did not change, and the upper is far above it. A
  hard-wrapped corpus keeps more lines of an edited paragraph, so arms are
  not comparable.
- **Independence.** The rule is D8's, and difflib is not the resolver's leaf
  correspondence. But the paragraphs, their line numbers and the text a span
  is checked in come from the blockspec reader, so a reader defect in
  segmentation reaches both sides.
- How it differs from D8's: lines come from the reader's paragraph lines,
  not from searching the file for a block's content; every paragraph is
  anchored, not a sample of 30; pairs with identical versions are not
  skipped; the deleted test compares paragraphs only.

Before a replay can decide a bar, the oracle has to place an edited or a
moved paragraph by something other than the resolver's own rules.

## What it does not measure

- Headings, tables and code blocks. The reader gives headings and tables no
  source lines, so the line oracle cannot place them. Code blocks have
  lines, but a span of three words is a poor model of a comment on code, so
  they are left out too. Only paragraphs are anchored.
- Suggestions. A suggestion resolves as a comment does; whether its gate
  applies is not graded.
- Where on the paragraph a comment sits. Every span is three words from the
  middle, away from the paragraph's edges, where the stored context is
  shorter. Requiring the span itself to be unique leaves out the repeated
  spans where §11.12's R3 and the `repeat` refusals live.
- History. Pairs are positions in `git log --reverse -- FILE`, so the two
  versions of a pair can sit on parallel branches; a file's history before
  a rename is not followed.

## Running it

    python3 -I replay.py --blockspec PATH --clone NAME=PATH ... [--arm NAME] [--gap N]
    python3 -I red_states.py --blockspec PATH
    python3 -I red_sweep.py BLOCKSPEC_PATH

with the clone names of `../D8-block-definitions/arms.json`. Each clone must
be at its pin with no tracked changes, and `--blockspec` a blockspec checkout
with none either; `replay.py` exits otherwise, and prints the blockspec
commit. File contents are read as bytes and decoded as UTF-8, so line
endings are the history's own. The reference is standard-library Python,
and so are these scripts.

The rehearsal was made with

    python3 -I replay.py --blockspec BLOCKSPEC --clone site-policy=CLONE --arm site-policy --gap 1 --gap 5

and took about twenty minutes on one machine.

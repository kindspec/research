# D8-anchor-replay: blockspec's anchor resolver on real document history

blockspec adjudication 0003 §12 names, first among what would reverse its
anchor design, "a replay over real history that prices the refusals": the
resolver adds refusals (near-copy, refilled-gap, crowded-gap, twin and
context rules, and the alignment) whose rate on real edits is unknown. This
experiment is that replay. It runs real file histories against the blockspec
reference resolver and grades each resolution with D8's independent line
oracle.

    replay.py                  the measurement
    red_states.py              each part of the grading broken on purpose
    red-states.txt             red_states.py's stdout
    rehearsal-site-policy.txt  replay.py's stdout on the rehearsal arm

**Nothing here is a verdict yet.** The arms that would decide anything have
not been run. The bar a result is held to is set before they run, by a
pre-registration the owner approves. Only the rehearsal arm, `site-policy`,
has been run, to show the harness works end to end.

## What replay.py measures

For each arm, each sampled file, and each pair of versions GAP commits
apart in that file's history (gaps 1, 5 and 25):

- every paragraph of the earlier version with at least 20 characters gets a
  comment on three words from its middle, written as blockspec `SPEC.md`
  §11.1 creates one: `prefix + span + suffix` must occur once in the
  paragraph, or no comment is made;
- the comment is resolved against the later version by the reference
  resolver (`blockspec.anchor.resolve`), with the earlier version as `base`;
- **truth** is D8's line oracle (`../D8-identity/anchor_eval2.py`,
  `line_oracle`), applied to paragraphs. difflib maps the earlier file's
  lines onto the later's. If at least half of the paragraph's non-blank
  lines survive, its target is the later paragraph holding most of them. If
  none survive and no later paragraph is 30% similar, it was deleted.
  Anything else is unknown and is not counted. The oracle is a different
  algorithm at a different granularity from the resolver's leaf
  correspondence.

A comment is graded against the oracle's target:

| truth | `correct` | `loud` | `WRONG` |
| --- | --- | --- | --- |
| the span occurs once in the target | resolves there, on that span | refused, `DETACHED` or `ORPHANED` | resolves anywhere else |
| the span is gone from the target, or the paragraph was deleted | loud | — | resolves |

A span that occurs more than once in the target is not counted. `loud`
where the span survives is the cost 0003 asks to price: a refusal of text
that is still there. Each is reported with its status, and a refusal with
its reason. A document the profile refuses (`SPEC.md` §4) yields no
comments, and its pairs are counted separately.

## What it does not measure

- Headings, tables and code blocks. The reader gives headings and tables no
  source lines, so the line oracle cannot place them. Code blocks have
  lines, but a span of three words is a poor model of a comment on code, so
  they are left out too. Only paragraphs are anchored.
- Suggestions. A suggestion resolves as a comment does; whether its gate
  applies is not graded.
- Where on the paragraph a comment sits. Every span is three words from the
  middle, away from the paragraph's edges, where the stored context is
  shorter.

## Running it

    python3 -I replay.py --blockspec PATH --clone NAME=PATH ... [--arm NAME] [--gap N]
    python3 -I red_states.py --blockspec PATH --clone NAME=PATH --arm NAME [--gap N]

with the clone names of `../D8-block-definitions/arms.json`. Each clone must
be at its pin with no tracked changes; `replay.py` exits if one is not.
`--blockspec` is a blockspec checkout, whose commit each run prints. The
reference is standard-library Python, and so are these scripts.

The rehearsal took about twenty minutes for site-policy at gaps 1 and 5, on
one machine.

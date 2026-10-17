# D8-anchor-replay: blockspec's anchor resolver on real document history

blockspec adjudication 0003 §12 names, first among what would reverse its
anchor design, "A replay over real history that prices the refusals": the
resolver adds refusals (near-copy, refilled-gap, crowded-gap, twin and
context rules, and the alignment) whose rate on real edits is unknown. This
experiment is a harness for that replay. It runs real file histories against
the blockspec reference resolver, grades each resolution with a word oracle,
and checks the oracle against a labelled sample.

    replay.py                  the measurement
    kinds.py                   the loud comments of a dump, by how much their paragraph changed
    sample.py                  a stratified sample of replay.py's comments, as blind packets to label
    score.py                   the labels against the oracle and the resolver
    labelling-brief.md         what each labeller is given, besides the packets
    red_states.py              a control and three broken resolvers on a fixture, and the rates, each checked
    red-states.txt             red_states.py's stdout
    red_sweep.py               replay.py broken twelve ways; red_states.py must fail each, or it exits 1
    red-sweep.txt              red_sweep.py's stdout
    rehearsal-site-policy.txt  replay.py's stdout on the rehearsal arm
    kinds-site-policy-gap5.txt kinds.py's stdout on it, at gap 5
    labels/site-policy-gap5/   the rehearsal arm's labelled sample: sample.py's key and stdout, both
                               passes of labels, and score.py's stdout

**Nothing here is a verdict.** The arms that would decide anything have not
been run. Only the rehearsal arm, `site-policy`, has been run, and labelled
at gap 5.

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
- **truth** is the word oracle (`word_oracle`). difflib matches the earlier
  version's paragraph words, in document order, onto the later version's.
  The span **survives** in the later paragraph its three words all map to,
  in order and adjacent. It is **gone** when its text, with each run of
  whitespace as one space, is in no later paragraph. Anything else is
  **unknown** and is not counted: the text is somewhere later, but not
  where the matching put it, as when a paragraph moves.

A comment is graded against the oracle's target:

| truth | `correct` | `loud` | `WRONG` |
| --- | --- | --- | --- |
| the span occurs once in the target, whitespace aside | resolves there, on that span | refused, `DETACHED` or `ORPHANED` | resolves anywhere else |
| the span is gone | loud | — | resolves |

A span that occurs more than once in the target is not counted. Each `loud`
is reported with its status and refusal reason. A soft line break renders
as a space, so a span rewrapped across lines is the same text; one with a
word inserted between its words, or a word changed, is gone.

Every comment that is not counted is reported too, by the resolver's
status. The report gives three rates of refusing text that survived, and
none of them is a bound:

- among the comments the oracle places;
- as if every loud comment it does not place had surviving text;
- and as if, besides, every comment on a pair whose later version the
  profile refuses (`SPEC.md` §4) had surviving text. Each of those resolves
  `REFUSED(not-in-profile)`.

`--dump` writes every comment, with its truth and its resolution, one JSON
line each, for `sample.py`.

## The labelled sample

The oracle's placements are difflib's, not a reader's, and it does not
place a moved paragraph. A labelled sample measures both.

`sample.py` puts each comment of one gap in a stratum: the oracle's class
(`placed`, the span survives where the oracle puts it; `gone`; `unplaced`,
not counted) crossed with the resolver's (`loud` or `resolves`). It draws
each stratum at random up to a cap, and writes one packet per comment: the
file's two versions as numbered paragraphs, with the span marked. A packet
says nothing of the resolver's status or the oracle's truth; those are in
the key, which the labellers are not given.

Each packet is labelled twice, independently, by labellers given only the
packet and `labelling-brief.md`: does the marked text survive in the later
version as the same passage, whitespace aside, and in which paragraph?
Where the two disagree, a third label settles it. `score.py` scales each
stratum's labelled shares to the stratum's size, and gives each share an
exact 95% interval (Clopper-Pearson; none where every comment in the
stratum was labelled). Each estimate is then given with every stratum at
the ends of its interval, which is wider than a joint interval and stays
finite when a stratum shows no errors.

## The rehearsal

`rehearsal-site-policy.txt`, at gaps 1 and 5, and its gap-5 sample in
`labels/site-policy-gap5/`. At gap 5 the oracle does not count 14 of 2,989
comments, and among those it places, 182 of 2,809 surviving spans are
refused (6.5%), with no `WRONG`.

The two passes of labels agree on all 129 packets. No label contradicts
the oracle where it places a comment, but 30 labelled comments stand for
the 2,627 that resolve, so the oracle's error is only bounded: at most
11.3%. Of the 14 comments the oracle does not place, 4 have surviving text.
With labels for truth, the refusal rate at gap 5 is 6.6%, from 6.3% to 8.2%
with every stratum at the ends of its interval (`score.txt`).

Some of the refusals of surviving text come where little changed
(`kinds-site-policy-gap5.txt`): of the 182 at gap 5, 18 are
`REFUSED(near-copy)` on a paragraph whose text is unchanged, and 11 are
`DETACHED` on one that changed only in whitespace, within the span's stored
context (32 code points each side). In the near-copy example it prints, the
unchanged list item is refused because a new list item two below it is
at least half like it.

## What the oracle cannot see

- **Independence.** difflib's word matching is not the resolver's leaf
  correspondence, which pairs paragraphs by character similarity and a
  margin. But the paragraphs and the text a span is checked in come from
  the blockspec reader, so a reader defect in segmentation reaches both
  sides, and the labels see the reader's paragraphs too.
- **A move it cannot follow** is unplaced, not misplaced; the labels price
  those comments, and the oracle's placements, only within the sample.
- **What "the same text" means** is the brief's: the same three words, in
  order and adjacent, punctuation attached. A span whose word is a link
  whose URL changed, or whose word changed case, is gone, though a reader
  might call the passage the same.

## What it does not measure

- Headings, tables and code blocks. Only paragraphs are anchored. Code
  blocks have lines, but a span of three words is a poor model of a comment
  on code.
- Suggestions. A suggestion resolves as a comment does; whether its gate
  applies is not graded.
- Where on the paragraph a comment sits. Every span is three words from the
  middle, away from the paragraph's edges, where the stored context is
  shorter. Requiring the span itself to be unique leaves out the repeated
  spans where §11.12's R3 lives.
- History. Pairs are positions in `git log --reverse -- FILE`, so the two
  versions of a pair can sit on parallel branches; a file's history before
  a rename is not followed.

## Running it

    python3 -I replay.py --blockspec PATH --clone NAME=PATH ... [--arm NAME] [--gap N] [--dump JSONL]
    python3 -I sample.py --blockspec PATH --clone NAME=PATH --dump JSONL --gap N --packets DIR --keydir DIR
    python3 -I score.py --keydir DIR --labels A.jsonl --labels B.jsonl [--adjudicated C.jsonl]
    python3 -I red_states.py --blockspec PATH
    python3 -I red_sweep.py BLOCKSPEC_PATH

with the clone names of `../D8-block-definitions/arms.json`. Each clone must
be at its pin with no tracked changes, and `--blockspec` a blockspec checkout
with none either; `replay.py` exits otherwise, and prints the blockspec
commit. File contents are read as bytes and decoded as UTF-8, so line
endings are the history's own. The reference is standard-library Python,
and so are these scripts.

The rehearsal was made with

    python3 -I replay.py --blockspec BLOCKSPEC --clone site-policy=CLONE --arm site-policy --gap 1 --gap 5 --dump DUMP
    python3 -I sample.py --blockspec BLOCKSPEC --clone site-policy=CLONE --dump DUMP --gap 5 --packets PACKETS --keydir KEY

and the replay took about twenty minutes on one machine. `sample.py` draws
the same packets and key from the same dump.

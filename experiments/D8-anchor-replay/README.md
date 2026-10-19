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
    histcheck.py               how many sampled files have a commit that does not hold them
    heldout-arms.json          the held-out arms of blockspec's pre-registration 5, read after arms.json
    histcheck.txt              histcheck.py's stdout on the rehearsal and verdict arms
    sample.py                  a stratified sample of replay.py's comments, as blind packets to label
    score.py                   the labels against the oracle and the resolver
    labelling-brief.md         what each labeller is given, besides the packets
    red_states.py              a control and three broken resolvers on a fixture, and the rates, each checked
    red-states.txt             red_states.py's stdout
    red_sweep.py               replay.py broken twenty-one ways; red_states.py must fail each, or it exits 1
    red-sweep.txt              red_sweep.py's stdout
    rehearsal-site-policy.txt  replay.py's stdout on the rehearsal arm
    kinds-site-policy-gap5.txt kinds.py's stdout on it, at gap 5
    prereg4/                   pre-registration 4's run on the verdict arms, and its verdict
    labels/site-policy-gap5/   the rehearsal arm's labelled sample: sample.py's key and stdout, both
                               passes of labels, and score.py's stdout

**The verdict is in `prereg4/`.** blockspec's pre-registration 4 fixed the
run before it ran; `prereg4/README.md` gives its outputs and its verdict.
Everything else here is the harness and its rehearsal arm, `site-policy`,
labelled at gap 5.

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
  in order and adjacent. It is **gone** when its words occur, in order and
  adjacent, in no later paragraph. Anything else is **unknown** and is not
  counted: the text is somewhere later, but not where the matching put it,
  as when a paragraph moves.

A comment is graded against the oracle's target:

| truth | `correct` | `loud` | `WRONG` |
| --- | --- | --- | --- |
| the span occurs once in the target, whitespace aside | resolves there, on that span | refused, `DETACHED` or `ORPHANED` | resolves anywhere else |
| the span is gone | loud | — | resolves |

A span whose words occur more than once in the target is not counted. Each
`loud` is reported with its status and refusal reason. Words are split on
whitespace, and a soft line break renders as a space, so a span rewrapped
across lines is the same text; one with a word inserted between its words,
or a word changed or lengthened, is gone.

Every comment that is not counted is reported too, by the resolver's
status. The report gives three rates of refusing text that survived, and
none of them is a bound:

- among the comments the oracle places;
- as if every loud comment it does not place had surviving text;
- and as if, besides, every comment on a pair whose later version the
  profile refuses (`SPEC.md` §4) had surviving text. Each of those resolves
  `REFUSED(not-in-profile)`.

`--dump` writes every comment, with its truth and its resolution, one JSON
line each, for `sample.py`; a comment on a pair whose later version the
profile refuses is written with verdict `profile`.

## The labelled sample

The oracle's placements are difflib's, not a reader's, and it does not
place a moved paragraph. A labelled sample measures both.

`sample.py` puts each comment of one gap in a stratum: its arm, the
oracle's class (`placed`, the span survives where the oracle puts it;
`gone`; `unplaced`, not counted) and the resolver's (`loud` or
`resolves`). It draws each stratum at random up to a cap (`--cap` changes
one), and writes one packet per comment: the file's two versions as
numbered paragraphs, with the span marked. A packet says nothing of the
resolver's status or the oracle's truth; those are in the key, which the
labellers are not given. A comment on a version the profile refuses has no
later paragraphs to label, so it is counted, not sampled.

Each packet is labelled twice, independently, given only the packet and
`labelling-brief.md`: does the marked text survive in the later version as
the same passage, whitespace aside, and in which paragraph? Where the two
disagree, a third label settles it. `score.py` validates the labels, scales
each stratum's labelled shares to the stratum's size, and gives each share
an exact two-sided 95% interval (Clopper-Pearson; none where every comment
in the stratum was labelled). Each estimate is then given with every
stratum at the ends of its interval. That range is not a confidence
interval, but it stays finite where a stratum shows no errors. Every arm in
the key is pooled into one rate, and each arm's own rate is printed beside
it, so which arms to pool is the caller's: `arms.json` says which never
are.

The rehearsal's labels were made by automated labellers, not people: each
pass by separate instances given the same brief and nothing else, with the
key kept out of their packets but on the same machine. The brief states
the rule a span survives by, which is the oracle's own rule for words; what
the labels add is which passage is the same one, through moves, merges,
splits and coincidental repeats, and agreement between the passes shows
the rule applied consistently, not a reader's independent judgement of it.

## The rehearsal

`rehearsal-site-policy.txt`, at gaps 1 and 5, and its gap-5 sample in
`labels/site-policy-gap5/`. At gap 5 the oracle does not count 10 of 2,989
comments, and among those it places, 182 of 2,809 surviving spans are
refused (6.5%), with no `WRONG`. Besides those, 800 comments sit on 11
pairs whose later version the profile refuses, every one for `raw-html`.

The two passes of labels agree on all 125 packets. No label contradicts
the oracle where it places a comment, but 30 labelled comments stand for
the 2,627 that resolve: with every stratum at the upper end of its
interval, the oracle's error is 11.4%. Of the 10 comments the
oracle does not place, 4 have surviving text. With labels for truth, the
refusal rate at gap 5 is **6.6%**, from 6.3% to 8.3% with every stratum at
the ends of its interval, among comments on versions the profile accepts;
counting each of the 800 as a refusal of surviving text, it is 27.3%
(`score.txt`).

117 of the 125 packets were labelled on an earlier draw of the same
comments, before the gone test matched whole words (the sample's key at
commit `361a6b3`). Their labels are carried over by comment (arm, file,
both versions, paragraph and span); the other 8 were labelled for this
draw, by two more passes given the same brief.

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
- History. Pairs are positions in `git log --reverse -- FILE`, from the
  commit after the last one that does not hold the file (one that deletes
  it, or moves it away), so the two versions of a pair can sit on parallel
  branches; a file's history before a rename is not followed, nor, on one
  line of history, before it last came back. "Last" is in `git log`'s
  order, so a deletion and a return on parallel branches can still join
  across it. Names that `git ls-files` quotes (non-ASCII, `"`, tab)
  give no pairs; no arm has one.

## Running it

    python3 -I replay.py --blockspec PATH --clone NAME=PATH ... [--arm NAME] [--gap N] [--dump JSONL]
    python3 -I sample.py --blockspec PATH --clone NAME=PATH ... --dump JSONL --gap N --packets DIR --keydir DIR [--cap CLASS/RESOLVER=N]
    python3 -I kinds.py --blockspec PATH --clone NAME=PATH ... --dump JSONL --gap N
    python3 -I histcheck.py --clone NAME=PATH ... [--arm NAME ...]
    python3 -I score.py --keydir DIR --labels A.jsonl --labels B.jsonl [--adjudicated C.jsonl]
    python3 -I red_states.py --blockspec PATH
    python3 -I red_sweep.py BLOCKSPEC_PATH

with the clone names of `../D8-block-definitions/arms.json` and
`heldout-arms.json`. Each clone must
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

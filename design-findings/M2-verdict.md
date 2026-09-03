# M2 — an independent implementation from the spec alone

The experiment: a second implementation written from `SPEC.md` and the fixture
tree, by an author forbidden to read `reference/`. It reported no contamination.

## Result: 129/131 cases pass — and the process is the finding, not the score

The fixture tree grew 57 → 114 → 131 while the author worked, because the
adversarial case author was running concurrently. So:

    against the ORIGINAL 57 cases      57/57 passed
    against the 74 cases added later   9 FAILED

**Every one of those nine was a documented guess that a later fixture
overturned.** Seven distinct wrong behaviours, and three of them produce
*plausible wrong numbers rather than errors* — precisely what §1 exists to
prevent.

The author's own summary is the lesson:

> Passing the suite is not evidence the prose is sufficient; it is evidence the
> suite is small.

**Verdict: `SPEC.md` is not yet sufficient for an independent implementer.**

## The most dangerous ambiguity in the document

`@c` in a group aggregate. The spec never states that `@` binds to the row being
computed while the aggregated column is scanned over *candidate* rows. Binding
both to the same row — the author's first reading — turns **every group
aggregate into a grand total**: a plausible number, never an error.

Second: §7 and §8 contradict each other. §8 says a value that will not coerce to
a number is `#REF!`; read literally that makes §7's own example,
`sum(amount where region = @region)`, always `#REF!`. The author implemented §8
literally and was later contradicted by a fixture.

## Two holes in my own runner, both now fixed

**1. `canon = lambda x: x` scored 129/131.** `run_cases.py` had no branch for
`check == "removes-padding"`, so that fixture asserted *nothing* — for the one
property §2 lists as deliberately specified *because* disagreement causes silent
corruption. Now fixed and proven: the identity function fails.

**2. Every `\r` was deleted before any implementation saw it.** Fixtures were
read in universal-newline mode, so both CR cases were unpassable and
`roundtrip/crlf` tested nothing. Fixed with `newline=""`; verified the CR byte
is now visible (1 with, 0 without).

These are the same defect in two costumes: **a check that cannot fail, reported
as a pass.** Third instance in this project, after the mutation gate going stale
and `#REF!` rendering as zero.

## What the spec got right, which I need on the record

- **§8's error propagation** — *"it must not sum the values it can read"* —
  precise, and the boldface earns its place. Right first time, mutations caught.
- **`#REF!(name)` carrying the originating name.**
- **§6's sort-key sentence**, which states the rule, the wrong alternative, and
  why it is wrong. The author called it *"a model normative sentence."*
- **"A row's position in the file is never an input to any computation"** —
  made the derive-then-evaluate architecture obvious, and
  `merge/backdated-appended-last` passed first time.
- **§5's co-location argument and §11's bare-repository reasoning** — the
  clearest prose in the document.

The pattern: **the architecture transmitted; the surface syntax did not.** The
author got opaque keys, derived order, tuple sort keys, error propagation and
line-per-row merge right on the first attempt — the hard part — and went wrong
on cell trimming, numeric literals, comment syntax and total-function edges,
which is exactly where silent divergence lives.

## The three fixes, in the author's priority order

1. **Add a lexical grammar and make §9 complete.** Line terminator, table-line
   shape, cell trimming, the prohibition on `|` in a cell (no escape exists),
   the alignment-cell pattern, ASCII numeric literals (a naive `\d` accepts
   Arabic-Indic digits), date grammar and integer comparison, text collation,
   comment syntax, and the conflict-marker set **including `|||||||`** — which
   is itself a table line, so an implementer who misses it parses a diff3
   conflict as data.
2. **Reconcile §7 and §8, and specify or delete `lookup`.**
3. **Make canonical form testable** — an exact expected-output file rather than
   a property check.

## What this validates about the process

The standing rule paid for itself immediately. An implementer working from the
prose found seven behaviours the prose does not determine, two holes in the
harness, and one contradiction — none of which the implementation's own author
had found in a week of adversarial testing, because the implementation *is* the
answer to every question the prose leaves open.

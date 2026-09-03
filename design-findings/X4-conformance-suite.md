# F. The conformance suite, built — `conformance/`

The red team's charge was precise: the suite's round-trip test was a tautology
(`parse` and `render` were identity functions, so it asserted `doc == doc`),
and ~15 categories were missing entirely. Since the suite IS the deliverable, a
demo could not stand.

## What now exists

    conformance/
      cases.py         33 cases declared as DATA, so an independent
                       implementation can consume them without importing ours
      runner.py        executes them against any implementation, using a
                       STOCK git binary for every merge
      ref_tbl.py       the reference implementation
      mutants.py       the mutation gate
      corpus_check.py  cross-file checks no parser can perform
      check.yml        the CI workflow

Categories: parse (14), roundtrip (5), eval (6), merge-under-stock-git (8),
confluence (1). Merge cases assert on the **evaluated value of the merged
artifact**, not just git's exit code — so a clean merge with a wrong number is
reported as `SILENTLY WRONG`, which is the only failure mode that matters.

## The tautology is gone

`render` now reconstructs the file from the parsed structure rather than
returning its input, so `render(parse(b)) == b` is a real assertion about the
parser's boundary detection. Proof that it is real: two of the mutants below
are killed *only* by round-trip cases.

## The mutation gate — the part that makes the suite credible

    15 mutants, 15 killed, 0 survived

Each mutant is a plausible implementation bug: drop every third row, ignore
conflict markers, allow duplicate columns / aggregates / row ids, skip the
field-count or alignment checks, ignore the declared row order, permit
row-relative operators without an order, render `#REF!` as zero, an off-by-one
in `cumulative`, drop the tail or the alignment row on render, skip NFC
normalisation, crash instead of reporting a missing aggregate column.

**The gate found two holes on its first run, and both were worth finding.**

1. **`ignore-declared-order` SURVIVED.** An implementation that ignores
   `order := by(date)` and computes in file order passed every case — because
   every ledger fixture I had written happened to be *already sorted by date in
   the file*. The whole point of declared order is that file order is
   irrelevant, and not one case tested that. Fixed by adding an
   order-*sensitive* case: a ledger whose file order is dates 5, 1, 3, asserting
   a running minimum that only dips if the declared order is honoured
   (`low = -50.0`).

2. **`skip-alignment-check` SURVIVED** — but that one was a bad mutant, not a
   hole. Replacing one line of a two-line f-string left dangling syntax, the
   runner crashed, and a crash was being counted as zero failures. Fixed both
   the mutant and the harness: **a runner that crashes on a mutant now counts
   as killed, not survived.**

The first is the more instructive. A suite written by the same person who wrote
the implementation inherits that person's blind spots, and the mutation gate is
what surfaces them mechanically. It is the third time in this project that a
mechanical check caught something careful thought did not.

## Corpus-scoped checks

`corpus_check.py` catches what no per-file parser can, because no single file is
invalid — the duplicate artifact UUID after a `cp`. Run against this repository
it correctly reports the deliberate duplicate planted in the namespace
experiment:

    DUPLICATE ARTIFACT ID 01J8ZQ4K7X
        experiments/X3-namespaces/uuid/doc.md
        experiments/X3-namespaces/uuid/copy.md
    504 identified artifact(s), 1 duplicate id(s)

## Two bugs the suite caught in the reference implementation immediately

Both were fixes I had made in one experiment directory and never propagated to
another copy: the alignment-row field-count check, and a missing aggregate
column crashing with a `TypeError` instead of producing `#REF!`.

That is a small thing that argues for something structural: **there must be ONE
reference implementation.** Duplicated prototypes silently diverge, and the
divergence is invisible until something executes all of them against the same
cases.

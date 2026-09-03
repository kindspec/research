# Dogfood verdict: one threshold failed badly, and it falsified a design rule

7,446 real commits, 112 authors, four corpora, 2011–2026. Measured against the
thresholds pre-registered before any data was collected.

    T1  refusal rate, .mdtbl      26.95%      FAIL -- 13.5x the 2% ceiling
    T1  refusal rate, CSV mode     2.93%      FAIL -- marginally
    T2  row-id carriage           99.925%     PASS  (and a lower bound)
    T3  diff ratio, median        1.0000      PASS
    T4  silent-wrong merges        0 of 528   PASS
    T5  canon churn            0.000105%      PASS

## The failure is one rule, and the rule is wrong

**95% of `.mdtbl` refusals involve a `|` inside a value. 1,863 are admitted
false positives** — the data is fine, the format cannot hold it.

    KS TV | Action

Ninety-three Ukrainian channels have a pipe in their own name. **From 2023-10-16
to HEAD, 100% of `channels.csv` commits are unrepresentable.** Before that date
the same corpus refuses 1.6% and passes T1 comfortably.

SPEC §4.1.3 says a cell can never contain `|` "because no escape exists and none
may be invented", and I wrote that as a virtue — the reasoning being that an
escape is parser complexity nobody needs. It was never paid for by evidence, and
the first contact with real data produced evidence against it. GFM has had `\|`
for years, for exactly this reason.

**This is a falsified design decision, not a mispriced threshold.** The
pre-registration said that if refusals are not real defects the answer is *not*
to loosen them — but that rule was written for strictness applied to genuine
defects. Here the format simply cannot represent a legal, ordinary value. That
is a representational gap, and the honest response is to close it.

## Everything else held, and some of it held well

**Row-id carriage 99.925%**, across mass re-sorts, a whole column set replaced
mid-life, and a column added three years in. And it is a *lower bound*: the real
history has no id column, so identity had to be reconstructed from the natural
key, which makes a human renaming a key read as delete-plus-add.

**Diff ratio 1.0000 lines median** — on real edits, a `.mdtbl` change touches
exactly as many lines as the same change to the CSV. The locality claim survives
contact with real editing.

**Zero silent-wrong merges in 528 real three-way merges.** The thing the whole
project is organised against did not occur.

## But read that last one carefully, because it cuts both ways

Zero silent-wrong merges **for plain CSV too.**

> For an ordinary sorted registry CSV, stock git already does what the format
> promises.

Four cases went the other way — `.mdtbl` over-conflicted where CSV merged
cleanly — caused by the identity mechanism itself: the same row added
independently on both branches gets two different minted ids, so lines that are
byte-identical as CSV differ as `.mdtbl`.

One case went our way, and it is exactly the designed scenario: git merged the
CSV cleanly with `<<<<<<< HEAD` sitting in it as data, and the `.mdtbl` refused.

And the sharpest sentence in the report: **what `.mdtbl` adds needs a computed
column, and none of these maintainers has wanted one in four years.**

## CSV mode failed its threshold and is the better story anyway

2.93% against a 2% ceiling — but **218 refusals with zero false positives.**
Every one a real defect: committed `<<<<<<< HEAD` markers in live channel data,
four commits where the header row is simply gone, a 250-row file appended to
itself, a BOM buried inside the fifteenth column name *in the fix for that*, and
Åland and Antarctica sitting two fields short so every value is in the wrong
column — for three years.

A threshold failed by 0.93 points where every refusal is a genuine defect is a
different kind of failure from one where 95% are false positives.

## A live contradiction found en route

SPEC §4.1.9's ABNF admits `-` and `.` in identifiers; `_check_ident` does not.
I introduced that when narrowing the identifier set and did not update the ABNF.
It alone moves the measured rate from 27.63% to 28.11%.

## The harness policed itself, which is why I believe the numbers

26 controls, all passing, and the author reported three of its own bugs
unprompted — including a merge oracle that padded ragged rows and produced
**five false silent-wrong verdicts**, and a misconfiguration that manufactured
324 refusals. It kept the buggy run alongside the corrected one.

## What was never exercised

No corpus has a computed column, an aggregate, or a declared order. Six refusals
never fired and **the evaluator never ran on real data at all.** The half of the
format that justifies its existence has still never been tested against
anything real — which is the same gap the ergonomics arm found from the other
side, where a user built a table for six rounds and never saw a computed value.

# The dogfood experiment — design and pre-registered thresholds

Written before any data was collected. The thresholds below are the point: a
dogfood run that cannot fail is a demo.

## What has never been tested

Every experiment so far uses fixtures I or an adversary constructed. The thesis
is about **a table maintained by several people over time**. Nobody has ever
maintained anything in this format, and no editing pattern in the suite came
from a human doing their own work.

## Why simulated history is not good enough

A multi-author history I invent is my own imagination again — the same failure
mode as writing my own tests, which this project has now hit five times. The
editing patterns must come from somewhere real.

**So: replay the real git history of a real CSV-in-git dataset through rowspec.**
A repository's commit log *is* a record of how humans actually edit a versioned
table: the sloppy pastes, the mass re-sorts, the column added three years in,
the row deleted and re-added under a different name. None of that is inventable.

## Method

1. Take real public CSV-in-git datasets with substantial history and more than
   one author.
2. Convert the file at its earliest commit to `.mdtbl`, minting row ids.
3. Walk forward through every real commit that touched it. At each step,
   re-import the real CSV and carry row ids forward by the M1 mechanism.
4. Where the real history contains merge commits, replay them as real merges.
5. Record, per commit: refusal or not and why; row ids carried, re-minted, lost;
   `.mdtbl` diff size against the CSV diff size for the same change; whether
   `canon` alters bytes a human wrote.

## Pre-registered falsification thresholds

    REFUSAL RATE on real, already-accepted commits
        > 2%     the format is too strict to use. Each refusal must be
                 individually justified as a real defect in the data, or it
                 counts against us.

    ROW-ID CARRIAGE across real edits
        < 95%    the identity mechanism does not survive human editing habits,
                 and the merge argument that rests on it is theoretical.

    DIFF SIZE, .mdtbl against the same change in CSV
        > 1.5x median   the locality claim fails on real edits, whatever the
                        constructed fixtures said.

    REAL MERGES replayed
        any silent-wrong    fatal, and the whole thesis is in question.
        heavy over-conflict compared to the CSV baseline is a serious finding
                        even though it is the safe direction.

    CANON churn
        rewriting bytes a human deliberately wrote, at any rate worth naming,
        means the canonical form fights its user.

## The second arm: ergonomics

Numbers cannot tell us whether the thing is usable. So a second, separate
worker uses rowspec cold — from `README.md` and `SPEC.md` only, no help, no
access to the research — to build and maintain a small real table, deliberately
hitting refusals, and reports whether the errors were actionable **for someone
who did not write the format**.

Both arms are run by workers other than me. The bias this project keeps
reproducing is that the author of a check cannot see what it fails to catch, and
a dogfood run I design *and* execute would pick friendly data without meaning to.

## What would make me stop

If the refusal rate is above the threshold and the refusals are not real defects,
the answer is not to loosen the refusals. It is that the format's strictness is
mispriced for the population that would use it, and that is a finding worth more
than the format.

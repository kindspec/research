# Tables under blockspec 0004's near-copy rule

**Question.** blockspec adjudication 0004 changed the near-copy test for an
unchanged leaf from code-point similarity (0003) to word similarity. A GFM
table's `|` separators count as words, so two tables of the same shape share
words they do not share in meaning; blockspec's conformance case
`anchor/near-copy/a-table-s-separators-are-words` is built on that. Does
0004 refuse, on real history, unchanged tables that 0003 kept? Pre-registration
5's replay scored paragraphs only, so it could not say.

**Answer: no, on these nine arms.** Every unchanged table 0004 refuses near-copy
because of `|` words alone, 0003 refused too, and 0004 refuses fewer unchanged
tables than 0003 did (54 against 88). The constructed case's shape, an
unrelated table of the same shape joined only by `|` words, does not occur.

## Arms

Pre-registration 5's four held-out arms (github-docs, vscode-docs,
docker-docs, mdn-en; `../heldout-arms.json`) and its five tuned regression
arms (rust-book, obsidian-help, k8s-en, cncf-toc, site-policy), each clone at
its pin, gap 5. 0004 is blockspec ae1d274; 0003 is blockspec 31e41d3.

## 1. The replay, with comments on tables

`replay.py` here is `../replay.py` at research 95bfc44 with the changes its
header lists. The one that matters: the original keeps a leaf only if its
node has `lines`, and a table leaf has none, so the original places no table
comment at all. With `REPLAY_TYPES=p`, this copy's site-policy output at gap 5
is byte-identical to that section of
`../prereg5/regression/replay-site-policy.txt` (its first line also names
the types).

    run.sh r0004 <blockspec ae1d274> ARM CLONEKEY CLONEPATH OUTDIR
    run.sh r0003 <blockspec 31e41d3> ARM CLONEKEY CLONEPATH OUTDIR
    python3 -I analyze.py <blockspec ae1d274> OUTDIR ARM=CLONEPATH ...

`analyze.txt` is that output, from the scripts as committed here. The dumps
themselves quote corpus text and are not committed.

261 table comments; 0004 and 0003 give every one the same status:

| status | comments | held-out | tuned |
| --- | --: | --: | --: |
| RESOLVED | 188 | 117 | 71 |
| EDITED | 28 | 16 | 12 |
| DETACHED | 19 | 14 | 5 |
| ORPHANED | 14 | 13 | 1 |
| REFUSED(crowded-gap) | 9 | 6 | 3 |
| REFUSED(not-in-profile) | 2 | 1 | 1 |
| REFUSED(near-copy) | 1 | 1 | 0 |

The one near-copy refusal is on an edited table, so it is the code-point
rule, and its span is gone (graded correct).

## 2. Every unchanged table leaf

261 comments is thin, so `scan.py` checks every base table leaf that pairs
EXACT, in every file of each arm's pathspec with a table in the earlier
version of a pair (up to three pairs a file, sampled as `replay.py` samples,
same seed), against both resolvers' near-copy rule, and computes word
similarity with and without `|` words.

    python3 -I scan.py <blockspec ae1d274> <blockspec 31e41d3> ARM CLONEPATH 5

One output per arm in `scan/`. Totals over the nine:

| | count |
| --- | --: |
| pairs with a table | 1,564 |
| pairs with a version the profile refuses, earlier version holding a `|` character | 1,694 |
| base table leaves | 3,946 |
| unchanged (EXACT) table leaves | 2,814 |
| ... with an unmatched current leaf | 1,680 |
| **0004 refuses near-copy** | **54** (github-docs 53, vscode-docs 1) |
| ... every trigger `|`-only | 11, all also refused by 0003 |
| ... not `|`-only, also refused by 0003 | 41 |
| ... not `|`-only, new under 0004 | 2 |
| **0003 refuses near-copy** | **88** (github-docs 73, vscode-docs 11, mdn-en 3, obsidian-help 1) |

Every trigger is another table. The two new refusals are in github-docs
`content/actions/reference/workflows-and-actions/events-that-trigger-workflows.md`
2431a1b6d38a..4f49e3bc00b1, leaves 56 (words 0.656, without `|` 0.571,
code points 0.492) and 98 (0.597, 0.509, 0.444), both against current leaf
86. Both stay at or above 0.5 without `|`: they are the word rule itself, not
the separators.

`scan.py` tests the near-copy condition itself, not the resolver's whole
verdict (`check_pair` can refuse earlier for another reason). Calling
`check_pair` for both resolvers instead gives the same near-copy refusals on
vscode-docs, site-policy, k8s-en and the events-that-trigger-workflows pair.

**Positive control.** `control.sh` rebuilds the conformance case as a git
history with fixed dates (HEAD 3d3c9bd0). Its pair is the case's base
against a current version with four short lines appended to the last
paragraph, so the gap-5 sampling reaches it; it checks `scan.py`'s near-copy
test, not the resolver. `scan/control.txt` reports 0004
refuses, 0003 does not, every trigger `|`-only (words 0.516, without `|`
0.000, code points 0.486).

## Limits

- 1,694 pairs whose earlier version holds a `|` character have a version
  outside the blockspec profile and are not scanned; where only the later
  version is refused, the replay's comments there are
  REFUSED(not-in-profile).
- The scan counts leaves, not comments; an EXACT leaf is unchanged by
  definition, so each refusal there refuses text that survived.
- Nine arms, the same corpora as pre-registration 5; no other population.

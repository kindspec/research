<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# E5 — The differential, re-run against §4.2's own parser

Harness: `experiments/E1-differential/e1.py` (rewritten), `e1_merge.py`.
Results: `experiments/E1-differential/out/fixed/`.
Measured against `reference/rowspec/table.py` md5 `70dbcde2…`, `SPEC.md` md5
`ca307b81…`, with rowspec's own suite green at that revision.

---

## 0. The headline, stated the way it should be quoted

**On ~1,478 non-trivial distinct facts drawn from 94 distinct expressions,
rowspec agrees with the values Excel itself cached, except for two cells whose
disagreement is float cancellation that neither engine gets right.**

The raw figure is 42,781 / 42,793 = **99.97%** over 61,852 compared cells. That
number is arithmetically sound — the ladder reconciles to the unit and the
comparison is `float == float`, never string — and it is **substantively much
smaller than its magnitude suggests**, for three reasons measured below.

## 1. What the rewrite fixed

E1 decided *evaluability* by parsing the translated expression as **Python**.
`IF(a="x",1,0)` is not valid Python — it reads `a="x"` as a keyword argument —
so 10,959 cells were bucketed `not-python:IF` and never compared. The gate is
now rowspec's own §4.2 parser.

Measured over all 5,458 SB912 workbooks, 170,590 CLEAN cells:

    old accepts, new accepts        54,481
    old rejects, new accepts         6,664      every one an `if`
    old ACCEPTS, new REJECTS              0

The zero is the surprise. Python accepts `a*.5`, `1.5e3`, `a**b`, none of which
§4.2's `literal` admits — but no CLEAN cell in this corpus spells a number that
way. The old gate's error was entirely one-directional: **too narrow, by 6,664
cells, all of them `if`.**

TmplEnron reproduced E1's published figures bit-identically (38,352 compared,
30,720 exact, 7,632 blank, 0 other), which is the strongest evidence the
exclusion ladder survived a rewrite of its central gate.

## 2. Why the headline is smaller than it looks

**62% of compared cells are one corpus of `column × constant`.** TmplEnron
contributes 38,352 of 61,852 compared and 30,720 of 40,599 exact agreements.
Every one of those cells has exactly one input and that input is `0.0` (30,720)
or blank (7,632). **Non-zero exact agreements contributed by TmplEnron: zero.**

**76% of all agreements have an expected value of `0`.** 32,672 of 42,781.

**The corpus replicates ~6×.** 557 of 2,667 SpreadsheetBench problems ship six
files each. Deduplicated to distinct `(expression, inputs, expected value)`:

| | cells | distinct facts | distinct expressions |
|---|---|---|---|
| all agreements | 42,781 | **1,520** | — |
| non-trivial | 9,969 | **1,478** | **94** |
| `if` path | 595 | **56** | **7** |
| `if` against a string literal | 84 | **16** | **3** |

The 12 disagreements are likewise **2 distinct cells** replicated sixfold —
`EXIT−ENTRY` on two time serials, where rowspec gives exactly IEEE
`17.69-17.99 = -0.29999999999999716`, Excel cached `-0.300000000000001`, and a
40-digit decimal cross-check says `-0.3`. Neither engine is right.

## 3. What this differential does NOT test

Every `.mdtbl` the harness builds has **one data row and one computed column**,
with dependencies substituted as cached-value literals. A mutant that breaks
every row after the first changes **nothing**.

So the run validates §4.2's expression grammar and its arithmetic, and nothing
else: not dependency ordering, not static cycle detection, not `#REF!`
propagation across columns, not lazy-versus-static analysis in `if`, not
row-relative operators, not multi-row semantics. The conformance suite covers
those; the differential does not, and the two must not be conflated.

## 4. Four broken controls, and the pattern they belong to

An adversary attacked the harness. The arithmetic held; the controls did not.

**`blank-is-zero` RAISED agreement.** It makes the evaluator treat a blank as
`0` — a direct §8 violation — and on TmplEnron went 30,720/30,720 = 100.00% to
38,352/38,352 = 100.00%, because zeroing blanks moves the excluded `Dref.blank`
class *into* the denominator where it agrees. **A control reporting a pass on a
real defect**, and the second time this failure has occurred in this harness's
mutation control.

**`mul-rel-1e-15` injected a factor of 16.** `'mul-rel-1e-15'.split('-')[-1]` is
`'15'`. Both arm checks passed, because ×16 is certainly not 1.0. A genuine
1e-15 perturbation is **invisible** — every affected cell moves from `A.exact`
into `A.15sig`, which the report counts as agreement. Only 3,394 cells (7.9% of
the denominator) are sensitive to the multiplication operator at all.

**No mutant perturbed COVERAGE.** A parser regression refusing every `if`
changes the headline by 0.0004 points and silently empties the entire `if`
sub-report. All six existing mutants perturbed answers; none perturbed which
cells were measured. This is the dead-`pyast.Add`-key failure with a new
subject.

**`e1_merge` accepted a duplicate shard**, doubling every tally while the
set-valued counters stayed correct.

Every mutant now declares the counter movement that proves it fired, checked
against the run's own numbers, and a mutation run that cannot show its signal
exits non-zero. `mul-rel` refuses to run below the report's own tolerance floor.

**The guard against merging a merge output was written after the guard against
duplicate shards let one through** — the first test of the new guard globbed
`out/*.json`, matched the previous `merged.json`, and doubled the headline. A
guard that misses the case that produced it is not a guard.

## 5. A translator defect the differential exposed

`if` EVALUABLE read 6,676 while `if` compared read 682. All 5,994 missing cells
came from **one problem replicated six times**, on a sheet whose header repeats
`PCS_MTR`, `DATE`, `PARTY_NAME` and three more.

The drop was legitimate — the name→column map really is ambiguous — but
`a1trans.translate` had returned **`CLEAN`** for a translation onto a name that
does not uniquely resolve. A CLEAN verdict asserts the expression mechanically
translates, and one that cannot be resolved against its own header does not.

Fixed: `translate` now returns `NEEDS-HUMAN` naming the ambiguous columns. After
the fix `if` EVALUABLE and `if` compared are both **682** — the inflated figure
is gone. **W3's "mechanically translatable" counts are optimistic by the same
error** wherever they were computed with the old translator.

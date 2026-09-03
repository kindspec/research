# Corrections 9–15, from clearance and scale testing

## 9. IronCalc is `MIT OR Apache-2.0`, not Apache-2.0 (verified)

    crates.io: ironcalc      license=MIT OR Apache-2.0  newest=0.8.3
               ironcalc_base license=MIT OR Apache-2.0  newest=0.8.3

Better than reported, and unchanged across all 15 releases. Grant-funded, no
CLA, no commercial tier — structurally unable to rug-pull the way Handsontable
did (last MIT release 6.2.2, 2018-12-19; flip at 7.0.0, 2019-03-06).

## 10. DESIGN.md §13 contradicts itself, and the fix changes the plan

§13 rejects CEL **for being IEEE-754-doubles-only**, then adopts IronCalc in the
same sentence while requiring "decimal arithmetic." **IronCalc is also f64-only**
(`CalcResult::Number(f64)`). The section argues against itself.

Worse for fit: IronCalc has **no grid-free named-binding API** — everything is
`(sheet, row, col)`, and `mod functions` is private. The engine I planned to
wrap is coordinate-native, which is the one thing this design exists to avoid.

**Resolution:** do not take IronCalc as a runtime dependency. Use its public
`expressions` parser as a **differential-testing oracle** for compatibility, and
implement the small function set over decimal arithmetic. That is affordable
precisely because of an earlier measurement: only ~7% of spreadsheets contain
any formula, and **76% of real formula usage is fifteen functions**. Fifteen
decimal functions is a weekend; a coordinate-native f64 engine is a permanent
contradiction.

## 11. Padding is an I1 violation and a merge hazard — the format changes

DESIGN.md §7 shows the table format with aligned columns. Measured on a
2,000-row table, changing one cell from `9` to `1000`:

    padded    2002 added / 2002 removed lines   238,370 bytes of diff
    canonical    1 added /    1 removed line        413 bytes

And it is not cosmetic. Two **genuinely disjoint** edits — one author widening a
cell, another editing a different row far away:

    padded      merge exit=1   CONFLICT
    canonical   merge exit=0   clean

At 100k rows the padded diff is 29.3 MB for a one-character semantic edit. A
widening cell reflows every row, so padding manufactures conflicts between
edits that do not touch each other.

**Canonical form is single-space `| a | b |`. Alignment is a rendered view.**
`render(parse(b)) == b` still holds for padded input — canonicalisation is a
separate explicit operation, and `canon(canon(x)) == canon(x)` is verified.

Note the size tax is mostly irrelevant: padded files are +176.7% over CSV raw
but only +15.1% under gzip. **The diffs were the problem, not the bytes** —
which is the same lesson as correction C5, in the opposite direction.

## 12. My closure hash silently truncated cycles

Correction 4 fixed the cache to hash the transitive dependency closure. The fix
introduced a new bug: a shared `seen` set made a cycle **terminate quietly and
return a hash for a closure it had not walked.** A two-cycle, a 100-artifact
ring and a self-reference all returned a hash with no error.

This is worse than the bug it replaced, and it is my own. Note also that an
earlier experiment recorded "could not turn a cycle into a silent fixed point —
HELD"; that was true of the *old* key and I carried the reassurance forward
across a rewrite that invalidated it.

Fixed — memoised DAG hash with an explicit recursion stack:

    two-cycle       Cycle detected: a.tbl -> b.tbl -> a.tbl
    self-reference  Cycle detected: c.tbl -> c.tbl

Measured elsewhere at 2.6× on flat graphs and **93.6× at depth 400**.

## 13. "Hashing is 2.3% of the parse it guards" inverts with depth

§9 quotes that figure to justify artifact-granularity content addressing. It was
measured on a **dependency-free artifact**. With a closure, `closure_hash` is
**83–84% of a warm build**, and from depth ~25 a warm build costs the same as a
cold one — the cache stops buying anything. The memoised rewrite restores it.

The claim in §9 is right about granularity and wrong about the constant.

## 14. Content equality standing in for identity — for the third time

The block merger silently **drops a their-side new block whose text duplicates
an existing block**. Same root cause as the paragraph-duplication bug in L3 and
the row-identity ablation: equality of content is not identity. Three
occurrences, three different subsystems, all mine.

## 15. The project name and file extension both fail clearance

Verified directly:

    crates.io  `gws`  EXISTS — JSON-RPC websocket client/server, 919 downloads
    npm        `gws`  EXISTS
    PyPI       `gws`  EXISTS — "A GWS module"

plus `StreakyCobra/gws` (237★), a git-workspace CLI occupying the same
conceptual slot. And `.tbl` matches **158,208 GitHub files** — roff `tbl`, game
mods, and four CAD/GIS formats.

**Both must change before the first commit.** Suggested: `RowSpec` and
`.mdtbl` (0 matches). Also flagged: the widely-repeated "Total War uses .tbl"
claim did not verify — do not repeat it.

## Also surfaced: the cross-artifact story is half-implemented

A table→table column formula (`unit = rates.tbl#rate`) **crashes** the
evaluator, and the design's own example file for it is zero bytes.
Document→table references resolve; table→table references are dependency edges
the engine discovers but cannot evaluate. §3's cross-artifact derivation is real
for one direction and aspirational for the other, and the report should say so.

## Prior art that must be credited

- **org-mode `#+TBLFM:` with its `!` column-name row** — nominal column
  addressing in a plaintext table, shipping for ~20 years, plus a live markdown
  port. It violates I2, I4, the `prev.` finding *and* namespace co-location,
  which makes it the perfect negative control rather than a competitor.
- **daff/Coopy** has shipped id-keyed three-way tabular merge **wired into
  `git merge`** since 2013. It does it through a merge driver — which this
  design proves undeployable. That single sentence is the thesis.
- **ClassSheets** (ASE 2005) and **Object Spreadsheets** (Onward! 2016).
- Check **nbdime**'s test suite before claiming novelty on "a conformance suite
  asserting evaluated values after a real git merge."

## What did not break

The realistic-repo simulation is comfortable: 2,000 artifacts, 4,998 commits,
95.6 MB tree — `git status` 4.0 ms, clone 262 ms, full `check` 1.06 s, warm
`build` 3.80 s, packed `.git` 11.9 MB. Markdown parsing found no limit at
57 MB/s. Nothing in the scale results threatens the architecture; the two things
that broke were a decoration and an implementation shortcut.

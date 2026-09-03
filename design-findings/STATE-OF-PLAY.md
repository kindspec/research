# State of play, and what must be settled before planning

> **Historical.** A–O below were the open list *before* the design passes and
> the rowspec build. They are closed or superseded; the record is kept because
> the sequencing argument is still the one being followed. Current state is at
> the bottom, under "Campaign log".

## Settled (evidence in DESIGN.md)

- Verdict: build a missing layer — a specified, conformance-tested
  representation discipline. Not a suite, not a substrate, not a merge driver.
- Two primitives: TEXT and ENTITY MAP.
- Seven invariants, I7 revised after measurement.
- Correctness lives in the representation, not in a merge algorithm.
- Git is the distribution and durability format; the version control is ours.
- The server owns the merge (forge-side merges ignore .gitattributes).
- CRDT only as live-session merge machinery over file bytes.
- Identity: minted UUID per artifact; opaque ids for rows; NO minted ids for
  prose blocks; quote-anchoring for annotations.
- The deliverable is an executable conformance suite.

## OPEN — design-blocking. I must resolve these.

A. **Meaning drift** (Risk 1, the deepest hole). A reference that still
   RESOLVES, to something else. `total→gross`, `net→total`, `sum(total)`
   untouched -> 504.00 where truth is 604.80, no error. No mechanism exists.

B. **Row-relative computation is now UNSUPPORTED.** I removed `prev.` because
   it is a coordinate, and left a hole: running totals, cumulative sums, and
   every time-series model. The prior pass already flagged this as the defect
   that made a competitor's engine unusable. I removed the bug and did not
   replace the capability.

C. **The namespace audit was never done mechanically.** R1 fixed one instance
   ad hoc. Nobody has enumerated every namespace in every format and checked
   co-location or parse-time validation. Seven breaks were found — nobody
   knows if that is the tail or the head.

D. **`.canvas` has zero test coverage** and three known referential-integrity
   holes: an override for a deleted node, an edge to a renamed node, and two
   branches adding different nodes with the same name.

E. **The document leg's markdown namespaces are unfixed** — link labels,
   footnote labels, heading anchors, frontmatter keys — plus artifact UUID
   duplication on `cp`.

## OPEN — deliverable-blocking. Must be built.

F. **The conformance suite is thin and contains a tautology.** ~15 missing
   categories enumerated by the red team, and no mutation gate. This is THE
   deliverable; it cannot ship as a demo.

G. **Nothing has been validated end-to-end on a realistic corpus.** Every
   experiment is a toy fixture; the largest `.tbl` tested has six rows.

H. **The server-side merge path is architecturally required and I have never
   run it.**

## OPEN — risk-reducing. Must be checked.

I. Scale and performance of these formats specifically.
J. Licensing and dependency clearance; name clearance before a repo exists.
K. The load-bearing 0.00% anchoring figure is one pass over three corpora.
L. Import/export interop with .xlsx/.csv/Sheets — untouched, and adoption
   depends on it entirely.
M. The editions/format-evolution mechanism has never been prototyped.
N. Prior-art recheck now that the design is concrete and specific.
O. Who this is for, concretely. Distribution killed everyone else.

## Sequencing

I take A–E (they need design judgment and are where the thesis lives).
Agents take F–O in two waves.
Then a second red-team pass against the FIXED design before planning.


---

## Campaign log

### 2026-08-30 — second dogfood campaign, closed

Four agents ran against the built artifact rather than against the design.

**E2 (ergonomics, second trial)** flipped the verdict from *"no, not as it
ships"* to *"yes, but I would not hand it to a colleague today"*. First valid
table in ~5 minutes with nothing guessed, against ~15 minutes of hunting in the
first trial. A 14-row whole-table conflict was resolved by hand and one `eval`
confirmed the grand total unchanged — *"with CSV I'd have had a diff and a
hope."* Then, three rounds in, an ordinary per-vendor subtotal over a computed
column **evaluated to 0 in every row** with `check` reporting `0 refused` and
`eval` exiting 0. Only `sum` did it; `min`/`max`/`avg` failed loudly. Fixed by
restructuring evaluation into plain → row-relative → group → plain.

**E3 (formula grammar)** found the same class independently by a different
route, and caught me breaking §8 by putting explanations *inside* `#REF!`
values — which are data that propagate through aggregates. §4.2 came out of
this pass.

**E1 (differential evaluation against real spreadsheets)** is the campaign's
headline. **55,681 formula cells from 267 real workbooks**, checked against the
values the original files had cached. **99.84% agreement excluding two
by-design classes**, 0.13% wrong numbers, and **not one unexplained
disagreement**. 38,352 cells from 47 Enron business workbooks, 30,720
bit-exact, zero wrong. The 48 wrong numbers were all one root cause — `_ast()`
called `ast.parse`, so §4.2 was normative prose while Python's grammar was what
ran. See `docs/rationale.md`. It also closed the arithmetic model: 501 cells
separated a decimal implementation from a binary64 one, both conformant.

**M0 (adversarial suite author)** wrote 51 cases against §4.2 without reading
the reference, found the `#REF!` originating-name relabelling, a cycle whose
shape was lost crossing the group pass, an unenforced §4.2 rule 5, and then two
defects in the hand-written parser that replaced `ast.parse` — stacked unary
minus, and a nesting depth bounded only by the host call stack.

**The recurring meta-finding reached its eighth instance**, this time in the
harness itself: the conformance runner took its fixture root as a relative
path, so run from the repository root it walked nothing and printed
`0 failure(s) across the fixture tree` over 226 unopened cases, four of them
failing. An empty tree is now a hard failure.

**Still open.** `#REF!(name)` conflates a name that does not exist with one
whose cell is blank — 30.4% of the differential's comparisons — and splitting
it changes §8's error vocabulary, so it is deliberately not being rushed.
Formula coverage is the real interop ceiling: 21,165 corpus cells are
translatable but outside §4.2 (`IF` 12,643, `SUM` 5,309), which is why W3's
11.4% must be read as ~7.9%.

# Pass 9 — what the red team broke, and what the design becomes

The adversary produced **seven (a)-class breaks**: clean merge under stock git,
wrong answer, no marker. I reproduced the worst of them myself. This is the
most important pass in the project, because it falsifies the design's sharpest
claim.

## Verified breaks

**1. The `.tbl` aggregate namespace is scattered — the design's own diagnosed
defect, inside the format offered as the safe contrast.** Alice adds
`subtotal := sum(qty)` near the top of the trailing block, Bob adds
`subtotal := sum(total)` at the bottom: `exit=0`, no markers, both lines
present, one author's binding silently gone.

Sub-case, verified: NFC `café` and NFD `café` are visually identical, merge
clean, and the NFD line **fails the aggregate regex** (`\w` rejects the
combining mark) so it is silently SKIPPED, leaving the other binding answering
to a name that renders identically.

PASS4 stated "co-locate a namespace's bindings" as a rule and then never
audited the formats against it. The column header is genuinely co-located and
held under every attack, including the Unicode one. The aggregate block is not.

**2. `prev.` is a coordinate, and it restores the 480-vs-660 defect.** The
row-relative operator I proposed for running totals means "the row above" —
a place. Alice inserts a row near the top, Bob edits one near the bottom:
clean merge, and a row neither of them touched changes from `-273.80` to
`218.68`. It also converts commutative aggregates into non-commutative ones:
`sum` survives a reorder, `min(balance)` — an overdraft check — does not.

**3. A rename makes a DIFFERENT column answer to the old name.** One header
line: `total`→`gross`, `net`→`total`, with `grand := sum(total)` untouched.
Clean merge, `grand = 504.00` where the truth is `604.80`, and **no `#REF!`**.
Verified, along with a second form: delete a column and keep the aggregate
name — "Nothing broke. The name resolved. The meaning changed."

**This is the deepest finding in the project.** I3 was aimed at the wrong
failure. It catches references that BREAK. The dangerous case is a reference
that still RESOLVES, to something else. Loud failure machinery is irrelevant
when nothing fails.

**4. My cache never invalidated on a cross-artifact dependency.** Verified and
FIXED. The key hashed one artifact's bytes, so editing a dependency left it
unchanged:

    old single-artifact key   before=1dcb75c5dbf2  after=1dcb75c5dbf2  CHANGED=False
    closure key (fixed)       before=4340c86139c2  after=adafc27b7e77  CHANGED=True

"Invalidation is exact" was true only for single-artifact derivations. It was
also an I4 violation: two machines at the same commit rendered different
numbers.

**5. My type-aware merger was LESS correct than stock git.** On a copy-pasted
duplicate row id, stock git gives the correct 684.0 and `merge3` gives 744.0,
with zero conflicts either way. This is exactly what I6 forbids, and it
reinforces the decision to keep structural merge outside the correctness
boundary rather than softening it.

**6. Markdown has four scattered namespaces, not one** — link labels (already
known), footnote labels, heading anchors including PASS5's own worked example
`{#findings}`, and YAML frontmatter keys. Also: `cp doc.md copy.md` duplicates
the minted artifact UUID that the notes sidecar is keyed by, and no mechanism
exists for that at all.

**7. The canvas format has no referential integrity**: an `@layout` override
for a node deleted on the other branch resolves to a position for a node that
does not exist; an edge to a renamed node silently vanishes.

## Fixes applied and verified

    duplicate aggregate name   -> Malformed: line 6: duplicate aggregate name 'subtotal'
    NFC/NFD name collision     -> Malformed: line 6: duplicate aggregate name 'café'
                                  (NFC-normalise on parse, then the collision is visible)
    cross-artifact cache key    -> closure hash over the transitive dependency set
    `prev.`                     -> REMOVED from the design

## What held, under deliberate attack

Twelve negative results, of which the ones that matter:

- The base table grammar: the adversary **could not reconstruct the 480 failure
  without `prev.`**.
- The column namespace is genuinely co-located; every collision conflicted.
- The address grammar is file-qualified, so cross-file name collision is
  impossible — "the one place the grammar genuinely helps".
- **Confluence held.** Six merge orders over three branches with a compounding
  formula produced **1 distinct outcome out of 6**. The adversary expected to
  break this and did not.
- Cycles fail loudly; a silent cached fixed point could not be constructed.
- `blocks.py` round-trip byte-exact on everything thrown at it.
- Conflict-marker rejection solid on every path.

## The conformance suite's own failure, and a correction to the charge

The charge: the `.tbl` I1 round-trip test is a tautology (`parse` and `render`
are identity functions, so it asserts `doc == doc`), and sabotaging `tbl.parse`
leaves the `.tbl` half green.

**The first half is correct and damning.** The second half overstates. I
mutation-tested it — sabotaging `parse` to silently discard every third row:

    baseline                          TOTAL FAILURES: 1
    with parse sabotaged              TOTAL FAILURES: 3
      !! two distant row inserts:     SILENTLY WRONG -- evaluated 420.0, expected 660.0
      !! disjoint cell edits:         SILENTLY WRONG -- evaluated 240.0, expected 516.0

The round-trip test stayed green, exactly as charged. The **semantic**
assertions caught the mutation. So the suite is not vacuous — but its I1 test
is, and a suite whose primary artifact is its own credibility cannot ship a
tautology. Both facts belong in the record.

Missing coverage the adversary enumerated, all of which is real: confluence,
duplicate row id, duplicate aggregate name, field-count mismatch,
delimiter-in-cell, numeric coercion, order independence, the address grammar,
derivation and cache, `.canvas` (no coverage at all), `merge-tree` in a bare
repo, CRLF/BOM/encoding, NFC/NFD, corpus size, and a mutation gate.

## The honest reformulation of I6

I6 as stated — "correct or loud under unmodified git" — is not achieved by
these formats, and seven ordinary cases prove it. The adversary's replacement
is better and I adopt it:

    Stock git merges correctly when the unit of merge is the unit of meaning
    AND every namespace in the artifact is co-located on one line.

PASS4 found the first clause and stated the second as a rule without auditing
against it. **Doing that audit mechanically, as a conformance test, is most of
the remaining work** — and it is exactly the kind of work a conformance suite
exists to force.

## What this does to the verdict's confidence

It does not reverse the direction, and it materially lowers the confidence.

- The core claim survives in a narrower form: nominal addressing removes a
  class of silent-wrong merges that positional addressing cannot avoid, and
  the adversary could not break the base grammar without the operator I have
  now removed.
- But **every format I wrote contained at least one instance of the very
  defect the design exists to eliminate**, and I did not find them. An
  adversary with a week found seven.
- The correct inference is not "the invariants are marketing". It is that
  **invariants of this kind are only real once mechanically enforced**, which
  is the argument for the conformance suite being the deliverable — now made
  by my own failure rather than by analogy to CommonMark.

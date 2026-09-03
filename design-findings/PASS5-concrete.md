# Pass 5 — the concrete design as it stands

Draft. D6 (computation), D7 (spatial), D8 (sub-artifact identity), D10
(interfaces), D11 (format evolution) are still out and will refine specifics.

## Repository layout

    myrepo/
      docs/q3-review.md
      data/budget.tbl
      diagrams/arch.canvas
      .notes/                  standoff annotations, keyed by artifact UUID
      .gitattributes
      .gitignore               ignores .cache/
      .cache/                  content-addressed derived values (never committed)

There is no manifest and no registry. **Type is the filename suffix.** A second
source of truth about what a file is can disagree with the tree; Unix and
`.gitattributes` already solved this.

## The four invariants, restated as acceptance criteria

    I1 LOCALITY              bounded edit -> bounded diff
    I2 NOMINAL ADDRESSING    references name things, never places
    I3 LOUD FAILURE          broken refs fail visibly; never 0/empty/stale
    I4 NO HIDDEN STATE       everything affecting output is in the files
    I5 VALID ARTIFACTS       the working tree never holds a file its own
                             format cannot parse
    I6 STOCK-GIT CORRECTNESS correct or loud under unmodified git with none of
                             our tooling installed

## Documents — `.md`

    ---
    id: 01J8ZQ4K7X
    title: Q3 Review
    ---

    # Findings {#findings}

    Procurement totalled {{ budget.tbl#grand }} against a plan of 500.00.

- Frontmatter carries the minted artifact UUID. One line per file; negligible
  cost, and the alternative was measured at 6% history recovery.
- Attributes use the `{#id .class}` syntax (pandoc/djot-compatible) so blocks
  can be named WHEN REFERENCED, not by default.
- **The parser finds block boundaries and never re-emits content** (L3), so
  round-trip is byte-exact by construction and the syntax is replaceable — the
  substrate is not married to markdown. This is what makes the djot question a
  later decision rather than a founding one.
- Merge: normal line merge (it usually works, and prose is the most
  collaborative type), plus client-side refusal to render or commit a file
  containing conflict markers. Residual risk stated in V-corrections.

## Tables — `.tbl`

    | item     | qty | unit  | total = qty * unit |
    | -------- | --: | ----: | -----------------: |
    | widget   |  10 | 12.00 |                    |
    | gadget   |  20 |  6.00 |                    |

    key := item
    grand := sum(total)

- **One row per line** — the merge unit is the meaning unit (Pass 4).
- **Formula in the column header, cells blank** — the formula namespace is
  co-located on one line, so a name collision is a line collision that git
  refuses (verified, `experiments/V-ns/`). Grist's column-formula model.
- **No coordinates exist in the grammar.** Verified consequence: the measured
  480-vs-660 silent-wrong merge becomes a clean 660 from stock git (L1).
- `key :=` declares row identity. Without it, structural merge degrades to
  alignment heuristics; with it, row order is irrelevant to merge.
- Row-relative access needs an explicit operator (`prev.total`), not an offset.

## Canvases — `.canvas`

    node api  "API Gateway"   {kind: service}
    node db   "Postgres"      {kind: datastore}
    edge api -> db            "queries"

    @layout
    db { at: 400, 500 }

- Semantics declared; **positions derived** by auto-layout.
- `@layout` is a SPARSE override layer keyed by name — USD's non-destructive
  composition idea, at document scale. Verified: adding a node and hand-nudging
  a different node merge cleanly, where the full-coordinate representation both
  conflicts and produces unparseable JSON (L4).
- Scope limit, stated honestly: this covers STRUCTURED diagrams. Freeform
  illustration has no semantic layer to derive from and should be an opaque
  versioned blob, not a merged artifact.

## The address grammar — one grammar, no coordinates

    budget.tbl#grand              an aggregate
    budget.tbl#q3.revenue         a named cell
    q3-review.md#findings         a named block
    arch.canvas#api               a named shape

Every kind resolves a NAME PATH. I2 is enforced by the grammar having no
coordinate syntax to express, rather than by discipline.

## The type contract — the entire extension surface

    parse   : bytes -> EntityMap        (boundaries only; never re-emit)
    render  : EntityMap -> bytes        (render . parse == id)
    resolve : EntityMap, NamePath -> Node
    refs    : EntityMap -> [Reference]  (dependencies DISCOVERED, not declared)

Four functions. Note what is NOT here any more: `diff` and `merge`. Pass 2 put
them in the contract; D3 removed them from the correctness boundary. Structural
merge is an optional local accelerator, because it cannot be deployed portably
AND cannot fix positional addressing anyway (daff produced the identical wrong
answer as plain git).

## Derivation — one mechanism

Keys are `(artifact, namepath)`; values are cells or whole files. Dependencies
are discovered by `refs`. Memoisation is content-addressed, so invalidation is
exact and reverting an edit is a cache hit (L5). Formulas, cross-document
references, charts and exports are the same mechanism — *Build Systems à la
Carte*'s suspending scheduler with a constructive-trace rebuilder.

Derived values are never committed by default. A rendered artifact is a
separate derived file; committing it is a `.gitignore` decision.

## Collaboration — two clocks

    within a session (seconds, humans watching)   text CRDT over file bytes,
                                                  state DISCARDED after merge
    across sessions  (days, nobody watching)      git three-way merge

A git commit is eg-walker's "critical version", which is what lets the op log
be truncated — the thing a pure-CRDT system can never do because someone may
reconnect after six months.

The write path is a **bare repository with per-writer indexes and `update-ref`
compare-and-swap**, retrying by re-applying INTENT rather than replaying a
diff. Verified: 200/200 concurrent commits to the same file, zero loss, 3.4s.
There is no global lock and no single-writer constraint.

Do NOT put a CRDT under tables or canvases: convergence does not preserve
invariants that span more than one property.

## What is deliberately NOT in the core

- a formula engine (wrap IronCalc)
- a layout engine (wrap ELK/dagre/Graphviz)
- a rendering/typesetting engine (wrap Typst)
- a structural merge algorithm (optional accelerator, outside correctness)
- a sync server (the bare-repo CAS write path is ~200 lines of git plumbing)
- per-file ACLs, forms, calendar protocols, real-time presence
- a CRDT for anything except live text sessions

---

# Revisions after D6 (computation) and D9 (git substrate)

## R1. Row identity: an opaque id column, not a natural key

L2 concluded "a declared key is what buys the clean merge". An ablation of four
identity functions across four scenarios shows a NATURAL key is not enough:

    identity        edit-2-cols   key renamed   both insert   duplicate keys
    natural key     ok            LOST AN EDIT  ok            OVERWROTE A ROW
    content hash    SPLIT ROW     SPLIT ROW     ok            ok
    opaque id       ok            ok            ok            ok
    positional      ok            ok            DROPPED ROW   ok

**Every failure was silent — zero conflicts reported in every wrong case.**

Revised format:

    | id     | item     | qty | unit  | total = qty * unit |
    | ------ | -------- | --: | ----: | -----------------: |
    | r_7f3a | widget   |  10 | 12.00 |                    |

The asymmetry that makes this palatable: **a human writes column NAMES into
formulas; a human never writes a row id into anything.** So literal names for
columns, opaque ids for rows. The id is machine-managed noise in a column the
reader can ignore, not a reference anyone types.

Convergent evidence: Grist's `mergeCols`, `sqldiff` and SQLite sessions both
requiring a declared PK, daff shipping `--id` because its 31-candidate-key
brute force is a fallback, and Willison's `git-history` requiring `--id`.

## R2. Tables are LONG (tidy), not WIDE

Measured: branch A adds a year, branch B adds a country. The WIDE file
conflicted across its entire contents; the LONG file merged automatically and
correctly. In wide form the header row is a shared mutable resource that every
category addition must rewrite — Pass 3's coupled-state defect, in table form.

So tidy/long is not a data-science style preference here; it is a merge
correctness requirement. Wide is a VIEW, produced by derivation.

## R3. Derivation granularity: artifact, not cell

Per-cell memoisation costs **21.3x the arithmetic it protects** (200k cells:
10.9 ms compute vs 232.9 ms bookkeeping). At artifact granularity, hashing is
**2.3%** of the parse it guards. Three orders of magnitude.

This explains why *Build Systems à la Carte* rates Excel the worst cell in its
taxonomy (restarting scheduler + dirty-bit rebuilder, "Minimal: No; Cutoff:
No") — a dirty bit is the only rebuilder you can afford per cell. Move the unit
up and content-addressing becomes free. **Granularity and rebuilder are the
same choice**, and L5's design is on the right side of it.

Also: non-determinism breaks the model (two `now()` calls 50 ms apart returned
the same cached timestamp). The fix is a taint — BSaLC's volatile key, Bazel's
`do_not_cache` — not cleverness.

## R4. Committed derived values are close to never acceptable

Holding the format and the edits fixed and changing ONLY whether results are
written into the file flipped L1's correct 660 into two distinct failures:

- two input edits far apart -> clean merge, every derived value in the file
  false, no marker (the file asserts `99 x 12.00 = 120.00`)
- both sides update the aggregate -> conflict offering 580 and 560 when the
  truth is 660. Git hands the user a two-way choice in which NEITHER option is
  correct.

Sharper rule than "don't commit outputs":

    A derived value may not be committed if its dependency set spans more than
    one mergeable entity.

Row-local values merge with their row. Cross-entity aggregates have no manual
remedy, so they must never be in the file.

## R5. The server owns the merge (the biggest structural change)

`.gitattributes` is not consulted in a bare repo, so forge-side merges ignore
every protection the repository declares (verified, `experiments/V-bare/`).
Custom merge drivers are unsupported on GitLab.com and ignored by GitHub.

Therefore the substrate needs a server component for correct collaboration:
`git merge-tree --write-tree` yields the three conflict stages as blobs in a
bare repo; the server merges them however it likes and writes back with
`hash-object` / `mktree` / `commit-tree` / `update-ref`. A plain `git clone`
then receives a correctly merged artifact with no attributes and no config.

**Git is the distribution and durability format; the version control is ours.**

Priced honestly: this means "just use GitHub's merge button" is unsafe for
these types, and a self-hosted or hosted component is not optional for teams.
It does NOT compromise the single-user or single-writer case, and `git clone`
remains a complete, verifiable backup.

## R6. Prose should use semantic line breaks

`git blame` credited the rewrapper with 6 of 10 lines after a one-word edit
plus a 72->80 column reflow, including two paragraphs he never touched; `-w`
and `-M -C -C -C` both fail. The same edit on unwrapped text: correct, and a
`1 1` numstat.

**This is a format decision, not a git limitation.** One sentence per line (or
one clause per line) makes blame, diff and merge all work on prose. It costs a
convention; it buys attribution that is otherwise simply wrong.

## R7. What the evidence says the product actually is

Only ~7% of spreadsheets contain any formula (Fuse corpus, 249,376 files), and
76% of Enron's formula usage is 15 functions. The 500-function requirement is
dead, and so is the formula-first framing.

More importantly: the ONLY error-reduction intervention with real evidence
behind it is **code inspection** — which is exactly what git provides and what
Excel structurally cannot. Chalhoub & Sarkar (CHI 2022) conclude that no
structure can replace the flexible grid, so do not try.

    The wedge is storage-and-review, not authoring.

This also resolves the prior pass's named-addressing counter-evidence.
McKeever & McDaid found range names made novices slower and more error-prone;
Calculation View (n=22) found 37.14% faster authoring and 40.7% faster
debugging (p<10^-3), with LOW-expertise users gaining most (55.3%). The
difference is not naming — it is whether the binding is VISIBLE beside the
reference or hidden in a Name Manager. Column headers are visible. That is the
mechanism, and it is now evidenced rather than asserted.

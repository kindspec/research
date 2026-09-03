# A Git-Backed Substrate for Knowledge Artifacts — design report

Research and prototyping: 2026-08-28. Thirteen parallel research tracks, one
dedicated adversary, and eight experiment sets of my own. Everything asserted
here as measured was run; the commands and output are in `experiments/`, the
evidence in `design-findings/`, and the earlier landscape pass in `RESEARCH.md`.

Where a claim is unverified it is marked. Where I was wrong, the correction is
in the text rather than in a footnote — there are seven of them, and the pattern
they form is itself a finding.

---

## 1. Verdict

**Build only a missing layer. Do not build a suite, and do not build a
substrate in the OpenDoc sense.**

The layer is a **specified, conformance-tested representation discipline for
git-versioned structured artifacts**, whose primary shipped artifact is an
executable conformance suite rather than a program. Tables are the beachhead.

Three things this verdict is not:

- Not "build Docs/Sheets/Slides on git." The graveyard is thirteen years deep
  and the post-mortems are unanimous about why.
- Not "build a universal document model." That is OpenDoc, Chandler, and
  Xanadu, and the failure mechanism is well documented.
- Not "build a merge driver," which is what the prosecution conceded to. That
  prescription is refuted below by measurement.

**Confidence: moderate, and materially lower than when I started drafting.** A
dedicated adversary found seven silent-wrong merges in the formats I had
designed specifically to eliminate silent-wrong merges, and I had not found
them myself. The direction survives; the assurance does not. The correct
inference is not that the invariants are marketing — it is that invariants of
this kind are only real once mechanically enforced, which is precisely the
argument for the deliverable being a test suite. That argument is now made by
my own failure rather than by analogy.

### What the value actually is

Not authoring. **Storage and review.**

Only ~7% of spreadsheets contain any formula at all (Fuse corpus, 249,376
files), and 76% of Enron's formula usage is fifteen functions. The
five-hundred-function requirement is dead, and so is the formula-first framing.
Meanwhile the only spreadsheet-error-reduction intervention with real evidence
behind it is **code inspection** — which is exactly what git provides and what
Excel structurally cannot. Chalhoub & Sarkar (CHI 2022) conclude that no
structure can replace the flexible grid, so the design should not try.

---

## 2. Strongest prior art, and how close each comes

| System | What it solves | Why it is not the answer |
|---|---|---|
| **Grist** | Column formulas, real dependency graph, ACLs | SQLite canonical; not a plaintext/git story |
| **dbt** | Structured data in git, DAG, `ref()`, wildly adopted | SQL models only; no documents, no canvases; needs a warehouse |
| **marimo** | Notebooks as pure `.py`, reactive DAG, no hidden state | Python-shaped; not an artifact substrate |
| **Dolt** | Cell-level three-way merge, conflicts in side tables | A MySQL server; opaque binary storage; tables only |
| **jujutsu** | First-class conflicts, change IDs, op log | Materialisation always writes markers; `.gitattributes` unsupported; pre-1.0 |
| **Irmin** | Mergeable types over a git-compatible store | The exact abstraction — but everyone who shipped on it left it |
| **CommonMark** | An executable spec that produced ~45 implementations | Cannot express a table; constrains one projection, not the model |
| **Ink & Switch (Patchwork/Upwelling)** | The deepest user research on versioning prose | Concluded against git-style branching; now barely mentions git |
| **Nimbalyst** | All three legs, MIT, active | CSV metadata line breaks CSV; sells to developers |
| **USD** | Non-destructive layered composition | Enormous; and its own FAQ concedes orphaned overrides are the user's problem |

The closest single thing to this design is **CommonMark's method applied to
structured artifacts**: an executable specification that makes conformance a
measurement. Nobody has done that for tables, and the evidence that it is the
active ingredient is unusually strong (§3).

---

## 3. The genuine remaining gap

Three findings triangulate it.

**(a) Positional addressing merges silently wrong, and no algorithm fixes it.**
Two branches inserting rows into a CSV with A1 formulas auto-merge with zero
conflicts and total 480 where the truth is 660 — LibreOffice confirmed. The
formal statement is Abiteboul, Hull & Vianu: named and unnamed perspectives
have equal expressive power but different primitive operators, so positional
addressing costs not expressiveness but *cheap correspondence* — which is what
merging is. Decisively: **`daff` merged the same file's rows perfectly and
produced the identical wrong answer.** A structural merger cannot see that a
string in a cell encodes a position.

**(b) The remedy cannot be shipped as a merge driver.** `.gitattributes` is
tracked and travels; `merge.<name>.driver` lives in `.git/config` and never
does. A fresh clone silently falls back to line merge. Worse, verified myself:
a **bare repository does not consult `.gitattributes` at all**, so a forge-side
merge writes conflict markers into a file the repository declared `binary`.
GitLab documents that custom merge drivers are unsupported on GitLab.com;
GitHub Support says GitHub "doesn't consider user-defined .gitattributes
files."

So the prosecution's own concession — "build the merge driver, the way daff
did" — is refuted twice over. It identifies the gap correctly and prescribes a
vehicle that does not work.

**(c) The active ingredient is a conformance suite, and there is nearly a
controlled experiment for it.** CommonMark and djot share an author. djot is
the better language design, written because "there are 17 principles governing
emphasis... and these rules still leave cases undecided." CommonMark ships 655
executable examples and has ~45 implementations across 25+ languages, each
claiming conformance as *a version number of the suite*. djot ships **no
conformance suite** and has six implementations after four years.

**Therefore the gap is: a specified, testable representation discipline that
makes stock git's dumb line merge correct — and nobody has written the spec or
the suite.**

---

## 4. Core principles and invariants

Seven invariants. Two were added by measurement after I got them wrong, and one
was reformulated by the adversary.

    I1  LOCALITY
        A semantic edit of bounded size produces a byte diff of bounded size.
        Enforced by render(parse(b)) == b and canon(canon(x)) == canon(x) as
        property tests over a corpus, never as a coding guideline.

    I2  NOMINAL ADDRESSING
        Nothing may be referenced by a coordinate that a concurrent edit can
        change. The address grammar contains no coordinate syntax at all, so
        this is enforced by the grammar rather than by discipline.

    I3  LOUD FAILURE
        A broken reference fails visibly and locally: never zero, never empty,
        never stale, never plausible. Errors propagate through aggregates.
        (Insufficient as stated — see §16, risk 1.)

    I4  NO HIDDEN STATE
        Everything affecting a rendered result is in the files. A derived value
        may not be committed if its dependency set spans more than one
        mergeable entity.

    I5  VALID ARTIFACTS
        The working tree never holds a file its own format cannot parse.
        (A property of a deployment, not of a format — worded accordingly.)

    I6  STOCK-GIT CORRECTNESS  (as reformulated by the adversary)
        Stock git merges correctly when the unit of merge is the unit of
        meaning AND every namespace in the artifact is co-located on one line.
        Type-aware merge may improve the experience, never the correctness.

    I7  SPECIFIED PERMISSIVENESS  (revised after measurement -- see §14)
        Recognition is total and framing is never ignorable. Exactly one
        lexically-marked ignorable channel exists, and it carries an INERTNESS
        PROMISE: nothing in it may ever contribute to a derived value.
        Poison the value, not the file; a reader that poisoned anything may
        not write.

### The defect all of this is organised against

Four failures that looked unrelated turned out to be one:

    A1 cell references           insert a row -> 480 instead of 660
    markdown alignment rows      my renderer silently dropped `--:`
    block trailing blank lines   moving a block defeated its identity
    Graphviz-derived positions   adding one node moved 4 of 4 others

**Coupled representation: state whose bytes must change when unrelated content
changes.** Coupled state destroys diffs, and destroyed diffs are what make a
git-backed system pointless.

### The rule that follows

    SERIALIZE SO THAT THE UNIT OF MERGE IS THE UNIT OF MEANING.

Git merges by line, so one line should be one entity. Three tracks reached this
independently, most sharply from the AST direction: *a line merger's boundaries
are the serialization's boundaries, and in a serialized AST those do not
coincide with the structure's.*

And its corollary, which I stated as a rule and then failed to apply to my own
formats:

    CO-LOCATE A NAMESPACE'S BINDINGS, or validate them at parse time.
    Scattered, unvalidated namespaces are silent-wrong generators.

---

## 5. Architectures considered and rejected

**Content-addressed immutable objects as canonical, git as transport.**
Rejected on the strongest evidence in the study. Four serious teams built it
and all left: Unison *deleted* git support then moved to SQLite; Tezos left
`irmin-git` for lmdb, leveldb, then `irmin-pack`; bup had to add non-git
indexes; Noms' author concluded decentralised merge "wasn't that satisfying"
and built something centralised. Built and measured directly: 2.5× the `.git`,
**4.5× the working tree**, 4× the file count, and `grep` returns hashes instead
of names. Nix's content-addressed derivations remain experimental four and a
half years after the RFC merged.

**A serialized AST as the canonical artifact.** Rejected on two measurements.
`pandoc -f json` hard-refuses an AST one minor version old — pandoc-types has
shipped 1.20→1.23 at roughly one break per eighteen months, each refusing
rather than degrading, which disqualifies AST-as-archive. And under line merge
a JSON AST is *worse than markdown in kind*: git's matcher aligns the
scaffolding (`{`, `"_type": "block",`) and splits one logical insertion into
two conflict hunks inside a single block, so the obvious resolution yields one
author's key with the other's text.

**A CRDT as canonical storage.** Rejected, but the question dissolved rather
than resolving. Eg-walker's authors: "we invoke the CRDT only to perform merges
of concurrent operations, and we discard its state as soon as the merge is
complete. We never write the CRDT state to disk." The CRDT is merge machinery,
not storage. And convergence is not correctness — Ink & Switch, 2026-07: "any
invariant that spans more than one property or object is invisible to it,"
naming cached counts, trees and uniqueness, which are exactly a formula result,
a slide order and a z-order.

**jujutsu as the engine.** Rejected despite having the best ideas here.
`.gitattributes` unsupported since 2022; `jj-lib` self-describes as
experimental with on-disk format breaks promised before 1.0; and a conflicted
jj commit exported to git **writes side A into the real path with no markers**,
so a plain-git consumer reads an unresolved conflict as clean content — the
exact failure class this design exists to remove. Steal the `Merge<T>` algebra
and the `change-id` header; take neither the dependency nor the storage.

**A document server protocol as the contract.** Rejected on the design's own
premise: if correctness must hold under stock git with nothing installed, the
bytes on disk are the only thing every consumer shares, so a protocol cannot be
the contract. I carried this idea for several passes before it fell.

**A structured edit API for agents.** Rejected on a published negative result:
Aider benchmarked exactly this via function calling and found "Plain text edit
formats worked best," with function-call formats worst across all models.

**Per-file encryption for sharing.** Rejected on measurement: a one-line edit
to a 201-row CSV flips 99.5% of ciphertext bytes; two disjoint edits that merge
cleanly in plaintext conflict when encrypted; and git-crypt has a reported case
producing *no conflict markers at all* — silent data loss.

---

## 6. Recommended architecture

**Two primitives, not three.**

    TEXT         a sequence of characters
    ENTITY MAP   an ordered set of named entities, each a map of
                 attribute -> value, where a value may be TEXT

The brief's three primitives are configurations of the second: a document is an
entity map of blocks whose principal attribute is text; a table is one of rows;
a canvas one of shapes; a deck one of slides; an outline adds a parent
attribute; tasks add status. **The suite's applications stop being
architectural categories and become attribute vocabularies over one algebra.**

Text stays a separate leaf because rich text genuinely does not decompose into
entities — the OHCO literature settles this, and its own authors refuted the
thesis: "even OHCO-3, the weakest version... does not seem immune from
counterexample," with tracked changes and link anchors named as items 1 and 3.
The boundary between the two primitives is the paragraph.

**Correctness lives in the representation, not in an algorithm.** This is the
central architectural commitment and it is forced by §3(b): the merge algorithm
cannot be deployed, is NP-hard in general, is a heuristic in practice (GumTree's
move/update actions were judged inaccurate by experts in >55% of 2,400 cases),
and could not fix positional addressing at any price. So the core is a
discipline plus a small runtime, and structural merge sits *outside* the
correctness boundary as an optional local accelerator.

**The core, complete:**

    - four per-type functions: parse, render, resolve, refs
    - one nominal address grammar
    - a demand-driven, content-addressed derivation engine
    - a validator
    - an executable conformance suite that runs against a stock git binary

**Everything else is outside it** (§15).

---

## 7. Canonical data and storage model

**The canonical unit of storage is a file.** Type is the filename suffix; there
is no manifest, because a manifest is a second source of truth that can
disagree with the tree.

    myrepo/
      docs/q3-review.md
      data/budget.tbl
      diagrams/arch.canvas
      .notes/                  standoff annotations, keyed by artifact UUID
      .gitattributes
      .gitignore               ignores .cache/
      .cache/                  content-addressed derived values, never committed

### Identity: four questions everyone conflates

    which artifact is this?   a minted UUID in the file (frontmatter `id:`)
    which version?            the git blob SHA -- free, never user-facing
    which change?             a `change-id` commit header (jj's convention;
                              valid plain git, survives clone/push/gc,
                              stripped by rebase/cherry-pick)
    what is it called/where?  path and title -- MUTABLE METADATA, not identity

Paths cannot be identity: measured on a 2,000-document repo across two renames
with heavy rewrites, `git log --follow` recovered **3 of 51 commits (6%)** where
a UUID scan recovered all 51 and every path the file had occupied. Rename
detection is a 50%-similarity heuristic; the actual similarity was 20%.

Identity must be **minted, not derived** — three systems converged on this
independently (Perkeep's permanode is "really just a signed random number";
Unison injects a UUID into the content hash of `unique` types; Datomic's entity
ids are transactor-assigned). Content addressing cannot identify a *mutable*
thing, which is why IPNS had to exist.

### Sub-artifact identity: three problems, none wanting a minted id

    correspondence  which block in v2 is this one?   similarity matching   no
    reference       what do I write to point here?   a name the AUTHOR     only
                                                     chose                 where
                                                                           named
    anchoring       where is this comment about?     quote + prefix/suffix no

The OHCO argument seems to force stored ids for standoff comments. It rests on
a hidden premise — that a sidecar must point at an *identifier*. It can point
at a **quote**. Two-stage quote anchoring across 25 commits of real history on
three corpora: **92.9% correct, 7.1% loud refusal, 0.00% silent-wrong.** And
decisively: *a stored id under stock git survives only when the block's bytes
did not change, which is precisely the case an exact-quote match already
handles.*

    A minted sub-file id is the prose form of `col_a7f3`.
    It is a coordinate with the coordinates hidden. I2 forbids it.

Reproduced: two branches each adding a *different* block while minting the same
id merge clean with two identical ids and no marker — and it does not take two
people, since copy-paste alone produces it.

**A referrer never writes to the target.** Materialising an id because someone
read a block is a write caused by an act of reading. References point at names
the author already chose; unnamed blocks cannot be referenced until a human
names one, which is the correct incentive.

### Documents — `.md`

    ---
    id: 01J8ZQ4K7X
    title: Q3 Review
    ---

    # Findings {#findings}

    Procurement totalled {{ budget.tbl#grand }} against a plan of 500.00.
    Variances above five percent require written justification.

**The parser finds block boundaries and never re-emits content.** Each block
retains its raw bytes; render is concatenation. Round-trip is therefore exact
*by construction, for every input, including inputs the parser misunderstands*.
Measured on a 664-byte torture file (frontmatter, setext and ATX headings,
three bullet markers, both fence styles with blank lines inside, GFM table, raw
HTML, hard breaks, entities, emoji, CJK, no trailing newline): **18 blocks,
664 bytes in, 664 out, exact.** Pandoc changes 42 of 53 lines on comparable
input; `mdast-util-to-markdown`'s positional tracker "isn't used yet."

This is the most important structural result in the design: it converts
byte-stability from an unsolved *serializer* problem into a free *parser-scope*
decision.

A block is **content plus separator**; only content participates in identity.
Without that split, moving a block defeats its own identity on whitespace
alone. Generally: *in any text serialization, separators are a property of
position, not of the entity.*

**One sentence per line.** Adopted so `git blame` stops crediting whoever
reflowed a paragraph (measured: the rewrapper credited with 6 of 10 lines,
including two paragraphs he never touched). It turns out to be independently
required by agent edit-anchor survival (reproduced: reflowed prose loses every
line and the anchor; semantic line breaks change one line and the anchor
survives) and by standoff reanchoring. **One convention selected by three
unrelated requirements is the signal that it is real rather than taste.**

### Tables — `.tbl`

    | id     | item     | qty | unit  | total = qty * unit |
    | ------ | -------- | --: | ----: | -----------------: |
    | r_7f3a | widget   |  10 | 12.00 |                    |
    | r_2d15 | gadget   |  20 |  6.00 |                    |

    key   := id
    grand := sum(total)

- **One row per line**; the merge unit is the meaning unit.
- **Formula in the column header, cells blank.** The formula namespace is
  co-located on one line, so a collision is a line collision that git refuses
  (verified). This is Grist's column-formula model.
- **No coordinates in the grammar.** Verified consequence: the 480-vs-660
  silent-wrong merge becomes a clean **660** from stock git with no driver.
- **An opaque row id column.** An ablation of four identity functions across
  four scenarios found natural keys lose an edit on rename and overwrite a row
  on duplication, and content hashes split rows; only an opaque id survives all
  four, and *every failure was silent*. The asymmetry that makes it palatable:
  a human writes column **names** into formulas and never writes a row id into
  anything, so the id is machine-managed noise, not an address.
- **Long/tidy, not wide.** Measured: adding a category to a wide table
  conflicts across its entire contents while the long form merges automatically
  and correctly. In wide form the header is a shared mutable resource every
  addition must rewrite. Wide is a *view*, produced by derivation.
- **No `prev.` operator.** I proposed one for running totals; the adversary
  showed it is a coordinate that restores the 480-vs-660 defect wholesale and
  converts commutative aggregates into non-commutative ones. Removed. Row
  order cannot be both semantically load-bearing and irrelevant to merge.

### Canvases — `.canvas`

    node api  "API Gateway"   {kind: service}
    node db   "Postgres"      {kind: datastore}
    edge api -> db            "queries"

    @layout
    db { below: auth, align-left: auth }

Semantics declared; **positions derived**; a sparse override layer keyed by
name. The overrides are **relational, never absolute** — measured on diagram
quality, an absolute override introduced an edge crossing that did not exist,
and *a numeric offset from a named anchor was worse than plain absolute*
because it is absolute in disguise. Only the qualitative form held.

Scope, honestly: this covers structured diagrams. Freeform illustration has no
semantic layer to derive from and should be an opaque versioned blob.

**A correction I have to record here.** I originally claimed absolute
coordinates are the spatial form of A1 references. That is false, and the error
was mine: my test regenerated *every* coordinate from auto-layout when a node
was added, which no real canvas editor does. Re-run properly, a coordinate file
merges clean with both authors' moves correct — confirmed against a real
42-element Excalidraw file. A clean coordinate merge is never silently wrong,
because the value has no dependents. The genuine spatial A1 is **array-position
z-order**, and fractional indexing already solves it.

What survives, strengthened: **derived coordinates must never be committed.**

---

## 8. Git, versioning and collaboration

**Git is the distribution and durability format; the version control is ours.**
That split is empirical. Git is excellent as a content-addressed, concurrency-
safe, delta-compressing, cryptographically verifiable object store where `git
clone` is a complete backup — a trust asset no rewrite recovers. It is poor at
merge semantics, sub-file identity, and file-scoped history.

### The single-writer constraint was wrong

The prior pass concluded "the architecture must guarantee a single writer per
repository — every other decision is downstream of that one." I reproduced the
correction myself: 8 concurrent writers × 25 commits each, all appending to the
**same file** in a **bare** repo, using private `GIT_INDEX_FILE` +
`commit-tree` + `update-ref` compare-and-swap with retry —

    elapsed 3.43 s   commits 201   lines 201   entries 200   LOST WRITES: 0

The essential detail: on CAS failure a writer re-reads and re-applies its
**intent**, not a diff. `git push` rejection is the same CAS with the retry
replaced by `pull --rebase`, which replays a *diff* — which is exactly why the
prior pass measured 8/8 rebase conflicts.

**The constraint is one writer per WORKING TREE, not per repository.** Git's
three layers differ: the object store is safe and unlimited, the index is
one-writer-per-file, refs are one-writer-per-ref. Gerrit uses `ObjectInserter` +
`RefUpdate` CAS and no index at all.

### The server owns the merge

This is the largest structural consequence in the report, and it costs
something. Because a bare repository does not consult `.gitattributes`, a
forge's merge button can silently corrupt artifacts and **no declaration inside
the repository can prevent it.** So correct collaboration needs a component:
`git merge-tree --write-tree` yields the three conflict stages as blobs; the
server merges them and writes back with `hash-object` / `mktree` /
`commit-tree` / `update-ref`. A plain clone then receives a correct artifact
with no attributes and no config.

Priced honestly: the green Merge button on a forge is unsafe for these types,
and a hosted or self-hosted component is not optional for teams. It does not
compromise the single-user case, and `git clone` remains a complete backup.
The mitigating elegance is that this server's public interface **is git** — a
required component implemented entirely through an interface stable since 2005.

### Conflicts are data beside the artifact, never markers inside it

Verified with stock git: `*.csv -merge` in `.gitattributes` yields exit 1,
`UU`, a working-tree file that is **valid CSV with zero markers**, and base /
ours / theirs all retrievable from index stages 1/2/3. That is jujutsu's
first-class-conflicts property, available today, repo-portable, zero config.

The cost is real — `-merge` disables automatic merging for that path entirely —
so it is applied by **failure mode**, not by format:

    conflicted form fails LOUDLY in its own format (JSON, SVG, YAML, .fods)
        -> normal merge; the format polices itself
    conflicted form renders as PLAUSIBLE CONTENT (markdown, CSV)
        -> the tooling must police it, because the format will not

Markdown is the dangerous case and inverts the usual intuition. **Git's conflict
markers are valid markdown**: verified, pandoc renders a conflict as an `<h1>`
followed by seven nested blockquotes, because `=======` is a setext underline.
A conflicted JSON canvas throws a parse error — loud and unmissable. A
conflicted document simply *renders*. I also tested the standard mitigation and
it fails: `conflict-marker-size=32` still produces an `<h1>`, now with
thirty-two nested blockquotes.

### Real-time and asynchronous, reconciled by time horizon

    within a session (seconds, humans watching)  text CRDT over file bytes,
                                                 state discarded after merge
    across sessions  (days, nobody watching)     git three-way merge

**A git commit is eg-walker's "critical version"**, which is what lets the op
log be truncated — the thing a pure-CRDT system can never do, because someone
may reconnect after six months. This is the specific thing git-backing buys.

Do not put a CRDT under tables or canvases: convergence does not preserve
invariants spanning more than one property.

**Do not sell branching.** Ink & Switch built git-style dependent branches,
user-tested them, and deleted them — "it made the model more difficult for
users to understand and did not add meaningful value." Overleaf hard-codes
exactly one branch, named `main`. Penflip's founder wrote that non-developers
"don't understand branches, forks, commits, rebasing, cloning... and they don't
care to learn," then removed git from his homepage within a month.

---

## 9. Computation and dependency model

**One engine.** *Build Systems à la Carte* proves a spreadsheet and a build
system are the same object — a scheduler × rebuilder over a key/value store
with dynamically discovered dependencies, with Excel as its worked example. So
formulas, cross-document references, charts and exports are one mechanism, not
four. Keys are `(artifact, namepath)`; values are cells or whole files;
dependencies are **discovered by parsing**, never declared.

**Granularity is the whole design decision.** Measured: per-cell memoisation
costs **21.3× the arithmetic it protects** (200k cells: 10.9 ms compute against
232.9 ms bookkeeping). At artifact granularity, hashing is **2.3%** of the
parse it guards. Three orders of magnitude. This is why the paper rates Excel
its worst cell — a dirty bit is the only rebuilder you can afford per cell.
Move the unit up and content-addressing becomes free. **Granularity and
rebuilder are the same choice.**

So: a suspending scheduler with a constructive-trace rebuilder, at artifact
granularity. Verified behaviour:

    cold                        miss -> 480.00
    warm, unchanged             hit  -> 480.00
    edit an input               miss -> 540.00     (invalidated exactly)
    REVERT the edit             HIT  -> 480.00     (undo is free)
    break the dependency        ValueError: budget.tbl#grand -> #REF!(unit)

The revert case is the concrete payoff of content addressing over mtime, which
no timestamp-based system can match.

**A defect the adversary found in my own engine, now fixed.** The cache key
hashed one artifact's bytes, so a change to a *dependency* left the key
unchanged and returned a stale value on a hit:

    old single-artifact key  before=1dcb75c5dbf2  after=1dcb75c5dbf2  CHANGED=False
    closure key (fixed)      before=4340c86139c2  after=adafc27b7e77  CHANGED=True

"Invalidation is exact" was true only for single-artifact derivations. It was
also an I4 violation, since two machines at the same commit rendered different
numbers.

**Determinism is a security constraint and a correctness constraint at once.**
Two `now()` calls 50 ms apart returned an identical cached timestamp. The fix
is a taint on volatile keys, not cleverness — and the same rule that keeps the
cache honest is the rule that makes formulas safe (§13).

**Committed derived values are almost never acceptable.** Holding format and
edits fixed and changing *only* whether results live in the file flipped a
correct 660 into two failures: distant input edits gave a clean merge with every
derived value false and no marker, and concurrent aggregate updates gave a
conflict offering 580 and 560 when the truth was 660 — a two-way choice in
which neither option is correct. Hence the sharper rule in I4: *a derived value
may not be committed if its dependency set spans more than one mergeable
entity.*

**Order-independence is what produces loud failure.** Given the same class of
concurrent edit that git auto-merges clean: A1 gives 480 silently, plain Python
last-wins silently, and **marimo refuses to run and names both cells**. The
mechanism is a single-assignment namespace, not reactivity — order-independence
removes "later", so a collision has nowhere to hide.

---

## 10. Rendering and view architecture

Semantic content and presentation are separate artifacts, and presentation is
**derived**. Typst is the recommended engine — Apache-2.0, a real content model
with set/show rules separating content from styling, tagged PDF by default,
byte-reproducible output, and no derived state left in the repository. Its own
compiler docs state the architecture in its own words: "the elements of the
content tree are well structured and order-independent and thus much better
suited for further processing than the raw markup." It is pre-1.0; vendor
themes and pin the compiler.

Diagram layout is derived by delegation — D2 or Graphviz via Kroki — never
implemented here, and **never committed**: adding one node to a four-node graph
moved all four and changed 44 of 61 SVG lines.

Slides are an outline projection (Marpit as a library), with a *named,
structured* escape hatch rather than loose coordinates.

**Do not ship a constraint solver.** Apple walked Auto Layout back twice, and
SwiftUI's selling point was that "there are no underconstrained or
overconstrained systems." Subform died. The relational override vocabulary —
`near`, `below`, `align-left`, `same-rank` — is D2's `near` plus Graphviz's
`rank=same`, and needs no solver.

**Existing formats get clean/smudge filters, which are the cheapest large win
available.** Measured: draw.io as shipped is 6,495 bytes on zero newlines and
any two edits conflict into malformed XML; pretty-printed it still conflicts on
the `modified=`/`etag=`/`agent=` header; pretty-printed **plus** a filter
stripping that churn gives exit 0 and a 2-line diff. Same for `.pptx`, whose
`slide1.xml` ships as 22 KB on one line.

---

## 11. Extension architecture

Three tiers, in order of preference:

    Tier 1  DATA, not code -- a type is a grammar + named queries + a template
    Tier 2  a PROGRAM ON PATH (`gws-type-<suffix>`, NDJSON, the four functions)
            -- git's own `git-foo` mechanism: twenty years, no registry, no ABI
    Tier 3  in-process, first-party frontends only, explicitly unstable

Zed's own docs support tier 1 carrying the bulk: "only language server, context
server and debugger extensions require custom Rust."

**No UI API.** This is the one irreversible mistake available. Obsidian's
*document* API is thin — `Vault` is strings, `MetadataCache` is an index, no
AST — and survived a whole CodeMirror 6 rewrite; its `Modal`/`Setting`/DOM
surface is what welds it to Electron permanently. VS Code made the opposite
choice, which is why the same extensions run in a browser, over SSH, and in a
WebWorker.

No WASM yet: WASI 0.2.0 remains the cited stable release, and nothing in tiers
1–2 forecloses adding it. Adopt Neovim's API contract nearly verbatim — an
`opts` dict everywhere, additive-only fields, a private namespace convention,
machine-readable `since` and `deprecated_since` — plus pandoc's in-band version
stamp.

---

## 12. CLI, TUI, GUI, API and agent interaction

**The contract is the file formats plus a plumbing CLI. Not a protocol, not a
library API.** Since correctness must hold under stock git with nothing
installed, the bytes on disk are the only thing every consumer is guaranteed to
share; everything above them is convenience.

The four type functions are not an extension API — **they are the plumbing
layer**:

    parse   ~ git hash-object      resolve ~ git rev-parse
    render  ~ git cat-file         refs    ~ git for-each-ref

Git promises stability by *audience*, not by layer: plumbing interfaces "are
meant to be a lot more stable than Porcelain level commands, because these
commands are primarily for scripted use."

Budget: four plumbing commands plus `check`, `build`, `watch`, `doctor`; type
handlers as programs on PATH; an MCP wrapper of at most five tools. **If a
capability cannot be reached from `sh`, it does not exist.**

### Agents edit text

I was inclined toward `insert_row_after(id)` and `set_cell`, and there is a
published negative result against exactly that. The edit *format* dominates
everything:

    changing only the edit format       GPT-4 Turbo 20% -> 61%
    disabling fuzzy patch recovery      9x increase in editing errors
    no "high level diff" prompting      30-50% increase in editing errors
    SWE-agent without edit linting      18.0% -> 15.0% pass@1
    whole-file viewer vs 30-line window 12.7% (worse)
    gpt-5(high), 2026                   still 8.4% malformed edits

And "GPT is terrible at working with source code line numbers... backed up by
many quantitative benchmark experiments." OpenAI's V4A format omits them
deliberately.

The document-format version of this measurement had not been made. Same 8-row
table in four representations: lines usable as an edit anchor, **`.tbl` 100% vs
nested JSON 12.8%**; minimum unique anchor for one edit, **1 line vs 4–7 lines
with three ambiguous matches**.

So: **addressed reads, textual writes.** Exactly two structured operations,
`set <address> <value>` and `apply <patch>` with fuzzy repair. No
`insert_row_after`, no `move_block`, no typed canvas mutations — those are a
schema, and the schema is what ages badly.

A distinction the design was blurring: **line-orientation buys edit
locatability; nominal addressing buys merge correctness.** They are
independent, and an A1-formula CSV proves it — perfect locatability, still
merges to 480.

### Addressing

    query language     transient, may return empty  (JSONPath, XPath, jq,
                                                     tree-sitter)
    identity language  durable, must fail loudly    (our name paths)

    A query language may appear on a command line.
    Only an identity language may be written into a file.

Enforced mechanically: query output must be name paths, never offsets. The
cautionary tale is LSP's UTF-16 position encoding — "a legacy of VSCode's
JavaScript implementation," raised January 2018, and the 3.17 fix could only
*add* an alternative, so UTF-16 is mandatory for every language server forever.
**A position encoding, once shipped, cannot be removed.** That is the strongest
argument for having no coordinates in the grammar at all.

---

## 13. Security and trust boundaries

**The organising principle, taken from git itself:**

    A REPOSITORY MAY DECLARE. A REPOSITORY MAY NEVER BIND.

Cloned bytes select behaviour from a set the local user already installed; they
can never introduce behaviour. This reframes the design's biggest apparent
risk: the split between declaring a capability in `.gitattributes` and binding
it in `.git/config` is **not a git defect, it is git's security boundary**. If
a checked-in file could bind a command, cloning would be arbitrary code
execution.

**The one place to beat git rather than copy it: make absence loud.** Git's
security property and its fail-open UX defect are the same mechanism. Keep the
property, fix the silence. Prototyped in ~30 lines — `doctor` reads the
declarations, resolves each against local config, and refuses rather than
degrading, and detects the bare-repo case where declarations are inert:

    REFUSING: 2 declared capability(ies) are not available.
      - *.tbl declares merge=gws-table, but merge.gws-table.driver is unset.
        git would SILENTLY fall back.

This composes with I6: because the *formats* are correct under stock git, a
loud refusal is an inconvenience rather than a blocker. Had correctness
depended on the driver, refusing would be the only safe behaviour and the
system would be unusable without installation.

**Executable content: make harm unrepresentable rather than sandboxing it.**
The formula language is total, terminating, deterministic and I/O-free, with no
flag that changes it — so `WEBSERVICE`, `IMPORTXML` and `INDIRECT`-over-a-path
are *unparseable*, not blocked. Escaping is unavailable by construction here,
since a leading `=` is the feature. Take CEL's guarantees but not CEL, which is
IEEE-754 doubles only and the flagship artifact is a financial table: named-
column syntax, IronCalc as the engine, evaluation constrained to CEL's
contract, decimal arithmetic, a static cost estimate plus a runtime budget.

Why not sandbox a real language: Grist, the closest shipping analogue,
sandboxes Python with gVisor requiring specific CPU flags — a server's answer,
not a desktop one. And sandboxes fail: wasmtime shipped two Critical escapes
two days apart in April 2026. WASM therefore belongs at the plugin/install-
consent boundary, never in the path that opens a stranger's spreadsheet.

**Agents.** This substrate does not get *exposed* to the lethal trifecta; it
instantiates all three legs as product features — repo access is private data,
a cloned repo is untrusted content by definition, and an agent that can push
has external communication. Only egress can be broken, and it must be enforced
outside the model: no automatic fetch of any repo-sourced URL ever (PDF/A's
"external content references are forbidden," arrived at independently); the
action set fixed before untrusted bytes are read; and **an agent may never
write anything governing its own permissions** — CVE-2025-53773 was exactly
that, repo content injecting Copilot into writing `"chat.tools.autoApprove":
true` about itself.

**Never auto-executed from a clone, at any trust level:** hooks; any code
delivered as repo bytes; any git config derived from repo content
(`core.fsmonitor`, `core.sshCommand`, `core.hooksPath`, `credential.helper`,
`diff.external`, `filter.*.clean/smudge`, `merge.*.driver`, `alias.*` with
`!`); any network fetch triggered by repo content. Trust-on-first-use keyed
locally by remote URL plus root-commit OID, never in the repo. Untrusted mode
must be **fully functional** — that is the payoff of making harm
unrepresentable, and what keeps a rare prompt meaningful rather than trained
away.

The risk class is live: CVE-2025-48384 (CVSS 8.0) is on CISA's Known Exploited
Vulnerabilities catalogue — a trailing carriage return asymmetry between git's
config writer and reader becomes RCE on clone. CVE-2024-32002 shows the danger
of resting on one predicate: one path check, four bypasses in three years.

**Erasure: scope it, do not disclaim it.** The substrate guarantees erasure for
content *declared erasable* and nothing for ordinary committed text. Mechanism:
git holds an identifier and a hash, bytes live in a mutable content-addressed
store, erasure is deleting an object — CNIL's commitment-on-ledger /
data-off-ledger pattern. Two further obligations: commit author name and email
are themselves personal data and cannot be retrofitted, so **pseudonymous
authorship is the default**; and a supported history horizon must be stated.
Note forges make this worse — data remains reachable from deleted forks and
repositories, and GitHub's position is that it "designed repositories to work
like this."

---

## 14. Format evolution and compatibility

**Editions, not a version field in every file.** A version field is tempting
and wrong: bumping it touches every file, which is a direct I1 violation.

Rust's model, and the transferable insight is an implementation detail rather
than a policy: **edition is a property of the source location, not of the
compilation.** rustc marks spans with the edition of the crate they came from,
which is exactly the capability Python lacked. The rule Rust states and never
breaks — "crates in one edition **must** seamlessly interoperate with those
compiled with other editions."

The two counter-examples are precise. Node built a dual-dialect system *without*
that guarantee and produced the dual package hazard — nine years, still
incomplete, `instanceof` failing across loaders. Python had no coexistence at
all — one interpreter, one language version, so migration was all-or-nothing
across an entire dependency tree: eleven years of dual maintenance, a
sixteen-year long tail, and `six` was the community hand-building a per-file
edition system on a runtime that refused to provide one.

Concretely:

    - edition declared ONCE per repository, not per file
    - artifacts of different editions coexist in one repository and one build
    - migration tooling rewrites to the INTERSECTION -- valid under both old
      and new -- so migration is incremental, never atomic
    - escape hatches are DATED. Go publishes a minimum lifetime for its
      compatibility settings (two years, four releases); Rust makes no
      time-bounded promise, and Go's is the better practice.
    - past a certain size of change, a new NAME is more honest than a version
      bump. Mattijsen on Raku, MacFarlane on djot, and Hickey generally
      converged on this independently.

**Error handling is specified, not chosen.** XHTML chose strictness and lost;
HTML4 chose unspecified permissiveness and produced a decade of quirks; HTML5
chose **specified permissiveness** — every input has exactly one defined
outcome, and a parse error is *detected and reported* separately from being
*handled*, so a browser and a validator run the same algorithm.

The counter-example cost twenty-three years: RFC 2616 left Transfer-Encoding
versus Content-Length ambiguous, RFC 7230 said such a message "ought to be
handled as an error" — which is not a conformance requirement — and only RFC
9112 mandated rejection. The gap was the HTTP request smuggling class.

    An ambiguity that is harmless for one implementation becomes a
    vulnerability the moment two implementations of the same spec meet in one
    data path.

This resolves the strict-parsing versus must-ignore tension. The line:

    degrading could yield a plausible VALUE      -> REJECT
    degrading could only lose DECORATION         -> PRESERVE and WARN

I7 is not "reject everything unknown." It is *never let an unknown thing
contribute to a computed result.*

**Graceful degradation** uses DITA's class-ancestry idea — ordered
general→specific class lists, so a processor that has never heard of a
specialised type reads the ancestry and knows what it IS-A. Cheapest structural
idea available, and it degrades in band with no registry.

---

## 15. What stays outside the core

Deliberately not implemented, each with the reason:

| Excluded | Why |
|---|---|
| A formula engine | Wrap IronCalc (Apache-2.0). ~7% of spreadsheets have any formula; 76% of real usage is 15 functions |
| A layout engine | Delegate to ELK/dagre/Graphviz/D2 |
| A typesetting engine | Wrap Typst |
| A structural merge algorithm | Undeployable, NP-hard, heuristic (GumTree judged wrong >55%), and cannot fix positional addressing |
| A CRDT for anything but live text | Convergence does not preserve cross-property invariants |
| A constraint solver | Auto Layout walked back twice; Subform died |
| A freeform canvas format | No semantic layer exists to derive from; version it as a blob |
| A universal document model | This is OpenDoc |
| A UI API | The one irreversible coupling |
| A protocol as the contract | The bytes are the contract |
| Per-file ACLs | No forge has them; sharing a subset means separate repos |
| Per-file encryption | Encrypted files do not merge; one case produced no markers at all |
| Forms, calendar protocols, presence | iTIP/iMIP are protocols, not files; forms need an auth server |
| Branching UX for non-developers | A measured negative result |

---

## 16. Major risks and likely failure modes

**1. I3 is aimed at the wrong failure. (Highest severity.)** It catches
references that *break*. The dangerous case is a reference that still
*resolves*, to something else. Measured: one header line renaming `total`→
`gross` and `net`→`total`, with `grand := sum(total)` untouched — clean merge,
`504.00` where the truth is `604.80`, **no `#REF!`**. A second form: delete a
column, keep the aggregate name; nothing breaks, the name resolves, the meaning
moved. No mechanism in the design currently detects this. The likely direction
is binding a reference to a *fingerprint* of what it named and warning when the
fingerprint changes, but that is unbuilt and unproven.

**2. Every format I wrote contained the defect it was designed to eliminate.**
Seven silent-wrong merges, none exotic, found by one adversary in one pass. The
`.tbl` aggregate block is a scattered namespace — the very defect I had
diagnosed in markdown and used `.tbl` as the contrast for. This is the central
risk to the whole thesis: the discipline is genuinely hard to follow even for
someone who has just finished writing it down. Mitigation is mechanical
enforcement, which is the deliverable.

**3. The forge-merge hole.** A bare repo ignores `.gitattributes`, so a merge
button can corrupt artifacts and nothing in the repository can stop it. This
costs the frictionless "just use GitHub" story and makes a server component
non-optional for teams.

**4. Markdown's residual I6 violation, which I cannot close.** Duplicate link
labels, footnote labels, heading anchors and frontmatter keys are all scattered
namespaces; conflict markers render as valid markdown; and `cp doc.md copy.md`
duplicates the artifact UUID with no mechanism at all. Client-side checks
cannot be relied on, because hooks are not cloned. This is a real, unfixable-by-
us hole for prose, and it is the strongest argument for a stricter syntax.

**5. Semantic conflicts are unfixable by any representation.** Two writers
changing different sentences produce a clean merge saying 14 days in one line
and 30 in another. Universal, not git-specific — Google Docs does the same —
but it means "correct merges" cannot be a headline claim. Note the tension:
semantic line breaks improve blame and anchoring while making this failure
slightly easier to reach.

**6. The 0.00% silent-wrong anchoring figure is one pass over three corpora**
and is load-bearing. It needs independent replication.

**7. Distribution, which killed everyone else.** Kova: best-in-class
engineering, 67 releases in 3.7 months, a full packaging estate, **$0.00
raised**. HN enthusiasm declining across a decade: Penflip 181 points → Moment
29 → Perchpad 2. ODF was ISO-standardised, vendor-backed and legally mandated,
and lost anyway when Massachusetts changed "must" to "may". Being right about
the format is not sufficient and has never been.

**8. Sourcing.** Two research tracks exhausted their search budgets and flagged
~35 unverified items between them, including a widely-repeated Guido quotation
about Python sandboxing, Rust edition adoption percentages, and several CVE
details. None are load-bearing above; none should be cited from those documents.

---

## 17. The smallest coherent implementation

**Not an application. A specification plus its executable conformance suite,
plus a reference implementation small enough to be credible.**

Ranked by evidence, the artifacts a format spec must ship with:

    1. AN EXECUTABLE CONFORMANCE SUITE, versioned independently of the spec
    2. FULLY SPECIFIED ERROR RECOVERY -- one outcome per input, errors
       signalled separately from handled
    3. A REFERENCE IMPLEMENTATION, as a suite companion, never as the
       definition (CommonMark's founding grievance was Markdown.pl)
    4. A VALIDATOR (meaningless until 2 exists)
    5. A PROSE SPEC, whose distinctive job is stating what is DELIBERATELY
       LEFT OPEN
    6. A FORMAL GRAMMAR for lexical structure only
    7. A CORPUS of real files -- for discovering what the suite is missing

The evidence that (1) is the active ingredient is nearly a controlled
experiment: CommonMark and djot share an author, djot is the better design, and
CommonMark ships 655 executable examples and has ~45 implementations while djot
ships no suite and has six after four years.

**But fix CommonMark's central defect.** Its own spec concedes "not every
feature of the HTML samples is mandated by the spec," so two implementations at
100% conformance can build different trees. *Testing input→output constrains
one projection of the model, not the model.* The suite must assert on parsed
entity maps, resolved addresses and **evaluated values**.

The existing prototype suite already does the valuable half, and its failure
proves the point. Mutation-tested by sabotaging the parser to silently drop
every third row:

    baseline                      TOTAL FAILURES: 1
    with parse sabotaged          TOTAL FAILURES: 3
      !! two distant row inserts: SILENTLY WRONG -- evaluated 420.0, expected 660.0
      !! disjoint cell edits:     SILENTLY WRONG -- evaluated 240.0, expected 516.0

The semantic assertions caught it. The round-trip assertion did not, because
`parse` and `render` are identity functions — a tautology, exactly as the
adversary charged. Both facts belong in the record, and a project whose primary
artifact is its own credibility cannot ship a tautological test.

**Milestone 0 — the thing that proves the architecture:**

1. `.tbl` specified: grammar, error recovery, edition, and what is left open.
2. A conformance suite asserting on **evaluated values after a stock-git
   merge**, covering at minimum: the 480-vs-660 case, duplicate row ids,
   duplicate aggregate names, NFC/NFD collisions, field-count mismatch,
   delimiter-in-cell, numeric coercion, order independence, confluence across
   merge orders, cross-artifact cache invalidation, and `merge-tree` in a bare
   repo — every one of which is a case an adversary actually broke.
3. A mutation gate: the suite must fail when the reference implementation is
   deliberately sabotaged. Without this, a suite measures nothing.
4. A reference implementation in one file.
5. `doctor`, for loud absence.

Calibration for how much testing is enough: SQLite is 155.8 KSLOC of library
against **590× as much test code**, and its promise to support the file format
through 2050 is credible only because that ratio exists.

Current prototype state: all five legs run in **282 lines** of Python across
`experiments/`. That is not production code, but the mechanisms are small
because the hard parts are wrapped rather than written.

---

## 18. Questions that need experimentation, not more reasoning

1. **Can meaning-drift be detected?** Risk 1 is the deepest open problem. Does
   binding a reference to a fingerprint of what it named catch the rename-swap
   and column-deletion cases without generating intolerable false positives?
   Nothing in the literature addresses this.
2. **Does the audit generalise?** Mechanically enumerate every namespace in
   every format and check co-location or parse-time validation. The adversary
   found seven; the honest question is whether that is the tail or the head.
3. **Is column-formula authoring usable by non-developers?** The naming
   evidence is genuinely split, and it tracks *visibility of the binding*:
   range names made novices slower and more error-prone, while Calculation View
   (n=22) measured 37.14% faster authoring and 40.7% faster debugging (p<10⁻³),
   with low-expertise users gaining most. Column headers are visible, which is
   the proposed mechanism — but it is unreplicated for this design.
4. **Replicate the 92.9% / 7.1% / 0.00% anchoring result** on independent
   corpora. The zero is load-bearing.
5. **Run the agent ablation nobody has run:** same model, one arm editing
   `.tbl` as text, one calling a `set_cell` API. The published evidence is from
   code, not documents.
6. **Does anyone actually want this?** The one measurable proxy: do people
   review diffs of tabular data when given the chance? dbt's adoption suggests
   yes for engineers; nothing establishes it beyond them.

---

## Appendix — my own errors, and why they are in the report

Seven corrections, all found by measurement rather than reasoning:

1. Content-hash block identity silently duplicated a paragraph where git
   correctly conflicted.
2. My renderer violated the round-trip law within an hour of my writing it
   down, dropping a markdown alignment row.
3. "Absolute coordinates are the spatial form of A1 references" — false; my
   test regenerated every coordinate, which no real editor does.
4. Path-based artifact identity — 6% history recovery.
5. My derivation cache never invalidated across artifacts.
6. My type-aware merger was *less* correct than stock git on duplicate ids.
7. My `.tbl` aggregate block was a scattered namespace — the exact defect I had
   diagnosed elsewhere and held `.tbl` up as the contrast for.

The pattern matters more than any individual item. Every one was found by a
test or an adversary; none by careful thought, and several occurred *after* I
had written down the principle they violated. That is the argument for the
conformance suite being the deliverable, and it is the reason to trust this
report's direction more than its assurances.

---

## 19. Post-publication corrections

This section exists because the format-evolution track reported after §14 was
written, and it corrects two things already stated above.

### C1. I7 as originally stated was measurably too strict

I wrote the line as *"reject when degrading could yield a plausible VALUE;
preserve-and-warn when it could only lose DECORATION."* Two problems.

**It is not decidable by a reader.** Not knowing what a construct means is the
premise; a reader cannot classify an unknown construct as structural or
decorative.

**And annotations are not inherently safe.** A `%unit-scale 1000` comment
yields `240.00` against a truth of `240000.00` — and the W3C TAG's 2008
*Preserve existing information* rule reaches for the identical USD/EUR example.
Independent rediscovery of the same hazard means it is structural, not
incidental.

**The measured cost of the strict reading**, over 12 inputs a v1 reader meets
across decades:

    policy          CORRECT   SILENT-WRONG   SAFE-REJECT   REFUSE
    permissive            4              8             0        0
    strict-all (I7)       1              0             5        6
    hybrid                2              1             5        4
    demand-driven         3              1             5        3

I7 as literally written has zero silent-wrongs — and **refuses six files that
had a correct answer, one of which differed only by a comment.** That is the
ecosystem fork, quantified. Zero silent-wrongs is not worth a format nobody can
extend.

**The resolution is that half the tension was a category error.** RFC 9413:
*"The ability to extend a protocol is sometimes mistaken for an application of
the robustness principle... relying on implementations to consistently handle
unexpected input is not a good strategy for extensibility."* Two distinct
questions had been conflated:

    Q1  RECOGNITION     is this input in the language?     strict lives here
    Q2  INTERPRETATION  what does a well-formed but
                        unknown construct mean?            must-ignore lives here

The 960 failure — my evaluator summing both sides of a conflict — was a **Q1
framing failure misdiagnosed as Q2 policy.** The parser did not tolerantly
ignore an extension; it failed to *frame* `<<<<<<<` as structure at all.
**Framing is unconditionally must-understand, and that is fully compatible with
unlimited extensibility.**

**The correct variable is the derivation closure, declared lexically by the
writer** — PNG's chunk case bits are the model: uppercase critical, lowercase
ancillary, with a separate safe-to-copy bit. Legible from the bytes, no
registry, and the writer decides.

So the operative rules become:

    P1  total recognition (verified by residue tests)
    P2  framing is never ignorable
    P3  exactly ONE ignorable channel, present in v1
    P4  THE INERTNESS PROMISE -- nothing in the ignorable channel may ever
        feed a derived value. Tested by stripping every annotation and
        asserting no computed value changes.
    P5  poison the VALUE, not the file
    P6  a reader that poisoned anything may not write
    P7  preserve what you ignore

P4 is the load-bearing one, and it is mechanically testable, which is the only
kind of guarantee this project has learned to trust.

### C2. The independent-implementation hypothesis is false in both directions

§14 leaned on plural implementations as the survival test. The record refutes
it both ways: **XHTML 2.0 and RSS had plural implementations and died; TeX and
SQLite have essentially one each and survived.**

RFC 2026 explains what plural implementations actually are — an *instrument*:
a feature two implementations cannot interoperate on is **deleted from the
spec**. They measure whether prose is precise. TeX and SQLite substituted a
better instrument: a precise oracle (TRIP/TRAP, and a 590:1 test-to-code
ratio).

    Sharpened: a format survives when its meaning is decidable from a durable
    artifact that is NOT a running program. A conformance suite is a valid
    substitute for plural implementations.

Which is the same conclusion §17 reaches, now resting on a correct premise.

Adoption by whoever controls distribution is a **separate and equally
necessary** condition. RTF had the best extension mechanism in the survey and
died by vendor decision. And the Massachusetts ODF mandate is worse than
usually told: ETRM v4.0 gives ODF and OOXML the *identical* wording — "may be
used" — so the only surviving obligation was to leave *binary*, which OOXML
satisfies by design. **The escape hatch was the alternative's design goal.**

### C3. Versioning, concretely

No per-file version field. One repository-level file, `.format`, containing
`edition 2026`.

    R-a  a READER never consults it. Interpretation is a function of the
         artifact's bytes alone.
    R-b  unknown annotation -> ignore and preserve; otherwise poison or reject
    R-c  there is no "unknown version" case, because "written by something
         newer" is handled per-construct, at feature granularity
    W-a  a writer emits only what the edition permits
    W-b  bumping the edition is a one-line commit that rewrites nothing

Measured, and the reason a per-file field is rejected: a version line at line 1
**conflicts with any concurrent edit to line 1** — which in a `.tbl` is the
header row — and the merge result is an invalid file, violating I5. Two things
that ran against my own argument and did not reproduce: blame survives a pure
insertion, and merges across a bump do not conflict.

### C4. Text encoding must be enforced by the parser, not by .gitattributes

NFC-only identifiers; `Cf` format characters rejected; UTF-8, LF, no BOM.
Measured: NFD renormalisation made a one-word edit produce a **4-line diff**,
and made two edits to *different paragraphs* conflict with both sides
pixel-identical. That is a simultaneous hit on I1, I2 and I3, and
`.gitattributes` cannot prevent it because a bare repo never reads it.

### C5. The size argument against plain text does not survive git

§5 dismissed the prosecution's 145,584-vs-28,457-byte comparison as "noise."
That was right but under-argued; here it is measured. A 288,607-byte markdown
document:

    raw markdown                        288,607 bytes
    git loose object                     49,617
    git packed                           31,942
    the .docx comparison point           28,457

A dead heat, on a document twice the size of the one the comparison used. And
across history it reverses completely:

    git pack, 21 revisions                36,562 bytes
    21 independent .docx copies          597,597 bytes      16x

Since `.docx` is itself a ZIP, its revisions delta badly in git — the prior
pass measured 21 revisions of a 2 MB compressed asset at 20.6x a single copy.
**The size objection is an artifact of comparing uncompressed text to a
compressed archive, and it inverts as soon as you store more than one version.**

### C6. Markdown's conflict rendering is worse than §8 states

§8 reports that a conflicted document renders as an `<h1>` containing the
marker. Against a *real* git conflict the marker is **consumed**: `=======`
acts as a setext underline, so the `<<<<<<<` line disappears and the ours-side
content is silently promoted to a heading. Four engines, three different
documents, all exit 0. The failure is not that the conflict looks odd — it is
that the conflict becomes invisible.

---

## 20. Second round: what a dedicated adversary found in the fixed design

A second adversary attacked the three mechanisms added after round one. It
broke all three. The ideas survive; the implementations did not, and neither did
my verification of them.

### The mechanism I called "closing the deepest hole" was silently wrong

`order := by(date)` sorted by a **string concatenation**, not a tuple. The key
was `(0, float(x), id)` or, when `float()` failed — which every real date does —
`(1, 0.0, str(order) + str(id))`. Two consequences, both verified by me:

    a hand-typed 2026-2-1 sorts after 2026-03-01
    low := min(balance), an overdraft check, reads 55.0 where the truth is 5.0
    -- through a clean merge, exit 0, zero markers

And because the tiebreak was concatenated, **row ids decided the order of rows
whose keys differ** (`Anna` before `Ann`), which falsifies §7's own justification
that an opaque id is "never an address."

Worse, `key :=` was optional, so ties fell back to physical file position — and
two transactions on one day is the *normal* ledger case, not an edge case. My
verified claim that "shuffling every row gives identical results" held only on
my fixture: numeric, distinct, no ties.

Fixed and verified: a real typed tuple, `key` mandatory under `order`, a single
declared type per ordering column (mixed types refused), computed order columns
refused, non-finite values refused.

### The round-trip test was still vacuous after I "fixed" it

I reported killing the tautology by making `render` reconstruct from the parsed
structure. It does not: `structure()` stores raw lines and `render()`
concatenates them, so the entity map is never consulted. Verified —

    a parser whose entire structure is {'raw': text} passes 5 of 5 round-trip cases

The real fix is to pair round-trip with a **mutation through the structure**:
set a cell via the structure, render, re-parse, assert the change. A raw-bytes
structure has no cells to set and fails 3 of 3. That is now in the suite.

### The CI workflow I proposed as the portable enforcement point did not run

It validated zero artifacts and its mutation step crashed with
`FileNotFoundError`. I wrote enforcement machinery and never executed it. Fixed;
all three steps now run from a clean checkout.

### The mutation gate measured the mutants, not the suite

"15 mutants, 15 killed" was self-authored on both sides. An adversary supplied
17 more; **14 of them survived.** They cluster exactly where the new mechanisms
live: the tiebreak (no case in the suite had a tie, so the whole confluence
claim was unexercised), `prior` and `delta` (which appeared in no case at all),
numeric coercion, blank-cell handling, and dependency order between computed
columns — which turned out to be **header position**, a coordinate hiding inside
the computation model.

All 14 are now addressed: 11 by new cases and implementation fixes, 3 correctly
classified as **equivalent mutants** — mutations no input can separate from the
original, because an earlier fix made the line unreachable. A gate cannot make
that distinction by itself, which is a limitation worth stating rather than
papering over. Current state: 30 mutants, 27 killed, 3 equivalent, 0 surviving.

### Meaning drift is not sound in its current framing

Six false positives, all ordinary work: a whitespace change, an operand
reorder, redundant parentheses, and — decisively — **a VAT rate changed from 1.2
to 1.25**. Identity is formula *text*, so any edit rebinds the column and every
downstream aggregate fires. A detector that fires on whitespace gets muted, and
a muted detector catches nothing.

And it is quiet on its own target class in two cases, including
`order := by(day)` → `by(seq)`, because the definition extractor explicitly
excludes `key` and `order`. **The two new mechanisms do not compose.**

Text equality is neither necessary nor sufficient for meaning. This needs a
different framing — most likely comparing the *evaluated column vector under a
fixed input*, so a rate change is visible as an intended edit while a rebinding
is visible as a discontinuity. That is unbuilt. **Risk 1 is reopened.**

### What held under deliberate attack

Confluence over six merge orders with `min()` and negative amounts: one
outcome, attacked hard. Physical shuffling genuinely irrelevant for distinct
numeric keys. `order := none` genuinely makes row-relative operators a parse
error. Column-name co-location holds. Conflict-marker rejection unbroken. The
rename fixpoint terminates and could not be made to mis-converge. Round one's
scattered-aggregate defect is genuinely fixed.

### The meta-finding, which is the most important result of the session

> Both "11 namespaces, 0 unprotected" and "15 mutants, 15 killed" are artifacts
> of the enumerator being the implementer.

That is now the third instance of the same failure mode, and it generalises past
this project: **a verification artifact authored by the implementer measures the
implementer's imagination.** The conformance suite is the right deliverable and
it cannot be written by whoever writes the reference implementation. An
adversarial suite author is a standing role, not a review step.

---

## 21. The verdict, revised

The architecture is unchanged. The claim made for it is not.

**Demand for correct merging is absent, and measurably so.** Not one instance
was found of a practitioner reporting a silently wrong number from a merged CSV
— the exact failure this design removes. The decisive datum is not the absence
of complaints, which a silent failure explains, but the absence of *attempts*:
3,672 repositories declare `*.xlsx binary` and 2,776 push it into LFS against
**28** trying `diff=xlsx`, a give-up-to-hack ratio near 230:1. GitHub built the
productised version, Flat Data, and archived it. Over $65M produced no
standalone survivor; DoltHub became healthy by abandoning data collaboration.
PCAOB AS 2201 contains no occurrence of "spreadsheet" or "version control."

**Demand for a validator is present and hand-rolled.** The four reference-data
registries surveyed had each independently built a CI check, a bespoke
`db:validate`, and a CONTRIBUTING file warning contributors in bold to *"make
sure that the number of columns in the file has not changed"* — a field-count
check, one of the eleven refusals in the spec, written by hand by people who had
never seen it.

**And the methodology is the only part with no prior art.** The format ideas all
have ancestors that must be credited — ClassSheets (ASE 2005), Object
Spreadsheets (Onward! 2016), Lotus Improv, and above all **Coopy/daff**, which
has shipped row-ID-aware git-integrated CSV merging for thirteen years. What
nobody does is *check out two branches, run stock git merge, evaluate the merged
file, and assert on the computed number*. jujutsu asserts on trees, Pijul is
purely algebraic, and nbdime — the strongest remaining candidate — has no
execution machinery in its test suite at all, which I verified directly.

Three independent lines, one conclusion:

    The format is not the contribution. The merge is not the product.
    The conformance methodology and the validator are both.

Coopy sharpens it: its author chose content-based row matching and treated IDs
as optional. A mandatory opaque id is a real departure — but one that only pays
off if something enforces it, and daff delivered the mechanism thirteen years
ago as a merge driver, which this report measures to be undeployable. **The
mechanism was never the missing piece. The enforcement was.**

### Interop bounds the migration story precisely

Measured on 5,458 real workbooks and 778,418 formula cells: **~7% of real
formulas translate mechanically, with a ceiling near 11%.** Adding filtered
aggregates and cross-table lookups — which are nominal, merge correctly, and are
not forbidden by the design as an earlier pass wrongly concluded — moved the
deduplicated rate from 5.3% to 6.9%, a 30% relative gain and a small absolute
one. The misses are structural: 63.6% of the SUMIF gap is multi-predicate
`SUMIFS`, 31.5% of INDEX usage is composite keys, and **fewer than half of real
lookup targets are unique at all** (key-ness 41.3%).

So the honest sentence is: *bring your data; formulas are rewritten by a human,
and the tool tells you cell by cell which ones need you.* Export is the strong
direction — `.tbl` → `.xlsx` with real Excel structured references and
`SUBTOTAL` aggregates is essentially lossless and verified recalculating in
LibreOffice.

One datum worth carrying: **5.4% of formula cells in the sampled corpus contain
a literal `#REF!`** — already broken in Excel, saved and redistributed anyway.

### What this means for building it

Build it as infrastructure, not a product. Lead with the validator, not with
480-vs-660. Expect adoption to be slow and to come from teams already
hand-rolling the check. And before writing production code, put the spec and
the suite in front of one of the four named registries and find out whether they
would replace their own script with it.

The one caveat that cuts the other way: the demand research got HTTP 403 from
Reddit on every attempt and exhausted its search budget, so the largest hole
sits over the population most likely to have the pain.

---

## 22. The merge server, built and stressed

### The core claim holds

A plain `git clone` — no `.gitattributes`, no merge configuration, nothing of
ours on `PATH` — receives a correctly merged artifact where stock `merge-tree`
would have written conflict markers. Alice edits a row's `qty`, Bob edits the
same row's `unit`, same line:

    | r_0002 | gadget   |  25 |  6.50 |
    both edits present, two-parent merge commit, refs/gws/* not fetched

### But the proposed mechanism was insufficient, and that is the headline

**`git merge-tree` reports only the paths where stock git FAILED.** Where stock
git merges *cleanly and wrongly* — an unescaped pipe, a duplicate row id, a
duplicate aggregate name, a file that already contains conflict markers — there
are no conflict stages at all, the type-aware merger never runs, and the server
publishes git's wrong answer. It committed a file containing conflict markers
and advanced the ref.

§8's mechanism as written — "merge the three stages" — is not sufficient. The
correct rule is:

    MERGE, AND THEN VALIDATE EVERY CHANGED PATH IN THE RESULTING TREE.

This is the validator becoming load-bearing for the third independent reason:
the parser needs it for nine of eleven namespaces, CI needs it because nothing
else travels, and now the server needs it because the merge machinery cannot
see its own clean-but-wrong outcomes. Three subsystems, one artifact.

Two further silent corruptions were found and fixed in the implementation: a
delete/modify pair resolved as a delete, discarding the other side's edit where
stock git correctly conflicts — the exact I6 violation, reintroduced by dead
code — and a fast-forward path that bypassed validation entirely. **A
fast-forward is a publish, and must be validated like one.**

After fixes: no silently-wrong cases, and no security failures across 17
malicious inputs. The honest cost of that safety: six of eleven red-team cases
now *refuse*, four of them cases where a forge would merge cleanly.

### Forge deployment is better than §8 assumed

§8 claims a self-hosted component is not optional for teams. That is too
pessimistic. **A github.com deployment works today**, without self-hosting: a
GitHub App creating two-parent merge commits through the Git Database API, plus
an organisation **ruleset** — not classic branch protection, where admins can
always push — naming the App as the sole bypass actor. The PR shows as merged
via GitHub's documented "indirect merges" behaviour, which is the same mechanism
bors has relied on for years.

Unusable for this: required status checks (they gate clickability, not the
merge), the merge queue (no substitution hook), and pre-receive hooks (GitHub
Enterprise Server only, GitLab self-managed only, absent on Bitbucket Cloud).

Residual hole, stated plainly: an indirect merge bypasses that PR's protections,
so anyone able to edit the ruleset can add themselves and land a stock merge.
Self-hosting now buys exactly one additional thing — rejecting a **direct push**
of an already-corrupt artifact, which no cloud forge permits.

### Operational findings

- Bare-repo CAS holds to 64 concurrent writers with zero loss, degrades at 128,
  and produces 19–27% loud failures at 192–256. A ~15-line serialising queue
  gives **1.00 attempts at every level, zero loss at 256, and 3.4× throughput.**
  Ship the queue.
- `git merge-tree` **SIGABRTs** on a malformed tree (`merge-ort.c:3772`), and
  git's default `receive.fsckObjects=false` accepts the poison. Enabling it is
  mandatory configuration for any self-hosted deployment.
- A one-cell merge rewrote **84 lines** until the renderer was made
  width-preserving — the padding defect of §11, arriving from a third direction.
- Crash safety is clean: killing the process after each of six git verbs left
  `fsck` at rc=0 with no torn writes and no duplicate commits, because
  `update-ref` is the only mutating step and is atomic by construction.

### The cost, honestly split

708 lines, 499 executable, standard library only, thirteen git verbs. The split
is the interesting part:

    ~235 lines   git plumbing        -- the "interface stable since 2005" claim survives
    ~265 lines   per FORMAT          -- merger, validation, refusal logic

**Correctness is per-format, and it is the larger half.** The plumbing is the
easy part and always was.

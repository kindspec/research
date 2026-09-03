# Pass 1 — architectural hypothesis (pre-evidence)

Written before D1–D12 reported, deliberately, so the evidence can falsify a
concrete position rather than fill a vacuum. Everything here is a claim to be
attacked.

## H1. Do not unify the content models. Unify everything else.

The seductive move is one universal typed tree that documents, tables and
canvases are all serializations of. That is OpenDoc, and it is the thing to
avoid. The three primitives have genuinely different algebra:

- sequential  = a total order of blocks; edits are insert/delete/reorder
- structured  = a set of named tuples + a dependency graph; edits are schema
                and value changes
- spatial     = a set of named entities with property maps; edits are property
                assignment

No common tree makes those three cheaper. What IS common is everything around
them: identity, addressing, references, derivation, history, merge, view.

**Hypothesis: the core owns the cross-cutting concerns and knows nothing about
markdown, tables or canvases. Content models are replaceable modules.**

## H2. The prime invariant is diff locality

    LOCALITY: a semantic edit of bounded size must produce a byte diff of
              bounded size.

Everything the prior research found is a corollary. Pithy's
marked->Tiptap->turndown save path violates locality, so first touch of any
imported file is a whole-file diff. Pandoc changed 42 of 53 lines. This is not
a bug in those tools; it is the absence of a stated law.

Corollary law for implementations:

    render(parse(b)) == b            for canonical b       (round-trip)
    canon(canon(x)) == canon(x)                            (idempotence)

Both are property-testable. A substrate that states and tests these is doing
work no incumbent does.

## H3. The second invariant is positional independence

    POSITIONAL INDEPENDENCE: no artifact may reference content by a coordinate
                             that a concurrent edit can change.

This unifies findings that looked unrelated:
- A1 cell refs   -> the measured 480-vs-660 silent-wrong merge
- line numbers   -> every "see line 40" comment rots
- array indices  -> JSON list merges
- absolute canvas coords, when something else refers to them

Note the careful scope: a shape's own x/y is a VALUE, not a reference. Values
merge last-writer-wins per property (Figma's model). Only references must be
nominal.

## H4. The third invariant is loud failure

    LOUD FAILURE: a broken reference must fail visibly and locally. It must
                  never resolve to zero, empty, stale, or plausible.

The 480-vs-660 result is the canonical violation: correct-looking output, no
marker anywhere. Silent-wrong is the enemy; conflict is fine.

## H5. The fourth invariant is no hidden state

Everything that affects a rendered result is in the files. Corollary: derived
values are not authoritative and by default are not committed.

## H6. Type is the filename suffix; there is no manifest

Unix and .gitattributes already do this. A manifest is a second source of truth
that can disagree with the tree. Remove it.

## H7. The per-type contract is the whole extension surface

    parse   : bytes -> Tree | Error
    render  : Tree  -> bytes                (render . parse = id on canonical)
    resolve : Tree, NamePath -> Node        (the address space)
    refs    : Tree -> [Reference]           (deps DISCOVERED, not declared)
    diff    : Tree, Tree -> [Change]
    merge   : base, ours, theirs -> bytes | Conflict

Six functions. If a new artifact kind implements them it gets history,
addressing, transclusion, derivation and merge for free. This is Irmin's
mergeable-types idea plus LSP's replaceable-implementation idea.

## H8. One address grammar, and it is nominal

    artifact#name           budget.tbl#total
    artifact#name.name      budget.tbl#q3.revenue
    artifact#name           diagram.canvas#gateway

Every kind resolves a NAME PATH. There are no coordinates in the grammar at
all. Positional independence is enforced by the grammar rather than by
discipline.

## H9. Identity is on-demand

Paths identify artifacts. Sub-artifact IDs are materialised into the file ONLY
when something references them. You do not pay the readability cost of UUIDs
until you use identity. Unreferenced prose stays clean.

## H10. Formulas, charts, exports and indexes are ONE mechanism

Build Systems a la Carte (Mokhov/Mitchell/Peyton Jones) already proves a
spreadsheet and a build system are the same object: scheduler x rebuilder over
a key/value store with dynamically discovered dependencies. Excel is their
worked example.

So: one demand-driven derivation engine, keys are (artifact, namepath), values
are cells OR whole files. A computed column and a chart.svg are the same kind
of thing. Results live in a gitignored content-addressed cache; committing a
derived artifact is a repo policy expressed in .gitignore, not a core concept.

## H11. Column formulas, not cell formulas

One formula per column stored in the header; cells blank. Minimal diff,
nominal addressing, still readable. Row-relative needs an explicit operator
(prev./next.) rather than an offset. Grist is the prior art.

## H12. Spatial = semantic layer + sparse named override layer

USD's composition model. Auto-layout derives positions; human nudges are a
sparse map keyed by NAME. Overrides merge cleanly because they are nominal.
The semantic/layout split already works in Graphviz/D2/Structurizr; the
override layer is what those lack and what makes it acceptable to humans.

## The smallest thing that proves it

Not an app. A test suite. Take the four invariants and make them executable
against one real repo:
1. one-word edit to an imported document changes one line
2. the 480-vs-660 merge produces 660, or a conflict, never 480
3. a deleted column makes dependents fail loudly, not silently
4. round-trip and idempotence property tests pass on a corpus

## Known weak points to attack

- H1 may be a cop-out: if the core knows nothing about content, does it do
  enough work to justify existing?
- H7's merge function may be undeployable: git merge drivers require LOCAL
  config and forges may ignore .gitattributes entirely. If so, H7 is fiction.
- H10 may collapse: cross-artifact recompute needs a graph that spans files;
  discovering it requires parsing everything, which is a global cost.
- H12 is untested by anyone at document scale.
- The whole thing may be strictly worse than composing existing tools.

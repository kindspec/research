# L4 — the spatial leg: derived layout + sparse named overrides (my own work)

`experiments/L4-spatial/`. Tests H12 — that spatial artifacts should store
SEMANTICS plus a sparse override layer keyed by NAME, with layout DERIVED,
rather than storing absolute coordinates the way Excalidraw, draw.io and SVG do.

## The experiment

Same diagram, same two concurrent edits, two representations.

    Alice: adds a node (which changes the DERIVED position of everything)
    Bob:   hand-nudges one existing node

### A) semantic + sparse named overrides

    node api  "API Gateway"
    node auth "Auth Service"
    node db   "Postgres"
    edge api -> auth
    edge auth -> db

    @layout
    db { at: 400, 500 }

    stock git merge-file  ->  exit=0, CLEAN

Derived layout after merge: `cache` placed by auto-layout at (260,200);
`db` keeps Bob's manual nudge at (400,500). Both intentions survive, and
nothing had to understand the file.

### B) full coordinates (what real canvas formats store)

    { "elements": [ {"id":"api","x":100,"y":80}, ... ] }

    stock git merge-file  ->  exit=1, 2 conflict markers
    json.decoder.JSONDecodeError: Expecting property name ... line 18

Conflicted, **and the merged file is no longer valid JSON** — so no tool that
reads the format can even open it to help resolve. This is the third
independent appearance of the same failure (L1 case 5: conflicted table;
L2: conflicted CSV-shaped data; here: conflicted canvas).

## Why A wins, stated precisely

Adding a node changes the position of unrelated nodes. In representation B that
is a WRITE to every element, so any concurrent edit collides. In representation
A it is not a write at all — positions are not in the file.

**Absolute coordinates are the spatial form of A1 cell references.** The 480-
vs-660 result and this conflict are the same defect: state that must be
rewritten when unrelated content changes. Name-keyed overrides are the spatial
form of named columns.

## The honest boundary

This works for STRUCTURED diagrams — flows, org charts, architecture, ERDs,
mind maps — where a semantic layer genuinely exists and auto-layout is
acceptable. It does NOT work for freeform illustration, a whiteboard sketch, or
pixel-precise design, where position IS the content and there is no semantic
layer to derive from.

So the substrate should carry structured diagrams natively and treat freeform
canvas as an opaque blob it versions but does not merge. Pretending otherwise
would be the mistake every "diagrams as code" tool makes in the other
direction — insisting auto-layout is always enough, which is why users
complain about not being able to nudge a box. The override layer is exactly
what makes auto-layout tolerable.

---

# CORRECTION — L4's headline claim was wrong, and the error was mine

A red-team pass on real files (real `.excalidraw`, `.drawio`, `.canvas`,
`.tldr`, `.pptx`, downloaded and edited) failed to reproduce case B, and
identified the reason. I verified it against my own code and it is correct.

## The methodological error

My representation B regenerated EVERY coordinate from auto-layout whenever a
node was added. No freeform canvas editor does that — a user moves one shape
and only that shape's coordinates change. So I compared "semantics + overrides"
against "coordinates PLUS an auto-layout that rewrites the whole file", which
is a strawman.

Re-run without the relayout, two authors each moving a different shape
(`experiments/L4-spatial/C_*.json`):

    coordinate merge WITHOUT relayout : exit=0, CLEAN, valid JSON,
                                        both moves landed correctly
    my original case B WITH relayout  : exit=1, conflict, unparseable

Corroborated on a real 42-element Excalidraw file: moving one shape changes 10
lines of 1,695; two authors moving different shapes merge clean **even when
the elements are adjacent in the file**, because `serializeAsJSON` ends with
`JSON.stringify(data, null, 2)` — one field per line.

## What is refuted

**"Absolute coordinates are the spatial form of A1 references" is FALSE.**
The failure classes are different in the way that matters most here:

    A1 reference   merges clean and yields a WRONG NUMBER, silently
    coordinate     merges clean and the shape is simply where it was put

A clean coordinate merge is never silently wrong. It cannot be — the value has
no dependents. That was the whole basis for calling it an A1 analogue, and it
does not hold.

## What actually is the spatial A1

**Array-position z-order.** JSON Canvas 1.0: "Nodes are placed in the array in
ascending order by z-index." Position in a list is exactly the coupled state
Pass 3 describes, and concurrent insertion silently reorders. Fractional
indexing already solves it in this domain — tldraw stores `index: "a2V"`,
Excalidraw added the same field, Figma's nodes carry `parentIndex.position`.

This also revises PASS2, which argued fractional indices were unnecessary
machinery because line order is document order. That holds for documents and
tables. It does not hold for z-order, which is the one case PASS2 flagged and
then under-weighted.

## What survives, and is strengthened

**Derived coordinates must never be committed.** Graphviz 2.42.4, adding one
node to a four-node graph, moved **4 of 4** pre-existing nodes and mirrored the
layout; the rendered SVG changed **44 of 61 lines**. That is the real coupled
state, and it is in the DERIVED artifact, not the source.

## What is newly discovered, and it is worse than the thing I got right

**The override layer merges cleanly and then becomes silently WRONG.** L4
checked that an override survives a merge. It never checked whether the
override is still CORRECT afterwards. Measured on diagram quality (total edge
length, crossings) when Bob pins a node and Alice adds one:

    override form                        before        after
    none                                 4.70, 0       5.90, 0 crossings
    absolute `at: 400,500` (L4's form)   5.32, 0       6.20, 1 crossing
    numeric delta from a named anchor    5.32, 0       8.27, 1 crossing
    qualitative `aligned-under auth`     4.94, 0       5.94, 0 crossings

Clean merge, worse diagram, no marker. And **a numeric offset from a named
anchor is worse than plain absolute** — it is absolute in disguise, which is a
warning about "nominal-looking" designs that still carry a magnitude.

**So the `.canvas` format's `@layout db { at: 400, 500 }` is wrong and must
become relational:** `near`, `below`, `align-left`, `same-rank` — D2's `near`
plus Graphviz's `rank=same`, with no solver. Nobody has fixed the stale
override: USD's own FAQ says an orphaned `over` "will be ignored... It is the
responsibility of the user... to ensure that shot.usda is updated", and
Structurizr logs "There is no layout information for the element named..." and
drops it. FreeCAD's 1.0 policy is the one to copy — error loudly, auto-repair
only on high confidence, "First, do no harm."

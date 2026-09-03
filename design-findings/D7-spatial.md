# D7 — the spatial / visual leg

Research + experiment, 2026-08-28. Environment: **git 2.47.3**, Debian 13,
Python 3.13.5, Graphviz 2.42.4, git-lfs present, PIL 11.1.0.
Experiments in `experiments/D7-canvas-formats/`, `D7-semantic-layout/`,
`D7-usd/`, `D7-slides/`, `D7-images/`.

This file was written to **falsify** `L4-spatial-results.md`, which concluded
that spatial artifacts must store semantics plus a sparse name-keyed override
layer, because "absolute coordinates are the spatial form of A1 cell
references". Real files were downloaded, real edits applied, real three-way
merges run.

**Headline: L4's experiment does not reproduce against real files. Its
conclusion is half right for the wrong reason, and the half that is right is
right for a different reason than L4 gave.**

---

## 0. The one-paragraph answer

Absolute coordinates are **not** the spatial A1. The A1 defect is *silent
semantic corruption on clean merge*; coordinates do not have it — a clean
coordinate merge gives exactly both authors' moves. What actually decides
whether spatial data survives git is three **serialization** properties, none
of which is about coordinates: (1) one value per line, (2) no per-save churning
metadata, (3) no rewriting of state the author did not touch. Real
`.excalidraw`, real `.tldr`, real `.canvas` and pretty-printed `.drawio` and
OOXML all merge cleanly under stock git once those hold. The semantic/override
split earns its place for a **different** reason: derived layout is globally
unstable, so an *absolute* override goes stale and silently degrades the
picture. The override layer must therefore be **relational**, not numeric — and
that is where L4 was closest to right without saying it.

---

## 1. Attacking L4 directly: what real canvas files actually do

L4's case B was a hand-written compact JSON in which Alice's edit rewrote the
coordinates of *every* element. Two things are wrong with that as a model of
"what Excalidraw/draw.io/SVG actually store".

1. **No freeform canvas re-runs layout on insert.** Adding a shape in
   Excalidraw or tldraw does not move any other shape. L4 gave representation B
   a write amplification that the real tools do not have.
2. **Real Excalidraw is not minified.** `serializeAsJSON` ends
   `return JSON.stringify(data, null, 2);`
   ([`packages/excalidraw/data/json.ts`](https://raw.githubusercontent.com/excalidraw/excalidraw/master/packages/excalidraw/data/json.ts)),
   i.e. one field per line, ~40 lines per element.

### The measurement

Real files, downloaded, not synthesised:

| file | source |
|---|---|
| `real2.excalidraw` (42 elements, 1695 lines, 41,887 B) | `slimtoolkit/slim` `assets/images/docs/SlimHow.excalidraw` |
| `real1.excalidraw` (37 elements) | `WhatsApp/erlang-language-platform` `docs/ELP-parser-dataflow.excalidraw` |
| `real.drawio` (21 `mxCell`, 6,495 B) | `agntcy/docs` `docs/assets/service_compositon.drawio` |
| `real.canvas` (20 nodes / 25 edges, 51 lines) | `miaomiaomiao1113/Claude-code-architecture-instruction` |
| `real.tldr` (48 records / 23 shapes, 1330 lines) | `dalenguyen/pdfun` `docs/architectures/pdf-chat.tldr` |
| `real.pptx` (1 slide, 13 shapes, 11 layouts) | `microsoft/BCTech` `samples/MachineLearning/images/architecture.pptx` |

Python's `json.dumps(obj, indent=2)` reproduces both `.excalidraw` files
**byte-for-byte**, so the edit simulation is faithful. Excalidraw's own
`mutateElement` was read to get the mutation exactly right: on a move it sets
`version+1`, `versionNonce = randomInteger()`, `updated = now` — and, crucially,
`if (!didChange) { return element; }`, so **untouched elements are not
touched at all**.

### Result — moving ONE shape

| format | serialization | total lines | changed lines |
|---|---|---|---|
| JSON Canvas `.canvas` | one node per line | 51 | **2** |
| SVG (one shape per line) | one element per line | 202 | **2** |
| USDA sparse override layer | line-oriented | 26 | **2** |
| pptx `slide1.xml`, pretty-printed | one element per line | 1071 | **2** |
| tldraw `.tldr` | tab-indented, ~40 lines/record | 1330 | **4** (x, y) |
| Excalidraw `.excalidraw` | 2-space, ~40 lines/element | 1695 | **10** (x, y, version, versionNonce, updated) |
| draw.io pretty + clean filter | one element per line | 89 | **2** |
| draw.io pretty, unfiltered | one element per line | 89 | **4** (2 are `modified=`/`etag=`) |
| draw.io **as shipped** | **single line, 0 newlines** | 1 | **whole file** |
| pptx `slide1.xml` **as shipped** | **single line, 22 KB** | 1 | **whole file** |
| `.pptx` **as shipped** | zip | binary | **whole 166 KB blob** |
| Excalidraw minified | single line | 1 | **whole file** |
| Excalidraw + auto-relayout on insert | 2-space | 1695 | **446 (26%)** |
| SVG rendered from derived layout (add 1 node to 4) | | 61 | **44 of 61 (72%)** |

### Result — real three-way merges (`git merge-file`, stock git, no drivers)

| scenario | format | exit | valid after? |
|---|---|---|---|
| Alice moves shape A, Bob moves shape B (far apart) | real `.excalidraw` | **0** | valid JSON, **both moves present** |
| Alice moves shape A, Bob moves the **adjacent** element | real `.excalidraw` | **0** | valid, both present |
| Alice adds a shape, Bob moves a shape | real `.excalidraw` | **0** | valid, 43 elements, both present |
| Alice and Bob move the **same** shape | real `.excalidraw` | 1 | conflict, invalid JSON |
| Alice **adds + relayouts**, Bob moves a shape | real `.excalidraw` | **2** | 2 conflicts, invalid JSON |
| same two moves, **minified** | `.excalidraw` | 1 | conflict |
| two different shapes | draw.io **as shipped** | 1 | malformed XML |
| two different shapes | draw.io pretty (header churn intact) | 1 | conflict **on the `modified=`/`etag=` line**, not the geometry |
| two different shapes | draw.io pretty + clean filter | **0** | both moves present |
| two nodes on distant lines | JSON Canvas | **0** | valid |
| two nodes on **adjacent lines** | JSON Canvas | **1** | conflict |
| two shapes, incl. adjacent records | tldraw | **0** | valid |
| two shapes **+ realistic session state** | tldraw | **1** | conflict |
| two shapes | pptx XML as shipped (one line) | 1 | conflict |
| two shapes | pptx XML pretty-printed | **0** | clean |
| two different prims | USDA override layer | **0** | clean |
| same prim | USDA override layer | 1 | conflict (correct) |

Merged results were verified semantically, not just by exit code: in the
Excalidraw clean merges exactly the two intended elements moved, to exactly the
intended coordinates, and element count was correct.

### What this actually shows

**L4's conclusion does not survive.** Full-coordinate representations of real
canvases merge cleanly under stock git for every edit pair except
edits-to-the-same-shape, which is a genuine semantic conflict no
representation can dissolve. The failures are caused by three orthogonal
serialization defects:

- **F1 — not line-oriented.** draw.io writes the whole diagram on one line;
  OOXML writes each part on one line; minified JSON is one line. Any two edits
  collide. This is the single biggest factor and it is purely cosmetic — pretty
  print draw.io and its merges go clean.
- **F2 — per-save churning metadata in a hot line.** draw.io's `<mxfile>` root
  carries `modified=`, `etag=`, and an `agent=` string containing the author's
  **browser user-agent**; every save rewrites them and every concurrent edit
  conflicts there. tldraw is worse: it persists `camera` (pan/zoom), `pointer`
  (last mouse position + `lastActivityTimestamp`), `instance.screenBounds`
  (**the author's browser window size**) and `instance_page_state.selectedShapeIds`
  (the current selection) as ordinary records in the file. With those included,
  two unrelated shape moves conflict; with them excluded, they merge.
  Excalidraw is the counterexample that proves this is a *choice*: `appState.ts`
  marks `scrollX`, `scrollY` and `zoom` as `export: false`, and a real exported
  file's entire `appState` is `{"gridSize": null, "viewBackgroundColor": "#ffffff"}`.
- **F3 — writing state the author did not touch.** This is L4's real finding,
  and it is caused by *persisted auto-layout*, not by coordinates. Adding one
  shape to the 42-element Excalidraw file with a relayout changes 446 lines and
  produces two conflicts and unparseable JSON; without relayout it changes 26
  lines and merges clean.

**F3 is where L4 was right, but it identified the wrong culprit.** The
dangerous thing is not storing coordinates; it is storing *derived* coordinates.

---

## 2. Derived layout is globally unstable — the real argument for the split

Measured with Graphviz 2.42.4 (`experiments/D7-semantic-layout/`). A 4-node
graph, one node added:

```
base:   api(1.05,2.25) auth(0.44,1.25) db(1.05,0.25) queue(1.68,1.25)
+cache: api(1.15,2.25) auth(1.78,1.25) db(0.60,0.25) queue(0.54,1.25) cache(1.78,0.25)
```

**4 of 4 pre-existing nodes moved, and the layout mirrored left-to-right**
(`auth` 0.44 → 1.78; `db` 1.05 → 0.60). Rendering the two graphs to SVG changes
**44 of 61 lines**.

This is a property of the algorithm, not of this example. Graphviz's own tracker
documents that layout is declaration-order dependent
([gitlab #2552](https://gitlab.com/graphviz/graphviz/-/issues/2552)) and that
a two-line reordering intended to remove 2 crossings produced a different layout
with **49 crossings instead of the expected 25**
([#1625](https://gitlab.com/graphviz/graphviz/-/issues/1625)). PlantUML is worse:
[plantuml #1244](https://github.com/plantuml/plantuml/issues/1244) shows the
*same unchanged input* rendering 3 different images across 100 runs. Penrose is
stochastic by construction — its own maintainers filed
[#1490](https://github.com/penrose/penrose/issues/1490) asking to "bake" a
diagram so it can be reproduced, and
[#1645](https://github.com/penrose/penrose/issues/1645) reports that adding one
unrelated circle changes an existing circle's radius "despite using identical
Style code and random seeds".

**Consequence: derived coordinates must never be committed.** A committed
derived layout turns every semantic edit into a whole-file rewrite (F3), which
is exactly the 446-line / 72%-of-file result above. That is the durable half of
L4.

---

## 3. Where the semantic/layout split breaks: the stale override

L4 showed the override *merges* cleanly. It did not test whether the override is
still *correct* after the merge. It is not.

Same harness, same graph. Bob nudges `db` one unit right of where auto-layout
put it. Then Alice adds `cache`, which mirrors the layout. Quality of the
resulting picture (total edge length, edge crossings):

| override form | before Alice's edit | after Alice's edit |
|---|---|---|
| none | 4.70, 0 crossings | **5.90, 0 crossings** |
| **absolute** `db { at: x,y }` (L4's form) | 5.32, 0 | **6.20, 1 crossing** |
| **numeric delta** `db = auth + (1.61,-1.00)` | 5.32, 0 | **8.27, 1 crossing** |
| **qualitative** `db: aligned-under auth` | 4.94, 0 | **5.94, 0 crossings** |

The absolute override is now 1.46 units from where layout wants `db` — further
than the width of the whole graph — and it **introduces an edge crossing that
did not exist**. The merge was clean; the diagram silently got worse. That is
the same shape of defect as the 480-vs-660 spreadsheet result, arriving through
a different door.

Note the second row: a **numeric offset from a named anchor is not a fix** — it
is absolute positioning in disguise and it scored worst of all. Only the
qualitative/relational form survives a relayout intact.

This failure mode is confirmed by every system that has shipped the pattern:

- **USD** — the most sophisticated non-destructive override system in
  existence — states it plainly in its own FAQ
  ([openusd.org/release/usdfaq.html](https://openusd.org/release/usdfaq.html)):
  > "what happens if a user independently working on `sequence.usda` moves
  > `Book_1` to `Desk`, or if `Book_1` is renamed to `Video_1`? In such a case,
  > the 'over' in `shot.usda` would be **'orphaned' and be ignored** when
  > composing and evaluating `/World/Sets/Desk/Book_1` in `shot.usda`. **It is
  > the responsibility of the user working on `sequence.usda` to ensure that
  > `shot.usda` is updated to avoid this problem.**"

  There is no automatic repair. Pixar's answer to the stale override is "a human
  must notice".

- **Structurizr** — the closest shipped prior art to L4's design: one semantic
  model, N views, element x/y stored in a *separate* JSON layer and merged on
  every push by a pluggable strategy. Its docs say
  ([docs.structurizr.com/ui/diagrams/manual-layout](https://docs.structurizr.com/ui/diagrams/manual-layout)):
  > "diagram layout information isn't something that you will ever author by
  > hand… element x,y positions are not stored in the source of your workspace"

  `DefaultLayoutMergeStrategy.java` matches elements by **canonical name →
  (name+class) → (description+class) → (id+class)** and, when nothing matches,
  logs `"There is no layout information for the element named …"` and drops that
  element's layout. Documented failure: *"If you rename an element and change
  the creation order… you may find that the element can't be matched"*, and
  *"Entire diagrams losing their layout information is generally caused by
  changing the key associated with that view."*

- **FreeCAD / parametric CAD** — the topological-naming problem is the same bug
  at industrial scale: derived names of faces and edges shift when the model
  changes and downstream features break.

- **Auto Layout** — Apple's own guide admits the failure is not even stable
  across builds: *"the effect of breaking constraints can vary greatly from
  layout to layout, or even from build to build."*

So: **the override layer is a known pattern that works, and every system that
ships it also ships the same unfixed hole.** Structurizr, USD and Graphviz all
degrade the same way — silently, gracefully, and wrongly. No tool surveyed has
*removed* an override layer it had shipped; the negative evidence is
"never shipped it" (Mermaid, D2 core) rather than "shipped it and regretted it".

---

## 4. Prior art the design should copy from

### 4.1 Penrose — the cleanest three-way split ever built

"Penrose: From Mathematical Notation to Beautiful Diagrams", Ye, Ni, Krieger,
Ma'ayan, Wise, Aldrich, Sunshine, Crane, *ACM TOG* 39(4) Art. 144, SIGGRAPH 2020.
[PDF](https://penrose.cs.cmu.edu/media/Penrose_SIGGRAPH2020a.pdf).
MIT licence, 7,973★, last commit 2026-08-04, latest tag v3.3.0 (2025-09-28),
`@penrose/core` ~6k npm downloads/month — **alive, small, academic**.

Three files: **Domain** (schema), **Substance** (instance data), **Style**
(visual encoding + layout constraints). The paper's own rationale:

> "A secondary decision is to split specification of mathematical content and
> visualization across two domain-specific languages: Substance and Style. A good
> analogy is the relationship between HTML, which specifies content, and CSS,
> which describes how it is rendered."

and, decisively for this design:

> "A conscious design decision… is to **exclude all graphical data (coordinates,
> sizes, colors, etc.) from Substance** — since its sole purpose is to specify
> abstract relationships rather than quantitative data. All such data is instead
> specified in Style or determined via optimization."

Layout is `ensure` (hard constraint) / `encourage` (soft objective) solved by
L-BFGS with random restarts. **Limits, from the paper and its successors:**
optimization is "the biggest bottleneck"; initial values are "sampled uniformly
at random", so output is non-deterministic (see §2). Bluefish (UIST 2024,
[arXiv:2307.00146](https://arxiv.org/pdf/2307.00146v4), by a former Penrose team
member) benchmarks it: *"Compared to Penrose on Insertion Sort, Bluefish scales
linearly while Penrose scales superlinearly"*, and argues global solvers
*"limit extensibility: common domain-specific algorithms for domains like trees
and graphs rely on custom imperative code that cannot be easily translated to or
integrated with a global solver's constraint language."*

Penrose's answer to nudging is **Bloom** (2024): a drag becomes a new constraint
and the optimizer re-solves live. Not a stored override — a *live* constraint.
That is the right shape.

### 4.2 USD — layering instead of merging

Composition is the LIVERPS strength ordering (the acronym now has an extra arc):

> "LIVERPS is an acronym for Local, Inherits, VariantSets, **Relocates**,
> References, Payload, Specializes, and is the fundamental rubric for
> understanding how opinions and namespace compose in USD."
> — [openusd.org glossary](https://openusd.org/release/glossary.html)

`over` is exactly the sparse override primitive:

> "Over is short for 'override' or 'compose over', and its purpose is just to
> provide a **speculative, neutral prim container for overriding opinions**… if
> all the PrimSpecs contributing to a prim have the over specifier, then the prim
> will not be visited… **When an application exports sparse overrides into a
> layer that sits on top of an existing composition, it is common to see deep
> nesting of overs.**"

The pipeline pattern is literally the L4 scenario, and USD's answer is *file
partitioning*: each department owns a layer; `shot.usd` sublayers
`shotFX.usd, shotAnimationBake.usd, sequence.usd`; nobody edits anyone else's
file.

**Tested (`experiments/D7-usd/`).** Built `model.usda` (semantic), `layout.usda`
(sparse `over` translate opinions), `stage.usda` (subLayers). Then:

| scenario | result |
|---|---|
| Alice adds a node in `model.usda`, Bob nudges a node in `layout.usda` | `git merge` **exit 0**, no textual merge occurred at all — disjoint file sets |
| Bob nudges one prim | **2-line diff** |
| two authors nudge different prims in the same `layout.usda` | **clean** (exit 0) |
| two authors nudge the same prim | conflict (correct) |
| two authors both *insert* new overs at the same position | conflict |

**The honest reading: USD's layering is not a better merge algorithm, it is
single-writer-per-file discipline with a composition engine behind it.** That is
the same constraint RESEARCH.md §4 already established for the whole substrate
("a single writer per repository"), applied at file granularity. The composition
machinery buys you *strength-ordered resolution across layers*; it does not buy
you concurrent editing of one layer.

**And it costs enormously.** USD is a multi-hundred-thousand-line C++ system with
TBB and a Python binding; it ships `usdview` with a dedicated composition
inspector, `usddiff`, `usdstitch`, `usddumpcrate`, `sdfdump` and `sdffilter`
*because* answering "why is my opinion not winning?" is hard. Studios largely
ship binary `.usdc` crate files (openusd.org's own performance guidance: *"Use
binary '.usd' files for geometry and shading caches"*), which are not diffable at
all — `.usda` text survives mainly for small hand-authored override layers,
which is precisely the role proposed here.

**Verdict on USD for this substrate: steal the idea, not the system.** The idea
is three lines long — *a weak semantic layer, a strong override layer, resolved
by a fixed strength order, with orphaned overrides ignored rather than
erroring*. Everything else in USD is 3D pipeline scale that a diagram does not
need.

### 4.3 Structurizr — the shipped version of L4

Covered in §3. Worth adding that the Mermaid community independently converged
on it: on [mermaid #2483](https://github.com/mermaid-js/mermaid/issues/2483) a
commenter writes *"I very much like the way structurizr solved it. They support
an (optional) additional file to save the coordinates."* Mermaid has had open
requests for manual placement since 2021 ([#2457](https://github.com/mermaid-js/mermaid/issues/2457),
[#2483](https://github.com/mermaid-js/mermaid/issues/2483)) and has shipped
nothing; the closest maintainer statement is *"We are very interested in adding
such a solution. That might have to be a different type of diagram though."*

### 4.4 D2 — and the licence trap

D2 core is **MPL-2.0** (`d2lang/d2` LICENSE.txt, verified). Its `near` keyword
is the relational override:

> "positioning is controlled entirely by the layout engine. It's one of the
> primary benefits of text-to-diagram that you don't have to manually define all
> the positions of objects… there are occasions where you want to have some
> control over positions." — [d2lang.com/tour/positions](https://d2lang.com/tour/positions/)

**But the useful half is paywalled.** From the same docs: *"`near` can be set to
constants for all layout engines, but only TALA can use it to set to objects"*,
and *"On the TALA layout engine specifically, users can directly set the `top`
and `left` values for objects."* TALA's own README:
> "TALA is closed-source… this is a paid layout engine, which requires a license
> for any commercial use… TALA is free to evaluate, but without a license, will
> render with a watermark."

So in open-source D2 you get `near: top-center` (8 page-relative constants) and
nothing else. Requests for a general escape hatch —
[#1845](https://github.com/d2lang/d2/issues/1845) (absolute position) and
[#1548](https://github.com/d2lang/d2/issues/1548) (`shape: manual`) — are open
and unimplemented. **Terrastruct's own commercial judgement is that
relational-to-object placement is the valuable part.** That corroborates §3's
measurement from the opposite direction.

Graphviz's override is `pos="x,y!"` + `neato -n` / `-n2`
([graphviz.org/docs/attrs/pos](https://graphviz.org/docs/attrs/pos/),
[command.html](https://graphviz.org/doc/info/command.html): *"If set, neato
assumes nodes have already been positioned and all nodes have a `pos`
attribute"*). It works only under `neato`/`fdp`, never under `dot`, and the
`-n` path still has open bugs ([#2845](https://gitlab.com/graphviz/graphviz/-/issues/2845)).

Kroki (MIT) fronts all of them — Graphviz, Mermaid, PlantUML, D2, Structurizr,
Excalidraw — behind one HTTP API, and is the cheap way to render without
vendoring engines.

---

## 5. Constraint layout: does anyone tolerate expressing position as constraints?

The historical record is unkind, and it is the strongest reason to keep the
override vocabulary *small*.

- **Cassowary** (Badros, Borning, Stuckey, ACM TOCHI 2001,
  [PDF](https://constraints.cs.washington.edu/solvers/cassowary-tochi.pdf)) was
  built for exactly this vocabulary: the paper names *"'inside,' 'above,'
  'below,' 'left-of,' 'right-of,' and 'overlaps.'"*
- **Apple Auto Layout** shipped it to millions and it is remembered for
  unsatisfiable-constraint console spam and ambiguous layouts. Apple's own guide:
  *"Auto Layout identifies the set of conflicting constraints. It breaks one of
  the conflicting constraints and checks the layout… the effect of breaking
  constraints can vary greatly from layout to layout, or even from build to
  build."*
- **Apple then walked it back twice** — UIStackView (2015), then SwiftUI (2019),
  which abandoned the solver for a parent-proposes/child-chooses algebra. WWDC
  2019 session 237, verbatim: *"there are no underconstrained or overconstrained
  systems in SwiftUI"* and *"There's no such thing as an incorrect layout unless
  you don't like the result you're getting."* That is a vendor naming both
  failure modes of the constraint model and selling their absence.
- **Subform** (Kevin Lynagh) argued articulately that a uniform relational model
  beat Flexbox — *"Flexbox introduces new concepts… all of which interact in
  surprising and literally invisible ways"* — launched to 219 points on HN in
  March 2018, and subformapp.com now reads *"Subform is no longer under active
  development."* (No shutdown post-mortem essay was found despite a real search;
  the evidence here is behavioural, not testimonial.)
- **Sketchpad had geometric constraints in 1963** and 63 years later general
  drawing tools are still absolute-coordinate. No authoritative analysis of *why*
  was located; treat the observation as suggestive, not explained.
- What *did* survive is narrow and declarative: CSS flow/Grid/Flexbox, ELK,
  WebCoLa, D2's `near`, Penrose's `ensure`/`encourage`. MDN's framing of normal
  flow is the design instruction: *"by starting in this way you're working with
  the document rather than struggling against it."*

**Design consequence: do not ship a constraint solver. Ship a fixed, tiny,
enumerable set of relational overrides** — `near: <id>`, `below: <id>`,
`align-left: <id>`, `same-rank: <id>,<id>`, `pin: <page-anchor>` — resolvable by
a single deterministic pass over the derived layout, with a defined resolution
order and no simultaneous system to solve. Every entry either resolves or is
dropped with a warning. That is D2's `near` plus Graphviz's `rank=same`, and it
is the largest vocabulary the historical record supports.

---

## 6. Merging spatial data — the general principle

Every system that has actually shipped concurrent spatial editing converges on
the same statement, and each says it in its own words.

### 6.1 Figma — the reference implementation of "good enough"

["How Figma's multiplayer technology works"](https://www.figma.com/blog/how-figmas-multiplayer-technology-works/),
Evan Wallace. Three quotes that settle the architecture question:

> "we didn't want to use operational transforms… OTs were unnecessarily complex
> for our problem space… They result in a combinatorial explosion of possible
> states which is very difficult to reason about."

> "Figma isn't using true CRDTs though. CRDTs are designed for decentralized
> systems where there is no single central authority to decide what the final
> state should be. There is some unavoidable performance and memory overhead with
> doing this. Since Figma is centralized… we can simplify our system by removing
> this extra overhead."

> "Figma's multiplayer servers keep track of the latest value that any client has
> sent for a given property on a given object. **This means that two clients
> changing unrelated properties on the same object won't conflict, and two
> clients changing the same property on unrelated objects also won't conflict. A
> conflict happens when two clients change the same property on the same object,
> in which case the document will just end up with the last value that was sent
> to the server.**"

And the deliberate acceptance of a result nobody intended:

> "If the text value is B and someone changes it to AB at the same time as
> someone else changes it to BC, **the end result will be either AB or BC but
> never ABC**. That's ok with us because Figma is a design tool, not a text
> editor."

**This is exactly what git's line-based three-way merge already gives you** for
a line-oriented file with one property per line — union on disjoint properties,
conflict on the same property. §1's measurements are Figma's model, reproduced
by stock git with no code.

Figma's tree handling is the other half:

> "The approach we settled on was to represent the parent-child relationship by
> storing a link to the parent as a property on the child. That way object
> identity is preserved."

> "To construct a tree we also need a way of determining the order of the children
> for a given parent. Figma uses a technique called 'fractional indexing'…"
> ([Realtime editing of ordered sequences](https://www.figma.com/blog/realtime-editing-of-ordered-sequences/)):
> "To insert between two objects, just set the index for the new object to the
> average index of the two objects on either side. We use arbitrary-precision
> fractions instead of 64-bit doubles so that we can't run out of precision."
> The known cost is named and accepted: "Merging new elements from multiple
> clients may interleave them… Interleaving concurrently inserted elements in a
> design is usually fine because the new objects likely don't overlap."

Figma also ships **branch and merge** — and its own docs say merges are
whole-file and reviewed visually, not hunk-selected:
> "At the moment, you need to merge all updates from the branch into the main
> file. **There isn't a way to select or merge specific changes.**"
> — [Merge branch into main file](https://help.figma.com/hc/en-us/articles/5691189138839)

and their documented recovery from a bad merge is rollback, not repair:
> "**Not all changes from the branch are applied to the main file.**"
> — [Incomplete merges or updates](https://help.figma.com/hc/en-us/articles/5691750511383)

So the design tool with the most sophisticated merge in the industry offers
*less* granularity than `git merge-file` does on a pretty-printed file.

### 6.2 Onshape — merge the program, not the geometry

> "**Onshape identifies all possible geometrical conflicts at the feature level
> prior to merging geometry changes from a branch, and will not make changes to
> features that have conflicts.**"
> — [onshape.com/en/features/branch-merge-cad](https://www.onshape.com/en/features/branch-merge-cad)

Parametric CAD merges the *feature tree* — a semantic, ordered program — and
regenerates geometry. That is the strongest industrial vindication of
"commit the source, derive the picture" (§2). Its safety net is the same as
Figma's: "you can always restore to an earlier version of your design at any
time."

### 6.3 KiCad — what happens without stable identity

KiCad 6+ put a UUID on essentially every primitive
([dev-docs.kicad.org sexpr-intro](https://dev-docs.kicad.org/en/file-formats/sexpr-intro/):
*"The `uuid` token defines an universally unique identifier"*), and the format's
stated design goal is *"Human readability."* It still does not merge, and a
practitioner names exactly why:

> "If you look at the .sch files, the data in there is simply a sequence of
> graphic elements — **it's like a list of instructions, without semantic
> information. When the net list is generated Kicad works out what is connected
> to what simply by looking at the x,y coordinates of the graphic elements.**"
> — bobc, [forum.kicad.info/t/kicad-version-control-and-merging/1975](https://forum.kicad.info/t/kicad-version-control-and-merging/1975)

That is the real spatial A1 defect, and note what it is: **connectivity inferred
from coordinates.** Not "coordinates are stored" — "coordinates are *load
bearing for meaning*". JSON Canvas and tldraw avoid it (edges/bindings reference
ids); KiCad schematics do not.

The consensus on that forum is blunt:
> "**Merging within files can succeed only accidentally.** Merging is of course
> OK if the distributed changes are made to different files."
> — eelik, same thread

and the observed cause is churn, exactly as in §1's F2:
> "by not introducing unnecessary diffs. Sections in the .pro file seem to move
> around at random, and the power symbols in the .sch are constantly getting
> renumbered for no apparent reason… It just seems like version control wasn't on
> the minds of the KiCad developers."
> — ppelleti, [forum.kicad.info/t/…/12843](https://forum.kicad.info/t/does-kicad-need-version-control-integration-or-is-it-just-me/12843)

### 6.4 FreeCAD — the override-goes-stale problem, industrialised

> "The topological naming problem… refers to the issue of a shape changing its
> internal name after a modelling operation… **This will result in other
> parametric features that depend on that shape to break or be incorrectly
> computed.**"
> "**This problem is not unique to FreeCAD. It is generally present in CAD
> software**, but most other CAD software has heuristics to reduce the impact."
> — [wiki.freecad.org/Topological_naming_problem](https://wiki.freecad.org/Topological_naming_problem)

The worked example is §3's stale override with different nouns: *"the top face of
the second pad was renamed from `Face13` to `Face14`. The third sketch is
attached to `Face13` as it originally was, but since this face is now on the
side… the sketch follows its orientation and now is incorrectly positioned."*

FreeCAD 1.0's mitigation is instructive and should be copied verbatim as policy:
identify broken references and **display an error**; sometimes *suggest* a fix
for the user to accept; auto-repair only *"with high confidence in the
correctness of the repair, because an incorrect automatic repair may
re-introduce the problem… **First, do no harm.**"*

And the prescribed structural workaround is the design instruction: attach
sketches to **datum planes** (stable, independent reference geometry) rather
than to **faces** (derived, renameable). Anchor overrides to things that cannot
be regenerated.

### 6.5 Blender — a second independent invention of layered override

Blender's **Library Override** system is USD's `over` at single-tool scale:
> "Library Overrides is a system designed to allow editing linked data, while
> keeping it in sync with the original library data… **When the library data
> changes, unmodified properties of the overridden one will be updated
> accordingly.**"
> — [docs.blender.org … library_overrides](https://docs.blender.org/manual/en/latest/files/linked_libraries/library_overrides.html)

It has the same unfixed hole: *"The relationships between linked data-blocks can
change, resulting in outdated overrides. When this happens, **overrides need to
be resynced**."* And Blender already replaced one attempt at this ("the old
proxy system has been deprecated in Blender 3.0, and fully removed in 3.2").

### 6.6 The industry's actual answer is locking

`git lfs` ships file locking whose documentation states the reason outright:
> "**Concurrent edits in Git repositories will lead to merge conflicts, which are
> very difficult to resolve in large binary files.**"
> — [git-lfs File Locking](https://github.com/git-lfs/git-lfs/wiki/File-Locking)

Perforce sells the same thing to *"19/20 of the top AAA game development
studios"*: *"Prevent merge conflicts with Exclusive File Locking."* USD achieves
it by convention — each department owns a layer file. And the KiCad hobbyist
reinvented it by hand: *"The only safe way I have found is to do 'exclusive'
changes… Git by its nature does not do exclusive, so you have to enforce such
rules yourself."*

This is RESEARCH.md §4's measured conclusion — "a single writer per repository"
— arriving from four unrelated industries.

### 6.7 The principle

**Spatial edits are mergeable exactly to the degree the representation is
decomposed into independently-identified, property-addressable units whose
identity is not positional.** They become unmergeable in exactly two places:

1. **Two edits to the same addressable unit.** Irreducible. Every system picks a
   winner (Figma: last write; git: conflict marker) and offers rollback.
2. **An edit expressed as a reference into a *derived* structure** — a face
   name, a screen coordinate, a layout position — rather than into stable
   identity. Upstream regeneration silently invalidates it and **no conflict is
   ever detected**. This is the topological naming problem, the orphaned USD
   `over`, the Structurizr unmatched element, and §3's stale override. It is the
   real spatial analogue of the 480-vs-660 spreadsheet result.

Every mitigation surveyed is the same move: replace *where it currently sits*
with *what it stably is*. Figma's parent-pointer + fractional index. KiCad's
UUIDs. Blender's override hierarchies. Onshape's feature tree. FreeCAD's datum
planes. tldraw's `index: "a2V"`.

**Not mergeable, ever, in any representation:**
- Two edits to the same property of the same object.
- **Ordering by array position.** JSON Canvas's spec says *"Nodes are placed in
  the array in ascending order by z-index"* — that is positional addressing and
  it merges as badly as A1 references. **Fractional indexing is the fix and it is
  already deployed in this exact domain**: tldraw stores `index: "a1"`, `"a2"`,
  `"a2V"`; Excalidraw added the same `index` field; Figma's `.fig` nodes literally
  carry `parentIndex: { guid, position }`. Copy it.
- **Reparenting / grouping** concurrent with a container edit.
- **Anything derived.** Do not commit it; recompute it.

The one thing spatial data has that spreadsheets do not: **a clean coordinate
merge is never silently wrong.** Both moves land where both authors put them. In
the spatial domain the silent wrongness lives entirely in the *override* layer
and in coordinate-inferred semantics (KiCad), never in stored coordinates
themselves.

---

## 7. Slides

Measured (`experiments/D7-slides/`) on a real one-slide `.pptx`:

- The deck is a zip. Git stores it as a **binary blob**; moving one shape
  produces a whole-file 166 KB replacement, even though **exactly one part**
  (`ppt/slides/slide1.xml`) differs.
- `slide1.xml` is **22 KB on a single line**, 13 `<p:sp>` shapes, 27
  `<a:off x= y=>` pairs in EMU. Moving one shape = 2 lines changed (i.e. the
  file), and two shape moves conflict.
- Pretty-printed to 1071 lines: moving one shape = **2 lines**, and two moves
  **merge cleanly**.

So a deck is git-native the moment it is unzipped and pretty-printed — the same
F1 fix as draw.io.

### 7.1 The outline projection is real and it works

Pandoc's manual states the projection rule outright
([Structuring the slide show](https://pandoc.org/MANUAL.html#structuring-the-slide-show)):

> "By default, the *slide level* is the highest heading level in the hierarchy
> that is followed immediately by content, and not another heading… The document
> is carved up into slides according to the following rules: A horizontal rule
> always starts a new slide. A heading at the slide level always starts a new
> slide. Headings *below* the slide level in the hierarchy create headings
> *within* a slide… Headings *above* the slide level… create 'title slides'."

Org-mode says the same thing with different nouns
([Frames and Blocks in Beamer](https://orgmode.org/manual/Frames-and-Blocks-in-Beamer.html)):
> "Org transforms heading levels into Beamer's sectioning elements, frames and
> blocks… Org headlines become Beamer frames when the heading level in Org is
> equal to `org-beamer-frame-level`."

Note what both do with the things an outline cannot express — columns, overlays,
special environments: they attach them as **properties on outline nodes**
(`BEAMER_COL`, `BEAMER_ENV`, `BEAMER_ACT`), never as coordinates. That is the
same shape as the override layer in §3 and §5: relational metadata on a named
node, resolved at render time.

### 7.2 Where the projection breaks — with the maintainer's own words

Marp's maintainer, on the two-column request
([marp-core#132](https://github.com/marp-team/marp-core/issues/132)):
> "You can use CSS Multi-column Layout Module such as `columns` property by
> tweaking style… **In general, Markdown syntax does just not suitable for
> complex layout so you have to use HTML.**"

The native primitive people keep asking for
([marpit#137, "Split slides"](https://github.com/marp-team/marpit/issues/137))
remains open. Deckset has `[.column]` with proportional widths and image
placement keywords (`![left]`, `![fit]`, `![inline 50%]`) but **no arbitrary
top/left placement at all**. reveal.js's `r-stack` is z-stacking, not placement.
remark's escape hatch is slide `template`/`layout` inheritance — again,
inheritance rather than coordinates.

**Quarto is the decisive counter-example**, and it should be read as an
admission ([revealjs/advanced.html](https://quarto.org/docs/presentations/revealjs/advanced.html)):
> "The `absolute` class lets you position elements at arbitrary positions on a
> slide. These elements have CSS `position: absolute` and can be placed relative
> to the `top`, `left`, `bottom`, and/or `right` edges of the slide."
> `![](image1.png){.absolute top=200 left=0 width="350" height="300"}`

A markdown deck tool shipped absolute x/y, smuggled in through pandoc attribute
syntax. So the boundary is precisely locatable: **outline projection covers
title/body/bullets/columns/backgrounds; anything else requires either raw HTML
or an explicit absolute escape hatch, and every serious tool eventually ships
one.**

Slidev's `v-drag` is the only shipping drag-to-position that writes back into
plaintext, and its own docs concede the mechanism:
> "**Slidev use regex to update the position value in the slide content.** If
> you meet problems, please use the frontmatter to define the values instead."
> — [sli.dev/features/draggable](https://sli.dev/features/draggable)

with corroborating bugs ([slidev#1811](https://github.com/slidevjs/slidev/issues/1811),
[#1959](https://github.com/slidevjs/slidev/issues/1959), the latter appending
`undefined` to the tag while dragging). RESEARCH.md §5's "WYSIWYG-slides gap"
finding stands unchanged as of 2026.

### 7.3 pptx's inheritance system — the best mainstream prior art, ignored in practice

`slideMaster1.xml` → `slideLayout*.xml` → `slide1.xml` is a real, shipped,
three-level inheritance system for exactly the semantic/style split:

> "A layout placeholder inherits from the master placeholder sharing the same
> type. **A slide placeholder inherits from the layout placeholder having the
> same `idx` value.**"
> "**In general, all formatting properties are inherited from the 'parent'
> placeholder. This includes position and size** as well as fill, line, and font."
> "**Any directly applied formatting overrides the corresponding inherited
> value.** Directly applied formatting can be removed be reapplying the layout."
> — [python-pptx, Understanding placeholders](https://python-pptx.readthedocs.io/en/latest/user/placeholders-understanding.html)

That is weak-layer/strong-layer opinion resolution, keyed by `type` + `idx`, with
`<p:ph type="title"/>` on a slide legally carrying **no `<a:xfrm>` at all**.
Colours are indirected the same way — ISO/IEC 29500 on `<a:schemeClr>`:
*"This element specifies a color bound to a user's theme."* Units are EMU
(914400 = 1 inch, 12700 = 1 point; verified in `python-pptx` `util.py`).

**And the real file shows authors routing around all of it.** The sampled deck
has 13 shapes and `<p:ph>` count = **0** — every shape is a free-floating text
box with explicit EMU coordinates and no inheritance. (A general prevalence
figure for placeholder vs. free-floating shapes could not be sourced; treat the
single-file observation as illustrative, not statistical.) The inheritance system
is available, mainstream, decades old, and unused where it matters most.

Google Slides is the opposite pole and worth naming: every `PageElement` has a
stable `objectId` and a full affine `transform`
(*"`x' = scaleX * x + shearX * y + translateX`"*,
[Slides API AffineTransform](https://developers.google.com/slides/api/reference/rest/v1/presentations.pages/other#Page.AffineTransform)) —
pure spatial, no outline concept whatsoever. Keynote's `.key` is Snappy-compressed
protobuf `.iwa` (reverse-engineered by `keynote-parser`; Apple publishes no spec)
and is simply out of reach.

### 7.4 Verdict

**A deck is (c) a view of an outline, until someone needs (b), and then no
amount of (c) helps.** The boundary is sharp and §7.2 locates it. The design
consequence is not to pick one: it is to make the outline the source, and give
the escape hatch a *named, structured* form — Quarto's `{.absolute}` on a
named element, or pptx's placeholder override — rather than letting arbitrary
coordinates leak into the body of the document.

---

## 8. Images and binary reality

Measured (`experiments/D7-images/`), 21 revisions of one image, each revision a
small annotation added. Cost of the whole history as a multiple of one copy:

| content | one copy | plain git (gc'd) | git-lfs | CDC (gear, avg 8 KiB) | fixed 8 KiB blocks |
|---|---|---|---|---|---|
| PNG, incompressible content | 4.18 MB | **2.33×** | 21.0× | 10.6× | 20.0× |
| PNG, compressible diagram | 94.7 KB | **6.51×** | 21.6× | **18.4×** | 20.0× |
| PPM, uncompressed raster | 4.20 MB | **1.05×** | 21.0× | 2.40× | 2.44× |
| SVG, text | 18.9 KB | **2.31×** | 23.5× | n/a (files < chunk size) | 3.65× |

Three results that change the prior recommendation:

1. **git-lfs is the worst option for repository size in every case (21–23×).**
   It stores every version whole and uncompressed under `.git/lfs/objects` and
   gets no delta compression. Its win is lazy fetch on clone, not storage.
2. **Content-defined chunking does not work on already-compressed formats.**
   For the compressible diagram PNG, CDC achieved 18.4× — barely better than
   storing every copy — because changing a few pixels near the top relocates the
   entire DEFLATE bitstream and no chunk boundary survives. On the *uncompressed*
   PPM the same chunker got 2.40×. **CDC is a function of the container, not the
   content.** The prior "use content-defined chunking into a CAS" recommendation
   is only correct if the substrate also controls the container.
3. **Plain git's delta compression beat CDC in all four cases** (1.05× / 2.33× /
   6.51× / 2.31×). For images at these sizes, stock git packfiles are already the
   better answer, and the earlier 20.6× figure appears to be a worst-case, not
   the typical one.

**What the substrate must specify:** store the *source*, not the export. An SVG
of the same 21 revisions costs a 2-line diff per revision. Rasters, when
unavoidable, belong in a CAS with pointer files for lazy fetch — but choose it
for fetch behaviour and for keeping the working tree small, not for
deduplication, which will not materialise on PNG/JPEG/MP4. Never store both a
vector source and its raster export under version control.

---

## 9. The kill question — should this leg be dropped?

**The strongest case for dropping it, stated fairly:**

1. Structured diagrams are *already solved and already text*. Mermaid, Graphviz,
   D2, PlantUML, Structurizr all diff like code and Kroki (MIT) renders all of
   them behind one API. Building a fifth diagram language adds nothing.
2. Freeform canvas has no semantic layer by definition. L4 concedes this. A
   whiteboard sketch's content *is* its coordinates, and the best the substrate
   can do is version a blob.
3. The override layer's central failure — the orphaned/stale override — is
   **unsolved by Pixar, unsolved by Structurizr, unsolved by Graphviz, unsolved
   by FreeCAD after twenty years**. Shipping it means shipping a known silent
   wrongness.
4. Every serious attempt at user-authored spatial constraints has been walked
   back (Auto Layout → SwiftUI) or died (Subform).
5. Slides are documents with page breaks 90% of the time, and the other 10% is
   PowerPoint's job.
6. §1 shows real canvas formats already merge fine once pretty-printed. If the
   formats are already adequate, the substrate's job is a **clean filter**, not a
   new representation — and a clean filter is 40 lines, not a leg.
7. And the bar is lower than it looks. Figma — the most advanced concurrent
   design tool in existence — resolves conflicts by per-property last-writer-wins
   and, on branch merge, offers *"no way to select or merge specific changes."*
   Stock `git merge-file` on a pretty-printed canvas already does **better than
   that**: union on disjoint properties, an explicit marker on the same one.

**Adjudication.** Point 6 is the decisive one, and it inverts the question. The
measurements say the substrate does not need to *invent* a spatial
representation; it needs to enforce four properties on whatever representation
passes through it. So:

**Drop "spatial" as a leg. Keep it as a conformance rule.** The core should
carry no canvas format, no diagram language, no layout engine. It should carry:

- **The four-property conformance rule** (below), applied to every format.
- **Clean/smudge filters** for the formats people actually use — pretty-print
  draw.io and OOXML parts, strip `modified`/`etag`/`agent` from `.drawio`, strip
  `camera`/`pointer`/`instance`/`instance_page_state` from `.tldr`. This is the
  cheapest large win in the whole D7 investigation and it is entirely
  mechanical.
- **`.canvas` (JSON Canvas 1.0) as the recommended freeform format**, because it
  is the only open spec in the survey that already satisfies three of the four
  properties: stable string ids, one node per line, edges referencing nodes by
  `fromNode`/`toNode` and sides rather than waypoints, and no session state. Its
  two defects are fixable: array-position z-order (add fractional indices) and
  records so dense that adjacent-line edits conflict (pad, or merge with a
  record-aware driver).
- **Diagrams: delegate to D2 (MPL-2.0) or Graphviz, rendered via Kroki.** Do not
  build a language. If an override layer is wanted, ship Structurizr's shape —
  a *separate* file, name-keyed, dropped-with-a-warning when unmatched — and
  restrict its vocabulary to relational operators only (§5). Never write derived
  coordinates to disk.
- **Slides: a document with page breaks, projected from an outline** (Marpit as
  a library, per RESEARCH.md §5), with a documented escape to `.pptx` when
  arbitrary placement is genuinely required. Do not attempt WYSIWYG slides over
  markdown; the gap is real and nobody has closed it.
- **Rasters: a CAS with pointer files, chosen for lazy fetch, not dedup.**

---

## 10. The conformance rule (the actual deliverable)

A spatial artifact is substrate-conformant iff:

1. **Line-oriented.** One value, or one small record, per line. Nothing that
   serialises a scene onto one line. (Fixes: draw.io, OOXML, minified JSON.)
2. **No churn.** No field that changes on save without a user edit: no
   timestamps, no etags, no user-agent, no viewport/camera, no window size, no
   current selection, no random nonce on an unchanged element. (Fixes: draw.io
   headers, tldraw session records. Excalidraw already complies for viewport and
   for untouched elements; its per-move `versionNonce` costs 4 extra changed
   lines but no false conflicts.)
3. **Stable identity, and no positional addressing.** Every object carries an id
   that survives edits by others. Ordering is expressed with **fractional
   indices**, never array position. Connections reference ids, never coordinates.
4. **Nothing derived is committed.** Auto-layout output, routed edge paths and
   rendered exports are build artifacts. Committing them converts every semantic
   edit into a whole-file rewrite (measured: 26% of an Excalidraw file, 72% of a
   Graphviz SVG) and is the sole cause of the multi-conflict, unparseable-output
   failure L4 observed.

Plus one rule for the override layer, if one is built:

5. **Overrides are relational and separately filed.** They live in a different
   file from the semantics; they are keyed by stable id (with name as a
   human-readable fallback); they use a fixed, small vocabulary of relational
   operators, never absolute or delta coordinates; and an override that cannot
   be resolved is **dropped with a warning, never applied and never fatal**.

---

## 11. Corrections to L4

| L4 claim | status |
|---|---|
| Full-coordinate JSON conflicts on two unrelated edits | **False for real files.** Real `.excalidraw`, `.tldr`, `.canvas`, pretty `.drawio` and pretty OOXML all merge cleanly. L4's case B was minified and carried a relayout. |
| "Absolute coordinates are the spatial form of A1 cell references" | **False.** A1's defect is silent wrongness on clean merge; coordinates merge to exactly both authors' intent. The spatial analogue of A1 is **array-position z-order**, which fractional indexing already solves. |
| Positions should be derived, not stored | **True, and for a stronger reason than given.** Adding one node moved 4/4 existing nodes and mirrored the layout; the SVG changed 72%. Derived coordinates in a file are the actual cause of the failure L4 measured. |
| Name-keyed sparse overrides merge cleanly | **True, and confirmed at scale** by Structurizr and USD. |
| …and are therefore correct after merge | **False.** Measured: after an unrelated node was added, the absolute override introduced an edge crossing that did not exist and sat 1.46 units from the derived position. Clean merge, worse diagram. |
| A numeric offset from a named anchor would fix it | **False, and it is worse than absolute** (8.27 vs 6.20 total edge length). Only qualitative/relational overrides survive. |
| Freeform canvas must be an opaque blob | **False and unnecessary.** JSON Canvas and tldraw are line-oriented with stable ids and merge cleanly once session state is filtered out. |
| The substrate should carry structured diagrams natively | **Rejected.** It should carry a conformance rule and clean filters, and delegate the languages. |

---

## Sources

Files: `experiments/D7-canvas-formats/{excalidraw,drawio,jsoncanvas,tldraw,svg}/`,
`D7-semantic-layout/`, `D7-usd/`, `D7-slides/`, `D7-images/`.

- Excalidraw source: `packages/element/src/mutateElement.ts`,
  `packages/excalidraw/data/json.ts`, `packages/excalidraw/data/restore.ts`,
  `packages/excalidraw/appState.ts`
- JSON Canvas 1.0 spec — <https://jsoncanvas.org/spec/1.0/>
- OpenUSD glossary (LIVERPS, Over, LayerStack, SubLayers) —
  <https://openusd.org/release/glossary.html>; FAQ (orphaned overs) —
  <https://openusd.org/release/usdfaq.html>
- Structurizr manual layout — <https://docs.structurizr.com/ui/diagrams/manual-layout>;
  `structurizr/java` `DefaultLayoutMergeStrategy.java`
- D2 — <https://d2lang.com/tour/positions/>, <https://d2lang.com/tour/layouts/>,
  `d2lang/d2` LICENSE.txt (MPL-2.0), `terrastruct/TALA` README
- Graphviz — <https://graphviz.org/docs/attrs/pos/>,
  <https://graphviz.org/doc/info/command.html>, gitlab issues #2552, #1625, #2845
- Mermaid issues #565, #2457, #2483; PlantUML issue #1244
- Penrose SIGGRAPH 2020 —
  <https://penrose.cs.cmu.edu/media/Penrose_SIGGRAPH2020a.pdf>; issues #1490,
  #1645; Bloom — <https://penrose.cs.cmu.edu/blog/bloom>
- Bluefish, UIST 2024 — <https://arxiv.org/pdf/2307.00146v4>
- Cassowary — <https://constraints.cs.washington.edu/solvers/cassowary-tochi.pdf>
- Apple Auto Layout conflict docs; WWDC 2019 session 237 (SwiftUI layout)
- Subform — <https://subformapp.com>, "Why Not Flexbox"
- Kroki — <https://kroki.io>
- Figma — <https://www.figma.com/blog/how-figmas-multiplayer-technology-works/>,
  <https://www.figma.com/blog/realtime-editing-of-ordered-sequences/>,
  help.figma.com branch/merge articles 360063144053, 5691189138839, 5691750511383;
  `.fig` = zip + `fig-kiwi` binary (evanw/kiwi schema format)
- Onshape — <https://www.onshape.com/en/features/branch-merge-cad>
- FreeCAD — <https://wiki.freecad.org/Topological_naming_problem>,
  <https://wiki.freecad.org/Document_structure>
- KiCad — <https://dev-docs.kicad.org/en/file-formats/sexpr-intro/>;
  forum threads 1975, 12843, 30802
- Blender Library Overrides —
  <https://docs.blender.org/manual/en/latest/files/linked_libraries/library_overrides.html>
- git-lfs File Locking — <https://github.com/git-lfs/git-lfs/wiki/File-Locking>;
  Perforce Helix Core exclusive locking
- Pandoc — <https://pandoc.org/MANUAL.html#structuring-the-slide-show>;
  Org — <https://orgmode.org/manual/Frames-and-Blocks-in-Beamer.html>
- Quarto `.absolute` — <https://quarto.org/docs/presentations/revealjs/advanced.html>;
  Slidev `v-drag` — <https://sli.dev/features/draggable>;
  marp-core#132, marpit#137
- OOXML — learn.microsoft.com "Working with slide layouts"/"slide masters",
  `<a:off>` / `<a:schemeClr>` ISO/IEC 29500 entries;
  <https://python-pptx.readthedocs.io/en/latest/user/placeholders-understanding.html>
- Google Slides API AffineTransform —
  <https://developers.google.com/slides/api/reference/rest/v1/presentations.pages/other#Page.AffineTransform>

### Method caveats

- Web search quota was exhausted early in two of the four research streams; those
  sections were built from direct fetches of known URLs and repo APIs, so
  coverage of *new* 2025–2026 entrants (especially in §7.2) is thinner than the
  rest.
- Not verified: any quantitative split of real-world pptx shapes between
  placeholders and free-floating text boxes; current Gamma/Tome markdown-import
  status; a Subform shutdown post-mortem (searched, not found — the evidence
  there is behavioural); GMF/Papyrus `.notation` desync literature (asserted from
  background knowledge only, no fetched source).
- The CDC figures for SVG in §8 are not meaningful (files smaller than the chunk
  size); the PNG and PPM figures are.

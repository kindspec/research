# D3 — Semantic diff and 3-way merge for non-code artifacts

Research + empirical testing, 2026-08-28. Environment: git 2.47.3, Debian 13,
LibreOffice (headless), mergiraf 0.19.0 (built from crates.io), daff 1.4.2 (npm).

All transcripts reproduce from `experiments/D3-*/`. Every number below came out of
a command run here, or from a paper/source I read. Claims I could not verify are
marked ⚠.

---

## 0. The three questions, answered up front

1. **How good can structural diff/merge get?** Good, and cheap, for *tree-shaped*
   artifacts (JSON, YAML, XML, Markdown) and for *tables* (daff). The literature is
   mature and the tools are real, installable, and worked on first try here.
2. **What does it cost?** Not CPU. `O(n²)` matchers are free at document scale.
   The cost is **deployment**, and it is fatal in the specific place it matters.
3. **Where does it fail to run?** **On every server.** A custom merge driver is
   selected by a repo-tracked `.gitattributes` line but *defined* only in local git
   config, which is never transferred. And in a **bare** repository — which is what
   a forge has — the repo's own `.gitattributes` is not even consulted. Both facts
   are demonstrated below.

---

## 1. Tree diff algorithms — what the literature actually says

### Complexity, and whether it matters

| Algorithm | Bound | Note |
|---|---|---|
| Tai 1979 | O(n₁·n₂·depth₁²·depth₂²) | first ordered TED |
| **Zhang–Shasha 1989** | O(n₁·n₂·min(depth₁,leaves₁)·min(depth₂,leaves₂)), **O(n⁴) worst case**, O(n₁n₂) space | the classic |
| Klein | O(n³ log n) | |
| **RTED** (Pawlik & Augsten, PVLDB 2011) | **O(n³) time, O(n²) space**, worst-case optimal | picks the optimal decomposition strategy in O(n²) first |
| **APTED** (TODS 2015 / Inf.Sys. 2016) | same time, less memory | supersedes RTED |
| **GumTree** (Falleri et al., ASE 2014) | **O(n²)** | heuristic; quarantines a cubic step inside `maxSize` |
| **truediff** (Erdweg, Szabó, Pacak, **PLDI 2021**) | **O(m+n)** — Theorem 4.1 | hashing + linear-typed subtree assignment |

Two hard results bound the whole field:

- **Unordered** tree edit distance is **NP-complete** — Zhang, Statman & Shasha,
  *IPL* 42(3):133–139, 1992. ⚠ (paywalled; the "binary trees, |Σ|=2" restriction is
  from secondary sources.)
- **Ordered** TED **cannot be computed in strongly subcubic time unless APSP can** —
  Bringmann, Gawrychowski, Mozes & Weimann, SODA 2018 / *TALG* 16(4):48, 2020,
  [arXiv:1703.08940](https://arxiv.org/abs/1703.08940). Verbatim: *"a truly subcubic
  algorithm for tree edit distance implies a truly subcubic algorithm for the all
  pairs shortest paths problem."* Note the contrast they draw: string edit distance
  is SETH-hard, tree edit distance is **APSP**-hard.
- **Minimum edit script including moves is NP-hard** (Bille, *TCS* 337:217–239,
  2005; cited as such in the GumTree paper, footnote 1).

**Does the big-O matter at document scale?** Mostly no, and the crossover is lower
than intuition suggests:

- At n ≈ 2,000 (a mid-size Markdown AST) an O(n²) matcher is 4×10⁶ ops — instant.
  Algorithm choice here is a **quality** question, not a performance one.
- O(n³) is *not* fine even at n=2,000. GumTree's own ASE 2014 measurements: RTED
  **OOM'd at 4 GB on ~5%** of real Java file revisions and blew a 10-second budget
  on another **~12%** — *"RTED is not capable of computing an edit script for around
  17% of the cases."* That measurement is the entire reason `maxSize = 100` exists.
- At n ≈ 200,000 (a large table, a big SVG) O(n²) = 4×10¹⁰ — dead. Only the linear
  class (truediff) or aggressive pruning survives.
- difftastic quantifies the same wall from the other side: its graph is **O(L×R)**
  with `DEFAULT_GRAPH_LIMIT = 3_000_000` vertices, source comment: *"small enough to
  terminate in ~5 seconds"*. Beyond it, it prints `Text (exceeded DFT_GRAPH_LIMIT)`
  and falls back to line diff.

**The scale trap:** quality degrades with n for a *different* reason than cost. More
repeated identical subtrees ⇒ more ambiguous matching. Large tabular documents are
worst-case for cost **and** correctness simultaneously.

### GumTree, precisely (the standard, and what everyone builds on)

Falleri, Morandat, Blanc, Martinez, Monperrus, *"Fine-grained and Accurate Source
Code Differencing"*, **ASE 2014**, DOI 10.1145/2642937.2642982,
[PDF](https://hal.science/hal-01054552/file/main.pdf).

Three phases: (1) **top-down** greedy isomorphic-subtree matching by height, only
for nodes taller than `minHeight`; (2) **bottom-up** container matching where
`dice(t1,t2,M) = 2·|matched descendants| / (|s(t1)|+|s(t2)|)` exceeds `minDice`;
(3) **recovery** — strip matched descendants and, if both residual subtrees are
smaller than `maxSize`, run RTED. Edit script from the mappings via Chawathe et al.
(SIGMOD 1996), also O(n²).

Defaults, verbatim from the paper: *"We recommend minHeight = 2 to avoid single
identifiers to match everywhere… we recommend to use maxSize = 100… Therefore we
recommend using minDice = 0.5."*

**Move detection is not a phase.** Moves fall out of the Chawathe generator given
the mappings — which means *mapping errors become move errors*, and move errors are
the ones humans notice.

### The failure-mode evidence — this is the part that matters

- **Frick, Grassauer, Beck & Pinzger, ICSME 2018** (IJM),
  [PDF](https://pinzger.github.io/papers/Frick2018-ijm.pdf). 307,081 Java file
  revisions; 2,400 edit actions manually assessed by **11 external experts**:
  *"over **55%** of GT's and over **81%** of MTD's generated move and update actions
  are inaccurate according to our definition."*
- **Fan et al., ICSE 2021**, [arXiv:2103.00141](https://arxiv.org/pdf/2103.00141).
  263,165 file revisions: *"GumTree, MTDiff and IJM generate inaccurate mappings for
  **20%–29%**, 25%–36% and 21%–30% of the file revisions, respectively."*
- **Martinez, Falleri & Monperrus, TSE 49(10), 2023** — hyperparameter tuning
  improves the edit script in **21.8%** of cases, i.e. the recommended defaults are
  demonstrably not optimal per-case.
- **Alikhanifard & Tsantalis, TOSEM 2024**, [arXiv:2403.05939](https://arxiv.org/abs/2403.05939)
  — first AST-mapping benchmark (800 bug-fix + 188 refactoring commits). Counts of
  *semantically incompatible* mappings: RefactoringMiner **0**, GumTree 3.0 greedy
  **629**, GumTree 3.0 simple 214, GumTree 2.1.0 504, IJM 85.
- **Falleri & Martinez, ICSE 2024** — the authors' own retraction of the RTED step:
  *"The main drawback of GumTree's algorithm is the use of an optimal, but expensive
  tree-edit distance algorithm that makes it difficult to diff large ASTs"* — their
  replacement heuristic gives **50×–281×** speedup and **50% smaller** edit scripts.

**Read this honestly:** the standard AST differ, on the domain it was designed for,
with expert raters, produces move/update actions judged wrong **more than half the
time**, and at least one bad mapping in **20–29% of file revisions**. Structural
diff is *better than line diff*, not *correct*.

### ChangeDistiller and its self-declared limit

Fluri, Würsch, Pinzger & Gall, *TSE* 33(11):725–743, 2007. Bigram string similarity
for leaves, Chawathe subtree similarity for inner nodes (threshold t = 0.6), dynamic
thresholds for small subtrees. 45% better than Chawathe on 1,064 manually classified
changes. Its stated Achilles heel is **Assumption 1** — at most one matching leaf
per leaf: *"Suboptimal results are very likely to occur whenever Assumption 1 does
not hold… these mismatches can be propagated to higher levels of the tree, leading
to a complete mismatch of a whole subtree."* Their own worked example finds **nine
changes where one was expected**. Repeated boilerplate breaks it — and documents and
tables are *made of* repeated boilerplate.

### truediff — the one that is actually linear

⚠ Correcting the brief's attribution: **Erdweg, Szabó & Pacak, "Concise, Type-Safe,
and Efficient Structural Diffing", PLDI 2021**, DOI 10.1145/3453483.3454052,
[PDF](https://andrepacak.de/paper/truediff_pldi2021.pdf) — not SLE, not Zwaan/van
der Storm, and "truediff" is in the body, not the title.

**Theorem 4.1:** *"truediff ∈ O(m+n)."* Two hashes per node (a `structureHash`
ignoring literals, a `literalHash`), a hash trie of *subtree shares*, greedy
assignment, *"a subtree can be assigned at most once."* Nodes carry URIs so the
**patch** is proportional to the change: *"truediff uses URIs to identify changed
nodes and does not mention unchanged nodes in the patch."*

⚠ **It does not require an incremental parser** — the brief's premise. The paper
says the opposite: tree-sitter *"only reveals which subtrees contain changes, not
how they changed"*, and an incremental parser's output would merely be a sound
over-approximation they could use as an *optimisation*. What it requires is that the
tree implement their `Diffable` interface. Note also: the *runtime* is linear in
**tree** size; only the *patch* is proportional to the edit.

### difftastic — and why its author refuses to merge

Wilfred Hughes, *"Difftastic, the Fantastic Diff"*, **6 September 2022** (⚠ not
October), <https://www.wilfred.me.uk/blog/2022/09/06/difftastic-the-fantastic-diff/>.

He did **not** abandon tree edit distance for something of his own — he adopted
Autochrome's formulation: *"autochrome is the most effective approach I found."*
Diffing is a **shortest-path problem on a DAG**; a vertex is *"(left-hand side
position, right-hand side position, list_of_parents_to_exit_together)"*; three edge
types (novel-left, novel-right, match) with match cheapest; solved with **Dijkstra**.
⚠ What he *did* abandon is A\*: *"I explored better route finding algorithms (e.g.
A\*) but I didn't see much improvement."* And he abandoned minimality as an
objective — *"This isn't what the user wants though… I solved this by adjusting the
graph edge cost model to produce nicer results."*

The reframing that drives it all: *"I thought of diffing programs as working out
what has changed. The goal of diffing is actually to work out what **hasn't**
changed!"*

On merge, the README is one sentence: **"AST merging is a hard problem that
difftastic does not address."** His closing lesson: *"I'd been wondering why this
type of tool is so rare. Now I know: it's extremely challenging to build."*

difftastic also does **no move detection at all** — *"considers ordering to be
meaningful everywhere, so it will always report ordering changes."* Its "tricky
cases" page documents *sliders*: repeated identical sequences match arbitrarily.
This is the same ambiguity as ChangeDistiller's Assumption 1, from a different angle.

---

## 2. Structured merge — the tools, tested

### mergiraf 0.19.0 — the real generic answer, and its real limits

GPLv3, Rust, Antonin Delpeuch + Ada Alakbarova.
<https://codeberg.org/mergiraf/mergiraf>, <https://mergiraf.org>.

**Architecture** (<https://mergiraf.org/architecture.html>), opening line:
*"Mergiraf broadly follows the architecture of spork."* Eight phases: tree-sitter
parse (language detected **by file extension**) → **GumTree classic** matching
(*"The heuristic we use to produce matchings between syntax trees is the GumTree
classic algorithm"*) → class-mapping → **PCS triples** (Lindholm's 3DM changeset
formulation) → changeset merge → tree build → delete/modify + duplicate-signature
checks → render with whitespace imitated from the originals.

**"Commutative parents"** is the key idea, declared per language in
`src/supported_langs.rs`. A node type marked commutative merges by taking left's
child list, removing right's deletions, appending right's additions. JSON's `object`
is commutative (*"the order of keys is deemed irrelevant"*) with
`signature("pair",[[Field("key")]])` so duplicate keys still conflict. Java's
`program` is commutative but *restricted* to children-groups, so concurrent imports
merge while an import cannot float into the class list.

**Auto-tuning**, exactly JDime's idea: line merge runs *first*; only if it conflicts
does the tree machinery run, seeded from the already-merged regions.

**Fallback:** *"If a parsing error occurs in any of the three revisions, the
algorithm aborts and falls back on line-based merging."* Verified — see M6 below.

**Languages (47 profiles at 0.19.0, verified by running `mergiraf languages`):**
Markdown, JSON, YAML, XML, HTML, TOML, INI + 40 programming languages.
**No CSV. No SVG.** (SVG can be forced onto the XML profile via `.gitattributes`;
there are no SVG-aware commutative parents, so `<g>` paint order stays ordered.)
⚠ The published languages page still omits Markdown; the source has it.

⚠ **Mergiraf publishes no accuracy percentage.** The author states his focus is
*"usability, in contrast to academic prototypes."* Two external numbers exist:
- **LWN, 31 Oct 2025** (<https://lwn.net/Articles/1042355/>): replaying Linux kernel
  history, of **7,415 conflicted merge commits** Mergiraf fully resolved
  **428 (5.8%)**, more partially.
- **LastMerge**, [arXiv:2507.19687](https://arxiv.org/abs/2507.19687): on 5,229 merge
  scenarios, Spork and Mergiraf disagree on conflict existence in **11.3%** of files;
  *"Mergiraf misses 42% fewer false negatives than Spork."*
There is **no Mergiraf paper**.

#### What I measured (`experiments/D3-tools/run-mergiraf.sh`, `mgwork/verify`)

| Case | plain git | mergiraf |
|---|---|---|
| **V2** JSON: two authors add a *different key* to the same object | **conflict** (false) | ✅ **merged correctly** — the commutative-parent win, real |
| **V3** JSON: two authors add the *same key* `timeout` at different places | silent duplicate key | ✅ **conflict** (signature check) |
| **M2** YAML: same key added at two places | **silent duplicate key** | ✅ **conflict** |
| **M4** SVG (forced onto XML profile): concurrent `<defs>` id | conflict | conflict (safe, no gain) |
| **M5** CSV: two authors edit different columns of the same row | conflict | **conflict** — *no CSV profile, falls back to line merge* |
| **M6** unparseable JSON (missing `}`) | clean line merge | **clean line merge** — graceful fallback, as documented |
| **M7** Markdown: adjacent paragraphs edited | clean | clean |
| **M1 / V1** Markdown: duplicate **link-reference definition** `[api]` introduced concurrently | **silent wrong** | ❌ **silent wrong — mergiraf merges it cleanly too** |
| **V4** JSON: array of objects, duplicate application-level `id` | **silent wrong** | ❌ **silent wrong** |

**V5 — formatting preservation verified.** Base with tabs and ragged spacing
(`\t"a"   :  1,`) came back byte-identical apart from the two changed values. This
matters more than it sounds: a structured merger that reformats destroys the diff,
which is the whole product premise.

**The honest verdict on mergiraf:** it converts *some* silent-wrong into honest
conflicts (duplicate keys), and converts *many* false conflicts into correct merges
(commutative parents). It does **not** catch semantic duplicates one level down —
duplicate `id` fields inside a JSON array, duplicate Markdown link labels — because
its signatures are **syntactic** (object keys), not application-level. Its guarantee
is *well-formedness and syntax-level identity*, not *document semantics*.

### daff 1.4.2 — the table answer, and the one that surprised me

Paul Fitzpatrick, MIT, <https://github.com/paulfitz/daff>, spec at
<https://paulfitz.github.io/daff-doc/spec.html> (also standardised as
[Frictionless tabular-diff](https://specs.frictionlessdata.io/tabular-diff/)).

**Alignment** (`coopy/CompareTable.hx`, `alignCore2`): with `--id` it indexes on the
declared key. **Without a key it discovers one**: score each common column by
distinct-value count, keep the top **N = 5**, enumerate all **2⁵−1 subsets** as
candidate composite keys, hash-index both sides (`Index.toKey` joins cells with
`" // "`), link rows unique on both sides; reject an index whose top key frequency /
(height+20) ≥ 0.1 — the source comment reads *"lousy no-good index, we should move
on."* A final pass links ambiguous rows adjacent to already-aligned ones.

**Highlighter format** — action column: `!` schema, `@@` header, `+++` insert,
`---` delete, `->` modify, `:` reorder, `...` elision. The schema row carries
column insert/delete, `(NAME)` for rename, `:` for reorder. Verified live:

```
!,,,+++,
@@,id,name,dept,salary
+,1,Alice,Eng,100
+,2,Bob,Eng,90
->,3,Carol,Eng,999->110
```

**Merge** (`coopy/Merger.hx`) is genuinely **cell-level** three-way. Row/column
*moves* are explicitly not merged — the source says `// row/col movement -- ignore
for now`.

#### What I measured (`experiments/D3-tools/run-daff.sh`)

| Case | plain git | daff as merge driver |
|---|---|---|
| D1 same row, different columns | ❌ conflict (false) | ✅ correct merge |
| D2 column inserted on one side + row edited on other | ❌ conflict (false) | ✅ correct merge |
| D3 row reorder on one side + row edit on other | ❌ mangled: 7 duplicated ids, **edit silently lost** | ✅ reorder **and** edit both preserved |
| D4 both edit the *same* cell | conflict, markers destroy the CSV | ✅ conflict, **CSV stays valid** (see §4) |
| **D5 A1 formulas, two row inserts** | ❌ **silent wrong, 3500 vs 5100** | ❌ **silent wrong, 3500 vs 5100 — identical** |

**D5 is the sharpest result in this whole document.** daff merged the *rows*
perfectly. The answer is still 31% wrong, because the formulas are **opaque strings
in cells** and A1 references are positional. A structural table merge cannot fix a
positional addressing scheme. **The format has to change; a better merge tool cannot
rescue it.** This is independent, mechanical confirmation of the named-column
recommendation in `RESEARCH.md` §3 — and it raises the stakes: named columns are not
an optimisation over cell-level merge, they are a *prerequisite* that cell-level
merge cannot substitute for.

### The academic lineage, with the numbers straightened out

- **FSTMerge** — Apel, Liebig, Brandl, Lengauer, Kästner, *"Semistructured Merge:
  Rethinking Merge in Revision Control Systems"*, **ESEC/FSE 2011**, DOI
  10.1145/2025113.2025141. Annotated grammars: you mark nodes ordered vs unordered;
  everything unannotated stays text. 24 projects, 180 merge scenarios. Verbatim:
  *"semistructured merge reduces the number of conflicts in **60%** of the sample
  merge scenarios by, on average, **34%**"* — ⚠ note the shape of that claim, it is
  "60% of scenarios", not "60% fewer conflicts". It also **increases** conflicts in
  **26%** of scenarios by 109±170%. Net: **35% overall reduction**.
- **JDime auto-tuning** — Apel, Lessenich & Lengauer, **ASE 2012** (⚠ not 2011),
  DOI 10.1145/2351676.2351694. Unstructured merge first, escalate to structured only
  on conflicting subtrees: **up to 12× faster, 5× on average** over pure structured
  merge on 72 scenarios / >17M LOC. This is the design mergiraf inherited.
- **Cavalcanti, Borba & Accioly**, *PACMPL* 1(OOPSLA) art. 59, 2017, DOI
  10.1145/3133883 — **>30,000 merges, 50 projects**. Semistructured merge cuts false
  positives but shows **no evidence of fewer false negatives**; their improved tool
  *"reduces the number of reported conflicts by half, has no additional false
  positives, has at least 8% fewer false negatives."* Their replication measured
  **62%** average conflict reduction against the original paper's 34%.
- **Spork** — Larsén, **Falleri, Baudry**, Monperrus (⚠ the brief's "Ryan" is
  wrong), *IEEE TSE*, DOI 10.1109/TSE.2022.3143766,
  [arXiv:2202.05329](https://arxiv.org/abs/2202.05329). 3DM PCS + GumTree + Spoon.
  890 merge scenarios / 1,740 file merges / 119 projects: **40% fewer conflict hunks
  than JDime**; conflicting *lines* 2,446 vs JDime's 13,975 (**63% better**).
  Formatting: median line diff **65 vs 308.5 (−78%)**, char diff **528 vs 2,181
  (−75%)**. Failure rate **4.77%**. ⚠ Spork does **not** benchmark against `git
  merge` for conflict counts.
  Its formatting trick — copy-paste the original source text for any subtree
  originating from a single revision — is the one mergiraf reproduces (V5 above).
- **3DM** — Tancred Lindholm, *"A three-way merge for XML documents"*, **ACM DocEng
  2004**, DOI 10.1145/1030397.1030399. Supplies the PCS/content-tuple formulation
  everything downstream uses. Known blind spot both Spork and Mergiraf had to patch:
  *"the lack of conflict in [delete/modify] is a known issue of the 3DM merge
  algorithm"* ([spork#529](https://github.com/ASSERT-KTH/spork/issues/529)).

### github/semantic — the negative evidence, read carefully

<https://github.com/github/semantic>. Haskell, tree-sitter-derived, 9,045 stars.
**Archived 1 April 2025**, last commit `2025-04-01`, "Merge pull request #751 from
github/end-of-life". README: *"NOTE: This repository is no longer supported or
updated by GitHub. If you wish to continue to develop this code yourself, we
recommend you fork it."*

⚠ **GitHub never published a reason.** No blog post, no post-mortem. What the record
*does* show: it was effectively dead by late 2021, and production code navigation
moved to **stack-graphs** (tree-sitter + a declarative name-binding DSL, no build
step), announced 9 Dec 2021,
<https://github.blog/open-source/introducing-stack-graphs/>. The team's own writing
(Thomson & Clem, *"Static Analysis at GitHub"*, ACM Queue 19(4), 2021, DOI
10.1145/3487019.3487022; Thomson et al., ICFP 2022,
[arXiv:2206.09206](https://arxiv.org/abs/2206.09206)) describes Semantic as shipped
for *"vulnerability analysis and code navigation"* — **navigation survived, diffing
did not**.

⚠ **I found no evidence GitHub ever shipped a user-facing semantic diff.** `semantic
diff` existed only as a CLI subcommand. Treat "GitHub demoed semantic diff then
killed it" as unverified.

The honest reading is still damning enough: ~6 years, a dedicated team, a
purpose-built Haskell stack, and **the diffing half never reached users.** That is a
real datapoint about semantic-diff economics at a company with unlimited resources.

### Adjacent, briefly

- **diffsitter** — tree-sitter AST difftool, diff only.
- **git-mediate** (Peaker/yairchu) — *not* structured: shows the two diffs a conflict
  implies and clears the markers once applied. A cheap UX win, no parsing.
- ⚠ **Automerge (CRDT) ≠ AutoMerge/automerge-ptm** (Zhu & He's Java structured-merge
  research tool, Spork's baseline). Easy citation trap.
- **DeltaXML** (<https://www.deltaxml.com/products/merge/>) — commercial, 3-way and
  N-way XML merge, ordered *and* unordered trees. The most mature commercial answer
  for non-code trees.
- **Oxygen XML** merges inside ZIP containers (ODF, OOXML) by unzipping and diffing
  member XML — the standard practical trick for office documents.
- ⚠ Beyond Compare / Araxis ship data-aware *comparison* rules, but their 3-way merge
  remains text-based. Treat "structured merge" claims there as marketing.

---

## 3. THE DEPLOYMENT REALITY — tested, not reasoned

`experiments/D3-merge-driver-deployment/` — a merge driver that logs every
invocation and writes an unmistakable banner, wired via `.gitattributes`.

### 3.1 Which git operations invoke a custom merge driver

`run.sh`, `run2.sh`. Overlapping edits, so a clean result **proves** the driver ran.

| Operation | Driver runs? |
|---|---|
| `git merge` | ✅ |
| `git rebase` (default `--merge` backend) | ✅ |
| `git rebase --apply` (old backend) | ✅ |
| `git cherry-pick` | ✅ |
| `git revert` | ✅ |
| `git stash pop` | ✅ |
| `git pull --rebase` | ✅ |
| `git pull` (merge) | ✅ |
| `git am -3` | ✅ |
| `git merge-tree --write-tree` (**non-bare** repo) | ✅ |
| `git merge-tree --write-tree` (**bare** repo) | ❌ **see 3.3** |
| `git merge-file` (plumbing) | ❌ by design — takes files, not paths |

So **client-side coverage is excellent**. Every porcelain operation a user runs
honours the driver. That is the good news, and it is the *only* good news.

### 3.2 The config split — the decisive fact

```
.gitattributes:      f.txt merge=probe        <- TRACKED FILE, ships with the repo
.git/config:         [merge "probe"]
                       driver = /path/to/tool %O %A %B %L %P   <- LOCAL ONLY
```

Verified in `run2.sh` section D: after `git clone`, `merge.probe.driver` is
`<UNSET>` while `.gitattributes` arrives intact. `.git/config` is **never**
transferred by clone, fetch or push. **The repo can say which driver to use; it can
never supply it.**

There are three states a cloner can be in (`run3.sh`), and all three are bad:

| State | `git merge` | `git merge-tree` |
|---|---|---|
| **1. Nothing configured** (fresh clone, tool not installed) | **Silently falls back to built-in text merge** → conflict markers | same |
| **2. `merge.probe.name` set, `.driver` missing** (half-configured) | **`fatal: custom merge driver probe lacks command line.`** — merge refuses entirely | same fatal |
| **3. Driver set, binary missing from PATH** | prints `not found`, then falls back to text merge → conflict | same |

**Is the colleague's failure silent corruption or clean failure?** On the case I
tested (overlapping edits) it is a **clean failure**: markers, `UU`, exit 1. But
that is the *lucky* case. **The real hazard is the silent downgrade**: when the
driver is absent, git does not refuse — it does a *line* merge. Any edit pair the
line merge happens to resolve cleanly is merged with **no driver, no marker, no
warning, and no record that the intended merge policy never ran.** Every silent-wrong
case in §5 is exactly what a colleague-without-the-tool gets.

That asymmetry is the deployment flaw: the failure mode is not "it breaks", it is
**"it quietly stops being the product you designed."**

### 3.3 Bare repositories — the finding I did not expect

`run4.sh`. A real bare "server" repo, pushed to from a normal repo, `.gitattributes`
committed in the tree.

```
$ git rev-parse --is-bare-repository
true
$ git cat-file -p main:.gitattributes
f.txt merge=probe                       <- it IS in the tree
$ git check-attr merge f.txt
f.txt: merge: unspecified               <- but git does NOT see it
```

**Consequences, all verified:**

- (a) Forge without the driver configured: driver not run, conflict. Expected.
- (b) **Forge WITH `merge.probe.driver` set in the server's own git config: driver
  still NOT run.** The attribute is never resolved, so the driver is never selected.
- (c) Populating an index with `git read-tree main` does **not** help —
  `check-attr` still reports `unspecified`.
- (d) The **only** thing that works is writing the attribute into the server's
  `$GIT_DIR/info/attributes` — a per-repository, server-side, sysadmin action.
- (e) Control: a **non-bare** clone of the same server, same config → driver runs.

So a server-side custom merge needs **two** independent pieces of local setup that
the repository cannot supply: the driver command in config, **and** the attribute in
`info/attributes`. Neither travels with a clone or a push.

⚠ Caveat, stated honestly: forges that merge by materialising a **temporary
worktree** (Gitea/Forgejo shell out to real `git` in a temp worktree) would see the
checked-out `.gitattributes`, so for them only requirement (1) binds. Forges using
bare `merge-tree` or libgit2 hit both.

### 3.4 What the forges actually say and do

- **GitLab** — the only forge that documents this explicitly, and it confirms the
  analysis exactly. <https://docs.gitlab.com/user/project/repository/files/git_attributes/>:
  **"Custom merge drivers are not supported on GitLab.com."** Self-Managed and
  Dedicated *can* have them — by an **administrator** editing `/etc/gitlab/gitlab.rb`
  and adding `merge.foo.driver` under `gitaly['configuration'] → git.config` (or
  `[[git.config]]` in `gitaly.toml`). That is instance-wide sysadmin configuration,
  exactly as predicted. A repository still cannot ship it.
- **libgit2** — I read `src/libgit2/merge_driver.c`. It registers exactly **three**
  built-in drivers: **`text`, `union`, `binary`**. It **never reads
  `merge.<name>.driver` from git config**; it only reads the `merge` attribute via
  `git_attr_get()`. An unregistered driver name falls back to a `"*"` wildcard and
  then errors — *"cannot use an unregistered filter"* — so the merge **fails** rather
  than silently degrading. Custom drivers exist only via the C API
  `git_merge_driver_register`, i.e. the **host application** must compile them in.
  Any forge on libgit2 therefore cannot honour a repo's merge driver, ever.
- **GitHub** — documents essentially nothing here. The "Customizing how changed files
  appear on GitHub" page covers only `linguist-generated`. **Merge drivers are not
  mentioned at all.** ⚠ I found no affirmative GitHub statement either way; the
  absence plus the config-scope argument is the evidence.
- **Git LFS is the instructive counterexample.** LFS is a `.gitattributes`
  `filter=lfs` clean/smudge filter that forges *do* support — because every forge
  **special-cased it in product code**, with dedicated storage, an API and UI. That
  is the price of getting one filter honoured server-side: a bespoke integration
  negotiated with every vendor. It is not a path available to a new file format.

**Verdict: depending on a custom merge driver for correctness is a fatal deployment
flaw.** It works on the machine of anyone who installs and configures it, and
nowhere else — not on GitHub, not on GitLab.com, not in any bare-repo merge, and not
for the colleague who just cloned.

### 3.5 The two merge behaviours that ARE repo-portable

Only attributes handled by git's **built-ins** need no local config, and there are
just three (`text`, `union`, `binary`) — the same three libgit2 implements:

- **`merge=union`** — concatenates both sides. Always "clean", never a marker.
  Verified: two branches appending different rows to a CSV produced
  `3,Dave` / `3,Carol` — two records sharing an id, **no marker anywhere**. This is
  a silent-wrong generator (§5, S10) that ships in `.gitattributes`. Do not reach
  for it as a table merge strategy.
- **`-merge` / `merge=binary`** — refuse to merge. Verified: `warning: Cannot merge
  binary files`, ours kept verbatim, file marked `UU`, **no markers injected**.
  **This is the one repo-portable primitive worth having**, because it converts every
  concurrent edit into an honest, well-formed, tool-resolvable conflict instead of a
  corrupted file. See §4.

### 3.6 Clean/smudge filter coverage — measured

`run2.sh` section F. Which operations run the filters:

| Operation | clean | smudge |
|---|---|---|
| `git checkout` / `restore` | — | ✅ |
| `git add` | ✅ | — |
| `git diff` (worktree vs HEAD) | ✅ | — |
| `git stash push` / `pop` | ✅ | ✅ |
| **`git archive`** | — | ✅ |
| **`git log -p`** | ❌ | ❌ |
| **`git show HEAD`** | ❌ | ❌ |
| **`git cat-file -p`** | ❌ | ❌ |
| **`git grep`** | ❌ | ❌ |

The split is coherent once you see it: filters operate between worktree and blob, so
anything comparing **two stored blobs** (`log -p`, `show`, `cat-file`) works in
*clean space* and never smudges. Practical consequences:

- **Every diff you can see is in *clean space*.** `log -p`, `show` and `diff HEAD~1
  HEAD` compare stored blobs directly (no filter); `git diff` against the worktree
  runs the *clean* filter first. Verified: with a smudge filter prefixing
  `SMUDGED:`, the worktree reads `SMUDGED:alpha` while **every** diff shows plain
  `alpha`. So a smudge filter's output is a form the user sees in the editor and
  **can never see in any diff or in history** — which, for a product whose premise is
  "every save is a reviewable commit", is a serious asymmetry.
- `git grep` searches stored blobs — search misses anything the smudge filter adds.
- `git archive` **does** smudge, so release tarballs contain the smudged form while
  the repo contains the clean form. Verified both ways here.
- The diff-side analogue, `diff.<driver>.textconv`, is **also local config only** —
  same portability problem as merge drivers, same server-side blindness.

---

## 4. Conflict representation

### 4.1 What git actually produces — tested on six formats

`experiments/D3-conflict-wellformedness/run.sh`: one conflicting edit per file,
then attempt to parse.

| File | Parses after conflict? |
|---|---|
| `data.json` | ❌ `JSONDecodeError: Expecting property name… line 7` (and `jq: Invalid numeric literal`) |
| `pic.svg` | ❌ `ParseError: not well-formed (invalid token): line 3` |
| `sheet.fods` | ❌ `ParseError: not well-formed (invalid token): line 5` |
| `conf.yaml` | ❌ pyyaml scanner error |
| `post.md` (YAML frontmatter) | ❌ frontmatter fails to parse |
| **`data.csv`** | ⚠️ **"parses OK, 8 rows"** — *worse than failing* |

`merge.conflictStyle=diff3` and `zdiff3` change nothing: they add a `|||||||` base
section, and JSON still fails at the same line. **There is no git conflict style that
preserves well-formedness.**

**CSV and Markdown are the dangerous pair, because they do not fail.** A conflicted
CSV parses as a table with mixed row widths — `['<<<<<<< HEAD']` and `['=======']`
become one-column data rows. I loaded one into **LibreOffice headless**:

```
id,name,dept,salary
1,Alice,Eng,100
<<<<<<< HEAD,,,
2,Bob,Support,80
Err:510,,,          <- "=======" parsed as a formula
2,Bob,Marketing,95
>>>>>>> A,,,
3,Carol,Eng,110
```

**No error dialog. No warning.** The user gets a spreadsheet with three junk rows
and one `Err:510` cell, and nothing anywhere says "this is a merge conflict."

Markdown is the same class: a conflicted `.md` still renders, and worse, the markers
are *meaningful markdown*. In test S13 the `=======` line immediately above a `---`
line was parsed as a **setext H2 heading titled `=======`**. Conflict markers in
Markdown are not visible damage, they are silently-rendered content.

### 4.2 daff's in-band conflict — the one representation that stays valid

This is the answer to the brief's "do any formats have in-band conflict
representation that stays valid?" — **yes, and it is shipping.** daff's D4 result:

```
id,name,qty
1,a,10
2,b,((( 20 ))) 999 /// 222
3,c,30
```

`Merger.hx` writes `base + sep + ours + sep + theirs` into **the conflicted cell
only**, with `conflict_sep` defaulting to `!->` and the separator *grown* (prepend
characters until it does not occur in the data). The file is **still a valid 3-column
CSV** — I re-parsed it: `row widths: Counter({3: 4})`. And git still marks it `UU`,
so the conflict is not lost.

Properties worth naming, because they are the design target:
1. **Well-formed** — the structured editor can still open the document.
2. **Localised** — the conflict is confined to one cell, not a line range that
   swallows unrelated rows.
3. **Complete** — base, ours and theirs are all present, so a UI can offer all three.
4. **Detectable** — a distinguishable sentinel a parser can find.
5. **Still a git conflict** — `UU` in the index; the commit cannot happen by accident.

The failure mode of in-band representation is the mirror image: a conflict marker is
now *valid data*, so a tool that does not know the convention will happily commit it,
render it, or sum it. That argues for pairing in-band representation with a
**pre-commit validator** that refuses to commit any file containing the sentinel —
and for choosing a sentinel that is loud in a rendered view.

### 4.3 Recommendation

Detail on jj / Pijul / Dolt / Fossil and the WYSIWYG-product survey is in §7, from a
parallel investigation. The design recommendation that follows from what I measured:

**Never let git's own conflict markers touch a structured file.** For every
structured format in the substrate, set `-merge` in `.gitattributes` — the one
repo-portable primitive that produces an honest, well-formed conflict with the file
left intact and marked `UU`. Then resolve conflicts in the application, out of band,
where you can show the user base/ours/theirs in the document's own idiom.

That inverts the usual instinct — it *gives up* on git auto-merging these files —
but it is the only policy that behaves **identically for every collaborator**,
whether or not they installed anything, and on every server. The custom merge driver
then becomes a *local accelerator* that improves the experience where it is
installed, never a correctness dependency. That is the only role §3 permits it to
have.

---

## 5. Silent-wrong-merge catalogue

`experiments/D3-silent-wrong/`. **Clean merge, exit 0, no marker, wrong document.**
Verified with real parsers, and where relevant with LibreOffice.

### S1b — CSV with A1 formulas (the RESEARCH.md case, extended)

Two branches each insert one row, far apart, each extending `=SUM(D2:D7)` to
`=SUM(D2:D8)`. **git: `Merge made by the 'ort' strategy`, exit 0.**

```
item,qty,price,total          intended   computed
a,1,100,=B2*C2                     100        100
NEW-B,10,100,=B3*C3               1000       1000
b,2,100,=B3*C3                     200       1000   <- WRONG
c,3,100,=B4*C4                     300        200   <- WRONG
d,4,100,=B5*C5                     400        300   <- WRONG
e,5,100,=B6*C6                     500        400   <- WRONG
NEW-A,20,100,=B7*C7               2000        500   <- WRONG
f,6,100,=B7*C7                     600        500   <- WRONG
TOTAL,,,=SUM(D2:D8)               5100       3500   <- WRONG
```

**Six of eight rows wrong; total 31% low.** Confirmed independently by
**LibreOffice**, which evaluated the merged file to `TOTAL = 3500`. Note this is
strictly worse than the prior 480-vs-660 result: not only the total, but most
individual rows are wrong, and two rows now share the identical formula `=B3*C3`.

**daff does not fix it** (§2, D5) — same 3500.

### S5 / M1 — JSON: concurrent array inserts

Both branches add a user and bump `"count"`. **Clean merge, 100% of 200 randomised
trials silently wrong** (`experiments/D3-ceiling/sweep2.py`):
duplicate `id: 6`, and `len(users) = 7` while `"seats" = 6`. The file parses
perfectly. **mergiraf produces the same wrong answer.**

### S6 / M2 — YAML: same key added at two places

Both add `timeout:` at different positions. **Clean merge, 100% silently wrong**
across 200 trials. pyyaml parses it and reports `timeout = 90` — **one writer's value
is silently discarded, last-definition-wins.** This is the classic
duplicate-key-is-legal-YAML trap arriving via merge. ✅ **mergiraf catches this one.**

### S12 / V1 — Markdown: duplicate link-reference definition

A sorted link-definition block; each author inserts `[api]:` alphabetically near
their own change. **Clean merge, 100% silently wrong** across 200 trials. Per
CommonMark the **first** definition wins, so one author's link target is silently
dead and *both* `[api]` references point at v1. ❌ **mergiraf also merges this
cleanly** despite declaring `link_reference_definition` commutative — the commutative
rule concatenates, it does not check label uniqueness.

### S15 — JSON: rename a key while the other side adds a reader of it

A renames `"database"` → `"primary_db"`; B adds `"replica_of": "database"`. **Clean
merge.** Parses fine, and now contains a dangling reference to a key that no longer
exists. No error at any layer. The general class: **any cross-reference between two
regions of a file that the two authors touch separately.**

### S10 — `merge=union` on CSV

The one repo-portable non-default driver. Both branches append a row. **Clean merge,
100% wrong** across 200 trials: two different records share `id`. No marker.

### S9 — SVG: viewBox change vs. new geometry

A rescales `viewBox` 100×100 → 1000×1000 and updates every coordinate; B adds a
circle in the old coordinate space. The result is valid XML but the new element
renders at 8% of intended position — effectively invisible. (In my run git happened
to conflict; when the two edits are further apart it merges clean. The general class
is **coordinate-space drift**, and it is unfixable by any syntactic merger, because
both sides are individually valid and there is no syntactic evidence of the coupling.)

### S3 / S8 — duplicate identity: Markdown `[2]` labels, SVG `id="grad1"`

Both conflicted in my runs (the two edits landed adjacent), but the *class* is the
same as S12: two authors independently mint the same identifier. When the insertions
are far enough apart the merge is clean and one definition silently wins. SVG is
worst here because duplicate `id` is not an error — renderers resolve `url(#grad1)`
to the first, so **both** authors' shapes get the *first* author's colour.

### The taxonomy this catalogue reveals

Every silent-wrong case is one of exactly **three** couplings, and none is visible to
a syntactic merger:

| Class | Examples | Why no merger catches it |
|---|---|---|
| **Positional reference** | A1 formulas, `viewBox` coordinates, `#This Row`-less spreadsheets | the reference is *derived from position*; both sides are individually correct; correctness is a property of the final layout, which neither side saw |
| **Namespace collision** | duplicate JSON `id`, YAML key, Markdown `[label]`, SVG `id` | uniqueness is an *application* invariant, not a syntactic one. mergiraf catches exactly the cases where the invariant happens to coincide with a syntax node's identity (object keys) and misses the rest |
| **Cross-region invariant** | `count` vs array length, TOC vs headings, `replica_of` vs renamed key | the two coupled regions are edited by *different* authors, so no single diff contains both halves |

**This is the load-bearing conclusion of §5.** A structural merger raises the floor —
it turns false conflicts into correct merges and *some* silent-wrongs into honest
conflicts — but it can only enforce invariants that are expressible in the *grammar*.
Positional references and application-level uniqueness are not. **Those must be
designed out of the file format, not merged around.**

---

## 6. The honest ceiling — measured

`experiments/D3-ceiling/sweep.py` and `sweep2.py`. Every trial is constructed so the
two authors' edits target **disjoint structural units** and therefore commute: there
is a unique correct merge and **zero legitimate conflicts by construction**. So every
conflict git reports is a **false conflict**, and every clean-but-different result is
a **silent wrong merge**.

### Sweep 1 — plain git, 200 trials per row

| Scenario | clean-correct | false conflict | silent wrong |
|---|---|---|---|
| CSV, no formulas, **1** edit each, 20 rows | **94.0%** | 6.0% | 0.0% |
| CSV, no formulas, **3** edits each | 55.5% | **44.5%** | 0.0% |
| CSV, **A1 formulas**, 1 edit each | 28.0% | **72.0%** | 0.0% |
| CSV, **A1 formulas**, 3 edits each | 6.5% | **93.5%** | 0.0% |
| Markdown, **1** section op each, 12 sections | **96.5%** | 3.5% | 0.0% |
| Markdown, **3** section ops each | 75.5% | 24.5% | 0.0% |

### Sweep 2 — scenarios whose failure mode is silent, 200 trials each

| Scenario | clean-correct | false conflict | **silent wrong** |
|---|---|---|---|
| JSON array insert + counter field | 0% | 0% | **100%** |
| YAML: same key added at two places | 0% | 0% | **100%** |
| Markdown: link-definition label collision | 0% | 0% | **100%** |
| CSV under `merge=union` | 0% | 0% | **100%** |
| Markdown: auto-numbered sections | 0% | **100%** | 0% |
| SVG: concurrent `<defs>` id | 0% | **100%** | 0% |

⚠ **Read these two tables carefully — the 0%/100% is not a probability.** These
outcomes are **shape-determined**: for a given *class* of edit pair, the result is
deterministic. The randomisation varies positions and sizes, not the outcome. So the
right reading is *"this edit class always merges silently wrong"*, **not** *"100% of
JSON merges are wrong."*

### The synthesis

Three regimes, and which one you are in is decided by the **file format**, not the
merge tool:

1. **Light concurrency on prose or keyless tables** (one edit each, disjoint
   regions): git alone is **94–96.5% correct**. Genuinely fine. This is most real
   editing, and it is why git-backed documents work at all.
2. **Realistic concurrency** (3 edits each): **24–45% false conflicts** on plain
   markdown/CSV. Every one of these is a conflict a user must resolve by hand that a
   structural merger would have resolved correctly. daff fixed **every** table case I
   threw at it (D1–D3); mergiraf fixed the JSON one (V2). **This is where structural
   merge earns its keep — and it is a UX win, not a correctness win.**
3. **Positional references, or any application invariant** (A1 formulas, unique ids,
   counters, cross-references): **72–93.5% false conflicts** *or* **100% silent
   wrong**, depending only on whether the writing tool renumbers. And this regime is
   **not rescued by any merge tool** — daff and mergiraf both fail it.

That third regime is the pincer, and it is the sharpest thing in this document.
**With A1 references in CSV you must choose between two failure modes and cannot
escape both:**

- If the writing app **renumbers correctly** on insert (as a real spreadsheet does),
  a single row insert rewrites every formula below it — an enormous diff — so
  concurrent edits collide almost always: **72% false conflicts at one edit each,
  93.5% at three.** Correct, but unusable.
- If the writing app **does not renumber**, edits merge cleanly and the numbers are
  wrong (S1b: 3500 vs 5100, confirmed by LibreOffice).

**Named-column addressing is not an optimisation. It is what removes the third
regime, and no merge technology substitutes for it.** RESEARCH.md §3 reached this
from the merge-diff argument; D5 shows that even a *correct cell-level table merge*
does not rescue A1 — which makes the case considerably stronger than it was.

### The answer to "what fraction"

For a realistic mixed workload on **well-designed formats** (named columns, no
positional references, no hand-maintained cross-file invariants):

- **~90–95% auto-merges correctly** with git alone at light concurrency; a structural
  driver pushes the remainder of the *false-conflict* bucket down substantially
  (daff resolved 3/3 of my table false-conflicts; mergiraf 1/1 of the JSON one).
- **~5–25% conflicts legitimately or falsely**, rising steeply with concurrency and
  with the number of edits per author. Structural merge converts most of the *false*
  share into correct merges.
- **Silent-wrong is not a percentage — it is a property of the format.** With
  positional references or unenforced uniqueness invariants it approaches **100% for
  the affected edit class**. Remove those from the format and it approaches **0**.

**That is the honest ceiling: the silent-wrong rate is a design variable, not a
measurement.** You do not reduce it with a better merge algorithm. You reduce it by
choosing formats where the invariants that can break are the ones the grammar can
enforce — and by making the remaining ones fail *loudly and locally*, as RESEARCH.md
§3's "a reference to a missing column must fail loudly" already argues.

---

## 7. How other systems represent conflicts

### 7.1 Jujutsu — solves storage, **not** well-formedness

jj replaces one-tree-per-commit with *"an ordered list of tree objects linked from
the commit… There will always be an odd number of trees… If the commit has trees
A, B, C, D, and E it means that the contents should be calculated as **A+(C−B)+(E−D)**"*
([technical/conflicts.md](https://github.com/jj-vcs/jj/blob/main/docs/technical/conflicts.md)).
A 3-way merge is `A+(C−B)`; conflicts nest by substitution and **simplify by
cancellation** — rebasing conflicted `C+(B−A)` onto D gives `D+((C+(B−A))−C)` which
simplifies to `D+(B−A)`. That algebra is what makes conflicts committable and
rebasable, and it drives the **auto-rebase** property: resolve once, descendants
re-derive, *"which removes the need for things like `git rebase/merge/cherry-pick/etc
--continue`."*

On the Git backend, conflicted commits appear as `.jjconflict-base-*/` and
`.jjconflict-side-*/` root directories whose *"purpose… is only to prevent GC of the
relevant trees; the authoritative information is in a non-standard `jj:trees` commit
header."*

**But the brief's hypothesis is correct, and I can now state it flatly:**
[docs/conflicts.md](https://github.com/jj-vcs/jj/blob/main/docs/conflicts.md) —
*"Conflicts are 'materialized' using **conflict markers** in various contexts. For
example, when you run `jj new` or `jj edit` on a commit with a conflict, it will be
materialized in the working copy."* The default `diff` style writes `<<<<<<<`,
`%%%%%%%`, `+++++++`, `>>>>>>>` into the file body; `ui.conflict-marker-style` offers
`diff` / `snapshot` / `git`, all of which inject markers. jj even *escalates* marker
length (to 15 characters) when file content might be confused for a marker — and the
open design discussion is literally
[#3975 "FR: Materialize files with conflict markers (or any files) in a way that can
be parsed"](https://github.com/jj-vcs/jj/issues/3975).

**So jj gives you conflict *storage and propagation*, and hands the user exactly the
same syntactically broken file git does.** It does not help the structured-editor
problem at all.

**And jj cannot run a merge driver.** `git-compatibility.md` states verbatim:
**".gitattributes: No."** The feature request exists and is empty:
[jj-vcs/jj#8071 "FR: Support using merge-drivers configured in gitattributes"](https://github.com/jj-vcs/jj/issues/8071)
(opened 2025-11-19). jj has only interactive `ui.merge-editor` / `[merge-tools.*]`
invoked by `jj resolve` — no automatic per-path driver. **Adding jj to the stack
*removes* the one deployment path a custom merge driver had.**

### 7.2 Pijul, Darcs, Fossil — same verdict

- **Pijul** models the repo as a DAG of lines; a conflict is a *state of the graph*
  (two alive vertices with no path between them, or opposite-direction paths, or
  zombies), never an error. *"Patches can even be applied to a conflicting
  repository, leaving the conflict resolution for later"*
  ([theory](https://pijul.org/manual/theory.html),
  [conflicts](https://pijul.org/manual/conflicts.html)). **Output to the file is
  still markers** — 32-character runs. Sound storage, broken working copy.
- **Darcs** encodes conflicts in patch theory via **conflictors**
  ([darcs.net/Theory/Conflictors](https://darcs.net/Theory/Conflictors)) — the Darcs2
  fix for Darcs1's exponential merge. Same outcome in the file.
- **Fossil** is conventional in-band but with the most self-describing markers of any
  VCS (`src/merge3.c`): `<<<<<<< BEGIN MERGE CONFLICT: local copy shown first`,
  `####### SUGGESTED CONFLICT RESOLUTION follows`, `||||||| COMMON ANCESTOR content
  follows`, `======= MERGED IN content follows`, `>>>>>>> END MERGE CONFLICT`. Better
  for humans; equally fatal to a parser.

**Every VCS that "solves" conflicts solves storage and propagation, and all of them
still hand the user a syntactically broken file.** There is no prior art to copy on
the well-formedness problem from the VCS side.

### 7.3 Dolt — the model to copy

Cell-level, and explicitly contrasted with git: *"conflicts are detected on a
cell-level. If two operations modify the same row, column pair to be different
values, a conflict is detected"* and *"**Unlike Git's conflict markers (`<<<` and
`>>>`), Dolt conflicts are stored in the `dolt_conflicts` set of tables.**"*
([concepts/dolt/git/conflicts](https://www.dolthub.com/docs/concepts/dolt/git/conflicts/))

Schema ([dolt-system-tables](https://www.dolthub.com/docs/sql-reference/version-control/dolt-system-tables)):
`dolt_conflicts(table text, num_conflicts bigint unsigned)`; and per table,
`dolt_conflicts_$TABLENAME` with `from_root_ish`, `base_<col>…`, `our_<col>…`,
`our_diff_type`, `their_<col>…`, `their_diff_type`, `dolt_conflict_id`, where
`*_diff_type ∈ {added, modified, removed}`. Separately
`dolt_schema_conflicts(table_name, description, base_schema, our_schema,
their_schema)` and `dolt_constraint_violations_$TABLENAME` with
`violation_type enum('foreign key','unique index','check constraint','not null')`
— **a merge can be conflict-free yet blocked on an invariant violation**, which is
precisely the §5 "namespace collision / cross-region invariant" category made
first-class. Resolution: `dolt conflicts resolve --ours|--theirs`, or UPDATE the row
and DELETE from the conflicts table.
⚠ Keyless-table cardinality column names unverified.

**The property that matters: the table never stops being a valid table.** Any SQL
client can open the database mid-conflict. That is the design target.

### 7.4 In-band representations that stay valid

- **`merge=union`** — [gitattributes(5)](https://git-scm.com/docs/gitattributes):
  *"take lines from both versions, instead of leaving conflict markers. This tends to
  leave the added lines in the resulting file in random order and the user should
  verify the result."* Preserves well-formedness at the cost of silent semantic
  garbage — measured at 100% wrong for the CSV append case (§5, S10).
- **`-merge` / `merge=binary`** — *"Take the version from the current branch as the
  tentative merge result, and declare that the merge has conflicts."* The conflict is
  recorded **only in the index** (stages 1/2/3, visible via `git ls-files -u`); the
  file is left clean. **This is the closest thing git has to out-of-band conflict
  representation, it needs no local config, and it ships in `.gitattributes`.**
- **daff's cell encoding** — measured in §4.2. Valid CSV, localised, carries all
  three versions.
- **Automerge** ([conflicts](https://automerge.org/docs/reference/documents/conflicts/))
  — the document is *always* valid; one value wins deterministically and the losers
  survive in a sidecar: `Automerge.getConflicts(doc, "x") // {'1@01234567': 1,
  '1@89abcdef': 2}` — *"the other values are not lost. They are merely relegated to a
  conflicts object."* The JSON analogue of Dolt's model.
- **Peritext** ([Ink & Switch](https://www.inkandswitch.com/peritext/)) — always a
  valid rich-text document; mutually exclusive marks resolve last-writer-wins, and
  the authors gesture at exactly the UI we need: *"we could also expose the
  conflicting value to the user interface—for example, the editor could show an
  annotation noting that a conflict had occurred, asking a human to review the merged
  result."*
- ⚠ **No standardized CSV or JSON in-band conflict convention exists.** Flagged as a
  genuine gap rather than a search failure, but confidence is lower here than
  elsewhere (search budget was exhausted).

### 7.5 WYSIWYG conflict presentation — has anyone done it well?

- **Microsoft Word is the strongest existing answer**, and its model is
  *conflicts-as-tracked-changes*. The object model is explicit:
  *"Represents a conflicting edit in a co-authored document. The type of a
  **Conflict** object is specified by the `WdRevisionType` enumeration… When the user
  performs an explicit document save, Word will enter **Conflict Resolution mode** if
  there are conflicts"* ([Word.Conflict](https://learn.microsoft.com/en-us/office/vba/api/word.conflict),
  `ActiveDocument.CoAuthoring.Conflicts`). **Conflicts are *revisions*** — the same
  rendering machinery as Track Changes — so the document stays a valid document and
  the conflict is an *annotation layer*. ⚠ Exact ribbon strings unverified.
  **This is the answer to "how does a WYSIWYG editor present a conflict to a
  non-developer": you reuse the affordance they already understand — tracked changes
  — and you never show them a marker.**
- **Figma** — visual, but coarse. [Merge branch into main file](https://help.figma.com/hc/en-us/articles/5691189138839-Merge-branch-into-main-file)
  has a **Resolve conflicts** step with side-by-side (*"The left side shows what your
  object looks like before your changes (the main file). The right side shows what
  that object will look like after the merge"*) or overlay/opacity review. But:
  *"At the moment, you need to merge all updates from the branch into the main file.
  There isn't a way to select or merge specific changes."* User reports match —
  "all changes bunched into a single conflict, all-or-nothing"
  ([forum 29613](https://forum.figma.com/t/bug-all-changes-bunched-into-a-single-conflict-all-or-nothing-branch-merging/29613)),
  "Resolve conflicts is erasing all the changes in the branch"
  ([forum 7424](https://forum.figma.com/report-a-problem-6/resolve-conflicts-is-erasing-all-the-changes-in-the-branch-7424)).
  **The best-funded canvas tool in the world ships all-or-nothing branch merge.**
  That is the realistic bar for canvas merge, and it is low.
- **Unity SmartMerge / UnityYAMLMerge** — the real shipped structured merge for
  non-code artifacts ([manual](https://docs.unity3d.com/6000.3/Documentation/Manual/SmartMerge.html)):
  merges `.unity` and `.prefab` *"in a semantically correct way"*, wired as
  `[mergetool "unityyamlmerge"] cmd = '<path>' merge -p "$BASE" "$REMOTE" "$LOCAL"
  "$MERGED"`. Modes Off / Premerge / Ask. Note the shape of its failure handling: it
  ships a `mergespecfile.txt` naming a **fallback merge tool** for what it cannot
  resolve — i.e. it degrades to a generic 3-way tool rather than producing a
  structured conflict artifact. Same architecture as mergiraf's line-merge fallback,
  same limitation.
- **Abstract** — git-for-design, *"True version control for Sketch files"* with
  branch/merge/"resolve design conflicts". ⚠ `goabstract.com` no longer resolves;
  `abstract.com` is now an unrelated VC firm. **No dated post-mortem found** — treat
  "shut down, date unknown" as the verified claim. It remains negative evidence that
  the category is hard to sustain, but I cannot cite a cause.
- **GitHub's own web conflict editor** handles only *"simple competing line change
  conflicts"* — it shows raw `<<<<<<<` / `=======` / `>>>>>>>` and asks the user to
  delete them, then **Mark as resolved**
  ([docs](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/addressing-merge-conflicts/resolving-a-merge-conflict-on-github)).
  **No forge presents conflicts structurally.**

### 7.6 The recommendation, stated once

Three findings converge on the same design:

1. Git's markers destroy every structured format, and **no conflict style fixes it**
   (§4.1). CSV and Markdown are worse than the rest because they *don't fail* — they
   silently absorb the markers as content, and LibreOffice opens the result without a
   warning.
2. **No VCS solves this.** jj, Pijul, Darcs and Fossil all materialise markers into
   the working copy; jj additionally cannot run merge drivers at all.
3. The systems that *do* keep the artifact openable — Dolt, Automerge, Word — all use
   the **same shape**: the artifact stays valid, and the conflict lives in a **sidecar
   record** that the native editor renders as an annotation.

**Therefore:**

- **Set `-merge` in `.gitattributes` for every structured file type in the
  substrate.** It is repo-portable, needs zero local config, behaves identically for
  every collaborator and on every server, and produces an honest conflict (`UU` in
  the index, stages 1/2/3 retrievable) **with the file left well-formed**. It is the
  only primitive in git that does this.
- **Resolve conflicts in the application**, reading base/ours/theirs from index
  stages 1/2/3, and present them in the document's own idiom — Word's
  conflicts-as-tracked-changes is the proven affordance for prose; Dolt's conflict
  sidecar is the proven model for tables.
- **Custom merge drivers (mergiraf, daff) are a local accelerator, never a
  correctness dependency.** §3 permits them no other role. Where installed they
  eliminate most false conflicts (daff: 3/3 of my table cases; mergiraf: the JSON
  commutative case) and turn a few silent-wrongs into honest conflicts (YAML
  duplicate keys). Where absent — every server, every fresh clone — the substrate
  must still behave correctly, and `-merge` is what guarantees that.
- **Design the silent-wrong classes out of the formats** (§5): named-column
  addressing instead of A1; no application-level uniqueness invariants the grammar
  cannot enforce; no hand-maintained cross-region invariants (counters, TOCs).
  This is the only lever that actually moves the silent-wrong rate, and §2's D5
  result proves no merge tool substitutes for it.

---

## 8. Reproducing

    experiments/D3-merge-driver-deployment/   run.sh run2.sh run3.sh run4.sh + 4 transcripts
    experiments/D3-conflict-wellformedness/   run.sh + transcript
    experiments/D3-silent-wrong/              run.sh run2.sh evalcsv.py + 2 transcripts
    experiments/D3-ceiling/                   sweep.py sweep2.py + 2 transcripts
    experiments/D3-tools/                     run-daff.sh run-mergiraf.sh + 2 transcripts
                                              (see its README for the two build commands)

Build artifacts (72 MB mergiraf binary, node_modules) were deleted after the runs;
the transcripts are the record.

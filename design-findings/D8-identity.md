# D8 — Sub-artifact identity, anchoring and transclusion

Artifact-level identity is settled elsewhere (minted UUID in frontmatter; version
= blob SHA; change = `change-id` commit header). This file is about the level
below: **blocks, rows, cells, shapes** — thousands per repo, sitting in the
middle of human-readable text.

Experiments: `experiments/D8-identity/`. Corpora: `rust-lang/book` (6,286
commits), `obsidian-help` (2,623), `commonmark-spec` (1,848), cloned as partial
clones and evaluated over real commit history.

---

## 0. The answer, stated first

**Sub-artifact identity is not one problem. It is three problems that have been
conflated, and each has a different correct answer. None of the three is a
minted id in the file.**

| job | question it answers | mechanism | stored in the file? |
|---|---|---|---|
| **correspondence** | "which block in v2 is the same block as this one in v1?" | similarity matching (L3: difflib > 0.5, git's own rename threshold) | **no** |
| **reference** | "what do I write in another artifact to point here?" | a **name the author chose** — heading slug or an explicit region marker | **yes, but only where a human decided to name something** |
| **anchoring** | "where is the span this comment/tracked-change is about?" | W3C quote + prefix/suffix, resolved **two-stage** (block first, then span), with a hard acceptance threshold and loud orphaning below it | **no** |

The OHCO tension dissolves because it rests on a hidden premise. Renear/Mylonas/
Durand prove a document is not a single hierarchy, so comments and tracked
changes must live in a standoff sidecar. That much is right. The hidden premise
is **"a standoff sidecar must point at an identifier."** It need not. It can
point at a quote. Measured below: a two-stage quote anchor resolves arbitrary
sub-block spans across 25 commits of real editing at **92.9% correct, 7.1% loud
refusal, 0.00% silent-wrong** — the exact failure profile invariant I3 demands.
A stored id under stock git does not beat that, because a stored id under stock
git survives **only when the block did not change**, which is precisely the case
an exact-quote match already handles.

**The one-line rule:** a minted sub-file id is the prose form of `col_a7f3`.
RESEARCH.md §3 already rejected exactly this shape of thing for tables —
*"in a plaintext format the file is the UI; `=col_a7f3 * col_9b21` is positional
addressing with the ergonomics removed."* `^7c475260-a227-4869-a31f-cb5f341b6ffe`
is that sentence again, in a document. I2 (nominal addressing) does not merely
tolerate this conclusion; it requires it.

---

## 1. The prosecution: stable sub-file ids ruin plaintext

### 1.1 They are what the substrate's own invariants forbid

I2 says: *names, not places.* A minted id is neither. It is an opaque token that
means nothing to the reader, cannot be typed from memory, cannot be guessed,
carries no information about what it points at, and exists only because a
machine needed a handle. It is a **coordinate with the coordinates hidden**.
Every argument RESEARCH.md makes against `col_a7f3` and for `[@Qty]` transfers
verbatim.

### 1.2 They are a SCATTERED NAMESPACE — the substrate's own known silent-wrong generator

PASS4 established, by reproducing it: *"Scattered namespaces are silent-wrong
generators… CO-LOCATE A NAMESPACE'S BINDINGS."* Two markdown link labels named
`[api]` in distant sections of one file merge cleanly and one author's citation
silently resolves to the other's URL.

Block ids are the worst possible case of that rule: **one binding per block,
scattered across every line of every file.** Git's unit of comparison is
position, so it cannot see a collision between two ids on distant lines.

Reproduced (`e2_controlled.sh`, arm 3): two branches each add a **different new
block**, each minting the id `^a3f91c2b`, in distant parts of the file.

```
3a-id-collision-different-blocks   exit=0 markers=0 occurrences_of_^a3f91c2b=2
```

Clean merge. Two blocks. One id. No marker anywhere.

It is worse than that, because the collision does not even need two people.
`e3_dup.sh`: one author **copy-pastes** an id-bearing paragraph into an appendix
— an ordinary act — and a second author retitles the document far away:

```
merge exit=0
conflict markers: 0
occurrences of ^a3f91c2b: 2
3:The reactor scram threshold is 4.2 sigma above baseline. ^a3f91c2b
33:The reactor scram threshold is 4.2 sigma above baseline. ^a3f91c2b
```

Every reference `[[doc#^a3f91c2b]]` is now ambiguous, silently. Copy-paste is
the single commonest operation in a document editor, and it breaks the
uniqueness invariant that the id's entire value rests on.

### 1.3 Writing an id is a WRITE — so referring to something conflicts with editing it

`e2_controlled.sh`, arm 1, with a control:

```
1a-CONTROL-no-id-write             exit=0 markers=0     Bob rewords a paragraph; Alice adds a paragraph elsewhere
1b-alice-writes-blockid            exit=1 markers=1     identical, except Alice also wrote ^a3f91c2b on Bob's paragraph
```

Alice did not change a word of Bob's paragraph. She linked to it. **The act of
referring turned a clean merge into a conflict.** Stated generally: on-demand id
minting makes *reading and citing* a mutation of the cited artifact, and the
line merger cannot distinguish an id-write from an edit because they are the
same line change.

Concurrent minting is worse (`e1_stock_git_ids.sh`, A1): two people who
independently link to the same paragraph mint two different ids on the same
line and get a conflict whose two sides are *semantically identical*:

```
<<<<<<< HEAD
The reactor scram threshold is 4.2 sigma above baseline. ^a3f91c2b
=======
The reactor scram threshold is 4.2 sigma above baseline. ^7e40dd18
>>>>>>> bob
```

This is unfixable in principle for random ids, and the reason is worth stating
precisely: **the only id two offline clients can mint identically for the same
block, with no coordination, is a content hash — and L3 proved content hashes
are not identity** (two people editing one paragraph produced silent
duplication rather than a conflict). So on-demand minting is inherently
non-convergent. Every non-deterministic scheme (UUIDv4/v7, ULID, NanoID, KSUID,
xid) has this property by construction; deterministic ones are disqualified for
a different reason. There is no third option.

### 1.4 They cost real bytes and real readability

`id_samples.md` — the same sentence, at real id lengths:

```
The reactor scram threshold is 4.2 sigma above baseline.
The reactor scram threshold is 4.2 sigma above baseline. ^7c475260-a227-4869-a31f-cb5f341b6ffe
The reactor scram threshold is 4.2 sigma above baseline. ^01a049a2-7411-7e3e-9fc6-d2767a44c46b
The reactor scram threshold is 4.2 sigma above baseline. ^01K3F9Q7ZPWXWCBYB6WK952SWA
The reactor scram threshold is 4.2 sigma above baseline. ^D0Rx432cUfC1NtksBRcxeEiv0G5
The reactor scram threshold is 4.2 sigma above baseline. ^xht5gmej146s6jr410dd
The reactor scram threshold is 4.2 sigma above baseline. ^4WKMP7nwF9BE-Odfta-5V
The reactor scram threshold is 4.2 sigma above baseline. ^YkmTmePLcMPp
The reactor scram threshold is 4.2 sigma above baseline. ^_wA0olMa
The reactor scram threshold is 4.2 sigma above baseline. ^w46qwx
The reactor scram threshold is 4.2 sigma above baseline. ^scram-threshold
```

Only the last one is readable, and it is the only one that is not a minted id.

Corpus cost if **every** block carries one (measured on the real files):

| corpus | blocks | bytes | +UUIDv4 `^id` | +ULID | +NanoID-21 | +short-8 | +Logseq `id::` line |
|---|---|---|---|---|---|---|---|
| obsidian-help | 5,539 | 720,322 | +29.2% | +21.5% | +17.7% | +7.7% | +33.8% |
| rust-book | 5,955 | 1,212,397 | +18.7% | +13.8% | +11.3% | +4.9% | +21.6% |

A fifth to a third of a prose repo being machine tokens is not a rounding error;
it is the difference between a file a human will edit in any tool and a file
that requires an application.

### 1.5 The short ids that ARE readable are not unique at repo scale

Collision probability of *any* collision among 10^6 sub-artifact ids
(birthday bound, `p ≈ 1 − exp(−n(n−1)/2N)`):

| scheme | bits | p(collision) at 10^6 | expected duplicates |
|---|---|---|---|
| UUIDv4 / NanoID-21 | 122 / 126 | ~1e−25 | 0 |
| ULID (80 random) | 80 | 4.1e−13 | 0 |
| UUIDv7 (74 random) | 74 | 2.6e−11 | 0 |
| NanoID-12 | 72 | 1.1e−10 | 0 |
| NanoID-10 | 60 | 4.3e−7 | 0 |
| **NanoID-8** | 48 | **0.0018** | 0.002 |
| base32 hash-8 | 40 | **0.365** | 0.46 |
| **base62-6 (Obsidian-shaped)** | 36 | **≈1.0** | **8.8** |
| base32 hash-6 | 30 | ≈1.0 | 466 |

**The readability line and the uniqueness line do not meet.** Anything short
enough to sit unobtrusively at the end of a prose line (≤8 chars) is not unique
at 10^6; anything unique at 10^6 (≥12 chars, and honestly ≥21 for comfort) is
visually loud. Obsidian escapes this only because its ids are scoped per-file
and a vault has thousands, not millions, of them — the 1% collision threshold
for a 6-char base36 id is reached at **6,615 ids**.

### 1.6 Where the road leads: the format stops being the format

The tell is that the two systems that took embedded per-block ids furthest both
moved the truth out of the text. And the systems that store ids and *do* keep the
invariant — Word's `w:commentRangeStart w:id`, Google Docs' opaque `anchor` —
can do so **only because they are the sole writer**. ISO/IEC 29500-1 §17.13.4.4
makes the id load-bearing to the point of validity: a `commentRangeStart`
without a matching `commentReference` id renders the document *"non-conformant"*.
Google's own Drive API documentation refuses even that guarantee:

> "Anchors are immutable, and their position relative to the content of a
> document cannot be guaranteed between revisions."
> — https://developers.google.com/workspace/drive/api/guides/manage-comments

A git-backed plaintext substrate is the opposite of a sole writer. `sed`, a
merge, another editor, a coding agent, and GitHub's web editor are all writers,
and none of them will maintain an id invariant. **An invariant you cannot
enforce is not an invariant; it is a bug you have scheduled.**

---

## 2. The defence: they are unavoidable

### 2.1 OHCO says a document is not a tree, so annotations must stand off

DeRose, Durand, Mylonas & Renear (1990) defined text as an *ordered hierarchy of
content objects*. Renear, Mylonas & Durand then refuted their own thesis (1993/
1996): a document has multiple concurrent, overlapping hierarchies. Comments and
tracked changes are the canonical counterexample — a comment's range crosses
paragraph and section boundaries at will, so it cannot be an element of the
document's own tree. It must go in a sidecar, and the sidecar must point back.

That much is correct and this design accepts it. Conflicts already live beside
the artifact (I5). Comments and tracked changes go in the same place.

### 2.2 The pointer has to survive editing, and offsets do not

Standoff markup's classic mechanism is a character offset, and its classic
critique is that offsets require the base text to be **frozen**. The W3C Web
Annotation Data Model says so in the spec itself, about its own
`TextPositionSelector`:

> "The use of this Selector does not require text to be copied from the Source
> document into the Annotation graph, unlike the Text Quote Selector, **but is
> very brittle with regards to changes to the resource.** Any edits or
> dynamically transcluded content may change the selection, and thus it is
> RECOMMENDED that a State be additionally used."
> — https://www.w3.org/TR/annotation-model/ §4.2.5

So position is out. That appears to leave exactly two candidates: a stored id,
or a quote. And the strongest form of the pro-id argument is that
**Phelps & Wilensky — the people who coined "robust locations" — kept a stored
unique id as the first tier of their scheme**, falling back to a tree walk and
then to ~25 characters of context. Nobody credible has proposed context-only.

### 2.3 Names rot; ids do not

A heading slug changes when someone improves the heading. An id does not. That
is the whole case for opacity, and it is the same case Airtable/Notion/Coda make
for opaque field ids — the case RESEARCH.md considered and rejected on the
grounds that it requires a UI layer between bytes and human.

---

## 3. Adjudication, with the measurements

**Provenance.** The raw output of all three anchor scripts is committed beside
them: `experiments/D8-identity/results-anchor.txt` (`anchor_eval.py`),
`results-anchor2.txt` (`anchor_eval2.py`), `results-anchor3.txt`
(`anchor_eval3.py`). Those three files were produced on 2026-09-09, and
`results-e4.txt` (`e4_uniqueness.py`, §3.3) on 2026-09-10, against these
partial clones:

```
rust-book      github.com/rust-lang/book             1500248d8f230566e4ec9f27fcbb8fe9e2898ab1
obsidian-help  github.com/obsidianmd/obsidian-help   327a782e90481268361b5ccccdb0c224b2b13fe6
cmspec         github.com/commonmark/commonmark-spec 3da939428d80f146f270cd1765e4ba462e96bb1b
```

`anchor_eval.py` and `anchor_eval2.py` take `<repo> <pathglob> <gap>` and were
run over all three corpora at gap ∈ {1, 5, 25}. `anchor_eval3.py` takes no
arguments and sweeps its own six arms. `e4_uniqueness.py` takes `<minlen>` and
was run at 20, 40 and 120. **The original pass did not record its corpus
commits**, so the arms below are the 2026-09-09 clone; where that changed a
number, §3.2 and §3.3 say which one and by how much.

### 3.1 Under stock git, a stored id survives exactly when the block is unchanged

`anchor_eval2.py` for the rates below, `anchor_eval.py` for the cross-tabulation
after them — two different samples, and the text says which is which. For each
of hundreds of real (commit_i, commit_j) pairs from `rust-lang/book`, an `^id`
is materialised into every block at commit_i and the author's *real* subsequent
edit is applied by stock `git merge-file` — i.e. a rebase, which is what
actually happens when one person cites a block while
another edits it. Independent oracle: git-style line correspondence (a different
algorithm at a different granularity); blocks the oracle cannot classify
confidently are excluded and reported.

```
### rust-book src/*.md gap=1   oracle-confident anchors=999  (92% of sample)
  COMPUTED (quote+context+fuzzy, nothing in the file)
     correct  99.8%   loud refusal 0.0%   SILENT-WRONG 0.2%
  STORED ^id under stock-git 3-way merge
     correct  97.7%   conflict     2.3%   SILENT-WRONG 0.0%

### rust-book src/*.md gap=5   oracle-confident anchors=849  (74%)
  COMPUTED  correct 99.1%   loud 0.5%   SILENT-WRONG 0.5%
  STORED    correct 88.7%   loud 11.3%  SILENT-WRONG 0.0%

### rust-book src/*.md gap=25  oracle-confident anchors=200  (38%)
  COMPUTED  correct 97.5%   loud 0.5%   SILENT-WRONG 2.0%
  STORED    correct 80.0%   loud 20.0%  SILENT-WRONG 0.0%
```

Every figure in that block reproduced exactly on 2026-09-09, including the
oracle-confident subset sizes (999, 849, 200) and the samples they came from
(1087, 1141, 533) — `results-anchor2.txt`, arms 1–3.

The cross-tabulation is the finding, and it comes from the *other* script.
`anchor_eval2.py` does not print a stored/computed cross-tab; `anchor_eval.py`
does, on its own smaller sample — `results-anchor.txt` arm 1: 37 version-pairs
and 762 block-anchors, against `anchor_eval2.py`'s 44 pairs and 999
oracle-confident anchors of 1087. Of those **762** blocks: `SURVIVED` = 701,
`EXACT` = 651, `SURVIVED/EXACT` = 649 and `CONFLICT/EXACT` = 2. (This section
previously attributed the last two of those to the 999-block subset, which
never produced them; 701 and 651 are stated here for the first time.) **The
stored id survives if and only if the block's bytes did not change** — which is
exactly the condition under which an exact-quote match trivially succeeds.
Under stock git, a stored id and an exact-quote anchor have *the same domain of
success*. The id adds bytes, a namespace to collide in, and a write on the read
path, and buys nothing.

This is not a defect of the experiment; it is a consequence of PASS4/I6. The
line merger is what will actually run (merge drivers are undeployable — GitLab:
*"Custom merge drivers are not supported on GitLab.com"*), and a line merger
cannot carry an identifier through an edit to the line the identifier is on.
**Stored ids need a merge driver to be worth anything, and merge drivers cannot
be deployed.**

The 0.0% silent-wrong column is real and is the id's genuine virtue: it fails
loudly. But it fails loudly *far more often* — 20% of anchors at gap=25 versus
0.5% — and the loud failures are conflicts inside prose files, which is the
worst place in the system to put them.

### 3.2 Computed anchoring's errors are concentrated in low-entropy blocks, not prose

`anchor_eval3.py` classifies every silent-wrong by block type:

```
### rust-book src/*.md gap=5  pairs=47  oracle-confident anchors=849
   block types: code=189 heading=80 html=65 list=55 prose=460
   naive  correct  99.1%   LOUD-refusal   0.5%   SILENT-WRONG  0.47%  (n=4)  by type: code=3 html=1
   hard   correct  97.9%   LOUD-refusal   2.0%   SILENT-WRONG  0.12%  (n=1)  by type: code=1

### rust-book src/*.md gap=25  pairs=19  oracle-confident anchors=200
   block types: code=30 heading=17 html=14 list=15 prose=124
   naive  correct  97.5%   LOUD-refusal   0.5%   SILENT-WRONG  2.00%  (n=4)  by type: code=4
   hard   correct  94.0%   LOUD-refusal   5.0%   SILENT-WRONG  1.00%  (n=2)  by type: code=2

### obsidian-help en/*.md gap=5  pairs=23  oracle-confident anchors=343
   block types: code=10 heading=58 list=35 prose=240
   naive  correct  98.5%   LOUD-refusal   0.9%   SILENT-WRONG  0.58%  (n=2)  by type: list=1 prose=1
   hard   correct  97.7%   LOUD-refusal   2.3%   SILENT-WRONG  0.00%  (n=0)
### obsidian-help en/*.md gap=25: too few (0)

### cmspec *.md gap=5  pairs=6  oracle-confident anchors=73
   block types: list=20 prose=53
   naive  correct 100.0%   LOUD-refusal   0.0%   SILENT-WRONG  0.00%  (n=0)
   hard   correct  94.5%   LOUD-refusal   5.5%   SILENT-WRONG  0.00%  (n=0)

### cmspec *.md gap=25  pairs=3  oracle-confident anchors=56
   block types: code=1 list=18 prose=36 table=1
   naive  correct 100.0%   LOUD-refusal   0.0%   SILENT-WRONG  0.00%  (n=0)
   hard   correct  98.2%   LOUD-refusal   1.8%   SILENT-WRONG  0.00%  (n=0)
```

That is `results-anchor3.txt`, unedited. Two things in it differ from what this
section carried before, and both are recorded rather than absorbed:

- **`cmspec` was measured, not skipped.** `anchor_eval3.py:92` drops any arm
  with fewer than 50 oracle-confident anchors and prints `too few (N)`. The
  earlier one-line `cmspec` summary carried no anchor count, which is
  indistinguishable from a skip. It is a real measurement: 73 anchors at gap=5
  and 56 at gap=25, 0.00% silent-wrong under both policies in both arms. The
  arm that *is* skipped is `obsidian-help` gap=25 — `too few (0)`, which is why
  it never appeared here. Not because the corpus is shallow: 13 of its 176
  `en/*.md` files have the 26 commits the arm needs (deepest 64). The script
  samples 14 files at `seed=7`, and the deepest file that sample drew has 19,
  so gap=25 has no `(C_i, C_j)` pair to evaluate at all.
- **`obsidian-help` gap=5 differs, and the old figures cannot be reconciled
  bucket by bucket.** They were `384 anchors  heading=78 list=90 prose=212` —
  but 78 + 90 + 212 = 380. `anchor_eval3.py` increments `EV` and the `TY:`
  bucket in the same statement, so the buckets always sum to the anchor count.
  The old line is therefore a bad transcription with roughly four anchors of
  some bucket dropped, and a missing `code=4` is as good a guess as no code
  bucket having existed. Which half is corrupt is decidable from the old line's
  own printed rate: 2/384 = 0.52%, which is what it printed, and 2/380 = 0.53%,
  which it did not. So `384` is the real `EV` and the bucket list is the damaged
  half. (The hardened rate cannot arbitrate — 1/384 and 1/380 both round to
  0.26%.) Nothing per-bucket can be compared across the two runs; the totals
  can, because one of them has just been shown to be the printed value. 343
  anchors against 384, and the naive arm's two silent mis-anchors typed
  `list=1 prose=1` rather than `list=2`. The `rust-book` arms are unchanged to
  the digit. The likeliest cause is that the corpus moved
  between the runs — `obsidian-help` is the most actively edited of the three —
  but the original clone's commit was not recorded, so that is an inference and
  not a measurement.

**The denominator, stated exactly.** Summing the `prose=` bucket over the five
arms that produced a measurement:

```
rust-book      gap=5    prose=460
rust-book      gap=25   prose=124
obsidian-help  gap=5    prose=240
cmspec         gap=5    prose= 53
cmspec         gap=25   prose= 36
                        --------
                             913
```

This section previously said **885**, which is that same sum over the original
run's figures — 460 + 124 + 212 + 53 + 36. The 89 that never reconciled were the
two `cmspec` arms, which is what made the missing `cmspec` counts load-bearing
rather than cosmetic. Either number is a count of anchor *evaluations*, not of
distinct blocks: it is five arms over three corpora, and the gap=5 and gap=25
arms of one corpus re-sample the same files.

**And the claim that denominator carried does not survive the re-run.** One of
the naive policy's silent mis-anchors is now typed `prose` — `obsidian-help`,
`en/Obsidian Sync/Version history.md`:

```
'---\naliases:\n  - Sync history\n---'    ->  '## Sync history'
```

That block is YAML frontmatter. `btype()` has no rule for frontmatter, so it
falls through to `prose`. It is a defect in the *classifier*, not a
counterexample to the finding — frontmatter is structured data, which is exactly
the category the paragraph below says the failures concentrate in — but the
harness prints `prose=1`, and what the harness prints is what this section may
claim:

> Across **913 prose-typed anchors in five arms over three corpora, the naive
> policy made one silent mis-anchor and the hardened policy made none.** The one
> naive failure is a YAML frontmatter block the type classifier calls prose.

The by-type breakdown is what carries the finding and it needs no denominator at
all: every other silent-wrong in every arm is a code fence, a raw-HTML block,
or a list item — a table of contents in `rust-book`, a numbered procedure in
`obsidian-help`:

```
'```rust,ignore\nf64::powi(2.0, 3)\n```'          ->  '```rust,ignore\ndimensions.0 * dimensions.1\n```'
'- [An I/O Project](ch12-00-an-io-project.md)'    ->  '- [Concurrency](ch16-00-concurrency.md)'
'```toml\n[dependencies]\n\nrand = "0.3.14"\n```'  ->  '```toml\n[dependencies]\nrand = "0.9.0"\n```'
```

This is not a coincidence, and it unifies the whole design. Those blocks are
low-entropy and near-duplicated *because they are structured data wearing prose
clothing* — and structured data is exactly what this project already addresses
nominally (named columns in L1, named overrides in L4). **Computed anchoring
works precisely where nominal addressing is unavailable (free prose), and fails
precisely where nominal addressing is already mandatory (structure).** The two
mechanisms cover disjoint halves of the substrate with no gap between them.

### 3.3 Is a quote a unique key in real prose? Measured: yes.

`e4_uniqueness.py <minlen>` (`minlen` defaults to 20), on the checked-out
working trees at the three commits pinned in §3 above. The raw output of all
three runs — 20, 40 and 120 — is committed beside the script as
`experiments/D8-identity/results-e4.txt`. The 40 and 120 arms, verbatim from
that file, are the ones this subsection argues from:

```
### rust-book  files=112  blocks>=40ch=4994
type           n   dup in same file   dup anywhere in corpus
code         909         6 ( 0.7%)            14 (  1.5%)
heading      172         0 ( 0.0%)             0 (  0.0%)
html         873       197 (22.6%)           229 ( 26.2%)
list          89         0 ( 0.0%)             0 (  0.0%)
prose       2938         0 ( 0.0%)             0 (  0.0%)
table         13         0 ( 0.0%)             0 (  0.0%)

### obsidian-help  files=176  blocks>=40ch=3662
type           n   dup in same file   dup anywhere in corpus
code         284        22 ( 7.7%)            25 (  8.8%)
heading       67         0 ( 0.0%)             0 (  0.0%)
html           2         0 ( 0.0%)             0 (  0.0%)
list         703         0 ( 0.0%)             0 (  0.0%)
prose       2526        16 ( 0.6%)            48 (  1.9%)
table         80         0 ( 0.0%)             0 (  0.0%)

### cmspec  files=2  blocks>=40ch=42
type           n   dup in same file   dup anywhere in corpus
code           2         0 ( 0.0%)             0 (  0.0%)
list          12         0 ( 0.0%)             0 (  0.0%)
prose         28         0 ( 0.0%)             0 (  0.0%)
```

```
### rust-book  files=112  blocks>=120ch=3195
type           n   dup in same file   dup anywhere in corpus
code         273         2 ( 0.7%)             2 (  0.7%)
html         293        16 ( 5.5%)            17 (  5.8%)
list          81         0 ( 0.0%)             0 (  0.0%)
prose       2535         0 ( 0.0%)             0 (  0.0%)
table         13         0 ( 0.0%)             0 (  0.0%)

### obsidian-help  files=176  blocks>=120ch=2137
type           n   dup in same file   dup anywhere in corpus
code          90         5 ( 5.6%)             5 (  5.6%)
heading        2         0 ( 0.0%)             0 (  0.0%)
html           2         0 ( 0.0%)             0 (  0.0%)
list         552         0 ( 0.0%)             0 (  0.0%)
prose       1414         4 ( 0.3%)            21 (  1.5%)
table         77         0 ( 0.0%)             0 (  0.0%)

### cmspec  files=2  blocks>=120ch=23
type           n   dup in same file   dup anywhere in corpus
code           2         0 ( 0.0%)             0 (  0.0%)
list           8         0 ( 0.0%)             0 (  0.0%)
prose         13         0 ( 0.0%)             0 (  0.0%)
```

A prose block of ≥40 characters is unique within its file in **100.0%** of
rust-book's 2,938 prose blocks (0 duplicated) and **99.4%** of obsidian-help's
2,526 (16 duplicated). Code and raw HTML are not: raw-HTML blocks in rust-book
duplicate within a single file at 22.6% at ≥40, and at **23.6%** at the script's
default ≥20 — `html 934 220 (23.6%)` in the `minlen=20` arm of `results-e4.txt`,
which is the threshold that 23.6% has always belonged to. Same split as §3.2,
from a different direction.

Crucially, the residual ambiguity is **detectable at resolve time** — the
resolver reads the whole file and sees two matches — so it becomes a loud
`#REF!`, not a silent wrong answer. Stored ids have no such property: §1.2 showed
a duplicate id arriving through a *clean merge* with nothing to see.

**Provenance correction, 2026-09-10 (kindspec/research#5).** Until this revision
§3.3 showed a four-row `corpus / minlen / prose blocks / dup in file / dup in
corpus` table that **the committed script could not produce**: `e4_uniqueness.py`
took no arguments and hardcoded a single `>=20` threshold, so it had no `minlen`
to vary, it printed one block per corpus with a row per block type rather than
one row per corpus, and its percentages are emitted to one decimal where the
table showed two. There was no `results-e4.txt` either. The script now takes
`minlen` and all three runs are committed. Re-measured at the §3 pins, two of
the four prose rows moved, both in `obsidian-help`:

```
corpus         minlen  superseded value              measured 2026-09-10
rust-book          40  2938   0 (0.00%)   0 (0.00%)   2938   0 (0.0%)   0 (0.0%)
rust-book         120  2535   0 (0.00%)   0 (0.00%)   2535   0 (0.0%)   0 (0.0%)
obsidian-help      40  2515  16 (0.64%)  40 (1.59%)   2526  16 (0.6%)  48 (1.9%)
obsidian-help     120  1408   4 (0.28%)  21 (1.49%)   1414   4 (0.3%)  21 (1.5%)
```

The two rust-book rows reproduce exactly. obsidian-help's prose-block counts are
11 and 6 higher, and its corpus-wide duplicate count at ≥40 is 48 rather than
40. The superseded values are recorded here rather than overwritten silently: the
derived claim above recomputes to 99.3666%, which still rounds to the 99.4% it
always read, but the population it is taken over is now 2,526 blocks and not
2,515.

Two things the re-measurement settles that the old table left ambiguous. First,
the **23.6%** raw-HTML figure belongs to `minlen=20`, not to the 40 of the table
printed beside it; at 40 the same measurement is 22.6% of 873 blocks. Second,
rust-book prose has **zero** duplicates at 40 and at 120, so the `0.00%` the old
table claimed for those rows was right. The nonzero row that raised the question
— `prose 2985 0 ( 0.0%) 4 ( 0.1%)` — is the `minlen=20` arm, where blocks of
20–39 characters are in scope, and it contradicts nothing in the table. Had it
been nonzero at 40 the paragraph above would still stand: a second match is
visible to the resolver, and a visible ambiguity is a loud `#REF!`.

### 3.4 The standoff case: arbitrary sub-block spans, two-stage anchoring

§3.1–3.3 anchor whole blocks. The OHCO/standoff argument demands more: a comment
anchors to an arbitrary span *inside* a block. `e7_span_anchor.py` samples
word-aligned spans of 4–12 words and anchors them with a W3C TextQuoteSelector
(exact + 32-char prefix + 32-char suffix, the Hypothes.is convention) plus a
position hint.

One-stage (a sliding fuzzy window over the whole later file, which is what
Hypothes.is does) versus **two-stage** (anchor the *block* first under the hard
policy of §3.2; if that refuses, orphan; otherwise search only inside that
block) — `e8_twostage.py`:

```
### span anchoring, rust-book gap=5    spans=1097
             correct   loud refusal   SILENT-WRONG
1stage         97.5%           0.7%          1.73%  (n=19)
2stage         97.9%           2.1%          0.00%  (n=0)

### span anchoring, rust-book gap=25   spans=352
1stage         83.8%           0.9%         15.34%  (n=54)
2stage         92.9%           7.1%          0.00%  (n=0)

### span anchoring, obsidian-help gap=5  spans=491
1stage         97.1%           0.2%          2.65%  (n=13)
2stage         96.5%           3.1%          0.41%  (n=2)
```

Two-stage anchoring is **both more accurate and dramatically safer**: at 25
commits of real editing it is 9 points more correct *and* it converts a 15.3%
silent-wrong rate to zero. The mechanism is simply that a span may not be
located anywhere the block containing it was not first located, so the search
can never wander into a lookalike elsewhere in the file.

This is a direct answer to the one criticism the anchoring literature makes of
itself. Robert Knight, Hypothesis's client lead, on
https://github.com/hypothesis/client/issues/7571:

> "It is correct that quote anchoring can anchor to text that is similar to the
> original but doesn't semantically match. … there is a trade-off between
> precision and recall when anchoring annotations."

The Hypothesis matcher (`src/annotator/anchoring/match-quote.ts`) returns `null`
only when *no* substring is within `quote.length / 2` edits; there is **no
minimum score threshold**, and position is a tie-breaker weighted 2 out of 92
(`quoteWeight = 50; prefixWeight = 20; suffixWeight = 20; posWeight = 2;`). It
is tuned for recall over precision. This substrate must be tuned the other way,
and I3 says so; the measurement says the cost of doing so is ~5 points of recall
at 25 commits, and the benefit is the elimination of an entire silent-wrong
class.

### 3.5 The only real numbers in the literature agree

Brush, Bargeron, Gupta & Cadiz, *Robust Annotation Positioning in Digital
Documents* (CHI 2001 / MSR-TR-2000-95,
https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2000-95.pdf) —
12 participants, 216 annotations, 302 position-satisfaction ratings:

- text **moved but unchanged**: *"100% of annotations attached to text that moved,
  but did not change, were found"*, median satisfaction **7.0/7**.
- text **edited**: 134 ratings, *"our algorithm successfully transferred 71 and
  orphaned 63"* — a **47% orphan rate** once the anchored text is itself
  rewritten, with a much cruder algorithm than either arm measured here.
- and the finding that settles the design question:
  satisfaction correlated **−.34 (p < .003)** with edit severity for *found*
  annotations and **+.72 (p < .001)** for *orphaned* ones.
  **Users prefer an honest orphan to a confident wrong anchor.** That is I3,
  measured on humans, in 2001.
- the stakes, from Cadiz et al.'s ~450 users over 10 months of Office 2000 Web
  Discussions: *"lost annotations was cited as the primary reason people stopped
  using the system."*

There are, so far as this investigation could establish, **no published
re-anchoring success rates from Hypothes.is**. The fuzzy-anchoring post carries
no numbers; the orphans announcement offers only *"Most pages aren't very
dynamic, and therefore won't have any orphans"*
(https://web.hypothes.is/blog/showing-orphaned-annotations/). The only
quantified production datapoint located was a single-page incident —
*"18 annotations anchor and 15 fail to anchor"*
(https://github.com/hypothesis/product-backlog/issues/143) — whose root cause
was an ad script polluting `Array.prototype`, i.e. plumbing, not matching. Any
claim of the form "fuzzy anchoring works X% of the time on the open web" is
unsourced. **The numbers in §3.1–3.4 of this file appear to be the only
measurements of block- and span-level re-anchoring over real version-control
history that this project has been able to find or produce.**

### 3.6 And the one advantage nobody in the literature had: git

Phelps & Wilensky needed a stored id because they had no way to see the document
as it was when the annotation was made. This substrate does. An annotation
records the **blob SHA** it was made against. Re-anchoring is therefore not a
guess from a 32-character window; it is a three-way problem with the base in
hand — precisely the shape L3's block merger already solves. And when it does
fail, it degrades to *"here is the paragraph as it stood when this comment was
written"*, which is a strictly better failure than *"this id is gone."*

---

## 4. What real systems actually do — the on-demand hypothesis, measured

The hybrid proposal was: mint an id **only when something references the block**.
Obsidian is the shipped example. Its own documentation
(`obsidian-help/en/Linking notes and files/Internal links.md`, a real file in a
real repo):

> "You can link to a block by adding `#^` at the end of your link destination,
> followed by a unique block identifier. For example: `[[2023-01-01#^37066d]]`.
> Fortunately, you don't need to manually find the identifier—when you type the
> caret (`^`), a list of suggestions will appear, allowing you to select the
> correct block."

> "You can also create human-readable block identifiers by adding a blank space
> followed by a caret (`^`) and the identifier. Block identifiers can only
> consist of Latin letters, numbers, and dashes."

> "**We do not support links to specific parts of quotations, callouts, and
> tables.**"

> "Block references are specific to Obsidian and not part of the standard
> Markdown format. Links containing block references won't work outside of
> Obsidian."

So: ids are minted lazily, on link creation; the granularity stops at the block;
and the vendor states the interop cost itself.

**Then census Obsidian's own 175-file help vault — the vendor eating its own
cooking, ~5,539 blocks:**

```
reference forms used:
  [[note]]            plain      709
  [[note#Heading]]    heading    687
  [[note#^blockid]]   block id    19
```

**Heading references outnumber block-id references 36 : 1.** Block ids exist on
**0.34% of blocks**. And of the 19 ids:

```
auto-generated (6 hex): 5     (three of which are examples inside the doc that documents them)
human slugs:           14
```

```
^37006f                                referenced by 0
^37066f                                referenced by 0
^a4b3a2                                referenced by 0    <- en/Obsidian/Credits.md:39, real orphan
^obsidian-sync-status                  referenced by 0    <- en/Obsidian Sync/Set up Obsidian Sync.md:83
^blockquote-system-limitation          referenced by 1
^quote-of-the-day                      referenced by 1
^sync-geo-regions                      referenced by 2
...
```

Four of twenty ids reference nothing. **20% garbage, in the vendor's own vault,
with no GC** — the predicted failure mode of on-demand minting, observed in the
wild. `^a4b3a2` sits on a line of the credits page pointing at nobody.

Three conclusions, all empirical:

1. **On-demand minting is real and it does keep prose clean** — 0.34% density is
   negligible. The hybrid's central claim survives.
2. **But when humans get to choose, they overwhelmingly choose names.** 14 of 19
   ids are slugs; 687 of 706 sub-note references are headings. The minted id is
   the fallback people use when there is no name available, not the primary
   mechanism.
3. **Garbage does accumulate and there is no GC story.** 20%, measured.

The on-demand hypothesis is therefore *half right*: laziness is correct, and the
thing to lazily create is a **name**, not an id.

**Two more facts about the Obsidian id, both relevant.** Its **scope is
file-local**, not vault-global — the link embeds the filename (`[[note#^id]]`),
so *moving a block to another note breaks the link* with no propagation (open
feature request since 2021, https://forum.obsidian.md/t/25412). Logseq's ids are
graph-global and therefore survive moves; this is the one axis on which the
heavier scheme genuinely wins. And the **format is unverifiable** — Obsidian is
closed source; all eight auto-generated ids in its own help repo are 6 hex
characters (`^b15695 ^37066d ^37066f ^37006f ^376b9d ^432ea1 ^a4b3a2 ^0f681f`),
while the ecosystem's tooling assumes base36
(`Math.random().toString(36).substring(2, 8)` in obsidian-advanced-uri). Either
way it is 6 characters, which §1.5 shows is p ≈ 1 for collisions at 10^6.

A weak but suggestive datum: two curated public vaults — `kepano/kepano-obsidian`
(103 notes, by Obsidian's CEO) and `bramses-highly-opinionated-vault-2023` (67
notes) — contain **zero** block ids between them.

### 4.2 Logseq: the id is real, the cost is measured, and the road ends in SQLite

A real public Logseq graph, verbatim
(`mutable-learning/notes`, `pages/Machine Learning.md`):

```markdown
tags:: Algorithmics
topic:: Machine Learning
algo:: Unit 4 Outcome 3

-
	- three common approaches to developing a machine learning algorithm correspond to learning paradigms
		- [[Supervised Learning]]
		  id:: 6530e3ab-2a82-4d18-8766-01b50c969552
		- [[Unsupervised Learning]]
		  id:: 6530e3b7-aefc-4b64-80c2-1337dab34c3a
		- [[Reinforcement Learning]]
```

and the property pile-up in another (`candideu/Logseq-Demo-Graph`):

```markdown
	- [logseq-localassets-plugin](...): embed files from your computer via a file browser
	  id:: 6498e61e-c28d-467f-85a6-308496e11e82
	  collapsed:: true
```

```markdown
- Orality, Sampling, Collective Memory, and Knowledge Sharing
  ls-type:: annotation
  hl-page:: 17
  hl-color:: yellow
  id:: 64950a90-38b6-4346-9cd8-e38aae050c06
  hl-stamp:: 1687489212049
```

Judged honestly: this is not markdown that a human would want to edit in another
tool, and Logseq's own users say so. *"When you open Logseq Markdown files in
another editor, properties make them unusable"*
(https://discuss.logseq.com/t/20073). On `collapsed::`: *"It creates lots of
visual clutter when viewing my files in Obsidian"*
(https://discuss.logseq.com/t/1016/2). And the argument this design should
adopt wholesale (https://discuss.logseq.com/t/14520): *"this metadata shouldn't
be a part of the documents and rather only be a part of the runtime or edn
cache… this is not important enough to add versions to change history in GIT or
sync."*

Machine-metadata lines measured at **4.5% and 12.6% of non-blank lines** in the
two larger public graphs. Orphan rates — ids written to disk that nothing
references — measured across three real graphs:

| graph | `id::` written | unique `((refs))` | orphaned |
|---|---|---|---|
| mutable-learning/notes | 51 | 30 | **22 (43%)** + 1 dangling ref |
| carducci/logseq-demo-graph | 4 | 1 | **3 (75%)** |
| candideu/Logseq-Demo-Graph | 21 | 19 | **2 (10%)** |

Logseq classifies its own ids as machine noise in source
(`graph_parser/property.cljs`):

```clojure
(defn hidden-built-in-properties
  "Properties used by logseq that user can't edit or see"
  []
  (set/union
   #{:custom-id :background_color :created_at :last_modified_at
     :id :background-color :heading :collapsed ...
```

Minting is lazy, on reference creation, exactly as the hybrid proposes
(`handler/editor.cljs`): `set-blocks-id!` — *"Persist block uuid to file if the
uuid is valid, and it's not persisted in file"* — called from `copy-block-ref!`.
Note the compensating virtue, which is genuine: because Logseq ids are
graph-global rather than file-local, **block refs survive a move**, which
Obsidian's do not.

**Where the road leads.** The prior brief's framing needs one correction: Logseq
2.0 is a **split**, not a replacement. Announced 2026-04-24
(https://logseq.io/p/e3YDyX5AYr): *"Logseq OG → File-based graphs (Markdown)"*
versus *"Logseq → Database graphs"*, with *"Logseq OG will continue to be
maintained. It will receive security and Electron upgrades, but no new
features."* Version 2.0.1 shipped 2026-07-13 as an early beta.

But for the product that is still being built, markdown is now a **lossy
export**. From `logseq/docs/db-version.md`, verbatim:

> "`Export EDN file` … **This is the only export type that fully captures a
> graph's data and is editable.**"
> "`Export as standard Markdown (no block properties)` … **Since this export is
> unlikely to ever export timestamps or all properties, it cannot capture all
> data in a graph.**"

Storage is `db.sqlite`; *"There is no re-index like in file graphs"*; properties
left the text entirely — *"Since properties are not a part of the block content,
properties can more naturally be added to these blocks"* — and `((uuid))` block
refs were dropped: *"blocks no longer use `(())` for referencing."* `logseq/og`
was last pushed 2025-05-28 and its final three commits are an Electron bump, a
CVE bump and a workflow tweak.

**The inference is not "ids in markdown cause SQLite".** It is narrower and
harder: *once the ids and the properties they attract are load-bearing, the text
file stops being able to hold the whole truth, and the honest move is to admit
it.* Logseq made that move. A substrate whose entire premise is that the file
IS the truth cannot follow it, and therefore must not start down it.

### 4.3 Roam: the sharpest evidence in the whole file

Roam's **own** official Help graph, exported by Roam in all three formats
(`MatthieuBizien/RoamResearch-offical-help`), measured directly:

- 7,228 uids; 6,687 are exactly **9 characters** over the 64-char NanoID
  alphabet `[A-Za-z0-9_-]`; the rest are `MM-DD-YYYY` daily-note pages.
- **100% of blocks and pages carry a uid** — in the JSON/EDN export.
- The markdown export of one whole file, verbatim:

```markdown
- {{embed-path: ((rdJcOMHVE))}}
```

And the measurement:

> Across 1,228 exported markdown files there are **103 raw `((uid))` references
> (79 unique) and ZERO uid anchors on any target block.**

Every block reference in Roam's markdown export is **structurally
unresolvable**. Confirmed by an importer author
(https://forum.obsidian.md/t/8186/5): *"the markdown as exported from Roam
doesn't include any details about block links. Therefore it would be impossible
to write a markdown importer that keeps this info, any importer would have to
deal with the JSON (or the EDN)."* Roam's own tracker concedes the same for
backups (Roam-Research/issues#451): *"Restoring a graph from a backup does not
preserve block-level back-references."*

This is the pure form of the failure: **identity in the database, not in the
file.** It is what "markdown export" means when the ids never lived in the text.

### 4.4 Org-mode, and the rule its index failure teaches

A real file — and note its title
(`jethrokuan/braindump/org/main/plain_text_is_not_enough.org`):

```org
:PROPERTIES:
:ID:       a3268b6d-203b-4be6-a4b6-de92585eba3d
:END:
#+title: Plain Text Is Not Enough
```

At per-heading density (`karlicoss/exobrain/memex.org`, 48 ids in one file):

```org
* related
:PROPERTIES:
:ID:       rltd
:END:
** memex is the ultiplate knowledge management solution                 :pkm:
:PROPERTIES:
:ID:       mmxsthltpltknwldgmngmntsltn
:END:
```

Three lines and ~57 bytes per anchored block.

Org is the most conservative of the lot, and says why. `org-id-link-to-org-use-id`
**defaults to `nil`** ("Never use an ID"), with the docstring:

> "The purpose of this setting is to **avoid proliferation of unwanted IDs**,
> just because you happen to be in an Org file when you call `org-capture`…"

Org 9.7 added `org-id-link-consider-parent-id` explicitly so that you can link
to a named sub-entry *"without requiring every sub-entry to have its own ID"*,
and Org-roam ships a FAQ titled *"How can I stop Org-roam from creating IDs
everywhere?"*

**And the index is the cautionary tale.** `~/.emacs.d/.org-id-locations` is a
single printed Lisp alist saved on `kill-emacs-hook`; the string
`org-id-locations` appears **zero times** in the 24,460-line Org manual (a
maintainer: *"It is an internal variable"*). The decisive fact for this design:

> `org-id-update-id-locations`: *"This will scan all agenda files, all associated
> archives, all open Org files, and all files currently mentioned in
> `org-id-locations`."*

**It is not rebuildable from the corpus.** None of its five inputs is a corpus
root, agenda-file expansion is non-recursive, and the fourth condition is
circular — the only record that a file exists is the cache you are trying to
rebuild. Hence the real breakage: *"the link works only on the computer i
created it. When i move the file to another computer, the link stops working"*
(emacs.stackexchange 12291). And hence org-roam had to replace it wholesale
(`org-roam-id.el`): `(advice-add 'org-id-find :before-until #'org-roam-id-find)`,
with `org-roam-update-org-id-locations` documented as *"like
`org-id-update-id-locations`, but will automatically use the currently bound
`org-directory` and `org-roam-directory` … where the lookup for files in these
directories will be always recursive."*

> **Rule (adopted): every index must be a pure, total function of the tracked
> corpus, rebuildable from a known root with no other input.** "Stale" must not
> be a state the system can be in. This is I4, and org-id is the counterexample
> that names the trap.

### 4.5 Notion, Anytype, Dendron — three more ways to lose

**Notion** puts 32-hex ids in **filenames only**. A real 2026 export:

```
CEH Practical Note/Engage Part I 26e98a430f6c80b1a5b4dd843f2703e7.md
[Pure Yr1](Maths%20e35a71c048bf4d79a3a9f8d10b2b42bf/Pure%20Yr1%20d643d48607f045cebabc1133c0cb9f9c.md)
```

A full 51-file export scan: **139 hex occurrences, all in filenames or link
targets; zero block ids in prose.** Notion's markdown export has no
block-reference mechanism at all. Note the reason the ids are in the filenames:
*"Notion differentiates notes with the UID which allows their users to work with
multiple notes with the same filename."* An entire cottage industry exists to
strip them (`notion-export-cleaner`, `notion_export_enhancer`,
`notion2obsidian`).

**Anytype** is the clean statement of a distinction worth naming: it is
local-first and **deliberately not plaintext**. `any-sync`: *"data in `any-sync`
is stored as encrypted Directed Acyclic Graphs (DAGs)"*; *"Objects are encrypted
at rest"*; *"Indexes stay local and unencrypted… stored separately from the
encrypted data itself."* Its markdown export uses slugified titles with a random
suffix only on collision — **no ids at all**. **Local-first ≠ plaintext-first**,
and only the second one is this project's bet.

**Dendron** is the one that shows the cost of an id you cannot change. Per-note
frontmatter, as expected:

```yaml
---
id: h5173rzm248clfhht7v128c
title: Block Anchors
---
```

> "Every page is published using its unique ID which means that urls will never
> change, even if the filenames do."

But it *also* auto-generated per-block anchors — *"To have Dendron automatically
generate random block anchors, select the target line… and run the `Copy Note
Link` or `Copy Note Ref` commands"* — appending 12 chars to the end of the source
line, visible in Dendron's own vault:

```markdown
If the note has a `desc` property, it will be overwritten by the content from `desc` ^ygk9kha1hgzy
```

And the finding that should end any thought of a "we can change the id scheme
later" escape hatch: the id-length histogram across Dendron's own 1,021-note
vault is `{36: 259, 23: 357, 21: 370, 16: 23}` — **four distinct id lengths, i.e.
several incompatible id generations coexisting in one corpus, permanently**,
because an id written into
a file cannot be migrated without rewriting every file and breaking every
reference. (Dendron is in maintenance only since Feb 2023: *"as a business, we
were ultimately not able to find product market fit."*)

### 4.6 Three cross-cutting costs the survey makes concrete

**In-band syntax collides with the language it lives in.** Obsidian's `^` is
parsed as a block id inside LaTeX (`x=a^2`) and inside code blocks — filed twice
against the community GC plugin (issues #1, #3). Any sigil placed in prose is a
sigil taken away from prose.

**GC is a data-loss hazard, not a feature.** Obsidian has no GC. The community
plugin that provides one deleted *every* block id, used and unused
(https://forum.obsidian.md/t/91674): *"ALL block IDs are gone: the unused AND
the used ones. So, from that point of view a good part of my notes collection
has been reduced to the Stone Age because I use embedding heavily so had many
block IDs."* A garbage collector for in-file ids must prove non-reachability
across the whole corpus *including uncommitted and remote branches*, which is
not a property a text file can carry.

**Ids leak into every export path.** Obsidian's are hidden in Reading view but
visible in Source and Live Preview, and Pandoc emits them raw —
*"It produces the above verbatim in the word doc"*
(https://forum.obsidian.md/t/15996). A plugin author who stamped every block:
*"since these IDs are visible in UI, notes become unbearably noisy."*

### 4.7 The strongest argument on the other side, stated fairly

The best case for stable ids is not technical, it is semantic. Sascha Fast
(https://zettelkasten.de/posts/the-hidden-problem-with-note-titles-as-links-and-how-to-fix-it/,
2026-02-24) argues that auto-rename is not enough, because *"if the title
effectively works as the ID, the ID carries meaning. This characteristic creates
friction: the meaning of the link needs to change depending on the context in
which you place it."* The concrete harm is real: renaming *"Willpower is
limited"* to *"Ego depletion"* silently corrupted the prose of every citing note
(https://forum.obsidian.md/t/5601/6). §6 measures exactly this and finds it
severe — only 33.6% of heading addresses survive 25 commits.

It is worth recording that the survey behind §4 was read by its own author as
arguing *for* stored ids: on that reading the id is not the problem, and the two
real failure modes are (a) no GC and (b) pathless refs resolved by an index that
cannot be rebuilt from a corpus root — so "ids in the files **plus** a
constructively derivable index" would avoid both. That is the strongest form of
the pro-id case and it is not silly. It is rejected here on one measurement and
one deployment fact: §3.1 shows that under **stock git** a stored id survives if
and only if the block's bytes did not change, which is exactly the condition
under which an exact-quote match already succeeds — so the id buys nothing a
quote does not — and PASS4/I6 says stock git is what will actually run, because
merge drivers cannot be deployed. The pro-id reading is correct for a system with
a merge driver or a database. This is neither.

The counter-position is Andy Matuschak's — *"Evergreen note titles are like
APIs… those titles become an abstraction for the note itself"*
(https://notes.andymatuschak.org/Evergreen_note_titles_are_like_APIs) — and it
is the one this design takes, with a mechanism Matuschak does not have: the name
is the *readable* address, the recorded quote is the *durable* one, and both
live in the referrer (§6, §7.3). That combination is what makes the semantic
objection survivable without putting a token in the target.


---

## 5. Ordering: fractional indices are unnecessary machinery — confirmed

`e5_ordering.sh` tests three serializations under stock git: pure line order; a
fractional key with the file kept sorted; and a fractional key with the file in
creation order and sorted at render.

```
== Format A: line order (no keys) ==
A1 inserts at two DIFFERENT points               exit=0 markers=0
A2 inserts at the SAME point                     exit=1 markers=1
A3 Alice MOVES 'echo' to top, Bob EDITS 'echo'   exit=1 markers=1
== Format B: fractional key, file kept sorted by key ==
B1 inserts at two DIFFERENT points               exit=0 markers=0
B2 inserts at the SAME point (interleaving test) exit=1 markers=1
B3 Alice MOVES 'echo' (key change only), Bob EDITS it  exit=1 markers=1
== Format C: fractional key, file NOT sorted (render sorts) ==
C3 Alice MOVES 'echo' (key edit in place), Bob EDITS it exit=1 markers=1
```

**Every case is identical.** The fractional index buys nothing, because the key
lives on the same line as the content, so a key change and a content change are
the same line change. It does not rescue move-plus-edit — the one case it is
supposed to be for.

The prior finding is confirmed and can be strengthened. Kleppmann et al.,
*Interleaving anomalies in collaborative text editors* (PaPoC '19,
https://martin.kleppmann.com/papers/interleaving-papoc19.pdf), condemns exactly
the dense-identifier family that fractional indexing belongs to:

> "both users spread the identifiers of their insertions across the interval
> (0.64, 0.95). When merged, the resulting character sequence is an arbitrary
> interleaving of the two. … The problem is even worse if the concurrent
> insertions are comprised of not just a single word but a paragraph or section.
> In these cases, interleaving the users' insertions would most likely result in
> an incomprehensible text that would have to be deleted and rewritten."

Git's line merge does not interleave; it **conflicts**, loudly, at the reader's
own granularity. That is strictly better behaviour. Figma's own mitigation for
identical keys is explicitly server-side — *"The server can avoid ever having two
objects with an identical position by just generating and assigning a unique
position to the second insert operation"*
(https://www.figma.com/blog/realtime-editing-of-ordered-sequences/) — which is
unavailable in an offline-first git model.

Measured growth (simulation): repeated midpoint insertion into the same gap grows
keys **one character per ~5.95 inserts** — 100,000 same-gap inserts produce a
**16,667-character key**. Under random human editing, growth is logarithmic: max
length 7 at n = 100,000. Benign for a canvas, unbounded for programmatic
insertion.

**Recommendation: no fractional indices for documents or tables. Document order
is line order.** They are admissible in exactly two places where order genuinely
is not line order: **canvas z-order**, and an ordered collection whose members
are separate files. Note that L4 already handles canvas ordering the right way
(sparse named overrides), so even that case may not need them.

The honest cost of line order is **move-plus-edit**, which conflicts (A3) — and
that is the case L3's computed block identity already resolves: *"one side MOVES
a section, other EDITS → 0 conflicts, both applied (git merge-file: CONFLICT)."*
Computed identity solves the problem fractional indices were proposed to solve,
without putting anything in the file. Mitigations for the raw-git path:
`merge.conflictStyle=zdiff3` (so the base is visible) and a lint that flags a
moved block whose content also changed.

---

## 6. The measurement that reorders the recommendation: names rot faster than quotes

The standard objection to nominal addressing is link rot — a heading slug changes
when someone improves the heading, and an id would not. `e9_headings.py` measures
how bad it actually is, over real history:

```
corpus            gap  pairs  headings    survived  renamed/gone
rust-book           1    100       672       89.6%         10.4%
rust-book           5     94       672       71.9%         28.1%
rust-book          25     42       420       33.6%         66.4%
obsidian-help       1     92       770       99.1%          0.9%
obsidian-help       5     69       622       94.2%          5.8%
obsidian-help      25     10        88       68.2%         31.8%

rust-book        files=112  headings=531   duplicate slug within a file: 0 (0.00%)
obsidian-help    files=175  headings=1533  duplicate slug within a file: 91 (5.94%)
```

(Survival is measured as exact slug presence anywhere in the later file, so a
*moved* heading counts as surviving; this is generous to the slug.)

**Heading slugs rot badly** — only 33.6% of rust-book's heading addresses survive
25 commits — **and they are not even unique**: 5.94% of obsidian-help's heading
slugs collide within their own file. Obsidian ships exactly this failure and
concedes it; a forum moderator on a 2025 report that renaming a heading breaks
inbound links: *"This is (unfortunately) expected behavior"*
(https://forum.obsidian.md/t/manually-renaming-a-linked-heading-breaks-the-link/103801),
and on the older request: *"they don't even show as broken; they simply stop
working"* (https://forum.obsidian.md/t/.../61942).

Now compare the three candidate addresses on the same corpus at the same edit
distance (25 commits of real editing):

| address | correct at gap=25 | silent-wrong | notes |
|---|---|---|---|
| heading slug | **33.6%** | slug reuse → wrong target | free; zero bytes; human-readable |
| stored `^id` under stock git | 80.0% | 0.0% | but 20% loud conflicts; +5–29% bytes; collides on copy-paste |
| **block quote anchor (hard policy)** | **94.0%** | **1.0%** (all code blocks) | zero bytes in the target |
| **two-stage span quote anchor** | **92.9%** | **0.00%** | zero bytes in the target |

**The quote is the most durable address of the three, by a wide margin, and it
is the only one that costs the target file nothing.** That is the finding that
settles the design.

### The rule that follows

> **Redundancy is free when it lives in the REFERRER, and pollution when it
> lives in the TARGET.**

Every serious anchoring design in the literature is redundant with fallback —
Phelps & Wilensky's UID → tree-walk → context ladder; the W3C's multiple
selectors (*"Multiple Selectors SHOULD select the same content, however some
Selectors will not have the same precision as others"*, §4.2); Hypothes.is's
four strategies tried in order. All of that redundancy can be stored where the
reference is made. **The referrer must never write to the target.** That single
constraint disqualifies on-demand id minting and preserves everything good about
it.

---

## 7. Recommended scheme, with exact syntax

### 7.1 Correspondence — nothing in the file

Keep L3 exactly as it is. Blocks are boundaries plus raw bytes; identity across
versions is computed by exact hash then `difflib` ratio > 0.5, on **content**
excluding the trailing separator. No change.

### 7.2 Reference — a name, chosen by a human, only where a human chose one

One address grammar for the whole substrate, the L5 grammar, unchanged:

```
{{ artifact-path#name }}
```

`name` resolves against a single per-artifact namespace, in this order:

1. an **explicit region marker** authored in the target;
2. a **heading slug** derived from a heading's text;

and resolves to a `#REF!` if it matches zero, or more than one, of either.

**The region marker, exact syntax:**

```markdown
<!-- #scram-threshold -->
The reactor scram threshold is 4.2 sigma above baseline, measured over a
rolling 30-second window.
```

and for a span that is not one block, an explicit begin/end pair (the MediaWiki
Labeled Section Transclusion shape, chosen over a bracketing form so that
regions may nest and overlap — which OHCO says they must be able to):

```markdown
<!-- #procedure-a:begin -->
1. Confirm the limit.
2. Arm the interlock.
<!-- #procedure-a:end -->
```

Why this exact form, each clause load-bearing:

- **An HTML comment** because it is the only carrier that is invisible in *every*
  renderer including GitHub's, with no extension. Verified with a CommonMark
  parser: `<!-- #scram-threshold -->` emits raw HTML passthrough and displays
  nothing, while Pandoc's `{#custom-id}` renders **literally as visible garbage**
  (`<h2>Head {#custom}</h2>`) because CommonMark has no attribute syntax — the
  spec contains no `{#` sequence at all. Pandoc `header_attributes`, kramdown
  IALs and `markdown-it-attrs` are three mutually incompatible extensions and
  GFM supports none of them.
- **A name the author typed**, never a minted token, so I2 holds and the file
  stays the UI.
- **On its own line**, so the marker is its own block: the boundary parser sees
  it cleanly, and a marker-write is not a write to the prose line.
- **`begin`/`end` as independent markers**, not a bracketing construct, so
  regions can nest and overlap. AsciiDoc's `tag::`/`end::` is the industrial
  precedent and its diagnostics are the ones to copy verbatim —
  `detected unclosed tag '%s' starting at line %d`,
  `mismatched end tag (expected '%s' but found '%s')`,
  `unexpected end tag '%s' at line %d` (`asciidoctor/lib/asciidoctor/reader.rb`).
- **Not `<<<<<<<`-shaped and never at column 0 in that form**, per `V-markers`:
  git emits 7-or-more-character `<<<<<<<`/`=======`/`>>>>>>>` runs at column 0,
  and a marker syntax must not collide with them, and must survive a three-way
  merge that splits a begin/end pair across two conflict hunks.

**Density budget: markers are rare by design.** Obsidian's own vault carries one
on 0.34% of blocks. At that density the byte cost is 0.1%, not the 5–29% of
§1.4. The author writes a marker when they decide a passage is part of the
document's public interface — the same act as naming a column.

**Rename is a refactoring that rewrites dependents.** This is already the
project's settled position for column renames (RESEARCH.md §3). It is what turns
the 33.6% slug-rot number into a non-issue on the happy path, and §7.3 covers
the unhappy one.

### 7.3 Anchoring — quote selectors, stored in the referrer, two-stage resolution

Every reference *also* records a W3C-style anchor, in the referrer, never in the
target. For a reference in a document, in the document's own frontmatter; for a
comment or tracked change, in the standoff sidecar. Exact shape:

```yaml
# frontmatter of the REFERRING artifact
refs:
  - id: r1                       # local to this file only; never written to the target
    target: policy.md#scram-threshold
    base: 8f2a1c9e               # blob SHA the anchor was taken against
    quote:
      exact:  "The reactor scram threshold is 4.2 sigma above baseline"
      prefix: "constraints below are mandatory.\n\n"
      suffix: ", measured over a rolling 30-second window."
```

```yaml
# comments.yaml -- the standoff sidecar the OHCO refutation requires
- on: policy.md
  base: 8f2a1c9e
  block:                          # STAGE 1: locate the block
    exact:  "The reactor scram threshold is 4.2 sigma above baseline, measured
             over a rolling 30-second window."
  span:                           # STAGE 2: locate the span, inside that block only
    exact:  "4.2 sigma"
    prefix: "scram threshold is "
    suffix: " above baseline"
  author: cam
  body: "Is this still right after the 2026 recalibration?"
```

Resolution order, and it is normative — DITA's refusal to fix resolution order
is a documented defect (*"different conforming DITA processors might produce
different results for the same initial data set"*):

```
1. name           -> region marker, then heading slug.  0 matches or >1 -> continue
2. exact quote    -> unique match wins
3. exact + context-> disambiguate multiple exact matches by prefix/suffix
4. fuzzy quote    -> ratio >= 0.5 AND margin over runner-up >= 0.15
                     AND context similarity >= 0.30
                     AND the quote has >= 24 distinct chars or >= 8 distinct words
5. otherwise      -> #REF!, loudly, showing the text as it stood at `base`
```

Stage 2 (a span) may only be searched **inside** the block stage 1 resolved.
That constraint is what produced 0.00% silent-wrong in §3.4, and it is the whole
difference from Hypothes.is, whose matcher has no minimum score threshold and
searches the entire document.

The three hard predicates in step 4 are not arbitrary; §3.2 shows each one buys
safety at a measured, small recall cost, and that the class of content they
refuse (code fences, TOC lines, boilerplate) is exactly the class that is
already addressed nominally elsewhere in the substrate.

### 7.4 If a minted id is ever needed anyway, here is the only defensible one

There is one place a minted id may still be wanted: an anonymous entity that is
genuinely not text — a canvas shape, a table row that the user explicitly wants
to carry an identity through reordering. For those, and **only** those:

- **ULID**, 26 chars, Crockford base32, `01ARZ3NDEKTSV4RRFFQ69G5FAV`.
  Lexicographically sortable (so it doubles as a stable tiebreak order without a
  second field), 80 bits of randomness (p(collision) at 10^6 = 4.1e-13), minted
  purely client-side, monotonic within a millisecond by spec.
- **Never below 12 base32 characters.** §1.5: NanoID-8 is 1-in-563 at 10^6, and
  a 6-char base62 id — Obsidian's shape — has p ≈ 1 with ~8.8 expected duplicates.
- **Never in prose.** These belong in structured formats where a line is already
  a record and a leading id column costs nothing readable.

Do not use UUIDv4 (36 chars, unsortable) and do not use a content hash as a
durable id — L3 proved content hashes are not identity.

---

## 8. Transclusion

### 8.1 Design rules, extracted from the survey

**R1 — Address nominally, through one indirection level.** DITA is the most
industrially serious transclusion system and it added `keyref` on top of
`conref` for exactly this reason: *"The key reference mechanism provides a layer
of indirection so that resources… can be defined at the DITA map level instead
of locally in each topic"*, in order to *"avoid creating topic-to-topic
dependencies that are difficult to maintain."* Positional addressing loses:
docutils `:lines:`, Sphinx `:lines:` and Org `:lines` all break on any edit
above the range, silently.

**R2 — The target must declare the region; the referrer may not invent one.**
Every system that operates on *mutable* text requires target cooperation:
AsciiDoc `tag::`/`end::`, MediaWiki `<section begin=>`, DITA `id=`, Obsidian
`^blockid`, Logseq `id::`. The single exception is Xanadu, and it is an
exception only because its content is immutable and append-only — Nelson's own
example gives a v2 insertion **new** addresses (7784–7850) rather than
renumbering, so *"link 2053 remains attached to all of these surviving
characters in any new version."* You cannot have Xanadu's arbitrary-span
addressing without Xanadu's immutable store; git gives you the immutable store
for *committed* blobs, which is why the anchor records a `base` blob SHA.

**R3 — Never materialise the transcluded text into the referrer.** Measured
(`e6_transclude.py`): one sentence edited in a source transcluded into 8
documents.

```
 mat0.md   | 2 +-      <- materialised copies
 ...
 mat7.md   | 2 +-
 policy.md | 2 +-
 9 files changed, 9 insertions(+), 9 deletions(-)
```

versus **1 file changed** with reference-only transclusion. Materialised
transclusion multiplies the blast radius of every edit by the fan-out, destroys
`git log --follow` on the referrers, and makes staleness invisible. This is I4
(no hidden state) applied to references.

**R4 — Fix the resolution order and publish it.** DITA's own spec concedes
non-determinism (§7.3 above). Ours is normative.

**R5 — Fail loudly, at build time, and render the failure into the document.**
See §9.

### 8.2 Can you edit a transcluded copy in place?

**No, and the evidence is unusually clean.** Exactly three systems allow it, and
each has a property this substrate does not:

- **Xanadu**: content is immutable and append-only; an "edit" appends new spans
  and rewrites an EDL, so the copy and the original genuinely are one thing.
- **Logseq**: *"Edits made to the embedded content are also made in the
  referenced content"* — because the DB is the source of truth and the embed and
  the original are the same node rendered twice. And Logseq 2.0 made SQLite
  canonical: *"There is no re-index like in file graphs"*, markdown demoted to
  import/export, and `((uuid))` block refs dropped entirely.
- **Notion** synced blocks — same reason, plus a data-loss edge: *"If a synced
  block has more than 10 copies, deleting the original will also remove all
  copies. Undo won't restore them."*

And the negative case is decisive: **Obsidian, the only file-first system in the
list, has not shipped it in five years.** The feature request
(https://forum.obsidian.md/t/edit-transcluded-embedded-notes-blocks-in-place/15339)
was opened 2021-03-26 *by an Obsidian team member*, is still open with 207 posts
and a 2026-07-18 comment, and appears in none of 484 changelog entries.

DITA takes the opposite branch and forbids editing outright: *"When using the
@conref attribute on an element, the content of that element is ignored… the
referencing element acts as a placeholder for the referenced element."*

**Rule: editable-in-place transclusion requires a single authoritative
representation — immutable append-only content, or a real database. A plaintext
substrate where both copies are editable text cannot offer it without becoming a
two-way sync problem.**

**So what should happen when a user tries?** Three behaviours, in order:

1. The rendered transclusion is **read-only, and visibly so** — different
   background, a source breadcrumb, an "edit at source" affordance that
   navigates to `policy.md#scram-threshold`.
2. If the user types anyway, offer **edit-at-source** (jump and edit the one
   real copy).
3. Offer **detach** as an explicit, named action: replace `{{ ... }}` with the
   resolved text plus a provenance comment, and say so in the commit. This is
   copy-on-write with the copy made deliberate rather than accidental.

Never silently write through, and never silently fork.

---

## 9. Backlinks: derived, and out of the tracked tree

**Recommendation: derived, always. Never write a back-reference into a tracked
file.** The evidence is one-sided.

**Every surveyed tool derives them, and none writes into the target.** Obsidian:
`MetadataCache.resolvedLinks` maps *source* path → destination paths, held in
IndexedDB in the app config dir (`~/.config/obsidian/`), outside the vault,
rebuildable from the corpus alone via *Rebuild vault cache*. Logseq: DataScript,
rebuilt from files. Roam: DataScript. Dendron: in-memory at engine init.
Zettlr: a `Map<string,string[]>` re-indexed on FS events. TiddlyWiki: queried on
demand. Even MediaWiki, the closest to stored, keeps `pagelinks` as source→target
rows and states *"Regenerating the pagelinks table is always possible using the
rebuildall.php maintenance script."*

**The one system that materialised derived link data into tracked files reversed
the decision.** Foam wrote a generated region into every note:

```
[//begin]: # "Autogenerated link references for markdown compatibility"
[//end]: # "Autogenerated link references"
```

`CHANGELOG [0.15.6] - 2021-11-18 — "Link Reference Generation is now OFF by
default."` The issue tracker is a catalogue of exactly the predicted failure
modes: rewrite-on-every-save with no content change (#1339); a fight with
markdownlint MD053 producing *"editor flicker (Foam adds / formatter removes),
noisy diffs, and duplicated blocks"* (#1503); and the generator **destroying
hand-authored reference-style links** in the same region, filed twice years
apart (#487, #1622). Those markers now sit in ~5,600 public GitHub files.

**Scale says derivation is affordable, but rebuild-from-scratch is not.** At
100,000 pages / 853,409 blocks / 1,873,962 links, Obsidian answered backlinks at
*"hundreds per second"* while the full index build took *"more than two hours"*
(https://www.goedel.io/p/interlude-obsidian-vs-100000). A 57k-note vault
re-indexes in over 5 minutes on every open; an 86,685-file mobile vault took
314,929 ms to start. Logseq's headline reason for moving to SQLite is precisely
*"There is no re-index like in file graphs."*

**Therefore:** a persistent, incremental, **gitignored** index — SQLite FTS5 is
already the project's choice (RESEARCH.md §6) — keyed by blob SHA so that
invalidation is exact and a revert is a cache hit (L5 result 4). Never
committed, always rebuildable from the corpus alone. This is I4, and it is the
correction to org-mode's `org-id-locations`, an out-of-band cache that goes stale
and needs a manual `org-id-update-id-locations`: **the index must be a pure
function of the tracked files, so "stale" is not a state that can exist.**

---

## 10. Broken references must fail loudly — and it generalises

L1 established this for tables (a renamed column yields `#REF!` everywhere and
the aggregate refuses to sum) and L5 for cross-artifact derivation. It
generalises. `e6_transclude.py`:

**Target region deleted:**

```
# Procedure 0

Before starting, confirm the limit.

**#REF!(no region `scram-threshold` in policy.md)**

Then proceed.

   (the materialised copy shows a STALE value instead:)
   The reactor scram threshold is 4.2 sigma above baseline, measured over a
```

**Ambiguous name — and note that it arrives through a CLEAN stock-git merge:**

```
== (iv) does the duplicate NAME arise from a clean stock-git merge? ==
   merge exit=0, markers=0
   render of proc0.md after the clean merge:
   **#REF!(region `scram-threshold` declared 2x in policy.md — ambiguous)**
```

That last result is the key mitigation for the scattered-namespace problem of
§1.2, and it extends PASS4's rule with a second clause:

> **Co-locating a namespace's bindings is the MERGE-time answer. A resolver that
> refuses on duplicates is the READ-time answer — and it is available whenever
> we own the resolver, which we do.**

Markdown's `[api]` collision (`V-mdref`) is silent-wrong only because CommonMark
*mandates* first-definition-wins. We are not obliged to. Git merges the
collision cleanly, cannot see it, and does not need to — the resolver reads the
whole file and refuses. **This satisfies I6 without a merge driver.**

Ranked loudness of the surveyed systems, worst to best, as a calibration:
Obsidian renamed headings (*"they simply stop working"*) < DITA broken conref
(*"The @conref is ignored"*) and Org (*"Org neither checks for correctness nor
validates the content in any way"*) < AsciiDoc missing tag (warning, empty
output) < AsciiDoc missing **file** (stamps `Unresolved directive in
my-document.adoc - include::content.adoc[]` **into the rendered output**) <
docutils `:start-after:` (`Text not found.` error) < **dbt / Terraform**, which
fail at parse/plan time before anything runs:

```
Compilation Error in model demo (models/demo/demo.sql)
  Model 'model.my_new_project.demo' (models/demo/demo.sql) depends on a node
  named 'my_python_model' which was not found
```

The systems trusted at industrial scale are exactly the ones that fail loudly,
early, and against an explicitly declared interface.

### What the UI must do

1. **Render the failure into the document, not only the log.** `#REF!(...)` in
   the flow of the prose, styled as an error, at the position where the content
   would have been. An empty gap is the forbidden outcome.
2. **Name the specific failure** — missing artifact, missing name, ambiguous
   name, orphaned anchor — never a generic "broken link".
3. **Show the last known good text, labelled as historical**, recovered from the
   `base` blob SHA: *"as of commit 8f2a1c9e this read: …"*. This is the
   advantage git gives that Hypothes.is and Phelps & Wilensky did not have, and
   it converts an orphan from a dead end into a resolvable diff.
4. **Propagate through aggregates.** A document containing a `#REF!` must not
   export, publish, or render to PDF as if the hole were whitespace, exactly as
   L1's aggregate refuses to sum.
5. **Orphaned annotations must be visible, not hidden.** Hypothesis's own
   backlog records the opposite failure: annotations that fail to anchor and are
   *not* reported as orphans — *"It's just sort of hanging around in limbo…
   unreported orphans will be offscreen … so they are effectively lost to you"*
   and *"Silent failures are easy to miss, which is why this has gone on so
   long"* (https://github.com/hypothesis/product-backlog/issues/954). And Brush
   et al. measured that users are **more** satisfied with an honest orphan than
   a confident wrong anchor (+.72 vs −.34).
6. **Fail the build.** A broken reference is a validation error in the
   conformance suite, not a rendering nicety.

---

## 11. What this changes, and what is still open

### Settled by this pass

- **No minted sub-artifact ids in prose.** Correspondence is computed (L3),
  references are named by humans, anchors are quotes stored in the referrer.
- **The OHCO refutation is answered without ids.** A standoff sidecar anchors by
  two-stage quote selector: 92.9% correct, 0.00% silent-wrong at 25 commits.
  TEI itself says ids are not required — *"Stand-off markup may be used even when
  the base text being annotated is plain text… the range of text to be marked up
  is indicated by character offsets"* — and the "frozen base text" argument
  turns out to be narrower than its reputation: Thompson & McKelvie's title says
  *read-only documents* because read-only was their **premise** (large,
  controlled-distribution corpora), not a proof that standoff implies
  immutability.
- **The referrer never writes to the target.** This is the load-bearing
  constraint and it kills on-demand minting while keeping its good idea.
- **No fractional indices** for documents or tables; document order is line
  order. Admissible only for canvas z-order, which L4 already handles better.
- **Backlinks derived, gitignored, incremental, keyed by blob SHA.**
- **Every index is a pure, total function of the tracked corpus**, rebuildable
  from a known root with no other input. `org-id-locations` — which scans agenda
  files, archives, open buffers and *the cache itself*, and is therefore not
  rebuildable — is the named counterexample.
- **The on-demand hypothesis is half right and its good half is kept:** laziness
  is correct (Obsidian's own vault marks 0.34% of blocks), but the thing lazily
  created must be a **name**, authored by the target's own author, not an id
  minted by a referrer.
- **Broken references render `#REF!` in place, name the failure, show the
  historical text, and fail the build.**

### A new invariant, earned by the measurements

```
I7  IDENTITY IS COMPUTED WHERE IT CAN BE, NAMED WHERE IT MUST BE,
    AND MINTED NOWHERE.
    Corollary: a reference may store as many redundant selectors as it
    likes, in the REFERRING artifact. It may write nothing into the
    artifact it refers to.
```

This is I2 (nominal addressing) extended below the artifact boundary, and it
completes the set: A1 ranges, absolute coordinates, block separators, alignment
rows and minted block ids are now all instances of one defect.

### Still open, honestly

1. **The oracle's confident subset shrinks with edit distance** — 92% of blocks
   at gap=1, 74% at gap=5, 38% at gap=25. The gap=25 numbers are computed on 200
   confidently-classified anchors out of 533. The direction of the result is not
   in doubt, but state the prose counts exactly, because they are no longer all
   zero: under the hardened policy the silent-wrong count is 0 for prose in
   every arm; under the naive policy it is 0 in every arm except `obsidian-help`
   gap=5, which has 1 — a YAML frontmatter block, per item 8 below. The gap=25
   precision figures carry real uncertainty and a larger corpus study would be
   worth doing.
2. **All three corpora are technical documentation in English.** Prose-block
   uniqueness (100% / 99.4% at ≥40 chars) may not hold for meeting notes, legal
   boilerplate, or templated documents, which are exactly the duplicate-heavy
   shapes a work substrate will meet. This is the most likely place the
   recommendation breaks, and it should be re-measured on a real corpus of that
   kind before shipping.
3. **CJK and languages without spaces** were not tested; the entropy predicate
   (`>= 8 distinct words`) is word-segmentation-dependent and will need a
   different form.
4. **`difflib` is O(n·m)** and every experiment here used it because L3 did.
   `approx-string-match` (Myers bit-parallel), which Hypothes.is moved to,
   is the production choice; the thresholds must be re-derived for it.
5. **Region markers still conflict when adjacent to a concurrent edit** —
   verified: a marker written on its own line immediately above a paragraph that
   another branch reworded produces a conflict. The frequency is low (0.34%
   marker density, and markers are normally authored by the document's own author
   in the same session, not by a third party), but it is not zero, and it is the
   residue of the same defect that makes on-demand minting unworkable.
6. **A deliberate search for any published argument preferring content-derived
   or computed anchoring over stored ids in a plaintext note system found
   nothing.** That is a negative result from one search pass, not proof of
   absence — but it means §0's conclusion has no located prior art agreeing with
   it, and should be held accordingly.
7. **Two facts in §4 could not be verified.** Obsidian is closed source, so its
   id alphabet is inferred from eight observed ids (hex) against ecosystem
   tooling that assumes base36; and Obsidian Publish's rendering of block ids
   was not checkable (JS shell). Neither affects the argument — the length is 6
   either way — but neither is confirmed.
8. **`btype()` has no rule for YAML frontmatter**, so it classifies a
   frontmatter block as `prose`. The 2026-09-09 re-run's single prose-typed
   silent-wrong is exactly that (§3.2). Any future harness should add the rule
   — and say that it did, rather than quoting a cleaner number as though the
   classifier had always had it.
9. **Nobody has published re-anchoring rates.** The numbers in §3 appear to be
   the only measurements of block- and span-level re-anchoring over real
   version-control history. That is a reason to distrust them until someone
   reproduces them, not a reason to be pleased.

---

## Appendix A — files

```
experiments/D8-identity/
  anchor_eval.py      stored-id vs computed-anchor, head to head over real history
  anchor_eval2.py     + independent line-correspondence oracle
  anchor_eval3.py     + block-type breakdown and the hardened acceptance policy
  e1_stock_git_ids.sh block ids under stock git: 5 cases
  e2_controlled.sh    controlled arms incl. the clean-merge id collision
  e3_dup.sh           copy-paste duplicate id through a clean merge
  e4_uniqueness.py    is a quote a unique key in real prose?
  e5_ordering.sh      fractional index vs line order under stock git
  e6_transclude.py    transclusion blast radius + loud failure + ambiguity
  e7_span_anchor.py   sub-block span anchoring (the standoff case)
  e8_twostage.py      one-stage vs two-stage span anchoring
  e9_headings.py      heading-slug link rot and uniqueness
  id_samples.md       every id scheme embedded in a real markdown line
  corpora/            rust-lang/book, obsidian-help, commonmark-spec (partial clones)
```

## Appendix B — primary sources

- W3C Web Annotation Data Model — https://www.w3.org/TR/annotation-model/
- Renear, Mylonas & Durand, *Refining our Notion of What Text Really Is* —
  http://hdl.handle.net/2142/9407
- DeRose, Durand, Mylonas & Renear 1990 — doi:10.1007/BF02941632 (no OA)
- TEI P5 ch. 21, Non-hierarchical Structures —
  https://tei-c.org/release/doc/tei-p5-doc/en/html/NH.html
- Sperberg-McQueen & Huitfeldt, GODDAG — http://cmsmcq.com/2000/poddp2000.html
- Thompson & McKelvie 1997 — https://www.ltg.ed.ac.uk/~ht/sgmleu97.html
- Bański, Balisage 2010 —
  https://www.balisage.net/Proceedings/vol5/html/Banski01/BalisageVol5-Banski01.html
- Brush, Bargeron, Gupta & Cadiz, *Robust Annotation Positioning in Digital
  Documents*, CHI 2001 / MSR-TR-2000-95 —
  https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2000-95.pdf
- Phelps & Wilensky, *Robust Hyperlinks and Locations*, D-Lib July/Aug 2000 —
  https://www.dlib.org/dlib/july00/wilensky/07wilensky.html
- Hypothes.is fuzzy anchoring — https://web.hypothes.is/blog/fuzzy-anchoring/ ;
  client source `src/annotator/anchoring/match-quote.ts`, `types.ts`
- Peritext — https://www.inkandswitch.com/peritext/
- Automerge rich text — https://automerge.org/docs/reference/documents/rich-text/
- Kleppmann et al., *Interleaving anomalies in collaborative text editors* —
  https://martin.kleppmann.com/papers/interleaving-papoc19.pdf
- Figma, *Realtime Editing of Ordered Sequences* —
  https://www.figma.com/blog/realtime-editing-of-ordered-sequences/
- Evan Wallace, fractional indexing —
  https://madebyevan.com/algos/crdt-fractional-indexing/
- RFC 9562 (UUIDv7) — https://www.rfc-editor.org/rfc/rfc9562.html ;
  ULID spec — https://github.com/ulid/spec
- OASIS DITA 1.3 — http://docs.oasis-open.org/dita/dita/v1.3/os/part1-base/
- AsciiDoc tagged regions —
  https://docs.asciidoctor.org/asciidoc/latest/directives/include-tagged-regions/
- Nelson, *Xanalogical Structure* — http://xanadu.com.au/ted/XUsurvey/xuDation.html ;
  Wolf, *The Curse of Xanadu*, Wired 3.06 — https://www.wired.com/1995/06/xanadu/ ;
  Udanax — http://udanax.xanadu.com/
- Obsidian help vault (a real corpus, cloned and censused) —
  https://github.com/obsidianmd/obsidian-help
- Foam link reference generation —
  https://github.com/foambubble/foam (`generate-link-references.ts`, CHANGELOG 0.15.6)
- Logseq DB version — https://github.com/logseq/docs/blob/master/db-version-changes.md
- XPointer `xpointer()` scheme, still a Working Draft —
  https://www.w3.org/TR/xptr-xpointer/
- CommonMark 0.31.2 (contains no attribute syntax) — https://spec.commonmark.org/0.31.2/

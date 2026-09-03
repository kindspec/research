# D4 — Reconciling real-time collaboration (CRDT) with git's asynchronous model

Research date 2026-08-28. Companion to `RESEARCH.md`, which already settled:
CodeMirror 6 + plain-text CRDT over markdown source (not ProseMirror+turndown),
and measured that concurrent git writers fail (12/12 pushes rejected, 8/8 rebases
conflicted, index.lock contention) — hence an assumed single-writer-per-repo
constraint.

**This document overturns that last constraint.** The `index.lock` result is an
artifact of the working tree, not a property of git. Measured below.

Every number marked **[measured]** was produced on this machine. Every quote is
from a primary source with a URL.

---

## 0. The three decisions, answered up front

**Is a CRDT needed at all, and at which layer?**
Yes, but only at the *live session* layer, over the *bytes of one file*. Not over
a structured document, not over the repo. The canonical artifact stays the
plain-text file in git. This is the architecture Nextcloud Text has run in
production for six years, the architecture the eg-walker paper formalises, and
the architecture Ink & Switch's own `pushwork` uses.

**How do sessions and commits coexist?**
Sessions own an in-memory CRDT plus a durable op log in a sidecar store outside
the repo. Git commits are produced *from* the CRDT's materialised text, by a
single serialising process, using bare-repo `commit-tree` + `update-ref` CAS with
a retry loop. Out-of-band file changes (a `git pull`, a desktop sync client) are
folded *into* the live CRDT via a text-diff splice (`Automerge.updateText` /
equivalent), not by clobbering it.

**Can CRDT history live in git without being an opaque blob?**
Mostly no, and it should not have to. Two facts settle it:
- Automerge 3.4.1 stores the **complete** editing history of the standard 182k-insert
  trace in **129,248 bytes against 104,852 bytes of plain text — 1.23×** **[measured]**.
  Storable, but binary and undiffable; gzip actually *grows* it (129,277 B).
- Loro's `exportJsonUpdates()` is the **only** text-native, round-trippable CRDT
  oplog in existence — human-readable JSON with named peers, Lamport clocks and
  explicit `deps` **[measured, exact round-trip]** — at 16× plain text raw
  (209 KB gzipped for a 105 KB document).

So: git holds text. History-of-record is git's own DAG. The CRDT op log is a
*cache* in a sidecar, truncatable, never the source of truth.

---

## 1. Ink & Switch — what they built, what they kept, what they abandoned

### 1.1 Upwelling (2023) — the explicit "merge what you can, fork what you can't"

<https://www.inkandswitch.com/upwelling/>

**Built:** a ProseMirror web editor over a **fork of Automerge** (rich text +
per-author attribution, features not then in stable Automerge), Node server for
storage and live sync, PWA that works offline. Model: a linear **stack** (main),
**drafts** (lightweight branches) that **float** — when any draft merges to the
stack, it is merged into every other open draft. Async transport was literally a
**tarball** of the stack + drafts + a metadata Automerge doc.

**Interview findings, verbatim:**

> "Writers don't want first drafts visible to the editor." — Journalist

> "If you don't want the editor or writer to see what you're doing until you're
> done, sometimes you make a copy of the doc and work in the copy, then paste it
> back (otherwise you have 17 canonical documents and people are editing the
> wrong thing)." — Newspaper Editor

> "I hate Track Changes! I'm dyslexic. I find reading Track Changes to be nearly
> impossible. If someone has heavily edited, I have to accept all of them and
> read it." — Fiction Writer

> "My preferred workflow for Word would be to pass it around one by one—a linear
> order, rather than having two people working simultaneously." — Educational Writer

They name the problem the **"fishbowl effect"**: real-time collaboration makes
writers feel watched. Users' existing workarounds were airplane mode and
copy-paste-into-a-new-doc.

**Their assessment of git, verbatim:**

> "Git cannot compare or merge files from WYSIWYG editors such as Microsoft
> Word, and although it is possible to train writers in Markdown or other
> plain-text formats, Markdown files in a Git repository lack important features
> from Google Docs and Word, such as associating comments and discussion threads
> with text passages. The command line interface is unfamiliar to most people who
> are not software developers, and graphical user interfaces for Git are cluttered
> with complex concepts such as commit hashes and visualizations of non-linear
> branching and merging histories."

**What they abandoned, and why:**

1. **Git-like dependent branches.** "We experimented with 'Git-like' dependent
   drafts in Upwelling and found that it made the model more difficult for users
   to understand and did not add meaningful value. Moreover, it encouraged the use
   of long-lived branches, which in turn increases the risk of conflicts."
2. **Single-author drafts** — too rigid; an editor fixing a typo had to open a
   whole new dependent draft.
3. **History rewriting (cherry-pick, squash, interactive rebase).** "we decided
   that adding similar features to Upwelling would introduce too much complexity
   and add too little value." Their substitute: if a reviewer wants only part of a
   draft, they *edit the draft* to undo the rest.
4. **Sophisticated conflict resolution.** "since semantic conflicts cannot always
   be detected, human review of the merged result is necessary in any case. We
   therefore prioritized a design that makes reviewing changes easy rather than
   investing in more sophisticated merge behavior."

**The admitted CRDT failure mode, verbatim** — this is the honest cost of
character-level merge on prose:

> "if 'white' is changed to 'frosty' in one draft and to 'soft' in another draft,
> the merged result is either 'frostysoft' or 'softfrosty.' This result requires
> human follow-up to correct"

> "Another syntactic conflict occurs when a writer deletes a paragraph in one
> draft, while a writer in another draft makes an edit within that paragraph. With
> current CRDT algorithms, any inserted characters are preserved in the place
> where the paragraph used to be, even though the surrounding text has gone."

**Two findings with direct architectural consequences for us:**

- *Concurrent merges break the review guarantee.* "Two collaborators
  concurrently merging different drafts onto the stack would violate the principle
  that the reviewed draft is identical to the final document… The Upwelling
  prototype currently does not enforce this rule." Their proposed fixes are both
  **serialisation**: "keep track of the latest stack on a server, and to allow
  writers to merge onto the stack only if approved by the server", or "design a
  custom CRDT that allows merges of drafts to only happen sequentially."
  → *A single serialising writer is what Ink & Switch concluded they needed too.*

- *You cannot redact CRDT history.* "Because Upwelling currently records and
  shares the full history of a document, there is no way to excise names or
  information that may have appeared in earlier drafts. **This is a problem caused
  by keeping too much history**… CRDTs are currently designed to guarantee that
  users will see the same results from the same inputs. In this case, users will
  want to see the same results from different inputs."
  → *A hard argument against CRDT-as-canonical for any document with sources,
  PII, or salary numbers in an early draft.*

**Why they stopped:** Upwelling was not killed for failure; it was superseded.
Patchwork (2024) explicitly cites it as too formal: "Upwelling, an earlier lab
project, was even more formal, requiring authors to create an explicit 'draft
layer' before making any edits."

### 1.2 Patchwork (2024–2026) — the successor, and what it concluded

<https://www.inkandswitch.com/patchwork/notebook/2024-version-control/> (11 notes,
Feb–Jul 2024) and the 2026 notes at `/patchwork/notebook/`.

Chapter by chapter, the durable findings:

- **03 Dynamic history.** Auto-save every keystroke; offer *flexible groupings*
  of that history rather than forcing commits. "in practice, though, it seems most
  cases can be supported by a small set of groupings, such as by author and edit
  time."
- **04 Diff visualisations.** "We've found that character count isn't the right
  metric for prose, but word/sentence counts are better." Team favourites:
  hover-to-show-deleted, and a "minibar" positional summary.
- **05 Edit groups — the anti-branching experiment.** Design principle:
  **"formality on demand"**. "Contributors just edit directly on the doc. No
  branches or drafts, no suggested changes." Retroactive rationale and grouping
  after the fact. Finding: "seeing recent edits and being able to easily revert
  them feels very useful—it's a form of undo that's not limited to the time order
  that edits happened." And a caution against over-structuring: "Because writing
  edits often consist of many small changes that could be independently merged,
  it's possible that grouping edits into atomically revertable units isn't a
  common need in this domain."
- **06 Simple branching — the design that stuck.** "**Users still edit on main by
  default**, so you can send a doc to someone and they can make changes without
  understanding branches." Rules: no branching from branches; no naming required
  (an AI can name it later); **merging deletes the branch — "There's no cleanup
  step."** You can create a branch *retroactively* from your current edit session.
- **07 AI bots.** Bots propose branches and appear as users in history. Bots are
  prompts, so they are themselves versioned documents.
- **08 Why Automerge.** "Automerge never deletes anything. It stores every change
  made to a document with efficient compression… Automerge can compute an exact
  difference between two points in history of a document. It doesn't need to
  resort to heuristics because the full edit history is tracked."
- **09 Version history as chat.** "We've found that the brief AI summaries are a
  remarkably useful way to understand writing edits at a high level—**more
  successful than any of our other diff visualizations so far**."
- **10 Beyond prose.** Ported to tldraw and to a Handsontable spreadsheet.
  "Branching and timeline are low-effort to add if you've already built your app on
  Automerge. Diff view and comments are more domain specific." Notable spreadsheet
  finding: "One challenge we encountered was diff that distinguish manually-edited
  cells versus recalculated formula result cells."
- **11 Universal comments.** A generic comment layer parameterised by app-defined
  **pointers** (a text span, a cell range, a shape set). Pointers were then reused
  to power diff views.

**What Patchwork became by 2026:** not a version-control product. The 2026 notes
(`account-history`, `breadboard`, `chitter-chatter`, `progressions`, `tasks-01/02`)
show it as a full malleable-software environment — an Automerge-backed OS-like
workspace with LLM-generated tools, spatial canvases, and a distributed task
framework. Version control is now infrastructure, not the pitch. **Git is never
mentioned in any 2026 Patchwork note.**

The version-control *line of research* moved to **Backstitch**.

### 1.3 Backstitch (2024–2026) — the sharpest evidence, and it is anti-git

<https://www.inkandswitch.com/project/backstitch/notebook/01/> and Dispatch 018.

Version control for Godot scene files, for **kids** learning game dev with the
Endless Foundation. Godot scenes *are already text files* in git — the exact
premise of this project — and Ink & Switch's finding is that this does not work:

> "When two developers modify the same scene, Git may report a conflict even when
> changes are semantically independent. One developer adds platforms at the top of
> a level while another adds coins at the bottom, but if these touch adjacent lines
> in the text file, Git sees a conflict. The resulting file contains conflict
> markers and won't load in Godot."

> "When using Git with Godot, it's unfortunately easy to corrupt scene files when
> merging, rendering them unable to load. **We've heard that this leads game
> developers to isolate their work to avoid conflicts** — one developer works on
> assets, another on layout — instead of collaborating freely."

Their design principle is worth stealing verbatim:

> "we can guarantee that you always get a loadable scene when merging. This
> doesn't mean that all changes can be combined automatically — conflicts are
> still possible… But we believe it's better to have a project you can open and
> work on within the editor than a project that won't open until you fix a bunch
> of conflicts in the abstract text representation."

Dispatch 018 (2026-06-30) reports the reception:

> "Godot project files are serialized as text and can be stored in a traditional
> VCS like git, but those files are not robust to merges when conflicts occur,
> leading to broken projects which are difficult or impossible to recover. This is
> an untenable situation for these students, and for all game devs using Godot."

> "In April, Lilith Duncan… presented Backstitch at GodotCon, and received a
> euphoric response. **The Backstitch discord is flooding with devs eager for a
> way out of git hell**, and there's already a shipping game that was built with
> Backstitch."

The talk's title is **"Beyond Git: Real-Time Version Control for Godot."**
`inkandswitch/backstitch` — 239★, pushed 2026-08-28.

**Read this carefully.** It is *demand evidence for version control*, and
*rejection evidence for git as the mechanism*, from the same population, in the
same breath. A plaintext-in-git product must have an answer for "merge produces a
file that will not open."

### 1.4 pushwork — Ink & Switch's actual answer to "git-backed files"

`inkandswitch/pushwork`, Apache-2.0, TypeScript, 54★, pushed 2026-08-13.
README, verbatim:

> "_Bidirectional directory synchronization using Automerge CRDTs._ pushwork turns
> any directory into a synchronized, conflict-free replicated folder… **It feels a
> bit like Git, but the 'merge' is a CRDT: there are no merge conflicts to resolve
> by hand**, and character-level edits to text files combine cleanly."

Verbs: `init`, `clone`, `sync`, `save` (alias `commit`), `status`, `diff`,
`heads`, `cut`/`paste`/`snarfs` (stash). Ignore file `.pushworkignore` (gitignore
syntax), attributes file `.pushworkattributes` ("modeled on `.gitattributes`").
Storage under `.pushwork/storage/` (Automerge `NodeFSStorageAdapter`).
**`.git` is on the always-ignored list.**

So Ink & Switch's shipped position is: **replace git, keep git's vocabulary.**
They reproduced init/clone/commit/status/diff/stash/ignore/attributes because
users need those concepts — and threw away git's storage and merge because those
are what break.

**The single most useful line of source in this whole investigation** is how
pushwork folds a disk-side file change into the CRDT
(`src/shapes/file.ts`, `applyFileEntry`):

```js
if (typeof d.content === "string" && typeof fresh.content === "string") {
    Automerge.updateText(d, ["content"], fresh.content);
} else {
    d.content = fresh.content;   // bytes: last-writer-wins
}
```

with the doc comment: *"Text content is merged with Automerge.updateText so
concurrent character edits converge; bytes and ImmutableString are atomic (last
writer wins)."*

`updateText` diffs the new whole-file text against the CRDT's current text and
applies the minimal insert/delete ops. **This is the reconciliation primitive the
whole "plain text canonical + live CRDT" architecture needs, and it ships in
stock Automerge.** Yjs has no equivalent in core; you diff and splice yourself.

Caveat, stated plainly: a whole-file text diff cannot recover *intent*. A moved
paragraph reads as delete+insert. It is safe and convergent, not smart.

### 1.5 Livelymerge (2026) — "Convergence Is Not Enough"

<https://www.inkandswitch.com/livelymerge/notebook/lm-02/> (Alex Warth, Dan
Ingalls, Peter van Hardenberg, 2026-07-27). Their newest and most important
negative result. Whole Lively-Kernel heap as an Automerge doc.

The worked example: a linked list `1→2→3→4`; A swaps 2 and 3, B concurrently
swaps 3 and 4. Automerge converges deterministically — onto either a **truncated
list** or an **infinite cycle**.

> "Let me emphasize: Automerge did nothing wrong here. Both clients converge on
> the same result, deterministically, exactly as promised. The trouble is that
> replaying B's writes after A's is not the same as performing B's intent after
> A's… **The merge replays effects, not intents**, and the programmer's
> invariants… were never written down anywhere that Automerge could see.
> Convergence is not enough."

> "all bets are off when you compose these datatypes — and this sort of thing
> happens very often in programming! The merge orders whole transactions, but it
> still replays their writes blindly, so **any invariant that spans more than one
> property or object is invisible to it**."

Their listed examples are exactly our data model: a doubly-linked list; a tree
(*"two users concurrently reparenting the same morph can break this today"*); "a
cached count or index that must agree with the collection it summarizes"; "an
'each element appears exactly once' constraint on anything."

Read *cached count that must agree with the collection* as **a spreadsheet
formula result**, and *tree invariant* as **a slide deck or a canvas z-order**.

Their honest mitigation: "With some careful programming… we've been able to build
a system that holds up well in day-to-day multi-user use. (Careful programming
isn't a solution, of course; it's what you do while you're waiting for one.)"

Their proposed direction — **merge-aware datatypes** — is to record the *type's*
high-level operations rather than the pointer writes, citing Kleppmann et al.'s
move-operation-for-replicated-trees as precedent, and noting the cost: "an
operation that was valid when it ran can be retroactively invalidated when an
operation with a lower timestamp arrives late, so users can watch previously-
accepted work get rolled back."

They also flag **Coln** (Kleppmann, Vincent Liu, Owen Lynch et al., part of the
ARIA Safeguarded AI programme) — a mergeable database where *"if merging would
break a constraint, the merge is simply refused, and it's up to the user (or an
AI) to get the data back into a state that satisfies the constraints before the
merge is allowed."* Refusing to merge is a legitimate design point. Git already
does it; it is called a conflict.

### 1.6 Peritext (CSCW 2022) — why markdown-in-a-plain-text-CRDT is *defensible*

<https://www.inkandswitch.com/peritext/>

The famous anomaly, verbatim from the source:

> Alice: `**The fox** jumped.` Bob: `The **fox jumped.**` merge →
> `**The **fox** jumped.**` → "The users' intent hasn't been preserved — both users
> bolded the word 'fox', but in the merged result it has ended up non-bold."

> "As another example, if two people created a top-level heading by inserting `#`
> at the beginning of a line, that would become `##` denoting a second level
> heading."

Two things the prior pass's decision rests on, and which Peritext itself supplies:

1. **Yjs has the same class of bug.** "This is the approach used by the CRDT
   library Yjs… Yjs has the most full-featured rich-text CRDT available today…
   However, it suffers from the anomaly shown in this section." So switching to a
   rich-text CRDT does not buy immunity, only a different anomaly set.
2. **Automerge's JSON representation is *worse*.** Two users independently
   formatting "jumped." — one bold, one italic — merges to
   `[{text:"The fox "},{text:"jumped.",bold},{text:"jumped.",italic}]`, rendering
   *"The fox jumped.jumped."* — "The last word has become duplicated!"

Peritext's own conclusion for our purposes: **there is no representation with no
anomaly.** The choice is which anomaly you accept. The prior pass chose
markdown-in-plain-text-CRDT because its anomalies are visible in a source editor
and user-fixable, while reserialization damage is silent and whole-file. Peritext
does not contradict that; it establishes the baseline that everyone has a bug.

### 1.7 Cambria (2020) — format evolution, and one finding we should copy exactly

<https://www.inkandswitch.com/cambria/>. `cambria-project` 698★, **last pushed
2024-06-14** — dormant. Treat as a paper, not a dependency.

The finding that matters most here:

> "**Data translations in decentralized systems should be performed on read, not
> on write.** Some of our early prototypes for storing documents that were
> compatible with multiple schemas performed data translations at write time…
> We eventually realized this was a flawed strategy. It struggled to handle new
> schemas getting added later on, after the write had already happened… So we
> switched to a simpler strategy: **store a log of raw writes in the form of the
> writer schema, and translate between versions at read time.**"

Direct consequence for us: when the `.sheet.md` or `.calc.md` format evolves, do
**not** rewrite the corpus. Keep files in the schema they were written in, tag
them, and lens on read. Rewriting on upgrade is a whole-repo diff — the same sin
as Pithy's turndown pass, at project scale.

Their second finding is the honest limit:

> "Interoperability requires trading off between irreconcilable design goals" —
> consistency, conservation ("neither side operates on data they can't observe"),
> and predictability ("the local intent of every operation is preserved"). "Sometimes,
> there are no perfect options."

And: "**Lenses require well-defined transformations.**" `firstName`+`lastName` →
`fullName` "works reliably in one direction" only. A lens that is not bijective is
not a lens.

### 1.8 The local-first essay (2019) — the seven ideals, and their own indictment

<https://www.inkandswitch.com/essay/local-first/>

Seven ideals: 1. No spinners; 2. Your work is not trapped on one device;
3. The network is optional; 4. Seamless collaboration with your colleagues;
5. The Long Now; 6. Security and privacy by default; 7. You retain ultimate
ownership and control.

Their scorecard puts **Git+GitHub at ✓ ✗/— ✓ — ✓ — ✓** and says:

> "Git and GitHub… are perhaps the closest thing we have to a true local-first
> software package."

with exactly two weaknesses:

> "1. Git is excellent for asynchronous collaboration… But Git has no capability
> for real-time, fine-grained collaboration… 2. Git is highly optimized for code
> and similar line-based text files; other file formats are treated as binary
> blobs that cannot meaningfully be edited or merged."

**Weakness 1 is precisely the gap this project fills.** Weakness 2 is why the
prior pass's plaintext-formats decision (`.sheet.md`, `.calc.md`, `.fods`, daff)
is load-bearing rather than aesthetic.

And the essay's own closing self-criticism, which is the strongest single
argument against CRDT-as-canonical:

> "**CRDTs accumulate a large change history, which creates performance problems.**
> Our team used PushPin for 'real' documents such as sprint planning. Performance
> and memory/disk usage quickly became a problem because CRDTs store all history,
> including character-by-character text edits. These pile up, but **can't easily be
> truncated because it's impossible to know when someone might reconnect to your
> shared document after six months away** and need to merge changes from that point
> forward."

Balanced by their pro-CRDT finding:

> "**Conflicts are not as significant a problem as we feared.** …we found that
> users surprisingly rarely encounter conflicts in their work when collaborating
> with others, and that generic resolution mechanisms work well… in all the
> prototypes we developed, we found that the default merge semantics to be
> sufficient."

### 1.9 Keyhive / BeeKEM / Subduction — their current auth and sync work

`inkandswitch/keyhive` 239★, pushed today. `inkandswitch/subduction` ("Sync
protocol for hash-linked data", Rust, Apache-2.0) 106★, pushed 2026-08-25 — and
it is now pushwork's **default** sync backend
(`wss://subduction.sync.inkandswitch.com`), displacing `wss://sync3.automerge.org`.

Keyhive 06 (2026-07-31, guest post by Derek Yen, NYU) is the mature framing of
why decentralised auth is hard, and it hands us the right mental model:

> "One of the primary functions of a central server is that it **serializes** the
> operations performed by group members, meaning that it imposes a canonical
> ordering of events… in the decentralized setting, where there is no central
> server, there is no authority to create this ordering."

> "For a familiar example of the causal order, **the commit graph of a git repo
> can be viewed as implementing a causal order over commits.**"

Two things follow. First, git's DAG *is* a causal order — we are not fighting the
model, we are reusing it. Second, if you want a canonical order (and for
"the file on main is the file") you need a serialiser. That is not a failure of
ambition; it is the same conclusion Upwelling reached and GitLab implements.

Relevance caveat: Keyhive solves **per-document E2EE and capability delegation
without a server** — which the prior pass flagged as an open trap ("per-file
sharing forces an auth server; no forge has per-file read ACLs"). Keyhive is the
research answer to that trap. It is pre-alpha.

---

## 2. The CRDT engines, honestly

All registry facts verified live 2026-08-28 against `registry.npmjs.org`,
`crates.io/api`, and the GitHub API. Size/time figures marked **[measured]** were
run against the canonical `automerge-paper` trace (259,778 txns / 182,315 inserted
chars / 77,463 deleted / 104,852-byte final text). Plain-text baseline:
**104,852 B raw, 27,485 B gzip -9.**

### 2.1 The headline measurement

```
PLAIN TEXT (final document)             raw= 104852B  gzip=  27485B  raw/text=1.00x
yjs 13.6.32 updateV2 gc=true            raw= 159926B  gzip=  68750B  raw/text=1.53x
yjs 13.6.32 updateV2 gc=false           raw= 226978B  gzip=  88717B  raw/text=2.16x
yjs 13.6.32 updateV1 gc=true            raw= 311035B  gzip= 105753B  raw/text=2.97x
loro 1.15.0 snapshot (full history)     raw= 251454B  gzip= 192474B  raw/text=2.40x
loro 1.15.0 shallow-snapshot            raw=  64952B  gzip=  56012B  raw/text=0.62x
automerge 3.4.1 save (full history)     raw= 129248B  gzip= 129277B  raw/text=1.23x
loro 1.15.0 exportJsonUpdates() (TEXT)  raw=1685066B  gzip= 209332B  raw/text=16.07x
```

**Automerge 3 stores the complete editing history in 1.23× the plain text.** This
inverts the folk wisdom that Automerge is the bloated one. Yjs's 1.53× is *not
comparable*: with `gc=true` it has already discarded deleted content and never had
a change DAG at all. Note also that Automerge's output is incompressible (gzip
*grows* it) because every column is already DEFLATEd.

Time and memory **[measured]**, Node 24.15, `--expose-gc`:

| | apply trace | reload from disk | heapUsed | RSS |
|---|---|---|---|---|
| Yjs 13.6.32 (gc=true) | 1,218 ms | 22 ms | 64.5 MB | 286 MB |
| Loro 1.15.0 | 578 ms | **3 ms** (snapshot) | 59.3 MB | 178 MB |
| Automerge 3.4.1 (259,778 changes) | 22,590 ms | 820 ms | 59.3 MB | 335 MB |
| Automerge 3.4.1 (1 giant change) | 109,275 ms | 163 ms | 59.4 MB | 387 MB |

Automerge is **18–90× slower to apply** than Yjs through the JS binding, and
scaling *within* a single change is superlinear (10k ops → 516 ms; 40k → 1,887 ms;
80k → 5,331 ms). Corroborated by open upstream issues: automerge#906 "Unexpected
quadratic performance loading a collaborative text document" (open since 2024-04),
#1244 "Loading large doc blocks main thread for 10+ seconds" (2026-01), #1387
"Severe write throughput regression… ~19× slowdown" (2026-05), #1084 "Load peak
memory is high".

### 2.2 Comparison table

| | Format | Binary? | Full history retainable? | Size on 182k/77k trace | Licence (registry-verified) | Latest | Health |
|---|---|---|---|---|---|---|---|
| **Automerge 3.4.1** | Columnar chunks, RLE/delta/ULEB128, DEFLATE per column | Yes | **Yes, by design** — change DAG always kept | **129,248 B (1.23×)** | MIT (npm + crates) | js 3.4.1 (2026-08-12); crate 0.11.0 | 6,541★, pushed today; 46k npm/wk |
| **Yjs 13.6.32** | lib0 varint/bit-packed updates (v1/v2) + state vectors | Yes | **No** — no op log, no DAG | 159,926 B (1.53×) gc=true; 226,978 B (2.16×) gc=false | MIT | 13.6.32 (2026-08-04) | 22,716★; **8.4M npm/wk** |
| **Loro 1.15.0** | OpLog + DocState "fast snapshot"; **also JSON oplog** | Yes (+ JSON) | **Yes**, opt-out via shallow snapshot | 251,454 B (2.40×) full; 64,952 B (0.62×) shallow | MIT | 1.15.0 (2026-08-27) | 6,081★; 164k npm/wk |
| **diamond-types** | Eg-walker columnar event graph + LZ4 | Yes | Yes (event graph *is* the storage) | paper: 20%–3× final text | ISC (no LICENSE file on GitHub) | **crate 1.0.0 (2022-08-25)**; repo active 2026-07-31 | 1,834★; 56 npm/wk |
| **cola 0.5.1** | Replica metadata only; **stores neither text nor history** | opt-in | N/A | n/a | MIT | 0.5.1 (2025-07-06) | 564★; last push 2026-01-13 |
| **collabs 0.13.4** | Custom per-Collab encodings | Yes | Framework-dependent | n/a | Apache-2.0 | **npm 2023-09-06** | 288★; one cosmetic commit in 18 mo — **dormant** |
| **Braid** | HTTP + patches; text-native | **No** | Server's choice | n/a | **braid-http declares NO licence** | 1.4.11 (2026-08-10) | 75 npm/wk |

Also: `yrs` (Rust Yjs) 0.27.4, 2026-08-22, MIT, **2.7M downloads** — the healthiest
Rust CRDT by adoption, and independent of Kevin Jahns's bus factor.

### 2.3 Engine notes that change the decision

**Automerge 3 is released and it is a memory rewrite, not a format change.**
From <https://automerge.org/blog/automerge-3/>: *"we've cut that down memory usage
by over 10x"*; *"Pasting Moby Dick into an Automerge 2 document consumed 700MB… in
Automerge 3 it only consumes 1.3Mb"*; a document that *"hadn't loaded after 17
hours loading in 9 seconds"*. And: *"Automerge 3.0 uses the same file format as
Automerge 2"* — the change is that the compressed columnar representation is now
used *at runtime* too. The binary format spec
(<https://automerge.org/automerge-binary-format-spec/>) is still marked **draft**.
Sync is Bloom-filter-based (`BITS_PER_ENTRY = 10`, `NUM_PROBES = 7`, 1% false
positive rate), per Kleppmann & Howard, arXiv:2012.00472.

**`automerge-repo` is still `2.6.0-alpha.3` (2026-08-20).** The sync/storage layer
you would actually build on has never had a stable release. That is a real risk.

**Yjs does not retain history, and this is the fact that decides the layer
question.** `gc = true` by default; `structs/GC.js` shows a garbage-collected
struct carries only `{id, length}`. From the README: *"we can garbage collect
tombstones if we don't care about the order of the structs anymore."* What Yjs
keeps is a *state*, not a log — no change DAG, no commit grouping, no timestamps,
no authorship. `Y.UndoManager` is in-memory and does not survive reload. Snapshots
require `gc: false` (2.16× plain text) and still give you only "restore to a state
vector."

**Yjs v14 has been in RC since 2022-08-18** — 47 pre-releases, newest
`v14.0.0-rc.24` (2026-07-15), and `dist-tags` are inconsistent (`next: 14.0.0-8` is
*older* than `beta: 14.0.0-16`). The prior pass's advice to pin `yjs ^13.6.32`
against `y-codemirror.next ^0.3.6` is confirmed correct. (`y-codemirror.next@0.3.6`
was republished 2026-08-18 — actively maintained.)

**Loro is the only engine with a text-diffable history format.**
`exportJsonUpdates()` produces round-trippable JSON with `schema_version`, named
`peers`, `lamport`, explicit `deps`, and readable ops:

```json
{"id":"0@0","timestamp":0,"deps":[],"lamport":0,"msg":null,
 "ops":[{"container":"cid:root-t:Text",
         "content":{"type":"insert","pos":0,"text":"\\documentclass[a4paper..."}}]}
```

Round-trip via `importJsonUpdates` is exact **[measured]**. `redactJsonUpdates()`
exists for selective history scrubbing — which is exactly the capability Upwelling
said CRDTs lack. `shallow-snapshot` is documented as *"like Git's shallow clone"*,
claims 70–90% smaller (**measured 74.2%**), with the stated cost: *"⚠️ Peers can
only sync if they have versions after the shallow snapshot point."* Loro 1.0
committed to format stability.

Automerge's nearest equivalent, `decodeChange` into JS objects, measured
**39,425,568 B — 376× plain text**, with no import path back.

**diamond-types is a research artifact, not a dependency.** crates.io stops at
`1.0.0` (2022-08-25); the repo's own README says *"the package published to cargo
is quite out of date, both in terms of API and performance."* Cargo.toml on master
says `version = "2.0.0"`, unreleased. No LICENSE file on GitHub. **Text only** —
*"Work is underway to add support for other JSON-style data types."* Steal the
algorithm; do not depend on the crate.

**Braid is expired.** Verified against the IETF datatracker API:

```
draft-toomim-httpbis-braid-http     rev 04  2024-05-22  EXPIRED, individual
draft-toomim-httpbis-versions       rev 04  2026-03-02  active, individual, expires 2026-09-03
draft-toomim-httpbis-range-patch    rev 00  2020-05-21  EXPIRED
draft-toomim-httpbis-merge-types    rev 00  2020-05-21  EXPIRED
draft-ietf-httpapi-patch-byterange  rev 04  2026-07-06  WG DOCUMENT (httpapi) — until 2027-01-07
```

The core Braid-HTTP draft was never adopted and *"has no formal standing in the
IETF standards process."* `braid-http@1.4.11` declares **no licence at all** — not
permissive, all-rights-reserved. The real standards-track work is
`draft-ietf-httpapi-patch-byterange` (Byte Range PATCH), which shed the Braid
branding and is a live working-group document. Track that; ignore Braid.

**collabs is dormant** — last npm publish 2023-09-06, one typo-fix commit in 18
months, 337 downloads/week. Intellectually the most interesting for a *table*
product (composable per-column merge semantics), but do not ship it.

### 2.4 Eg-walker — the paper that changes the architecture, not the library choice

Gentle & Kleppmann, *Collaborative Text Editing with Eg-walker: Better, Faster,
Smaller*, EuroSys 2025, arXiv:2409.14252.

The defining design statement:

> "Unlike existing algorithms, we invoke the CRDT only to perform merges of
> concurrent operations, and we **discard its state as soon as the merge is
> complete. We never write the CRDT state to disk and never send it over the
> network.**"

And the sentence that validates our whole architecture:

> "In contrast, OT and Eg-walker can load documents **orders of magnitude faster
> than CRDTs by caching the final document state on disk, and loading just this
> data (essentially a plain text file)**. Eg-walker and OT only need to load the
> event graph when merging concurrent changes or to reconstruct old document
> versions. **Document edits by the local user or applying non-concurrent remote
> events do not need the event graph.**"

That is, formally: *plain text is the working representation; the op log is a
sidecar consulted only for merge and history.* Not a hack — a EuroSys result.

Their **"critical version"** optimisation is the mechanism: a version that
partitions the graph so everything before happened-before everything after. *"Any
time the version of the event graph processed so far is critical, we can discard
the internal state."* A commit on a single-writer main branch **is** a critical
version. Mostly-sequential documents replay almost nothing.

Measured results from the paper:
- *"the steady-state memory use of Eg-walker is 1–2 orders of magnitude lower than
  the best CRDT… Yjs has up to a 3× greater memory use than our reference CRDT,
  and Automerge an order of magnitude greater."* (Automerge 3 postdates this.)
- *"OT performance degrades dramatically on the asynchronous traces (6 seconds for
  A1, and 1 hour for A2)… whereas Eg-walker remains fast (160,000× faster in the
  case of A2)."*
- Storage: *"The overhead of storing the event graph is between 20% and 3× the
  final plain text file size."* Format is columnar (event type/start/run-length;
  inserted content LZ4-compressed; parents; event-ID runs), *"inspired by the
  Automerge CRDT library… We also borrow some bit-packing tricks from the Yjs CRDT
  library."*

Honest caveat on their comparison: *"To ensure a like-for-like comparison we have
disabled Eg-walker's built-in LZ4 and Automerge's built-in gzip compression."* So
the published Automerge bars are uncompressed; my measured 1.23× is Automerge with
compression on. Not unfair, but not the comparison a product ships.

**Delightful detail:** their asynchronous benchmark traces A1 and A2 are
reconstructed **from git history** — `src/node.cc` from Node.js and `Makefile`
from git itself. *"The event graph mirrors the branching/merging of Git commits."*

---

## 3. The CRDT-in-git problem

### 3.1 Nobody stores CRDT ops in git, and the search space is empty

GitHub repo search, 2026-08-28:
- `crdt git merge driver in:name,description` → **0 results.**
- `yjs git markdown in:name,description` → **1 result**: `pooriaarab/gitmarkdown`,
  **3 stars**, MIT, created 2026-02-06 — *"Collaborative markdown editor with
  two-way GitHub sync, real-time collaboration… Built with Next.js, Tiptap,
  Firebase, and Yjs."* Its Yjs state lives in **Firebase Realtime Database**; git
  is only a sync *target* via the GitHub API. And it uses Tiptap → it will hit the
  reserialization problem documented in `RESEARCH.md` §2.

There is no meaningful prior art for CRDT-ops-committed-to-git. The one project
that markets the exact pitch keeps the CRDT outside git — the same choice as
Nextcloud, the same choice as pushwork.

Adjacent-but-not-CRDT systems worth naming so they are not re-investigated:
**Dolt** (git-like SQL, but three-way cell merge over a Merkle B-tree, not a
CRDT); **Pijul/Darcs** (patch theory — a different merge *algebra* with
associativity guarantees git lacks, and effectively zero adoption).

### 3.2 Nextcloud Text — the closest real system, read from source

`github.com/nextcloud/text`, AGPL-3.0, v10.0.0-dev. Yjs + ProseMirror over real
markdown files on disk, in production for six years. Its architecture *is* the
architecture in question, so its failure modes are our failure modes.

**Where the CRDT lives** (`lib/Service/DocumentService.php`):

```php
public function getStateFile(int $documentId): ISimpleFile {
    $filename = $documentId . '.yjs';
    ...
    return $this->appData->getFolder('documents')->getFile($filename);
}
```

The Yjs document is a `{documentId}.yjs` **binary sidecar in app data — not in the
user's file tree, not versioned, not visible.** Steps live in a SQL table
(`oc_text_steps`), sessions in `oc_text_sessions`. The markdown file is canonical.

**Session teardown deletes the CRDT** (`resetDocument`):

```php
$this->stepMapper->deleteAll($documentId);
$this->sessionMapper->deleteByDocumentId($documentId);
$this->documentMapper->delete($document);
$this->getStateFile($documentId)->delete();
```

guarded by `hasUnsavedChanges()` (steps version ≠ last-saved version). So the CRDT
is *explicitly ephemeral*, torn down at quiesce.

**The flush window is 10 seconds:** `public const int AUTOSAVE_MINIMUM_DELAY = 10;`

**External-change detection** (`assertNoOutsideConflict`): compare stored mtime and
etag against the file; if they differ, compare a content checksum; on mismatch:

```php
throw new DocumentSaveConflictException('File changed in the meantime from outside');
```

Two things about that checksum are worth flagging:

```php
public static function computeCheckSum(string $content): string {
    return hash('crc32', $content);
}
```

It is **CRC32 — 32 bits**, i.e. a ~1-in-4-billion chance of silently missing a
divergence per comparison. And it was only added in **September–October 2025**
(issue/PR #7677, *"feat: Save a checksum for documents and use it to detect
conflicts"*, backported to stable31/stable32). Before that, six years of
production with **only mtime+etag** to detect that someone had edited the file
underneath a live session. Use a cryptographic hash; this is a cheap correctness
win they took five years to make and still under-specified.

**The documented failure mode, from the maintainer** — issue #6914, *"Fix 409
(Conflict) causes and handling"*, opened 2025-02-19 by `max-nextcloud`, **still
open**:

> "Still some users are reporting changes being lost while editing with > 10
> people in text. 409 Responses are showing in their logs."

> "Sync requests can trigger 409 responses if the underlying files etag and mtime
> differ from the document records values. **This will happen if a file is saved
> through a different mechanism such as desktop client sync or restoring an old
> version.**"

> "The 409 will 'only' cause the editor to display the conflict screen with both
> options to pick from."

So: an out-of-band write (a desktop sync client — read: **`git pull`**) during a
live session produces a **whole-document pick-one dialog**, not a merge. That is
the honest state of the art in the only shipping system with this architecture.

**And the markdown round-trip is conceded to be unsolvable.** Issue #3477,
*"Detect changes to markdown syntax and open in code editing mode"*, opened
2022-11-23 by `max-nextcloud`, **still open in 2026**:

> "A lot of work is going into preserving the markdown syntax already but **the
> architecture of texts wysiwyg editing and limitations of the underlying
> libraries make it close to impossible to preserve all syntax out there.**"

Their proposal is capitulation: *"When opening a .md file… check if it would be
serialized to the same code. If serializing the document would change the syntax
open the document in code editing mode."* Its parent, #593 *"Markdown files from
external editors lose formatting on save"*, ran to **123 comments** before closing.

The `keepSyntax` hack itself (`src/markdownit/keepSyntax.js`) is one regex:

```js
const escaped = /(\n(?<linestart>[#\-*+>])|(?<special>[`*\\~[\]]+))/
```

It tags ten literal characters with a ProseMirror mark so the serializer will not
escape them — and `src/extensions/KeepSyntax.js` **removes the mark on any manual
edit** (`onUpdate` strips it from any node that is not a single text character), so
the escaping comes back the moment a user touches it.

**Live data-loss bug, filed two days ago:** #9108 (2026-08-26, open) —
*"Editing a Markdown file with inline (data: URI) images deletes them from the
file."* From the report: *"the image is absent from the document Text builds, so
the next save writes the file back without it. **A one-word text edit is enough to
destroy every picture in the document.**"*

That is the canonical shape of the failure: an editor that cannot represent
something *silently deletes it on save*, because the save path is
"serialize whatever the editor model holds" rather than "apply a diff."

**This is the single strongest vindication of the prior pass's editor decision.**
The bug class does not exist when the editor buffer *is* the file bytes.

### 3.3 The rest of the field

**Logseq — the most consequential data point.** Logseq shipped **2.0 Beta (the "DB
version")** in July 2026: notes now live in a local **SQLite database as the
canonical source of truth**, not a folder of markdown files. The product **split
in two** — the file-based markdown app became "Logseq OG", moved to its own repo,
receiving security and Electron maintenance but **no new features**. Realtime sync
(RTC) is paid and invite-only. Markdown is now an *export*, and re-supporting
markdown files in the DB version is described as still-being-researched.

The flagship markdown-files-are-canonical PKM abandoned markdown-files-as-canonical
in the same release that shipped realtime sync. Whatever else that is, it is not
encouraging for the premise. It is also the clearest possible statement that
*"files as canonical" and "realtime multiplayer" pull in opposite directions* — and
that if you keep files canonical you must accept the constraints in §5.

**tldraw** — proprietary (`NOASSERTION`, verified in the prior pass). Its sync is a
server-authoritative store, not a peer CRDT. Ink & Switch's Patchwork tldraw
integration replaced the persistence layer with Automerge rather than using
tldraw's.

**Anytype** (`any-sync`) — CRDT-based, but its on-disk representation is opaque
protobuf in a local store. Local-first, not file-first.

**SilverBullet** — markdown files + a server, single-user-per-file; no multiplayer
CRDT. It is the existence proof that CodeMirror-over-markdown-source works, not
that it multiplayers.

**Etherpad** — changeset-based OT, not a CRDT, with the full changeset log in SQL.
**CryptPad** — ChainPad, an OT variant with Nakamoto-style consensus over a
hash-linked history. Both keep their history in a database, not in files.

### 3.4 The critical question: is "ephemeral CRDT, plain text canonical, commit on quiesce" sound?

**Yes — with four failure modes that must each be engineered, not hoped away.**

The architecture is validated three independent ways: Nextcloud Text ships it,
eg-walker formalises it (*"caching the final document state on disk, and loading
just this data (essentially a plain text file)"*), and pushwork implements it with
`Automerge.updateText` as the reconciliation primitive.

**Failure mode 1 — the session server dies before flushing.**
You lose the debounce window. The industry numbers, verified from source:
- **Hocuspocus** (`packages/server/src/Hocuspocus.ts`): `debounce: 2_000`,
  `maxDebounce: 10_000` — **up to 10 seconds** of edits.
- **Nextcloud Text**: `AUTOSAVE_MINIMUM_DELAY = 10` — same order.
- **`y-websocket`'s bundled backend** is *"a simple in-memory backend that can
  persist to databases, but it can't be scaled easily."* With no persistence
  adapter configured, the document is lost when the last client disconnects.

**Mitigation:** persist the *op log* (not the materialised doc) synchronously on
every update to a local append-only store, and debounce only the git commit. A
10-second loss window on the file is acceptable; a 10-second loss window on the
op log is not, because the op log is what lets a reconnecting client rebase.
Hocuspocus's own docs warn that with `unloadImmediately: false`, *"persistence is
no longer guaranteed by the time `disconnect()` resolves."*

**Failure mode 2 — the file changes on disk during a live session.**
This is the one everybody gets wrong. Three possible behaviours:
- *Clobber the disk* (what a naive autosave does) → silently destroys the
  `git pull`. Unacceptable.
- *Clobber the CRDT* → silently destroys in-flight typing. Unacceptable.
- *Splice the disk content into the CRDT as ops* → `Automerge.updateText(d,
  ["content"], newDiskText)`. Convergent, preserves both, loses intent
  (a moved paragraph reads as delete+insert). **This is the right answer**, and it
  is what pushwork does.

Nextcloud's answer — a 409 and a two-option dialog — is worse, and it is what you
get if you only detect divergence rather than reconcile it. Detect **and** splice.

**Failure mode 3 — undetected divergence.**
Nextcloud used mtime+etag alone for six years, then added CRC32. Use SHA-256 of the
last-written bytes, recheck on an inotify/FSEvents watch *and* before every write,
and treat the check as a precondition, not a heuristic.

**Failure mode 4 — the reconnecting client with a stale op log.**
Ink & Switch's own indictment: *"can't easily be truncated because it's impossible
to know when someone might reconnect… after six months away."* But in *this*
architecture the answer is easy and git gives it to us: **git history is the
fallback.** A client whose op log predates the sidecar's truncation point does not
need to merge ops — it needs a three-way merge between its local text, the merge
base commit, and current `main`. That is `git merge-file` (plus `daff` for CSV).
The CRDT's job ends at the boundary of what the sidecar retains; git's job starts
there. **This is what a git-backed product buys that a pure-CRDT product does not
have: a principled truncation point.**

---

## 4. The single-writer question — and the measurement that overturns it

### 4.1 The crux experiment

The prior pass measured 8 concurrent `git add` → 1 success, 7 `index.lock`
failures, and concluded a single writer per repository was mandatory. **That
result is real but it measures the working tree, not git.**

Reproduced here for the contrast, `git 2.47.3` **[measured]**:

```
=== CONTRAST: 8 concurrent 'git add' in a WORKING TREE
      3 fatal: Unable to create '.../wt/.git/index.lock': File exists.
=== git status of index after:
A  f1.txt  A  f4.txt  A  f5.txt  A  f6.txt  A  f8.txt
?? f2.txt  ?? f3.txt  ?? f7.txt          # 3 of 8 writers' work simply gone
```

Now the same workload against a **bare** repo, each writer using its own
`GIT_INDEX_FILE`, building the tree with `read-tree`/`update-index`/`write-tree`,
committing with `commit-tree`, and publishing with `update-ref <new> <old>`
compare-and-swap plus a retry loop **[measured]**:

```
=== 8 concurrent writers x 25 commits each, bare repo, private index, update-ref CAS
writer=3 committed=25 cas_retries=54  gaveup=0
writer=5 committed=25 cas_retries=120 gaveup=0
writer=7 committed=25 cas_retries=122 gaveup=0
writer=6 committed=25 cas_retries=127 gaveup=0
writer=8 committed=25 cas_retries=133 gaveup=0
writer=4 committed=25 cas_retries=143 gaveup=0
writer=1 committed=25 cas_retries=147 gaveup=0
writer=2 committed=25 cas_retries=158 gaveup=0
real 0m3.215s
=== commits on main (expect 200 + 1 seed):  201
```

**200/200 commits landed. Zero loss. Zero index.lock errors. 3.2 seconds.**

And the harder case — **all eight writers appending to the same file**, re-reading
the current content at CAS time and re-applying their intent **[measured]**:

```
=== 8 writers x 20 appends to THE SAME FILE, CAS + re-read-and-reapply
real 0m2.675s
=== final shared.md line count (expect 1 header + 160):  161
=== per-writer counts (expect 20 each):
     20 w1   20 w2   20 w3   20 w4   20 w5   20 w6   20 w7   20 w8
```

**160/160 lines landed on the same file. Zero loss.**

Scale test, 32 concurrent writers × 10 commits to the same file **[measured]**:

```
real 0m12.333s
=== total lines (expect 321):  321
=== distinct writers landed:   32
=== total commits:             321
```

320/320. Throughput degrades from ~62 to ~26 commits/sec as retries grow roughly
linearly with concurrency (~24 retries per successful commit at 32-way) — this is a
shell-subprocess-bound number and libgit2 in-process would be far higher, but the
*shape* is the point: **CAS retry converges; it does not lose work.**

### 4.2 What this changes

The correct statement is not "git cannot take concurrent writers." It is:

> **A git *working tree* has exactly one index and therefore exactly one writer. A
> bare git repository is a content-addressed object store with per-ref
> compare-and-swap, and takes as many concurrent writers as you can throw at it,
> provided each writer (a) builds its tree without a shared index and (b) retries
> on CAS failure by re-reading and re-applying its intent.**

`git push` rejection is not a different problem — it is the *same* CAS, with the
retry loop replaced by `git pull --rebase`, which re-applies your intent as a
*textual patch* rather than as a semantic operation. That is why the prior pass
measured 8/8 rebase conflicts: rebase re-applies a diff, and a diff of concurrent
prose does not apply. Re-applying the *intent* (splice this text at this CRDT
anchor) always applies.

**Consequence for this project:** the writer does not have to be the *only* writer.
It has to be the only *worktree*. Different agents, sessions, devices and an
AI bot can all commit concurrently to one bare repo. That materially changes what
is buildable.

### 4.3 What the forges actually do — every one of them serialises, and here is how

**Gitea/Forgejo — per-request temporary clone.** Verified in
`services/repository/files/temp_repo.go`:

```go
func NewTemporaryUploadRepository(repo *repo_model.Repository) (*TemporaryUploadRepository, error) {
    basePath, _, cleanup, err := repo_module.CreateTemporaryGitRepo("upload")
```

then `Clone(ctx, branch, bare)` with `Shared: true`, `CommitTree`, and:

```go
func (t *TemporaryUploadRepository) Push(ctx, doer, commitHash, branch string, force bool) error {
    ... if git.IsErrPushOutOfDate(err) { return err } else if git.IsErrPushRejected(err) { return err }
```

Every web-editor commit gets **its own throwaway clone and its own index**, then
pushes back. Rejection is surfaced to the user, **not retried**. That is the same
insight as §4.1 with the retry loop missing — Gitea makes the user hit reload.
Their `modules/globallock` package (Redis- or memory-backed `Lock`/`TryLock`) is
used for exactly one thing: `services/pull/check.go`.

**GitLab/Gitaly — an explicit, documented, PostgreSQL-backed per-repository write
lock.** From `doc/serialized_writes.md` ("Praefect Serialized Writes"):

> "The problem is that at the `prepared` phase, **on-disk ref locks have already
> been taken**. With two concurrent transactions T1 and T2 updating overlapping
> refs A and B: Node 1: T1 locks A, T2 locks B; Node 2: T2 locks A, T1 locks B.
> Each transaction is now waiting for the other… **The cluster is deadlocked.**"

> "The fix is to serialize transactions **before** any node has taken an on-disk
> ref lock. If only one transaction per repository can advance past this point at a
> time, lock acquisition order is globally consistent."

They needed an **upstream Git change** to get a hook phase early enough:

> "`60d8c1e97d62c27ef60db0bc3d5deadd6dfdb98d` — *refs: add 'preparing' phase to the
> reference-transaction hook* — First released in **Git v2.54.0**."

Phase → action: `PREPARING_PHASE` → `WriteLockManager.Lock` (block until exclusive);
`PREPARED_PHASE` → renew; `COMMITTED_PHASE` → unlock. And on *why not a mutex*:

> "A `sync.Mutex` (or any per-process construct) only serializes within a single
> Praefect… With an in-process lock, two Praefect instances would each happily
> believe they hold the lock for the same repository at the same time."

**And GitLab is leaving filesystem git entirely.** `doc/mvcc_rpc_flow.md` documents
an MVCC backend where **S3 is the source of truth**, with a manifest pointer
(`GIT_MVCC_MANIFEST_PATH`) and a local cache:

> "This is to ensure that every Git command spawned during the lifetime of this RPC
> uses the same manifest hash, otherwise Git commands for the same RPCs might
> execute on different 'snapshot' of the Git repository, **which can lead to data
> corruption**."

The largest self-hosted git platform in the world is converting git storage into a
manifest-over-object-store MVCC system because filesystem git does not survive
concurrency at scale. That is corroboration, not contradiction, of §4.1 — they
kept the *object model* and replaced the *filesystem locking*.

**Gerrit** is the clean case: it builds commits in-memory with JGit's
`ObjectInserter` and publishes with `RefUpdate` compare-and-swap. **No index, no
worktree, ever.** It also pioneered the `reftable` storage format, now in
upstream git — verified available in `git 2.47.3` via
`git init --ref-format=reftable`, which produces a `reftable/` directory instead of
per-ref `.lock` files.

### 4.4 The five architectures, adjudicated

| | Real systems | Verdict |
|---|---|---|
| **(a) one repo per user, cross-sync via merge/PR** | GitHub fork model; Upwelling's abandoned dependent drafts | **No.** Upwelling: dependent branches "made the model more difficult for users to understand and did not add meaningful value… encouraged the use of long-lived branches, which in turn increases the risk of conflicts." N× storage, N× sync, and the merge is still textual. |
| **(b) single server process owns the repo** | Gitea (temp clone per request), Gitaly (PG lock), Nextcloud Text | **Yes, as the *deployment* model — but §4.1 shows it need not be a single *process*.** A bare repo + CAS is a *protocol*, not a process. That distinction is what keeps it "git-backed": any git client can clone, any commit is a real commit, `git log` works, and the server is not a required intermediary for reading. |
| **(c) per-file locking** | `git lfs lock` — server-enforced: *"any updated files matching one of 'their' locks will halt the push"*; Perforce; Office lock files | **Useful garnish, not the architecture.** It exists and is enforced at push time, but locking is the thing Upwelling's users were working *around* (airplane mode, copy-the-doc). Worth offering for binary assets (`.fods`, images) where merge is impossible. |
| **(d) branch-per-editor with automatic merge** | Upwelling's drafts; Patchwork's simple branches | **Yes for the *user-facing* model, no for the *storage* model.** Patchwork's rules are the design: edit on main by default, no branching from branches, no forced naming, merge deletes the branch. Ephemeral refs under `refs/drafts/*`, not long-lived branches. |
| **(e) CRDT live layer, git archival with periodic snapshots** | Nextcloud Text, eg-walker, pushwork | **Yes — this is the recommendation.** With the crucial amendment that git is not merely archival: it is the merge fallback when the CRDT op log has been truncated (§3.4, failure mode 4). |

**Recommended: (e) + (b)-as-protocol + (d)-as-UI + (c) for binaries.**

---

## 5. "Do users want branches?" — the evidence

The evidence is unusually good, and unusually two-sided.

**Yes, with the ceremony removed.** Patchwork 06 is the clearest statement:

> "We think that 'branch' is a great name and a great concept, and if we can
> provide a simple, comprehensible UI and avoid footguns we believe it's something
> writers can learn and benefit from."

with the constraints that made it work: *"Users still edit on main by default, so
you can send a doc to someone and they can make changes without understanding
branches"*; *"There's no branching from branches"*; *"You don't need to name
branches when you create them"*; *"When you merge the branch, it's deleted. There's
no cleanup step."* And branches can be created **retroactively** from an edit
session already in progress.

Patchwork 10 generalises it: *"For each case where we've applied branching to a new
domain (writing, diagrams, and spreadsheets), we've quickly found useful ideas for
applying them. This suggests branching is a powerful general primitive for all
kinds of creative work."* With a specifically spreadsheet-shaped finding: *"We saw
the value in using branches as a way to try out alternate what-if scenarios, a
common scenario in spreadsheets and financial modeling."*

**But what users actually asked for, in their own words, was not branching — it
was privacy and legible review.** The Upwelling interviews:

> "Writers don't want first drafts visible to the editor."

> "There can be hundreds of comments, and you can't search them. If something
> changed in the doc, we bold it."

> "I hate Track Changes! I'm dyslexic."

Branching is Ink & Switch's *answer*; the *ask* was creative privacy plus a
readable diff. Note that Patchwork 05 (Edit Groups) tested the no-branch answer to
the same ask and also found it useful — *"seeing recent edits and being able to
easily revert them feels very useful—it's a form of undo that's not limited to the
time order that edits happened."* Both designs satisfy the ask. That is evidence
the ask is privacy-and-review, not branching per se.

**The most surprising finding is that AI summaries beat every diff visualisation
they built.** Patchwork 09: *"We've found that the brief AI summaries are a
remarkably useful way to understand writing edits at a high level—**more successful
than any of our other diff visualizations so far**."* They tried git-style
+/- stats (rejected: *"character count isn't the right metric for prose, but
word/sentence counts are better"*), blobs, a positional "minibar", and per-section
stats. An LLM-written commit message beat all of them.

**And Backstitch is the demand evidence outside prose**: kids and Godot developers
"flooding the discord… eager for a way out of git hell," for a tool whose talk is
titled *Beyond Git*. They want versioning. They do not want git's interface or
git's merge failures.

**Sober counterweight.** Patchwork 06 itself concedes *"we've already encountered
occasional cases where"* one-level branching is not enough, and Patchwork 05 warns
*"it's possible that grouping edits into atomically revertable units isn't a common
need in this domain."* Nobody has shipped this to a non-developer population at
scale and reported retention. This remains a research finding, not a market fact.

---

## 6. Offline-first beyond CRDTs — what suffices when a CRDT is too heavy

The literature's own answer, from the people who wrote the CRDT essay:

> "**Conflicts are not as significant a problem as we feared.** …users surprisingly
> rarely encounter conflicts in their work when collaborating with others, and that
> generic resolution mechanisms work well… **Users have an intuitive sense of human
> collaboration and avoid creating conflicts with their collaborators.** For example,
> when users are collaboratively editing an article, they may agree in advance who
> will be working on which section for a period of time."

Combine that with the eg-walker result — *"Document edits by the local user or
applying non-concurrent remote events do not need the event graph"* — and Upwelling's
*"perhaps the most straightforward way of reducing the risk of conflicts is to limit
the number of edits made in each draft"*, and the minimum viable offline stack is:

1. **A durable local copy of the bytes.** This is what git already is. Ideal #3 of
   the local-first essay ("the network is optional") is satisfied by `git clone`
   with no additional machinery.
2. **A merge base.** Three-way merge needs only the common ancestor, which git
   stores. `git merge-file` on markdown; `daff` on CSV (verified in the prior pass
   to handle column insert and row reorder correctly); `.fods` gets cell-level
   three-way merge free.
3. **A per-file "who is editing this" presence signal**, so the social mechanism
   the essay describes ("I'm working on the introduction today") can operate.
   Cheaper than any CRDT and, on the essay's own evidence, more effective.
4. **A CRDT only for the concurrent-live-cursors case** — genuinely simultaneous
   typing in one file. This is a small fraction of sessions and it is exactly where
   three-way merge is unusable.

That is the ladder. Note that (1)–(3) require **no CRDT at all** and cover
offline-edit-then-reconcile completely. The CRDT earns its place only at rung 4.

The alternatives to a full CRDT, ranked by weight:
- **Three-way merge with a merge base** — git's own model. Free, works offline,
  fails on prose paragraph-level concurrent edits.
- **cola's model** — CRDT metadata as a *sidecar*, with your `String` staying the
  real content. `struct Document { buffer: String, crdt: Replica }`. Architecturally
  the best fit for git-backed; but text-only, one maintainer, low velocity.
- **Eg-walker's model** — event graph on disk, materialised text cached, CRDT state
  built only for a merge and then discarded. This *is* the right model; it is just
  not yet a shippable library.
- **Server-authoritative OT with a version vector** (`@codemirror/collab`'s
  authority model, Etherpad, CryptPad) — fine when you already accept a single
  serialising server, which §4.3 shows every forge does. Its weakness is exactly the
  eg-walker finding: *"6 seconds for A1, and 1 hour for A2"* on long-diverged
  branches. Offline-heavy usage is where OT dies.

---

## 7. The adversarial pass

### 7.1 The case AGAINST any CRDT in this system

1. **Every claimed CRDT benefit is already provided by git, worse-but-adequately.**
   History, branching, merge, offline, provenance, blame, three-way merge — git has
   all of it, and it is the product's premise. Adding a CRDT means two
   history-of-record systems that must be kept consistent. That is the most
   expensive kind of complexity.
2. **The CRDT cannot be the canonical artifact without destroying the premise.**
   Automerge's `.automerge` file is binary, undiffable, unmergeable by git, and
   monotonically growing. Loro's shallow-snapshot and Yjs's `gc` both *destroy
   history* to control size. Once the canonical file is a CRDT blob, `git diff`
   shows nothing, GitHub renders nothing, `grep` finds nothing, and every claim in
   the pitch deck is false.
3. **The CRDT cannot forget, and documents must.** Upwelling, verbatim: *"there is
   no way to excise names or information that may have appeared in earlier drafts.
   **This is a problem caused by keeping too much history.**"* Any product touching
   PII, salaries, sources, or unreleased numbers needs redaction. Git offers
   `filter-repo`; a CRDT offers a research problem. (Loro's `redactJsonUpdates` is
   the only shipped exception, and it breaks sync with older peers.)
4. **Convergence is not correctness, and our data model is exactly the vulnerable
   kind.** Livelymerge, 2026: *"any invariant that spans more than one property or
   object is invisible to it"* — naming cached counts, trees, and uniqueness
   constraints. A spreadsheet's cached formula results, a slide deck's ordering, a
   canvas's z-order and parent links are all in that set. `RESEARCH.md` §3 already
   measured the analogous git failure (480 instead of 660 on a clean auto-merge);
   a CRDT does not fix it, it just makes it converge silently rather than
   conflict noisily.
5. **The engines are not where the marketing says.** `automerge-repo` is
   `2.6.0-alpha.3` after four years. Yjs v14 has been in RC since **2022**. Yjs is
   bus-factor-1 on 8.4M weekly downloads. `collabs` is dormant, `diamond-types`'
   published crate is four years old with no LICENSE file, Braid's core draft is
   **expired** and its reference implementation declares **no licence**.
6. **The performance is not free.** Automerge 3.4.1 took **22.6 seconds** to apply
   a 105 KB single-author editing trace through the JS binding **[measured]**, with
   superlinear scaling inside a change and four open upstream issues about exactly
   this. A canvas emits ops far faster than a text editor.
7. **The single measured user-research signal points at git as the villain.** Ink &
   Switch's own current version-control project is titled *"Beyond Git."* Its
   community is described as *"eager for a way out of git hell."* Building the
   CRDT and keeping git means shipping the thing they want to escape, plus a
   second system.
8. **The prior pass's own numbers say most sessions do not need it.** Eg-walker:
   *"Anecdotal evidence suggests that the majority of documents in practice are
   sequentially edited – that is, they either have a single author, or multiple
   authors who take turns."* Local-first: *"conflicts are not as significant a
   problem as we feared."* You would be paying a permanent architectural tax for a
   minority case.

### 7.2 The case FOR

1. **Weakness #1 of git, named by the people who like git most.** Local-first
   essay: *"Git has no capability for real-time, fine-grained collaboration."* That
   is the entire product gap. Without a CRDT (or OT) there is no multiplayer, and
   without multiplayer this is a git client with a nice editor, competing with
   Obsidian, whose largest SKU git gives away for free.
2. **`git pull` during an open editor is not optional, and only a CRDT handles it
   without a dialog.** Even single-user, multi-device, a background fetch will
   rewrite a file that an editor holds. `Automerge.updateText(doc, path, diskText)`
   folds it in convergently. Nextcloud, which lacks this, shows the user a
   pick-one 409 screen — and has an open maintainer issue saying people lose work.
3. **The measured size objection is dead.** Automerge 3.4.1 holds the **complete**
   history of a 105 KB document's 259,778 edits in **129 KB — 1.23× the plain
   text** **[measured]**. Eg-walker: *"between 20% and 3× the final plain text file
   size."* This was the strongest anti-CRDT argument in 2019 and it no longer holds.
4. **The memory objection is dead too.** Automerge 3: *"we've cut that down memory
   usage by over 10x"*; Moby Dick 700 MB → **1.3 MB**; a document that
   *"hadn't loaded after 17 hours loading in 9 seconds."*
5. **The architecture has a formal foundation, not just a hack.** Eg-walker,
   EuroSys 2025: *"we invoke the CRDT only to perform merges of concurrent
   operations, and we discard its state as soon as the merge is complete. We never
   write the CRDT state to disk."* Plain-text-canonical-with-ephemeral-CRDT is a
   published result, and its "critical version" concept maps exactly onto a commit.
6. **Git's merge is measurably worse than a CRDT's on this content.**
   `RESEARCH.md` measured git auto-merging two CSV row-inserts into a silently
   wrong total (480 vs 660). Ink & Switch measured git corrupting Godot scenes into
   unloadable files. A character-level CRDT produces `frostysoft` — *visible*
   garbage a human fixes in two seconds — instead of a plausible wrong number.
   **Visible-wrong beats silently-wrong.** That is the strongest technical argument
   for the CRDT, and it applies most where the prior pass found git weakest.
7. **The library risk is manageable.** Automerge 3.4.1 (MIT, pushed today, 6,541★),
   Loro 1.15.0 (MIT, pushed yesterday, 6,081★), Yjs 13.6.32 (MIT, 8.4M/wk), yrs
   0.27.4 (MIT, 2.7M downloads). Four viable engines, all permissively licensed,
   all shipping. Contrast the prior pass's HyperFormula/Handsontable licensing trap.

### 7.3 Adjudication

**A CRDT belongs in this system, in one narrow place, and nowhere else.**

The two positions are not actually opposed, because they are about different
layers. Every anti-CRDT argument (1–4, 8) is an argument against **CRDT as
canonical storage**. Every pro-CRDT argument (1, 2, 6) is an argument for **CRDT as
live-session merge machinery**. Both are correct.

The synthesis is eg-walker's, and it is a published result rather than a
compromise: *the materialised text is what you store and load; the CRDT is
constructed to perform a merge and discarded.* Git holds the text. Git's DAG is
the history of record. The CRDT op log is a truncatable sidecar whose only jobs are
(i) merging concurrent keystrokes within a live session, and (ii) folding an
out-of-band file change into that session without a dialog. When the sidecar is
gone or stale, git's three-way merge takes over — and unlike a pure-CRDT system,
**there is something to fall back to.** That is the specific advantage of building
this on git, and it should be stated as the thesis rather than discovered later.

Arguments 5 and 6 of the against-case (immaturity, performance) survive as
engineering constraints, not as objections:
- Do not put a CRDT under the spreadsheet grid or the canvas. Livelymerge's
  cached-count and tree-invariant failures are exactly those data models, and
  Automerge's superlinear per-change cost is exactly their op rate. Use
  named-column addressing + `daff` (already decided) and last-writer-wins per
  cell/shape with presence.
- Do not adopt `automerge-repo` while it is alpha. Own the session server.
- Pin `yjs ^13.6.32` / `y-codemirror.next ^0.3.6`, as already decided, and treat
  the v14 RC train as a four-year-old risk, not an upgrade path.

And argument 7 (the "Beyond Git" signal) is the real strategic risk, not a
technical one. Ink & Switch's evidence says users want versioning and reject git's
interface and merge behaviour. This product's answer must be that git is the
**substrate**, never the **interface** — Pithy's leaked string
`"Complete or abort the rebase in a terminal."` is the failure mode to design
against. §4.1's CAS-retry result is what makes that possible: the user never sees a
push rejection, because the server retries.

---

## 8. Recommendation

**Layer:** plain-text CRDT over the bytes of a single file, live-session only.
Not over a structured document (Peritext's own evidence: every representation has
an anomaly, and rich-text CRDTs break the file). Not over the repo (Livelymerge:
convergence is not correctness, and cross-object invariants are invisible).

**Engine:** **Automerge 3.4.1** for documents if history-in-the-sidecar matters
(1.23× plain text for the *complete* DAG, `updateText` for disk reconciliation,
MIT, active). **Yjs 13.6.32 + y-codemirror.next 0.3.6** if the priority is a
battle-tested CodeMirror binding and 18× faster apply, accepting that it keeps no
history at all (which is fine — **git keeps the history**). Given that git is the
history of record, Yjs's amnesia is a feature, not a defect, and its
`y-codemirror.next` binding is the one the prior pass already chose. **Choose Yjs;
keep Automerge's `updateText` pattern as the reconciliation design.** Watch Loro
as the upgrade path — it is the only engine whose history is text-diffable, which
is the one thing that could later make CRDT-history-in-git viable.

**Persistence:** op log appended synchronously to a per-document sidecar outside
the repo (`.gws/sessions/<id>.log`), gitignored, truncated at every commit —
because a commit is a critical version.

**Commits:** a serialising committer against a **bare** repo using
`hash-object`/`read-tree`(private `GIT_INDEX_FILE`)/`write-tree`/`commit-tree`/
`update-ref` CAS with re-read-and-reapply retry. Never a shared working tree.
Never `git add`. Never surface a push rejection.

**Disk reconciliation:** SHA-256 precondition on every write; on divergence,
splice the disk content into the live CRDT via a text diff — never clobber either
side, never show a pick-one dialog.

**Branches:** Patchwork's rules exactly — edit on main by default, one level only,
optional names, retroactive creation from a live session, merge deletes the branch,
AI-written summaries as the primary diff surface.

**Do not:** put a CRDT under sheets or canvas; store CRDT state in the repo; adopt
`automerge-repo` while alpha; build on Braid, collabs, or `diamond-types` as
published; or let the word "rebase" reach a user.

---

## Sources

**Ink & Switch** — Upwelling <https://www.inkandswitch.com/upwelling/> ·
Patchwork notebook <https://www.inkandswitch.com/patchwork/notebook/2024-version-control/01/>…`/11/`
and `/patchwork/notebook/{account-history,breadboard,chitter-chatter,progressions,tasks-01,tasks-02}/` ·
Backstitch <https://www.inkandswitch.com/project/backstitch/notebook/01/> ·
Livelymerge <https://www.inkandswitch.com/livelymerge/notebook/lm-01/>, `/lm-02/` ·
Peritext <https://www.inkandswitch.com/peritext/> ·
Cambria <https://www.inkandswitch.com/cambria/> ·
Local-first <https://www.inkandswitch.com/essay/local-first/> ·
Keyhive <https://www.inkandswitch.com/keyhive/notebook/06/> ·
Universal Version Control <https://www.inkandswitch.com/universal-version-control/> ·
Dispatches 017, 018 · `github.com/inkandswitch/{pushwork,backstitch,keyhive,subduction,cambria-project}`

**Papers** — Gentle & Kleppmann, *Collaborative Text Editing with Eg-walker*,
EuroSys 2025, <https://arxiv.org/abs/2409.14252> · Kleppmann & Howard, *Byzantine
Eventual Consistency*, <https://arxiv.org/abs/2012.00472>

**Engines** — <https://automerge.org/blog/automerge-3/> ·
<https://automerge.org/automerge-binary-format-spec/> ·
<https://automerge.org/blog/2026-july/> · `github.com/yjs/yjs` ·
`github.com/loro-dev/loro` · `github.com/noib3/cola` ·
`github.com/josephg/diamond-types` · `github.com/composablesys/collabs` ·
registry.npmjs.org / crates.io (queried 2026-08-28)

**IETF** — <https://datatracker.ietf.org/doc/draft-toomim-httpbis-braid-http/>
(expired) · <https://datatracker.ietf.org/doc/draft-ietf-httpapi-patch-byterange/>
(WG document)

**Systems** — `github.com/nextcloud/text` (`lib/Service/DocumentService.php`,
`src/markdownit/keepSyntax.js`, `src/extensions/KeepSyntax.js`; issues #593, #3477,
#3570, #6914, #7677, #9108) · `github.com/go-gitea/gitea`
(`services/repository/files/temp_repo.go`, `modules/globallock/`) ·
`gitlab.com/gitlab-org/gitaly` (`doc/serialized_writes.md`, `doc/mvcc_rpc_flow.md`) ·
`github.com/ueberdosis/hocuspocus` (`packages/server/src/Hocuspocus.ts`) ·
`github.com/yjs/y-websocket` · `github.com/git-lfs/git-lfs`
(`docs/api/locking.md`) · Logseq 2.0 DB-version announcement, July 2026

**Experiments** — scratchpad `gitexp/{writer.sh,writer2.sh}`, git 2.47.3, all
output reproduced inline in §4.1.

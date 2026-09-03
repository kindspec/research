# Storage + collaboration layer for a git-backed Google Workspace

Research date: **2026-08-28**. Method: live fetches (curl/WebFetch), `api.github.com` via
authenticated `gh`, and **local git/tool experiments run on this machine** (git 2.47.3).

Labels used throughout:

- **VERIFIED** — I fetched the page/repo/API myself on 2026-08-28, or measured it locally.
- **MEASURED** — I ran the command on this machine; the command is shown.
- **REPORTED** — secondhand (search snippet, third-party blog); not independently confirmed.
- **NOT FOUND** — I looked and could not confirm it exists. Stated explicitly rather than guessed.

---

## Headline findings

1. **The editor buffer must *be* the markdown file** — CodeMirror 6 + `Y.Text`, not ProseMirror with a
   markdown projection. Peritext's anomaly is real but narrow (concurrent *overlapping mark* ops only),
   visible and repairable; reserialization is common, whole-file, silent, destroys git's diff, and has
   two shipping counterexamples. **This reverses an earlier draft of §G.** (§G.0, §A.1)
2. **Committing a CRDT binary to git is not viable** — not for size (measured: only ~11% worse than
   Markdown) but because git answers two divergent `.ydoc` files with `Cannot merge binary files`, and
   the only resolution discards one collaborator entirely. (§A.3)
3. **Auto-commit + multiplayer is non-functional on git.** Measured: **12/12 pushes rejected** for the
   second concurrent writer; with a `pull --rebase` retry loop on a shared paragraph, **8/8 rebases
   conflicted and 0% of the second writer's work landed.** This is the biggest risk in the design. (§B.6)
4. **The architecture that works is already shipping** — CollabMD runs CodeMirror 6 + `y-codemirror.next`
   over the markdown source with the filesystem as source of truth; Keystatic proves the
   CRDT-session-plus-git-commit half (via Markdoc, not CommonMark); Zed does the same for code. (§A.3, §E.1, §G.0)
5. **Tables are solved; prose nearly is.** `daff` did correct cell-level three-way CSV merges on every
   case tested. `mergiraf` and `difftastic` **do not support Markdown or CSV at all**. `weave` (v0.5.2,
   6 months old) merged prose git could not, and correctly refused every dangerous case. (§C)
6. **File count is not the problem; attachments are.** Measured: 100k Markdown files behave fine
   (`git status` <0.1 s), but 21 revisions of one 2 MB image cost **20.6× a single copy**, while 21
   revisions of a 1.1 MB text file cost **less than one copy**. (§D)
7. **jj has the best model and the wrong storage.** Its change-ID/`evolog` split is the only clean
   answer to "every save is a commit" — but it has no LFS after 4.5 years, defaults to refusing files
   over 1 MiB, and **its conflicts cannot be represented in plain git.** (§B.3)

---

## The core tension, stated precisely

A CRDT wants to be the document: it owns identity, history, and merge semantics, and its on-disk
form is an opaque binary op-log. Git wants a file: an opaque-to-it byte string it snapshots, diffs
line-wise, and merges line-wise. These are two different *systems of record* for the same document.
You cannot have both be authoritative. Every real system resolves this by **demoting one of them**.

The finding of this research is that the working systems all demote the CRDT to a *session
transport*, and keep the plain file as the durable artifact. The systems that try to make the CRDT
durable inside git produce something git cannot read, diff, or merge — which forfeits the entire
reason for choosing git.

---

## A. CRDTs and files

### A.1 The killer result: Markdown cannot be the CRDT

This is the single most important prior finding, and it is not a matter of engineering effort — it
is a semantic impossibility.

**VERIFIED** — Ink & Switch, *Peritext: A CRDT for Rich-Text Collaboration*, Geoffrey Litt, Slim
(Sarah) Lim, Martin Kleppmann, Peter van Hardenberg, **November 2021**;
<https://www.inkandswitch.com/peritext/>. Published as Litt, Lim, Kleppmann & van Hardenberg,
*Peritext: A CRDT for Collaborative Rich Text Editing*, PACM HCI Vol. 6, CSCW2, Article 531,
November 2022, <https://doi.org/10.1145/3555644>.

The essay contains a section titled literally **"Markdown in a plain text CRDT"**, which tests the
exact architecture a git-backed suite would reach for first — store Markdown, sync it with an
off-the-shelf plain-text CRDT — and shows it breaks. Alice bolds "The fox"; Bob concurrently bolds
"fox jumped". Merging the plain-text insertions interleaves the two users' asterisks:

```
**The **fox** jumped.**
```

which renders as *The* fox *jumped* — both users bolded "fox", and in the merged result it is **not
bold**. Neither user's intent survived. The essay's generalisation:

> "This is just one example of a more general problem, due to the fact that the language was not
> designed to preserve intent under concurrent edits. As another example, if two people created a
> top-level heading by inserting `#` at the beginning of a line, that would become `##` denoting a
> second level heading."

It then rules out the two obvious escapes:

- **Hidden control characters** — the approach Yjs actually uses. Peritext states plainly that Yjs
  *"has the most full-featured rich-text CRDT available today ... However, it suffers from the anomaly
  shown in this section."* Overlapping `<bold>`/`</bold>` markers produce the same lost-intent result,
  and control characters *"do not tell us which formatting is older and which is newer."*
- **Format spans in a JSON CRDT** — the naive Automerge approach. Splitting a span to apply formatting
  merges badly: two users splitting the same span duplicate text.

**Consequence for this project — but read §G.0 before acting on it.** This result is real and I have
verified it, but it is **narrower than it first appears, and an earlier draft of this report
over-generalised it.** What Peritext proves is that *concurrent, overlapping **mark** operations* over
a plain-text CRDT do not preserve intent. It says nothing about concurrent text insertion or deletion,
which a plain-text CRDT merges correctly and which is the overwhelming majority of real co-editing.

Peritext's own framing is **asynchronous** collaboration — independently edited copies reconciled much
later — and in the architecture recommended here, async divergence is handled by git branches and merge
drivers (§C), not by CRDT merge at all. Inside a live session the concurrency window is one network
round-trip.

So the honest statement is: **Markdown is a poor rich-text merge *algebra*, and an excellent storage,
diff, and interchange format.** §G.0 weighs that narrow, visible, repairable anomaly against the
whole-file reserialization damage that the alternative causes, and comes down against the rich-text
projection. Do not read this section on its own as an argument for ProseMirror.

### A.2 What Yjs and Automerge actually persist

**VERIFIED** via authenticated `gh api` on 2026-08-28:

| Repo | Stars | License | Last push | Note |
|---|---|---|---|---|
| `yjs/yjs` | 22,716 | MIT (LICENSE file; GitHub reports NOASSERTION due to a dual-copyright header) | 2026-08-06 | Created 2014-07-29 |
| `yjs/y-websocket` | 710 | MIT | 2026-08-06 | Reference sync server |
| `yjs/y-leveldb` | 115 | — | 2026-03-07 | **ARCHIVED** |
| `yjs/y-indexeddb` | 280 | — | 2025-02-12 | Browser persistence; quiet ~18 months |
| `yjs/y-prosemirror` | 463 | MIT | 2026-08-20 | ProseMirror/Tiptap binding |
| `ueberdosis/hocuspocus` | 2,560 | **MIT** | 2026-08-27 | Yjs websocket backend |
| `automerge/automerge` | 6,541 | MIT | 2026-08-28 | Rust core + JS/WASM |
| `automerge/automerge-repo` | 706 | MIT | 2026-08-25 | Sync/storage framework |
| `inkandswitch/peritext` | 790 | MIT | 2022-09-16 | Research prototype, dormant |
| `inkandswitch/upwelling` | 30 | none | 2022-11-02 | Research prototype, dormant |

Two flags worth carrying into a build decision:

- **`y-leveldb` is archived** (VERIFIED: archived flag true, last push 2026-03-07). The canonical
  server-side Yjs persistence adapter is no longer maintained; Hocuspocus's own Database/SQLite/S3
  extensions are the live path.
- **Hocuspocus is MIT open source** (VERIFIED). It is built by the Tiptap team, who monetise a
  *separate* hosted product and paid Pro editor extensions, but the server itself carries no license
  fee and self-hosting is the documented path. Server extensions (VERIFIED at
  <https://tiptap.dev/docs/hocuspocus/introduction>): Database, Logger, Redis, SQLite, Throttle,
  Webhook, S3.

**What they store is not a document — it is an op-log.** `Y.encodeStateAsUpdate(doc)` yields a binary
update blob; Automerge's format is likewise a compressed binary change log
(<https://automerge.org/automerge-binary-format-spec/>, REPORTED — seen via search, not fully read).

**VERIFIED by reading the source:** `automerge-repo-storage-nodefs`
(`packages/automerge-repo-storage-nodefs/src/index.ts`) writes each document as **binary chunk files in
a nested directory**, and its own source comment warns of data spread *"across thousands of chunk files
for a single document"*. The closest thing to "an Automerge document on a filesystem" is a directory of
thousands of opaque binary blobs.

### A.3 Does anyone persist a CRDT *as* a git-committed file?

**Short answer: essentially no, and the projects that come closest deliberately do not.**

I searched for this specifically and found no established project, pattern, or advocacy for committing
Yjs update blobs or Automerge binaries into git. That absence is itself the finding, and it is well
explained: a CRDT binary committed to git is a file git cannot diff, cannot merge, and cannot show in a
PR. You would pay git's entire cost and receive none of its benefits, while *also* still needing the
CRDT's own merge machinery.

I tested this rather than asserting it. **MEASURED** (Node v24.15.0, yjs 13.6.32, git 2.47.3):

*Size is **not** the objection.* I committed 300 successive edits of a document as both `doc.md` and
`doc.ydoc`. After `git gc --aggressive`, all 300 versions packed to **66,387 bytes for the Markdown**
and **74,032 bytes for the Yjs binary** — only ~11% worse. Yjs updates are append-mostly and
garbage-collect tombstones, so they delta-compress in git better than folklore suggests. The common
"CRDT binaries bloat your repo" argument **did not reproduce**.

*Mergeability is the objection, and it is fatal.* I forked one base document into two branches — Alice
changes `brown`→`red`, Bob changes `lazy`→`tired`, disjoint edits — and merged:

```
$ git merge alice
Auto-merging doc.md
CONFLICT (content): Merge conflict in doc.md
warning: Cannot merge binary files: doc.ydoc (HEAD vs. alice)
CONFLICT (content): Merge conflict in doc.ydoc
$ git status --short doc.ydoc
UU doc.ydoc
```

Git cannot merge the CRDT. The only resolutions it offers are "take ours" or "take theirs" — each of
which **silently discards one collaborator's work in its entirety**. Applying both updates through Yjs
itself merged the two edits perfectly.

That is the whole argument in one experiment: **only the CRDT can merge CRDT state.** If the `.ydoc` is
the record, then every `git merge`, every pull request, every branch — the entire reason to choose git —
requires an application-level merge step git cannot perform or even display. You keep git's costs and
lose its function.

What the real systems do instead — **the CRDT is the wire protocol, the file is the record**:

**CollabMD** — `github.com/andes90/collabmd` (**VERIFIED**: MIT, 268 stars, 19 forks, created
2026-03-04, last commit **2026-08-28** — active today; site <https://collabmd.app>). This is the single
most directly relevant project found: the exact architecture this project needs, already shipping. Its
README states the model in one sentence:

> "Your filesystem is the source of truth. CollabMD reads files from disk, uses Yjs for realtime
> collaboration, and continuously writes plain text back to disk as you type. External changes from
> tools like Obsidian, direct file writes, or git-driven file updates are watched and reconciled back
> into live rooms and the explorer."

Its marketing site (**VERIFIED**) is headlined *"Your folder, now multiplayer"*, and the sample document
rendered in its own demo states the principle better than a paraphrase:

> "Keep the vault as plain files and let **the room layer stay ephemeral**. Yjs merges concurrent
> edits. No save button, no conflicts."

**Its editor stack is the load-bearing detail, and it is not what I first assumed** (**VERIFIED** from
`package.json`): `@codemirror/lang-markdown ^6.5.2`, `y-codemirror.next ^0.3.6`, `yjs ^13.6.32`,
`markdown-it ^15.0.0`. CodeMirror 6 with a plain-text Yjs binding over the **markdown source**, and
`markdown-it` — a parser with no serializer — for one-way preview only. **There is no ProseMirror,
no Tiptap and no turndown in it, so nothing is ever reserialized on save.** This is what makes its
git commits clean, and it is why §G.0 reverses this report's original editor recommendation.

*The room layer stays ephemeral* is the whole design. Three more things worth stealing:

- **Git review from the browser**: *"review an open file's changes, include them in the next commit,
  and commit with a message from the browser"* — commits are **explicit and user-driven**, not
  per-keystroke. §B.6 shows why that matters. The site also notes a scoping call worth copying:
  *"Publish goes straight to the configured branch. **No PR gate in v1. This is intentional.**"*
- **A lease model for formats that cannot merge.** For draw.io files: *"one connected client holds the
  edit lease for a `.drawio` file, while other viewers open it read-only and refresh after saves land.
  This avoids silent overwrite races without claiming true realtime canvas co-editing."* This is the
  honest answer for slides, diagrams and formula-bearing sheets.
- **Its stated limitation is the scaling wall**: *"Single-instance deployment only: collaboration room
  state is kept in-process and is not shared across replicas."* See §G.

Note: `rodgersgitau/collab-md` (0 stars, created 2026-03-31) carries an identical description and
appears to be a copy, not an independent project. **VERIFIED** via `gh api`.

**Zed** — `zed-industries/zed` (**VERIFIED**: 89,366 stars, last push 2026-08-28). Its blog *"How CRDTs
make multiplayer text editing part of Zed's DNA"* (<https://zed.dev/blog/crdts>, VERIFIED) explains the
CRDT: edits expressed against *logical* positions derived from immutable insertion history rather than
absolute offsets, so concurrent operations commute. Architecturally, one participant is the **host** who
owns the filesystem; guests edit the host's files remotely. **VERIFIED** from Zed's own docs:

> "Sharing a project gives collaborators access to your local file system within that project. Only
> collaborate with people you trust." — <https://zed.dev/docs/collaboration>
>
> "This will allow channel members to edit the code hosted on your machine as though they had it
> checked out locally. ... Collaborators can open, edit, and save files, perform searches, and interact
> with language servers." — <https://zed.dev/docs/channels>

The decisive detail: in a Zed session there is exactly **one filesystem and one git working copy — the
host's.** Guests have no checkout to diverge from. The CRDT is session state over a buffer; the file on
the host's disk stays ordinary text and git operates on that, **from one machine.** Same shape as
CollabMD, and the same shape §B.6 shows is mandatory.

**Contrast — Notion.** From the Peritext essay (VERIFIED; Notion funded that research): Notion supports
offline editing, but *"if two users concurrently edit the same paragraph (called 'block' in Notion),
then only one of those edits is preserved, and the other is discarded."* A shipped, enormously
successful product resolves block-level concurrency by **throwing one side away**.

**Contrast — Dropbox / Evernote.** From the local-first essay (VERIFIED): Dropbox produces a
"conflicted copy" the user merges by hand; Evernote moves the note to a "conflicting changes" notebook
with *"nothing to support the user in resolving the situation — not even a facility to compare the
different versions."* The mass-market baseline for conflict handling is very low — useful calibration
on how much merge fidelity the market actually demands.

### A.4 Ink & Switch: the research that has already been done here

**Local-first software: You own your data, in spite of the cloud** — Kleppmann, Wiggins, van Hardenberg,
McGranaghan, **April 2019**, <https://www.inkandswitch.com/essay/local-first/> (**VERIFIED**; note the
live URL is `/essay/local-first/` — `/local-first/` returns an empty page).

This is the sharpest available statement of what this project is signing up to fix. **VERIFIED** — the
essay's scoring table gives Git+GitHub ✓ on *Fast, Offline, Longevity, User control* and **fails it on
Multi-device, Collaboration, and Privacy**. Its verdict:

> "We think the Git model points the way toward a future for local-first software. However, as it
> currently stands, Git has two major weaknesses: [1] Git has no capability for real-time, fine-grained
> collaboration, such as the automatic, instantaneous merging that occurs in tools like Google Docs,
> Trello, and Figma. [2] Git is highly optimized for code and similar line-based text files; other file
> formats are treated as binary blobs that cannot meaningfully be edited or merged."

Those two sentences are precisely the product gap. The essay also noted in 2019 that *"Support for
mobile devices is currently weak, although Working Copy is a promising Git client for iOS"* — see §E.

**Upwelling: Combining real-time collaboration with version control for writers** — Karissa Rae
McKelvey, Scott Jenson, Eileen Wagner, Blaine Cook, Martin Kleppmann, **March 2023**,
<https://www.inkandswitch.com/upwelling/> (**VERIFIED**). The transferable findings:

- The **"fishbowl effect"**: realtime collaboration is not universally wanted. *"Writers don't want
  first drafts visible to the editor."* Several interviewees found keystroke-level observation
  stressful, and some worried about management monitoring them. **A git-backed suite's branch/draft
  model is therefore a feature, not a consolation prize** — it is the thing Google Docs cannot offer.
- Named findings include ***"Automatic merging is necessary but not sufficient"*** and ***"It's better
  to avoid conflicts in the first place"*** — even with a CRDT, the design goal is to *structure work so
  conflicts don't arise*, not to merge heroically.
- Also *"Keystrokes should be grouped meaningfully"* — directly relevant to commit granularity.

**Patchwork: Version control for everything** — Geoffrey Litt, Paul Sonnentag, Max Schöning, Adam
Wiggins, Peter van Hardenberg, Orion Henry. A lab notebook of **11 entries, 2024-02-13 to 2024-07-19**;
<https://www.inkandswitch.com/patchwork/notebook/2024-version-control/> (**VERIFIED** — all 11 read).
The project page lists the span as 2024–2026 and adds Orion Reed, grjte, chee and Alex Warth.

*Naming correction:* the brief referred to *Patchwork/"Trellis"*. These are unrelated. `inkandswitch/trellis`
(**VERIFIED**: MIT, 521 stars, last push **2020-05-18**) is an old *Trello clone sample app for Automerge
persistence*, not version-control research.

The entries that matter most:

- **03 · Dynamic history** (2024-02-22) — the direct answer to "should every save be a commit". Their
  synthesis: *auto-save every character typed*, *offer flexible views of that history depending on the
  task*, and *let users mark milestones*. Granular capture and legible history are **decoupled**:
  record everything, then *query* it into groupings (by author, by edit time). **This is the design that
  makes autosave tolerable** — the raw log is machine-level; the human-facing history is a projection.
- **08 · History and diffs with Automerge** (2024-03-26) — why a CRDT is a good version-control
  substrate: Automerge *"never deletes anything"*, so history is free; it computes **exact** diffs
  between any two points *"without heuristics"* because every character has an ID; clone/merge gives
  branching. A genuine advantage over git: **git diffs are heuristic reconstructions; CRDT diffs are
  ground truth.**
- **06 · Simple branching** (2024-03-05) — branches work for writers, but only with severe
  simplification: no branching from branches, no naming required at creation, merge deletes the branch
  with no cleanup step, and **you edit on main by default** so a recipient who doesn't understand
  branches can still just type. Plus: create a branch *retroactively* from edits already made.
- **05 · Edit groups** (2024-02-29) — design principle **"formality on demand"**: supply rationale
  *after* the fact rather than deciding up front whether you are "suggesting" or "editing" (an explicit
  criticism of Google Docs suggestion mode and of Upwelling's own mandatory draft layers).
- **09 · Version history as chat** (2024-03-28) — their most successful history UI: a timeline where
  **every change gets an AI-generated summary**. Their words: *"remarkably useful ... more successful
  than any of our other diff visualizations so far."* Directly applicable — **an LLM writing the commit
  messages is what makes an auto-committed history readable.**
- **10 · Beyond prose** (2024-04-03) — generalised to a tldraw diagram editor and a Handsontable
  spreadsheet. Finding: **branching and timeline port almost for free; diff views and comments are
  domain-specific and cost real work.** They hit this project's exact spreadsheet problem: *"diff that
  distinguish manually-edited cells versus recalculated formula result cells."*
- **11 · Universal comments** (2024-07-19) — a cross-format comment layer built on **"pointers"**: the
  app declares what can be pointed at (a text span, a cell range, a set of shapes) and the shared layer
  owns threads/replies/storage. They then reused the same pointer primitive to drive **diff
  highlighting**. If this suite wants comments across docs/sheets/slides, this is the design.

**Embark: Dynamic documents for making plans** — Paul Sonnentag, Alexander Obenauer, Geoffrey Litt,
**November 2023**, <https://www.inkandswitch.com/embark/> (**VERIFIED**). Less relevant to storage, but
relevant to the sheets question: it puts **spreadsheet-like formulas, structured-data mentions, and rich
views (maps, calendars) inside a text outline**, "unbundling apps into data, computations, and views".
Prior art for formulas-embedded-in-prose if the suite wants formulas without inventing a spreadsheet
format.

### A.5 Summary table — CRDT / collaboration options

| Tech | License | File-friendly? | Maturity | Notes |
|---|---|---|---|---|
| **Yjs** | MIT | ✗ as storage / ✓ as session | Very mature (2014, 22.7k★, active) | Fastest, largest ecosystem. Rich text via control characters — **has the Peritext anomaly on concurrent overlapping formatting**. Persist binary, project to Markdown. |
| **y-prosemirror / Tiptap** | MIT | n/a (binding) | Mature, active | The standard WYSIWYG binding. ProseMirror schema ⇄ Markdown is the lossy boundary, not Yjs. |
| **Hocuspocus** | **MIT** | n/a (server) | Mature, active (2.5k★) | Self-hostable Yjs backend, no license fee. Redis ext scales connections but **not CPU** — see §G. |
| **y-leveldb** | — | — | **ARCHIVED 2026-03-07** | Do not build on it. |
| **Automerge** | MIT | ✗ as storage (binary chunk dirs) | Mature-ish, very active | Full history free; **exact non-heuristic diffs**; clone/merge = branches. Best fit if version control *is* the product. Heavier than Yjs. |
| **automerge-repo** | MIT | ✗ (`nodefs` = thousands of binary chunks/doc) | Active | Storage: IndexedDB, Node FS. Network: websocket, BroadcastChannel, MessageChannel. |
| **Peritext** | MIT | ✓ conceptually | **Research prototype, dormant since 2022-09-16** | The correct rich-text merge semantics. Read the paper; don't depend on the code. |
| **Plain Markdown + text CRDT** (Y.Text) | n/a | **✓ — the buffer *is* the file** | Shipping (CollabMD; Obsidian/SilverBullet single-user) | **The recommended substrate — see §G.0.** Byte-stable for free. Inherits Peritext's anomaly only on *concurrent overlapping mark ops*: rare, visible, repairable. |
| **CRDT binary committed to git** | n/a | ✗✗ | No adopters found | **MEASURED**: git reports `Cannot merge binary files`; resolution discards one side entirely. Not a real option. |
| **Edit lease / single-writer** (CollabMD's `.drawio` model) | n/a | ✓ | Shipping | The honest answer for slides, diagrams, formula sheets. Not multiplayer, but never corrupts. |
| **Yjs `Y.Text` + CodeMirror 6** (`y-codemirror.next`, CollabMD) | MIT | **✓✓ buffer is the file** | Shipping; binding maintained (206★, 2026-08-18) | **The recommendation (§G.0).** Pin 0.3.x — `main` targets unstable yjs v14. |
| **Rich-text CRDT + markdown projection** (Tiptap/ProseMirror + turndown/remark) | MIT | **✗ — reserializes the whole file** | Shipping **and demonstrably losing data**: Pithy (`00-pithy-teardown.md`), Nextcloud Text (`03` §7, 6 yrs, ~25 open issues) | **Rejected — see §G.0.** Correct mark merges, but rewrites files on first touch and destroys git's diff. |
| **ProseMirror + a round-trippable format** (Keystatic → Markdoc) | MIT | ✓ *if you change the format* | Shipping (multiplayer "experimental") | The real third path: block WYSIWYG **and** tight round-trip, paid for by the files no longer being plain CommonMark. |

---

## B. Git as a sync/storage substrate for non-code

### B.1 Large-file and data layers

| Project | Stars | License | Latest release | Status (2026-08-28) |
|---|---|---|---|---|
| **git-annex** | n/a (self-hosted) | AGPL-3.0-only | 10.20260717 | Very active, ~monthly releases |
| **git-lfs** | 14,446 | NOASSERTION | v3.8.0 (2026-08-28) | Active |
| **DVC** (now `treeverse/dvc`) | 15,850 | Apache-2.0 | 3.67.1 (2026-03-31) | **Acquired by lakeFS 2025-11-18** |
| **xet-core** (`huggingface/xet-core`) | 564 | Apache-2.0 | — | Active. `xetdata/xet-core` dead since 2024-10-16 |
| **Dolt** | 24,286 | Apache-2.0 | v2.3.1 (2026-08-19) | Very active |

**git-annex — steal its metadata pattern.** VERIFIED from
<https://git-annex.branchable.com/internals/>: the `git-annex` branch is an orphan branch whose files
are *"all designed to be auto-merged by simply concatenating them together. So each line has a
timestamp, to allow the most recent information to be identified."* That is a **last-write-wins
register CRDT encoded as an append-only, union-mergeable log inside git**. For a Drive's mutable
per-file metadata — sharing ACLs, stars, trash state, rename history — this makes metadata merges
*structurally unconflictable* instead of relying on three-way text merge. This is the cheapest big win
in the whole report.

Also VERIFIED: the **git-annex assistant** (<https://git-annex.branchable.com/assistant/>) is a daemon
that watches a folder and auto-commits/syncs across machines, drives and cloud remotes. It is the
**oldest production example of exactly this design doc's architecture**, and note what it does: pairs
auto-commit with **out-of-band content storage** rather than putting blobs in git.

**git-lfs — the granularity trap.** VERIFIED from the spec
(<https://github.com/git-lfs/git-lfs/blob/main/docs/spec.md>): pointer files are <1024 bytes,
`oid sha256:...` plus `size`. LFS deduplicates at **whole-file granularity** — every save of a 50 MB
file stores another 50 MB object. For a documents product that autosaves, this is the wrong shape.

**Xet / content-defined chunking — the most directly applicable prior art in this report.**
VERIFIED: Hugging Face acquired XetHub in **August 2024** (<https://huggingface.co/blog/xethub-joins-hf>);
**`xethub.com` now returns HTTP 404** — the product is gone, the technology shipped into the Hub.
From <https://huggingface.co/docs/hub/en/xet/deduplication> (VERIFIED):

> "Xet-enabled repositories utilize content-defined chunking (CDC) to deduplicate on the level of
> bytes (**~64KB of data** ...). Each chunk is identified by a **rolling hash** that determines chunk
> boundaries based on the actual file contents, making it resilient to insertions or deletions
> anywhere in the file." Chunks are grouped into **64 MB blocks** in a content-addressed store.
>
> "**Git LFS is designed to notice only that a file has changed and store the entirety of that
> revision.** By deduplicating at the level of chunks, the Xet backend enables storing only the
> modified content in a file."

A documents app saving every few seconds is *exactly* the "small edit to a large file, repeatedly"
workload that kills LFS and that CDC solves. Note the sharp caveat: **git's own object model does none
of this** — git stores whole blobs and recovers space only through heuristic delta compression at gc
time. Xet is a *replacement* for git's large-object storage, not an enhancement to it. Academic origin
cited by HF: *"Git is for Data"*, Low et al., CIDR 2023
(<https://www.cidrdb.org/cidr2023/papers/p43-low.pdf>).

**Dolt — the proof that git *semantics* and git *storage* are separable.** VERIFIED
(<https://www.dolthub.com/docs/architecture/storage-engine/prolly-tree>): Dolt gives branch / diff /
merge / PR over structured data with **cell-level merges**, and achieves it by **discarding git's
object model entirely** in favour of **Prolly Trees** ("Probabilistic B-trees", from the Noms
lineage) — content-addressed, structurally shared, with diffs that *"scale with the size of the
differences, not the size of the tree."* If this suite needs real spreadsheet semantics, Dolt is the
argument not to force that into git blobs. (DoltHub funding figures circulating (~$21M) are
**REPORTED** via CBInsights only — do not print them as fact.)

### B.2 Software that treats git as an app database

**The most important negative result:** Gitea (57,657★, MIT) and Forgejo (5,393★ on Codeberg,
GPL-3.0+ since v9.0) — projects whose *entire product* is git — store issues, PRs and wiki in a
**normal SQL database**, not in git. Even git-native products keep mutable app state in SQL. That is
load-bearing evidence against "put everything in git".

Forgejo timeline (VERIFIED): Gogs (2014) → Gitea fork (Nov 2016, MIT) → Gitea Ltd (Oct 2022) →
Forgejo soft fork (Nov/Dec 2022) → **hard fork 2024-02-15** (<https://forgejo.org/2024-02-forking-forward/>)
→ **relicensed GPLv3+ at v9.0, 2024-08-22** (<https://forgejo.org/2024-08-gpl/>).

**Radicle — the best worked example of "git as an app database", and the one to learn from.**
VERIFIED from <https://radicle.dev/guides/protocol>. Two mechanisms matter here:

1. **Per-writer namespaces over a shared object database.** *"Instead of each of the repository's peers
   storing data in a separate Git repository with a separate object database, peer data is stored
   within the same Git repository using Git namespaces"* — each peer's Node ID is a namespace under
   `refs/namespaces/<nid>/`, so **each client writes only into its own namespace and never conflicts**,
   while objects are shared so *"only one copy of each object is stored across all repository
   namespaces."* For a Drive with N devices per user this maps directly, and it is a real answer to
   the push-rejection problem measured in §B.6.1.
2. **Collaborative Objects (COBs) as a commit-DAG CRDT.** Issues/patches/identity
   (`xyz.radicle.issue`, `xyz.radicle.patch`, `xyz.radicle.id`) are *"encoded as a set of commits in a
   directed acyclic graph"*. In their words: *"Data integrity is guaranteed by Git. Synchronization is
   handled by Git. ... It may be useful to think of Radicle's usage of Git commit histories as a form
   of conflict-free replicated data type (CRDT). When the histories of two peers are synchronized, the
   commit graphs are simply unioned."*

   Honest caveat: this works because every COB is **append-only and small**. It says nothing about a
   200 MB file rewritten every 5 seconds.

**Fossil — the strongest counter-model.** VERIFIED
(<https://fossil-scm.org/home/doc/trunk/www/tech_overview.wiki>). Fossil ships version control *plus*
wiki, tickets, forum, chat and a web UI in one binary, and it implements all of it by putting
content-addressed artifacts **in SQLite tables**, not by reimplementing git's on-disk format. Its
compression numbers are the honest counterweight to bloat fear: for the SQLite project, **7.1 GB of
artifacts compress to under 97 MB — about 74:1** — with a median compressed blob of **156 bytes**.
Fossil also explicitly separates *"local state ... not versioned and ... not synchronized"* from
versioned global state — the same lesson as Gitea. (Fossil's license is **VERIFIED BSD-2-Clause** —
`COPYRIGHT-BSD2.txt`, "Copyright 2007 D. Richard Hipp".)

**Tangled — real, funded, and it validates the split.** VERIFIED: **`tangled.sh` now redirects to
`tangled.org`**; the core repo is self-hosted there, not on GitHub. Per SiliconANGLE, **2026-03-02**
(<https://siliconangle.com/2026/03/02/tangled-announces-4-5m-round-build-github-alternative-built-blueskys-protocol/>):
**Tangled Labs Oy** (Finland, founded 2025) raised **$4.5M** led by **ByFounders**, with Bain Capital
Crypto, Antler, former GitHub CEO Thomas Dohmke and Tailscale CEO Avery Pennarun participating;
**>7,000 users and >5,000 repositories**. Users self-host repos as **"knots"**. REPORTED (from
third-party blogs, not a Tangled primary source): knots are lean headless servers holding the git
repos, **"spindles"** are CI runners, and a shared AppView indexes the network; identity and social
records live in atproto lexicons on the user's PDS while blobs/history live in the knot's git repo.

**Tangled is the closest live analogue to the architecture recommended here: git for content, a
separate protocol for identity and app metadata.** They did not try to cram social data into git refs.

**Pijul** — VERIFIED: latest **1.0.0-beta.22, 2026-08-23**, GPL-2.0-or-later, self-hosted at
nest.pijul.com. Active, but **still beta after ~10 years**. Cite it as the argument that git's merge
is a heuristic rather than an algebra; **do not build on it.**

**Sapling** — VERIFIED: 6,994★, GPL-2.0, commits landing daily from Meta engineers, **not archived**.
But public binary releases are sparse: **2025 had exactly one release**. The honest framing: *the code
is alive; the public product is neglected.*

### B.3 Jujutsu (jj): is it actually a better fit for "every save is a commit"?

VERIFIED facts: canonical repo is **`jj-vcs/jj`** (`martinvonz/jj` redirects), created 2020-12-18,
**31,243 stars**, **Apache-2.0**, latest **v0.44.0 (2026-08-06)**, pushed 2026-08-28. Martin von
Zweigbergk's README states it is *"my full-time project at Google"* but explicitly *"not a supported
Google product"*, and describes jj as *"an experimental version control system."*

**Where jj is genuinely better — and this is substantive, not marketing:**

1. **Auto-snapshot is the native mode.** VERIFIED (`docs/working-copy.md`): *"Jujutsu will
   automatically create commits from the working-copy contents when they have changed."* No staging
   area; added files are implicitly tracked. `jj util snapshot` is a **supported command for
   periodic snapshots** (VERIFIED, FAQ). You are not fighting the tool with a watcher shelling out to
   `git add && git commit`.
2. **`jj evolog` structurally solves the "useless history" problem — the single best idea found in
   this entire report.** VERIFIED (FAQ): every command updates the working-copy commit, *"unless you
   move to another revision, **the change ID will not change**"*, and *"You can see the actual history
   of working copy changes using `jj evolog`."* Autosaves **amend the current change** (same change
   ID, new commit ID) rather than appending siblings to the main graph. So `jj log` stays one entry
   per meaningful unit of work while the second-by-second trail remains fully addressable on a
   separate axis. **Every git-based auto-commit tool dumps thousands of timestamp commits straight
   into `git log`; jj is the only system here that gets fine-grained autosave *and* readable history
   with no squash step and no history deletion.**
3. **The operation log is a better undo than anything in git.** VERIFIED (`docs/operation-log.md`):
   `jj op log` records every repo-modifying operation with a full view snapshot; `jj undo`,
   `jj op revert`, `jj op restore` revert the *repository*, not just the worktree.
4. **Lock-free concurrency — directly relevant to multi-device sync.** VERIFIED, same doc: *"it allows
   lock-free concurrency -- you can run concurrent `jj` commands without corrupting the repo, even if
   you run the commands on different machines that access the repo via a distributed file system."*
   Concurrent operations produce a **divergent change** surfaced in the UI, not a corrupt index.
   Contrast §B.6.1, where the git equivalent simply rejects the second writer.
5. **First-class conflicts remove the modal wedged state.** VERIFIED
   (`docs/technical/conflicts.md`): a conflict is recorded as *"an ordered list of tree objects linked
   from the commit"* — always an odd number — so a three-way merge is the expression `A+(C-B)`.
   Contents are computed on demand. The elegant part is **conflict simplification**: rebasing a
   conflicted commit from C onto D yields `D+((C+(B-A))-C)`, which `Merge::simplify()` reduces to
   `D+(B-A)` — *"This is what lets the user keep old commits rebased to head without resolving
   conflicts and still not get messy recursive conflicts."*

**What jj does NOT solve — and these are disqualifying for a Drive:**

1. **jj stores whole files.** It is git's object model underneath (via gitoxide). No content-defined
   chunking, no rolling hash, no sub-file dedup. Saving a 40 MB document every 30 seconds writes a new
   40 MB blob every 30 seconds. **Because jj commits more often, its write model makes the storage
   problem worse than git's, not better.** Xet (§B.1) and Dolt solve this; jj does not attempt it.
2. **No Git LFS support after 4.5 years.** VERIFIED: issue
   [#80](https://github.com/jj-vcs/jj/issues/80), opened **2022-02-24, still open**.
3. **The default file-size limit is 1 MiB.** VERIFIED (`docs/config.md`): *"as an anti-footgun
   measure, `jj` will refuse to add new files to the snapshot that are larger than a certain size; the
   default is 1MiB"* (`snapshot.max-new-file-size`). A VCS whose default posture is "refuse files over
   1 MiB" is telling you its intended workload, and a Drive's median attachment exceeds it.
4. **Conflicts are still textual and line-based.** `jj resolve` shells out to an external merge tool;
   otherwise conflict markers are written into the file and re-parsed on the next scan. jj changes
   **when** you must resolve, not **how well** it can be resolved — nothing about first-class
   conflicts makes merging prose, a spreadsheet, or a `.docx` smarter. Everything in §C still applies.
5. **The conflict model does not survive contact with plain git — the killer for this project.**
   VERIFIED (`docs/git-compatibility.md`): *"**Commits with conflicts cannot be represented in Git.**
   They appear in the Git commit as root directories called `.jjconflict-base-*/` and
   `.jjconflict-side-*/` ... the authoritative information is in a non-standard `jj:trees` commit
   header."* Change IDs are likewise a non-standard header and are *"not preserved through a rebase
   operation"* by standard git tooling. **If the product promise is "your Drive is a real git repo you
   can clone", then jj's best features are exactly the ones that don't travel** — a plain-git consumer
   sees garbage `.jjconflict-*/` directories.
6. **jj is a CLI, not a server.** No multi-tenancy, auth, ACLs, or web API. The pluggable backend
   traits are the interesting part, not the product.

**Verdict: steal jj's *model*, do not adopt jj.** The **change-ID / commit-ID split with an evolution
log** is the correct answer to "every save is a commit produces unreadable history", and it appears
nowhere else in this survey. The **operation log** is the correct answer to undo and to lock-free
multi-writer concurrency. Both are ideas implementable over any storage layer. But jj's storage layer
*is* git's, with more frequent writes and a 1 MiB default ceiling — the wrong substrate for documents
that are saved continuously.

### B.4 The "auto-commit every save" pattern in the wild

**Obsidian Git** — VERIFIED: the canonical repo is **`Vinzent03/obsidian-git`**
(`denolehov/obsidian-git` redirects to it); 11,872★, MIT, latest 2.39.0 (2026-08-12). Defaults read
directly from `src/constants.ts` (VERIFIED):

```ts
commitMessage: "vault backup: {{date}}",
commitDateFormat: "YYYY-MM-DD HH:mm:ss",
autoSaveInterval: 0,          // auto-commit is OFF by default (minutes)
autoBackupAfterFileChange: false,
squashCommitsBeforePush: false,
pullBeforePush: true,
syncMethod: "merge",
```

Worth stating precisely because it is commonly gotten wrong: **auto-commit is opt-in, not the
default.** That `squashCommitsBeforePush` exists at all is evidence the maintainer considers the
useless-history problem real.

**The documented failure modes** (VERIFIED issue list):

| Problem | Evidence |
|---|---|
| **Data loss** on multi-device conflict | [#558](https://github.com/Vinzent03/obsidian-git/issues/558) *"Data loss when mobile has conflicts"* — **open since 2023-07-13** |
| Conflict UX broken on mobile | [#920](https://github.com/Vinzent03/obsidian-git/issues/920) (2025-06-08, open), [#340](https://github.com/Vinzent03/obsidian-git/issues/340) (2022-10-16, open), [#563](https://github.com/Vinzent03/obsidian-git/issues/563) (open) |
| `index.lock` contention from auto-commit | [#1077](https://github.com/Vinzent03/obsidian-git/issues/1077) *"`index.lock` left behind ... when auto commit-sync is enabled"*, plus [#683](https://github.com/Vinzent03/obsidian-git/issues/683), [#342](https://github.com/Vinzent03/obsidian-git/issues/342), [#186](https://github.com/Vinzent03/obsidian-git/issues/186) — **spans 2022→2026, structural not a regression** |
| Repo bloat | [#763](https://github.com/Vinzent03/obsidian-git/issues/763) — user reports shallow re-clone + aggressive gc *"can reduce a checkout size ... by hundreds of MB or more, often more than halving the size on disk"* |
| 100 MB push limit hit by ordinary users | [#248](https://github.com/Vinzent03/obsidian-git/issues/248) |
| Mobile performance | [#572](https://github.com/Vinzent03/obsidian-git/issues/572) — mobile path uses **isomorphic-git** (pure JS), a known bottleneck |

**The gc arithmetic — do this in the design doc.** VERIFIED from <https://git-scm.com/docs/git-gc>:
`gc.auto` default is **6700** loose objects; `gc.autoPackLimit` default **50** packs;
`gc.autoDetach` default **true**. At a 1-minute autosave interval a single user generates ~1,440
commits/day, each producing at minimum a commit object + tree objects + a blob — call it 3–5 loose
objects. **You cross the 6,700-object threshold in roughly one to two days of single-user editing.**
Then `gc --auto` fires *in the background*, concurrently with the next autosave. That is precisely the
race that produces the `index.lock` bug family above — documented defaults colliding with documented
bug reports. Note jj hits the identical class of bug (`working_copy.lock` corruption under Vite file
watchers, VERIFIED in jj's FAQ). **Any snapshot-on-a-timer design must own a real locking story.**

**gitwatch** (`gitwatch/gitwatch`, VERIFIED: 1,736★, GPL-3.0, v0.6 2026-06-11) is the only maintained
shell-level tool: `inotifywait` → 2-second debounce → `git add --all` → commit `"Auto-commit: %d"` →
optional push. Its own README warns *"If you have any large files in your repository that are changing
frequently, you might wish to ignore them"* — which is not an option when the churning large file
**is the user's document**. Note `SKIP_IF_MERGING` defaults to **false**: by default it commits during
a merge, a merge-storm accelerant.

**"git-autocommit" is not a project — do not cite it.** VERIFIED: there is no canonical tool by that
name, only six small abandoned namesakes (largest 77★, last push 2014-02-12). That six people
independently wrote and abandoned the same script is itself the finding.

**Also VERIFIED:** `ryuslash/git-auto-commit-mode` (Emacs, 193★) is dormant since 2022-12-07.
**etckeeper has no canonical GitHub repo** — describe it by behaviour, don't link a fork as canonical.
**NOT CONFIRMED:** whether Logseq, Foam, Dendron, SiYuan or Anytype auto-commit to git. Anytype in
particular is generally described as a custom CRDT protocol, **not** git — do not assert otherwise.

**Why every mitigation is unsatisfying:** squash-on-push destroys the fine-grained recovery points
that were the reason for autosaving; shallow re-clone deletes the history (issue #763's own "Cons"
say *"no history"*); aggressive gc races the next autosave; `.gitignore` cannot exclude the document
itself; `rebase --autosquash`/`filter-repo` are manual and unusable as a mobile background process.
**Only jj's change-ID/evolog split gets both granular recovery and clean history by construction.**

### B.5 VCS options — fit for this use case

| VCS | License / status | Every-save-is-a-commit | Conflict model | Non-code / large files | Ecosystem & interop | Fit |
|---|---|---|---|---|---|---|
| **git** | GPL-2.0, universal | Poor natively — needs a watcher; races `index.lock`; crosses `gc.auto` (6700) in ~1–2 days | Line-based, blocking, modal. **MEASURED: 100% failure for the 2nd concurrent writer** | Whole blobs; LFS is whole-file granularity | Total. Every host, every client, every user already has it | **Use it — as the archive/interop layer.** Its ubiquity *is* the product promise |
| **jj** | Apache-2.0, 31k★, self-described **experimental** | **Best in class** — native auto-snapshot + `jj util snapshot`; **`evolog` keeps main history clean by construction** | **First-class**: conflicts stored in commits, `A+(C-B)`, simplify on rebase, non-blocking. Still line-based | Same as git, **worse**: commits more often, **1 MiB default file limit**, **no LFS after 4.5 yrs** | Git-compatible for commits/files — but **conflicts and change IDs do NOT survive to plain git** (`.jjconflict-*/`, `jj:trees` header) | **Steal the model, not the tool.** change-ID/evolog + op-log are the right ideas; storage layer is wrong |
| **Dolt** | Apache-2.0, 24k★, very active | N/A (SQL writes) | **Cell-level merge** — genuinely solves tabular conflicts | Prolly trees, structurally shared, diffs scale with change size | SQL/MySQL wire, **not git** | **Strong candidate for the Sheets layer only.** Not a Drive |
| **Fossil** | **BSD-2-Clause** (VERIFIED), steady | N/A | Line-based | SQLite BLOBs + delta+zlib, **~74:1 measured on SQLite's own repo** | Self-contained, own ecosystem | **Not adoptable, but the best counter-model**: proves app state belongs in SQLite, not in the VCS |
| **Pijul** | GPL-2.0+, **1.0.0-beta.22 after ~10 yrs** | Unproven | Patch-theory: commutative/associative merges (theoretically superior) | Unproven at scale | Tiny | **Do not build on it.** Cite as proof git's merge is a heuristic, not an algebra |
| **Sapling** | GPL-2.0, 7k★ | N/A | Line-based | EdenFS virtual filesystem for huge monorepos | Code very active; **only 1 public release in 2025** | **No.** Meta-internal tool exported publicly |
| **Radicle** | P2P, Heartwood | N/A | **Per-writer namespaces = no conflicts by construction**; COBs = commit-DAG CRDT | Append-only small objects only | Own P2P network | **Steal the namespace pattern** for multi-device writes |

**The three ideas to take from this table, none of which requires adopting a new VCS:**

1. **Radicle's per-writer namespaces** (`refs/namespaces/<device-id>/`) over a shared object database —
   each device writes only into its own namespace, so concurrent writes *cannot* conflict, and objects
   are deduplicated. This is a direct structural answer to the 100%-push-rejection result in §B.6.1.
2. **git-annex's timestamped, union-mergeable append-only logs** for all mutable metadata (ACLs,
   trash, stars, rename history) — makes metadata unconflictable by construction.
3. **jj's change-ID vs commit-ID split with an evolution log** — granular autosave on one axis, clean
   readable history on the other, with no squash step and no history deletion.

---

### B.6 "Every save is a commit" — measured on this machine

This subsection reports **local measurements**, because the failure mode here is the biggest single
risk in the whole design and deserves evidence rather than argument.

All **MEASURED** on git 2.47.3, using a bare `origin.git` and two clones acting as two clients.

#### B.6.1 Concurrent auto-commit to one branch: the second writer is simply locked out

Two clients, each committing on every "save" and pushing to `main`, 12 rounds each:

```
PUSH REJECTED: B round 1
PUSH REJECTED: B round 2
... (rounds 3–12 identical)
```

**12 of 12 of client B's pushes were rejected. Zero of B's commits reached origin.** The final history
on `origin/main` contains only client A's 12 commits. Git's push is
compare-and-swap on a ref: whoever loses the race is rejected, every time, and the loser's work stays
stranded on their laptop. There is no partial success and no queueing.

#### B.6.2 The standard remedy (`pull --rebase` retry loop) fails outright on prose

The obvious fix is to have the rejected client pull-rebase and retry. I implemented that loop, with
both clients editing **the same paragraph** — the realistic co-authoring case:

```
push rejected (B r1) -> pull --rebase
  CONFLICT (content): Merge conflict in doc.md
  *** REBASE CONFLICT — human required ***
... identical for rounds 2 through 8
```

**8 of 8 rebases hit a merge conflict requiring human intervention. Client B's work never landed —
0% success across the whole run.** Origin ended with only A's commits.

This is §C.1 compounding with §B.6.1: because a paragraph is one line, *every* concurrent edit
conflicts; because every push race forces a rebase, *every* conflict lands in the automated retry
path where there is no human to resolve it.

#### B.6.3 The conclusion this forces

**Independently corroborated at the index layer.** A parallel scaling pass measured 8 concurrent
`git add` against one repo: **1 succeeded, 7 failed** with
`fatal: Unable to create '.git/index.lock': File exists.` Eight concurrent commits produced **3
commits from 8 attempts**. So the second writer is locked out at *both* ends — the index locally and
the ref remotely. Git's index is one file with one lock; there is no multi-writer story at any scale.

**Auto-commit-every-save and real multiplayer are directly incompatible at the git layer.** Not slow,
not messy — non-functional for the second writer. Any design that has two user devices independently
committing and pushing edits to the same document will lose data or deadlock, and no choice of diff
algorithm, commit interval, or retry policy fixes it, because the conflict is created by the storage
model itself.

This is precisely why every working system in §A.3 does the same thing: **a single writer process owns
the file.** In CollabMD the server owns the vault and writes debounced plain text; in Zed the host
owns the filesystem and guests never touch it. Concurrency is resolved in the CRDT *before* anything
reaches git, and git sees a linear sequence of commits from one writer. Git is the **archive and the
async/branching layer**, never the realtime sync channel.

#### B.6.4 The recommended architecture, validated

I then implemented the architecture this report recommends and ran the identical workload:
one server-side `Y.Doc` as session state, two clients editing **the same paragraph concurrently every
round**, the server merging both via CRDT and a **single writer** projecting to Markdown and committing.

**MEASURED** — 8 rounds, both clients editing concurrently in every round:

```
commits landed: 8   failures: 0
final doc.md: Intro paragraph. A0. B0. B1. A1. B2. A2. A3. B3. A4. B4. A5. B5. B6. A6. B7. A7.
```

**Every edit from both clients survived; zero conflicts; a clean linear history of 8 commits.** Same
workload, same concurrency, same git — the only change is *where the merge happens*. That is the
entire architectural argument, reduced to an experiment.

---

## C. Merge conflicts for prose and tables

This section is **MEASURED** — I ran every case locally on git 2.47.3.

### C.1 What actually happens when two people edit the same Markdown paragraph

A Markdown paragraph is conventionally **one long line**. Git merges by line. So two edits to
*different words of the same paragraph* are a hard conflict.

**MEASURED.** Base: `The quick brown fox jumps over the lazy dog and then returns home to rest.`
Alice changes `brown` → `*red*`; Bob changes `lazy` → `sleepy`. Disjoint words, no overlap.

```
$ git merge alice
Auto-merging doc.md
CONFLICT (content): Merge conflict in doc.md
exit=1
```
```
<<<<<<< HEAD
The quick brown fox jumps over the sleepy dog and then returns home to rest.
=======
The quick *red* fox jumps over the lazy dog and then returns home to rest.
>>>>>>> alice
```

Two people cannot touch one paragraph without a conflict. For a documents product this is fatal on
its own.

### C.2 "Just use semantic linefeeds" — MEASURED, and it does not save you

The standard advice is one sentence per line. It helps, but far less than people assume, because
**git requires at least one *unchanged* line between the two sides' edits.** I measured the exact
boundary:

**MEASURED** — 5-line file, Alice edits line 1, Bob edits line *N*:

| Bob edits | Unchanged lines between | Result |
|---|---|---|
| L2 | 0 | **CONFLICT** |
| L3 | 1 | clean |
| L4 | 2 | clean |

So with one-sentence-per-line, two people editing **adjacent sentences still conflict**. Only edits
two or more sentences apart merge cleanly. In real co-authoring — where two people work over the same
paragraph — adjacency is the common case, not the rare one.

### C.3 Diff algorithms do not help. At all.

A widespread misconception is that `patience`/`histogram` diff or `--word-diff` improve merging. They
do not: they change how a diff is *computed or displayed*; the merge granularity is still the line.

**MEASURED** — the C.1 case, retried under every strategy option:

```
git merge <default>              -> exit=1 (conflict)
git merge -Xpatience             -> exit=1
git merge -Xhistogram            -> exit=1
git merge -Xignore-all-space     -> exit=1
git merge -Xdiff-algorithm=histogram -> exit=1
```

`git diff --word-diff` / `--word-diff-regex` are **display-only**; there is no `--word-merge`.
Fixing prose merge requires a **custom merge driver** (`.gitattributes` `merge=<name>` plus
`merge.<name>.driver` in git config), not a diff option.

### C.4 CSV is worse — and then it is solved

**MEASURED** — plain git, `s.csv`:

- Alice edits `qty`, Bob edits `price`, **same row** → **CONFLICT** (the row is the merge unit; two
  different cells cannot both survive).
- Alice edits a cell, Bob **inserts a column** → **whole-file conflict** — every line changed, so git
  conflicts on the entire file including the header.

This is the "CSV cannot be collaborative" result. But it is a *tooling* gap, not a fundamental one:

**`daff` solves it.** `paulfitz/daff` (**VERIFIED**: MIT, 923 stars, created 2013-01-11, last push
2026-05-27). It aligns tables and does genuine **cell-level three-way merge**, and ships a git driver
installer (`daff git csv`).

**MEASURED** — I installed daff 1.4.2 in a throwaway venv and ran the real git merge-driver path
(`merge.daff-csv.driver = daff merge --output %A %O %A %B`):

| Case | Plain git | daff driver |
|---|---|---|
| Different cells, same row (qty vs price) | CONFLICT | **clean** → `widget,25,7.50` (both edits kept) |
| Column insert vs cell edit | CONFLICT (whole file) | **clean** → `widget,25,5.00,W1` |
| Row inserted on both sides | (would conflict) | **clean** — both rows kept |
| Rows reordered + cell edit | (would conflict) | **clean** — matched by key, not position |
| **Both edit the same cell** | CONFLICT | **CONFLICT** (correct) — `((( 10 ))) 25 /// 99`, exit 1 |

That is exactly the behaviour you want: merge everything genuinely independent, refuse only true
collisions. Verified end-to-end through `git merge`, which reported
`Auto-merging s.csv / Merge made by the 'ort' strategy`.

*(Caveat, MEASURED: `daff merge --inplace` did not produce a merged result in my testing — it left the
local file unchanged and returned exit 1. The `--output` form used by the official git driver works
correctly. Use the driver, not `--inplace`.)*

*(Housekeeping note: `daff git csv` writes to **global** git config (`git config --global`). I ran it
in a scratch directory and have since removed the `diff.daff-csv` / `merge.daff-csv` sections from the
global config; `git config --global --get-regexp daff` now returns nothing.)*

### C.5 Structured merge for prose: mergiraf, difftastic, weave

**mergiraf — VERIFIED, real, but does NOT cover Markdown or CSV.** The brief asked me to verify this.
It exists and is healthy, but it is hosted on **Codeberg, not GitHub**: `mergiraf/mergiraf`
(**VERIFIED** via Codeberg API: 423 stars, created 2024-10-31, updated 2026-08-17;
<https://mergiraf.org>). It is a tree-sitter-based syntax-aware git merge driver whose stated
philosophy is good — *"Don't sweep conflicts under the rug ... err on the side of caution and retain
conflict markers"*, and it falls back to line-based merge when that already works.

I read its full supported-language list (<https://mergiraf.org/languages.html>, VERIFIED): 29
programming languages plus declarative formats (JSON, YAML, TOML, XML, HTML, INI, HCL, etc.).
**Markdown is not on the list. CSV is not on the list.** Mergiraf does not help this project today.

**difftastic — VERIFIED, but it is a *diff* tool, not a merge tool.** `Wilfred/difftastic`
(**VERIFIED**: MIT, 25,830 stars, active, push 2026-08-28), manual describes v0.71.0, "over 30
programming languages". It produces beautiful structural diffs and would improve *review* UI, but it
**cannot resolve a merge** — it is diff-only. And I read its full language table
(<https://difftastic.wilfred.me.uk/languages_supported.html>, VERIFIED): like mergiraf, **it lists
neither Markdown nor CSV.** Do not plan around it for conflict resolution.

**weave — the one tool that actually merged prose in my tests.** `Ataraxy-Labs/weave` (**VERIFIED**:
Apache-2.0, 1,261 stars, created **2026-02-06**, last push 2026-08-27; latest release **v0.5.2**,
published 2026-08-22). Entity-level tree-sitter merge driver; README claims Markdown and CSV among
supported languages, and it explicitly targets *"false conflicts git invents when independent agents
edit the same file"* — i.e. it was built for the AI-agent era, which is this project's context too.
Notably its `--help` shows **first-class jj support** alongside git:

```
git invokes this as:  weave-driver %O %A %B %L %P
jj  invokes this as:  weave-driver $base $left $right -o $out -l $len -p $path
```

**MEASURED** — I downloaded the official `v0.5.2` linux binary and ran the three cases plain git failed:

| Case | Plain git | weave v0.5.2 |
|---|---|---|
| Same paragraph, `brown`→`*red*` vs `lazy`→`sleepy` | CONFLICT | **clean, both kept**: `The quick *red* fox jumps over the sleepy dog...` (reported "1 entities auto-resolved (medium confidence)") |
| Different `##` sections of one doc | CONFLICT | **clean, both kept** ("2 entities auto-resolved (very_high confidence)") |
| Adjacent lines L1 & L2 | CONFLICT | **clean, both kept** ("medium confidence") |

Then the important test — **does it silently merge things it shouldn't?** I gave it three
semantically dangerous cases. **MEASURED — it correctly refused all three:**

| Dangerous case | Result |
|---|---|
| Contradictory facts in one sentence (`5V`→`12V` vs `100mA`→`250mA`) | **CONFLICT**, exit 1, `refused_by: merge_ladder_exhausted` |
| One side deletes a sentence, other edits it | **CONFLICT**, exit 1, `refused_by: statement_fold`, markers note "deleted in ours" |
| **Negation flip** (`is safe` → `is NOT safe`) vs unrelated rewording of the same sentence | **CONFLICT**, exit 1 |

The negation case is the one that matters: a naive word-level merger would have produced
*"The migration is NOT safe to run on the production cluster"* — or, worse, silently dropped the NOT.
Weave refused, with an explanation and a `weave explain` / `weave check` workflow.

I also ran a realistic structured document — YAML front-matter, headings, a Markdown table, and a
bullet list — with one side changing the prose *and* a table cell, and the other changing front-matter
*and* adding a list item. **MEASURED:** `weave: 3 entities auto-resolved (high confidence)`, exit 0,
and the merged file correctly contained **all four** changes (`tags: [finance, q3, draft]`, the revised
sentence, `| EU | 150 |`, and `- item three`) with the document structure intact. Plain git would have
conflicted on the front-matter and table blocks.

**Verdict on weave:** it is the only thing I found that does a real three-way merge on prose, its
conflict markers are unusually informative, and it was conservative in every dangerous case I could
construct. **But** it is ~6 months old, at v0.5.x, from a small unknown vendor, and — the real
caveat — the cases it *did* merge were labelled *"medium confidence"* auto-resolutions. Those are
silent merges of prose that no human reviews. That is a meaningful residual risk (see §F).

### C.6 What this means

- **Nothing in stock git does a good three-way merge on prose.** Confirmed by measurement, not
  inference.
- **CSV/tables are solved today** by `daff` — a 13-year-old, MIT, cell-level three-way merge driver
  that behaved correctly on every case I threw at it. This is the strongest, lowest-risk finding in
  the whole report and it directly addresses the "sheets is the hard part" gap in `RESEARCH.md`.
- **Prose is solvable but only with young tooling** (`weave`) or by not needing merge at all — which
  is what the CRDT-session architecture in A.3 buys you.
- The deepest lesson is Upwelling's: **"It's better to avoid conflicts in the first place."** The
  architecture should make concurrent divergent edits to one paragraph *rare* (live CRDT session for
  the common case; branches for deliberate divergence), rather than making them *mergeable*.

---

## D. Scaling and practical limits

All figures below are **MEASURED** on this machine (git 2.47.3, Linux 6.12, SSD, warm page cache)
unless labelled otherwise. Warm-cache desktop numbers are the *optimistic* case — treat them as an
upper bound on performance, not a typical one.

### D.1 Many small files: not the problem people expect

I generated a synthetic Drive of Markdown documents and measured real operations.

| Corpus | `git add -A` (cold) | `git commit` | `git status` (warm) | `git status` after 1 edit | `.git` | index |
|---|---|---|---|---|---|---|
| **20,000 files** (79 MB) | 1.96 s | 0.09 s | 0.02 s | 0.02 s | 83 MB | 1.7 MB |
| **100,000 files** (393 MB) | 6.37 s | 0.32 s | 0.03–0.09 s | 0.11 s | 354 MB | **8.5 MB** |

A local `git clone` of the 100k-file repo took **8.04 s**.

**Conclusion: at Drive-plausible document counts, git is fine.** 100,000 markdown files is not a
performance problem on a modern machine — `git status` stays under 100 ms and incremental `add` is
~0.1 s. Enabling `feature.manyFiles` (which sets `index.version=4` and `core.untrackedCache`) changed
warm `status` from 0.02 s to 0.01 s here — i.e. **immeasurable at this scale**; those knobs matter at
Windows-monorepo scale, not at ours.

**The number that actually matters is the index: 8.5 MB at 100k files.** Git reads and rewrites the
index on essentially every operation. On a desktop that is free. On a phone, over a JS git
implementation, it is not — see §D.4.

### D.2 The real bloat driver: binary attachments (MEASURED, and it is stark)

Same number of commits, two different file types:

| Scenario | Current file size | `.git` after 21 revisions (post `gc --aggressive`) |
|---|---|---|
| **2 MB image, re-saved 21×** | 2.0 MB | **41 MB — 20.6× a single copy** |
| **1.1 MB text file, 21 append edits** | 1.1 MB | **180 KB — *smaller than one copy*** |

That is roughly a **230× difference in storage behaviour** for the same revision count. Git's delta
compression works beautifully on text and does essentially nothing for already-compressed binary
formats (PNG, JPEG, PDF, `.docx`, `.xlsx`), so **every revision of an image is stored in full, forever.**

Twenty edits to one embedded photo cost more than the entire 20,000-file text corpus in §D.1. **It is
not the number of files and it is not the documents — it is the attachments.**

A parallel pass measured the same effect on **real JPEGs** and it is even starker: 50 photos packed at
a **0.998 pack/worktree ratio with 0 of 50 blobs deltified**; ten trivial re-saves of one 483 KB photo
grew the pack by **508,682 bytes per edit** — a full copy every time; and after deleting every image,
`.git` remained at **30 MB against a 4 KB worktree**. Git gets *zero* benefit from both delta and zlib
on already-compressed formats, and the cost is permanent.

Relevant knob (**VERIFIED**, <https://git-scm.com/docs/git-config>): `core.bigFileThreshold`, default
**512 MB**, above which git skips delta compression *and* does not load the file into memory whole.
Note this does **not** save you here: a 2 MB image is far below the threshold, so git *tries* to delta
it, fails to find useful deltas, and stores it in full anyway. You can mark paths `-delta` in
`.gitattributes` to skip the wasted CPU, but that changes nothing about the storage cost.

**This is why §G puts attachments in a content-addressed store with content-defined chunking rather
than in git blobs.** It is also why git-annex, git-LFS, DVC and Xet all exist — every one of them is a
workaround for this exact measurement.

### D.3 Partial and shallow clone: what you gain and what you lose

**VERIFIED** from git's documentation and GitHub's partial-clone guidance:

| Mode | Command | Effect | What breaks |
|---|---|---|---|
| **Shallow** | `--depth 1` | Only the tip commit | No history at all — `log`, `blame`, `bisect` are gone. Deepening later is awkward |
| **Blobless** | `--filter=blob:none` | All commits + trees, blobs fetched on demand | `log -p`, `blame`, `diff` of old revisions trigger network round-trips; **unusable offline** |
| **Treeless** | `--filter=tree:0` | Commits only | Almost any history operation refetches; only good for throwaway CI |
| **Sparse checkout** | `--filter=blob:none` + cone mode | Materialise only some directories | Fine — the best fit for a Drive: check out only the folders the user opened |

**Correction — `--filter=blob:none` on its own buys you nothing.** A parallel scaling pass measured a
blobless clone at **exactly the same size as a full clone** (22 M vs 22 M; and at 100k-file scale
136 M full vs 12 M only once `--sparse` was added). A blobless clone still fetches every blob needed to
check out `HEAD` — which is the entire current workspace. **The 15–35× win comes from `--sparse`, not
from the filter.**

**And the filter fails open.** Without `uploadpack.allowFilter=true` on the server, git prints
`warning: filtering not recognized by server, ignoring` and performs a **full clone anyway** — a
warning, not an error. This is trivially easy to ship misconfigured across a whole mobile fleet and
never notice.

The honest trade for this product: **blobless + sparse cone checkout** is the right default for a
client, because a Drive user genuinely does not need every blob of every historical version of every
document on their laptop. But note the consequence — **history browsing becomes an online operation**,
which quietly forfeits one of the local-first ideals the whole design is meant to deliver. Obsidian
Git users hit this from the other direction: issue #763's proposed fix for repo bloat was
`--depth 1`, and the requester's own "Cons" note reads simply *"no history in Vaults"*. **Every
storage remedy in this family is paid for in history.**

`scalar` (Microsoft's large-repo wrapper, from the VFS-for-Git work) is in mainline git. **Now
VERIFIED**: git's own release notes for **2.38.0 (released 2022-10-03)** state *"The 'scalar' addition
from Microsoft is now part of the core Git installation."* Two details from its actual applied config
are worth copying: it sets `index.version=4` directly but **`feature.manyFiles=false` and
`index.skipHash=false`**, and it sets **`gc.auto=0` + `maintenance.strategy=incremental`** — replacing
ad-hoc gc with scheduled maintenance, which is exactly the fix for §B.4's `index.lock` race.
**It does not enable `core.splitIndex`** — and a parallel pass found `core.splitIndex` combined with
`index.version=4` + `index.skipHash` reproducibly **SIGABRTs** on git 2.47.3
(`BUG: wt-status.c:584: multiple renames on the same target?`), corrupting the index. That is the exact
combination you get from "enable all the performance knobs". **Do not set `core.splitIndex`.**

### D.4 Mobile — where "git is your Drive" actually breaks

This is the weakest link, and the Ink & Switch local-first essay flagged it in 2019: Git+GitHub
**fails the Multi-device ideal** outright, with the note that *"Support for mobile devices is currently
weak."* Seven years later the situation is not much better.

The evidence from a real, popular, actively-maintained product (**VERIFIED**, obsidian-git issues):

- Mobile git runs on **isomorphic-git**, a pure-JavaScript implementation — issue
  [#572](https://github.com/Vinzent03/obsidian-git/issues/572) is an open discussion about replacing it
  with `wasm-git` for performance. Clone crashes and multi-minute pushes are reported
  ([#694](https://github.com/Vinzent03/obsidian-git/issues/694),
  [#501](https://github.com/Vinzent03/obsidian-git/issues/501)).
- **Conflict resolution on mobile is effectively unsupported** —
  [#340](https://github.com/Vinzent03/obsidian-git/issues/340) *"Merge Conflicts not supported on
  mobile?"* (open since 2022-10-16), [#920](https://github.com/Vinzent03/obsidian-git/issues/920)
  *"Conflict experience on mobile needs improving"* (2025).
- And the one that matters: [#558](https://github.com/Vinzent03/obsidian-git/issues/558) **"Data loss
  when mobile has conflicts" — open since 2023-07-13.**

Combine that with §D.1's measurement that the index alone is **8.5 MB at 100k files** — a structure
that must be parsed and rewritten on every operation, in JavaScript, on a phone — and with §D.2's
result that attachments dominate repo size. **A phone cannot sensibly hold a full clone of a real
Drive**, and the git implementations available to it are the slowest and least complete.

**The decisive finding, from a parallel scaling pass (VERIFIED via GitHub API and issue trackers):
the two features that make large repos tractable are exactly the two no mobile-viable git library
implements.**

| Feature | canonical git | libgit2 | isomorphic-git |
|---|---|---|---|
| **Partial clone (`--filter`)** | yes | **NO** — issue #5564 open, untouched since 2022-05-01 | **NO** |
| **Sparse checkout** | yes | **NO** — issue #2263 open since **2014-04-11 (12 years)** | **NO** — issue #1735 open |
| Shallow clone | yes | yes (v1.7.0+) | yes |

§D.3 just established that **`--sparse` is where all the value is**. Mobile cannot have it. Working
Copy — the healthiest mobile git client, VERIFIED on libgit2 1.9.7 by its own 6.9.4 release notes —
documents neither shallow, partial, nor sparse anywhere in its 121 KB manual, consistent with those
gaps.

Two further disqualifying facts about **isomorphic-git**, which is what Obsidian Git runs on mobile:
it **emits no packfile deltas at all** (its pack writer is `readObject → writeObject → deflate`, with
no base selection or `ofs_delta`/`ref_delta` emission), so every push ships whole objects over
metered cellular; and it holds whole packs in memory — a reported measurement shows reading **one
commit** from a 768 MB pack peaking at **~2.5 GB RSS**. For contrast, canonical git cloning a
100k-file repo peaked at **150 MB RSS**. The memory problem is an isomorphic-git problem, not a git
problem.

**The practical answer** is that mobile must not be a git client at all. It should be a thin client of
the document server (§G): the CRDT session gives it realtime editing and offline buffering, and the
server owns the repository. This is also what Zed does — guests hold no checkout — and it is the only
model in this report that does not produce data-loss bug reports.

### D.5 What breaks first, in order

1. **Concurrent writers** (§B.6) — immediately, at any scale, and it loses data. Measured at both the
   ref layer (12/12 pushes rejected) and the index layer (7/8 `git add` failed on `index.lock`). Not a
   scaling issue; an architecture issue.
2. **Binary attachments** (§D.2) — 20.6× amplification per revised image, **0 of 50 JPEGs deltified**,
   and **unrecoverable**: deleting the images leaves the history intact forever. This is the only item
   here you cannot fix after the fact without rewriting history and breaking every clone. **Decide it
   before the first commit.**
3. **Mobile clients** (§D.4) — where the product promise quietly dies, because libgit2 and
   isomorphic-git lack the exact two features (partial clone, sparse checkout) that make it tractable.
4. **Loose-object explosion and `index.lock` vs background gc** (§B.4) — within days of enabling
   autosave. A parallel pass measured 1,000 autosave commits at **38 MB loose → 1.5 MB packed**, a
   25× penalty for not packing. Set `gc.auto=0` and run scheduled `git maintenance`, as scalar does.
5. **Ref explosion**, if you model per-document or per-client refs — 5,000 refs cost **20 MB in 5,001
   loose files** (4 KB of slack each) until `git pack-refs --all`. Consider the **reftable** backend.
6. **History legibility** (§B.4) — cosmetic, but it destroys the "you can inspect your own data" pitch.
7. **File count** (§D.1) — **not a problem** below ~100k documents; `git status` is ~90 ms at 100k, or
   ~6 ms with a sparse index, or ~35 ms with a free `-uno`. Do not spend engineering here first.
---

## E. Existing "git is my drive" products

### E.1 The headline finding: exactly one product does realtime multiplayer on git

**Keystatic** (`Thinkmill/keystatic`, **VERIFIED**: MIT, 2,322★, last commit 2026-08-26;
<https://keystatic.com>) is the **only** product in this survey that does true realtime multiplayer on
top of git — and its architecture is precisely the one recommended in §G.

**VERIFIED from its source:** `packages/keystatic` depends on `yjs ^13.6.11`, `y-prosemirror`,
`y-protocols` and `@toeverything/y-indexeddb`. `src/app/shell/collab.tsx` builds a `Y.Doc`, an
`Awareness` instance for presence, an IndexedDB provider for offline, and a `WebsocketProvider`
pointed at `wss://live.keystatic.cloud/${project}`. Presence is scoped per branch and per document.
The Yjs doc is keyed per entry inside a shared `Y.Map<Y.Doc>` and hydrated from the parsed file value
(`getYjsValFromParsedValue`) — i.e. **the file is canonical, the CRDT is hydrated from it, and a save
collapses CRDT state into a single git commit.**

It is gated behind Keystatic Cloud **Pro ($10/mo base, +$5/mo/user past 3)** and their own docs label
it *"Multi-player editing (experimental)"*.

**Two things this tells us.** First, the architecture in §G is not speculative — it is shipped, by two
independent teams (Keystatic and CollabMD), reached independently. Second, that the only implementation
is *experimental and paywalled* tells you where the difficulty actually sits: not in the CRDT, but in
running the relay and deciding **who commits, and when, at the end of a session.**

**Everything else in this space is one-writer-at-a-time.** Decap, Sveltia, TinaCMS, Pages CMS,
CloudCannon, Gitea/Forgejo and Prose all serialise through "load file → edit → commit". Keybase goes
further and takes an actual lock.

### E.2 Comparison table

| Product | License | Status / last commit | Multiplayer? | Conflict handling | Editor engine |
|---|---|---|---|---|---|
| **Keystatic** | MIT | Alive, 2,322★, 2026-08-26 | **YES — Yjs CRDT** (Cloud Pro, experimental) | CRDT merge in session; one commit per save | ProseMirror + Yjs |
| **TinaCMS** | Apache-2.0 | Alive, 13,758★, 2026-08-28 | No | Branch-per-editor + PR (**paid** tier) | Plate (Slate) |
| **Decap CMS** (ex-Netlify CMS) | MIT | Alive, 19,321★, 2026-08-21 | No | **Rebase + force-push**; only detects *branch-name* collisions | Slate → Plate (Apr 2026) |
| **Sveltia CMS** | MIT | Very alive, 2,759★, 2026-08-28 | No | **None — silent last-write-wins** | Lexical + turndown/marked |
| **Pages CMS** | MIT | Alive-ish, 3,949★, 2026-06-08 | No | Not surfaced | — |
| **Front Matter CMS** | MIT | Alive, 2,539★, 2026-08-21 | No | Delegated to your git client | VS Code |
| **Prose.io** | BSD-3 | **Dead.** last commit 2024-02-21; last release **2014-04-23** | No | — | Backbone-era |
| **CloudCannon** | Proprietary | Alive, commercial | No | Branch workflows (Team tier, $350/mo) | Proprietary |
| **Netlify Visual Editor** (ex-Stackbit) | Proprietary | **Acquired 2023-06-29** | No | Two-way content sync | Proprietary |
| **Forestry.io** | — | **Dead** — domain redirects to Tina | — | — | — |
| **Gitea / Forgejo web editor** | MIT / GPL-3 | Alive | No | **Warn, then overwrite on confirm** | Plain text + Preview. **No WYSIWYG for files** |
| **Working Copy** (iOS) | Proprietary | **Very alive**, v6.9.4 2026-08-24, shipping since 2014 | No | Git merge + explicit resolve UI; folder sync = **last-modified-wins + 7-day undo bin** | Basic text editor |
| **GitJournal** | AGPL-3.0 | **Semi-dormant.** commits to 2026-05-26 but last release **2021-09-15**, last iOS update **2022-06-29** | No | Git merge (assumes single user) | Markdown |
| **Obsidian Git** | MIT | Very alive, 11,872★ | No | Merge; conflict markers | Obsidian |
| **gitfs** (PressLabs) | Apache-2.0 | **Dead.** last commit 2021-08-09, last release 2019-10-20 | No | *"automatically accepting local changes"* | FUSE |
| **Keybase git / KBFS** | BSD-3 | Repo alive, product coasting (Zoom-owned) | No | **Repository locking — "No overwriting or conflicts"** | — |
| **GitStorage** | Proprietary hardware | **DEAD** — DNS resolves, no HTTP response | No | — | Basic web edit |
| **tinkerhub/git-drive** | none | **Stillborn.** 3★, single commit 2021-04-30, README only | — | — | — |

### E.3 Nobody merges — the five real strategies

This is the least flattering part of the prior art, and it is worth being blunt about in the design doc.
**VERIFIED** from source and docs:

1. **Rebase + force-push (Decap).** `packages/decap-cms-backend-github/src/API.ts` rebases the draft
   branch then `patchBranch(..., {force: true})`. The only thing Decap calls a "conflict" is a
   *branch-name* collision. **Content-level concurrency is not detected at all.**
2. **Silent last-write-wins (Sveltia).** No conflict/409/base-SHA handling anywhere in its backends.
   Its only `Conflict*` UI component handles **asset filename collisions on upload**. Second save wins,
   silently.
3. **Warn, then clobber (Gitea/Forgejo).** The two most instructive strings in this whole survey, from
   `options/locale/locale_en-US.json`:
   > *"The file contents have changed since you started editing. Click here to see them or **Commit
   > Changes again to overwrite them**."*
   >
   > *"The Commit ID does not match the ID when you began editing. **Commit into a patch branch and
   > then merge.**"*

   That is the honest state of the art for browser editing on a forge.
4. **Pessimistic locking (Keybase).** <https://book.keybase.io/git>: *"**No overwriting or conflicts.**
   ... Keybase knows to lock your repository when necessary."* They built git-as-a-drive and solved
   concurrency by **forbidding it**.
5. **Last-modified-wins with a data-loss warning and an undo bin (Working Copy).** Verbatim from
   <https://workingcopy.app/manual/> §6.5: Working Copy picks *"the side most recently changed"*, flags
   it with a warning icon *"to draw your attention to this **possible data-loss**"*, and — crucially —
   *"You can restore files overwritten or deleted by tapping Restore... **Backup files are kept for at
   least seven days.**"*

**Steal #5.** It is the only *humane* option in the set, it is the cheapest to build, and it is the
only place in the entire survey where anyone builds a **recovery path** instead of pretending the
problem does not exist. A visible "this overwrote something, here is the other version, for 7 days" is
worth more than a clever merge that is wrong 5% of the time.

### E.4 The branch convention everyone converged on

**VERIFIED from source.** Decap's `packages/decap-cms-lib-util/src/APIUtils.ts`:

```ts
export const CMS_BRANCH_PREFIX = 'cms';
export function branchFromContentKey(contentKey) { return `${CMS_BRANCH_PREFIX}/${contentKey}`; }
export function generateContentKey(collectionName, slug) { return `${collectionName}/${slug}`; }
```

So a draft lives on **`cms/<collection>/<slug>`**, with a PR opened against main. Status is tracked
**out-of-band** and per-backend: GitHub uses **PR labels prefixed `decap-cms/`**, GitLab uses MR
labels, Bitbucket uses PR comments. **Sveltia uses the identical convention**
(`WORKFLOW_BRANCH_PREFIX = 'cms'`), though only for GitHub and GitLab.

Note what this means: **git branches carry the content, but the workflow *state* does not fit in git**
and gets pushed into the forge's label system. That is the same lesson as Gitea storing issues in SQL
(§B.2) — mutable app state does not belong in git.

### E.5 WYSIWYG ↔ Markdown: Slate/Plate won, and the round-trip is the lossy part

| Product | Engine | Markdown bridge |
|---|---|---|
| Decap (legacy) | Slate 0.118 | unified/remark/rehype (`rehype-remark`) |
| Decap (new, Apr 2026) | **Plate** | markdown widget **deprecated, not actively maintained** |
| TinaCMS | **Plate** + ~22 plugins | `@tinacms/mdx` |
| Keystatic | **ProseMirror** | `@markdoc/markdoc` — canonical format is **Markdoc, not CommonMark** |
| Sveltia | **Lexical 0.49** | `turndown` (HTML→MD) + `marked` (MD→HTML) |
| Gitea/Forgejo | none | plain text + Preview tab |

Three observations that matter for this project:

- **Nobody uses Tiptap** in the git-CMS space, and **only Sveltia uses Lexical**. Choosing Slate/Plate
  puts you on the Decap+Tina path; Lexical puts you on Sveltia's.
- Both Decap and Sveltia route through an **HTML intermediate** (`rehype-remark`; `turndown`), and
  **that is where round-trip loss concentrates** — HTML that Markdown cannot express gets flattened or
  dropped.
- **Keystatic sidesteps the problem by changing the format**: it maps ProseMirror nodes directly to
  **Markdoc** AST nodes, giving a much tighter round-trip at the cost of not being plain CommonMark.
  This is a real strategic fork for a git-backed suite: *plain Markdown with lossy WYSIWYG*, or *a
  slightly extended Markdown with a faithful one*. Decap deprecating its own eight-year-old
  Slate↔remark bridge in April 2026 is evidence that the first option is hard to maintain.

### E.6 Mobile and filesystem products

**Working Copy** is the healthiest thing in the survey and the strongest counter-example to "mobile
git is impossible": **VERIFIED** v6.9.4 shipped **2026-08-24**, on the App Store since **2014-11-08**,
4.85★ over 3,740 ratings. Ink & Switch's 2019 call that it was *"a promising Git client for iOS"* has
aged well. Its **Files.app document provider** exposes repos as a Files location so any Files-aware app
reads and writes in place and Working Copy commits afterward; it also ships a WebDAV server and
Shortcuts automation. **NOT CONFIRMED:** which git library it uses — libgit2 appears nowhere in its
manual or listing. Do not assert libgit2.

**Obsidian Git is the cautionary tale, in its own words.** Its README states in bold: **"The Git
implementation on mobile is very unstable! I would not recommend using this plugin on mobile."** No
Obsidian plugin can shell out to native git on iOS/Android, so it runs **isomorphic-git** (pure JS),
which costs it **SSH auth entirely**, caps repo size by RAM, and provides no rebase strategy and no
submodules. **This is the single strongest signal in the survey that "git in the browser / on mobile"
is an engineering wall, not a detail.** It corroborates §D.4 independently.

**"Git-Drive" — there is no real product by this name.** `tinkerhub/git-drive` exists but is
stillborn: **3 stars, no license, one commit (2021-04-30), README only**, with "How to configure: To be
added". Its README is nonetheless a perfect one-paragraph statement of this project's thesis:
*"Normally we write google docs and save it in drive. Git drive is an open source self hosted platform
where you can write docs and save it to a github repo instead."*

**GitStorage — confirmed to have existed, confirmed dead.** gitstorage.com resolves (52.203.25.192) but
does not respond on :80 or :443. The Wayback snapshot of **2019-12-25** confirms **GitStorage Inc.,
Boston MA**, selling a solid-state **git server appliance** ("GS-64") with an encrypted filesystem, a
web frontend for repo/user/permission management, and — relevant here — *"Users can also view and edit
files without the need to clone repositories."* Marketed at programmers *and* CAD users and web
designers. **A useful data point that "git as a private drive appliance" was tried commercially and did
not survive.**

**gitfs (PressLabs)** — Apache-2.0, 2,594★, **dead** (last default-branch commit 2021-08-09, last
release 2019-10-20). Still the canonical "git is my filesystem" artifact, and its thesis is this
project's: mount a repo and *"all their changes will be automatically converted into commits... useful
in places where you want to keep track of all your files, but at the same time you don't have the
possibility of organizing everything into commits yourself."* Its conflict strategy was
*"automatically accepting local changes."* Built by a managed-WordPress host for internal use — the
economics never worked as a product.

**FUSE-over-git generally is an empty space**: `artagnon/phoenixfs` (208★, 2019), `centic9/JGitFS`
(36★), `semk/GitFS` (32★, 2020), then a tail of toys. The one live project,
`cloudflare/artifact-fs` (1,124★, Apache-2.0, pushed 2026-08-12), is read-optimised lazy hydration for
**agent sandboxes**, not a user drive.

**Keybase git** is architecturally the most interesting: a **git remote helper**
(`keybase://team/<team>/<repo>`) making the repo end-to-end encrypted — Keybase cannot read contents,
filenames, or the repo name — with every write signed by device keys. The docs explicitly distinguish
*first-class git repos* from *a repo sitting in KBFS*, and the reason is concurrency: **only the former
gets locking.**

### E.7 Gitea / Forgejo web editing: exactly what exists

**Exists** (VERIFIED from `locale_en-US.json` and Codeberg docs): create / edit / delete / upload file,
rename via path field, a **Preview** tab and a **Preview Changes** diff tab, commit message + extended
description, a choice of *"commit directly to this branch"* or *"create a new branch and start a pull
request"*, GPG signed commits, and auto-fork-then-edit for users without write access.

**Does not exist:** any **WYSIWYG for repository files**. Rich-text editing is confined to issue/PR
comment boxes. Hard limits are explicit: `cannot_edit_lfs_files`, `cannot_edit_too_large_file`,
`cannot_edit_non_text_files` (*"Binary files cannot be edited"*), `file_is_a_symlink`,
`must_be_on_a_branch`.

**There is a large, obvious product gap here**, and it is the one this project is aiming at.

### E.8 The Netlify Identity vacuum — a real strategic risk

VERIFIED lineage: Netlify CMS → **Decap CMS, announced 2023-02-23**; `netlify/netlify-cms` now
**redirects** to `decaporg/decap-cms`. Netlify **acquired Stackbit on 2023-06-29** (VERIFIED from
netlify.com/press); it is now **Netlify Visual Editor**. **Forestry is dead** and its users were
migrated to Tina.

The important part: **Git Gateway's entire purpose was to let editors write to a repo *without giving
them direct write access*** — exactly the permission problem a git-backed Workspace has. But
**`docs.netlify.com/llms.txt` (the full 160-entry docs index, fetched 2026-08-28) contains zero entries
for Identity or Git Gateway**, and both Identity doc paths return 404. Decap's docs now lead with
escape hatches ("Git Gateway without Netlify", self-hosted GoTrue, PKCE mode with a `gateway_url`), and
Decap announced **Decap Turbo on 2026-05-05** — a SaaS focused on *"centralized authentication, and
granular permissions."* Sveltia never implemented git-gateway at all.

**The shared hosted-identity layer that made git-backed CMSs usable by non-developers has evaporated,
and every project is now rebuilding it as a paid service.** (The exact deprecation announcement is
**NOT VERIFIED** — the evidence is absence-from-docs, which is strong but circumstantial.)

For this project that is both a risk and the opportunity: **you cannot outsource the "editors without
repo write access" problem to anyone. You have to build it — and it is exactly what people pay for.**

### E.9 Business models

The pattern is unambiguous: **the editor is free and open source; the money is in hosted auth,
permissions, coordination and media. Nobody charges for editing Markdown.**

| Product | Model |
|---|---|
| **Keystatic Cloud** | Free (3 users) → Pro **$10/mo** + **$5/mo/user** past 3. Pro unlocks **multiplayer** |
| **TinaCMS** | Free (2 users) · Team **$24/mo** · Team Plus **$41/mo** (**adds Editorial Workflow**) · Business **$249/mo** |
| **CloudCannon** | Standard **$55/mo** · Team **$350/mo** (**adds branching workflows**) · migrations from **$3,000** |
| **Decap** | Donations → **Decap Turbo** SaaS (auth + granular permissions) |
| **Sveltia** | Fully free, sponsorship only |
| **Working Copy** | **One-time purchase, no subscription**; free tier deliberately cannot **push** |
| **GitJournal** | Pay-what-you-want, one-time; "email me if you can't afford it" |

**Two structural observations.** First, **editorial workflow is the paywall** — Tina puts it on Team
Plus, CloudCannon puts branching on the $350 tier, Decap Turbo's pitch is auth and permissions. The
free tier is always *"one writer commits to main."* **Multi-writer coordination is empirically the
thing people pay for**, which is a good position for this project, since that is the product.

Second, **Working Copy's model is the only one that has survived twelve years unchanged**: perpetual
license, no subscription, one developer, and the free tier's paywall sits exactly at **push** — the
write boundary to the remote.

### E.10 What to take from the prior art

1. **The architecture is proven twice** — Keystatic and CollabMD independently reached CRDT-session +
   git-durable-store. Read Keystatic's `collab.tsx` before designing your own.
2. **Use `cms/<collection>/<slug>` if you want ecosystem interop**, or at least steal its shape. But
   note that workflow *state* had to go into forge labels, not git.
3. **Copy Working Copy's conflict humility**: last-writer-wins + visible warning + a 7-day restore bin
   beats a clever merge that is subtly wrong.
4. **Assume mobile is not a git client.** Obsidian Git's own README says so.
5. **Own the identity/permissions layer.** Netlify Identity's disappearance means nobody will provide
   it for you, and it is simultaneously the thing the market pays for.
---

## F. What will actually break

Ordered by when you will hit it, not by how bad it is. Items marked **MEASURED** were reproduced on
this machine; the rest are sourced.

**1. Two people in one paragraph — day one. (MEASURED)**
A Markdown paragraph is one line; git merges by line. Two disjoint word edits to the same paragraph
conflict, always (§C.1). Semantic linefeeds only help when edits are **≥2 lines apart** — adjacent
sentences still conflict (§C.2). No diff algorithm option changes this (§C.3). *Mitigation:* the CRDT
session absorbs this before git ever sees it. This is only fatal if you skipped that layer. For the
residual cases that still reach git, copy **Working Copy's recovery pattern** (§E.3): pick a winner,
say so visibly, and keep the loser restorable for seven days.

**2. Concurrent auto-commit locks out the second writer — day one. (MEASURED)**
Two clients auto-committing and pushing to one branch: **12/12 of the second client's pushes rejected,
zero of its commits reached origin.** With a `pull --rebase` retry loop and both editing the same
paragraph: **8/8 rebases conflicted, 0% of the second writer's work landed** (§B.6.1–B.6.2). This is
the single biggest risk in the design and it has no configuration-level fix. *Mitigation:* exactly one
process writes the working copy. Non-negotiable.

**3. Rich-text intent silently lost, if Markdown is the sync format — day one, invisibly.**
Concurrent overlapping formatting merges to something neither author asked for, and there is no error
(§A.1, Peritext). This one is dangerous precisely because it never announces itself. *Mitigation:*
never merge into Markdown; project out of a rich-text CRDT.

**4. `index.lock` races between the autosaver and background gc — within days.**
`gc.auto` fires at **6,700 loose objects** and `gc.autoDetach` defaults to **true**, so gc runs
*concurrently* with the next autosave. At a 1-minute interval a single user crosses that threshold in
**one to two days** (§B.4). Obsidian Git has a documented bug family spanning 2022→2026 from exactly
this, and jj hits the same class of bug with `working_copy.lock`. *Mitigation:* own a real locking and
gc-scheduling story; never let two writers near the same `.git`.

**5. Unreadable history — within a week.**
Thousands of `vault backup: 2026-08-28 14:31:07` commits destroy `git log`, `git blame` and `git
bisect`. Every mitigation trades something away: squash-on-push destroys the recovery points that
justified autosaving; shallow re-clone deletes the history outright (issue #763's own "Cons" say *"no
history"*). *Mitigation:* commit at explicit, coalesced boundaries with **LLM-written messages** —
Patchwork's most successful history UI (§A.4, entry 09) — and keep the fine-grained trail in the CRDT,
on a separate axis, the way jj's `evolog` does.

**6. CSV collaboration — the first time two people touch a sheet. (MEASURED)**
Plain git: two different cells in the same row conflict; a column insert conflicts the **entire file**
(§C.4). *Mitigation:* this one is genuinely solved — the `daff` merge driver handled every case
correctly in testing, including column insert and row reorder, and conflicted only on a true same-cell
collision. Wire it up on day one; it is nearly free.

**7. Binary attachments in git — as soon as real users embed images.**
Git stores whole blobs; LFS deduplicates at whole-file granularity, so every save of a large file
stores it again (§B.1). GitHub's 100 MB hard limit is hit by ordinary note-taking users
(obsidian-git #248). *Mitigation:* content-defined chunking into a CAS (the Xet model, ~64 KB
rolling-hash chunks), pointers in git. Do not put attachment bytes in git blobs.

**8. Prose merges that are *plausible but wrong*.**
`weave` merged three cases git could not, and correctly refused three semantically dangerous ones
(§C.5) — but the ones it merged were labelled **"medium confidence"** auto-resolutions, i.e. silent
prose merges no human reviews. It is at **v0.5.2, six months old, from a small unknown vendor**.
*Mitigation:* if you adopt it, surface every non-`very_high` resolution for review rather than trusting
it silently; keep git's conflict markers as the fallback.

**9. The document server becomes the bottleneck and the single point of failure.**
Room state is in-process (CollabMD says so explicitly). Hocuspocus's Redis extension gives you
availability and fan-out but **not CPU headroom** — *"all messages will be handled on all instances"*
(§G, VERIFIED). *Mitigation:* shard rooms to instances by document ID with sticky routing. The
single-writer rule already forces a document's room and its working copy to be co-located, so
room-sharding is the natural topology rather than a retrofit.

**10. jj's best features do not survive contact with plain git.**
If you adopt jj for its autosave model, note that **conflicted commits cannot be represented in git**
— they persist as non-standard `jj:trees` headers plus decoy `.jjconflict-*/` directories — and change
IDs are *"not preserved through a rebase operation"* by standard git tooling (§B.3). Anyone who clones
your "real git repo" sees garbage. *Mitigation:* steal jj's model (change-ID/evolog, operation log);
do not put jj in the data path if plain-git interop is the product promise.

**11. Mobile.**
See §D. Flagged here because it is where the whole "git is your Drive" promise is most likely to be
quietly abandoned.

### The one-line version

Everything above is survivable except **#2**. Prose merge is annoying, bloat is manageable, history
noise is cosmetic — but *two devices independently committing and pushing the same document loses
work, measurably and silently*, and no amount of tuning fixes it. **The architecture must guarantee a
single writer per repository. Every other decision in this document is downstream of that one.**
---

## G. Recommended storage + collaboration architecture

### G.0 Resolved: the editor is CodeMirror 6 over the markdown source, not ProseMirror

**An earlier draft of this section recommended Tiptap/ProseMirror over a rich-text Y.Doc, projected
out to Markdown on save. That was wrong, and I am reversing it.** The conflict with
`03-docs-editors.md` §5–6 is resolved in that document's favour. What follows is the reasoning, the
conditions, and the tradeoff I am accepting.

**What actually settled it — the decisive check.** `03` argues byte-stability is free only when the
editor buffer *is* the markdown file. I tested that against the one product I had already identified
as the closest live analogue to this project (§A.3). **VERIFIED** — CollabMD's `package.json`:

```
@codemirror/lang-markdown  ^6.5.2      y-codemirror.next  ^0.3.6
@codemirror/state/view     ^6.x        yjs                ^13.6.32
markdown-it                ^15.0.0     y-websocket        ^3.1.0
```

**No ProseMirror. No Tiptap. No turndown.** CodeMirror 6 + a plain-text Yjs binding over the markdown
source, with `markdown-it` — a parser with *no serializer* — for one-way preview rendering only. The
shipping product that does realtime multiplayer over plain files in a git repo already uses `03`'s
architecture, not mine. I had cited CollabMD as corroborating my recommendation; on inspection it
corroborates the opposite one.

**Why my Peritext argument does not carry the weight I put on it.** §A.1 is still correct on its own
terms, but I over-generalised it. The anomaly requires **concurrent, overlapping *mark* operations** —
two users bolding ranges that intersect, within one sync window. Three things narrow that sharply:

1. **It is not the common operation.** The overwhelming majority of co-editing is text insertion and
   deletion, which a plain-text CRDT merges correctly and which the anomaly does not touch at all.
2. **Peritext's own framing is asynchronous collaboration** — independently edited copies reconciled
   later. But in this architecture async divergence is handled by **git branches and merge drivers**
   (§C), not by CRDT merge. The CRDT only ever merges edits inside a live session, where the
   concurrency window is one network round-trip. Two users applying overlapping marks within ~200 ms
   is genuinely uncommon. **Peritext's counterexample lands hardest on the case this design does not
   use a CRDT for.**
3. **The failure is visible and locally repairable.** In a source-visible editor the user sees
   `**The **fox** jumped.**` and fixes it. It is a formatting glitch confined to a few characters.

**The severity asymmetry is the whole argument.** Compare the two failure modes honestly:

| | Peritext anomaly (plain-text CRDT) | Reserialization (rich-text CRDT + projection) |
|---|---|---|
| **Trigger** | Concurrent *overlapping mark* ops in one live session | **First touch of any file the editor did not author** |
| **Frequency** | Rare | **Every imported document, every time** |
| **Blast radius** | A few characters | **The whole file** |
| **Visible?** | Yes — stray delimiters in the source | **No** — the diff just says everything changed |
| **Repairable in-band?** | Yes, by any user | No — the bytes are already gone |
| **Effect on git** | None | **Destroys the diff, i.e. the product** |
| **Shipping evidence** | No product failure attributed to it | **Pithy** (`00-pithy-teardown.md`) and **Nextcloud Text** (`03` §7) both demonstrably lose data |

`00-pithy-teardown.md` shows a shipped product whose save path is *exactly* my original §G, and one
character rewrites the file into turndown's dialect. `03` §7 shows Nextcloud Text — Yjs + ProseMirror
over real markdown files, the best-resourced attempt at my original recommendation — with six years of
public failure: whole-file destruction "not just on the edited line", a still-open meta-tracker of ~25
markdown-preservation issues, a hand-maintained `keepSyntax.js` regex patch, data loss filed as
recently as **2026-08-26**, and a current effort to build *semantic* diffing because reserialization
had made byte diffs meaningless. **That last point is disqualifying on its own: this product's premise
is that git's diff is meaningful.** I am not going to recommend the one architecture with two
independent shipping counterexamples.

**Question 4 — minimal-edit serialization — is closed, negatively.** Diffing projected markdown against
the previous file and patching only changed regions is the option that would rescue the rich-text path.
Nobody has built it. **VERIFIED**: the canonical serializer `mdast-util-to-markdown` (MIT) exposes a
positional `Tracker`, and its own README says of it — *"This info isn't used yet but such functionality
**will allow** line wrapping, source maps, etc."* Source mapping is explicitly future work upstream.
And Nextcloud Text, with six years and the strongest incentive of anyone, did not build it either —
they built a regex escape-hatch and then pivoted to semantic diffing. Treat minimal-edit serialization
as **a research project, not an integration**.

**The decision, with conditions.** Use **CodeMirror 6 + `@codemirror/lang-markdown` + a live-preview
decoration layer, with `y-codemirror.next` binding a Yjs `Y.Text` over the markdown source.** The
buffer is the file; byte-stability is a property, not a feature; merges are text merges; and the CRDT
still does all the realtime work. **VERIFIED**: `yjs/y-codemirror.next` is maintained (206★, last push
2026-08-18) — but pin the released 0.3.x line, because its `main` branch now targets the unstable
**yjs v14**. CollabMD ships `y-codemirror.next ^0.3.6` against `yjs ^13.6.32`; match that.

**The tradeoff I am accepting, stated plainly:**

- **Concurrent overlapping mark operations can interleave delimiters.** Rare, visible, user-fixable.
  Mitigate by applying mark commands as single atomic CRDT transactions rather than two separate
  delimiter inserts, which removes the common case.
- **No true block-level WYSIWYG.** There are no blocks, only text and decorations, so drag handles,
  nested containers and arbitrary embeds get much harder. Tables are the known sore spot — `03` records
  Atomic Editor's author conceding *"the abstraction leaks in tables"*.
- **This does not generalise to Sheets and Slides.** A CSV grid and a slide canvas are different
  surfaces with different editors. That is fine and arguably correct, but it means "one editor for the
  suite" is off the table.

**Conditions under which the reversed choice would be right again** — worth recording, because they are
not exotic:

- **If the product were not git-backed.** Without a requirement for meaningful byte diffs, ProseMirror
  plus a rich-text CRDT is the better editor and Peritext's argument becomes decisive.
- **If you change the canonical file format to one designed for round-tripping.** This is Keystatic's
  move (§E.5): it serializes ProseMirror to **Markdoc**, not CommonMark, and gets a tight round-trip
  because the format is the editor's model. A real third path — it buys block WYSIWYG at the cost of
  the files no longer being plain Markdown.
- **If someone ships minimal-edit serialization.** Then the rich-text path gets byte-stability too, and
  this decision should be revisited.

Everything below is unchanged by this reversal except the editor layer: the CRDT is still session
state, the file is still the record, and there is still exactly one writer per repo.

### G.1 The stack

Stated as a layered stack:

```
┌─ EDITOR (browser / desktop / mobile) ────────────────────────────────┐
│  CodeMirror 6 + lang-markdown + live-preview decorations             │
│  y-codemirror.next binds a Yjs Y.Text over the MARKDOWN SOURCE       │
│  The buffer IS the file. Awareness = cursors/presence.               │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ y-websocket / Hocuspocus (MIT)
┌──────────────────────────▼───────────────────────────────────────────┐
│  DOCUMENT SERVER — the SINGLE WRITER for a given repo                │
│  · merges all concurrent edits in the CRDT (conflicts impossible)    │
│  · debounces, then writes the Y.Text buffer verbatim to disk         │
│  · owns the git working copy; nothing else ever writes to it         │
│  · watches the filesystem so agent/CLI edits flow back into the room │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ explicit, coalesced commits
┌──────────────────────────▼───────────────────────────────────────────┐
│  GIT — the archive, the branch/PR layer, the interop promise         │
│  · plain .md / .csv, human-readable, agent-readable, diffable        │
│  · daff merge driver for *.csv   ·  (optionally weave for *.md)      │
│  · metadata in timestamped union-merged append-only logs             │
│  · large attachments out-of-band (CDC/CAS), not as git blobs         │
└──────────────────────────────────────────────────────────────────────┘
```

**This is not a speculative design.** **CollabMD** is this exact stack, shipping and active —
CodeMirror 6 + `y-codemirror.next` over the markdown source, filesystem as source of truth, git commits
from the browser (§A.3, §G.0). **Keystatic** proves the CRDT-session-plus-git-commit half independently,
though it takes the other editor branch (ProseMirror serialized to **Markdoc**, not CommonMark — the
format-change escape hatch described in §G.0). **Zed** uses the same host-owns-the-filesystem shape for
code. The remaining hard part, and the reason Keystatic still labels its multiplayer "experimental", is
*who commits and when*.

**The load-bearing rules, each earned by a measurement or a cited source:**

1. **The CRDT is the wire protocol; the file is the record.** Never commit the `.ydoc`. §A.3 measured
   that git responds to two divergent CRDT binaries with `Cannot merge binary files` and offers only
   "keep ours / keep theirs" — i.e. silent total loss of one collaborator's work — while the CRDT
   merged the same two edits perfectly.
2. **Exactly one process writes the working copy.** This is not a preference; §B.6.1/§B.6.2 measured
   100% push rejection and 100% rebase-conflict failure for a second concurrent writer. Both shipping
   systems do this: CollabMD's server owns the vault, Zed's host owns the filesystem (both VERIFIED).
3. **The buffer is the file — never reserialize on save.** This replaces the earlier "Markdown is a
   projection" rule; see §G.0 for why it was reversed. Peritext's anomaly (§A.1) is real but narrow and
   visible; reserialization is common, whole-file, silent, and destroys git's diff, with two shipping
   counterexamples (`00-pithy-teardown.md`, `03` §7). Use remark/mdast for **analysis and a one-time
   normalization pass when a foreign file first enters a workspace** — never in the save path.
4. **Commits are explicit and coalesced, never per-keystroke.** Follow Patchwork's *dynamic history*
   (03): capture everything fine-grained in the CRDT, and project a *readable* history into git.
   Use Patchwork's finding (09) that **LLM-generated change summaries were their most successful
   history UI** to write the commit messages. Do not ship `vault backup: 2026-08-28 14:31:07`.
5. **Use a merge driver for tables today.** `daff` is 13 years old, MIT, and measured correct on every
   CSV case in §C.4 — including column insert and row reorder, which plain git cannot survive. This is
   the cheapest large win available and it directly addresses the "sheets is the hard part" gap.
6. **Use an edit lease for anything that cannot merge.** Copy CollabMD's `.drawio` model for slides,
   diagrams, and formula-bearing sheets: one holder edits, others view read-only and refresh on save.
   Honest, never corrupts, and vastly cheaper than a bespoke CRDT per format.
7. **Keep mutable app state out of git.** Gitea and Forgejo — projects whose product *is* git — use
   SQL for issues/PRs/wiki. Fossil puts artifacts in SQLite. Follow them: permissions, presence,
   comment threads and share links belong in a database. Use git-annex-style timestamped union-merged
   logs only for the metadata that genuinely must travel with the repo.
8. **Attachments do not go in git as blobs.** Use content-defined chunking into a content-addressed
   store (the Xet model: ~64 KB rolling-hash chunks, 64 MB blocks) with pointers committed to git.
   Git's whole-blob model plus autosave is the combination that kills repos.

**Where branches fit.** Ink & Switch's Upwelling found the "fishbowl effect" is real — writers do not
always *want* to be watched. A git-backed suite can offer what Google Docs structurally cannot:
private drafts that merge when ready. Implement it with Patchwork's constraints (06): edit on main by
default, no branching from branches, no naming required at creation, merge deletes the branch,
retroactive branch creation from edits already made.

**One scaling caveat on the document server, VERIFIED.** CollabMD's stated limitation — *"collaboration
room state is kept in-process and is not shared across replicas"* — is the generic Yjs-server problem.
Hocuspocus's Redis extension is the standard fix, but read its own warning carefully
(<https://tiptap.dev/docs/hocuspocus/server/extensions/redis>):

> "Hocuspocus can be scaled horizontally using the Redis extension. ... **The Redis extension does not
> persist data; it only syncs data between instances.** ... Please note that **all messages will be
> handled on all instances of Hocuspocus, so if you are trying to reduce cpu load by spawning multiple
> servers, you should not connect them via Redis.**"

So Redis buys you availability and connection fan-out, **not CPU headroom** — every instance processes
every message for every room. Real horizontal scale requires *sharding rooms to instances* (consistent
hashing on document ID with sticky routing), not broadcast. Plan for that from the start, because the
single-writer rule (#2) means a document's room and its git working copy must be co-located anyway —
which conveniently makes room-sharding the natural topology rather than an awkward retrofit.

---

## H. Verification gaps — do not assert these

Stated explicitly, per the research rules. These are things I looked for and could **not** confirm, or
confirmed only secondhand.

**Reversal recorded (§G.0).** An earlier draft of §G recommended Tiptap/ProseMirror over a rich-text
Y.Doc projected to Markdown, and cited CollabMD as corroboration. **Both were wrong.** CollabMD's
`package.json` shows CodeMirror 6 + `y-codemirror.next` with no ProseMirror and no serializer. The
recommendation is reversed in §G.0, and §A.1 and §A.5 are annotated accordingly. Flagged here because
anyone who read the first draft should know which parts changed.

**Could not confirm exists / not found:**
- **Minimal-edit markdown serialization** — diffing a projected document against the previous file and
  patching only changed regions. I could not find any implementation. `mdast-util-to-markdown`'s own
  README says its positional `Tracker` *"isn't used yet"* and describes source maps as future work, and
  Nextcloud Text did not build it in six years. Treat as unbuilt. (My WebSearch budget was exhausted
  before I could search exhaustively, so this is "found nothing", not "proved nothing exists".)
- No project, pattern, or advocacy for **committing CRDT binaries into git** as a durable format. The
  absence is a finding, not a gap in searching — but it is an absence, not a proof of impossibility.
- **"git-autocommit"** is not a canonical project. Six small abandoned namesakes exist (largest 77★,
  last push 2014-02-12). **Do not cite it as a tool.**
- **etckeeper** has no canonical GitHub repository under its own name; only stale mirrors and forks.
  Describe it by behaviour; do not link a fork as canonical.
- **XetHub the product is gone** — `xethub.com` returns HTTP 404. Do not link it.
- **`git.kernel.org` git-annex path is dead** (HTTP 404). The canonical source is
  `git://git-annex.branchable.com/`. Do not cite kernel.org.

**Verified as REPORTED only (secondhand; do not print as fact):**
- **Tangled's knots/spindles architecture** and the exact split between atproto PDS records and git
  storage. The funding facts (Tangled Labs Oy, $4.5M, ByFounders, 2026-03-02) are solid from
  SiliconANGLE; the architecture details come from third-party blogs, not a Tangled primary source.
- **DoltHub funding figures** (~$21M total, $16M Series A) — CBInsights via search only.
- **Radicle's current Heartwood release version and funding status**; the `refs/cobs` namespace layout
  comes from a generated wiki, not primary docs.
- **The Xet "default for all new repos as of 2025-05-23" date** — search-summarised, not fetched.
- **The date `martinvonz/jj` was renamed to `jj-vcs/jj`.** The redirect is VERIFIED; the date is not.
- **Automerge's binary format spec details** — the spec page was seen via search, not read in full.
- Whether **Logseq, Foam, Dendron, SiYuan or Anytype** auto-commit to git. Unchecked. **Anytype in
  particular is generally described as a custom CRDT protocol, not git** — do not assert otherwise.
- Any specific **"my .git folder reached N GB"** figure for Obsidian vaults. The only quantified claim
  I could verify is a user's estimate in issue #763 (*"hundreds of MB or more, often more than halving
  the size on disk"*).

**Section D sourcing:** the performance and storage figures in §D.1–D.2 are my own measurements on this
machine. The partial-clone/`scalar` material in §D.3 is from git's documented behaviour and is
**REPORTED** where noted — in particular **I did not verify the git version in which `scalar` was
upstreamed**, and the partial-clone trade-off table describes documented semantics rather than
benchmarks I ran.

**Attributed to a parallel scaling pass, not measured by me:** the JPEG deltification figures, the
8-way concurrent `git add`/commit results, the split-index SIGABRT, the loose-object and ref-explosion
numbers, the blobless-clone-size correction, `uploadpack.allowFilter` failing open, the libgit2 /
isomorphic-git feature gaps, and the isomorphic-git memory and no-delta findings. I have folded these
in because they corroborate or correct my own §D; the underlying commands and logs are that pass's, not
mine. The split-index crash in particular is **reproducible locally on 2.47.3 but of unknown upstream
status.**

**Measured but with caveats:**
- **`jj` was not installed on this machine and I did not install it** (per the standing rule against
  ad-hoc tool installs). Every jj claim in §B.3 is sourced from jj's own documentation and repository,
  **not** from running it. The conflict-model and evolog behaviour is quoted, not reproduced.
- **`weave` results are from v0.5.2** on a handful of hand-built cases. Six cases merged or refused
  correctly, but that is a spot-check, not a benchmark. Its "medium confidence" auto-resolutions are an
  unquantified risk.
- **`daff --inplace` did not work** in my testing (left the local file unchanged, exit 1); the
  `--output` form used by the official git driver worked correctly on every case. Use the driver.
- **`daff git csv` writes to global git config.** I ran it in a scratch directory and removed the
  `diff.daff-csv` / `merge.daff-csv` sections afterwards; `git config --global --get-regexp daff` now
  returns nothing. No other machine state was modified by this research.

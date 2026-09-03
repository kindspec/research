# DOCS layer: prior art, substrates, and the real gap

Research date: **2026-08-28**. All GitHub numbers (stars, license, last commit, open issues)
were pulled from the GitHub REST API on that date via authenticated `gh api`, unless noted.

**Labelling:** `[V]` = VERIFIED, I fetched the primary source (repo API, README, source file,
issue body, or ran the command myself). `[R]` = REPORTED, secondhand — a search snippet, a
third-party article, or an HN comment. `[V-E]` = verified *empirically*, I ran the experiment
and the output is reproduced below.

---

## 0. Executive summary

Three findings dominate everything else:

1. **The two biggest markdown-native projects both moved *away* from plain files this year.**
   Logseq split in two on 2026-04-24: the DB version stores everything in `db.sqlite` and
   markdown syntax "is no longer visible or editable"; the file-based app was exiled to
   `logseq/og`, is maintenance-only, and has had **no commit since 2026-05-28**. Outline's
   markdown column is annotated `@deprecated` in the source, with a comment that its own
   markdown export is "lossy". The industry is converging on JSON/CRDT-canonical, and treating
   markdown as an export format. That is the opening.

2. **The lossless-markdown problem is real, and the *architectural* answer is not a better
   serializer.** I round-tripped a 53-line torture-test file through pandoc and through
   remark. Pandoc changed 42 of 53 lines and silently deleted the YAML frontmatter. Remark
   changed ~12 regions. No configuration of remark-stringify is byte-stable on arbitrary
   input — tuning the options just moves *which* constructs get rewritten. The tools that
   actually get this right (Obsidian, SilverBullet, Atomic Editor) don't serialize at all:
   they keep the raw markdown text as the editor buffer and render decorations over it.

3. **ProseMirror and CodeMirror left GitHub on 2026-04-01 and 2026-04-15** — every repo in both
   orgs is archived — and their author shipped a *new* editor, Wordgard, on 2026-07-02.
   This is a substrate-selection event, not a footnote.

**Recommendation: build on CodeMirror 6 with a live-preview decoration layer** (the Obsidian
model), taking `kenforthewin/atomic-editor` (MIT) as the reference implementation or starting
point. See §6 for why, and §5 for the evidence that the ProseMirror-family alternatives
cannot give you clean git diffs.

---

## 1. Category A — local-first markdown apps with plain files on disk

| App | Storage on disk | Git | WYSIWYG | License | Last activity | Verdict |
|---|---|---|---|---|---|---|
| **Obsidian** | **True plain `.md`** in a folder + `.obsidian/` config | Community plugin (`obsidian-git`), not native | Live Preview via **CodeMirror 6**; raw md stays the buffer `[V]` | Proprietary (free for personal) | releases repo pushed 2026-08-28 `[V]` | **The reference implementation.** Closed source, so not a substrate — but the architecture to copy |
| **Logseq (file / "OG")** | Plain `.md` (org-mode support dropped) | None native | Outliner, not WYSIWYG | AGPL-3.0 | **repo `logseq/og`, last commit 2026-05-28** `[V]` | **Effectively frozen.** Maintenance-only by the vendor's own announcement (2026-04-24); 264 stars, one release (1.0.0, 2026-04-15) |
| **Logseq DB (2.0)** | **`db.sqlite`** — files abandoned `[V]` | None | Block editor | AGPL-3.0 | 2.0.1 released 2026-07-13; repo pushed 2026-08-27 `[V]` | **They abandoned plain files.** Docs: "Markdown syntax for blocks is no longer visible or editable" |
| **SilverBullet** | **True plain `.md`** in a "space" | None native | Live preview (**CodeMirror 6 + `@lezer/markdown`**) `[V]` | MIT | 2026-08-27 `[V]` | **Strong open-source reference.** Self-hosted server, Lua scripting, built-in query language. 5,947 ★ |
| **Zettlr** | True plain `.md` | None native | CodeMirror-based | GPL-3.0 | 2026-08-25 `[V]` | Alive. Academic/writing focus; not a suite |
| **Dendron** | Plain `.md` (VS Code) | Via VS Code | No | Apache-2.0 | **last commit 2025-06-01** `[V]` | **DEAD.** README states verbatim: "Dendron is currently in maintenace only, active development has ceased." |
| **Foam** | True plain `.md` (VS Code ext.) | Whatever VS Code does | No | NOASSERTION | 2026-08-13 `[V]` | Alive but thin — a bundle of VS Code extensions, not an app |
| **Joplin** | **SQLite** + resource blobs; markdown is the note *body* and an import/export format `[V]` | None native | Partial WYSIWYG | AGPL-ish (NOASSERTION) | 2026-08-28 `[V]` | Very active (56k ★) but **not files-on-disk** |
| **Anytype** | Local encrypted object DB (`anytype-heart`) | None | Block editor | NOASSERTION | 2026-08-26 `[V]` | Not plain files. Own CRDT/protocol |
| **AFFiNE** | **OctoBase** (Rust, local-first CRDT DB) `[V]` | None | BlockSuite blocks; docs **and** edgeless canvas | NOASSERTION | 2026-08-28 `[V]` | Huge (72k ★), does docs+canvas+DB views, but **blobs not files** |
| **Notesnook** | Encrypted, IndexedDB-based FS `[V]` | None | Tiptap-based | GPL-3.0 | 2026-08-27 `[V]` | E2EE-first; not files-on-disk |
| **Trilium (TriliumNext)** | **Database** (own note store) `[V]` | None | Rich text (CKEditor) | AGPL-3.0 | 2026-08-28 `[V]` | Very active fork (37.6k ★) after `zadam/trilium` was handed over — that repo now **redirects** to `TriliumNext/Trilium` `[V]`. Not plain files |
| **TiddlyWiki** | Single HTML file, or a folder of `.tid` tiddler files | None native | Own wikitext, not markdown | NOASSERTION (BSD) | 2026-08-25 `[V]` | Files-on-disk possible, but **wikitext not markdown** |
| **MarkText** | True plain `.md` | None | **Real WYSIWYG-over-markdown** | MIT | **revived 2026** `[V]` | **Notable:** dormant from v0.17.1 (2022-03-07) to v0.19.0-rc.1 (**2026-05-23**) — a 4-year gap — now shipping (v0.20.0-rc.1, 2026-07-05). 60.7k ★ |
| **Typora** | True plain `.md` | None | Best-in-class WYSIWYG-over-md | **Proprietary, paid** | n/a | Gold standard for the *feel*; closed, so not a substrate |
| **Zed** | Files on disk (it's a code editor) | Native git UI | Markdown preview, not WYSIWYG | NOASSERTION (GPL/AGPL mix) | 2026-08-28 `[V]` | Not a docs product; its git UI is worth studying |
| **Emacs org-mode** | Plain `.org` | Via magit | No (overlays) | GPL | n/a | Solves the whole problem for ~0.1% of humans. Note HN comment on Atomic Editor: "I regret to inform you that... you have built an Emacs + Orgmode" `[V]` |
| **Obsidian Bases** | **`.base` = YAML view config; the data stays in `.md` frontmatter** `[V]` | n/a | Table/card/list views | Proprietary | Core plugin, shipped 2026 | **Directly relevant to "Sheets".** The sidecar pattern: view config in one file, data in frontmatter. Cannot hold data not in a note |
| **Reor** | Plain `.md` + local vector index | None | Basic | AGPL-3.0 | **ARCHIVED**, last commit 2025-05-13 `[V]` | **DEAD** (repo is archived on GitHub) |
| **Flatnotes** | True plain `.md`, flat directory, no DB | None native (files are yours) | No — plain textarea + preview | MIT | 2026-08-02 `[V]` | Small (3.2k ★) but architecturally honest: self-hosted, zero database |
| **Memos** | **SQLite / MySQL / Postgres** `[V]` | None | Markdown-ish micro-notes | MIT | 2026-08-28 `[V]` | Very active (62.6k ★) but a DB app, and micro-blog shaped |

### What this table says

Only **six** of these keep true plain `.md` on disk *and* are alive: Obsidian (closed),
SilverBullet, Zettlr, MarkText, Flatnotes, Foam. Of those, exactly **two** — Obsidian and
MarkText — offer real WYSIWYG-over-markdown, and one of them is proprietary. SilverBullet is
live-preview, which is the same architecture minus polish.

Everything with a serious block/database feature set (Logseq DB, AFFiNE, Anytype, Trilium,
Notesnook, Joplin, Memos) has a database underneath. **Nobody has shipped an open-source,
files-on-disk, real-WYSIWYG docs app with git as the storage layer.**

---

## 2. Category B — self-hosted collaborative docs

The key question is the on-disk format. The answer is almost uniformly "blobs in Postgres."

| App | On-disk format | License | Last commit | Verdict |
|---|---|---|---|---|
| **Nextcloud Text** | **Real `.md` files in Nextcloud's file storage** `[V]`. Built on **Tiptap/ProseMirror** `[V]` | AGPL-3.0 | 2026-08-27 `[V]` | **The single closest existing thing to the thesis** — collaborative WYSIWYG that writes actual markdown files. Also the best available case study in why it's hard (see §7) |
| **Outline** | Postgres. Columns: `content` (**ProseMirror JSONB**), `state` (**Yjs bytea**), `text` (markdown TEXT, **`@deprecated`**) `[V]` | BSL/NOASSERTION | 2026-08-28 `[V]` | Source comment: *"@deprecated Use `content` instead, or `DocumentHelper.toMarkdown` if exporting **lossy** markdown. This column will be removed in a future migration."* They are actively deleting markdown as a storage format |
| **Docmost** | Postgres `pages` table: `content jsonb` (ProseMirror), `ydoc bytea` (Yjs), `text_content text` (search only) `[V]` | AGPL-3.0 | 2026-08-27 `[V]` | Same shape as Outline. Not files |
| **La Suite Docs** (`suitenumerique/docs`) | Postgres; BlockNote + Yjs. Django `Document` model carries title/excerpt/permissions, content is the Yjs doc `[V]` | MIT | 2026-08-28 `[V]` | French state-backed, 16.7k ★, very active. **Not files.** Uses BlockNote, whose markdown API is literally named `blocksToMarkdownLossy` |
| **HedgeDoc** | Markdown text **in a DB** (SQLite/MariaDB/Postgres) | AGPL-3.0 | 2026-08-28 `[V]` | Alive on the 1.x line (1.12.0, 2026-08-21) `[V]`. **HedgeDoc 2.0 still has not shipped** — the rewrite has been in progress for years; `archived_develop` branch exists `[V]` |
| **Etherpad** | Changeset/OT log in a DB (Postgres/SQLite/etc.) `[V]` | Apache-2.0 | 2026-08-27 `[V]` | Plain text, not markdown; markdown only via `ep_markdown` plugin. Not files |
| **AppFlowy** | Local SQLite + `collab` CRDT documents | AGPL-3.0 | **default branch last commit 2026-06-26** `[V]` | 76k ★ but the public repo's default branch is quiet; work has moved to AppFlowy-Cloud/other repos. Not files |
| **CryptPad** | **Encrypted blobs** — server cannot read content by design `[V]` | AGPL-3.0 | 2026-05-26 `[V]` | E2EE is fundamentally incompatible with "files an AI agent can read." Wrong model for this project |
| **BookStack** | MySQL; HTML (WYSIWYG) or markdown text in DB `[V]` | MIT | 2026-08-28 `[V]` | Extremely well-maintained (**1 open issue** at 19k ★) but DB-backed |
| **Wiki.js** | DB canonical, **plus a real Git storage module** with `sync`/`push`/`pull` modes on a 5-minute schedule `[V]` | AGPL-3.0 | **2026-05-01** `[V]` | **The most important prior art in this table.** It proves the "DB is truth, git is a mirror" pattern ships — and it's the pattern to *invert*. Note the repo has been quiet since May 2026 (v3 rewrite has long been "coming") |
| **Collabora Online / OnlyOffice** | OOXML (`.docx`/`.xlsx`) | MPL-2.0 / AGPL-3.0 | 2026-08-27 / 2026-07-22 `[V]` | Binary-ish XML in a zip. Diffs are useless, agents can't read it. Out of scope |

**Conclusion for B:** exactly one self-hosted collaborative editor (Nextcloud Text) stores real
markdown files. Every other serious project stores ProseMirror JSON + a Yjs blob and treats
markdown as a lossy import/export. Wiki.js's git module is the only shipped git integration,
and it is a one-way mirror, not a storage layer.

---

## 3. Category C — editor components

**The headline:** on **2026-04-01** every repo in the `ProseMirror` GitHub org was archived, and
on **2026-04-15** every repo in the `codemirror` org was archived `[V]`. Both projects moved to
Marijn Haverbeke's self-hosted forge at `code.haverbeke.berlin`. The READMEs left behind say so
verbatim: *"This repository has moved to https://code.haverbeke.berlin/prosemirror/..."* `[V]`.
On **2026-07-02** he released **Wordgard**, an MIT rich-text editor that replaces ProseMirror's
step system with CodeMirror-6-style changes and facets `[V]`. He states *"ProseMirror isn't going
anywhere—it will continue to be maintained."* `[V]`

This matters practically: the forge is not GitHub, so issue history, PR workflow, and
dependency-scanning tooling all change. Top HN comment (item 48772573, 341 pts, 2026-07-03):
*"The thought that Prosemirror is no more in active development is scary."* and
*"The code appears to be unavailable. This includes not just wordgard but all the ProseMirror
code as well."* `[V]` — the latter is an overstatement (it moved, it isn't gone), but it
captures the ecosystem's reaction.

| Component | Markdown round-trip fidelity | License | Last activity | Verdict |
|---|---|---|---|---|
| **CodeMirror 6** | **N/A — and that's the point.** The buffer *is* the markdown text. Fidelity is byte-perfect by construction; there is no serializer to be lossy | MIT | archived on GitHub 2026-04-15, dev at `code.haverbeke.berlin` `[V]` | **Build on this.** Powers Obsidian (Live Preview *and* Source mode) `[R]` and SilverBullet (`@codemirror/lang-markdown` + `@lezer/markdown`) `[V]` |
| **`kenforthewin/atomic-editor`** | Byte-perfect. README: *"Raw markdown is the source of truth. Every decoration is view-only, so copy, save, and round-trip through any other markdown tool are **byte-for-byte identical to a plain textarea**."* `[V]` | **MIT** | last commit 2026-07-11, pushed 2026-08-24 `[V]` | **The most directly reusable substrate found.** Obsidian-style live preview for CM6 in React, incl. WYSIWYG tables, wiki links, virtualization. Caveat: young (135 ★), and the Show HN (item 48345201) has real bug reports — *"typing things around and things jumps everywhere"*, cursor jumping to end of document; author shipped a fix in 0.4.2 mid-thread `[V]` |
| **ProseMirror** | `prosemirror-markdown` maps to a **CommonMark-subset schema** (doc, para, blockquote, hr, heading, code_block, lists, text, image, hard_break + em/strong/link/code) `[V]`. Anything outside that schema is dropped on parse | MIT | archived on GitHub 2026-04-01 `[V]` | Excellent editor, **wrong storage model** for byte-stable md. Its markdown module is a convenience, not a fidelity guarantee |
| **Tiptap** | Inherits ProseMirror's. No official markdown-canonical mode | **MIT** `[V]` | v3.30.5 on **2026-08-28** `[V]` | **The licensing scare is backwards:** in 2025 Tiptap *open-sourced* ~10 formerly-Pro extensions under MIT (HN 44202103, 2025-06-06; 44326955, 2025-06-20) `[V]`. Core is MIT and shipping daily. Paid tier = hosted collaboration/comments/AI, not the editor |
| **BlockNote** | **Explicitly lossy, by API name.** Docs table marks Markdown import *and* export "(lossy)"; the function is `blocksToMarkdownLossy()`. Docs advise: *"It's recommended to use BlockNote JSON… guaranteed to be lossless"* `[V]` | NOASSERTION (MIT + commercial "Pro") | 2026-08-26 `[V]` | **Disqualified as markdown-canonical**, and they say so themselves. Note they *replaced unified.js with a custom md parser/serializer* (PR #2624, merged 2026-04-03) and are still fixing round-trip bugs (#2720, 2026-05-07) `[V]` |
| **Milkdown** | Built on remark + ProseMirror — inherits remark's normalization (see §5). Better than BlockNote, still reserializes the whole doc | MIT | 2026-08-25 `[V]` | Open issue **#2396**: *"Provide a way to **patch** the current markdown without doing a full replace"* `[V]` — i.e. the full-reserialize problem, acknowledged upstream. Open issue **#2428** (2026-07-28): a plugin *"silently deletes user-authored inline `<br>` from loaded markdown"* `[V]` |
| **MDXEditor** | Lexical + mdast. Better md posture than most block editors, but still parse→AST→reserialize | MIT | 2026-08-27 `[V]` | Open bugs on escaping and paste mangling markdown (#918, #784) `[V]`. Reasonable if you accept normalization |
| **Lexical** (Meta) | Own node model; markdown is a transform plugin, lossy for anything outside it | MIT | 2026-08-27 `[V]` | Healthy (23.8k ★). Same architectural objection as ProseMirror |
| **Slate** | No markdown story at all; you build it | MIT | 2026-08-26 `[V]` | Long-standing "still pre-1.0" reputation; 650 open issues |
| **BlockSuite** (AFFiNE's) | Block/CRDT model; markdown is export | MPL-2.0 | **default branch last commit 2025-07-07** `[V]` (repo pushed 2026-08-26 — work is on other branches) | Coupled to AFFiNE. Not a neutral substrate |
| **Plate** (udecode) | Slate-based; has md plugins | NOASSERTION | 2026-08-24 `[V]` | Same objection as Slate |
| **Editor.js** | Block JSON, no markdown canon | Apache-2.0 | 2026-08-04 `[V]` | Not applicable |
| **Quill** | Delta format, no markdown | BSD-3 | **2025-07-25** `[V]` | Quiet for ~13 months. Not applicable |
| **Remirror** | ProseMirror wrapper | MIT | 2026-06-22 `[V]` | Slowing (3k ★). No reason to pick over Tiptap |
| **Wordgard** | Unstated — the 0.1 release post says nothing about markdown serialization `[V]` | MIT | released 2026-07-02 `[V]` | Too new to bet on (0.1, no upgrade path from ProseMirror), but **watch it** |
| **remark / mdast** | See §5 — the best serializer available, still not byte-stable | MIT | 2026-07-01 `[V]` | Use it for *analysis and normalization*, not as the editing model |
| **markdown-it** | **Parser only — there is no serializer.** `[V-E]` I introspected `markdown_it.MarkdownIt`: the only output methods are `render`, `renderInline`, `renderer` (all → HTML) | MIT | 2026-08-27 `[V]` | Pair it with your own serializer, or with CM6 where you don't need one. This is what Nextcloud Text does |

---

## 4. Category D — git-sync UX prior art

| Tool | How git is presented | Platform | License | Last activity | Verdict |
|---|---|---|---|---|---|
| **Obsidian Git** | Scheduled auto commit-and-sync; also a full Source Control view (stage/unstage/diff), History view, and per-line gutter signs | Desktop good, **mobile officially "highly unstable"** | MIT | 2026-08-17 `[V]` | The most complete git UX in a notes app — and its own README tells mobile users not to use it (§4.1) |
| **GitSync** (`ViscousPot/GitSync`) | Standalone sync app, no editor; the plugin's README recommends it over itself for mobile `[V]` | Android + iOS | GPL-3.0 | 2026-08-19 `[V]` | 2,259 ★. Recommended by obsidian-git, but see the friction section — sync is paywalled and constrained by iOS |
| **GitJournal** | **Never shows a merge conflict.** Author, on HN: *"It'll never present you with a merge conflict and will instead just make prefer the local changes… in the worst case, the wrong option is chosen, but no data is lost since the history is there in Git."* `[V]` | Mobile-first (iOS/Android) | AGPL-3.0 | **last commit 2026-05-26** `[V]` | Alive but slow (3 months quiet). **The single most useful design precedent in this whole survey** — see §4.2 |
| **Working Copy** | Full git client on iOS, exposed to other apps via the iOS Files provider | iOS | Proprietary, paid | n/a | The standard iOS answer. Integration with editors is the weak point — HN: *"I've tried… connecting 1Writer (editor) to Working Copy (git client). Although both apps are very slick, **the integration is not**."* `[V]` |
| **GitHub Desktop** | Explicit git verbs, softened | Desktop | MIT | 2026-08-20 `[V]` | Still exposes branch/commit/push as concepts. Not a model for non-technical users |
| **Gitea / Forgejo** | Web markdown editor, commit form on save | Web | MIT / GPL-3.0 | Gitea 2026-08-28 `[V]`; Forgejo updated 2026-08-28 (5,393 ★ on Codeberg) `[V]` | Commit message is a required field — that alone loses non-technical users |
| **Prose.io** | Minimal GitHub markdown editor | Web | BSD-3 | **last commit 2024-02-21** `[V]` | **DEAD** — 2.5 years quiet, 196 open issues |
| **Decap CMS** | Git-backed CMS; "editorial workflow" maps drafts to PRs; git-gateway hides auth | Web | MIT | 2026-08-21 `[V]` | Still committing (incl. non-bot work: image transformations 2026-08-21, git-gateway PKCE fix 2026-08-13) `[V]`. But 591 open issues |
| **Sveltia CMS** | Same model, modern rewrite | Web | MIT | 2026-08-28 `[V]` | README claims **320 Decap issues solved (740 incl. duplicates)** and migrations from US government agencies `[V]`. **The healthier of the two** |
| **TinaCMS** | Visual editing, commits to git behind the scenes | Web | Apache-2.0 | 2026-08-28 `[V]` | Alive, planning v4. Site: *"Tina stores everything as Markdown in your Git repo, so your content stays clean, portable, and **AI-friendly**"* `[V]` — the exact pitch, aimed at websites rather than a workspace |
| **Publii** | Desktop static-site editor; git is not the model | Desktop | GPL-3.0 | 2026-08-01 `[V]` | Not git-centric |
| **Obsidian Sync** | Not git. Paid, E2EE, per-device settings, built-in version history; a **headless client** landed ~2026-02 (HN 47197267, 587 pts) `[V]` | All, incl. iOS | Proprietary | 2026 | The commercial answer to why git isn't enough — see §4.1 |

### 4.1 The iOS wall — the hardest constraint found

This is structural, not a bug anyone can fix.

`obsidian-git`'s own README, verbatim `[V]`:

> **Mobile Support (⚠️ Experimental)** — The Git implementation on mobile is **very unstable**!
> I would not recommend using this plugin on mobile, but try other syncing services.
>
> It is not possible for an Obsidian plugin to use a native Git installation on Android or iOS.
>
> ❌ **Mobile Feature Limitations**: No SSH authentication; limited repo size, because of memory
> restrictions; no rebase merge strategy; no submodules.
>
> ⚠️ Depending on your device and available free RAM, Obsidian may **crash on clone/pull**,
> create buffer overflow errors, or **run indefinitely**. It's caused by the underlying git
> implementation on mobile… **I don't know how to fix this.** If that's the case for you, I
> have to admit this plugin won't work for you. So commenting on any issue or creating a new
> one won't help. I am sorry.

The cause is `isomorphic-git` — pure JS git, because native git is unavailable in the sandbox.

The OS-level version, from HN item 47197267 (2026-02-28), user `TheDong` `[V]`:

> iOS makes it painful to use third-party sync protocols and servers, like syncthing can't run
> in the background, a git sync service can't run in the background, only iCloud gets to run in
> the background… As such, on iOS the native sync is the only one that works cleanly and
> seamlessly, and so **you're incentivized to pay for it**.

And on the workaround (GitSync), same thread `[V]`:

> Which gates "sync" behind an expensive "premium" paywall. It feels criminal to charge that
> much for the sync feature when it also can't possibly work, iOS actively does not want apps
> to run in the background…

**Implication:** a git-backed workspace cannot promise Dropbox-grade background sync on iOS.
Sync must be foreground/on-open, or you need a server-side component that holds the repo and
speaks a cheap HTTP protocol to the phone — which is what Obsidian Sync is, and what people
pay for. From the same thread `[V]`: *"I used to use SyncThing, then Dropbox, then iCloud. But
then I just caved and paid for Obsidian Sync and it is the best money spent."*

### 4.2 Conflicts: what tools actually do

Nobody shows a non-technical user a conflict. The two shipped strategies:

- **GitJournal: auto-resolve, never surface.** Prefer local, rely on history for recovery `[V]`.
  This is the right default, and the author is explicit that it can pick wrong.
- **Obsidian Git: surface everything.** Full source-control view, diffs, gutter signs — which
  is why it's beloved by developers and useless to everyone else.

The structural complaint, HN 31914003, user `remram` `[V]`:

> The Git model is to version everything together. This means that **a conflict blocks the
> entire repo until it's fixed**. In many situations, it's better to version separate
> pages/items/notes separately, and have a conflict to a single note leave the rest of your
> repo working and syncing.

This is a genuine design constraint. A repo-wide conflict state is the wrong granularity for a
document workspace, where one bad file should not stop the other 500 from syncing.

### 4.3 Why app authors don't ship git sync

GitJournal's author, `vhanda`, HN 31914003 `[V]` — the most useful list in the thread:

> 1. Decent desktop apps to sync the data, not everyone is comfortable hacking a Cron script…
> 2. For mobile apps, a way to drastically reduce the overhead. **Cross compiling libgit2 +
>    deps + NDK is a major pain**…
> 3. **There is no competing with a simple http call vs the complexity of git.** Plus the
>    entire onboarding process.
> 4. Many many apps do write to Dropbox or Google Drive, but for me that's not a win as you
>    aren't in control of your data.
> 5. …more than 80% [of GitJournal users] use GitHub.

He also confirmed a costly implementation detour `[V]`: *"deciding to write git myself instead
of fixing the problems with all cross-compilation was a terrible idea. I've now reverted back
to libgit2."*

Another user, `nindalf`, on why editor vendors avoid it `[V]`:

> Editor apps are also reluctant to provide git integration for the reasons you listed, **plus
> it will reduce future revenue from a hosted solution they could offer**.

### 4.4 Binary assets and repo bloat

A real, unsolved problem for a docs product where users paste screenshots.

- **Git LFS is effectively unavailable on mobile.** GitJournal's author `[V]`: *"GitJournal
  doesn't yet support LFS, and since neither libgit2 or go-git supports it, it's unlikely that
  I'll implement it."* (A rebuttal in-thread from a former forestry.io CTO notes libgit2's
  filter API *can* do it `[V]`, but nobody has shipped it here.)
- Users ask for exactly this: *"The next biggest wish I have is for inclusion and management of
  binary files. Photos, videos, etc. **It'd be nice for them to not be in the git repo**, but
  to still be distributed, addressable…"* `[V]`
- Partial clone was floated as the LFS replacement; still not a solved mobile story `[V]`.

### 4.5 The other frictions, briefly

- **Git isn't a sync tool for interrupted work.** `[V]` *"I use Google Keep… start editing on
  one, finish on the other, no 'commit/push/fetch/rebase/merge' cycle required… I don't see how
  git sync helps this issue."*
- **Plain hostility to the model.** `[V]` *"I personally wouldn't put 'easy' and 'git' in one
  sentence. To sync it's too much typing requires and possible conflicts need to be resolved."*
- **But git wins on auditability.** `[V]` *"I used to store my DayOne journal in git, and boy,
  their cloud sync conflict resolution was sometimes quite destructive. **Having the git history
  showed me that, and allowed me to correct it.**"* This is the strongest argument *for* the
  thesis in the entire corpus.
- **The generalisable ask** `[V]`: *"I'd rather love to see 'select folder for storage' become a
  standard app feature… Integration of $APP_FEATURES and $SYNC_BACKENDS in apps is a major
  waste of developer resources."*

---

## 5. The lossless-markdown problem

### 5.1 Why it's hard: CommonMark is many-to-one

Multiple source spellings produce the same AST, so a serializer must *choose*, and its choice
usually differs from what the author wrote. The concrete lossy points:

| Construct | Ambiguity |
|---|---|
| Emphasis | `*em*` vs `_em_`; `**strong**` vs `__strong__` |
| Headings | ATX (`# H`) vs setext (`H` + `===`); optional closing `#` |
| Bullets | `-` vs `*` vs `+`; item indent 1 vs 2 vs 4 spaces; tight vs loose |
| Ordered lists | `1.` vs `1)`; sequential vs all-`1.` numbering; start offset |
| Hard breaks | two trailing spaces vs trailing `\` |
| Code blocks | 4-space indented vs fenced; ` ``` ` vs `~~~`; fence length; info-string spacing |
| Links | inline vs reference (`[x][ref]`); autolink `<url>` vs `[url](url)`; title quoting |
| Tables | delimiter-row width, cell padding, alignment colon placement |
| Escapes | which `*`, `_`, `[`, `` ` `` need backslashes — and serializers routinely add *unneeded* ones |
| Thematic break | `---` vs `***` vs `___`, and length |
| Frontmatter | not CommonMark at all; some tools drop it |
| Line wrapping | hard-wrapped at 80 vs one-line-per-paragraph vs semantic line breaks |
| Raw HTML | block vs inline classification, and whether it survives at all |

`mdast-util-to-markdown`'s own README concedes the point `[V]`:

> `mdast-util-to-markdown` will do its best to serialize markdown to match the syntax tree, but
> there are several cases where that is impossible.

### 5.2 Empirical results — I ran these

**Test file:** 53 lines, 714 bytes, exercising every row of the table above.

**pandoc 3.1.11.1, `-f gfm -t gfm`** `[V-E]`:

```
original 714 bytes -> pass1 740 bytes -> pass2 740 bytes
idempotent after pass 1: YES
changed lines: 42 of 53
```

What it did, all in one pass:

- **silently deleted the entire YAML frontmatter block** (data loss)
- setext heading → ATX
- `_em_` → `*em*`, `__strong__` → `**strong**`
- **injected `<!-- -->` HTML comments** between adjacent lists to keep them separate
- `1. one` → `1.  one` (two spaces)
- trailing-backslash hard break → two-space hard break
- unwrapped a two-line blockquote into one line
- padded every table cell
- ` ```python ` → ` ``` python `
- inlined the reference link and deleted the `[ref]:` definition
- `***` → a 72-character row of dashes

**Verdict: pandoc is unusable as a markdown storage layer.** It is a *converter*.

**remark (remark-parse + remark-gfm + remark-frontmatter + remark-stringify), defaults** `[V-E]`:

```
original 714 bytes -> pass1 718 bytes -> pass2 718 bytes
byte-stable (orig == pass1): false
idempotent (pass1 == pass2): true
```

Much better — it kept the frontmatter, the bullet characters, the blockquote line breaks, the
reference link, and the `***` rule. Remaining changes:

- setext → ATX
- `_em_` → `*em*`, `__strong__` → `**strong**`
- two-space hard break → `\`
- table cells padded
- **indented code block → fenced code block**
- `underscore_in_word` → `underscore\_in\_word` — **over-escaping**, matching open issue
  `syntax-tree/mdast-util-to-markdown#72` (*"do not escape underscore inside of words"*,
  opened 2026-01-09, still open) `[V]`

**Can options fix it?** No `[V-E]`. With `{bullet:'*', emphasis:'_', strong:'_', setext:true,
fences:false, rule:'*', listItemIndent:'one'}` the file was *still* not byte-stable — the
rewrites just moved: now `# Heading one` became setext, and `*emphasis*` became `_emphasis_`.
**There is no option set that preserves an arbitrary author's mixed style, because the
serializer emits one style and real documents contain several.**

**mdast carries source positions** `[V-E]` — every node has
`{start:{line,column,offset}, end:{...}}`, e.g. `{"start":{"line":8,"column":1,"offset":68},
"end":{"line":9,"column":15,"offset":97}}`. So surgical, offset-based editing of the original
text *is* mechanically possible. Nobody in the survey does it for a full editor.

### 5.3 The strategy that does work: normalize-first

If the file is already a fixed point of the serializer, everything downstream is clean.
Measured `[V-E]`:

```
normalize-first: stable over 5 further round-trip cycles?  true
after a one-word edit on the canonical form, changed lines: 1 of 55
```

**One word changed, one line changed.** That is a perfect git diff. The entire cost of the
approach is a single "normalize" commit the first time a foreign file enters the workspace.

This is what `mdformat` productizes. Its docs state it **guarantees both idempotent formatting
and HTML preservation** — *"Once converted to HTML and rendered on screen, formatted Markdown
should yield a result that is visually identical to the unformatted document"* — and its CLI
carries *"a safety check that will error and refuse to apply changes to a file if Markdown AST
is not equal before and after formatting"* `[V]` (the `--no-validate` flag confirms this check
is on by default `[V]`). Its stated style choices are explicitly diff-minimizing: ATX headings
only, fenced code only, backslash hard breaks, non-consecutive ordered-list numbering
"to minimize diffs", reference links consolidated and sorted `[V]`. Design philosophy, quoted:
*"minimizes diffs (for ease of reviewing changes), sometimes at the cost of some readability."*

Caveat: `hukkin/mdformat` is Python, 814 ★, **last commit 2025-10-19** (repo pushed 2026-08-17)
`[V]` — a maintained-but-slow dependency, and the wrong language for a JS editor.

### 5.4 Prettier is *not* a safe normalizer

Prettier's markdown formatter has multiple **open** non-idempotency bugs as of today `[V]`:

| Issue | Opened | State | Title |
|---|---|---|---|
| #18990 | 2026-03-31 | **open** | Fix non-idempotent formatting of wrapped inline code in markdown list items |
| #17353 | 2025-04-14 | **open** | Markdown mid-word underscores are interpreted inconsistently and non-idempotently |
| #17104 | 2025-02-12 | **open** | Markdown: empty sub bullet point is formatted non-idempotently, **changing semantics** |
| #18067 | 2025-10-13 | **open** | HTML comment in markdown, descendant of a task list item, is not idempotent |
| #19644 | 2026-07-16 | closed | non-idempotent indent drift (**+4 spaces per run**) under a task-list item (regression in 3.9.0) |

"Changing semantics" and "+4 indent drift per run" are exactly the failure modes that would
corrupt a user's document across repeated saves. **Do not put prettier in the save path.**

### 5.5 The real answer: don't serialize

The tools with perfect markdown fidelity all share one property — **the raw markdown text is the
editor's document model**, and formatting is a *view-layer decoration* over it.

- **Obsidian**: CodeMirror 6 powers both Live Preview and Source mode; Live Preview is
  DOM-identical to Source mode except that inactive markdown tokens are replaced with a
  zero-width space `[R]`.
- **SilverBullet**: `@codemirror/lang-markdown` + `@lezer/markdown`, no serializer `[V]`.
- **Atomic Editor**: *"Every decoration is view-only, so copy, save, and round-trip through any
  other markdown tool are byte-for-byte identical to a plain textarea."* `[V]`

The trade-off is honest and worth stating: this model makes true block-level WYSIWYG (drag
handles, nested block containers, arbitrary embeds) much harder, because there are no blocks —
only text and decorations. Atomic Editor pulls off inline-editable tables; it took work, and
the HN thread shows the seams (*"the abstraction leaks in tables"*, *"if you try to delete the
opening fence, the closing fence turns into a closing fence"*) `[V]`.

Notably, Atomic's author chose CM6 *after* trying the other family `[V]`:

> I originally went with Milkdown (Prosemirror-based)… ProseMirror doesn't provide
> virtualization out of the box… long documents were causing delays on initial page load and
> some lag during edits. I didn't find anything like it with native virtualization that felt
> right to me so I built Atomic Editor.

And a second developer in the same thread, independently `[V]`: *"I actually went through a
similar path of trying milkdown/tiptap/a few others as the core for my own editor needs but
kept running into issues where the abstractions got in the way eventually."*

---

## 6. Recommendation

**Substrate: CodeMirror 6 + a live-preview decoration layer, with `kenforthewin/atomic-editor`
(MIT) as the reference implementation or fork base.**

Reasons, in order of weight:

1. **It is the only architecture that makes the git premise work.** Byte-stability is not a
   feature you add to a serializer; it's a property you get free when the buffer is the file.
   Every ProseMirror/Lexical-family editor reserializes on save, which means opening a file
   rewrites it, which means every commit is whole-file noise.
2. **It is the proven one.** Obsidian and SilverBullet, the two healthiest plain-file markdown
   apps alive, both do exactly this.
3. **The license is right** (MIT), and CM6 has native virtualization — which matters for
   long documents and, per Atomic's author, is what ProseMirror lacks.
4. **The competition is walking away from files.** Logseq DB, Outline, Docmost, La Suite Docs,
   BlockNote all now treat markdown as lossy export. That leaves the files-on-disk position
   open.

**Secondary decisions this implies:**

- Use **remark/mdast for analysis and normalization only** — never in the save path. Run a
  one-time `mdformat`-style normalize when a foreign file first enters a workspace, then never
  reserialize again. My measurement: after normalization, a one-word edit is a one-line diff.
- Use **markdown-it or `@lezer/markdown` for parsing**; markdown-it has no serializer, which is
  a feature here, and it is what Nextcloud Text uses.
- **Do not** adopt BlockNote or plain Tiptap for the docs surface. Tiptap is healthy and MIT
  (the licensing worry is unfounded — they went *more* open in 2025), but its storage model is
  ProseMirror JSON, not markdown.
- **Watch Wordgard** (MIT, 2026-07-02) but don't build on 0.1 with no upgrade path.
- Plan for CM6/ProseMirror dependencies now living at `code.haverbeke.berlin`, not GitHub.
- **Study Nextcloud Text before writing a line.** It is the only project that has actually
  tried collaborative WYSIWYG over real markdown files, and its issue tracker is a map of every
  mine in the field (§7).
- On git UX: copy **GitJournal's** conflict philosophy (auto-resolve, prefer local, never show
  a conflict, trust history for recovery), not Obsidian Git's (expose everything).
- On mobile: do not promise background sync on iOS. Sync on foreground/open, or run a
  server-side repo holder.

---

## 7. Case study: Nextcloud Text, or, what happens when you try this

Worth its own section because it is the closest anyone has come, and the failure modes are
documented publicly over six years.

- **Issue #593, "Markdown files from external editors lose formatting on save"** (closed
  2020-01-19) `[V]` — the canonical statement of the problem:

  > Markdown files that are created in external markdown and text apps will have their
  > formatting **completely overridden and/or lost** when edited through the Nextcloud web
  > interface. Newlines, tabs, and spaces are thrown out everywhere in the document — **not
  > just on the edited line** — and lists will be changed to asterisks instead of dashes.
  > […] When I edit these files through my Nextcloud web interface, **the formatting of the
  > entire file is destroyed.**

  "Not just on the edited line" is precisely the thing that makes a git-backed product
  unusable.

- **Issue #3327, "Overview of markdown related issue reports"** (opened 2022-10-28, **still
  open**) `[V]` — a meta-tracker linking ~25 separate markdown-preservation issues and 6 prior
  PRs. Six years of engineering against one problem.

- **They built a defence: `src/markdownit/keepSyntax.js`** `[V]` — a markdown-it core rule that
  tags `` ` ``, `*`, `\`, `~`, `[`, `]` and line-start `#-*+>` characters with a `keep-md`
  span so the serializer won't escape them. A hand-maintained regex patch over the
  round-trip problem. That is what the "just use a good serializer" path actually costs.

- **It still loses data today.** Issue **#9108**, opened **2026-08-26**, open `[V]`:

  > Text does not render Markdown images whose source is a `data:` URI, and — more seriously —
  > once such a document is opened and edited, **the images are removed from the stored file**…
  > **A one-word text edit is enough to destroy every picture in the document.**

- **They are now building semantic markdown diffing.** Issue/PR **#9047, "Derive semantic
  Markdown changes"** (2026-08-14) `[V]`, first of a six-PR stack:

  > nothing could tell you what actually changed between two Markdown revisions. **A byte diff
  > says edits happened. It does not say that a paragraph was inserted, a link target changed,
  > or a table row moved.** […] A comparison model built on ProseMirror ChangeSet.

  This is a direct admission that once you reserialize, byte diffs become meaningless and you
  must rebuild semantic diffing on top. **If the buffer is the file, you never incur this cost
  — git's own diff stays meaningful.**

---

## 8. The gap

Everything below is *simultaneously* true today, and no shipped product sits at the
intersection:

- Real WYSIWYG (or Obsidian-grade live preview) over markdown — **solved** (Obsidian, Typora,
  MarkText, Atomic Editor), but only Atomic Editor is MIT and reusable.
- Plain `.md` files on disk — **solved**, and *shrinking*: Logseq abandoned it in 2026, Reor is
  archived, Dendron is dead, Foam is thin.
- Collaborative editing over real markdown files — **attempted exactly once** (Nextcloud Text),
  still fighting data-loss bugs after six years.
- Git as the storage layer with a UX a non-technical person survives — **nobody**. GitJournal
  came closest and is 3 months quiet on mobile; Obsidian Git is explicit that mobile does not
  work; Wiki.js treats git as a one-way mirror of a database.
- Byte-stable markdown — **only** via the "don't serialize" architecture, which nobody has
  combined with collaboration or with a sheets/slides layer.

**The single biggest unsolved thing:** *collaborative editing whose durable artifact is a
byte-stable markdown file.* Every collaborative editor in existence has chosen a CRDT/JSON
document as truth and markdown as export — because Yjs/ProseMirror state and a text file are
different data models, and reconciling them means reserializing, which destroys byte stability,
which destroys the git diff, which destroys the whole premise. Nextcloud Text is the only
project that has attacked this head-on, and PR #9047 (2026-08-14) shows them building semantic
diffing precisely because they lost the ability to trust byte diffs.

A CM6-buffer-is-the-file architecture sidesteps it for single-player and for
one-writer-at-a-time. Making it work for *simultaneous* editors — CRDT over the markdown text
itself, rather than over an abstract document — is the genuinely novel engineering, and the
real moat.

---

## 9. Corrections to note

- **Tiptap did not move to a paid cloud model.** Core is MIT (`LICENSE.md`, Tiptap GmbH) `[V]`
  and shipped v3.30.5 on 2026-08-28 `[V]`. In 2025 they open-sourced ~10 formerly-Pro
  extensions under MIT (HN 44202103, 2025-06-06) `[V]`. Paid tier is hosted
  collaboration/comments/AI infrastructure.
- **ProseMirror and CodeMirror are not abandoned**, despite every GitHub repo showing
  "archived". They relocated to `code.haverbeke.berlin` on 2026-04-01 and 2026-04-15 `[V]`.
  Do not read the archive flag as death — but do account for the forge move.
- **`zadam/trilium` no longer exists as an independent repo** — the API redirects to
  `TriliumNext/Trilium` `[V]`.
- **`ether/etherpad-lite` now resolves as `ether/etherpad`** `[V]`.
- **AppFlowy's 76k ★ overstates its public velocity** — default-branch last commit is
  2026-06-26 `[V]`; the work is elsewhere.
- **Unverified:** I could not fetch `code.haverbeke.berlin` directly — it returns a JS cookie
  challenge to curl `[V]`. Its existence and contents are confirmed via the moved-repo READMEs
  (primary) and search results (secondary).
- I did not independently verify Joplin's, Anytype's, Trilium's, or Notesnook's internal schema
  by reading their migrations; those rows rest on README/doc statements and are marked
  accordingly.

## 10. Sources

Repo facts: GitHub REST API, 2026-08-28. Selected primary sources:

- Logseq split: https://logseq.io/p/e3YDyX5AYr · https://github.com/logseq/docs/blob/master/db-version-changes.md · https://github.com/logseq/og
- Wordgard: https://marijnhaverbeke.nl/blog/wordgard-0.1.html · https://wordgard.net/ · HN https://news.ycombinator.com/item?id=48772573
- Outline storage: https://github.com/outline/outline/blob/main/server/models/Document.ts
- Docmost schema: `apps/server/src/database/migrations/20240324T086300-pages.ts`
- BlockNote lossiness: https://www.blocknotejs.org/docs/converting-blocks
- Nextcloud Text: issues #593, #3327, #9047, #9108; `src/markdownit/keepSyntax.js`
- mdformat style guide: https://mdformat.readthedocs.io/en/stable/users/style.html
- Prettier md idempotency: prettier/prettier #18990, #17353, #17104, #18067, #19644
- mdast round-trip: syntax-tree/mdast-util-to-markdown #72, #75
- Milkdown: Milkdown/milkdown #2396, #2428
- obsidian-git mobile: https://github.com/Vinzent03/obsidian-git README
- Atomic Editor: https://github.com/kenforthewin/atomic-editor · HN https://news.ycombinator.com/item?id=48345201
- Git friction: HN https://news.ycombinator.com/item?id=31914003 (GitJournal, 305 pts) · https://news.ycombinator.com/item?id=47197267 (Obsidian Sync headless, 587 pts) · https://news.ycombinator.com/item?id=45157505 (Semantic Line Breaks)
- Sveltia CMS: https://github.com/sveltia/sveltia-cms · TinaCMS: https://tina.io/

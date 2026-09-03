# Git-backed office suite: landscape, architecture, and the honest case

Research date 2026-08-28. Supersedes the first-pass version of this file, which
contained three material errors — corrected and flagged below.

Detailed evidence lives in `findings/00` through `findings/11`. This file is the
synthesis. Every number here was verified by fetch, API, source read, or binary
teardown; claims that could not be verified are marked.

---

## The question

Does a git-backed Google Workspace already exist — Docs as markdown, Sheets as
CSV, Slides as `---`-separated markdown, with a git repo as the drive?

**Answer: yes, several times over, in pieces — and one project (Nimbalyst) now
ships all three legs.** The idea is not imaginary and it is not unclaimed. What
remains open is narrower and more interesting than "nobody built it".

---

## Corrections to my first report

1. **"Pithy doesn't exist" — wrong.** It exists at `pithy.md`. I searched
   `pithy.app` and `getpithy` and never tried the `.md` TLD, and the site is
   password-gated so search engines don't index it. The prior chat was right.
2. **"HyperFormula is MIT" — wrong, and materially so.** npm reports
   `GPL-3.0-only`. Dual-licensed with an unpublished commercial price. Building a
   closed product on it would have been a licensing trap. Handsontable is worse:
   non-free since 2019 with a non-compete clause that explicitly bars this product
   category. Use **IronCalc** instead (Apache-2.0, 4,125★, 495 functions —
   more than HyperFormula, plus spill ranges and LAMBDA).
3. **"Sheets is unsolved; nobody ships formulas in plaintext" — wrong.** Three
   shipped designs exist (§3). The real gap is narrower.

---

## 1. Who actually exists

| Product | Docs | Sheets | Slides | Git | Licence | Status |
|---|---|---|---|---|---|---|
| **Nimbalyst** | `.md` | `.csv` + `.calc.md`, real formulas | `.slides.md` (reveal) | real, `simple-git` | MIT | 1,595★, commits daily. Ex-Crystal (3,113★) |
| **Pithy** | `.md`/`.mdx` | `.csv`, no formulas, 1,000-row cap | none | real | claimed AGPL *and* MIT | **frozen since 2026-03-28** |
| **Kova** | — | `!sheet` md tables | `---` md, PPTX/PDF/HTML | none | GPL-3.0 | 283★, active, $0 raised |
| **Perchpad** | `.md` | `.csv` | none | repos on their Fly.io boxes | closed | Show HN Feb 2026, 2 points |
| **Moment** | `.md` | — | — | pushes to `git.moment.dev` | closed | HN 29 points |
| **Eigen** | Tiptap+Yjs | in-tree engine | pixel canvas | **none** | — | pre-1.0 |
| **CollabMD** | `.md` | — | — | real, browser commits | MIT | 268★, pushed today |

**"Git-backed" is usually a half-truth, and that is the wedge.** Moment's own docs
concede that on sharing *"the central server becomes the source of truth"*.
Perchpad hosts repos itself with GitHub sync still "Coming Soon". Eigen has no git
at all. Moment's top HN critic asked the right question: *"what does this provide
my team that git does not?"*

### Pithy, from the binary (findings/00)

I downloaded the AppImage, extracted the squashfs, and decompiled the Node
sidecar. Author **Tyler Tate**; bundle id `md.pithy`; CI path
`/home/runner/work/pithy-desktop/pithy-desktop`; two private repos
(`pithy-desktop`, `pithy-app`), so the 404 means private, not fictional.

Tauri v2 → Node sidecar (Express, better-sqlite3 WAL, SQLite FTS5, `simple-git`
shelling to real git, Yjs) → React + Tiptap frontend. Documents are genuinely
files; SQLite holds only users/orgs/comments/search.

Verified absent by grep, not inference: **no formula engine** (only PapaParse's
`escapeFormulae`), **no slides**, **no MCP server** (every "mcp" hit is a
`vnd.3gpp.mcptt-*` MIME type). Shipped UI string:
`"Cannot add rows — file exceeds 1,000 row limit"`.

**Its save path is `file.md → marked → HTML → Tiptap → getHTML() → turndown →
file.md`, with no reconciler.** Turndown is configured `bulletListMarker:"*"`,
`emDelimiter:"_"`, `codeBlockStyle:"indented"`. So editing one character in an
imported file rewrites the whole file into turndown's dialect. In a product whose
pitch is "every save is a commit", first touch produces a whole-file diff. This is
the central technical lesson of the whole exercise (§2).

Worth stealing: their git vocabulary. Push is **"Publish changes"**, commit is
**"Commit this change to version history?"**, branches sit under **"Branches &
version history"**. It leaks, though — `"Complete or abort the rebase in a
terminal."` is a shipped string.

---

## 2. The editor architecture — settled, with evidence

Two agents reached opposite conclusions and I made them resolve it. The
resolution reversed the stronger-sounding position.

**The losing position:** markdown cannot be the CRDT — Peritext (Ink & Switch,
CSCW 2022) shows Alice bolding "The fox" and Bob bolding "fox jumped" merges to
`**The **fox** jumped.**`, rendering "fox" *not bold*. Therefore keep a rich-text
CRDT and project markdown out.

**What settled it:** CollabMD — the one shipping product doing realtime
multiplayer over plain markdown in a git repo — was cited as corroboration. Its
`package.json` says otherwise, and I verified it:

    "@codemirror/lang-markdown", "@codemirror/state", "@codemirror/view",
    "y-codemirror.next": "^0.3.6",  "yjs": "^13.6.32",  "y-websocket",
    "markdown-it": "^15.0.0"        <- parser only, no serializer

No ProseMirror. No Tiptap. No turndown.

**The argument is a severity asymmetry, not a refutation of Peritext.** The
Peritext anomaly needs concurrent *overlapping mark* operations, is rare, spans a
few characters, is **visible** in a source editor, and is user-fixable.
Reserialization hits **every imported file on first touch**, whole-file,
**silently**, and destroys the diff — the product's premise. Pithy is one shipping
counterexample. **Nextcloud Text is a worse one**: Yjs + ProseMirror over real
markdown files for six years, a hand-maintained `keepSyntax.js` regex patch, a
data-loss bug filed 2026-08-26, and now building *semantic* diffing because byte
diffs stopped meaning anything.

The escape hatch is closed: `mdast-util-to-markdown`'s own README says its
positional `Tracker` *"isn't used yet"*. Nobody has built minimal-edit
serialization despite Nextcloud having six years and every incentive.

**Decision: CodeMirror 6 + a live-preview decoration layer, plain-text CRDT
(`y-codemirror.next`) over the markdown source.** Byte-stability isn't something
you achieve by picking a better serializer — it's free when the editor buffer *is*
the file. Obsidian Live Preview and SilverBullet both do exactly this.

**Tradeoffs accepted, explicitly:** no true block-level WYSIWYG (text +
decorations only; tables are the known sore spot); mark operations should be
single atomic CRDT transactions; Sheets and Slides become genuinely different
editors rather than the same one. Pin `y-codemirror.next ^0.3.6` against
`yjs ^13.6.32` — its `main` targets unstable yjs v14.

Empirical backing (findings/03): on a 53-line torture file, **pandoc changed 42 of
53 lines and silently deleted the YAML frontmatter**; no remark option set is
byte-stable. But normalize-once-then-edit held stable over 5 cycles, with a
one-word edit producing **1 changed line of 55**. Prettier is unsafe in the save
path — open bugs for non-idempotency and indent drift.

**Substrate risk:** ProseMirror and CodeMirror archived every GitHub repo
(2026-04-01 / 2026-04-15) and moved to `code.haverbeke.berlin`. Verified. Not
death, but plan for it.

---

## 3. Sheets — the actual state of the art

Three shipped plaintext-formula designs, none of them CSV-with-a-sidecar:

| Design | Shape | Addressing | Diff | Interop |
|---|---|---|---|---|
| Nimbalyst `csv-spreadsheet` | real `.csv`, formula text in cells | **A1** | metadata is one minified JSON line | breaks — see below |
| Nimbalyst `calc-sheets` | `.calc.md`, line-oriented | **named variables + units** | excellent | none (bespoke) |
| Kova `!sheet` | GFM markdown table | **named columns, relative** | excellent | it's just a markdown table |

Nimbalyst persists CSV metadata as `# nimbalyst: {...}` on line 1. Most CSV
consumers don't skip `#`, and the agent found it worse than that: **the commas
inside that JSON widen the whole sheet to three columns.**

`.calc.md` is the most elegant: named variables, unit-aware arithmetic with
dimensional checking (`g0 = 9.80665 m / s^2`), `->` formatters, `assert`
statements, results in a gutter and never written to the file. Their demo is a
Falcon 9 rocket equation.

### The finding that matters

**A1 references don't merely diff badly — they merge into silently wrong
numbers.** The agent constructed two branches each inserting a row far enough
apart that **git auto-merged with zero conflicts**, and the resulting sheet
totalled **480 instead of 660**, a 27% error with no marker anywhere.
LibreOffice computed it. Named columns: one added line, clean merge, correct.

This is backed by the literature. Chambers, Erwig & Luckey (SheetDiff, VL/HCC
2010) concede that inferring structural change from positional cells *"is
generally ambiguous and not straightforward… does this signify that a row has been
added or simply that many of the cells have been changed?"* Under named
addressing the question never arises. Abiteboul, Hull & Vianu give the formal
statement: named and unnamed perspectives have **equal expressive power but
different primitive operators** — positional addressing doesn't cost
expressiveness, it costs cheap correspondence, which is what merging *is*.

### Named columns are the mainstream, not a bet

Excel Tables already do this (`=[@Qty]*[@Unit]`, `=SUM(Table1[Total])`) — added
*on top of* A1 precisely because A1 breaks on row insert. **None of Airtable,
Notion, Coda, Baserow, NocoDB, Teable or Grist has any positional reference at
all.** Coda says it outright: *"In Coda, all objects have names. No coordinates
needed!"* Lotus Improv did it in 1991.

Two sharp details:
- **Google Sheets shipped Tables in May 2024 with structured references but
  explicitly declined per-row ones.** Verified on Google's own page: *"Tip:
  #This Row currently is not supported."* The per-row named reference is the piece
  the world's second-largest spreadsheet has not shipped.
- **Store names as literal text, like Excel does.** Four of the seven no-code
  tools store an opaque field ID and project a name for display — but that
  requires a UI layer between bytes and human. In a plaintext format *the file is
  the UI*; `=col_a7f3 * col_9b21` is positional addressing with the ergonomics
  removed. Rename therefore becomes a refactoring that rewrites dependents, and
  the design imperative shifts to **diagnostics**: a reference to a missing column
  must fail loudly and locally, never as zero, empty, or a stale value.

### The honest counter-evidence

McKeever & McDaid's three EuSpRIG papers found non-experts using range names were
**slower and more error-prone**. The rebuttal (Miller & Hermans) is that a named
range is *pure indirection* — *"not much more than an alias for a reference"* —
whereas a column-header reference has **no indirection**, since the name is
printed atop the column the reader is already looking at. That rebuttal is
plausible but unreplicated. **Named addressing is defensible on merge grounds — a
version-control argument — not on usability grounds.** Do not claim otherwise.

### Recommendation

Three file types, because "spreadsheet" is three unrelated jobs:
`.sheet.md` (Kova-style named-column GFM tables) for tabular data; `.calc.md` for
models; `.fods` as the fidelity escape hatch. `.fods` gets **cell-level three-way
merge free from stock git** (CSV structurally cannot), costs +26% repo space vs
CSV where `.xlsx` costs 3.8×, and its printer-name churn is removable with a clean
filter the agent wrote and tested. CSV+sidecar and SQLite-in-git both failed
concretely.

Kova's engine is real (555 lines, proper lexer/parser/evaluator, cycle detection,
63 tests) but its library is a toy (11 functions) and it has **no row-relative
operator**, so no time-series models. Keep the syntax, swap in IronCalc.

---

## 4. Storage and collaboration — one hard constraint

**Measured, not reasoned:** with two devices auto-committing and pushing the same
repo, **12/12 pushes were rejected** for the second writer; with a `pull --rebase`
retry loop on a shared paragraph, **8/8 rebases conflicted and 0% of the second
writer's work landed.** At the index layer, 8 concurrent `git add` → 1 succeeded,
7 failed on `index.lock`.

**The architecture must guarantee a single writer per repository. Every other
decision is downstream of that one.**

Other measured results:
- **File count is a non-issue** — 100k markdown files, `git status` under 0.1s.
- **Attachments are the bloat driver** — 21 revisions of one 2 MB image cost
  **20.6× a single copy**; 21 revisions of a 1.1 MB text file cost less than one.
  Use content-defined chunking into a CAS with pointers in git.
- **`daff` (MIT) did correct cell-level three-way CSV merges on every case
  tested**, including column insert and row reorder, which plain git cannot
  survive. Cheapest large win available. `mergiraf` and `difftastic` support
  neither markdown nor CSV.
- **Mobile is where this breaks.** libgit2 and isomorphic-git implement **neither**
  partial clone nor sparse checkout (libgit2's sparse issue has been open 12
  years). obsidian-git's own README calls mobile "highly unstable… I don't know
  how to fix this." Corrected en route: `--filter=blob:none` alone gives no size
  win (22M vs 22M); the win is `--sparse`, and it fails open with a warning if the
  server lacks `uploadpack.allowFilter`.
- Keep mutable app state out of git. Gitea and Forgejo — whose product *is* git —
  use SQL for issues and wiki.

---

## 5. Slides — wrap, don't build

Wrap **Marpit + Marp Core as libraries** (MIT, four repos all pushed within three
weeks). `Marpit.render()` turns a string into HTML+CSS, which is the only
architecture that can back a live editor; Slidev is a Vite dev server and
reveal.js is a browser runtime. Marp's escape hatch is CSS, so the file still
reads as a document.

**But not Marp for PPTX.** Its own README: default `--pptx` is "pre-rendered
background images… contents cannot to modify or re-use". `--pptx-editable` is a
PDF→LibreOffice vectoriser that drops speaker notes and is still `[EXPERIMENTAL]`
19 months on. Editable PPTX comes from Pandoc `--reference-doc` or PptxGenJS.

**The WYSIWYG-slides gap is real.** The nearest thing is Slidev's `v-drag`, which
writes positions back into the `.md` but only repositions elements you already
declared, and its docs admit it's regex-based and fragile. Slides.com — by
reveal.js's own author — treats markdown as one-way import. Gamma's markdown
import is an **open feature request as of 2026-02-11**. Typora proved
WYSIWYG-over-markdown works for documents; nobody built the slides equivalent.

Two names from the original brief **do not exist**: Slidebeamer and Presentic.

---

## 6. The rest of the suite

**Cheap wins:** tasks — Backlog.md (MIT, 6,564★, pushed 2026-08-26) is the live
answer to "issues as files"; todo.txt diffs best of anything here. Diagrams —
Mermaid, D2, PlantUML, Graphviz all diff like code, and **draw.io is Apache-2.0
with `compressXml` defaulting to false**, i.e. plain XML, one `<mxCell>` per
shape. Calendar — vdir + Radicale, whose manual ships a git commit hook. Search —
ripgrep day one, SQLite FTS5 as a **gitignored** index.

**Traps:** per-file sharing forces an auth server (no forge has per-file read
ACLs — Gerrit's are ref-only, Gitea/Forgejo unit-level, CODEOWNERS is routing not
access). Form responses in git (append conflicts, immutable PII, no auth;
Staticman's last commit was 2020-07-06). **tldraw is proprietary** — verified
`NOASSERTION`. Taskwarrior is disqualified: 3.0 moved storage to
`taskchampion.sqlite3`. Calendar invitations are iTIP/iMIP protocols, not files.

`.ics` diffs badly — RFC 5545's 75-octet line folding reflows a whole property on
any length-changing edit; a one-word change produced 10 changed lines.

---

## 7. The market case, honestly

**For.** The MCP steering group maintains exactly two document-substrate reference
servers — **Filesystem and Git** — and *archived* the Google Drive one. The API
tax is quantified in public trackers: ~21,411 tokens of Notion tool schemas per
session; 410,053 tokens for a 500×20 Excel read as JSON. `microsoft/markitdown`
has 176,800 stars purely to turn Office files into markdown for LLMs. The
docs-buyer is repricing upward — Mintlify $1M→$10M ARR in a year, $500M valuation
April 2026, on "nearly 50% of traffic to documentation comes from AI agents".

**Against, and it is strong.** **OfficeCLI: 29,444 stars in five months**
(Apache-2.0, created 2026-03-15) by *keeping* .docx/.xlsx/.pptx and giving agents
a render loop. GenOffice: 3,860 stars in four weeks doing byte-preserving .docx
edits. The incumbent gap closed in 2026 — Copilot agent mode GA in Word/Excel/
PowerPoint on 2026-04-22, Claude for M365 GA 2026-05-07. There is a thirteen-year
graveyard with verbatim post-mortems: Editorially (*"even if all of our users paid
up, it wouldn't be enough"*), Penflip, Draft, EqualTo, Stashpad (*"did not reach
business viability"*), Poetica — whose whole value proposition was collaboration
*without* "arcane tools like git".

And **HN enthusiasm is declining**: Penflip 181 points (2013) → Moment.dev 29 →
Perchpad **2** (2026). Kova is the sharpest data point of all: best-in-class
engineering, 67 releases in 3.7 months, 283 stars, its own apt/rpm/AUR/Nix/Flatpak
distribution estate — and **$0.00 raised from 0 contributors on Open Collective**,
which I verified directly against their GraphQL API.

Note also that git-backing **deletes the closest analogue's revenue line**:
Obsidian's largest SKU is Sync at $48/user/yr, and git gives sync away.

**My read of the OfficeCLI counter-argument.** markitdown's 176k stars are people
converting Office files *into* markdown so agents can read them; OfficeCLI's are
people keeping OOXML as *storage*. Together they say the market has settled on
markdown as the **interchange** layer while leaving OOXML as the **storage** layer.
The bet here is specifically that markdown can be the storage layer too. That is
unproven rather than refuted — but it is the bet, and it should be named as one.

---

## 8. What is actually open

Not "can formulas live in plaintext" — three shipped answers exist. The open
questions are:

1. **Has anyone made a plaintext sheet good enough to replace a real spreadsheet?**
   No. Kova's engine has 11 functions. Nimbalyst's CSV mode breaks CSV. Pithy caps
   at 1,000 rows with no formulas.
2. **Has anyone carried all three legs for a non-developer audience?** No.
   Nimbalyst has the legs and sells to developers orchestrating coding agents.
   Kova is a deck tool that grew a formula feature. Pithy had the right audience
   and stopped shipping.
3. **Can the per-row named reference — the thing Google Sheets declined to
   ship — be made ergonomic?** Genuinely unclaimed.

The build is no longer the moat; Eigen proves one person plus agents can clone
fourteen Workspace apps in seventeen months. **Distribution is the binding
constraint**, and every project in this space has failed at it.

---

## Sources

`findings/00-pithy-teardown.md` · `01-direct-competitors.md` ·
`02-sheets-plaintext.md` · `03-docs-editors.md` · `04-slides.md` ·
`05-git-collab.md` · `06-market-agents.md` · `07-suite-surface.md` ·
`08-nimbalyst-formats.md` · `09-database-tools-formula-refs.md` ·
`10-spreadsheet-literature.md` · `11-named-column-addressing.md`

`teardown/` holds the extracted Pithy frontend bundle, server bundle and manifest.

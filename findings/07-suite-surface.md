# The remaining suite surface: everything that isn't Docs/Sheets/Slides

Research date: **2026-08-28**. All GitHub star counts / last-push dates below were pulled from
`api.github.com` on that date and are marked **VERIFIED**. Licenses were read from the actual
`LICENSE` file wherever GitHub's API reported `NOASSERTION`. Claims sourced from documentation I
fetched are **VERIFIED**; claims from search-result summaries or third-party writeups are
**REPORTED**.

Two diffability claims in here were tested empirically rather than asserted; the test scripts and
output are reproduced inline.

---

## A. Calendar

### The format story is unusually good

`.ics` (iCalendar, **RFC 5545**) is the format, and — crucially — there is already a *filesystem*
binding for it, so you don't have to invent one.

**vdir** (VERIFIED — <https://vdirsyncer.pimutils.org/en/stable/vdir.html>) specifies:

- a collection is a **folder**; a calendar is a collection
- an item is **one file**, extension **must** be `.ics` (or `.vcf` for contacts)
- "The file _must_ contain exactly one event, task or contact" — with an explicit exception that
  recurrence exceptions may add components to that same file
- metadata lives in extensionless sidecar files: `displayname`, `description`, `color`
  (`#RRGGBB`), `order`
- writes *should* be atomic; `.tmp` files and extensionless files must not be treated as items

This is, almost exactly, the layout a git-backed suite would have designed anyway.

**Calendar-in-git is not speculative — it's in the Radicale manual.** VERIFIED from
<https://radicale.org/v3.html>: the default storage is `multifilesystem` (folder per collection,
one file per event, plus a `.Radicale.props` JSON per collection), and the docs give a
copy-pasteable versioning recipe:

```
hook = git add -A && (git diff --cached --quiet || git commit -m "Changes by "%(user)s)
```

with a `.gitignore` of `.Radicale.cache`, `.Radicale.lock`, `.Radicale.tmp-*`.

So the answer to "can a folder of .ics files in git be a real calendar?" is: **yes, and people
already run it.** Point real CalDAV clients (iOS, Android, Thunderbird) at Radicale, and every save
becomes a commit.

### What actually breaks

**1. `.ics` diffs worse than it looks.** Tested empirically (script in
`scratchpad/icstest`, RFC 5545 folding at 75 octets, continuation lines start with a space).
Changing **one word** in a long `DESCRIPTION` — `session` → `sync`, three characters shorter —
reflows the entire remainder of the property:

```diff
-DESCRIPTION:Quarterly planning session covering roadmap, hiring, budget and
-  the annual retrospective for the platform team, plus follow ups, action i
- tems, and the list of owners for each workstream agreed in the previous me
- eting.
-SEQUENCE:0
+DESCRIPTION:Quarterly planning sync covering roadmap, hiring, budget and th
+ e annual retrospective for the platform team, plus follow ups, action item
+ s, and the list of owners for each workstream agreed in the previous meeti
+ ng.
+SEQUENCE:1
```

Ten changed lines for a one-word edit. Add `DTSTAMP` (rewritten on every single save) and
`SEQUENCE`, and **no `.ics` edit ever produces a clean diff**. Property ordering is also not
canonical, so a round-trip through a different client can rewrite the whole file. A pre-commit
normalizer (unfold long lines, sort properties, pin `DTSTAMP`) would fix most of this and is
maybe 100 lines — but you have to write it, and unfolded output is no longer spec-conformant on
the wire, so it has to refold on export.

**2. Recurrence leaks the one-event-per-file invariant.** `RRULE` + `EXDATE` + per-instance
`RECURRENCE-ID` overrides all live in the same file, which vdir explicitly permits. So the file
that looks like "one meeting" is actually a small database, and editing "just this occurrence"
rewrites a shared file. khal's own docs state the limitation plainly (VERIFIED,
<https://khal.readthedocs.io/en/stable/>): *"only rudimentary support for creating and editing
recursion rules"* and *"you cannot edit the timezones of events."* The best-in-class CLI client
punts on exactly the two hardest bits.

**3. Timezones.** `VTIMEZONE` blocks are inlined per file — duplicated across every event,
verbose, and capable of going stale relative to the tzdata your runtime uses.

**4. Invitations are a protocol, not a format.** Group scheduling is **iTIP (RFC 5546)** —
`REQUEST` / `REPLY` / `CANCEL` methods with an `ATTENDEE`/`PARTSTAT` state machine — bound to email
via **iMIP (RFC 6047)**, i.e. iCalendar objects as MIME parts over SMTP (VERIFIED, rfc-editor.org).
A folder of `.ics` files has **no way to receive an RSVP**. Free/busy is likewise a CalDAV
`free-busy-query` REPORT — a server operation, not a file read.

This splits "calendar" into two products with wildly different costs: *my calendar* (cheap, files,
already solved) and *scheduling a meeting with other humans* (a mail-connected server, an RFC 5546
state machine, and probably a Google/Microsoft connector).

| Component | Plaintext format | Best existing tool | License | Diffs well in git? | Build or wrap? |
|---|---|---|---|---|---|
| Calendar storage | vdir: folder of `.ics` (RFC 5545) | vdir spec / Radicale `multifilesystem` | spec: n/a | **No** — line folding + `DTSTAMP`/`SEQUENCE` churn | **Wrap**, add a normalizer |
| CalDAV server (so real clients work) | same files on disk | Radicale (4,936★, pushed 2026-08-24) | GPL-3.0 | n/a | **Wrap** |
| CalDAV server (PHP/sabre) | same | Baïkal (3,282★, pushed 2026-08-13) | GPL-3.0 | n/a | Wrap |
| Sync engine | vdir ↔ CalDAV | vdirsyncer (1,869★, pushed 2026-08-20) | BSD-3-Clause (VERIFIED from LICENSE; GitHub says NOASSERTION) | n/a | Wrap |
| CLI/TUI client | vdir | khal (3,043★, pushed 2026-08-28) | MIT | n/a | Wrap or reimplement UI |
| Recurring events | `RRULE`/`EXDATE`/`RECURRENCE-ID` | python `dateutil.rrule`, `ical.js` | varies | Poorly (shared file) | Wrap a library, never hand-roll |
| **Invitations / RSVP** | iTIP RFC 5546 over iMIP RFC 6047 | — (Radicale has no scheduling) | — | **N/A — not a file** | **Trap.** Server + mail, or omit |
| **Free/busy** | CalDAV REPORT (RFC 4791) | Radicale/Baïkal partial | — | **N/A — not a file** | Trap / omit |

**Assessment.** Calendar is the cheapest non-core win in this whole document *if* you scope it to
"see and edit my own calendar." vdir + Radicale gives you real CalDAV client support for
approximately zero engineering. The trap is that users mean *scheduling* when they say "calendar,"
and scheduling is a protocol you cannot represent as a folder.

---

## B. Tasks / project management

### The plaintext formats are settled and boring, which is good

**todo.txt** (VERIFIED — <https://github.com/todotxt/todo.txt>, the repo is a **spec**, not code,
licensed **GPL-3.0**): one task per line; `x ` prefix = done; `(A)` priority first if present;
`YYYY-MM-DD` creation/completion dates; `+project`; `@context`; arbitrary `key:value` metadata.
Its stated design goal is that *"a text editor that can sort lines alphabetically should be able to
sort your task list in a meaningful way."* It is the single best-diffing format in this entire
document: one task = one line, edits are localized, appends by two people in different regions
merge cleanly, and the only real conflict (two people completing the same task) is a one-line
conflict a human resolves instantly.

**Taskwarrior is disqualified, and this is the surprise.** VERIFIED from
<https://taskwarrior.org/news/news.20240324/> and <https://taskwarrior.org/docs/upgrade-3/>:
**Taskwarrior 3.0 (2024-03-24) replaced the flat `.data` files with `taskchampion.sqlite3`.**
The repo is very much alive (MIT, 6,021★, pushed 2026-08-28) but it is no longer a plaintext store
and no longer a candidate. Anyone citing "Taskwarrior's data format" as a plaintext exemplar is
citing 2.x.

### "Issues as files" — the 2026 survey

All activity below **VERIFIED** via `api.github.com` on 2026-08-28.

| Project | Storage | License | Stars | Last push | Alive? |
|---|---|---|---|---|---|
| **Backlog.md** (MrLesk) | **`.md` files with YAML frontmatter** | MIT | 6,564 | **2026-08-26** | **Yes — the answer** |
| git-bug | JSON op-packs in **git objects** under `refs/<ns>/<id>` — *not files* | GPL-3.0 | 10,017 | 2026-07-06 | Yes |
| git-issue (dspinellis) | files under `.issues/`, shell script | GPL-3.0 | 883 | 2025-10-17 | Semi |
| tissue (Arun Isaac) | gemtext files in the repo + Xapian index, GNU Guile | — | n/a (self-hosted) | REPORTED active | Probably — see note |
| sit | JSON records in the repo | Apache-2.0 | 556 | **2018-12-20** | **Dead** |
| ticgit (jeffWelling) | git refs | GPL (LICENSE_GPL) | 267 | **2014-02-09** | **Dead** |
| Fossil tickets | ticket-change **artifacts** in the Fossil repo | BSD-2-Clause | n/a | active | Yes, wrong VCS |
| Vikunja | database | AGPL-3.0 | 5,192 | 2026-08-28 | Yes, not plaintext |
| Plane | database | AGPL-3.0 | 58,457 | 2026-08-28 | Yes, not plaintext |
| Linear | closed SaaS | — | — | — | Not plaintext |

**Backlog.md is the answer to "is there a good issues-as-files project alive in 2026?"** — yes,
and it's this one. VERIFIED by reading a real task file out of its own repo
(`backlog/tasks/back-200 - Add-Claude-Code-integration-with-workflow-commands-during-init.md`):

```yaml
---
id: BACK-200
title: Add Claude Code integration with workflow commands during init
status: To Do
assignee: []
created_date: '2025-07-23'
updated_date: '2025-09-06 21:22'
labels: [enhancement, developer-experience]
dependencies: [task-24.1, task-208]
priority: medium
---

## Description
...
## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Claude Code template files are stored in src/templates/claude/
<!-- AC:END -->
```

Filename encodes `<PREFIX>-<id> - <slug>.md`; folder is configurable (`backlog/`, `.backlog/`).
Ships a CLI, a web kanban board, and an **MCP server** so coding agents manipulate tasks. MIT.
This is precisely the shape a git-backed suite wants: frontmatter for structured fields, markdown
body for prose, one file per item, one line per field.

**git-bug deserves a specific caution.** VERIFIED from its design doc: it stores JSON operation
packs as git blobs referenced by trees and commits under `refs/<namespace>/<id>`, merged
deterministically with **Lamport logical clocks** plus lexicographic tiebreak. The merge semantics
are *genuinely better* than files-in-a-tree — concurrent edits never conflict. But the data is
**invisible in a checkout**: you cannot `grep` it, you cannot open it in an editor, and you cannot
hand the folder to an LLM agent. For a suite whose entire pitch is "the files are the API," that
disqualifies it despite being the most technically sophisticated option here.

| Component | Plaintext format | Best existing tool | License | Diffs well in git? | Build or wrap? |
|---|---|---|---|---|---|
| Personal task list | todo.txt (one line per task) | todo.txt spec + any client | GPL-3.0 (spec repo) | **Excellent** | **Wrap** |
| Project tracker | `.md` + YAML frontmatter, one file per task | **Backlog.md** | MIT | **Excellent** | **Wrap or copy the schema** |
| Checklists inside docs | GFM `- [ ]` / `- [x]` | none needed | — | Excellent | Nothing to build |
| Emacs-native | org-mode `TODO`/`DONE` + `SCHEDULED:` | org-mode | GPL-3.0 | Excellent | Steal the ideas |
| CRDT-correct issue merge | git objects (opaque) | git-bug | GPL-3.0 | n/a — invisible | **Don't** — wrong ergonomics |
| Kanban DB apps | none | Vikunja / Plane | AGPL-3.0 | No | Out of scope |

**Assessment.** The cheapest win in the entire document, and there is nothing left to invent.
A kanban view over `backlog/tasks/*.md` is roughly a week of work and buys a disproportionate
amount of "this is a suite, not an editor."

---

## C. Forms / surveys

### There is no vendor-neutral plaintext form standard with mainstream traction

Two real contenders, both narrow.

**JSON Schema + UI Schema** is the web-dev default: `rjsf-team/react-jsonschema-form`,
**Apache-2.0**, 15,877★, pushed 2026-08-27 (VERIFIED). But *UI Schema is rjsf-specific* — it is a
convention of one library, not a spec. JSON Schema itself standardises validation, not presentation.
**Formily** (Alibaba, MIT, 12,566★) last shipped **2025-06-21** — 14 months stalled; treat as
unmaintained (VERIFIED via the commits feed).

**XLSForm is the only thing that resembles an actual standard**, and it belongs to the humanitarian
sector. A form is defined in a spreadsheet with `survey` / `choices` / `settings` sheets and
compiled to XForms XML by **pyxform** (**BSD-2-Clause**, VERIFIED from LICENSE). The ecosystem is
genuinely alive: **ODK Central** (Apache-2.0, VERIFIED, last commit 2026-08-21), **Enketo**
(Apache-2.0, VERIFIED, 2026-08-28), **KoboToolbox `kpi`** (AGPL-3.0, VERIFIED, 2026-08-28).
**The catch is fatal for us: XLSForm's canonical authoring artifact is `.xlsx` — a binary zip that
does not diff in git.** A CSV or markdown-table rendering is mechanically possible but non-standard,
so you'd be forking the format.

**W3C XForms is dead on the standards track.** XForms 2.0 is still a *First Public Working Draft
dated 2012-08-07* and never advanced (VERIFIED, <https://www.w3.org/TR/xforms20/>). It survives only
as ODK's internal intermediate representation.

**SurveyJS is a licensing trap that looks open.** `survey-library` is genuinely **MIT** (VERIFIED),
but `survey-creator` — the builder, i.e. the part that makes it a Forms product — ships a
**Devsoft Baltic OÜ commercial EULA** (VERIFIED by reading the LICENSE file). Both are active as of
2026-08-28. **Formbricks** is similarly mixed: **AGPL-3.0** core with an `apps/web/modules/ee`
enterprise directory under a separate license and MIT SDK packages (VERIFIED from LICENSE;
12,834★, pushed 2026-08-28). **OhMyForm is dead** — AGPL-3.0, **archived**, last push 2024-10-31
(VERIFIED). Tally and Fabform are closed SaaS.

### Where do responses go? Essentially nobody has solved this

**Staticman** (`eduardoboucas/staticman`, MIT, 2,451★) is still the reference implementation of
"commit a user submission into a git repo as YAML/JSON," and **its last commit is 2020-07-06**
(VERIFIED). It is not formally archived — just abandoned. No maintained successor surfaced. The
nearest living thing is **Decap CMS** (pushed 2026-08-21), which wraps git *content editing*, not
form *reception*.

This niche is unoccupied, and it is unoccupied for reasons:

- **Concurrent submissions conflict deterministically.** Two responses appending to one CSV touch
  the same final line; git has no append-merge driver by default. Volume makes this worse, not
  better.
- **It is a privacy failure by construction.** Anyone with clone access reads every response, and
  PII becomes **immutable in history** — a redaction request requires a history rewrite and a
  force-push that breaks every existing clone.
- **No auth, no rate limiting, no spam control.** A public form endpoint that writes to your repo is
  a write primitive handed to the internet.

| Component | Plaintext format | Best existing tool | License | Diffs well in git? | Build or wrap? |
|---|---|---|---|---|---|
| Form definition (general) | JSON Schema + uiSchema | react-jsonschema-form | Apache-2.0 | **Yes** (pretty JSON / YAML) | **Wrap** |
| Form definition (survey/field data) | XLSForm | pyxform + ODK Central | BSD-2-Clause / Apache-2.0 | **No — `.xlsx` binary** | Wrap + write a CSV shim |
| Renderer | JSON | SurveyJS `survey-library` | MIT | Yes | Wrap |
| Visual builder UI | — | SurveyJS `survey-creator` | **Commercial EULA** | — | **Build** (or skip) |
| Full form product | — | Formbricks | AGPL-3.0 core + EE dir | No (DB-backed) | Out of scope |
| Legacy standard | XForms XML | — | W3C | Yes | Dead — ignore |
| **Response sink** | CSV / JSONL in repo | **none maintained** (Staticman, 2020) | MIT | **No — appends conflict** | **Build, or don't** |

**Assessment.** Split the problem. The **form definition** as a text file is a genuine cheap win —
a `form.yaml` (JSON Schema + a UI hint block) diffs perfectly, reviews in a PR, and rjsf renders it
for free. **Responses in git are a trap**, and Staticman's death is evidence rather than
coincidence. Version the definition; route responses to a real store (SQLite, a hosted endpoint,
even an appended file *outside* the repo) and offer "export responses to `responses.csv`" as an
explicit, user-triggered commit. That gives you the git story without the conflict, privacy, and
abuse story.

---

## D. Drawing / diagrams / whiteboard

This area splits cleanly into **text-as-source** (diffs like code) and **GUI-app formats** (diffs
like a database dump). The split matters more than any individual tool choice.

### Tier 1 — genuinely text-diffable

All VERIFIED 2026-08-28 via `api.github.com`:

- **Mermaid** — MIT, 89,972★, pushed 2026-08-28. Renders natively in GitHub, GitLab, and Claude
  artifacts. The default.
- **D2** — repo is **`d2lang/d2`** (Terrastruct is the company; `terrastruct/d2` redirects).
  **MPL-2.0**, 25,092★, pushed 2026-08-28. Better layout engines (ELK, TALA) and a real language.
- **PlantUML** — LGPL-3.0, 13,277★, pushed 2026-08-27. Widest diagram-type coverage; needs a JVM
  and Graphviz for several layouts.
- **Graphviz / DOT** — **EPL-2.0** (VERIFIED, <https://graphviz.org/license/>). The substrate under
  several of the above.

For all four, a diagram edit is a *source* edit: one changed line, reviewable in a PR, mergeable by
git's normal three-way merge, and comprehensible to an LLM agent. This is the tier you build on.

### Tier 2 — GUI formats, and they are not all equal

**Excalidraw** — MIT, 130,697★, pushed 2026-08-28. Better than its reputation, worse than text.
VERIFIED from source:

- `packages/excalidraw/data/json.ts` serializes with `JSON.stringify(data, null, 2)` — **pretty
  printed, one field per line.** So it is line-oriented, not a single-line blob.
- `packages/element/src/types.ts` shows every element carries `seed`, `version` (*"sequentially
  incremented on each change"*), `versionNonce` (*"regenerated on each change"*), `updated`
  (*"epoch (ms) timestamp of last element update"*), `index` (fractional index), and `isDeleted`.
- Deleted elements are **tombstoned** (`isDeleted: true`) rather than removed, so files grow
  monotonically.
- `appState` is exported (cleaned, but present), so view/config state churns too.

Simulating the app's exact mutation for dragging one rectangle 40px right (SIMULATED from the
VERIFIED schema — I could not fetch a real `.excalidraw` file with history because GitHub code
search was rate-limited):

```diff
-      "x": 400,
+      "x": 440,
-      "version": 7,
-      "versionNonce": 993310,
+      "version": 8,
+      "versionNonce": 441209,
-      "updated": 1756300000000,
+      "updated": 1756399999000,
```

Four changed lines, one meaningful — **75% noise**. Verdict: two people editing *different* shapes
will merge fine at the line level; two people editing the *same* shape produce a conflict on
`version`/`versionNonce` that no human can resolve meaningfully; and nobody will ever review a
diagram change by reading the diff. Usable as an escape hatch, never as the primary representation.

**tldraw is NOT open source — confirmed.** VERIFIED by reading
<https://github.com/tldraw/tldraw/blob/main/LICENSE.md>: it is a proprietary *"tldraw license"*
from tldraw, Inc. Permissions cover development environments only; the conditions include
**"Not to use the Software in Production Environments"** and **"Not to disable, change, or interfere
with the Software's License Key enforcement."** Production use requires a commercial license from
tldraw. GitHub reports `NOASSERTION`; 50,008★; pushed 2026-08-28 (very active — but that is
irrelevant). **Do not build on it.** Your instinct was right.

**draw.io / diagrams.net is the surprise.** `jgraph/drawio`, **Apache-2.0**, 7,777★, pushed
2026-08-28. And the compression concern is stale: VERIFIED from the official docs
(<https://www.drawio.com/doc/faq/configure-diagram-editor>), the `compressXml` setting is
**"The default is `false`"** — so `.drawio` files are plain, readable `mxGraphModel` XML by default,
with roughly one `<mxCell>` element per shape. Moving a shape changes one line. Caveat: legacy
files and some embed-mode integrations still emit deflate+base64 payloads inside `<diagram>`, which
are completely opaque to git; a repo would want a pre-commit check that rejects
`<mxfile compressed="true">`.

**SVG-as-source**: text, but GUI editors renumber ids, reorder elements, and re-emit path data at
full float precision, so churn is severe. Excellent as a *rendered output* committed alongside the
source; bad as the source of truth.

| Component | Plaintext format | Best existing tool | License | Diffs well in git? | Build or wrap? |
|---|---|---|---|---|---|
| Flow/sequence/ER diagrams | Mermaid text | mermaid-js/mermaid | MIT | **Excellent** | **Wrap** (renders natively in most viewers) |
| Richer diagrams-as-code | D2 text | d2lang/d2 | MPL-2.0 | **Excellent** | Wrap |
| UML / widest coverage | PlantUML text | plantuml/plantuml | LGPL-3.0 | Excellent | Wrap (JVM dependency) |
| Graph layout primitive | DOT | Graphviz | EPL-2.0 | Excellent | Wrap |
| GUI diagram editor | `.drawio` XML (uncompressed default) | jgraph/drawio | Apache-2.0 | **Decent** — one `<mxCell>` per shape | **Wrap** — best GUI option |
| Freehand whiteboard | `.excalidraw` pretty JSON | excalidraw/excalidraw | MIT | **Poor but not fatal** — ~75% noise, tombstones | Wrap as escape hatch, warn users |
| Infinite canvas SDK | proprietary | tldraw | **Proprietary "tldraw license"** — no production use | n/a | **Avoid — license** |
| Rendered output | SVG | any renderer | varies | Poor as source | Commit as artifact, not truth |

**Assessment.** Make Mermaid/D2 first-class: the diagram source lives *inside the document*, and
the app renders it. That is a wrap job with essentially no format risk. Offer Excalidraw for
freehand and be honest in the UI that its history is not reviewable. draw.io is the sleeper pick if
you want a full GUI diagram editor with an OSI license and text files. Avoid tldraw regardless of
how good it is.

---

## E. Email

**Verified facts.** Maildir stores one message per file, immutable, with IMAP flags encoded in the
*filename* suffix (`:2,S` for seen, etc.) — so "mark as read" is a rename, which git records as a
delete plus an add. **notmuch** (GPL-3.0-or-later, VERIFIED from `COPYING`; the GitHub mirror shows
209★, pushed 2026-08-24) indexes a Maildir with Xapian and keeps **tags in the database, not in the
files** — meaning the part of notmuch that is actually the product lives outside the plaintext.
**isync/mbsync** does IMAP↔Maildir sync. Clients: **aerc** — MIT, now maintained at
`~rjarry/aerc` on sourcehut, the original `~sircmpwn/aerc` being unmaintained (REPORTED, LWN
<https://lwn.net/Articles/993498/>) — and **Himalaya**, Apache-2.0, 7,124★, pushed 2026-08-27
(VERIFIED).

**Assessment: out of scope, and not close.** Email is not a document store; it is a delivery
protocol plus an immutable archive. Every property git gives you — diff, merge, blame, review — is
meaningless for messages, which are never edited and never merged. Meanwhile every cost is
present at full strength: a real mailbox is tens of gigabytes of already-compressed attachments,
which is the single worst case for git's delta compression (see area F); it grows append-only at a
rate where you must choose between one commit per message and batching that destroys the
granularity you committed for; and every message is PII that becomes **permanent and unrewritable**
in the history of a repo that people will clone onto laptops.

The one real coupling is worth naming, because it is not obvious: **calendar invitations arrive as
email.** iMIP (RFC 6047) puts iCalendar objects in MIME parts over SMTP, so a suite that promises
meeting scheduling needs *read access to* a mailbox and *send access to* an SMTP server even though
it should never *own* a mail archive. The correct posture is integrate-never-store: IMAP or JMAP to
read invitations, SMTP to send `REPLY`s, and no Maildir anywhere near the repo.

---

## F. Files/Drive UX

### Binary attachments

- **git-lfs** — actual license is **`MIT AND BSD-3-Clause`** (VERIFIED from `LICENSE.md`; MIT for
  GitHub Inc. + contributors, BSD-3-Clause for vendored Go `subprocess`/`tools`). Alive:
  v3.8.0 released 2026-08-28, 14,446★. Model: a `.gitattributes` filter replaces the file with a
  ~130-byte pointer blob; bytes move over a separate HTTP batch API.
  **The quota is a product killer.** VERIFIED from docs.github.com: Free/Pro get **10 GiB storage +
  10 GiB bandwidth/month**; Team/Enterprise 250 GiB each. Exceed bandwidth without a payment method
  and *"Git LFS support is disabled on your account until the next month"* — the repo still clones,
  but **every attachment 404s**. GitLab.com Free is 10 GiB per project covering repo + LFS combined,
  and going over makes the project **read-only** (REPORTED). Gitea (MIT) and Forgejo self-host LFS
  with no vendor quota; you pay for disk instead.
  Other failure modes (VERIFIED): `git lfs migrate import` *"rewrite[s] your Git history, changing
  commits and generating new commit SHAs"* and requires force-pushing every branch — catastrophic
  for a multi-device consumer sync product. A clone without git-lfs installed (or with
  `GIT_LFS_SKIP_SMUDGE=1`) yields pointer text where the user expects a PNG.
- **Just committing binaries** — VERIFIED GitHub limits: **50 MiB warning, 100 MiB hard block per
  file, 25 MiB via the web UI**; repos *"ideally less than 1 GB"*, *"strongly recommended less than
  5 GB"*. Every edit of a JPEG/PDF/MP4 stores a full new zlib copy (delta compression is
  near-useless on already-compressed formats) and history is permanent: a 5 MB image edited 100
  times is ~500 MB forever.
- **git-annex** — **AGPL-3.0-or-later** (VERIFIED, <https://git-annex.branchable.com/license/>:
  *"licensed as a whole under the AGPL, version 3 or higher"*), v10.20260717 released 2026-07-20.
  Symlinks into a content-addressed `.git/annex/objects` store plus "special remotes". Technically
  the best model — files can be present or absent per-clone, per-device — but AGPL, Haskell, and
  symlinks-on-Windows make it wrong for a shipped consumer app. **Steal the model, don't ship it.**
- **Xet** — `huggingface/xet-core`, **Apache-2.0**, 564★, pushed 2026-08-28, v1.6.0 2026-08-03.
  Same pointer-file + `.gitattributes` mechanism as LFS but with content-defined chunking and
  chunk-level dedup. HF docs say Git LFS *"remains supported"* as legacy. It is Hub-coupled, not a
  general git remote.
- **Blobless clone** — `--filter=blob:none` / `blob:limit=1m` with sparse-checkout. VERIFIED from
  git-scm's `partial-clone` doc: missing blobs are demand-fetched from a *promisor remote*, but
  `git log -p A..B` can drag everything down, and dynamic fetching *"invokes fetch-pack once per
  missing object"* with repeated auth. Great server-side; bad for offline-first clients.
- **jj (Jujutsu)** — Apache-2.0, 31k★, v0.44.0 2026-08-06 — has **no large-file story**: issue #80
  "Add support for Git LFS" has been open since 2022-02-24 with 100 comments (last activity
  2026-07-13).

### Per-file sharing — this is the trap

**No git forge on earth does per-file read ACLs.** The smallest unit of read authorization is the
repository (or, in Gerrit's case, the ref). Two commonly repeated beliefs are **wrong**, both
verified against primary docs:

- **Gerrit does not have per-path access control.** `project.config` ACLs are keyed on *ref*
  patterns only (`refs/heads/master`, `refs/heads/*`, regex). The `code-owners` / `find-owners`
  plugins are **submit requirements** — approval routing, exactly like CODEOWNERS — not access
  control.
- **GitLab "Protected paths" are HTTP rate limits, not file ACLs** — they return HTTP 429 on
  endpoints like sign-in. Nothing to do with repo paths. GitLab CODEOWNERS is Premium/Ultimate and
  is approval routing; "Allowed to push and merge" bypasses it.
- **Gitea** and **Forgejo** both have *unit*-level permissions (Code / Issues / PRs / Releases /
  Wiki / Projects / Packages / Actions, at No Access / Read / Write). **No file- or path-level
  access control in either.** (VERIFIED: docs.gitea.com/usage/permissions;
  forgejo.org/docs/v15.0/user/collaboration/repo-permissions/)
- **GitHub CODEOWNERS** is review routing, not access control.

**Encryption-per-file as a share primitive fails on revocation.** git-crypt (GPL-3.0, 9,875★) is
effectively dormant — 12 commits since 2024-01-01, and 0.8.0 (2025-09-24) was mostly CI/README
housekeeping. transcrypt (MIT, 1.7k★, v2.3.2 2026-05-18) is a livelier shell script. SOPS
(`getsops/sops`, **MPL-2.0**, 22.9k★, v3.13.3 2026-07-23) is healthy but encrypts *structured
config*, not documents. All three fail identically: revoking a recipient means re-encrypting, and
the old ciphertext stays in history forever.

**Share links.** VERIFIED from docs.github.com: pressing `y` rewrites a branch URL into a
commit-SHA permalink so *"anyone you share it with will see exactly what you saw"*, with
`#L10-L20` line pinning. But a GitHub permalink is **still gated by repo access** — it is a
*stable* link, not a *shareable* one. There is no git-native equivalent of a Google Docs
"anyone with the link" URL, because that requires an unauthenticated read path scoped to a single
object, which no forge exposes.

| Component | Approach | Best tool | License | Works on git? | Build or wrap? |
|---|---|---|---|---|---|
| Images/PDFs in docs | pointer file + side store | git-lfs v3.8.0 | MIT AND BSD-3-Clause | Yes, native | **Wrap** — host your own LFS server, never rely on GitHub quota |
| Large media, per-device presence | symlink to CAS + special remotes | git-annex 10.20260717 | AGPL-3.0-or-later | Yes | Steal the model; AGPL blocks shipping |
| Chunk-level dedup at scale | CDC pointer files | xet-core v1.6.0 | Apache-2.0 | HF Hub only | Build on the protocol |
| Fast clone of a doc repo | `--filter=blob:none` + sparse-checkout | core git | GPL-2.0 | Yes | **Wrap**, server-side only |
| **Per-file read ACL** | **none exists** | — | — | **No** | **Build an app layer — this is the trap** |
| Per-file review gate | CODEOWNERS | GitHub / GitLab / Gerrit plugin | — | Yes | Wrap (but it is not access control) |
| Encrypt one doc | filter-driver crypto | transcrypt / git-crypt | MIT / GPL-3.0 | Yes | **Avoid** — no revocation |
| Share link | commit-SHA permalink | GitHub `y` | — | Yes, but access-gated | Build your own renderer |

**Assessment — the permissions problem is structural, not a gap you can close.** Git's object
model has no ACL anywhere; authorization is bolted on by the *server* at the ref/repo boundary
because that is the only boundary the wire protocol exposes. Four real options, ranked:

1. **Server-side app layer owns ACLs; git is storage only.** The user never talks to git — your API
   does. This is what **Hugging Face Hub** does (git+LFS/Xet under a permission system users never
   see as git) and what every git-backed CMS does (Decap/Netlify CMS, GitBook). The only option
   that supports "share this one doc with a client, revoke tomorrow."
2. **Repo-per-sharing-scope.** Honest and forge-native, but 300 docs across 40 audiences is a repo
   explosion; Gitea/Forgejo unit perms don't help.
3. **Publish/export pipeline** — render one file to a static unguessable URL. Closest thing to a
   Docs share link, read-only, no revocation without breaking the URL.
4. **Submodules as a boundary** — a submodule *is* a separate repo, so this is option 2 with worse
   UX; git records a gitlink whose target the reader can't fetch, producing a broken checkout rather
   than a clean permission error.

**Design consequence: git can be your storage and history layer, but the moment the product
promises Google-Docs-style sharing you are writing an authorization server.** Plan for it in v1
rather than discovering it after committing to "the forge is the backend."

---

## G. Notes/wiki + search

### The headline: Logseq abandoned markdown as the source of truth

This is the most important single fact in this section. VERIFIED from
<https://raw.githubusercontent.com/logseq/docs/master/db-version.md> (page dated **2026-04-28**):
Logseq's DB version persists "a graph to `~/logseq/graphs/GRAPH-NAME/db.sqlite`" — **SQLite is
canonical, files are not.** The file-based application was split out to **`logseq/og`** (last
commit **2026-05-28**, VERIFIED) in maintenance-only mode. The main repo remains AGPL-3.0 and very
active (44,663★, pushed 2026-08-27).

The most prominent plaintext-first outliner in the world concluded that plaintext could not carry
the index. Treat this as a live risk, not a historical curiosity: **expect sustained internal
pressure to make the index authoritative, and resist it.**

### What the survivors actually do

Every project that is still healthy converged on the same shape: **files are truth, the index is a
rebuildable, disposable cache.**

- **Obsidian** (closed source): VERIFIED from obsidian.md/help — the vault is "Markdown-formatted
  plain text files" plus a hidden `.obsidian` folder holding hotkeys/themes/plugins; the index lives
  in **IndexedDB plus a rebuildable metadata cache outside the vault.** So the vault genuinely is
  portable and the index genuinely is throwaway.
- **SilverBullet** (MIT, 5,947★, pushed 2026-08-27): VERIFIED from
  <https://silverbullet.md/Architecture/Datastore> — the object index is "an IndexedDB-backed
  key-value store — the client's local persistence layer."
- **Foam** (MIT per its LICENSE; GitHub reports NOASSERTION; 17,379★, pushed 2026-08-13): a VS Code
  extension over a folder of markdown. Alive but quiet.
- **Dendron** (Apache-2.0, 7,465★): **dead, and it says so.** The README states verbatim
  *"Dendron is currently in maintenace only, active development has ceased."* (VERIFIED);
  default-branch commits stop 2025-06-01.

### Search engines for indexing a repo of markdown

| Engine | License | Activity | Shape | Verdict |
|---|---|---|---|---|
| **ripgrep** | MIT / Unlicense | 2026-08-04 | subprocess, no index | **Day-one search.** Zero build cost |
| **SQLite FTS5** | Public domain | core SQLite | embedded, incremental | **The default persistent index** |
| **tantivy** | **MIT** (VERIFIED) | 2026-08-27, 16,002★ | embedded Rust lib | Wrap if you outgrow FTS5 |
| **Pagefind** | MIT | 2026-08-26 | prebuilt static index | Good for published/exported sites |
| **Orama** | **Apache-2.0** (VERIFIED from LICENSE.md — GitHub's NOASSERTION is wrong) | 2026-08-04, 10,536★ | in-memory JS | Viable in a web client |
| **MiniSearch** | MIT | 2025-09-16 | in-memory JS | Alive but slow at scale |
| **Meilisearch** | **`MIT AND BUSL-1.1`** (VERIFIED — `enterprise_editions` files are BUSL-1.1; production use needs a commercial agreement; converts to MIT after 4 years) | 2026-08-27, 59,112★ | **separate server process** | **Avoid** — license + ops burden |
| **Lunr** | MIT | **last commit 2020-08-19** | in-memory JS | **Dead** |

### Backlinks and tags: no spec exists

**CommonMark has no wikilink.** It is still at 0.31.2, and `[[...]]` appears only on the
`commonmark-spec` wiki's *Proposed Extensions* page (VERIFIED). GitHub renders `[[...]]` **in wikis
only**, not in repo markdown. So `[[link]]`, `#tag`, and YAML frontmatter are **de-facto
conventions with per-tool resolution rules** — Obsidian's shortest-unique-path resolution, Dendron's
dotted hierarchy, and Logseq's page-name resolution are all mutually incompatible.

Practical consequence: pick one resolution rule, document it, and store the *resolved* target
nowhere — recompute it into the index. Do not write resolved links back into the files, or you have
made the index authoritative through the back door.

| Component | Plaintext format | Best existing tool | License | Diffs well in git? | Build or wrap? |
|---|---|---|---|---|---|
| Notes | `.md` + YAML frontmatter | — (convention) | — | **Excellent** | Nothing to build |
| Ad-hoc search | — | ripgrep | MIT / Unlicense | n/a (no index) | **Wrap** |
| Persistent index | — | **SQLite FTS5** | Public domain | **Gitignore it** | **Wrap** |
| High-performance index | — | tantivy | MIT | Gitignore it | Wrap if needed |
| Published-site search | — | Pagefind | MIT | Build artifact | Wrap |
| Backlinks | `[[wikilink]]` | no spec; Obsidian is the de-facto reference | — | Excellent (plain text) | **Build** the resolver, pick one rule |
| Tags | `#tag` / frontmatter `tags:` | no spec | — | Excellent | Build the index |

**Assessment.** Cheap win, with one hard rule: **the index must be a gitignored cache that can be
deleted and rebuilt from the files at any time.** ripgrep on day one, SQLite FTS5 when you need
ranking and incremental updates, tantivy only if you outgrow it. Avoid Meilisearch (BUSL plus a
server process). The trap here is not technical — it is Logseq's trap: the moment the index holds
something the files don't, plaintext stops being the product.

---

## H. Has anyone assembled a *suite* from plaintext parts?

### org-mode: the only one that actually shipped

org-mode is the single existence proof. It has, in one format, in one file type, for twenty years:
agenda (calendar + tasks), tables with a spreadsheet formula language, Babel (executable code
blocks — a notebook), capture (an inbox), and export to HTML/LaTeX/Beamer/reveal.js (docs *and*
slides). GPL-3.0.

Three lessons, and they are the important part of this whole document:

1. **The integration is the product, not the formats.** org's actual value is that a `TODO` typed
   into a meeting note *is* an agenda item with no sync step, no import, no second app. Every
   plaintext suite that stops at "we have good formats" has built a filing cabinet, not a suite.
2. **A suite with one client has a ceiling.** org is unusable by anyone who will not adopt Emacs.
   Orgzly and org-mode parsers exist, but the format is so Emacs-shaped that fidelity outside Emacs
   is a permanent tax. The corollary for a new project: *design the format so a second
   implementation is plausible* — which argues hard for markdown + YAML frontmatter over anything
   clever.
3. **org has essentially no collaboration story**, and that is precisely where every plaintext
   suite dies.

### Everyone who tried to be a suite abandoned plaintext

- **Nextcloud** (AGPL-3.0, 36,604★, pushed 2026-08-28) is the closest *shipped* suite, but its
  substrate is a database plus a WebDAV file store, and its office layer (Collabora / OnlyOffice) is
  OOXML/ODF — a binary-ish XML zip that is round-tripped, not authored as text. It proves a suite is
  assemblable; it also proves that the instant you want real-time editing you reach for a document
  engine, not a file format.
- **AFFiNE** (71,969★, pushed 2026-08-28; license is **mixed** — most of the tree is MIT per
  `LICENSE-MIT`, but `packages/backend` and `packages/common/native` fall under a separate
  restricted license, VERIFIED from `LICENSE`) stores documents as **Yjs binary** via BlockSuite.
  Markdown is an *export adapter*, not the truth (REPORTED, docs.affine.pro; corroborated by
  `toeverything/affine-reader`, whose stated purpose is converting a Yjs doc into markdown).
- **Anytype** (`anyproto/anytype-ts`, 8,711★, pushed 2026-08-26) is under the **Any Source Available
  License 1.0** — VERIFIED from `LICENSE.md`: use/modify/redistribute permitted only *"(a) for
  Non-Commercial Use, or (b) for Commercial Use in Allowed Networks."* **This is source-available,
  not OSI open source.** Storage is protobuf blocks plus CRDT change objects over any-sync
  (REPORTED).

Both AFFiNE and Anytype are "local-first" without being "plaintext," and both chose a CRDT because
they wanted real-time collaboration. **That is the fork in the road**, and it is the single most
important strategic fact in this document.

### Folder-native PKM: succeeds at notes, stalls at suite

VERIFIED activity 2026-08-28: SilverBullet (MIT, 5,947★, pushed 2026-08-27), Foam (MIT per its
`LICENSE`; GitHub says NOASSERTION; 17,379★, pushed 2026-08-13), **Dendron (Apache-2.0, 7,465★ —
explicitly dead: its README says *"Dendron is currently in maintenace only, active development has
ceased."*)**, Logseq (AGPL-3.0, 44,663★, pushed 2026-08-27), Obsidian (closed source). Tana and
Capacities are proprietary and object-DB-backed (REPORTED).

**Logseq is the third data point and the most damning**, because it did not stall and it did not
start out as a database product — it *converted*. Its DB version makes `db.sqlite` canonical and
demotes the file-based app to `logseq/og` in maintenance mode (VERIFIED, area G). So the pattern
now reads: **every folder-of-markdown project either stalls at notes (Dendron), converts to a
database when it tries to grow (Logseq), or was never plaintext to begin with (AFFiNE, Anytype,
Notion, Nextcloud's office layer).** The only survivors that are still plaintext-first — Obsidian,
SilverBullet, Foam — are all *notes apps that never attempted to be a suite*.

That is the strongest argument against this whole thesis, and it deserves to be stated plainly
rather than buried. The counter-argument is that all three of those conversions were driven by
wanting **queryable structure and real-time collaboration**, not by markdown being inadequate for
documents — which is exactly the pair of features a git-backed suite should decline to promise in
v1.

### What the history teaches

Nobody has assembled the plaintext suite because **the formats were never the hard part.** Docs,
sheets, slides, calendar, tasks, and diagrams all have credible plaintext representations today,
most of them twenty years old and battle-tested. What is missing is:

- **(a) one shell that opens all of them** — org-mode solved this and paid for it with Emacs;
- **(b) an identity and permission layer** — git cannot provide it (area F), so it must be built;
- **(c) a collaboration model** — and this is where plaintext-as-truth and CRDT-as-truth are in
  genuine tension, not merely in tradeoff.

The honest read: (a) is where the differentiation is and it is mostly product work, (b) is
unavoidable engineering that people underestimate, and (c) is a strategic choice you should make
explicitly in v1 rather than discover in v3.

---

## Minimum credible "suite" scope

**Ship (core, from findings 01–06):** Docs (`.md`), Sheets (`.csv` + formula/format sidecar),
Slides (`.md` with `---`, wrapping Marp).

**Add, in cost order:**

1. **Tasks** — `backlog/tasks/*.md` with YAML frontmatter, exactly Backlog.md's schema. Highest
   ratio of perceived-suite-ness to build cost in the whole document.
2. **Diagrams** — Mermaid/D2 fenced blocks rendered inline in docs. Zero format risk; `.excalidraw`
   as a documented escape hatch.
3. **Search** — ripgrep on day one; SQLite FTS5 as a **gitignored** index when ranking is needed.
4. **Calendar** — vdir folder + Radicale sidecar for CalDAV. Read/edit *my* calendar only.
5. **Attachments** — self-hosted LFS (never a public forge's quota).
6. **Forms — definition only.** A `form.yaml` (JSON Schema + UI hints) rendered by rjsf. Responses
   go somewhere else.

**Explicitly out of scope for v1:** email; form response collection in the repo; per-file sharing
without a server; real-time co-editing; meeting scheduling, invitations, and free/busy.

### The seven traps, ranked by how expensive they are to discover late

1. **Per-file sharing forces an authorization server** (F). Not a git gap you can close — no forge
   on earth has per-file read ACLs. Decide in v1 whether the product promises Docs-style sharing.
2. **The index becoming authoritative** (G, H). Logseq's conversion is the cautionary tale. The
   index must be deletable and rebuildable from files, forever.
3. **Real-time collaboration vs plaintext-as-truth** (H). Every project that chose collab chose a
   CRDT and left plaintext behind. This is a fork, not a tradeoff.
4. **Form responses in git** (C). Deterministic merge conflicts, immutable PII, no auth. Staticman
   died in 2020 and nobody replaced it.
5. **Calendar invitations and free/busy are protocols, not files** (A). iTIP/iMIP needs a mail path.
   Users mean "scheduling" when they say "calendar."
6. **Binary attachments on a public forge's LFS quota** (F). Exceeding GitHub's free bandwidth
   disables LFS and every attachment 404s while the repo still clones.
7. **License surprises** — **tldraw** is proprietary with a no-production-use clause (D);
   **SurveyJS Creator** is a paid EULA behind an MIT library (C); **Meilisearch** is BUSL-1.1 in
   part (G); **Anytype** is source-available, not open source (H); **git-annex** is AGPL (F).

## Sources

Calendar: <https://vdirsyncer.pimutils.org/en/stable/vdir.html> · <https://radicale.org/v3.html> ·
<https://khal.readthedocs.io/en/stable/> · <https://www.rfc-editor.org/rfc/rfc5546> ·
<https://www.rfc-editor.org/rfc/rfc6047.html>

Tasks: <https://github.com/todotxt/todo.txt> · <https://taskwarrior.org/news/news.20240324/> ·
<https://taskwarrior.org/docs/upgrade-3/> · <https://github.com/MrLesk/Backlog.md> ·
<https://github.com/git-bug/git-bug/blob/master/doc/design/data-model.md> ·
<https://fossil-scm.org/home/doc/trunk/www/bugtheory.wiki> ·
<https://archive.fosdem.org/2023/schedule/event/tissue/>

Diagrams: <https://github.com/tldraw/tldraw/blob/main/LICENSE.md> ·
<https://www.drawio.com/doc/faq/configure-diagram-editor> · <https://graphviz.org/license/> ·
<https://github.com/excalidraw/excalidraw/blob/master/packages/element/src/types.ts> ·
<https://github.com/excalidraw/excalidraw/blob/master/packages/excalidraw/data/json.ts>

Forms: <https://github.com/eduardoboucas/staticman> · <https://xlsform.org/en/> ·
<https://github.com/getodk/central> · <https://www.w3.org/TR/xforms20/> ·
<https://raw.githubusercontent.com/surveyjs/survey-creator/master/LICENSE>

Notes/search: <https://raw.githubusercontent.com/logseq/docs/master/db-version.md> ·
<https://github.com/logseq/og> ·
<https://obsidian.md/help/Files+and+folders/How+Obsidian+stores+data> ·
<https://silverbullet.md/Architecture/Datastore> · <https://github.com/dendronhq/dendron> ·
<https://github.com/meilisearch/meilisearch/blob/main/LICENSE-EE> ·
<https://github.com/oramasearch/orama/blob/main/LICENSE.md> ·
<https://github.com/commonmark/commonmark-spec/wiki/Proposed-Extensions>

Email: <https://lwn.net/Articles/993498/> · <https://github.com/pimalaya/himalaya>

Drive: <https://github.com/git-lfs/git-lfs/blob/main/LICENSE.md> ·
<https://docs.github.com/billing/managing-billing-for-git-large-file-storage/about-billing-for-git-large-file-storage> ·
<https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github> ·
<https://git-annex.branchable.com/license/> · <https://git-scm.com/docs/partial-clone> ·
<https://huggingface.co/docs/hub/en/storage-backends> · <https://github.com/jj-vcs/jj/issues/80> ·
<https://gerrit-review.googlesource.com/Documentation/access-control.html> ·
<https://docs.gitlab.com/administration/settings/protected_paths/> ·
<https://docs.gitea.com/usage/permissions> ·
<https://forgejo.org/docs/v15.0/user/collaboration/repo-permissions/> ·
<https://docs.github.com/en/repositories/working-with-files/using-files/getting-permanent-links-to-files>

Suite: <https://orgmode.org/features.html> · <https://docs.affine.pro/blocksuite-wip/store/transformer-and-adapter> ·
<https://github.com/anyproto/anytype-ts/blob/main/LICENSE.md> · <https://doc.anytype.io/anytype/data/storage>

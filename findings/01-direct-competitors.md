# Direct Competitors — Git-Backed Docs / Sheets / Slides

Research date: **2026-08-28**. All HTTP status codes and timestamps below were observed on that date unless otherwise noted.

Legend: **VERIFIED** = I fetched it myself and quote the observed response. **REPORTED** = a third party asserts it; I could not independently confirm.

---

## Summary table

| Product | What it is | Status / last activity | Open source? | Docs / Sheets / Slides | Verdict |
|---|---|---|---|---|---|
| **Nimbalyst** (§4) | Electron desktop workspace for orchestrating Claude Code / Codex / OpenCode agents; plain files + real `simple-git` integration; 26-extension marketplace | **ACTIVE — commits and a release on 2026-08-28.** 96 releases, 1,594★ | **MIT (client only)** — sync server and the Slides extension are **private/404** | Docs ✅ `.md` · Sheets ✅ `.csv` **with formula support** · Slides ✅ **`.slides.md`, reveal.js, `---` separators** | **The real competitor, and it was under-weighted in the brief. It already ships all three legs on plain files in git.** Different audience though: developers running coding agents, not teams doing office work |
| **Moment** (§3) | ~7-person Seattle co. Markdown workspace with a bespoke OT collab engine, jj-over-git storage, embedded agent terminal, code cells | **Shipping hard to 2026-05-01, then ~4 months quiet.** Binary still `0.3.706` despite "v1.5" marketing | ❌ closed source. **No self-hosting** | Docs ✅ · Sheets ❌ (CSV is an *attachment*, not an app) · Slides ❌ | Strongest tech brand in the set (352- and 272-point HN blog posts). **But collaboration and publishing route through `git.moment.dev`, not your repo** — that gap is the wedge |
| **Pithy** (§1) | Tauri desktop app: WYSIWYG markdown + CSV grid, local git repo as the drive, GitHub OAuth, full git UI | **Stalled.** Binaries last built **2026-03-28**; demo repo last commit **2026-03-30**; ~5 months silent | **Claimed, but FALSE today.** `github.com/PithyDocs/pithy-app` → **404 even authenticated**. Page says AGPL-3.0 in one place and MIT in another | Docs ✅ `.md`/`.markdown`/`.mdx` · Sheets ✅ `.csv` (PapaParse grid, no formulas) · Slides ❌ | Nearly identical thesis to this project and a genuinely complete build — but never launched, **zero** public footprint, apparently abandoned. Solo side project by Tyler Tate (product leader at Instacart) |
| **Eigen** (§5) | Self-hosted Google Workspace clone: 14 apps incl. mail/IMAP, CalDAV, CardDAV, WebDAV, chat | **VERY ACTIVE** — 745 commits in 30 days, pushed 2026-08-28. But **14★, 1 fork, 2 issues ever, 2 releases with zero binaries** | **MIT, fully open** (the only one here with nothing held back) | Docs ✅ · Sheets ✅ (fortune-sheet fork — **the deepest sheet found**) · Slides ✅ (WYSIWYG object canvas) | **NOT git-backed at all** — SQLite + Yjs CRDT; docs are `.eigendoc`/`.eigensheets`/`.eigenslides` SQLite containers. Cautionary tale on scope: hyper-productive, ~zero adoption, bus factor 1 |
| **Perchpad** (§2) | Web app: server-hosted git repo per workspace, realtime markdown collab, CSV tables, AI "bird", MCP server | **Live but dormant.** Site 200; last Fly.io deploy **2026-04-05**; Show HN got **2 points / 2 comments** | ❌ no public repo found | Docs ✅ `.md` · Sheets ⚠️ `.csv` as editable tables · Slides ❌ | Solo weekend project. **Cloud-first, not local-first** — GitHub sync is still listed "Coming Soon". No published pricing. Effectively zero traction |
| **Kova** (§6) | GPL-3.0 Tauri markdown **presentation** editor: `---` slides, 11 themes, PPTX/PDF/HTML export, Marp import, plus `!sheet` computed tables (formulas live inside a GFM table) | **ACTIVE** — 67 releases in 3.7 months, pushed 2026-08-23. **0 open PRs, 4 open issues** | **GPL-3.0** — the only copyleft project in the set, no CLA, so it cannot be relicensed or vendored | Docs ❌ · Sheets ⚠️ formulas as a *slide widget*, not a product · Slides ✅ **the most polished slide tool found** | **Neither threat nor component.** Competes with Marp/Slidev, not with a workspace — one `.md` file, no collab, no git, no multi-file drive. But its **distribution is the best in this report** and worth copying. Solo dev, **$0 raised**, never posted to HN |
| **Notula** (§7.2) | Closed-source commercial WYSIWYG that commits plain `.md` to **your own** repo; no branches or PRs by design | **LIVE** — Show HN 2026-08-19 (2p/3c) | ❌ closed | Docs ✅ · Sheets ❌ · Slides ❌ | **The most direct live commercial rival on the Docs leg**, and the one product that gets "your own repo" fully right |
| **Ledgit** (§7.2) | Tauri/Rust + AG Grid over CSV/TSV files on disk, with commit/branch/three-way-merge and per-cell conflict resolution via `daff` | **Stalled** — created 2026-02-27, last push 2026-02-28, **0★** | MIT | Docs ❌ · Sheets ✅ **plain CSV in git** · Slides ❌ | The **only** git-backed CSV spreadsheet found. Abandoned after one day. Proof the Sheets leg is buildable and unclaimed |
| **Tachiko Work** (§7.2) | Rust/git/AI-native workspace for documents, spreadsheets and computation | **ACTIVE pre-alpha**, pushed 2026-08-28, 0★ | Apache-2.0 | Docs (projection) · Sheets ✅ typed model + formulas · Slides ❌ | The one active project that could beat this to a suite — but it **rejects plain files** for a typed semantic model. Opposite bet |
| **md4lp** (§7.2) | Byte-exact WYSIWYG↔git, ephemeral edit branches, comments anchored to text, agents-as-editors over MCP | **DEAD** — one-day burst 2026-07-04; md4lp.com TLS-fails | Apache-2.0 | Docs ✅ · Sheets ❌ · Slides ❌ | Dead, but **the deepest technical prior art on the hard problems.** Read its README before designing the editor |
| **MarkdownOffice** (§7.2) | A Substack whitepaper stating this project's exact thesis | **VAPORWARE** — posted 2025-12-27, org repos empty | proposes open-core | claims all three | The pitch is already public. Nobody has executed it |

---

## 1. Pithy — `pithy.md`

### 1.1 The password gate is cosmetic

`GET https://pithy.md` → **HTTP 200** (Cloudflare, `cf-ray: a3241d896dddebb9-YYZ`). The page renders a "This site is in private alpha / Enter the password to continue" gate, but **the entire marketing site ships in the same HTML response** and the gate is pure client-side CSS `display` toggling. The password is hardcoded in an inline `<script>`:

```js
var HASH = '8f14e45fceea167a5a36dedd4bea2543'; // md5 of 'samepage'
...
if (val === 'samepage') { sessionStorage.setItem('pithy_alpha','granted'); ... }
```

So the "private alpha" is not private at all. **VERIFIED.**

### 1.2 Positioning (verbatim from the page)

- `<title>`: *"Pithy — Git-backed markdown and CSV editor for AI-forward teams"*
- Hero: *"Write together. You, your team, and your AI agents — finally on the same page."*
- *"A beautiful markdown editor where your docs are files on GitHub that your whole team — humans & AI — can read, write, and comment on."*
- *"Your docs are files in git. Everything else follows."*
- Explicit FAQ entries positioning against **Notion** ("proprietary database") and **Google Docs** ("requires a browser, an internet connection, and a Google account… not a simplified 'version history' you can't diff or branch").
- *"Spreadsheets, not just docs — CSV files open in an editable spreadsheet grid… Toggle to source view to see the raw CSV."*

This is essentially the same thesis as the git-backed-GWS idea, minus slides.

### 1.3 Pricing (published, VERIFIED)

| Tier | Price | Notes |
|---|---|---|
| Free & Open Source | $0 | Local single-player desktop editor, Mac/Win/Linux, git version history, "AI agent filesystem access" |
| Team | **$7 / user / mo** | Realtime collab, inline comments, AI writing assistant, iOS+Android apps, browser editing without a local repo |
| Enterprise | Custom | SSO/SAML/SCIM, audit logs, self-hosted or BYOC, SOC 2, SLA |

### 1.4 The open-source claim does not hold up

The page says *"Pithy is open source under **AGPL-3.0**"* in the Open Source section, but the footer says *"© 2026 Pithy. Open source under **MIT**."* — an internal contradiction, which is itself a tell that the licensing was never actually settled.

More decisively:

- `GET https://api.github.com/repos/PithyDocs/pithy-app` → **HTTP 404** (`"message": "Not Found"`), confirmed with an **authenticated** token, so it is not a permissions artifact from an unauthenticated request. The repo the site links to (`https://github.com/PithyDocs/pithy-app`, linked from both "View on GitHub" and "Star on GitHub") **does not exist publicly**.
- The site's terminal mock instructs `git clone https://github.com/PithyDocs/pithy-app.git` — this would fail.

**Conclusion: Pithy has never been open source. The claim is aspirational marketing on a site nobody has read.** NOT FOUND: any public Pithy source code.

### 1.5 Everything else on the site is vaporware links

| Link on the page | Result |
|---|---|
| `https://app.pithy.md` | **DNS NXDOMAIN** — "Could not resolve host" |
| `https://docs.pithy.md` | **DNS NXDOMAIN** |
| `https://docs.pithy.md/api` (API Reference) | **DNS NXDOMAIN** |
| `https://docs.pithy.md/self-host` (Self-hosting) | **DNS NXDOMAIN** |
| `https://pithy.md/blog` | **404** |
| `https://pithy.md/changelog` | **404** |
| `https://pithy.md/about` | **404** |
| `https://pithy.md/privacy`, `/terms` | **404** |
| `https://x.com/pithymd` | **404** — the X account does not exist |
| `https://pithydocs.com` | **HTTP 522** (Cloudflare origin unreachable) |

Only three things actually exist: the landing page, the desktop binaries, and a Cloudflare Worker.

### 1.6 The binaries are real, and the app is substantial

`https://releases.pithydocs.com/desktop/latest/` itself is **404** (no directory listing), but the exact filenames from the page's JS all return **200**:

| File | Size | `last-modified` |
|---|---|---|
| `Pithy-latest-x86_64.AppImage` | 114,592,248 B (114 MB) | **Sat, 28 Mar 2026 05:15:15 GMT** |
| `Pithy-latest-aarch64.dmg` | 35,253,532 B (35 MB) | **Sat, 28 Mar 2026 05:15:14 GMT** |
| `Pithy-latest-x64-setup.exe` | 24,848,299 B (24 MB) | **Sat, 28 Mar 2026 05:15:12 GMT** |

No version-numbered paths exist (`/desktop/0.1.0/…`, `/desktop/v1/…`, `/desktop/stable/…`, `/desktop/`, `/` all → **404**), and there is no electron-builder `latest.yml` / `latest-mac.yml` / `latest-linux.yml` (**404**), i.e. **no auto-update feed and no published version history**. The download links carry a manual `?v=7` cache-buster, suggesting roughly 7 hand-rolled release iterations.

Note the Mac build is **aarch64 only** — no Intel Mac build.

### 1.7 Architecture, from disassembling the Windows installer (VERIFIED)

I downloaded `Pithy-latest-x64-setup.exe` and extracted it (`7z`; identified as `Type = Nsis`, `NSIS-3 Unicode`).

**Stack: Tauri (not Electron) + a bundled Node.js sidecar server + SQLite.**

- `$PLUGINSDIR/nsis_tauri_utils.dll` and 172 `tauri` / 45 `tao` / 24 `wry` string hits in `pithy-desktop.exe` (12.4 MB) → **Tauri v2**, Rust.
- `binaries/pithy-server-x86_64-pc-windows-msvc.exe` (**61 MB**) → a compiled **Node.js single-executable sidecar** (string hits: `nodejs`, `Node.js`, `Express`, `hono`, `Yjs`, `better-sqlite3`).
- `binaries/node_modules/better-sqlite3/…` including `build/Release/better_sqlite3.node` → local SQLite index/cache alongside the files.
- Frontend: `dist/assets/index-BzRuOYAC.js` (1.7 MB) — **React + TipTap/ProseMirror + Yjs + CodeMirror + PapaParse**. It is also shipped as a **PWA** (`manifest.json`, `sw.js`, `sw-register.js`), which is how the promised browser/mobile tier would be delivered from the same codebase.
- Sidecar env vars found in the Rust binary: `PORT`, `REPO_PATH`, `NODE_ENV`, `DIST_PATH`, `NODE_PATH`, `FEEDBACK_ENDPOINT`.
- Bundle identifier: `md.pithy`. Author string: **`Tyler Tate`**, description `Pithy desktop app`.

**Build provenance:** the PDB path embedded in the binary is
`D:\a\pithy-desktop\pithy-desktop\pithy-desktop\src-tauri`
— the `D:\a\` prefix is the **GitHub Actions Windows runner** working directory. So there is a **private** repo named `pithy-desktop` with CI, and a sibling frontend directory referenced as `../../pithy-app/dist`. Note the desktop repo is `pithy-desktop`, while the *public* link points at `pithy-app` — the frontend package. Neither is public.

**Backend:** `https://pithy-services.tyler-0de.workers.dev/api/reports` is a **Cloudflare Worker** (account handle `tyler-0de`). `GET /` → **HTTP 404 with a JSON body** and CORS headers `access-control-allow-methods: POST, OPTIONS` — i.e. the Worker is **still deployed and running today**, it just only accepts POSTs. This is the crash/feedback reporting endpoint.

### 1.8 Feature surface, extracted from the shipped JS bundle (VERIFIED)

REST routes the client calls:

```
/api/auth/github
{base}/files, {base}/files/{path}, {base}/files/favorites, {base}/files/recent/view,
  {base}/files/recent/viewed, {base}/files/reveal
{base}/comments, {base}/comments/{id}
{base}/git/status   {base}/git/commit   {base}/git/push    {base}/git/pull
{base}/git/branches {base}/git/checkout {base}/git/discard {base}/git/init
{base}/git/history/{path}  {base}/git/show/{ref}/{path}
{base}/repo-settings
{base}/collab/{workspace}
```

UI strings recovered from the bundle show how finished it is:

> "Git-backed markdown for teams" · "Sign in to GitHub" · "Continue with GitHub" · "Your repositories" · "No repositories found" · "Open a remote repo" · "Repository URL" · "Failed to clone repository" · "Initialize repo" · "Uncommitted changes" · "Committed, not yet pushed" · "Commit changes" · "Commit to branch" · "Commit directly to current branch" · "Don't commit yet" · "Create new branch" · "Branch off the current branch" · "New branch with pull request" · "Your changes aren't on a branch" · "View on GitHub" / "Show on GitHub" · "New spreadsheet" · "Create a blank CSV file" · "No comments yet" · "Select text and click the comment icon to add one" · "Set up AI to get started" · "Add model provider API key" · "Enter a model ID instead"

**File formats handled:** `.md`, `.markdown`, `.mdx`, `.csv` — and nothing else. Grepping for slide libraries found **no reveal.js, no Marp, no Slidev**; every `Reveal` hit in the bundle is either a React fiber internal (`revealOrder`, `tailMode`) or the `revealFile` / "reveal in file manager" action. **Pithy has no slides support of any kind.** This is the single clearest gap versus a full git-backed Workspace.

The AI story is BYO-key ("Add model provider API key", "Enter model ID") plus filesystem access for external agents — it does not ship its own model.

### 1.9 Who is behind it

- GitHub org `PithyDocs` (`GET /orgs/PithyDocs` → **200**): id **32466681**, name "Pithy", blog `https://pithydocs.com`, location **"San Francisco Bay Area"**, `created_at` **2017-10-02**, `updated_at` **2026-03-24**, 4 public repos, **0 followers**, not verified.
- The org is **recycled**: its old repos are `seriously-website` ("GetSeriously.com", last pushed 2017-10-18), `seriously-api` (2017-10-14), and `tylertate` ("My website", first commit 2011-03-28). It was clearly an old *Seriously* org renamed to **PithyDocs around 2026-03-24**. That renaming date is the effective birth of the project's public identity.
- `GET /orgs/PithyDocs/public_members` → empty array. No public members.
- **The person is Tyler Tate.** `GET /users/tylertate` → **200**: name "Tyler Tate", company `@CremaCo`, blog `http://www.tylertate.com/`, location **"Mountain View, California"**, account created 2010-01-22, 31 followers, `updated_at` 2026-08-11.
- Corroborating commit metadata in `PithyDocs/summit-robotics-docs`: the initial commit is authored by **`Tyler Tate <tyler@Tylers-MacBook-Pro.local>`**.
- Corroborating binary metadata: Tauri author field = `Tyler Tate`; Cloudflare Workers subdomain = `tyler-0de`.

**Background (VERIFIED from `http://www.tylertate.com`, HTTP 200):** *"Hi, I'm Tyler, currently a product leader at **Instacart**. Previously I was co-founder and CEO of **Crema.co** (a coffee marketplace), co-founder at **Twigkit** (enterprise search), lead designer at **Nutshell** (SaaS CRM), and co-author of *Designing the Search Experience*. I live and work in the San Francisco Bay Area."*

So: an experienced product/design leader with a full-time job, building this solo on the side. (One lead-generation site claimed he is at Perplexity — **that is REPORTED and contradicted by his own site**, which says Instacart. Treat the Perplexity claim as false/stale.)

### 1.10 The demo repo is a goldmine of behavioural evidence

`PithyDocs/summit-robotics-docs` (`created_at` **2026-03-20**, `pushed_at` **2026-03-30**, 0 stars) is a **fictional company's docs tree** used as a demo/fixture — "Summit Robotics", Everest/Khumbu expedition robots. Structure:

```
README.md
engineering/{architecture,postmortems,rfcs,runbooks}/*.md
finance/{2026-budget.md, series-c-summary.md}
legal/*.md
operations/{field-ops,maintenance,safety,supply-chain}/
people/{onboarding,culture,team-structure.md}
product/{k1-summit-spec.md, roadmap-2026.md, sdk-overview.md, vision.md}
assets/.gitkeep
```

Two things matter here:

1. **It is 100% `.md`. There is not a single `.csv` file** in the whole demo, despite CSV spreadsheets being a headline feature. The spreadsheet story is real in code but was not worth demoing.
2. **The commit log reveals Pithy's auto-commit identity and message format:**

```
2026-03-30T18:01:14Z | Local User <local@pithy.md> | Update product/roadmap-2026.md — 3/30/2026, 2:01:14 PM
2026-03-30T17:57:21Z | Local User <local@pithy.md> | Updating roadmap-2026.md
2026-03-20T21:45:50Z | Local User <local@pithy.md> | Updating vision.md
2026-03-20T21:31:10Z | Local User <local@pithy.md> | Adding vision.md
2026-03-20T21:28:20Z | Tyler Tate <tyler@Tylers-MacBook-Pro.local> | Initial commit: Summit Robotics internal docs
```

The app commits as a generic `Local User <local@pithy.md>` with a machine-generated `Update <path> — <locale timestamp>` message. That is a **known weak point worth beating**: it destroys authorship attribution in the git history, which is the main thing a git-backed drive is supposed to buy you over a proprietary version history. It also means multi-author repos get a useless `git blame`.

### 1.11 Liveness verdict: dormant, probably dead

| Signal | Evidence |
|---|---|
| Wayback Machine | `http://archive.org/wayback/available?url=pithy.md` → `{"archived_snapshots": {}}`. CDX query for `pithy.md` → `[]`. **Zero snapshots, ever.** |
| Wayback for `pithydocs.com` | Exactly **one** snapshot, `20141017050025` — a decade before this project. The domain is old and unrelated to the current effort. |
| Hacker News | `hn.algolia.com/api/v1/search?query=pithy.md` → **nbHits 0**. `query=pithydocs` → 1 hit, an unrelated 2018 article. **Never posted to HN.** |
| Web search | No results for Pithy-as-git-backed-editor at all. |
| Social | `x.com/pithymd` → 404. Org has 0 followers. |
| Last build | 2026-03-28 |
| Last demo-repo commit | 2026-03-30 |
| Backend | Cloudflare Worker still deployed (a Worker costs nothing to leave running) |

**Verdict:** Pithy is a well-built, ~5-month-stale, never-launched solo side project. It got as far as shipping cross-platform binaries and a polished marketing site, then stopped — no launch post, no HN, no social account, no public repo, no docs site. The infrastructure that still runs (landing page, R2/CDN binaries, Worker) is all zero-maintenance. The parts that require ongoing effort (docs, app, changelog) were never built or have been torn down.

### 1.12 Strategic read on Pithy

This is the closest thing to a direct competitor found, and the important lesson is **not** that the space is taken — it's that **someone with strong product credentials validated the same thesis, built it to a high standard, and it went nowhere for lack of distribution, not lack of product.** Specific takeaways:

- **Slides are genuinely unoccupied.** Pithy deliberately scoped to docs + sheets. Markdown-with-`---` slides is a differentiator no direct competitor here has.
- **The auto-commit identity problem is unsolved.** `Local User <local@pithy.md>` is a bad answer. Per-author commits (or at minimum author trailers) is a cheap, visible win.
- **The formula sidecar is unoccupied.** Pithy's CSV support is a plain PapaParse grid — cells only, no formulas. A CSV + formula-sidecar design is beyond anything shipped here.
- **"Open source" as a claim without a repo is a trust liability.** Pithy links a 404 from two separate CTAs. Actually shipping the repo is a low-cost credibility advantage.
- Tauri + Node sidecar + better-sqlite3 + TipTap/Yjs is a validated architecture for this exact product, if that's useful as a reference build.

**Sources (all fetched, all 200 unless noted):**
`https://pithy.md` · `https://releases.pithydocs.com/desktop/latest/Pithy-latest-x64-setup.exe` (and `.dmg`, `.AppImage`) · `https://api.github.com/orgs/PithyDocs` · `https://api.github.com/orgs/PithyDocs/repos` · `https://api.github.com/repos/PithyDocs/summit-robotics-docs/git/trees/main?recursive=1` · `https://api.github.com/repos/PithyDocs/summit-robotics-docs/commits` · `https://api.github.com/users/tylertate` · `http://www.tylertate.com` · `http://archive.org/wayback/available?url=pithy.md` · `https://web.archive.org/cdx/search/cdx?url=pithydocs.com*&output=json` · `https://hn.algolia.com/api/v1/search?query=pithy.md`
404/522/NXDOMAIN observed at: `https://api.github.com/repos/PithyDocs/pithy-app` (404) · `https://pithydocs.com` (522) · `https://x.com/pithymd` (404) · `app.pithy.md`, `docs.pithy.md` (NXDOMAIN)

---

## 2. Perchpad — `perchpad.co`

### 2.1 The Show HN

**HN item 46919903** — *"Show HN: Perchpad – Collaborative real-time Markdown editor backed by Git"*, by **`halotrope`**, posted **2026-02-07T00:08:45Z**.

**Traction: 2 points, 2 comments.** It sank without trace. (VERIFIED via `https://hacker-news.firebaseio.com/v0/item/46919903.json` and `https://hn.algolia.com/api/v1/search?query=perchpad`.)

The author's pitch, verbatim:

> "I've wanted something like this for a long time and finally built it **over the weekend** after seeing a tweeet about LLM memory. Perchpad is a collaborative real-time Markdown editor where your workspace is just a folder of flat .md and .csv files, version-controlled with Git.
> — Git-native storage, your workspace is plain files. git clone them, download as zip, or just edit locally. No proprietary format lock-in.
> — Deep LLM support. hook it up to Claude as persistent memory/context…
> — Web based real-time multiplayer – full collaborative editing, multiple cursors, the usual.
> — Text-to-speech longform read-aloud with decent voice options.
> The idea is that your notes and docs should be portable plain text first, collaborative second, and AI-augmented third — not the other way around."

### 2.2 The entire discussion (both comments)

There were exactly two comments, and this is the whole thread:

> **chux52** (2026-02-07T00:59:27Z): *"How does the git part work if you are always fighting github authentication. It's git only, not github?"*
>
> **halotrope** (2026-02-07T21:19:09Z): *"no you can give github oauth access to a repo and then it will sync automatically."*

Worth noting: the author's answer describes GitHub OAuth sync — but the live site lists **"GitHub Sync — Auto-sync to private GitHub repos"** under **"Coming Soon"**. So either the reply overstated what shipped, or the feature was subsequently pulled. Either way, **as of today the git repo lives on Perchpad's servers, not in a GitHub repo you own.** That is a meaningful architectural difference from the local-first thesis.

### 2.3 Who built it

`halotrope` — HN account created 2015-04-20, karma 1525. His HN bio (VERIFIED): *"co-founder of https://markets.sh/ — twitter: @markets_sh"*. 44 story submissions since 2015; Perchpad is his lowest-scoring Show HN by a wide margin (his best was *"Show HN: Webhooks for Any Event"* at 56 points in 2024). Self-described weekend build; a later comment of his (2026-03-18) reads *"idk it works for me it build stuff that would have taken weeks in hours ymmv"* — consistent with heavy AI-assisted development.

### 2.4 What it actually is (from the live site, HTTP 200)

Hosted on **Fly.io** (`server: Fly/c97294087`). Positioning: *"A writing workspace that thinks with you"* — a "calm" workspace with a **cartoon bird AI assistant**. Notably, the consumer-friendly bird framing has replaced the developer-first "git-backed" framing that led the Show HN title.

Feature claims, verbatim:

- **Plain Flat Files** — *"Your project is just files on disk — markdown, CSV, whatever you need. No database, no proprietary format, no lock-in."*
- **Git Built In** — *"Every workspace is a real git repo. Clone it, push to it, pull from it — standard commands just work."*
- **Version control:** *"Changes **auto-commit every 60 seconds**. You can `git clone`, `git push`, and `git pull` with standard tools."* (Same auto-commit pattern as Pithy — and the same likely authorship problem.)
- **Formats:** *"Markdown (.md) with live preview, and CSV (.csv) rendered as editable tables with sticky headers."* — **docs + sheets, no slides.**
- **MCP server** for Claude Desktop / Cursor.
- **Email-to-workspace**, configured with an `AGENTS.md` file.
- Roles: owners / editors / viewers. Public share links.
- Read-aloud TTS; document "playlists" for reading/research.
- **Coming Soon (i.e. NOT shipped):** GitHub Sync, Webhooks, **Excel (.xlsx) support**, PDF support.

### 2.5 Pricing: NOT FOUND

There is **no published pricing**. `https://perchpad.co/pricing`, `/docs`, `/blog`, `/changelog`, `/about`, `/terms`, `/privacy`, `/signup`, `/register` all return **HTTP 200 but serve an identical 2,546-byte stub** containing only the title *"Perchpad — A collaborative writing workspace"* — i.e. a catch-all that returns 200 for everything. The real landing page is 27,189 bytes. The only real routes are `/`, `/login`, `/contact`, and `/projects` (the app).

### 2.6 Liveness

| Signal | Evidence |
|---|---|
| Site up | **HTTP 200**, served from Fly.io, today |
| Last deploy | The stylesheet is versioned `?v=registry.fly.io/perchpad:deployment-01KNER6Z7ND9NZKRNQ2Z40KSGM`. Decoding that ULID's timestamp gives **2026-04-05T11:59:51Z** — the last deployment was ~5 months ago |
| Wayback | CDX for `perchpad.co` → `[]`. **Zero snapshots.** |
| HN | One Show HN, 2 points, 2 comments, nothing since |
| Social | `https://x.com/perchpad` returns 200, but that is X's generic SPA shell and is not evidence the account has content |

**Verdict:** alive in the sense that it's still running, but **dormant** — last deployed 2026-04-05, no pricing, no docs, no marketing, effectively zero users. A solo weekend project that its author moved on from.

### 2.7 Strategic read on Perchpad

- It is the **cloud-first mirror image** of the idea: the git repo is a server-side artifact you may clone, not a folder on your disk you already own. It concedes the local-first property entirely.
- It independently confirms the docs (.md) + sheets (.csv) pairing as the natural minimum viable scope — **and again, no slides.**
- The `AGENTS.md`-configured email-to-workspace ingestion is a genuinely novel idea worth noting.
- The HN result (2 points) is a useful calibration: **"git-backed markdown editor" as a headline does not get attention on its own.** Both direct competitors that reached the public got either no launch (Pithy) or an ignored one (Perchpad). Distribution, not the concept, is the binding constraint in this category.

**Sources (all fetched):**
`https://perchpad.co` (200) · `https://perchpad.co/pricing` (200, stub) · `https://hacker-news.firebaseio.com/v0/item/46919903.json` · `.../item/46920208.json` · `.../item/46927489.json` · `https://hacker-news.firebaseio.com/v0/user/halotrope.json` · `https://hn.algolia.com/api/v1/search?query=perchpad` · `https://web.archive.org/cdx/search/cdx?url=perchpad.co&output=json`

---
## 3. Moment — `moment.dev`

> **Real, live, technically serious, and the best-funded-looking effort in the direct set.** ~7-person Seattle company. Genuinely git-backed for local/solo use — but **the moment you share or publish, the source of truth moves to Moment's own git server**, not a repo you own. That gap is the clearest opening against them.

### 3.1 Site and positioning — VERIFIED

`moment.dev` resolves (A record `216.150.1.1`), **HTTP 200**, redirects to `https://www.moment.dev/`.

Subpage sweep: `/` **200** · `/pricing` **200** · `/docs` **200** · `/blog` **200** · `/templates` **200** · `/login` **200** · `/about` **404** · `/changelog` **404** · `/careers` **404** · `/jobs` **404** · `/signup` **404** · `/security` **404** · `/enterprise` **404**.

Headline, verbatim: **"RUN YOUR ENTIRE BUSINESS OUT OF A MARKDOWN FILE."**
Positioning: *"a collaborative, Markdown-based workspace for agents and humans to build personalized software together… It is backed by [[jj]] and [[git]]."*
Third marketed pillar, verbatim: **"REAL MARKDOWN FILES. STORED ON DISK. IN JJ (GIT) REPOS."**
Footer: **© 2026 Moment, Inc.**

### 3.2 The git-backed question — the most important finding on Moment

It is **not** fake internal versioning. But it is also **not** "syncs to your GitHub repo."

From `https://www.moment.dev/docs/how-moment-works` (200):

> *"When you create a new document, it exists entirely on your local machine as a collection of Markdown files in a Git repository… **At this stage, Git is the sole source of truth.**"*
> *"Once you're ready to share… Moment leverages Reboot to make the document collaborative in real time. When a document is shared: **The central server becomes the source of truth.** Reboot manages a `collab/main` branch that represents the live, canonical state."*

From `https://www.moment.dev/docs/publishing` (200):

> *"publishing is essentially… committing outstanding changes, and **pushing those changes to a remote at `git.moment.dev`**."*
> *"**Moment currently supports logging in only with GitHub.** If you do not have a GitHub account, you will be unable to publish."*

So:

- **Local / solo = fully real git.** `/docs/committing-changes` (200) documents a real commit UI with A/M/D/R/!/T/? file statuses, real `git diff` output, branch visualization, commit history.
- **Shared / published = Moment-hosted.** The remote is `git.moment.dev` (**HTTP 401**, auth-gated). GitHub is used for **OAuth login only**. No documentation was found anywhere stating that Moment pushes to a user-owned GitHub/GitLab remote.
- **Import works both ways:** dropping a `moment.yml` in an existing git repo root turns it into a collaborative doc (`/blog/changelog-0006`, 2025-12-12) — with explicit caveats: beta, *"very likely to run into bugs,"* poor inline-HTML support, breaks down on repos with thousands of `.md` files. Branching + conflict merge added in changelog-0007 (2025-12-19).
- **The VCS layer is Jujutsu (jj) over git**, not git plumbing directly — confirmed on the landing page, in the Show HN text (*"ok, technically in jj"*), and in a founder HN comment about attaching assets to "jj change IDs."
- **Self-hosting: NOT FOUND.** No mention in any docs page fetched. The Enterprise tier lists SSO/SAML, SLA, custom integrations — **no on-prem**, despite courting infra/platform/SRE buyers who normally demand it.

### 3.3 Feature set — **docs only. No sheets. No slides.**

Desktop app on all three platforms; manifest live at `https://git.moment.dev/public/v1/desktopapp/download` (**200**): macOS aarch64 + x64 `.dmg`, Linux `.AppImage`/`.deb`/`.rpm`, Windows `x64-setup.exe`. Current build **`0.3.706+2272`** — note the binary is still **0.3.x** while the marketing says "v1.5". Installer download verified live (**HTTP 200**, `application/x-apple-diskimage`).

Shipped: live collaborative editing; embedded terminal with an agent picker (zsh, Claude Code, Amp, Codex, Copilot, Gemini); reactive JS/React/Tailwind code cells; HTTP/gRPC/Postgres/SQLite request pages; `.env` secrets via a Rust proxy (`{{env.X}}`); wikilinks; cron "Workflows" (shell or AI agent on a schedule); import from folder (Obsidian vault / `docs/`); CSV + SQLite **attachments**; daily notes; publish-to-web with templates; branches + merge conflict UI. Template gallery includes an NES emulator, a SQLite browser, a GitHub PR dashboard, a K8s pod dashboard, an AWS Cost & Usage explorer.

Note the shape: CSV appears only as an *attachment* to a document and as a data source for code cells — **there is no spreadsheet application.** The "sheets" need is answered with executable code cells instead of a grid.

### 3.4 Pricing — VERIFIED (`https://www.moment.dev/pricing`, 200)

| Tier | Price | Notes |
|---|---|---|
| Free | $0 forever | 1 user, unlimited docs/apps, git-backed storage, live rendering, executable blocks |
| **Team** | **$30/mo for up to 5 users, then +$6/user/mo** | Real-time collab, access controls, priority support |
| Enterprise | Custom | 50+ users, SSO/SAML, SLA, custom integrations |

(Compare: Pithy's stated $7/user/mo. Moment's effective per-seat price at 5 users is $6.)

### 3.5 Team and company

- **Alex Clemmer** — CEO/co-founder. X `@hausdorff_space`, HN `antics`, email `alex@moment.dev` (posted publicly by him on HN). VERIFIED as author of the blog posts and the Show HN.
- **Lita Cho** — CTO/co-founder. HN `litacho1`, email `lita@moment.dev`.
- **LinkedIn company page** `/company/moment-technologies-inc` (**200**): *"Moment · Software Development · **Seattle, WA** · 276 followers · **7 employees**."* VERIFIED.
- Entity name drifts: **"Moment Technologies, Inc."** (2025 footers) → **"Moment, Inc."** (2026 footers and ToS). `https://legal.moment.dev` (**200**): ToS effective 2023-06-13, last updated **2026-03-17**.
- GitHub org **`moment-eng`** (`api.github.com`, **200**): created 2019-11-24, 20 public repos, 13 followers, **0 public members**, description still carries the *old* pitch: *"A programmable workspace for infrastructure developers, platform engineers, and SREs."*

⚠️ **Name-collision warning for any further research:** there is a *different* "Moment, Inc." — a camera-gear marketplace, founded 2014, **also headquartered in Seattle**, ~49 employees. Crunchbase/Tracxn/BuiltIn queries for "Moment" return **that** company. Do not trust aggregator data on this name.

### 3.6 Funding — NOT FOUND

- **SEC EDGAR full-text search** for `"Moment Technologies"` → **0 hits**, all forms (`efts.sec.gov`, 200). No Form D indexed.
- **No YC batch found.**
- Crunchbase (**403**), Wellfound (**403**), AlternativeTo (**403**), PitchBook — all bot-blocked; nothing verified.
- ⚠️ The frequently-cited **"$56M–$61M, Lightspeed/Venrock/Contrary"** figures belong to a **different Moment** — a fixed-income/bond-investing API fintech. **Not this company.** Do not repeat those numbers.
- **Verdict: no funding, investors, or YC affiliation could be confirmed.** REPORTED-only signal: they were hiring engineering roles as of Feb 2025, and state they spend **>$10k/yr** sponsoring `react-prosemirror`.

### 3.7 History: this is a pivot, four times over — VERIFIED via Wayback

Wayback CDX shows **51 snapshots from 2021-02-05 to 2026-06-08**:

| Snapshot | Positioning |
|---|---|
| 2021-04-18 | *"Automate Infrastructure Workflows — Infrastructure-aware notebooks that reduce support burden on platform and SRE teams."* Waitlist. |
| 2022-12-05 | *"The fastest way to turn infrastructure into a self-serve platform… interactive docs and runbooks, service catalogs, internal ops tools."* |
| 2023-11-17 | *"Docs that are Apps — Centralize infrastructure expertise."* |
| **2024-11-06** | *"A modern docs platform, based on Markdown."* ← **the pivot** |
| 2025-06-13 → 2025-11-01 | *"Docs, reimagined for developers… Markdown files stored locally in git repositories on your device."* |
| 2026 (current) | *"Run your entire business out of a Markdown file"* — agent-centric framing |

Their own blog confirms: *"In the second half of 2024 we set out to build a high-performance, collaborative… document editor."* So: **a 2019-era SRE runbook/notebook startup that pivoted in late 2024 to Markdown+git, then re-angled again in 2026 to an AI-agent workspace.** Stale artifacts of the old identity are still live — `docs.moment.dev/humans.txt` (**200**) still reads *"designing software for infrastructure engineers… Visit https://www.moment.dev/jobs"*, and that URL is now **404**.

### 3.8 Liveness — shipping hard through May 2026, then ~4 months quiet

| Signal | Last activity | Age (at 2026-08-28) |
|---|---|---|
| Blog (RSS, 17 items, **200**) | **2026-05-01** — "Moment v1.5" | ~4 months |
| Bluesky `@moment.dev` (public API, **200**) | **2026-03-03** — v1 launch thread | ~6 months |
| GitHub org metadata | `updated_at` 2026-08-04 | recent |
| GitHub repos (most recent push) | `example-data` 2026-03-24 | ~5 months |
| Wayback last capture | 2026-06-08 | ~3 months |
| Download manifest + installer | **live, 200** | current |
| X `@moment_dev` / `@hausdorff_space` | **NOT FOUND** — syndication endpoints returned 429 then empty; could not verify | — |

Blog cadence was near-weekly Nov 2025 → Mar 2026, then a single post on May 1, then nothing. Bluesky has only **35 posts / 59 followers**, silent since March. **No affirmative evidence of abandonment**, but the public cadence has clearly dropped off since May. Worth re-checking in 30–60 days.

### 3.9 Reception — the engineering brand is far stronger than the product

**Show HN (2026-03-03): "We want to displace Notion with collaborative Markdown files"** — `https://news.ycombinator.com/item?id=47236374` — **29 points, 14 comments.** That is the *highest-scoring launch in the entire direct competitive set*, and it is still weak. Criticisms, verbatim:

- *"I'm not understanding the value here… what does this provide my team that git does not? I can easily write the markdown docs and they will render fine in most git forges."*
- *"The problem with the mission statement mentioning Notion is that notion is too big of a product and you are probably only aiming to displace a small part of it."*
- No server-spin-up for zero-setup guest collaboration ⇒ not really a Notion replacement.
- Scope confusion: *"I got confused with the Postman capabilities… Why would I reach for that instead of Claude Code building a dashboard with HTML/CSS/JS?"* (Lita's answer: collab + publishing; *"Claude Code is great for single-player, but it breaks down when you want to share."*)
- *"So Retool but for using agents."*

**But their blog is a genuine distribution engine:**

- *"Lies I was told about collaborative editing, Part 1"* (2024-12-06): **352 points, 122 comments** — `https://news.ycombinator.com/item?id=42343953`
- *"Part 2: Why we don't use Yjs"* (2026-03-13): **272 points, 160 comments** — `https://news.ycombinator.com/item?id=47359712`

Sentiment there is strongly positive and deeply technical (CRDT vs OT; Loro/Automerge/Yjs; `josephg`, author of ShareJS, engaged directly). **Almost none of that discussion is about the product** — it is about the algorithms.

Reddit: **NOT FOUND.** Product Hunt launch: **NOT FOUND.** Lobsters: **NOT FOUND.**

### 3.10 Strategic read on Moment

**Strengths:** a from-scratch collaboration engine (lightweight OT, explicitly *not* Yjs/CRDT), jj-over-git storage, real local files, embedded agent terminal, a credential-isolating Rust proxy, and a cross-platform desktop app that actually ships. The strongest technical brand of anyone in this set.

**Openings against them:**

1. **The "your own git repo" gap is the soft spot.** Local git is real, but collaboration and publishing route through `git.moment.dev`, with GitHub-OAuth-only login. **Anyone offering true sync-to-your-own-remote attacks the exact promise their marketing leans on** — and their own most-upvoted HN critic already asked *"what does this provide my team that git does not?"*
2. **No self-hosting, no on-prem.**
3. **No sheets, no slides.** CSV is an attachment, not an application.
4. **Positioning instability** — four repositions in five years, with stale old-identity artifacts still live on their own properties.
5. **Weak commercial traction** — 29-point Show HN, 59 Bluesky followers, 276 LinkedIn followers, ~7 people, no verifiable funding, binary still 0.3.x.
6. **Scope sprawl** from a 7-person team: docs + Postman client + Retool-style internal tools + cron workflows + wiki + publishing. The most common HN critique was literally *"I don't understand what this is."*

**Sources (all fetched):** `https://www.moment.dev/` · `/pricing` · `/templates` · `/docs/how-moment-works` · `/docs/publishing` · `/docs/committing-changes` · `/blog/changelog-0006` · `/blog/changelog-0007` · `https://git.moment.dev/public/v1/desktopapp/download` · `https://legal.moment.dev` · `https://api.github.com/orgs/moment-eng` · `https://efts.sec.gov` full-text search · Wayback CDX for `moment.dev` · HN items 47236374, 42343953, 47359712

---

## 4. Nimbalyst — `github.com/nimbalyst/nimbalyst`

> **This is the most serious competitor found, and it was under-weighted in the original brief.** It is the only product in this research that ships **docs + sheets + slides, all as plain files, with real git integration**. It is actively developed with same-day commits.

### 4.1 Repo facts — VERIFIED (`GET https://api.github.com/repos/nimbalyst/nimbalyst` → **HTTP 200**)

| Field | Value |
|---|---|
| Stars / forks | **1,594 / 231** |
| License | **MIT** |
| created_at | **2025-10-30T21:28:59Z** |
| pushed_at | **2026-08-28T06:53:52Z** (same day as this research) |
| Default branch / language | `main` / TypeScript (38.1 MB TS, 938 KB Swift, 398 KB Kotlin) |
| Homepage | `https://nimbalyst.com/` (HTTP 200) |
| Archived | **false** |
| Topics | agentic-ai, claude-code, codex, opencode, electron, kanban, markdown-editor, mcp, worktree-manager, wysiwyg-editor, … |

Self-description: *"The open-source visual workspace for Claude Code, Codex, and OpenCode. Run multiple coding agents in parallel, edit their work visually in markdown, mockups, and diagrams, and track tasks. Free, MIT-licensed desktop app for macOS, Windows, Linux, with mobile companion for iOS and Android."*

Issues/PRs (search API): **505 open issues, 533 closed; 74 open PRs, 213 merged.**

### 4.2 Activity — VERIFIED

- **~5,779 commits** on `main` in ~10 months.
- **421 commits in the last 30 days; 1,169 in the last 90.**
- Latest commits on 2026-08-28: `Release v0.75.4`, `fix: complete Codex web search tool cards (#1386)`.
- **38 contributors.** Top: `ghinkle` (Greg Hinkle) **4,208**, `jordan-BAIC` 1,279, then a long tail.
- **Bus factor 1:** in the last 90 days `ghinkle` wrote **1,041 of ~1,169 commits (89%)**. The #2 all-time contributor's last commit was **2026-04-02** — gone ~5 months.
- Heavily agent-authored (repo root has `CLAUDE.md`, `AGENTS.md`, `.claude/{agents,commands,rules}/`, and a file named `agent-mistakes.md`), but backed by real `__tests__`, Playwright + Vitest configs, CI, DCO sign-off and a signed release pipeline. This is an engineering operation, not a weekend build.

### 4.3 Releases — VERIFIED

- **96 releases.** First `v0.45.25` (2025-11-14) → latest **`v0.75.4` (2026-08-28T07:27:29Z)**. Cadence: every 1–3 days.
- **44 stable / 52 prerelease** — explicit stable + alpha release channels, user-selectable in Settings.
- **19 assets per release**, real signed binaries: `Nimbalyst-macOS-arm64.dmg`, `-macOS-x64.dmg`, `Nimbalyst-Windows-x64.exe`, `-Windows-arm64.exe`, `Nimbalyst-Linux.AppImage`, plus electron-updater `latest*.yml`/`alpha*.yml` manifests.
- **Total asset downloads across all releases: 5,695,026.** ⚠️ *Caveat:* the `.yml` update manifests are counted as assets and are polled continuously by electron-updater, so this figure is materially inflated. The binary subset was not separated out. Treat as "real but unknown-magnitude adoption."

### 4.4 Architecture — VERIFIED

**Electron.** TypeScript monorepo on npm workspaces (`nimbalyst-monorepo`). Workspaces include `packages/electron`, `packages/runtime`, `packages/ios` (SwiftUI), `packages/android` (Kotlin), `packages/cli`, `packages/extension-sdk`, `packages/extensions/*`, `packages/collab-{protocol,client,bundle,adapters}`, `packages/marketplace`, `packages/browser-extension`, `packages/opencode-plugin`.

Editor tech: **Lexical ^0.44** (incl. `@lexical/yjs`) for WYSIWYG, **Monaco ^0.55.1** for code, `electron-builder ^26`.

**On-disk storage: plain files in your own git repo.** No proprietary container. File patterns registered by extensions:

| Format | Editor |
|---|---|
| `.md` | Markdown WYSIWYG (core) |
| `.csv`, `.tsv` | CSV Spreadsheet extension |
| `.calc.md` | Calc Sheets (line-oriented worksheets with units) |
| **`.slides.md`** | **Slides (reveal.js)** |
| `.excalidraw` | Excalidraw |
| `.mockup.html` | MockupLM |
| `.prisma` | DatamodelLM |
| `.anim.json` | Animation |
| `.db`/`.sqlite` | SQLite browser |
| JSON Canvas | Project Canvas |

**Git integration is real and shells out to the `git` binary** — VERIFIED three ways:
1. `packages/electron/package.json` depends on **`simple-git@^3.36.0`** (the only git dep in the monorepo — no isomorphic-git, no libgit2/nodegit).
2. `packages/electron/src/main/services/GitStatusService.ts` imports `execFile, execSync` from `child_process` and runs `execFile('git', ['--no-optional-locks','status','--porcelain'], …)`.
3. `docs/GIT_INTEGRATION.md` (HTTP 200) documents an event-driven design: a **`GitRefWatcher`** (Chokidar) watches `.git/refs/heads/<branch>` and `.git/index` to detect commits and staging changes **from any source** — their UI, the CLI, VS Code — invalidates a 5s cache in `GitStatusService`, and emits `git:status-changed` / `git:commit-detected` IPC events. The doc states **"NO POLLING — removed as of 2026-01-23."**

There are ~20 further git service files: `GitWorktreeService.ts`, `GitCommitService.ts`, `GitOperationLock.ts`, `GitCatFileBatch.ts`, `gitCommitProposalPromptUtils.ts` (**AI-drafted commit messages**), plus GitHub issue adoption/overlay services.

> **Note the contrast with Pithy and Perchpad:** Nimbalyst does *not* auto-commit behind your back with a generic identity. It watches the real repo, coexists with your CLI, and proposes commit messages. That is the better design, and it is already shipped.

### 4.5 Slides: the extension is REAL and ships — but its source is private

This took three steps to establish:

- It is **NOT** in `packages/extensions/` (28 dirs, no `slides`).
- `packages/marketplace/release-extensions.txt` lists it as an **out-of-tree sibling repo**: `../../../nimbalyst-slides|skip-build`.
- `github.com/nimbalyst/nimbalyst-slides` → **HTTP 404 even authenticated**, and absent from `orgs/nimbalyst/repos?type=all`. **Slides source is NOT public.**
- But the shipped artifact is confirmed: `GET https://extensions.nimbalyst.com/registry` → **HTTP 200**, 37,079 bytes, `generatedAt: 2026-08-28T04:59:34Z`, containing **`com.nimbalyst.slides` / "Nimbalyst Slides" / v1.0.3 / "Presentation editor with live reveal.js preview"**, tags `slides, presentation, reveal.js, markdown, deck, speaker-notes`.
- **The on-disk format is exactly the one proposed in this project's thesis.** An in-tree sample, `design/transcript-embed-samples/launch.slides.md` (HTTP 200, 402 B), is YAML frontmatter (`theme: black`, `transition: slide`) plus **`---`-separated markdown slides**.

**This is the single most important finding in the report: the "markdown with `---` separators = slides" idea is already shipping in a 1,594-star product.**

### 4.6 Full extension marketplace (26 extensions, VERIFIED from the live registry)

animation, astro, automations, browser, calc-sheets, canvas (Project Canvas), csv-spreadsheet, datamodellm, developer, electronics, excalidraw, git, github-issues-importer, image-generation, ios-dev, jupyter, memory, mindmap, mockuplm, namenym, pdf-viewer, planning, playwright, replicad, **slides**, sqlite-browser.

Sheets detail: `com.nimbalyst.csv-spreadsheet` (v1.1.3 live, v1.3.0 in-tree) — *"Edit CSV files with a spreadsheet interface and **formula support**"*; changelog shows live formulas, find/replace, per-column filters, cell styling, collaborative editing. Plus `com.nimbalyst.calc-sheets` — *"Line-oriented calculation worksheets with units, formulas, and live result gutters"* (`.calc.md`).

> **The formula-on-CSV gap is narrower than assumed.** Nimbalyst's CSV extension already claims formula support. Where the formulas are persisted (sidecar vs. in-memory vs. a separate file) was not determined — **NOT VERIFIED** — and is worth a follow-up, because that is exactly the design decision at the heart of the sheets half of this project.

The marketplace is a **Cloudflare Worker + R2** (`packages/marketplace/wrangler.toml`, CDN `cdn.extensions.nimbalyst.com`). Registry reports `downloads: 0` for every extension — **treat as unpopulated telemetry, NOT as zero adoption.**

### 4.7 Not fully open source

- The collaboration sync server behind `wss://sync.nimbalyst.com` is a **separate closed project** (README says so explicitly); the repo ships only the wire protocol in `packages/collab-protocol/`.
- `nimbalyst-slides`, `nimbalyst-extension-astro`, `nimbalyst-namenym` are all **404 / private**.
- So "MIT-licensed" describes the client, not the whole system — the same shape of overclaim as Pithy, just far less egregious.

Org public repos (9): `nimbalyst` (1,594★), `product-manager-claude-code-commands` (51★), `developer-claude-code-commands` (25★), `skills` (25★), `nimbalyst-electronics` (4★), `nimbalyst-mindmap` (2★), `nimbalyst-replicad` (1★), `nimbalyst-jupyter` (0★), `wrapped` (0★).

### 4.8 Traction

`https://nimbalyst.com/` → **HTTP 200** ("Nimbalyst: Visual Editor for Claude Code & Codex (Open Source)"). `https://docs.nimbalyst.com/` → **HTTP 200**.

**HN: six submissions, all low-traction.** Best is *"Local WYSIWYG Markdown, mockup, data model editor powered by Claude Code"* (2025-12-18, **29 points, 5 comments**, id 46318191). Then 2026-04-30 Show HN (8 pts), 2026-05-12 Show HN (7 pts), 2025-11-25 (5 pts), two more at 1–3 pts. **The 1,594 stars came from somewhere other than HN.**

### 4.9 Verdict: actively developed, well-funded-looking, bus factor 1

Commits today, 421 in 30 days, 96 releases with signed cross-platform binaries and dual update channels, a real Cloudflare-hosted extension marketplace, native iOS and Android apps, 38 contributors, 213 merged PRs. Risks: 89% of recent commits from one person; **505 open vs 533 closed issues** (backlog at near-parity for a 10-month-old project); key pieces closed-source.

**Strategic read:** the framing is the differentiator, not the file formats. Nimbalyst is positioned as **an IDE-adjacent workspace for orchestrating coding agents** (worktrees, kanban, parallel agent runs, MCP) that happens to have markdown/CSV/slides editors. It is aimed at developers managing Claude Code. A "git-backed Google Workspace" aimed at **teams and non-developers** — where the docs, the sheet and the deck are the point rather than a side-panel for an agent run — is a genuinely different product to a genuinely different buyer. But the technical claim "nobody has built markdown docs + CSV sheets + `---` slides on git" is **false**, and any positioning that rests on it will not survive contact with an informed reader.

---

## 5. Eigen — `github.com/eigen-is/eigen`

> **Important correction: Eigen is NOT git-backed at all.** It is a self-hosted Google Workspace clone using SQLite + Yjs CRDTs, and its documents are proprietary SQLite-in-a-folder containers. It is a competitor on *scope* and *self-hosting*, not on the git/plain-files thesis.

### 5.1 Repo facts — VERIFIED (`GET https://api.github.com/repos/eigen-is/eigen` → **HTTP 200**)

| Field | Value |
|---|---|
| Owner type | **User**, not an org (`GET /orgs/eigen-is` → **HTTP 404**) |
| Stars / forks | **14 / 1** |
| Open issues | **0** (2 issues ever; 3 merged PRs; 0 open PRs) |
| License | **MIT** |
| created_at | **2025-03-07T13:43:13Z** |
| pushed_at | **2026-08-28T09:30:06Z** (same day) |
| Language | TypeScript (10.45 MB), plus **7.9 KB Yacc** — the spreadsheet formula grammar |
| Homepage | `https://eigen.is` (HTTP 200) |
| Topics | bun, caldav, **crdt**, email, google-workspace-alternative, privacy, self-hosted, webdav, **yjs**, … |

Self-description: *"Your own workspace. A self-hosted, open source alternative to Google Workspace: mail, drive, docs, sheets, slides, calendar and chat."*

### 5.2 Activity — VERIFIED

- **~5,011 commits** since 2025-03-07 (~17.7 months). **745 in the last 30 days; 1,846 in the last 90** — roughly 25 commits/day, sustained, by one person.
- **3 contributors:** `eigen-is` **4,831**, `markknol` 112, `reindernijhoff` 68.
- **`eigen-is` and `reindernijhoff` are the same human** — every `eigen-is` commit carries git author name **"Reinder Nijhoff"**, and the `reindernijhoff` account's commits stop at 2026-06-19 (he switched to the project account). Combined: **4,899 of 5,011 = 97.8%.**
- `markknol` (Mark Knol) contributed Feb–Jun 2026, last commit 2026-06-16, 4 commits in the last 90 days.
- Overwhelmingly agent-authored (`CLAUDE.md`, `AGENTS.md`, `.claude/` config present) but disciplined: `bun run check` = lint + typecheck + repo guards + tests; Biome; `.githooks` gate. A pair of consecutive commits on 2026-08-28 **retracting a benchmark claim** (`docs(sheets): retract the 68s cold open — the bench was measuring machine load`) is the signature of a human catching an agent's bad measurement.

### 5.3 Releases — VERIFIED

- **Only 2 releases:** `v0.1.0` (2026-07-19) and `v0.1.1` (2026-08-13). Both non-draft, non-prerelease. 8 tags total.
- **ZERO downloadable assets on either release.** Distribution is `git clone` + `bun install` + Docker Compose.
- README is explicit: *"Breaking changes are likely between minor versions until 1.0"*, *"If data loss in your workspace would be catastrophic, wait for 1.0."*

### 5.4 Architecture — VERIFIED

Not Electron, not Tauri, not Next.js. **A self-hosted server plus a browser SPA.**

- **Runtime: [Bun](https://bun.sh)**, monorepo via Bun workspaces (`packages/*`, `apps/*`).
- **Backend: Elysia + Drizzle ORM over SQLite**, type-safe end-to-end via Eden Treaty.
- **Frontend: React 19 + TanStack Router/Query + Tailwind 4 + shadcn/ui**, Vite, Biome.
- **Auth: better-auth** (email/password, 2FA, orgs, teams).
- **Real-time: Yjs CRDTs over WebSocket + SSE.**
- **Deployment: 5 Docker containers** — Caddy (auto-HTTPS), Eigen API (Bun), Postfix (SMTP), Dovecot (IMAP), Unbound (DNS).

**On-disk layout** (`docs/STORAGE.md`, HTTP 200): one directory per principal, **one SQLite DB per subsystem per user**, no shared database.

```
data/home/{userId}/
├── settings.json
├── mounts/default/       # Drive files + metadata.db
├── eigen.mail/           # Maildir++ + mail.db
├── eigen.contacts/       # .vcf vCards + contacts.db + avatars
├── eigen.calendar/       # calendar.db
└── eigen.notifications/  # notifications.db
```

**Document formats are proprietary containers, not plain text:**

| App | On-disk | Confirmed by |
|---|---|---|
| Docs | **`.eigendoc`** | `apps/api/src/lib/preview/eigendoc-render.ts`, `packages/lib/src/docs/eigendoc/` |
| Sheets | **`.eigensheets` folder** | `docs/SHEETS.md` TLDR; fixture `festival-budget.eigensheets/{data.db,comments.db}` |
| Slides | **`.eigenslides` folder** | `docs/SLIDES.md` TLDR; fixture `sponsor-pitch.eigenslides/{data.db,comments.db,media/logo.svg}` |

Interop is by **export only** (`DOCX_MIME`, `XLSX_MIME` are the only two constants in `packages/lib/src/constants/mime.ts`; Docs exports DOCX/PDF/HTML). Mail (Maildir++) and Contacts (vCard) are the honourable exceptions — those *are* open formats.

**GIT INTEGRATION: NONE.** VERIFIED negatively four ways:
1. Code search across the repo: `isomorphic-git` → **0 results**, `simple-git` → **0**, `nodegit` → **0**.
2. No git dependency in the root `package.json` or in `apps/{api,docs,sheets,slides}`, `packages/{sheet,lib}`.
3. Full recursive tree (2,482 paths): the only `git`-matching paths are seven `.gitkeep` files, `.github/`, `.githooks/`, `.gitignore`, `.gitattributes`.
4. The only git usage is dev tooling: `"prepare": "git config core.hooksPath .githooks"`.

Versioning and conflict resolution are **Yjs CRDT**, not commits. Backup is `scripts/backup.sh` / a directory copy.

### 5.5 Feature coverage — the widest scope of anything found

`apps/` contains 14 apps: admin, api, calendar, chat, contacts, docs, drive, index, mail, sheets, slides, space, stickies, vector.

- **DOCS:** Tiptap + Yjs, DOCX/PDF/HTML export, embedded comment threads with @mentions.
- **SHEETS:** an in-tree spreadsheet engine **forked from fortune-sheet/luckysheet** (`packages/sheet`) with **op-level Yjs sync** (each edit → a small op pushed to a Y.Array; remote clients `applyOp()`). `docs/SHEETS.md` is **32,268 bytes** describing a custom canvas renderer, conditional formatting, autofilter, tick boxes, custom number/date/currency formats, a Sheets-style menu bar. **This is the deepest spreadsheet implementation found in this research** — and a useful reminder of how much work a real sheet is.
- **SLIDES:** pixel canvas 1920×1080, resolution-independent via `pxToPercent()` and CSS container query units. Yjs model: `slideOrder` (Y.Array), `slides`/`objects` (Y.Map). Object types: text (Tiptap HTML) and image. **Not markdown-based** — a real WYSIWYG object canvas.
- **Beyond the trio:** Mail (webmail + Maildir++ + Dovecot IMAP + DKIM), Drive (ACL, thumbnails, S3 backend, WebDAV mount), Stickies (kanban with per-card chat), Calendar (RFC 5545 RRULE, **built-in CalDAV server**), Contacts (vCard 3.0/4.0, **built-in CardDAV server**), Chat (80+ slash commands), Space, Admin.
- **Open protocol support is its real differentiator:** IMAP, CalDAV, CardDAV, WebDAV (RFC 4918 Class 1+2), SMTP with DKIM.

### 5.6 Traction — essentially none

`https://eigen.is` → HTTP 200 (SPA). **`https://demo.eigen.is` → HTTP 200 — a live public demo workspace that resets hourly.**

HN: query `"eigen.is"` → **nbHits 0**; `eigen-is` → 121 hits, **all false positives** (the Eigen C++ linear-algebra library). The real posts:
- *"Eigen: Building a Workspace"* (2026-02-03) — **17 points, 3 comments**
- *"Show HN: I'm building Eigen, a self-hosted Google Workspace alternative"* (2026-04-16) — **3 points, 2 comments**

Context that matters: **the same author's unrelated posts did far better** (Wolfenstein raytracing in WebGL, 235 pts; Townscaper rendering, 177 pts). He has HN reach. Eigen specifically did not land.

### 5.7 Verdict: enormously productive, essentially unadopted

Commits today; 745 in 30 days; ~5,011 total in 17 months; 97.8% from one human driving coding agents hard. The README is unusually honest: *"Eigen is pre-1.0 and built by one person… provided as-is, in good faith, with no SLA."*

**This is the opposite failure mode from Pithy's.** Not abandoned — hyper-active — but with 14 stars, 1 fork, 2 issues ever, 0 open PRs, 2 releases with zero downloadable artifacts, and a Show HN that got 3 points. Bus factor 1, with no community to absorb the loss, and a scope (mail server, CalDAV, CardDAV, WebDAV, forked spreadsheet engine, slide canvas, chat) that would be ambitious for a funded team.

**Strategic read:** Eigen is the cautionary tale for *scope*. It demonstrates that one person plus agents can now build a credible 14-app Workspace clone in 17 months — the build is no longer the moat. It also validates that going wide (mail! calendar! chat!) buys **zero** distribution. And by choosing SQLite containers over plain files, it forfeits precisely the property that makes the git-backed thesis interesting, which is a point of genuine differentiation to press.

---
## 6. Kova — `github.com/KovaMD/Kova` / `kova.md`

> **Neither a threat nor a component today — but the most likely of anyone to stumble into the Sheets leg from the side.** A GPL-3.0 markdown *presentation* editor with unusually professional distribution and a shipped formula engine, run by one UK developer with no funding and no launch. Its roadmap shows zero movement toward a docs/sheets suite.

*(Repo facts, slide features and the `!sheet` formula design are covered elsewhere and are not repeated here. This section covers people, traction, business model, roadmap and judgement.)*

### 6.1 Who is behind it

**One person: Ross Millen (`RDMillen`, `rossmillen@protonmail.ch`).** VERIFIED via `GET /repos/KovaMD/Kova/contributors` (**200**):

| Contributor | Contributions | Notes |
|---|---|---|
| **RDMillen** (Ross Millen) | **620** | Sole maintainer. 73 of the last 100 commits |
| `Ayush7614` (Felix-Ayush / Ayush Kumar) | 76 | The only substantial second contributor |
| `vadika` | 28 | |
| `florian-hubertSE` (Florian Hubert) | 9 | Commits from **`florian.hubert1@se.com`** — a **Schneider Electric** corporate address |
| `ferkans-amir` / `amir-rezaei` (same person) | 6 | Commits from **`amir.rezaei@tu-berlin.de`** — TU Berlin |
| `github-actions[bot]` | 4 | |
| `anderlli0053`, `a1880`, `Barry1`, `Sl-Alex` | 1 each | Drive-by fixes |

**Bus factor 1** (~86% of contributions), but with a meaningfully healthier contributor tail than Pithy (1), Eigen (effectively 1), or Perchpad (1). The Schneider Electric and TU Berlin addresses are the only evidence anywhere in this report of **institutional users** patching a git-backed editor — weak, but real, signal of enterprise and academic pickup.

Org `KovaMD` (`GET /orgs/KovaMD` → **200**): name "Kova", location **"United Kingdom"**, contact **`opensource@kova.md`**, blog `kova.md`, created 2026-05-06, **7 followers**, **0 public members**, not verified. Description: *"KovaMD - Markdown presentation software, with a focus on compatabiltiy with polling and diagramming software."* (typo in the original).

Four repos, all GPL-3.0: `Kova` (283★), `Web` (2★, the site), `Themes` (2★), `VSCodePlugin` (0★, created **2026-08-23** — same day as the latest release).

**No about page, no team page, no company entity found.** `kova.md/about`, `/pricing`, `/download`, `/sponsor`, `/donate` all → **404**. This is an individual's project, not a company.

### 6.2 Traction and reception — the weakest of anyone, on the numbers

**Hacker News: never posted. VERIFIED.**
- `hn.algolia.com/api/v1/search?query=kova.md` → **nbHits 0**
- `query=Kova markdown presentation` → **nbHits 0**
- `query=KovaMD` → 4 hits, and **none is a Kova submission.** The only 2026 hit (id `49142268`, 2026-08-02) is a *comment* by an unrelated user (`wordius`) in a link-roundup — *"Among today's links are markdown editors Editorial and SiYuan, Eziwiki… **KovaMD, a presentation app**, and Agenda"* — posted on a story that was itself **[dead]** (flagged/killed). So Kova's single HN mention ever is a passing name-check inside a dead thread.

**Reddit and Lobsters: NOT VERIFIED.** `reddit.com/search.json` and `lobste.rs/search.json` both refused the request (non-JSON response / `"400 Unpermitted query or form parameter"`). No conclusion either way. **ProductHunt: NOT FOUND.** **No launch post of any kind was located.**

**Downloads are small — but the headline number understates reality.** `GET /repos/KovaMD/Kova/releases` (**200**), all **67 releases**:

- **5,789 binary-asset downloads total** (excluding `.yml`/`.json`/`.sig` manifests); 5,877 including them.
- Per release: ~100–600, typically ~150. The v0.7.9 breakdown is instructive — **Windows `.exe` 37 + `.msi` 27** vs macOS `.dmg` 15, and the `latest.json` auto-update manifest at 59 is the single most-fetched asset.
- ⚠️ **Important caveat:** Kova ships from its **own apt repo (`deb.kova.md`, HTTP 200), rpm repo, AUR, Nix flake and a self-hosted Flatpak repo**, plus a signed self-updating AppImage. **Traffic through those channels is completely invisible to the GitHub numbers**, and Linux users — the audience most likely to use them — are exactly who this project courts. The true install base is unknown and is certainly higher than 5,789. Do not quote that figure as total adoption.

**Stars: 283, forks 25, watchers 4** in ~3.7 months (created 2026-05-04) ≈ **~76 stars/month**, sustained. **Star history timeline: NOT VERIFIED** — the `application/vnd.github.star+json` stargazer endpoint returned no `starred_at` data on repeated attempts.

**The community-health numbers are genuinely excellent and stand out in this report:**

| Metric | Value |
|---|---|
| Merged PRs | **103** |
| **Open PRs** | **0** |
| Closed issues | **103** |
| **Open issues** | **4** |

Zero open PRs and a 103:4 closed-to-open issue ratio, on a 4-month-old project, is exceptional maintenance discipline. Compare **Nimbalyst's 505 open / 533 closed**. The four open issues are mundane: a broken Nix flake (#233), a **Windows malware false-positive during install** (#224 — a real adoption tax for an unsigned-ish indie Tauri binary), incomplete Gantt rendering (#195), and a presenter-mode aspect-ratio request (#137).

**Release cadence: 67 releases in ~3.7 months** (`v0.4.1` 2026-06-03 → **`v0.7.9` 2026-08-23**), roughly one every 3 days, 18 assets each, only 3 prereleases. Shipping is not the problem.

### 6.3 Business model: there isn't one, and the funding is literally zero

- **No paid tier, no hosted service, no cloud component, no accounts.** The site states it plainly: *"Free, open source, and runs natively on macOS, Linux, and Windows. **No account required.**"* Footer: *"© 2026 Kova contributors · GPLv3."*
- **README:** *"Kova is free and community funded. If you'd like to support development, you can donate via Open Collective."*
- `.github/FUNDING.yml` (**200**) has exactly **one** active line — `open_collective: kovamd`. Every other platform is commented out, including `ko_fi: # RDMillen`.
- **Open Collective `kovamd` — VERIFIED via the Open Collective GraphQL API:**

```json
{"collective":{"name":"Kova","slug":"kovamd","createdAt":"2026-06-21T10:34:31.975Z",
 "stats":{"totalAmountReceived":{"value":0,"currency":"USD"},
          "balance":{"value":0,"currency":"USD"},"contributorsCount":0}}}
```

**Total raised in ~2 months: $0.00. Contributors: 0.** This is the single hardest data point on monetisation in this entire report, and it is a warning about the whole category: a well-run, actively-shipping, 283-star open-source tool in this space has raised **nothing**.

The website is served by **LiteSpeed** (commodity shared hosting, `last-modified` 2026-08-07) — not Vercel/Cloudflare. Consistent with a self-funded hobby budget, notwithstanding the impressive package-repo estate.

**What GPL-3.0 means for anyone wanting to build on it:**

This is the key commercial fact and it cuts sharply. **GPL-3.0 is a strong copyleft licence, not a permissive one.** Practical consequences:

1. **You cannot vendor Kova's renderer, theme engine, or formula evaluator into a proprietary or source-available product.** Any derivative work must itself be released under GPL-3.0 with complete corresponding source. This rules out lifting its `!sheet` evaluator or PPTX exporter into a closed product.
2. **Contrast with the rest of the field:** Nimbalyst is **MIT**, Eigen is **MIT**, Ledgit is **MIT**, md4lp and Voiden are **Apache-2.0**. Kova is the **only GPL-3.0 project in the direct set** — and therefore the only one you categorically cannot borrow code from unless you also go GPL.
3. **All four org repos are GPL-3.0**, including `Themes` — so even the theme YAML collection is encumbered.
4. **Wrapping vs. shelling out:** invoking the Kova *CLI* as a separate process (it has one: `--import`, `--export pdf`, `--check`, `--present`) is the conventional way to use GPL software from a non-GPL product, and is far safer than linking. But it means shipping and requiring a GPL binary — an awkward dependency for a commercial suite, and one that hands a competitor's release cadence control over your feature.
5. There is **no CLA and no copyright assignment** — with 11 contributors, Ross Millen **cannot unilaterally relicense** Kova (e.g. to dual-license commercially) without every contributor's agreement. The GPL is effectively permanent here. That also means **no acqui-license path**.

### 6.4 Roadmap: firmly a deck tool, with no suite ambitions

**VERIFIED negatively, three ways:**

1. **The README has no roadmap section at all.** Headings are: Features, Download, Linux, Building from source, Keybindings, Themes, Support, License. No future plans, no docs/sheets language.
2. **The wiki (`wiki.kova.md`, HTTP 200, MkDocs Material) has no roadmap page.** Its entire IA is Getting Started → Writing Slides → Working with Kova → Examples → Contributing. It opens with *"A Kova presentation is a **single `.md` file**. Slides are separated by `---` on its own line."* The three worked examples are Business Pitch, Technical Talk, Classroom Slides.
3. **The last 25 merged PRs are ~100% presentation work.** PPTX export fidelity (KaTeX→images, strikethrough, YouTube/local video via `addMedia`), PDF handout options (`--notes`/`--per-page`/`--paper`), **Marp import** (`--import marp`, preserving `![bg]`), progressive-reveal build animations (#225, #234), speaker-note fence parsing, `{author}` template variables, standalone interactive HTML deck export, localization (German), and a js-yaml security fix. **Exactly one** touched the sheet engine — **#207, `fix(sheet): standardize error message phrasing in formula evaluator`** — a string-polish fix, not an expansion.

The website's own audience framing is decks end-to-end: Educators, Professionals, Markdown writers, and *"Teams with docs — turn existing technical documentation into **training sessions and onboarding decks**."* Documents are an *input* to slides, never an output.

**Conclusion: `!sheet` computed tables are a slide-content feature — a way to keep a budget table on a slide live — not the beginning of a spreadsheet product.** There is no evidence of intent to become a docs/sheets suite, and no milestones, discussions (`has_discussions: false`) or public planning artifacts to suggest otherwise.

### 6.5 Judgement: neither a threat nor a usable component — but the best distribution playbook in the report

**Not a threat, on three grounds:** it does not do docs; it does not do sheets as a product; and it has no collaboration, no git integration, no multi-file workspace and no "repo as drive" concept. A Kova presentation is *one `.md` file*, opened from the filesystem. It competes with **Marp and Slidev**, not with a workspace — and it knows it, to the point of shipping a Marp importer to convert their users.

**Not a component, because of GPL-3.0.** Its slide renderer and PPTX exporter are the most mature in the report and would be genuinely tempting to reuse — and copyleft plus a no-CLA multi-contributor history makes that a closed door for anything but a GPL product. Shelling out to its CLI is technically viable and strategically unattractive.

**The one place it should genuinely inform strategy:**

1. **It is the only project here converging on the thesis from the *slides* side.** Everyone else came from docs. If Kova ever generalises `!sheet` from a slide widget into a standalone editor, it arrives with 283 stars, a Linux packaging estate, and a Windows/macOS/Linux install base already in place. **Watch `examples/sheet-basics.md` and any PR touching the formula evaluator beyond bug fixes.** Today the signal is flat.
2. **Its distribution is the best in this report and is worth copying outright.** Own apt + rpm repos, AUR, Nix flake, self-hosted Flatpak, a *signed self-updating* AppImage, a status page, a MkDocs wiki and a Matrix room — from a solo dev in four months. Compare Pithy (three unversioned files on a CDN, no update feed), Eigen (two releases, **zero** binaries) and Moment (a single download manifest). Distribution is the binding constraint in this whole category, and Kova is the only one treating it as a first-class problem.
3. **It corroborates §8.4's core finding from the opposite direction.** Kova ships the polished slide tool — themes, PPTX/PDF export, presenter view, build animations — and gets 283 stars, $0, and no HN post. **Slides is not a wedge, even when you build the best one.**
4. **The Flathub note is a live, quotable market fact.** Its README states that *"Flathub's current policy excludes LLM-assisted apps, so Kova ships from a self-hosted Flatpak repo."* Openly AI-assisted development now carries a concrete **distribution-channel penalty** on at least one major Linux store — a real constraint to plan around for any agent-built product in this space.

**Sources (all fetched):** `https://api.github.com/repos/KovaMD/Kova` · `/contributors` · `/commits` · `/releases` (67) · `/issues?state=open` · `/contents/.github/FUNDING.yml` · `/readme` · `https://api.github.com/orgs/KovaMD` · `/orgs/KovaMD/repos` · `https://api.github.com/search/issues` (4 counts) · `https://api.opencollective.com/graphql/v2` (collective `kovamd`) · `https://kova.md` (200) · `https://wiki.kova.md` (200) · `https://status.kova.md` (200) · `https://deb.kova.md` (200) · `https://hn.algolia.com/api/v1/search?query=kova.md` (nbHits 0) · `https://hacker-news.firebaseio.com/v0/item/49142268.json`
NOT VERIFIED: Reddit and Lobsters search (both refused the request); star-history timeline; ProductHunt presence.

---

## 7. The rest of the field — products not named in the brief

A separate sweep ran ~35 HN Algolia queries and ~30 GitHub search-API queries. The important result is not any single find — it is the **shape** of the field.

### 7.1 Most relevant finds

| Name | URL | Docs | Sheets | Slides | Truly git-backed? | OSS / license | Stars | Last activity | Liveness |
|---|---|---|---|---|---|---|---|---|---|
| **Notula** | notula.org | ✅ WYSIWYG, Google-Docs-like | ❌ | ❌ | ✅ **real — commits plain `.md` to *your* repo** | closed source | — | Show HN 2026-08-19 (2p/3c) | **LIVE, shipping** |
| **SkillDocs** | skilldocs.dev | ✅ multiplayer CRDT + comments | ❌ | ❌ | ✅ real (connect a GitHub repo) + MCP server | closed source | — | Show HN 2026-08-20 (4p/1c) | **LIVE** |
| **Ledgit** | github.com/jackhale98/Ledgit | ❌ | ✅ **CSV/TSV on disk** | ❌ | ✅ real (Tauri+Rust; commit/branch/merge/push/pull; daff cell diffs) | MIT | 0 | pushed 2026-02-28 | **Stalled after 1 day** |
| **md4lp** | github.com/md4lp/md4lp | ✅ WYSIWYG + comments | ❌ | ❌ | ✅ real (isomorphic-git, byte-exact `.md`, ephemeral edit branches) | Apache-2.0 | 0 | pushed 2026-07-04 | **Dead** — md4lp.com TLS-fails |
| **Tachiko Work** | github.com/nurockplayer/tachiko-work | (projection) | ✅ typed model + formulas | ❌ | ✅ Git/CI adapter, canonical LF text, semantic diff | Apache-2.0 | 0 | pushed **2026-08-28** | **ACTIVE pre-alpha** |
| **md-office** | github.com/einapoli1/md-office | ✅ TipTap WYSIWYG | ❌ | ❌ | ✅ real (go-git, repo per workspace, auto-commit on save) | none stated | 0 | pushed 2026-02-17 | **Abandoned after 4 days** |
| **Voiden** | voiden.md | ✅ `.void` MD blocks (API docs) | ❌ | ❌ | ✅ real, offline-first, files beside your code | Apache-2.0 | **1,596** | pushed 2026-08-27 | **LIVE — market proof** |
| **Tabula** | github.com/pblazh/tabula | ❌ | ✅ **formulas inside CSV & MD, recompute on save** | ❌ | git-friendly by design (CLI only) | GPL-3.0 | 2 | pushed 2026-07-04 | Alive, tiny |
| **MarkdownOffice** | markdownoffice.substack.com | ✅ | ✅ | ✅ | claims "Git-friendly text artifacts" | proposes open-core | ~1 | Substack 2025-12-27 | **VAPORWARE — whitepaper, no code** |
| **docs.dev** | docs.dev | ✅ MDX in your GitHub repo | ❌ | ❌ | ✅ real | template OSS | — | Show HN 2026-07-13 | LIVE |
| **DocColab** | github.com/JoelBondoux/DocColab | ✅ (via GDocs/Word sync) | ❌ | ❌ | ✅ GitHub canonical MD; conflict branches + PRs | MIT | 0 | pushed 2026-08-24 | Active, unknown |
| **Corpo** | github.com/ilikesymmetry/corpo | ✅ MD wiki + comment GUI | ❌ | ❌ | ✅ files in your repo; ships as a Claude Code skill | none stated | 0 | pushed 2026-03-13 | Dead |
| **DVCS** | github.com/SaintFreddy/dvcs | ✅ .docx | ✅ .xlsx | ❌ (.pptx stub) | ✅ git filters + semantic CDM tree | NOASSERTION | 0 | pushed 2026-03-16 | Stalled |

### 7.2 Notable individual finds

**Notula** (notula.org, Show HN 2026-08-19) is the **most direct live commercial rival on the Docs leg**. WYSIWYG markdown for docs in git repos, no git commands or markdown syntax required, *"where humans edit the Markdown your AI agents read."* Files stay plain `.md` in **your own repository**. Notably it **avoids branches and PRs entirely** — background fetch, conflicts surfaced as paragraph-level choices, publishes as ordinary commits. Explicit exit guarantee: *"delete the app and every document and every comment is still there."* Docs only.

**md4lp** is dead but is the **deepest technical prior art** on the hard problems: WYSIWYG that "never leaves the text buffer" so the `.md` in git stays **byte-exact**; server-held single-editor lock with heartbeat; auto-save to an **ephemeral edit branch** consolidated to `main` on release; comments anchored to *text* not line numbers, with intact/moved/orphaned triage; per-user comment threads on sidecar branches; **AI agents as first-class editors over MCP under the same lock**. Read its README before designing the editor.

**Ledgit** is the only existing **git-backed CSV spreadsheet**: AG Grid over CSV/TSV files on disk, staging and commits from the sidebar, commit log, working-tree diff, branching, three-way merge with a **three-pane Ours/Merged/Theirs conflict editor with per-cell accept buttons**, cell-level diffs via **daff**, push/pull to remotes, prebuilt macOS/Linux/Windows binaries. Created 2026-02-27, last push 2026-02-28, **0 stars**. Proof the Sheets leg is buildable — and completely unclaimed.

**Tachiko Work** is the one actively-developed project that could plausibly beat this idea to a full suite: *"A Rust-native, Git-native, and AI-native workspace for documents, spreadsheets, structured data, and computation,"* with deterministic formula calculation, dependency tracking, semantic diff with formula-impact analysis, and a provider-neutral Git/CI adapter. **But it explicitly rejects the plain-file architecture:** *"Tachiko Work is not an Office clone… Traditional document and spreadsheet views are future projections of that model rather than separate sources of truth."* It stores a typed semantic model (`.ro` v2, `.roproj/v1`), not markdown/CSV. Opposite bet — which is the differentiator against it.

**MarkdownOffice** matters only as a warning: a Substack post from **2025-12-27** states this exact thesis — *"an LLM-first, Markdown-native office suite where documents, spreadsheets, and slides are deterministic, Git-friendly text artifacts, enabling auditability and self-hosting."* The GitHub org has 5 repos, all effectively empty (`MarkdownOfficeIntro`'s entire README is the string "MarkdownOfficeIntro"). **The pitch is already public; nobody has executed it.**

**Voiden** (1,596★, Apache-2.0, pushed 2026-08-27) is not a competitor but is the **best market proof in the whole report**: an offline, git-native, plain-markdown workspace that displaced a SaaS category (Postman) and got real adoption. It shows the model *can* sell — when it replaces a specific tool people already hate.

### 7.3 The plain-CSV-with-formulas gap is real and verified empty

- A web search for a spreadsheet app that saves plain CSV with formulas in a separate file returned **no such product**. The recurring failure mode — saving to CSV evaluates every formula to its result and the logic is permanently lost — has **no product answer**.
- Existing responses are either (a) `xltrail` / Git XL, which split an **.xlsx** into sheets/VBA/queries and version each (still binary-origin), or (b) DoltHub's "So you want spreadsheet version control?" (versioning inside a SQL database). *(REPORTED via search snippets; those pages were not fetched.)*
- Closest prior art: **Tabula** — *"Run spreadsheet-style formulas inside CSV and Markdown files. Recompute on save"* — but it is a **CLI transformer** and embeds formulas **inline** in the CSV rather than in a sidecar.
- Adjacent: **md-advanced-tables** (`tgrosinger/md-advanced-tables`, MIT, **189★**, last push 2024-09-05) — spreadsheet formulas in Markdown tables, the reference implementation behind Obsidian's Advanced Tables plugin. Dormant ~2 years, and the most-used artifact in this niche.
- **The incumbents do not store plain files.** **Grist** (`gristlabs/grist-core`, Apache-2.0, **11,630★**, active) — a document is a **SQLite file (`.grist`)**. **Quadratic** — own grid format, cloud-backed. NocoDB / Baserow / Rows are database-backed (*REPORTED — not individually fetched*). VisiData / sc-im / Modern CSV / csvbase are genuine CSV tools but have no git integration and no formula persistence model.
- ⚠️ **EqualTo "Sheet Markup"** — *"add spreadsheets to a Markdown document"* — Show HN 2023-04-11, **120 points / 47 comments**, the **highest-scoring post found anywhere in this niche**. `www.equalto.com` **no longer resolves (DNS failure)**. The idea drew real HN interest three years ago and the company is gone. Read that either as "the audience is small" or as "the spreadsheet angle is the one that lands" — but do not ignore it.

### 7.4 Markdown slides: commodity, not a wedge

Presenterm (306p on HN, 2025-03-08), MkSlides (78p, 2025-11-27), Slidev, remark.js, Marp, Slideck, slidr, Colloquium, Slaide; plus `jacksingleton/hacker-slides` (676★, dormant since 2019), **Kova** (283★, pushed 2026-08-23 — covered in full in §6).

All are plain `.md` files that live happily in a git repo — but every one is a **compiler with an editor bolted on**, not a workspace. No collaboration, no "the repo is the drive."

**Assessment: the slides leg is the least contested *and* the least defensible.** Marp and Slidev already own `---`-separated markdown slides and are free. Combined with Nimbalyst's shipping `.slides.md` extension (§4.5), **slides is a feature of the suite, not a wedge.**

### 7.5 Well-known adjacent tools — almost none are actually git-backed

| Tool | Storage | Git-backed? |
|---|---|---|
| SilverBullet (5,947★, MIT, active) | plain `.md` on disk | ❌ own sync engine; git is the user's problem |
| Obsidian | plain `.md` on disk | ❌ core; ✅ only via a community git plugin |
| Logseq (44,663★, AGPL) | plain `.md`/`.org` | partial — git integration exists, docs only |
| Foam (17,379★) / Dendron | `.md` in a VS Code folder | ✅ *incidentally* — it's just files in your repo. No app-level git |
| Outline (40,360★) | Postgres | ❌ |
| Docmost (21,500★, AGPL) | Postgres | ❌ |
| Wiki.js | DB + optional git *sync* | ⚠️ git as a mirror, not source of truth |
| GitBook | git sync | ⚠️ sync, and it's a docs publisher |
| AppFlowy / AFFiNE / Anytype | local DB / CRDT blocks | ❌ not markdown files at all |
| HackMD / CodiMD | DB + GitHub push | ⚠️ export/sync |
| Notesnook / Zettlr / Typora / iA Writer | plain `.md` | ❌ single-file editors, no git |
| **OpenKnowledge** (`inkeep/open-knowledge`, **3,675★**, GPL-3.0, pushed 2026-08-28) | markdown | *"AI-native markdown IDE and LLM wiki."* Show HN 2026-06-25 — **381 points / 173 comments**, by far the biggest post in the wider space. Docs only; git status **NOT VERIFIED** |

**AI office suites that are markdown-adjacent but not git-backed:** `genspark-ai/genoffice` (**3,860★**, Apache-2.0, active — Docs/Sheets/Slides as `.docx`/`.xlsx`/`.pptx` + Markdown, no git); `criptogus/HermesOffice` (**528★**, *"AI-native office suite… byte-preserving round-trip, 100% local,"* OOXML, no git); `cowork-os/cowork-os` (440★, MIT).

### 7.6 White space that is genuinely unoccupied

1. **Sheets as plain CSV + a formula sidecar, in git.** VERIFIED: nothing ships this. Ledgit has no formula layer; Tabula embeds formulas inline and is a CLI. **The strongest and most defensible leg of the idea, and the hardest to copy.**
2. **All three legs in one repo, for non-developers.** Every git-backed find is docs-only (md-office, md4lp, Notula, SkillDocs, Corpo, docs.dev, Voiden, Moment, Perchpad, Pithy) or sheets-only (Ledgit). Only **Nimbalyst** actually ships all three — and it is aimed at developers orchestrating coding agents, not at teams doing office work.
3. **"The repo IS the drive" as the organizing metaphor.** A GitHub search for `"repo is your drive"` returned **zero** results. Everyone treats git as a versioning backend bolted onto a document app; nobody ships the file-tree-as-drive UX.
4. **Non-technical users never seeing git.** md4lp identified it ("branch-based collaboration, hidden from the author") and Notula solves it by refusing branches entirely — but both are docs-only and one is dead.
5. **Cell-level merge for spreadsheets as a first-class collaboration primitive.** Ledgit built the three-pane per-cell conflict resolver and abandoned it in a day. `daff` exists and works.

### 7.7 Crowded — proceed carefully

- **Docs alone is now a crowded 2026 category:** Notula, SkillDocs, Moment, Perchpad, Nimbalyst, Pithy, docs.dev, OpenKnowledge (3,675★), markra (787★), Corpo, plus every WYSIWYG-markdown project on GitHub. **Do not lead with Docs.**
- **Slides is commodity.** See §7.4.

### 7.8 The most important pattern in the whole sweep

**No "markdown in git" launch has ever gotten traction on Hacker News.**

| Launch | Score |
|---|---|
| Moment — *"We want to displace Notion with collaborative Markdown files"* (2026-03-03) | **29 pts / 14 comments** |
| Nimbalyst — best of six submissions (2025-12-18) | **29 pts / 5 comments** |
| Eigen — *"Building a Workspace"* (2026-02-03) | **17 pts / 3 comments** |
| SkillDocs (2026-08-20) | **4 pts / 1 comment** |
| Perchpad (2026-02-07) | **2 pts / 2 comments** |
| Notula (2026-08-19) | **2 pts / 3 comments** |
| Pithy | **never posted — 0 HN footprint** |

And for contrast, the two things in this space that *did* land:

| Launch | Score |
|---|---|
| OpenKnowledge — *"AI-native markdown IDE and LLM wiki"* (2026-06-25) | **381 pts / 173 comments** |
| **EqualTo — *"add spreadsheets to a Markdown document"* (2023-04-11)** | **120 pts / 47 comments** — *company now dead* |
| Moment's *"Lies I was told about collaborative editing"* blog posts | **352 pts** and **272 pts** |

The lesson is blunt: **"git-backed markdown editor" as a headline does not get attention.** What gets attention is a hard technical problem written up honestly (Moment's CRDT posts), an AI-native framing (OpenKnowledge), or **spreadsheets in plain text** (EqualTo).

---

## 8. Synthesis — what changes the strategic picture

### 8.1 The concept is validated to the point of being crowded, but nobody has won

Nine separate teams have independently arrived at "docs as markdown in a git repo" in the last 18 months. Not one has traction. The binding constraint in this category is **distribution, not the build** — and Eigen proves the build itself is no longer a moat (one person + coding agents shipped a 14-app Workspace clone in 17 months).

### 8.2 The single biggest correction to the brief: Nimbalyst already ships all three legs

`.md` docs + `.csv` sheets **with formula support** + **`.slides.md` reveal.js slides with `---` separators**, all as plain files, with real `simple-git` integration that watches `.git/refs` and coexists with your CLI — in an MIT-licensed, 1,594-star, actively developed Electron app with 96 signed releases and mobile apps.

**Any positioning that rests on "nobody has built this" is false and will not survive contact with an informed reader.** What is *not* taken is the **audience and the framing**: Nimbalyst is an IDE-adjacent console for orchestrating coding agents, sold to developers. A git-backed Workspace sold to **teams** — where the document, the sheet and the deck are the work rather than a side-panel on an agent run — is a different product to a different buyer.

### 8.3 The second biggest correction: "git-backed" is usually a half-truth, and that is the wedge

| Product | Where the source of truth actually lives when you collaborate |
|---|---|
| **Moment** | **`git.moment.dev`** — their server. GitHub is OAuth login only. No self-hosting |
| **Perchpad** | **Perchpad's Fly.io servers.** GitHub sync is *"Coming Soon"* |
| **Pithy** | Your own GitHub repo — the correct answer, but the product is abandoned |
| **Nimbalyst** | Your own repo for files; collab sync goes through a **closed-source** `wss://sync.nimbalyst.com` |
| **Eigen** | Its own SQLite containers — no git at all |
| **Notula** | **Your own repo** — the one live product that gets this fully right, docs only |

Moment's own top HN critic asked *"what does this provide my team that git does not?"* — and the honest answer for Moment is "a server you don't own." **True sync-to-your-own-remote, plus self-hosting, attacks the exact promise every one of these products leans on in its marketing and quietly walks back in its docs.**

### 8.4 Lead with Sheets

This is the clearest finding in the report. Docs is crowded (ten-plus entrants) and slides is commodity (Marp/Slidev, free). But:

- **Nothing ships CSV + a formula sidecar.** Verified empty.
- The one attempt at git-backed CSV (Ledgit) was abandoned after one day at 0 stars, having already built cell-level three-way merge.
- The universal complaint — *"saving to CSV loses my formulas"* — has no product answer anywhere.
- And the **only post in this entire niche that ever got real HN attention was EqualTo's spreadsheets-in-markdown at 120 points** — from a company that no longer exists.

**Two honest qualifications, both added after the Kova review:**

1. **Formulas-in-plain-markdown is no longer unshipped.** Kova's `!sheet` computed tables (§6) put live formulas in a GFM table with *"the source keeps only the formulas"*, and Nimbalyst's CSV extension claims formula support (§4.6). What remains genuinely unoccupied is narrower and should be stated precisely: **formulas over plain `.csv` files, persisted in a sidecar, versioned in a user-owned git repo, in a real grid UI.** Kova's is a slide widget over a markdown table; Nimbalyst's persistence model is unverified. Do not claim "nobody has done formulas in text" — claim the sidecar-over-CSV design.
2. **The "attention" argument rests on one 2023 data point.** EqualTo's 120 points is the best evidence that the spreadsheet angle lands, and that company is dead. Kova is the counter-example that cuts the other way: it built the most polished tool in its lane and got 283 stars, **$0 raised**, and no HN post at all. Build quality does not produce distribution in this category, for any of the three legs.

Sheets is still the hardest leg to build and the least contested — but the moat is the *sidecar-over-CSV-in-git* design, not "formulas in text" as a general idea.

### 8.5 Cheap, concrete wins available from competitors' mistakes

- **Fix commit attribution.** Both Pithy (`Local User <local@pithy.md>`) and Perchpad (auto-commit every 60s) destroy `git blame` — the exact thing a git-backed drive is supposed to buy. Per-author commits, or at minimum author trailers.
- **Do not link a 404 from a "View on GitHub" button.** Pithy does it twice, and contradicts itself on AGPL-3.0 vs MIT in the same page. If the claim is open source, ship the repo.
- **Follow Nimbalyst's git design, not Pithy's.** Watch `.git/refs` and `.git/index` with a file watcher; coexist with the user's CLI and editor; propose commit messages rather than silently auto-committing.
- **Read md4lp's README before designing the editor.** Byte-exact WYSIWYG round-trip, comment re-anchoring (intact/moved/orphaned), and hiding branches from non-technical authors are all solved there in writing.
- **`daff` is the off-the-shelf answer for cell-level CSV diff/merge.** Ledgit proved it works.

### 8.6 Watch list

| What | Why | Re-check |
|---|---|---|
| **Nimbalyst** | The real competitor. Watch whether it broadens beyond coding-agent orchestration | Monthly |
| **Tachiko Work** | Actively developed, git-native, docs + sheets + formulas. The one that could beat you to a suite | Monthly |
| **Moment** | Blog silent since 2026-05-01. Is it winding down or heads-down? | 30–60 days |
| **Notula / SkillDocs** | Both launched Aug 2026, both commercial, both docs-only. Do they add sheets? | 60 days |
| **Pithy** | Dormant 5 months. If Tyler Tate resumes or open-sources `pithy-app`, the picture changes | Quarterly |
| **Kova `!sheet`** | Today it is a slide widget with flat momentum (1 of the last 25 PRs). If the formula evaluator generalises into a standalone editor, it arrives with 283★ and the best Linux distribution in the field. Watch `examples/sheet-basics.md` and any non-bugfix PR touching the evaluator | Monthly |
| **Kova licensing** | GPL-3.0 with **no CLA** across 11 contributors — permanently uncopyable and unrelicensable. Re-check only if a CLA appears | Quarterly |
| **Nimbalyst CSV formula persistence** | **NOT VERIFIED** — where its CSV extension stores formulas (sidecar? in-memory?) is the single most important open question in this report | Immediately |

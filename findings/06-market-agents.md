# 06 — Market & strategy: a git-backed, plaintext-native office suite for AI agents

Research date: **2026-08-28**. Researcher: agent sweep over HN Algolia, GitHub API, live site
fetches, and web search.

**Labelling convention**

- **VERIFIED** = I fetched the artefact myself in this session (HN item JSON, GitHub API, HTTP
  response, page body) and the number/quote is copied from that fetch.
- **REPORTED** = secondhand (news article, third-party estimate, search-result summary).

**Access limitation, stated honestly:** `reddit.com`, `old.reddit.com`, redlib mirrors and
`lobste.rs` search were all blocked or 403'd from this environment (verified: reddit JSON returned
HTTP 302 to a block page; `redlib.catsarch.com` returned 403; WebFetch refuses reddit domains;
lobste.rs search returned no parseable results). **There is therefore no Reddit or lobste.rs
primary evidence in this document.** Every quantitative signal below comes from Hacker News
(Algolia + Firebase item API), the GitHub API, a live HTTP fetch of a company page or issue
tracker, or a labelled third-party estimate. Treat the absence of r/selfhosted / r/ObsidianMD
data as a gap, not as evidence of absence.

**Other stated gaps:** Obsidian has never disclosed revenue — the $5–12M figure in §D.4 is
arithmetic from a verified user count and verified pricing, not a source. Nextcloud, Collabora,
ONLYOFFICE, Outline, Joplin and Anytype revenues are private. Coda's, Skiff's and Standard Notes'
acquisition terms are undisclosed. WebSearch quota was exhausted partway through the §D research.
Ratio of labels in this document: **109 VERIFIED / 16 REPORTED**.

---

## A. Demand evidence — is anyone actually asking for this?

### A.1 What the demand actually looks like

The honest summary: **there is large, loud, repeated demand for three adjacent things, and only
weak demand for the specific thing proposed.**

1. **Huge demand: "a Google Docs / Notion alternative I control."** Sovereignty, self-hosting,
   no-lock-in. This is the biggest signal in the whole space by an order of magnitude.
2. **Large demand: "my notes should be markdown files on my disk."** Obsidian is the proof, and
   HN reacts strongly to anything in that shape.
3. **Real but narrower demand: "my agent should be able to work on my documents."** Rising fast
   through 2026, but the market is currently answering it in the *opposite* direction from this
   thesis (see A.4 / C).
4. **Weak demand: "docs+sheets+slides as diffable plaintext with git as the drive."** Every time
   somebody ships exactly this, it lands with a thud.

### A.2 Demand evidence table

| Source | Date | Signal | Strength |
|---|---|---|---|
| HN [43378239](https://news.ycombinator.com/item?id=43378239) — "Docs – Open source alternative to Notion or Outline" (La Suite Docs, FR+DE governments) | 2025-03-16 | **1,952 points, 454 comments** — the largest signal found anywhere in this space. VERIFIED via Algolia. Repo `suitenumerique/docs`: **16,754★** (VERIFIED). Reading the thread, the demand is about **sovereignty and lock-in**, not plaintext: top comments are about state-funded FOSS, foreign dependency as a security issue, and "the main problem is lock-in. If you can't get your data out you can't leave." Note the format: Django + React + Yjs, **not** files-on-disk. The market's biggest cheer in this space went to a product that is not plaintext-native. | **Very strong — but for a different product** |
| HN [48179677](https://news.ycombinator.com/item?id=48179677) — "Show HN: Files.md – Open-source alternative to Obsidian" | 2026-05-18 | **730 points, 356 comments.** VERIFIED. Repo `zakirullin/files.md`: 4,122 stars. Pitch is literally "Simple app for .md files." | **Strong (docs-as-files)** |
| HN [44945532](https://news.ycombinator.com/item?id=44945532) — "Obsidian Bases" | 2025-08-18 | **695 points, 255 comments.** VERIFIED. Obsidian shipping a database/table layer *over markdown files* — i.e. the market pulling structured data into the plaintext vault. | **Strong (proxy for "sheets in plaintext")** |
| HN [48675435](https://news.ycombinator.com/item?id=48675435) — "Show HN: OpenKnowledge – open source AI-first alternative to Obsidian/Notion" | 2026-06-25 | **381 points, 173 comments.** VERIFIED. Explicitly markdown-on-disk + Claude/Codex/Cursor integration + MCP + CRDT + git. Repo `inkeep/open-knowledge`: 3,675 stars. **This is the closest thing to the thesis that has gotten real traction — and it is docs-only.** | **Strong** |
| HN [44022448](https://news.ycombinator.com/item?id=44022448) — "Ditching Obsidian and building my own" | 2025-05-18 | **471 points, 559 comments.** VERIFIED. Enormous appetite for arguing about plaintext PKM. Note the shape: people *build their own*, they don't buy. | **Strong interest / weak willingness-to-pay** |
| HN [47197267](https://news.ycombinator.com/item?id=47197267) — "Obsidian Sync now has a headless client" | 2026-02-28 | **587 points, 212 comments.** VERIFIED. | **Strong** |
| HN [43117020](https://news.ycombinator.com/item?id=43117020) + [43115767](https://news.ycombinator.com/item?id=43115767) — "Obsidian is now free for work" | 2025-02-20 | **282 + 139 points.** VERIFIED. | Strong |
| HN [12119050](https://news.ycombinator.com/item?id=12119050) / [25745615](https://news.ycombinator.com/item?id=25745615) / [41550603](https://news.ycombinator.com/item?id=41550603) — Plain Text Accounting | 2016 / 2021 / 2024 | 328p+237c, 473p+200c, 334p+120c. VERIFIED. Repeated, durable, decade-long enthusiasm for plaintext in a "serious" domain. | Strong (see §E) |
| HN [48053163](https://news.ycombinator.com/item?id=48053163) — "Ask HN: What is your go-to solution for a personal wiki in 2026?" | 2026-05-07 | Only **16 points, 21 comments**, but the OP's requirement list is the thesis almost verbatim: *"Simple file format like markdown so that you're not locked into something proprietary"*, *"Option to export data out as a backup"*, and — critically — *"Nice to have: support for inline tables of data with simple calculations/sorting"*. VERIFIED quote from HN item JSON. **The answers were Obsidian (×4), org-mode/emacs, Fossil SCM, Bookstack, Trilium, Joplin, Hyperclast, Flatnotes+git, and Google Docs.** Only one answer involved git at all, and its author flagged it as not meeting the requirements: *"I personally use Flatnotes with a connected git repository, but this does not meet your requirements."* **No git-backed office suite was named, because none is established.** | Medium — real need, zero brand awareness for the category |
| HN [49206096](https://news.ycombinator.com/item?id=49206096) — "Ask HN: Team Documentation (GDrive vs. Markdown)" | 2026-08-07 | 1 point, 0 comments — but the OP is a live datapoint: *"At work we use Google Docs and its MCP, and most of my colleagues use Codex to write any documents. For my side projects, we use markdown in repo mostly."* VERIFIED quote. The split is real and people feel it. | Weak signal, high relevance |
| HN [47721153](https://news.ycombinator.com/item?id=47721153) — "Ask HN: Is a purely Markdown-based CRM a terrible idea? Optimized for LLM agents" | 2026-04-10 | VERIFIED. Someone reaching for exactly this architecture. The one substantive reply is the counter-argument (see A.5). | Weak-medium |
| HN [32040573](https://news.ycombinator.com/item?id=32040573) — "Ask HN: Non programming professionals, what do you use for version control" | 2022-07-10 | 8p, 21c. VERIFIED. **This is the most important negative datapoint in section A** — see A.5. | Strong (negative) |
| HN [35524256](https://news.ycombinator.com/item?id=35524256) — "Show HN: Sheet Markup – add spreadsheets to a Markdown document" (EqualTo) | 2023-04-11 | **120 points, 47 comments.** VERIFIED. Genuine engagement with "spreadsheet formulas in plaintext". Notably, EqualTo's own founder said in-thread: *"We've found 'sheet markup' (a simplified, textual representation of a spreadsheet) useful in other contexts, such as when interacting with an LLM."* — in **April 2023**, three years early. | Medium (and see graveyard: equalto.com is now NXDOMAIN) |
| HN [48807225](https://news.ycombinator.com/item?id=48807225) — "OfficeCLI: Office suite for AI agents to read and edit Microsoft Office files" | 2026-07-06 | **215 points, 62 comments**, and the repo `iOfficeAI/OfficeCLI` has **29,443 stars / 2,007 forks in five months** (created 2026-03-15). VERIFIED via GitHub API. **This is the single largest demand signal in the entire report for "agents + office documents" — and it is squarely against the plaintext thesis.** | **Very strong — and pointing the wrong way** |

### A.3 What people say they want, in their own (verified) words

From HN [48053163](https://news.ycombinator.com/item?id=48053163), 2026-05-07, the requirements
list for a personal wiki in 2026:

> * Simple file format like markdown so that you're not locked into something proprietary (no need
>   for crazy formatting options like MSWord)
> * Option to export data out as a backup
> * Nice to have: support for inline tables of data with simple calculations/sorting

From HN [43378239](https://news.ycombinator.com/item?id=43378239) (La Suite Docs, 2025), user
`jdvh`:

> I think the main problem is lock-in. If you can't get your data out you can't leave. This is true
> for open source and for commercial products alike. If you own your data and if you have the
> option to self-host you can always opt out of updates you don't like.

From HN [48675435](https://news.ycombinator.com/item?id=48675435) (OpenKnowledge, 2026-06-25), the
founder's own framing of why they built it — a clean statement of the wedge:

> We built this because we wanted a Notion-like experience for writing and sharing markdown files
> across our team. Obsidian is the best alternative we tried, but found it doesn't have a true
> WYSWIG UI and it didn't integrate well with Claude/Codex outside of community plugins.

The clearest statement of the *emotional* driver behind plaintext, from the author of Files.md
(730 points, HN [48179677](https://news.ycombinator.com/item?id=48179677), VERIFIED) — note it is
about ownership and longevity, not about agents:

> I believe that not only you should own your data in plain files, but also you should own the
> software that opens those files. So that your files and tools can grow together, fully under your
> ownership, through the ages.

And the sharpest constraint on "just use markdown files", from the OpenKnowledge thread (`jfim`):

> Obsidian is a lot more than "just markdown" though. For example, with the appropriate plugins
> like dataview and charts, it's possible to create dashboards, lists, and tables that update
> automatically based on data elements present in documents or documents themselves. […] I'd love
> to migrate away from Obsidian towards something that's not proprietary, but I haven't seen
> anything that allows querying other documents.

### A.4 The 2026 cohort: everyone is trying this, nobody is landing it

VERIFIED via HN Algolia (Show HN, 2025-01-01 onwards) and GitHub API. This is a traction table,
and it is brutal:

| Project | HN | GitHub | Note |
|---|---|---|---|
| **OfficeCLI** (agents ↔ .docx/.xlsx/.pptx) | 215p / 62c | **29,443★** in 5 months | Not plaintext. Won the category. |
| **OpenKnowledge** (md + agents, docs only) | 381p / 173c | 3,675★ | Docs only, no sheets/slides |
| **Files.md** (md notes) | 730p / 356c | 4,122★ | Notes only |
| **GenOffice** (GenSpark's AI office suite) | 4p / 0c | **3,860★ in 1 month** | Not plaintext (.docx/.xlsx/.pptx) |
| **Nimbalyst** (visual workspace over md/csv for agents) | 8p / 4c | 1,594★ | Closest OSS substrate; framed as agent workspace |
| **SmallDocs** ("an office suite for coding agents") | surfaced in OfficeCLI thread | 201★ | **Same thesis as this product.** Markdown source → exports .pptx/.xlsx/.pdf. |
| **Moment.dev** ("displace Notion with collaborative Markdown files", md in jj/git) | **29p / 14c** | — | Real engineering (custom CRDT, 60fps collab), near-zero HN reaction. Pricing VERIFIED 2026-08-28: Free 1 user / **$30 per month for up to 5 users, +$6 per additional user** / Enterprise 50+. |
| **Perchpad** (git-native md+csv workspace, MCP for agents) | **2p / 2c** | — | Exactly the thesis. Two points. |
| `einapoli1/md-office` — "Markdown-native office suite — React + TipTap v3 + Go/Fiber + go-git" | — | **0★** | |
| `tonioab49/focal` — "collaborative, markdown-based, git-backed editor" | — | **0★** | |
| `dcox761/collab-editor` — "Collaborative Markdown editor with LLM and Git support" | — | **0★** | |
| `HerozDotExe/gittype` — "Collaborative markdown editor based on git" | — | **0★** | |
| `akkrevsky/citadelMD` — "Self-hosted collaborative Markdown editor with real-time CRDT, Git-based versioning, and MCP server" | — | **1★** | |

**Read this carefully.** In 2026 there are at least five independent implementations of
"git-backed collaborative markdown editor with an MCP server" sitting at 0–1 stars, while the
thing that got 29k stars keeps the binary formats and gives agents a CLI. The idea is not
un-thought-of. It is *over*-thought-of and under-wanted.

### A.5 The opposite case — verified threads arguing this is a bad idea

**(i) Non-technical professionals do not want git, and never have.**
HN [32040573](https://news.ycombinator.com/item?id=32040573) asked exactly the target-user
question. VERIFIED replies:

> A while back I started storing my important files on Dropbox. That at least lets you revert to
> earlier versions […] As an added check, at key moments in a project I'll just add (or increment)
> the number at the end of my filename — `MilnerRoute`

> I would save a copy of my main excel spreadsheet with the date as the file name. Once a day. Not
> perfect but it worked. — `BMc2020`

Nobody in that thread reached for git. Not one person.

And it is not only non-programmers. In HN [44022448](https://news.ycombinator.com/item?id=44022448)
("Ditching Obsidian and building my own", **471 points, 559 comments**, 2025-05-18), the author —
a technical person building their own PKM specifically to own their data forever — explicitly
declined git (VERIFIED):

> Agreed Git can be used to sync your notes. Its a great solution for those comfortable putting
> their notes into a Git repo like Github. **I wasn't comfortable with that however.**

Two commenters then had to explain to them that git is distributed and does not need a server.
This is the target user of a "git-backed" product actively refusing the mechanism.

**(ii) "Docs as code is a broken promise."**
[thisisimportant.net, 2024-04-10](https://thisisimportant.net/posts/docs-as-code-broken-promise/)
— VERIFIED fetch. The pitfalls enumerated by a practising technical writer:

> Git is confusing / Processes must be defined and reflected in Git workflows / Tools to write docs
> can be inconsistent / Merge gates and build checks are great… if you have them / Reviewing
> content in the repository is hard to read

> To do docs as code, writers need to learn how to use and troubleshoot Git. And Git isn't simple

This is the *friendliest possible* audience (technical writers, already bought into the
philosophy), and the verdict is that the tooling defeats them. HN discussion of docs-as-code is
consistently ambivalent: [40917358](https://news.ycombinator.com/item?id=40917358) 111p/**99c**,
[41894631](https://news.ycombinator.com/item?id=41894631) 102p/**113c**,
[33468213](https://news.ycombinator.com/item?id=33468213) 178p/**88c** — comment counts near or
above point counts is the HN signature of an argument, not an endorsement.

**(iii) Token economics may favour queries over files.**
HN [47721153](https://news.ycombinator.com/item?id=47721153), reply by `noemit` (VERIFIED):

> i think its more efficient for models to write queries than read large(ish) documents. at some
> point you have to have a tradeoff - smaller docs, but the model has to find them (thats a query)
> or larger docs, and the model has to read them. My take is AI native apps that have longevity
> will prioritize token-efficiency - and I believe queries do that.

**(iv) Markdown may not even be the agents' preferred format.**
HN [48071940](https://news.ycombinator.com/item?id=48071940), "Using Claude Code: The unreasonable
effectiveness of HTML" — **528 points, 274 comments, 2026-05-09** — is a post *from the Claude Code
team* arguing for HTML over markdown as an agent output format. VERIFIED comment from that thread
(`gabesullice`):

> It's been confusing to me that so many people have treated markdown as the lingua franca for
> agent instructions when their training corpus must be dramatically biased to HTML instead of
> Mardown. Markdown only makes sense for us meatbags becuse it's easy for us to edit and version
> control

The nuance that *helps* the thesis: the same argument splits the world into "rich HTML for
decision surfaces, Markdown for durable records" — and this product is a durable-records product.
But it is a warning that "agents love markdown" is not a settled fact.

**(v) Agents want to *see* the document, which plaintext does not give them.**
From HN [48807225](https://news.ycombinator.com/item?id=48807225) (OfficeCLI), a genuinely
important disagreement. `rcarmo` (author of a competing OOXML MCP server) argues renders are
wasted tokens; `wongarsu` (VERIFIED):

> if you task Claude with making a moderately sized powerpoint matching existing style guides, it
> will spend at most 30% of the time on the initial version. The remaining time is spent rendering
> out slides, looking at them and adjusting them […] if you want good results where everything is
> aligned and has proper contrast you need a visual feedback loop

and `maxloh` (VERIFIED):

> I have had a lot of experience creating and editing PowerPoint slides with Claude recently. It
> always converts the file to a PDF using LibreOffice and then renders the PDF into images to see
> if everything went right and that no text has overflowed.

OfficeCLI's own README makes this its headline claim (VERIFIED fetch): *"OfficeCLI's built-in HTML
rendering engine reproduces documents with high fidelity — and that's what gives AI eyes."*
**For slides especially, "it's plaintext so the agent can read it" is not sufficient; the agent
needs a render loop.**

**(vi) The corporate world is not leaving .docx/.pptx.** Same thread, `SoftTalker` (VERIFIED):

> I don't think the corporate world is moving away from Word and PowerPoint anytime soon.

---

## B. The graveyard — what died, and why

### B.1 Graveyard table

| Project | What it was | Died when | Why (verified where quoted) |
|---|---|---|---|
| **Editorially** | Web collaborative Markdown editor for writers/editors; 11 staff | Announced 2014-02-12, offline 2014-05-30; team joined Vox Media 2014-06 | **Their own post-mortem, VERIFIED fetch:** *"Editorially has failed to attract enough users to be sustainable."* And on monetisation: *"Why not just charge for use? We thought of that, and in fact, it was always our plan to do so. But Editorially is a sophisticated application that requires a team of engineers to maintain and develop. **Even if all of our users paid up, it wouldn't be enough.**"* HN [7232778](https://news.ycombinator.com/item?id=7232778), 58p/58c. |
| **Penflip** | "GitHub for writers" — markdown + real git, bootstrapped solo founder. Launched into the Editorially vacuum | Gone. `penflip.com` is **NXDOMAIN** (VERIFIED: `curl` → "Could not resolve host") | Show HN [6617063](https://news.ycombinator.com/item?id=6617063) got **181 points, 81 comments** in 2013 — better HN reception than any 2026 git-backed markdown editor. It still died. Pricing plan stated in-thread: "free for public projects, small monthly fee (~$8) for private projects". Commenter `leobelle` at the time (VERIFIED): *"If you can get 1,000 paying customers you're doing really, really well… when I see sub-$20 plans and freemium it's such a warning signal."* |
| **Draft (draftin.com)** | Nate Kontny's collaborative markdown writing tool, the main Editorially alternative recommended on HN | Gone. `draftin.com` is **NXDOMAIN** (VERIFIED) | Simply wound down. |
| **Poetica** | Collaborative writing/editing, founded by a Twitter founding engineer, TechCrunch-covered (HN [7908740](https://news.ycombinator.com/item?id=7908740), 153p/40c) | Shutdown post 2016-03-01, HN [11421362](https://news.ycombinator.com/item?id=11421362) | Technology acquired by Condé Nast, public service discontinued. **VERIFIED from their own post:** *"Our technology and design enable the sort of collaboration that a few short years ago was only accessible to those who could climb the steep learning curve of arcane tools like git."* and *"we've tackled the dual problems of creating a humane, intuitive, and collaborative way to interact with text… and the parallel challenge of creating a viable business model. Unfortunately, these goals were often at odds with each-other."* **Their explicit conclusion was that hiding git was the value, and even so the business model fought the product.** |
| **Authorea** | "Google Docs/GitHub for scientists" — git-based collaborative research writing. Raised $610k seed (TechCrunch, 2014) | Acquired by Atypon/Wiley 2018-09, HN [17937942](https://news.ycombinator.com/item?id=17937942) | Absorbed into a publisher; the git-for-writing angle did not become the product. |
| **Stashpad** | Techstars-backed; "Stashpad Docs — a minimal Google Docs alternative with markdown support and no account required" | Fall 2024. HN [42181243](https://news.ycombinator.com/item?id=42181243) / [41294379](https://news.ycombinator.com/item?id=41294379) | **Their own wind-down page, VERIFIED fetch:** *"While we did not reach business viability, we learned a tremendous amount."* Notable: they got a TechCrunch launch (HN [39712573](https://news.ycombinator.com/item?id=39712573), 130p/68c) and still could not convert. |
| **EqualTo / Sheet Markup** | A spreadsheet-in-markdown DSL with real formulas — the single closest prior art to "Sheets = plaintext + formulas" — plus "Spreadsheets as a service" | `equalto.com` is **NXDOMAIN** (VERIFIED) | 120p/47c Show HN in 2023, an LLM angle spotted three years early, and it is gone. **This is the most directly relevant death in the whole table.** |
| **Skiff** | Privacy-first Docs/Drive/Mail suite | Acquired by Notion 2024-02, shut down within ~6 months; HN [39323973](https://news.ycombinator.com/item?id=39323973) "Skiff is shutting down in six months" | Acqui-killed. Left users so unhappy that HN threads titled "Notion's Lies Sunsetting Skiff Mail" (2025-04) and "Tell HN: Notion's Fraudulent Sunset of Skiff" (2025-02) followed. |
| **Coda** | Docs-as-apps, well funded, ~$1B+ valuation era | Acquired by Grammarly 2024-12-17, HN [42442852](https://news.ycombinator.com/item?id=42442852), 130p/83c | Not a failure exactly, but the independent "rethink the document" company did not stay independent. |
| **Hackpad** | Collaborative pads | Shut down 2017, migrated into Dropbox Paper (HN [14160835](https://news.ycombinator.com/item?id=14160835)) | Absorbed. |
| **Dropbox Paper** | Dropbox's Google-Docs competitor | Mobile app discontinued 2025-09; HN [45186011](https://news.ycombinator.com/item?id=45186011), 150p/121c | Even a company with 700M+ registered users and a filesystem could not make a document layer stick. |
| **Fargo** (Dave Winer) | Outliner over OPML files in Dropbox — the 2013 version of "your documents are just files in your sync folder" | **Retired end of September 2017** | **VERIFIED** — `fargo.io` now serves a "Fargo Retirement Page": *"Once upon a time, an application named Fargo resided at this location. It was a multi-tab outliner that used Dropbox for storage. Fargo was retired at the end of September 2017."* HN [5772623](https://news.ycombinator.com/item?id=5772623), 39p/33c. Same idea, twelve years earlier, from a well-known author with a built-in audience. |
| **Prose.io** | Web content editor writing markdown straight to a GitHub repo — "git is the drive" in 2012 | Site still returns HTTP 200 (VERIFIED) but the category never grew past static-site authors | HN [7691934](https://news.ycombinator.com/item?id=7691934), 101p/51c in 2014. It works. Nobody built an office suite on it. |
| **Fidus Writer** | Academic semantic word processor | Nearly died once publicly — the maintainers' own post is titled *"Is Fidus Writer dead?"* (2015-06), HN [9753565](https://news.ycombinator.com/item?id=9753565) | Survives on NLnet grant funding (HN [39452759](https://news.ycombinator.com/item?id=39452759)), not revenue. |
| **GitBook (v1)** | Markdown + git → books, MIT CLI, Show HN [7524956](https://news.ycombinator.com/item?id=7524956) **442 points** in 2014 | The open git-first toolchain was abandoned; the community forked it as **HonKit** (HN [23659451](https://news.ycombinator.com/item?id=23659451), 100p/36c, 2020) | **This is the pattern to study.** GitBook survived by *abandoning* the git-native local toolchain and becoming a hosted SaaS. The 442-point plaintext-and-git version is the part that got dropped. |
| `md-office`, `focal`, `collab-editor`, `gittype`, `citadelMD` | 2026 independent implementations of this exact product | Alive but at **0–1 GitHub stars** (VERIFIED via GitHub search API, 2026-08-28) | Not dead yet — just never alive. |
| **MarkdownOffice** | Self-described "LLM-first, Markdown-native office suite" | Never shipped — Substack + YouTube only, no repo, no site (per prior `RESEARCH.md` verification, 2026-08-28) | Vapour. |
| **Pithy** | The closest real competitor: git-backed markdown+CSV editor for AI-forward teams | Binaries built 2026-03-28, unchanged for 5 months; advertised repo `github.com/PithyDocs/pithy-app` 404s; `pithydocs.com` returns 522 (per prior `RESEARCH.md`) | **Stalled.** A well-built, well-positioned execution of exactly this thesis that stopped shipping. |

### B.2 The three causes of death, distilled

1. **The market is a feature, not a company.** Editorially's own words: *"Even if all of our users
   paid up, it wouldn't be enough."* Collaborative writing tooling has a low ceiling on
   willingness-to-pay and a high floor on engineering cost, because you are competing with a free
   product from a trillion-dollar company. Penflip, Draft, Stashpad, Poetica all hit the same wall.

2. **Git is the moat and the wall at the same time.** Every project that put git in front of
   non-developers either kept only developers (Prose.io, docs-as-code) or dropped git to grow
   (GitBook). The 2022 HN thread on how non-programmers version things — dated filenames and
   Dropbox — is twelve years of consistent evidence that the target user does not want the
   headline feature.

3. **Acquisition is the exit, and the acquirer kills the product.** Skiff→Notion→dead.
   Authorea→Wiley. Coda→Grammarly. Hackpad→Dropbox Paper→also dying. If you build this well, the
   most likely good outcome is a small acquihire, not a durable business.

### B.3 The enthusiasm curve is going the wrong way

The uncomfortable longitudinal fact, all VERIFIED from HN Algolia:

| Year | Product | Pitch | HN reception |
|---|---|---|---|
| 2013 | Penflip | "A Github for writers?" | **181 points, 81 comments** |
| 2014 | GitBook v1 | markdown + git → books | **442 points, 78 comments** |
| 2014 | Prose.io | web editor writing markdown to a GitHub repo | 101 points, 51 comments |
| 2023 | EqualTo Sheet Markup | spreadsheets with formulas inside markdown | 120 points, 47 comments |
| 2026 | Moment.dev | "displace Notion with collaborative Markdown files" | **29 points, 14 comments** |
| 2026 | Perchpad | "Collaborative real-time Markdown editor backed by Git" | **2 points, 2 comments** |

**HN's appetite for "git for writing" peaked in 2014 and has declined for twelve years.** The 2026
cohort is not landing on a receptive audience that has been waiting; it is landing on an audience
that has watched this fail four times. Meanwhile the 2026 attention went to OfficeCLI (29k stars,
keeps .docx) and to the *knowledge-base* framing (OpenKnowledge 381 pts), not to the office-suite
framing.

---

## C. The AI-agent-native angle — how real is it?

**Bottom line up front:** the *pain* is completely real and independently documented across the
whole MCP ecosystem. The *proposed cure* (a plaintext office suite) is not the cure the market
picked. In 2026 the incumbents shipped in-place agentic editing, and the strongest open-source
challenger (GenOffice, 3.8k stars in four weeks) attacks the same problem by making OOXML
agent-friendly rather than by replacing it with markdown. The durable, defensible slice of the
thesis is **markdown + git as the substrate for agent-maintained knowledge work** — which
Karpathy blessed in April 2026 and which now has real, quantified traction — not "a Google
Workspace clone."

---

### 1. MCP servers for documents/office: what exists, and what's broken

#### 1.1 There is no official reference server for any office product — and Google Drive was *removed*

**VERIFIED** — `https://raw.githubusercontent.com/modelcontextprotocol/servers/main/README.md`
(fetched 2026-08-28). The reference server list maintained by the MCP steering group is now only
seven servers: Everything, Fetch, **Filesystem**, **Git**, Memory, Sequential Thinking, Time.

There is no Docs, Sheets, Slides, Word, Excel, PowerPoint, Notion, or Office server. And Google
Drive is explicitly listed under **"### Archived"**:

> - **[Google Drive](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/gdrive)** - File access and search capabilities for Google Drive.

**This is the single most on-thesis fact in the whole area.** The only two document-substrate
servers the MCP steering group still maintains are *the filesystem* and *git*. The officially
blessed way for an agent to touch documents is: files on disk, versioned in git. The Google Drive
path was tried and archived.

#### 1.2 The third-party ecosystem is large, fragmented, and unofficial

**VERIFIED** — GitHub search API via authenticated `gh api search/repositories`, 2026-08-28.
Topic counts: `mcp-server google docs` = 38 repos, `google sheets` = 33, `notion` = 58,
`excel` = 69, `office` = 67, `powerpoint` = 38, `word docx` = 24.

| Repo | Stars | Created | Last push | Note |
|---|---:|---|---|---|
| [makenotion/notion-mcp-server](https://github.com/makenotion/notion-mcp-server) | 4,610 | 2025-03-10 | 2026-07-25 | **Official Notion.** 187 open issues |
| [haris-musa/excel-mcp-server](https://github.com/haris-musa/excel-mcp-server) | 4,144 | 2025-02-12 | 2026-04-12 | Community. Unmaintained ~4 months |
| [microsoft/mcp](https://github.com/microsoft/mcp) | 3,618 | 2025-04-09 | 2026-08-28 | Microsoft's official catalog |
| [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) | 3,081 | 2025-04-27 | 2026-08-28 | **Community, not Google.** 184 open issues |
| [xing5/mcp-google-sheets](https://github.com/xing5/mcp-google-sheets) | 989 | 2025-03-22 | 2026-05-14 | Community |

The de-facto standard Google Workspace MCP server is a *community* project by one maintainer
(taylorwilsdon), not Google's.

#### 1.3 Official vendor servers — all three now exist, all three are thin

**Notion (official)** — VERIFIED, 4,610 stars, 187 open issues.

**Microsoft** — VERIFIED, `https://raw.githubusercontent.com/microsoft/mcp/main/README.md`. The
official catalog contains M365 Calendar, Mail, User, Copilot Chat, Teams, OneDrive/SharePoint,
SharePoint Lists, and exactly one document app server:

> ### 📄 Microsoft Word
> - **DESCRIPTION**: MCP Server containing tools to work with Microsoft Word documents. Enables
>   reading and understanding documents, creating new ones, and collaborating through comments.
> - **TYPE**: `REMOTE` - `https://agent365.svc.cloud.microsoft/agents/tenants/{tenant_id}/servers/mcp_WordServer`

Read, create, comment — **not edit an existing document**. And there is **no official Excel or
PowerPoint MCP server at all** in Microsoft's catalog.

**Google (official, new in 2026)** — VERIFIED,
`https://developers.google.com/workspace/docs/api/guides/configure-mcp-server`. Google now ships
first-party Docs/Sheets/Drive MCP servers. The Docs server exposes exactly two tools:

> The following tools are available for the Google Docs MCP server:
> - `read_doc`
> - `update_doc`

Status: **Developer Preview** only — "Available as part of the Google Workspace Developer Preview
Program." The page's only substantive caveat section is about prompt injection:

> "Because MCP hosts like Google Antigravity have access to powerful tools and APIs through the
> Google Docs MCP server, they can read, modify, and delete data in your Google Account."

A 2026-07-16 review (**VERIFIED**, `https://www.usecarly.com/blog/google-docs-mcp/`) is blunter:
it "requires creating a Google Cloud project, enabling two APIs, and configuring an OAuth consent
screen yourself"; "You own the plumbing, the project, and the scopes"; and

> "The Docs MCP server is a way to _ask_ about a document and make one-off edits mid-conversation.
> It is not a way to make Docs work **run**."

#### 1.4 The limitations, with receipts

**(a) Token cost of reading documents through an API is the #1 complaint — and markdown is the fix everyone independently reaches for.**

- **VERIFIED** — [makenotion/notion-mcp-server#330](https://github.com/makenotion/notion-mcp-server/issues/330),
  opened 2026-07-10, still open:
  > "The server's 24 tools cost **~21,411 tokens** (tiktoken cl100k) at `tools/list` — the heaviest
  > of 20 popular servers we measured. The descriptions are terse (nice!); the weight is schemas…
  > the same Notion object subtrees inlined into tool after tool."

  That is ~21k tokens of *tool definitions* consumed before the agent reads a single word of a document.

- **VERIFIED** — Notion's own fix, [PR #320 "Add page-as-Markdown tools (retrieve + update)"](https://github.com/makenotion/notion-mcp-server/pull/320),
  merged 2026-06-17. The official server added a *markdown* projection of Notion pages.

- **VERIFIED** — [Grey-Iris/easy-notion-mcp](https://github.com/Grey-Iris/easy-notion-mcp) README:
  > "Reading a page's content costs about **6–7× fewer response tokens** than the official Notion
  > MCP server, because Notion's raw block JSON carries per-block metadata (block IDs, timestamps,
  > author objects) that an agent reading for content never needs."

  **Important honest caveat from the same README** (this cuts against a naive version of the thesis):
  > "The win is metadata omission, not encoding efficiency. At equal information the two formats
  > cost about the same (the common intermediate-representation ratio is ~1.0–1.06× on fully
  > represented page shapes, and 1.32× on typical prose)."

  Markdown is not intrinsically cheaper than JSON. It is cheaper because it *drops the metadata an
  agent doesn't need*. Same effect, different mechanism — worth being precise about in a pitch.

- **VERIFIED** — [haris-musa/excel-mcp-server#92](https://github.com/haris-musa/excel-mcp-server/pull/92),
  2025-08-23, merged. Task link field reads verbatim:
  > "**Task:** User feedback - Excel MCP tool returns excessive metadata making it unusable for AI
  > agents needing clean data"

  It replaced the reader with a sparse one for a **92.5% output reduction (31,362 → 2,362 characters)**.

- **VERIFIED** — [haris-musa/excel-mcp-server#139](https://github.com/haris-musa/excel-mcp-server/pull/139),
  2026-06-17, still open. Benchmarked JSON→GCF encoding on realistic Excel payloads: 697,319 →
  291,311 tokens, **58.2% reduction**. A 500×20 sheet costs **410,053 tokens** as JSON.

**(b) Formatting fidelity is genuinely lossy through the API layer.**

- **VERIFIED** — [makenotion/notion-mcp-server#266](https://github.com/makenotion/notion-mcp-server/issues/266),
  2026-04-12, open: "Multi-row `<table>` silently collapses to single row in Enhanced Markdown converter."
  > "a `<table>` with `<tr>` and `<td>` elements written inline on the same line is silently
  > collapsed into a single `<tr>` containing all `<td>` cells from all original rows. **No error or
  > warning is returned — the row grouping is lost without any signal to the caller.**"

- **VERIFIED** — google_workspace_mcp has repeated PRs titled
  [`fix(utils): preserve Word text fidelity in extract_office_xml_text`](https://github.com/taylorwilsdon/google_workspace_mcp/pull/1071)
  (#1059 and #1071, both 2026-08-25/27) and
  [`fix(utils): distinguish an unreadable Office file from an empty one`](https://github.com/taylorwilsdon/google_workspace_mcp/pull/1060).
  Text extraction from OOXML is still being patched in August 2026.

**(c) The "can't edit an existing doc" gap — filed against Anthropic itself.**

**VERIFIED** — [anthropics/claude-code#83942](https://github.com/anthropics/claude-code/issues/83942),
opened **2026-08-04**, **still open**, 2 👍:

> "The built-in Google Drive/Docs MCP supports create, read, copy, and search, but has **no tool to
> edit an existing Google Doc**. Once a doc exists, Claude can't update it in place."
>
> "I'm a PM using Claude Code to author living documents (Feature Overviews for sales/CX). Every
> revision forces `create_file` → a **brand-new doc each time**: new URL, lost comments/history/
> sharing settings, and orphaned copies I can't even delete via the connector. In one session I had
> to recreate the same doc **four times** for minor edits."

Note it also records that this is a *solved problem for a competitor*: "OpenAI Codex already does
this today via its connected Google account — targeted `documents.batchUpdate` edits… with a
revision ID for safe concurrent writes." The reporter says a prior filing (#72576) was auto-closed
by a bot as `not_planned`/`invalid`.

**(d) The whole ecosystem is converging on "convert it to markdown."**

- **VERIFIED** — [microsoft/markitdown](https://github.com/microsoft/markitdown): **176,797 stars**
  (created 2024-11-13, pushed 2026-08-19). "Python tool for converting files and office documents
  to Markdown." It is listed in Microsoft's *own* official MCP catalog. Microsoft ships one of the
  most-starred repos on GitHub whose entire job is turning Office documents into markdown so LLMs
  can read them.
- **VERIFIED** — [dealfluence/adeu](https://github.com/dealfluence/adeu), 149 stars, created
  2025-12-30. Tagline verbatim:
  > "**LLMs speak Markdown; reviewers speak 'Track Changes.'**"
  > "Adeu solves this by translating `.docx` files into a token-efficient Markdown representation.
  > This frees AI agents to focus entirely on document semantics instead of **wasting tokens
  > wrestling with OpenXML**."

  It ships as a Claude Code plugin *and* an Agent Skill, and applies edits back as native Word
  tracked changes.
- **VERIFIED** — `n24q02m/better-notion-mcp`, `Grey-Iris/easy-notion-mcp`: both self-describe as
  "Markdown-first … for AI agents."

**Read this correctly:** three independent teams, plus Microsoft, plus Notion itself, all
concluded the agent-facing representation of a document should be markdown. That is powerful
validation of *markdown as the agent interface* — and simultaneously the strongest argument that
you don't need a new office suite to get it. A translation layer is enough.

---

### 2. Do people actually do document work with markdown + git + agents?

Yes — and 2026 is the year it went mainstream, but under the banner of **knowledge bases**, not
office documents.

#### 2.1 The Karpathy "LLM Wiki" moment (the single biggest datapoint)

**VERIFIED** — HN story [id=47640875](https://news.ycombinator.com/item?id=47640875),
**296 points, 95 comments, 2026-04-04**, linking
`https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`.

I fetched the raw gist. It describes exactly the substrate in question:

> "**Raw sources** — your curated collection of source documents… These are immutable.
> **The wiki** — a directory of LLM-generated markdown files… The LLM owns this layer entirely.
> **The schema** — a document (e.g. CLAUDE.md for Claude Code or AGENTS.md for Codex) that tells
> the LLM how the wiki is structured."

> "In practice, I have the LLM agent open on one side and Obsidian open on the other… **Obsidian
> is the IDE; the LLM is the programmer; the wiki is the codebase.**"

> "**The wiki is just a git repo of markdown files. You get version history, branching, and
> collaboration for free.**"

And, notably for the slides layer of the pitch:

> "**Marp** is a markdown-based slide deck format. Obsidian has a plugin for it. Useful for
> generating presentations directly from wiki content."

Karpathy is independently prescribing markdown + git + agent + Marp-for-slides. That is most of
the product thesis, published by the most-followed practitioner in the field, in April 2026.

#### 2.2 The wave it produced (all VERIFIED via HN Algolia API)

| HN id | Title | Points | Comments | Date |
|---|---|---:|---:|---|
| [48675435](https://news.ycombinator.com/item?id=48675435) | Show HN: OpenKnowledge – open source AI-first alternative to Obsidian/Notion | **381** | 173 | 2026-06-25 |
| [47640875](https://news.ycombinator.com/item?id=47640875) | LLM Wiki – example of an "idea file" (Karpathy) | **296** | 95 | 2026-04-04 |
| [47899844](https://news.ycombinator.com/item?id=47899844) | Show HN: A Karpathy-style LLM wiki your agents maintain (Markdown and Git) | **260** | 114 | 2026-04-25 |
| [48995181](https://news.ycombinator.com/item?id=48995181) | Show HN: CodeAlmanac – Karpathy-style codebase wiki from your conversations | 60 | 21 | 2026-07-21 |
| [48351115](https://news.ycombinator.com/item?id=48351115) | Karpathy LLM Wiki pattern integrated into Obsidian agentic workflow | 28 | 9 | 2026-06-01 |
| [46589926](https://news.ycombinator.com/item?id=46589926) | Show HN: Pane – An agent that edits spreadsheets | 32 | 10 | 2026-01-12 |
| [47236374](https://news.ycombinator.com/item?id=47236374) | Show HN: We want to displace Notion with collaborative Markdown files (moment.dev) | 29 | 14 | 2026-03-03 |

Repo traction (**VERIFIED** via `gh api`, 2026-08-28):
- `inkeep/open-knowledge` — **3,675 stars**, created 2026-06-03 (≈3 months). "Beautiful, AI-native
  markdown IDE and LLM wiki."
- `nex-crm/wuphf` — **1,248 stars**, created 2026-03-25.

OpenKnowledge's Show HN text (**VERIFIED**):
> "We built this because we wanted a Notion-like experience for writing and sharing markdown files
> across our team. Obsidian is the best alternative we tried, but found it doesn't have a true
> WYSWIG UI and **it didn't integrate well with Claude/Codex outside of community plugins**."

#### 2.3 The long tail is enormous but shallow

**VERIFIED** via HN Algolia. There is a constant stream of Show HNs on this exact idea, and almost
all of them get single-digit points:

- Perchpad ("Collaborative real-time Markdown editor backed by Git") — [46919903](https://news.ycombinator.com/item?id=46919903),
  **2 points, 1 comment**, 2026-02-07.
- Flashtype ("Markdown editor for Claude and Codex with in-line diffs") — [48764289](https://news.ycombinator.com/item?id=48764289), 5 pts, 2026-07-02.
- Nimbalyst — [47962230](https://news.ycombinator.com/item?id=47962230), 8 pts; [48108137](https://news.ycombinator.com/item?id=48108137), 7 pts.
- Quillium "Git for Writers" — [47483896](https://news.ycombinator.com/item?id=47483896), 6 pts, 2026-03-23.
- GitWriter — [46943159](https://news.ycombinator.com/item?id=46943159), 5 pts, 2026-02-09.
- Strata ("real-time Markdown editor you can mount as a filesystem") — [48748000](https://news.ycombinator.com/item?id=48748000), 5 pts.
- Mkdnsite, MarkdownLM, Kilroy, Memoriki, Cortex, Zendoc, MEO, wrds.cc — all 1–6 points.

**Honest read:** the *pattern* breaks out (296–381 pts when framed as "agent-maintained knowledge
base"). The *products* do not (2–8 pts when framed as "markdown editor with git"). Framing is
doing enormous work here, and the market is crowded with identical unnoticed attempts.

#### 2.4 Counter-evidence from the same threads (real quotes, all VERIFIED)

- **"Why not just git?"** — `DerArzt`, [47253773](https://news.ycombinator.com/item?id=47253773),
  on moment.dev:
  > "I'm not understanding the value here. If I'm writing markdown and avoiding notion, what does
  > this provide my team that git does not? I can easily write the markdown docs and they will
  > render fin in most git forges."

- **Plaintext isn't the moat; collaboration is.** moment.dev's own team, `litacho1`,
  [47242524](https://news.ycombinator.com/item?id=47242524):
  > "We think Claude Code is great for single-player, but it breaks down when you want to share
  > with your team."

- **Markdown ≠ enough.** `jfim`, [48678774](https://news.ycombinator.com/item?id=48678774), on OpenKnowledge:
  > "Obsidian is a lot more than 'just markdown' though. For example, with the appropriate plugins
  > like dataview and charts, it's possible to create dashboards, lists, and tables that update
  > automatically… **I'd love to migrate away from Obsidian towards something that's not
  > proprietary, but I haven't seen anything that allows querying other documents.**"

- **Files alone don't serve agents — you still need an MCP surface.** `najmuzzaman` (wuphf),
  [47901876](https://news.ycombinator.com/item?id=47901876):
  > "Agents need an MCP surface. An Obsidian plugin API won't do. `/lookup`, `entity_fact_record`,
  > `notebook_write`, and `team_wiki_promote` are MCP tools the agent runtimes call directly."

- **Scope objection.** `nashashmi`, [47236771](https://news.ycombinator.com/item?id=47236771):
  > "Notion is a lot of things; pages, triggers, actions, databases, and agents. **You are focusing
  > only on pages.**"

- **General skepticism.** `imafish`, [47900185](https://news.ycombinator.com/item?id=47900185):
  > "Cool idea. But is anyone actually building real stuff like this with any kind of high quality?
  > Every time I hear someone say 'I have a team of agents', what I hear is 'I'm shipping heaps of
  > AI slop'."

- **The spreadsheet-specific killer objection.** `ashwindharne`,
  [46591742](https://news.ycombinator.com/item?id=46591742), on the Pane thread — this person is
  building a competing Excel add-in:
  > "by far the hardest part is figuring out the right representation for a spreadsheet workbook and
  > the right primitives for the agent to be able to navigate it adeptly and cost-effectively;
  > **structure is incredibly variable and the data just compresses rather poorly (values, formulas,
  > formatting, charts, pivots, etc.)**"

  CSV + a formula sidecar does not automatically solve representation. It just moves it.

- **But also the best pro-thesis anecdote**, `mattmm11`,
  [46611531](https://news.ycombinator.com/item?id=46611531), 2026-01-14:
  > "Yesterday I was trying to have Gemini help put together a toy model to calculate some financial
  > scenarios in Sheets, and **it struggled mightily. The biggest challenge was it didn't have a
  > good way to port formulas over into specific cells, so I basically had a CSV and a bullet list
  > of formulas to put in by hand.**"

  And `subpixel`, [46593169](https://news.ycombinator.com/item?id=46593169):
  > "Gemini in sheets is not that hot yet… But if I ask Gemini to build be formulas and than just
  > paste them into Google Sheets the results are pretty darn good."

  The model can do the work; the *transport into the document* is the broken part. That is precisely
  the gap the thesis targets.

**Methodological note:** Reddit's JSON API returned HTTP 403 from this environment
(`www.reddit.com` and `old.reddit.com`, with a browser UA), and Anthropic's WebSearch tool refuses
`reddit.com` as a domain. **I have no verified Reddit data.** Any Reddit claims elsewhere in this
research should be treated as unverified.

---

### 3. Incumbent moves — the gap largely closed in 2026

This is the part of the landscape that has changed most since the thesis was first plausible, and
it is mostly bad news for the pitch.

**Anthropic**
- File creation (.xlsx/.docx/.pptx/.pdf) — **VERIFIED**,
  `https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude`:
  > "Code execution and file creation is available to all Claude users (Free, Pro, Max, Team, and
  > Enterprise) on the web, Claude Desktop, and Claude Mobile."

  Max file size 30 MB. The help page is oriented to *creation*; it does not document robust in-place
  editing of an uploaded file.
- **Claude for Microsoft 365 — GA 2026-05-07.** **VERIFIED**,
  `https://claude.com/blog/collaborate-with-claude-across-excel-powerpoint-word-and-outlook`
  (published 2026-05-07). Excel, PowerPoint and **Word all generally available**; Outlook in public
  beta; paid plans, Mac + Windows. Verbatim:
  > "Adjust an assumption in Excel and the chart in PowerPoint and the number in your Word memo
  > automatically update, too."
- **REPORTED** (search snippets, not fetched): Claude Office add-ins run as task-pane add-ins that
  "can edit cells, draft slides, or rewrite paragraphs **in place**"; Word edits reportedly land as
  **native tracked changes**; Claude described as the first non-Microsoft model shipping natively
  across the full Office suite. File creation opened to free accounts 2026-02-11.

**Microsoft**
- **Copilot agent mode GA in Word, Excel and PowerPoint — 2026-04-22.** **VERIFIED**,
  `https://www.microsoft.com/en-us/microsoft-365/blog/2026/04/22/copilots-agentic-capabilities-in-word-excel-and-powerpoint-are-generally-available/`:
  > Excel: "Copilot helps you explore data, build and explain analysis, and **make changes directly
  > in your workbook**—from formulas to tables to visuals"
  > PowerPoint: "…**updating existing decks** with the latest talking points, and data"
  > "Copilot can take multi-step, app-native actions directly in your documents, worksheets, and
  > presentations"

  Included in M365 Copilot, M365 Premium, and **M365 Personal and Family**. The page's own roadmap
  language concedes remaining weakness — it promises "deeper, **more reliable** editing for complex
  workflows," which implies today's is not.
- **REPORTED**: Excel agent mode rolled out on Web in Dec 2025, Desktop/Mac in Jan 2026; Word agent
  mode Nov 2025.

**Google**
- **VERIFIED**: first-party Docs / Sheets / Drive MCP servers now exist, in **Developer Preview**
  (§1.3). Sheets MCP lets agents "read cell values or updating formulas." These are explicitly
  designed to let "AI applications like Google Antigravity **and Claude**" act in Workspace.

**What this means for the thesis.** In January 2026 the honest pitch was "agents literally cannot
edit your documents." By August 2026 that is no longer true: Microsoft's own agent edits Office
files in place (GA April), Anthropic's add-in does too (GA May), and Google exposes `update_doc`
to third-party agents (preview).

**What is still true — and it is the narrower, sharper wedge:**
1. **It's the vendor's model in the vendor's app.** Copilot agent mode is Copilot. Claude for Excel
   is a sidebar bound to Claude's cloud. Neither is *your* Claude Code session on *your* laptop
   with *your* CLAUDE.md, subagents, skills, and shell tools.
2. **Claude Code still cannot edit a Google Doc** — [claude-code#83942](https://github.com/anthropics/claude-code/issues/83942)
   is open as of 2026-08-04 (§1.4c). The gap exists *inside Anthropic's own product line*.
3. **No diffs, no branches, no review.** Nothing in the incumbent stack gives you `git diff` on a
   deck, a PR on a memo, or a bisect on a financial model.
4. **Google's is preview-gated and needs a GCP project + OAuth consent screen** to use.

---

### 4. Startups in the space

#### 4.1 Nobody is shipping the exact pitch (docs=md + sheets=CSV/formulas + slides=md, git-backed)

Closest, all **VERIFIED** to exist:

| Product | What it is | Gap vs. the pitch |
|---|---|---|
| [Pithy](https://pithy.md) | Git-backed markdown + CSV editor, explicit "agents edit the files" pitch | **No slides.** Source repo 404s; binaries unchanged since 2026-03-28 (per prior `RESEARCH.md`) |
| [Perchpad](https://perchpad.co) | Git-native md + csv workspace, MCP server, realtime collab | **No slides.** Show HN got **2 points** |
| [moment.dev](https://www.moment.dev/) | Markdown files in git (jj), realtime collab, programmable | **Docs only** |
| [OpenKnowledge](https://github.com/inkeep/open-knowledge) | WYSIWYG markdown IDE, direct Claude/Codex/Cursor integration, 3,675★ | **Docs only.** No sheets, no slides |
| [Nimbalyst](https://github.com/nimbalyst/nimbalyst) | md/CSV/Mermaid editors + built-in git | Framed as agent workspace, slides only via SDK extension |

**Finding: the "docs + sheets + slides, all plaintext, git as the drive" suite does not exist.**
That is genuinely open — but note that everyone who gets close stops at docs, and the two who added
sheets (Pithy, Perchpad) both stalled or got no traction.

#### 4.2 The money is going the *other* way — into AI inside Excel

- **Shortcut** (shortcut.ai), by Fundamental Research Labs — **REPORTED** (TechCrunch 2025-08-01 +
  search snippets): raised **$33M** in Aug 2025 from Prosus, and reportedly **$40M** total including
  a16z, Eric Schmidt's First Spark, Patrick Collison, Balaji Srinivasan. It is an **Excel add-in and
  agent**, not a plaintext tool. Claimed to beat first-year McKinsey/Goldman analysts 89.1% of the time.
- **Quadratic** (quadratichq.com) — **VERIFIED** (fetched). "Connect your data, ask AI, and get
  powerful, shareable, and repeatable code-based spreadsheets." Ships an **MCP server + Spreadsheet
  API** — "trigger AI runs, read and write cells, and orchestrate agents from your own code."
  Python/SQL/JS cells, 100M rows. It is the closest thing to an agent-native spreadsheet, but its
  storage format is not documented as plaintext/git-friendly.
- Also real, all AI-on-top-of-grid rather than plaintext: Rows, Sourcetable, Pane (paneapp.com),
  Banker (banker.so).

#### 4.3 The most important competitor: GenOffice

**VERIFIED** — [genspark-ai/genoffice](https://github.com/genspark-ai/genoffice), created
**2026-07-31**, **3,860 stars and 629 forks in under four weeks**, Apache-2.0,
`https://genoffice.ai/`. README verbatim:

> "GenOffice is a free, open-source alternative to Microsoft Office… built around **AI editing as a
> first-class workflow rather than a bolted-on chat box**."
> - "**Microsoft Word–compatible, byte-preserving `.docx` editing** — only what you touched changes;
>   Word never notices."
> - "**AI that edits documents** — block-level edits with snapshots and diffs, document-aware agents."
> - "**Bring your own key (BYOK)** — run the AI on your own API key: Claude, OpenAI, Gemini, DeepSeek…"

**REPORTED** (press): built by roughly one engineer in about a week for ~$10k of AI tokens.

This is the sharpest strategic threat. It solves the *same user problem* — agents that edit
documents, with diffs and snapshots, on your own model key — while keeping `.docx`/`.xlsx`/`.pptx`
compatibility, so there is **zero migration cost and no interop tax**. It got in four weeks the
traction Pithy and Perchpad never got. It concedes nothing on format and wins anyway.

---

### 5. Verdict

### Sharpest evidence FOR "AI agents need plaintext office files"

1. **The MCP steering group's only surviving document servers are Filesystem and Git; Google Drive
   was archived.** (VERIFIED, modelcontextprotocol/servers README.) The protocol's own maintainers
   converged on files-on-disk.
2. **microsoft/markitdown has 176,797 stars.** Microsoft's own most-starred AI tool exists purely to
   turn Office documents into markdown for LLMs. The industry has already voted on the agent-facing
   representation.
3. **Karpathy published markdown + git + agent + Marp-for-slides as the pattern (2026-04-04, 296 HN
   pts)**, explicitly: "The wiki is just a git repo of markdown files. You get version history,
   branching, and collaboration for free." A 381-pt and a 260-pt Show HN followed within ten weeks.
4. **Hard numbers on the API tax:** ~21,411 tokens of Notion tool schemas per session (#330);
   410,053 tokens for a 500×20 Excel read as JSON (#139); "excessive metadata making it unusable for
   AI agents" → 92.5% reduction (#92); 6–7× token savings from markdown projection (easy-notion-mcp).
5. **The gap is documented inside Anthropic's own tracker.** claude-code#83942, open 2026-08-04:
   "In one session I had to recreate the same doc **four times** for minor edits."
6. **Silent data loss through the API path:** Notion's markdown converter collapses multi-row tables
   "without any signal to the caller" (#266).

### Sharpest evidence AGAINST

1. **The gap closed in 2026.** Microsoft Copilot agent mode GA in Word/Excel/PowerPoint
   **2026-04-22** — "make changes directly in your workbook." Claude for M365 GA **2026-05-07**.
   Google's `update_doc` MCP tool is live in preview. The premise "agents can't edit documents" now
   needs qualifying to "agents *of my choosing* can't."
2. **GenOffice proves you can solve it without plaintext** — byte-preserving `.docx` editing, agent
   diffs and snapshots, BYOK, Apache-2.0, **3,860 stars in four weeks**, zero migration cost.
3. **The translation layer is sufficient.** markitdown, adeu, easy-notion-mcp, and Notion's own
   `page-as-Markdown` PR all deliver "agents see markdown" without anyone changing where their
   documents live. Adeu even round-trips back to Word tracked changes.
4. **Markdown is not intrinsically cheaper.** easy-notion-mcp's own benchmark: "At equal information
   the two formats cost about the same… the win is metadata omission, not encoding efficiency."
5. **Spreadsheets are the unsolved part, and plaintext doesn't solve them.** A competing builder,
   verbatim: "structure is incredibly variable and the data just compresses rather poorly (values,
   formulas, formatting, charts, pivots, etc.)."
6. **"What does this give me that git doesn't?"** is the first question real users ask (moment.dev
   thread), and the honest answer from moment.dev's own founders is *collaboration* — which is a
   hard multiplayer-CRDT problem, not a file-format problem.
7. **Demand signal is framing-dependent and brutally so.** "Karpathy-style LLM wiki your agents
   maintain" = 260 pts. "Collaborative real-time Markdown editor backed by Git" = **2 pts**. Same
   substrate. Pithy and Perchpad, the two closest existing products, are stalled and unnoticed.
8. **Capital is flowing to Excel add-ins** ($33–40M into Shortcut), not plaintext suites.

### Net read

The agent-native angle is **real as a pain and real as a pattern, weak as a product category**.

- The pain is documented with numbers, in public issue trackers, by the vendors themselves.
- The winning *pattern* is markdown + git + agent — but for **knowledge bases and living documents**,
  which is where all the 2026 breakout traction (Karpathy, OpenKnowledge, wuphf) actually is.
- The losing *framing* is "office suite." Every project pitched that way is invisible, and the
  incumbents plus GenOffice now cover the office-file use case with better compatibility.
- **Sheets is the only genuinely unclaimed hard problem** (CSV can't hold formulas; nobody has
  shipped a good git-diffable spreadsheet), and it is unclaimed because it is *hard*, not because
  it's been overlooked.

If this product is built, the defensible story is not "Google Workspace but plaintext." It is
"**the git-versioned substrate an agent maintains for you**" — with the slides layer (wrap Marp,
which Karpathy already recommends) and a real formula story as the two things nobody else has.

---

## D. Business model reality — how comparables monetize, and how big they are

### 1. Comparables table

| Product | Model | Price (verified) | Revenue / users | Source | Status |
|---|---|---|---|---|---|
| **Obsidian** | Free local app; paid Sync/Publish/Catalyst/optional Commercial | Sync $4/user/mo annual ($5 monthly); Publish $8/site/mo annual ($10 monthly); Catalyst $25 one-time; Commercial $50/user/yr (**optional** since 2025-02-20) | "we probably have three or four million users, and we're seven people" — CEO Steph Ango | [obsidian.md/pricing](https://obsidian.md/pricing); [obsidian.md/blog/free-for-work](https://obsidian.md/blog/free-for-work/); [Dialectic ep. 8, 2025-02-03](https://jacksondahl.com/dialectic/steph-ango) | **VERIFIED** |
| Obsidian ARR | — | — | ~$2M (Getlatka/Fueler) up to $25M (viral Apr 2026 post); Obsidian has **never** disclosed revenue | [BigGo 2026-04-06](https://finance.biggo.com/news/iVboYp0Bga3fZL9MJEv_) explicitly says "according to third-party estimates"; [OperatorBook](https://www.operatorbook.dev/stories/obsidian-revenue-estimates-2m-to-25m) | **REPORTED** (wide, unsourced) |
| **Notion** | SaaS seats + AI | $10–$20/seat/mo tiers | ARR $610M end-2025 (+53% YoY); $865M July 2026; $11B valuation (Jan 2026 tender); ~$344M primary raised; >50% of ARR from AI-enabled customers | [Sacra](https://sacra.com/c/notion/) | **REPORTED** |
| **Airtable** | SaaS seats | — | **$480M ARR, >20% YoY, >500,000 organisations, 80% of Fortune 100** (June 2026). Sold to Bending Spoons 2026-08-04: **$1.285B enterprise value / ~$2.25B equity value** | [Bending Spoons investor newsroom, 2026-08-04](https://investors.bendingspoons.com/newsroom/bending-spoons-agrees-to-acquire-airtable) | **VERIFIED** |
| Airtable history | — | — | Raised >$1.4B; peak valuation **$11.7B** (2021 Series F). Exit ≈ **2.7× ARR**, ~89% below peak | [TechCrunch 2026-08-04](https://techcrunch.com/2026/08/04/bending-spoons-to-buy-airtable-for-1-28b/); [Fortune 2026-08-05](https://fortune.com/2026/08/05/bending-spoons-italian-unicorn-startup-airtale-ipo/) | **VERIFIED** (raise/valuation), multiple |
| **Coda** | SaaS seats (docs+tables) | — | ~$41.1M ARR 2024 (from $26.8M 2023); $240M total raised; $1.4B valuation (Series D, July 2021, Ontario Teachers') | [Getlatka](https://getlatka.com/companies/coda); [Forbes 2021-07-08](https://www.forbes.com/sites/rashishrivastava/2021/07/08/all-in-one-doc-startup-coda-reaches-14-billion-valuation-in-100-million-raise-from-a-major-pension-fund/) | ARR **REPORTED**; funding **VERIFIED** |
| Coda exit | Acquired by Grammarly, announced **2024-12-17**, closed Jan 2025. Terms **undisclosed**. Coda CEO Shishir Mehrotra became Grammarly CEO. Grammarly then bought Superhuman (2025-07-01) | — | Grammarly: 40M active users, $13B valuation at time of deal | [TechCrunch 2024-12-17](https://techcrunch.com/2024/12/17/grammarly-acquires-productivity-startup-coda-brings-on-new-ceo) | **VERIFIED** (event), terms undisclosed |
| **Grist** (Grist Labs) | Open core (grist-core, Apache-2.0) + cloud + paid self-host | Free (5k rows/doc); Pro $10/user/mo ($8 annual); Business $30/user/mo ($24 annual, min 5); **Self-hosted paid $30/user/mo ($24 annual)**; Enterprise custom (min 50 users); **free self-host activation key for orgs <$1M annual revenue/funding**; 50% nonprofit discount | Seed round closed early 2026, led by angel **Perry Tam**, amount undisclosed. New CEO Anais Concepcion; hired a CRO (ex-OSI ED Stefano Maffulli) Apr 2026 | [getgrist.com/pricing](https://www.getgrist.com/pricing/); [getgrist.com blog 2026-04-24](https://www.getgrist.com/blog/a-new-chapter-for-grist-labs-scaling-for-the-era-of-sovereignty/) | **VERIFIED** (pricing, leadership); amount undisclosed |
| Grist public-sector traction | France's **La Suite numérique** (DINUM/ANCT) | — | **20,000 MAU in French public administration in Jan 2026, vs 2,000 in Jan 2025 (10×)**; 15 ministries, all 100 prefectures, Lyon and Strasbourg. France is "the largest contributor to the project, alongside the original developer" — contributing code upstream for 3 years, no fork | [EC Interoperable Europe / OSOR, 2026-01-26](https://interoperable-europe.ec.europa.eu/collection/open-source-observatory-osor/news/grist-joins-suite-numerique-public-administration) | **VERIFIED** |
| **Outline** | Source-available (BSL 1.1), self-host free community edition + cloud | Cloud: $10/mo (1–10 members), $79/mo (11–100), $249/mo (101–200), custom above; 30-day trial; 30% nonprofit/edu | No public revenue | [getoutline.com/pricing](https://www.getoutline.com/pricing) | **VERIFIED** (pricing); revenue unknown |
| **Nextcloud** | Open source + enterprise subscription/support | Not published on a simple public page | No reliable public revenue. Own blog (2022-08-04) claims **+75% revenue and +133% net income 2020→2021, 10× userbase**, but publishes **no absolute figures**. Third-party "revenue" numbers (Zippia $7.1M, Growjo) are scraped guesses and mutually inconsistent | [nextcloud.com blog 2022-08-04](https://nextcloud.com/blog/nextcloud-keeps-growth-up-with-75-more-revenue-and-10x-userbase/) | Growth % **VERIFIED**; absolute revenue **UNKNOWN** |
| **CryptPad** (XWiki SAS) | Grant-funded + cryptpad.fr subscriptions + donations | Subscriptions on cryptpad.fr | **2025 actuals: subscriptions €121k, donations €29k, client roadmap €14.3k, other client €27.2k, research projects €388k, CIR tax credit €28.5k → total €608k. Costs €619.5k. 8 FTE.** 2026 expected €730k on 9 FTE. States it needs **€400k of subs+donations by 2027** to balance spending — i.e. must roughly **quadruple** self-generated revenue | [blog.cryptpad.org 2026-02-18](https://blog.cryptpad.org/2026/02/18/CryptPad-Funding-Status-2026/) | **VERIFIED** |
| **Standard Notes** | E2EE notes, open source, paid tiers | **Productivity $90/yr; Professional $120/yr**; free tier unlimited device sync | >300,000 active users at acquisition. **Acquired by Proton 2024-04-10**; terms undisclosed; prices honoured, stays open source | [standardnotes.com/plans](https://standardnotes.com/plans); [proton.me/blog](https://proton.me/blog/proton-standard-notes-join-forces); [TechCrunch 2024-04-10](https://techcrunch.com/2024/04/10/proton-standard-notes/) | **VERIFIED** |
| **Anytype** | Local-first, p2p, open source; paid network/storage tiers | Free 100MB remote storage; paid tiers **$4/mo** (1GB), **Pro $8/mo** (10GB), **Ultra $16/mo** (100GB); −20% yearly; 50% edu discount; separate "Anytype for Business" with SSO/self-host | **$13.4M Series A (Aug 2023, Balderton)**; ~$14.1M total raised. No public revenue | [anytype.io/pricing](https://anytype.io/pricing) (curl); [Balderton](https://www.balderton.com/news/anytype-announces-13-4-million-round-following-launch-of-open-beta/); [Tech.eu 2023-08-23](https://tech.eu/2023/08/23/anytype-raises-13-4m-decentralised-web/) | Pricing/funding **VERIFIED**; revenue unknown |
| **Logseq** | Open source, Open Collective + sync for backers | Sync/RTC gated to sponsors/backers | **Total raised on Open Collective $737,336.80; disbursed $688,287.93; balance $49,048.87; estimated annual budget $251,578.74.** Separately ~$4.1M VC seed (2022) | [opencollective.com/logseq](https://opencollective.com/logseq) | **VERIFIED** (Open Collective ledger); VC figure **REPORTED** |
| **Joplin** | Open source markdown notes + Joplin Cloud | Basic €2.99/mo (€28.69/yr, 2GB); Pro €5.99/mo (€57.48/yr, 30GB); Pro 100GB €9.99/mo; Teams €7.99/user/mo (€80.28/yr, min 2) | Solo founder (Laurent Cozic); no investors; funded by Cloud subs + donations/Patreon. No public revenue | [joplinapp.org/plans](https://joplinapp.org/plans/) | Pricing **VERIFIED**; revenue unknown |
| **Skiff** | VC-backed E2EE mail/docs/drive | — | ~$14M raised; **>2M users (Nov 2023)**. Acqui-hired by **Notion 2024-02-09**; all services sunset **2024-08-09**; no account migration, users had to export manually | [TechCrunch 2024-02-09](https://techcrunch.com/2024/02/09/notion-acquires-privacy-focused-productivity-platform-skiff/amp/); [Wikipedia](https://en.wikipedia.org/wiki/Skiff_(email_service)) | Event **VERIFIED**; funding/users **REPORTED** |
| **LibreOffice / TDF** | Nonprofit foundation, donations + app-store sales | Free | **2025 income €2,175,997** — donations €1,976,825, app stores €168,975 (Apple €118,942, Microsoft €35,393), securities €30,197. **2024 income €1,387,589.** 2025 spend €1,457,343. **18 employees, 11 on development.** >90% of donations from private individuals, <10% from public bodies and companies. **>100M estimated users**, ~1M downloads/month | [TDF Annual Report 2025 financials, 2026-07-13](https://blog.documentfoundation.org/blog/2026/07/13/financials-and-budget-tdf-annual-report-2025/); [How LibreOffice is funded, 2026-08-28](https://blog.documentfoundation.org/blog/2026/08/28/how-libreoffice-is-funded/) | **VERIFIED** |
| Thunderbird (comparison point cited by TDF) | Donations | Free | **$10.3M in 2024 from >335,000 donors** | [TDF, 2026-08-28](https://blog.documentfoundation.org/blog/2026/08/28/how-libreoffice-is-funded/) | **VERIFIED** (as quoted by TDF) |
| **ONLYOFFICE** (Ascensio System SIA, Riga) | AGPL-3.0 core + commercial enterprise/developer editions | Enterprise plans quoted ~$75–$5,000 | ~$5.2M annual revenue; 82–122 employees (sources disagree) | Datanyze / ZoomInfo scrapes | **REPORTED** (low confidence) |
| **Collabora Productivity Ltd** | Open source LibreOffice-based; sells Collabora Online/Office support | — | UK company 08644931, incorporated 2013-08-09, active, last accounts to 2024-12-31. **Turnover not publicly disclosed** in filings surfaced. Parent Collabora Ltd ~150 employees | [Companies House 08644931](https://find-and-update.company-information.service.gov.uk/company/08644931) | Existence/filing **VERIFIED**; revenue **NOT PUBLIC** |
| **openDesk** (ZenDiS GmbH) | German federal sovereign office suite, publicly funded | Not published on the public site | Operated since Jan 2024 by **ZenDiS GmbH, a publicly-funded federal entity**, commissioned by the German Federal Ministry of the Interior. Bundles OSS components (Nextcloud, Collabora, OpenProject et al.). No adoption or pricing figures published | [opendesk.eu](https://opendesk.eu/en/) | Existence/ownership **VERIFIED**; numbers not published |
| **Mintlify** | Docs-as-code SaaS (markdown + git), hosted docs | — | **$45M Series B at $500M valuation, announced 2026-04-14/17**, a16z + Salesforce Ventures; **$67M total raised**. **20,000+ companies**; content reaches 100M+ people/yr. Series A $18M (2024-09-03, a16z). ARR **$10M end-2025, up 10× from $1M end-2024**; 150% NRR | [mintlify.com/blog/series-b](https://www.mintlify.com/blog/series-b); [mintlify.com/blog/series-a](https://www.mintlify.com/blog/series-a); ARR from [Sacra](https://sacra.com/c/mintlify/) | Funding/customers **VERIFIED**; ARR/NRR **REPORTED** |
| Mintlify — AI thesis | — | — | **"nearly 50% of traffic to documentation comes from AI agents"** and growing; docs framed as "infrastructure" for AI; shipping MCP support for external agents | [mintlify.com/blog/series-b](https://www.mintlify.com/blog/series-b) | **VERIFIED** (company claim) |
| **GitBook** | Docs SaaS, git sync | Free $0/site (1 user); **Premium $65/site/mo annual**; **Ultimate $249/site/mo annual**; **+$12/user/mo** on paid; Enterprise custom; 2 months free annual | ~$3.9M ARR, 35 employees, founded 2014 | [gitbook.com/pricing](https://www.gitbook.com/pricing); ARR from [Getlatka](https://getlatka.com/companies/gitbook.com) | Pricing **VERIFIED**; ARR/headcount **REPORTED** |
| **ReadMe** | API docs SaaS | Tiered subscription | ~$10.7M ARR (2024); ~71 employees; **$9M Series A (Accel, YC), no round announced since 2019** | [Getlatka](https://getlatka.com/companies/readme.com); [Tracxn](https://tracxn.com/d/companies/readme/__82GSpsc8bUCwffMFY8qofmAuacf30CexllehGP79Hf0) | **REPORTED** |
| **Docusaurus** | Meta OSS, unmonetized | Free | No revenue model; monetization happens in the hosting layer above it (Netlify/Vercel/Mintlify) | — | **VERIFIED** (no product to buy) |

---

### 2. What actually monetizes

**Nobody monetizes the file format. Everybody monetizes the thing the files can't do
by themselves.** Across every comparable, the paid SKU is one of five things:

1. **Sync / hosting** — Obsidian Sync, Joplin Cloud, Anytype storage tiers, Standard Notes, cryptpad.fr.
2. **Publishing** — Obsidian Publish, GitBook (per *site*, not per user), Mintlify, ReadMe.
3. **Multiplayer + admin** — SSO, groups, audit logs, provisioning: Outline, Grist Business, Notion, Airtable.
4. **Support + indemnity + sovereignty** — Nextcloud, Collabora, ONLYOFFICE enterprise, Grist self-hosted/Enterprise, openDesk.
5. **Seats in a workflow the team already lives in** — Notion, Airtable, Coda.

The editor itself is free in every single local-first case. That is not a coincidence;
it is the price the category pays for the "your files are yours" promise.

### 3. What does *not* monetize

- **Donations at consumer scale.** LibreOffice earns **€2.18M/yr from 100M+ users** —
  about **€0.02 per user per year**. Mintlify's 20,000 *companies* generate ~5× the
  revenue of LibreOffice's 100 million *people*. User count is nearly uncorrelated with
  revenue in this category; **buyer type is everything**.
- **Open Collective / community funding as a business.** Logseq's ledger is a hard
  ceiling: **$251,578 estimated annual budget, $737k raised across its entire life.**
  That funds ~1.5 engineers. Logseq also took ~$4.1M VC on top, and still stalled.
- **Grant-funded local-first.** CryptPad is **64% research-grant funded** (€388k of €608k
  in 2025) and says outright it must quadruple subscriptions+donations to €400k by 2027
  to break even. Eight FTE, running a €11k deficit. That is a research programme wearing
  a product's clothes.
- **VC-scale privacy/local-first consumer.** Skiff: $14M raised, 2M users, dead in
  30 months and sold for parts. Standard Notes: 300k active users, sold to Proton.
  Anytype: $14.1M raised in 2023, no disclosed revenue three years later.
- **VC-scale "docs + spreadsheets, but better."** Coda raised $240M at $1.4B and exited
  at undisclosed (read: disappointing) terms into Grammarly. Airtable raised $1.4B at
  $11.7B and exited at **2.7× ARR / $1.285B EV** — a ~89% haircut, with $965M of the
  $2.25B equity value being *Airtable's own unspent cash*. Both had genuinely large
  revenue. Both still failed to justify the round. **Category-adjacency to Google Docs
  does not clear a venture bar.**

### 4. Willingness to pay for "local plaintext files + sync" — the actual number

Obsidian is the definitive datapoint, and it needs arithmetic because the ARR is not
disclosed. **VERIFIED inputs:** 3–4M users; 7 people; no investors; Sync $48/user/yr;
Publish $96/site/yr; Catalyst $25 once; Commercial $50/user/yr and **optional since
Feb 2025**.

**ANALYSIS (my arithmetic, not sourced):** at 3.5M users, a 3% Sync conversion is
105,000 subs ≈ **$5.0M**; 5% is **$8.4M**; the widely-repeated $25M figure would require
~520,000 Sync subscribers ≈ **15% conversion on a free app**, which is far outside normal
freemium behaviour. Publish and Catalyst add a tail, not a multiple. **A defensible
estimate is $5–12M ARR**, and the $2M low-end estimates look too low for a 7-person team
with that user base. Either way the conclusion is the same:

> **The best-executed product in this category, with a near-monopoly on the plaintext
> markdown audience and zero dilution, is a ~$5–12M/yr, 7-person business.** That is an
> outstanding outcome for founders. It is not a venture outcome, and it took ~6 years.

Prosumer price anchors are also low and remarkably tight: Obsidian $48/yr, Joplin
€28.69/yr, Anytype $48/yr, Standard Notes $90/yr. **The prosumer plaintext buyer pays
$30–$90/year and no more.** Team/dev buyers pay 3–10× that per seat (Grist $96–$288/yr,
GitBook $144/user/yr *plus* $780–$2,988/site/yr, Notion $120–$240/yr).

### 5. The realistic wedge

Ranked by *demonstrated willingness to pay*, not by enthusiasm:

**1. Dev/docs teams (docs-as-code + AI agents) — strongest.** This is the only segment in
the dataset that is *growing fast and repricing upward*. Mintlify went **$1M → $10M ARR in
one year** and got a **$500M valuation in April 2026** on an explicitly agent-shaped thesis:
*"nearly 50% of traffic to documentation comes from AI agents"* (VERIFIED, company claim).
GitBook and ReadMe sit at ~$4–11M with per-site pricing that shows this buyer tolerates
four-figure annual line items. Crucially, this buyer **already accepts markdown-in-git as
the source of truth** — no education needed — and pays for the layer above it.

**2. Regulated / sovereignty self-host — real, slow, and underrated.** Grist went from
**2,000 → 20,000 MAU inside the French state in twelve months** (VERIFIED, EC/OSOR),
15 ministries, all 100 prefectures; France is now the largest upstream contributor.
Germany funds ZenDiS/openDesk directly. Grist Labs responded by hiring a CRO and closing
a seed in 2026 specifically for "the era of sovereignty." This buyer pays for support,
indemnity, SSO, audit logs and data residency — never for the editor. The catch: long
sales cycles, and Grist Labs is still small enough that it took angel money in 2026.

**3. Agencies / small teams — plausible, unproven, no clean comparable.** Outline's
$79–$249/mo team tiers are the closest shape. No public revenue anywhere to size it.

**4. Individuals / prosumer — proven but capped.** Obsidian owns it, at $5–12M and
$30–$90/yr per head. Viable as a *funnel*, fatal as a *plan*.

**5. Consumer privacy/local-first — avoid.** Skiff, Standard Notes, Logseq, CryptPad,
Anytype. Every single one either died, sold, stalled, or lives on grants.

#### The specific risk for a *git-backed* suite

This is the sharpest finding in the whole area and it deserves to be stated plainly:

> **Obsidian's largest revenue line is Sync. A git-backed product gives that away for
> free, on day one, using infrastructure the customer already pays GitHub for.**

The proposed differentiator deletes the proven monetization of the closest analog. That
does not kill the idea, but it forces the paid SKU to be something else — publishing,
review/approval workflows, spreadsheet compute at scale, non-technical-user onboarding
onto git, SSO/audit, or agent orchestration — and each of those is a *different* product
with *different* competitors (Mintlify, Grist, Outline) rather than Obsidian.

#### Revenue-plausibility sanity check (ANALYSIS)

- **Prosumer path:** $48–$90/yr. To reach $5M ARR you need **~70,000–100,000 paying
  individuals**, which at a 3–5% freemium rate implies **1.5M–3M free users** — i.e. you
  must replicate essentially all of Obsidian's six-year audience to match its revenue.
  Realistic ceiling **$5–12M ARR**, supporting **5–10 people**.
- **Dev-team path:** at $20–$30/user/mo, $10M ARR needs **28,000–42,000 paid seats**, or
  roughly **2,000–4,000 paying teams at 10–20 seats**. GitBook and ReadMe are at that
  scale after ~10 years; Mintlify hit $10M in ~3. Plausible, and the only path in this
  dataset with a demonstrated 10×-in-a-year precedent.
- **Sovereignty path:** contracts, not seats. Grist's French deployment is 20,000 MAU;
  even at €50/user/yr of paid support that is €1M — real money, one logo, and it took
  three years of upstream contribution to earn. A $10M ARR sovereignty business needs
  **5–10 national-scale customers**, which is a 5+ year enterprise motion, not a launch.
- **Blended realistic target:** **$3–8M ARR by year 3** on a dev-team-led wedge with a
  free prosumer funnel, if execution is very good. Anything modelling $50M+ requires
  believing this is Notion, and Notion's own comparables (Coda, Airtable) just sold at
  2.7× ARR and undisclosed terms respectively.

### 6. Verification gaps (stated, not papered over)

- **Obsidian ARR** — no primary source exists. Every figure in circulation, including
  the $25M one, traces to unsourced third-party estimates. The $5–12M range in §4 is my
  own arithmetic from VERIFIED user count and VERIFIED pricing, and should be treated
  as an estimate.
- **Nextcloud, Collabora, ONLYOFFICE, Outline, Joplin, Anytype revenue** — private, not
  disclosed, and the scraped third-party numbers for these are mutually inconsistent
  enough that I decline to quote them as fact.
- **Coda's exit terms and Skiff's, Standard Notes' acquisition prices** — all undisclosed.
- **Grist Labs seed amount (2026)** — closed but not disclosed.
- **WebSearch quota** was exhausted mid-research; Notion's user count (the widely-cited
  "100M users") is REPORTED only and I could not reach a Notion primary source for it.

---


## E. Does plaintext actually win in serious domains? (honest read)

**Yes — in exactly four conditions, none of which fully hold for a general office suite.**

### E.1 Where plaintext demonstrably won

| Domain | Evidence | Verified |
|---|---|---|
| **Scientific writing (LaTeX)** | Overleaf: **"20+ million Overleaf users"** as of 2025-06; had 100k registered users when Digital Science first invested in 2014. Acquired/absorbed into Digital Science. Overleaf's own OSS repo exists (HN [40832930](https://news.ycombinator.com/item?id=40832930), 246p/127c). | REPORTED (Digital Science press, via search); the HN items VERIFIED |
| **Infrastructure-as-code** | Terraform/HCL, Kubernetes YAML, Ansible. The entire operational substrate of modern computing is plaintext in git. Not contested. | Common knowledge |
| **Docs-as-code** | `facebook/docusaurus` **66,114★**; `squidfunk/mkdocs-material` **27,342★**. VERIFIED via GitHub API 2026-08-28. | VERIFIED |
| **Reproducible science / publishing** | `quarto-dev/quarto-cli` **5,965★**, created 2020, pushed 2026-08-28. HN [30042831](https://news.ycombinator.com/item?id=30042831) 234p, [39367103](https://news.ycombinator.com/item?id=39367103) 205p/61c. | VERIFIED |
| **Personal task management** | Taskwarrior: HN [17029560](https://news.ycombinator.com/item?id=17029560) **424p/228c**, [31390728](https://news.ycombinator.com/item?id=31390728) 248p, [41372482](https://news.ycombinator.com/item?id=41372482) 173p/70c. todo.txt: [4957983](https://news.ycombinator.com/item?id=4957983) 88p/80c, [20745654](https://news.ycombinator.com/item?id=20745654) 83p/49c. | VERIFIED |
| **org-mode** | 683 HN stories; the canonical Karl Voit post hit **556p/241c (2017)**, **518p/245c (2019)** and *again* **287p/218c (2026-01-10)** — nine years of durable interest. | VERIFIED |
| **Version-controlled tabular data** | `dolthub/dolt` ("Git for Data") **24,286★**; `gristlabs/grist-core` **11,630★**. Both alive and actively pushed 2026-08-28. Real pull for "version control on data" — **but note both solved it with a database, not with plaintext files.** | VERIFIED |

### E.2 Where plaintext won a *category* but not a *market* — the accounting cautionary tale

Plain-text accounting is the single best analogue for "plaintext spreadsheets", and it is the one
you should study hardest, because **it is simultaneously the strongest proof of the thesis and the
clearest ceiling on it.**

VERIFIED (GitHub API, 2026-08-28):

- `ledger/ledger` — **6,019★** (created 2008)
- `beancount/beancount` — **5,948★**
- `plaintextaccounting/hledger` — **4,674★** (created 2013)

VERIFIED (HN Algolia): plaintextaccounting.org has been submitted and hit the front page
repeatedly across a decade — 328p/237c (2016), 473p/200c (2021), 290p/122c (2021), 334p/120c
(2024), and still 142p/91c on 2026-01-02.

**But:** eighteen years, three flagship projects, ~16,600 combined stars, and **no company.** There
is no plain-text-accounting business of consequence. The users are exactly the users who will
never pay: technical, opinionated, self-hosting, DIY. The category is a permanent, beloved,
un-monetised niche. This is the risk case for a plaintext office suite in miniature.

### E.3 The verdict from section E

Plaintext + git wins when **all four** of these hold:

1. The artefact is genuinely linear text or genuinely declarative data (LaTeX source, HCL, docs).
2. The users are already developers, or are willing to become semi-developers for a large payoff
   (reproducible research, publishing pipelines).
3. **The rendered output is decoupled from the source** — nobody edits the PDF; the PDF is built.
4. Correctness/diffability matters more than WYSIWYG immediacy.

For **Docs**, 1/3/4 hold and 2 is the constraint. For **Slides**, 1/3 hold, and the layer is
already thoroughly won: **`slidevjs/slidev` 48,317★**, `hakimel/reveal.js` 72,225★,
`marp-team/marp` 12,420★ (all VERIFIED, GitHub API 2026-08-28), plus Marp is what Karpathy names
in the LLM-wiki gist. Markdown slides is a solved, commoditised, un-monetised layer — wrap it,
never rebuild it, and do not expect it to be a differentiator. For **Sheets**, condition 1 **fails**: a spreadsheet is not linear text, CSV
cannot express formulas, and every attempt to bolt a formula DSL onto markdown (Sheet Markup /
EqualTo) has died. The obvious mitigation — values in `.csv` plus a formula/format sidecar, with
HyperFormula (`handsontable/hyperformula`, **2,772★**, VERIFIED, 400+ formulas) as the engine — is
sound engineering but has **zero market validation**: nobody has shipped it and found users.

---
---

## F. Closing assessment — real opportunity, or trap?

### F.1 The one-paragraph answer

**As pitched — "Google Workspace, but plaintext and git-backed" — this is a trap.** It is a
thirteen-year-old idea with a well-documented graveyard (Editorially, Penflip, Draft, Poetica,
Fargo, EqualTo, Stashpad), *declining* HN enthusiasm, at least five zero-star 2026
implementations, two stalled direct competitors (Pithy, Perchpad), and a market that in 2026
answered the same user problem in the opposite direction: **OfficeCLI took 29,443 GitHub stars in
five months by keeping `.docx`/`.xlsx`/`.pptx` and giving agents a CLI with a render loop, and
GenOffice took 3,860 stars in four weeks doing byte-preserving `.docx` editing.** Meanwhile the
incumbents closed the headline gap — Microsoft Copilot agent mode GA in Word/Excel/PowerPoint on
**2026-04-22** ("make changes directly in your workbook"), Claude for Microsoft 365 GA
**2026-05-07**. **There is a real opportunity inside this, but it is smaller, sharper, and
differently named.**

### F.2 What is genuinely true and defensible

1. **Files-on-disk + git is the officially blessed agent substrate.** The MCP steering group
   maintains exactly two document-substrate reference servers — **Filesystem and Git** — and
   *archived* Google Drive. That is the strongest single fact in this report.
2. **The API tax is real and quantified:** ~21,411 tokens of Notion tool schemas before reading a
   word of content; 410,053 tokens for a 500×20 Excel read as JSON; a merged PR whose own task note
   reads *"Excel MCP tool returns excessive metadata making it unusable for AI agents"*; and silent
   data loss in Notion's own markdown table converter.
3. **The pattern has a champion and breakout traction — under a different name.** Karpathy's LLM
   Wiki gist (296 HN points, 2026-04-04) prescribes markdown + git + agent + Marp-for-slides:
   *"The wiki is just a git repo of markdown files. You get version history, branching, and
   collaboration for free."* It spawned OpenKnowledge (381 points, 3,675★) and wuphf (260 points,
   1,248★) within ten weeks.
4. **Nobody has shipped docs + sheets + slides as plaintext with git as the drive.** Everyone stops
   at docs. That gap is real.
5. **Diff, branch, review and audit on a document** is something no incumbent offers and none is
   building. Copilot edits your deck; it does not give you a pull request on it.
6. **The dev/docs-team buyer is repricing upward right now.** Mintlify went **$1M → $10M ARR in a
   year** and raised at a **$500M valuation in April 2026** on an explicitly agent-shaped thesis:
   *"nearly 50% of traffic to documentation comes from AI agents."* That buyer already accepts
   markdown-in-git as the source of truth.

### F.3 Where the trap actually is

| Trap | Evidence |
|---|---|
| **Git is the headline and the repellent.** | Poetica's own shutdown post said their value was enabling collaboration *without* "arcane tools like git". The docs-as-code practitioner post lists "Git is confusing" as pitfall #1 — for *technical writers*. Non-programmers version files by appending dates. The author of a 471-point "build your own PKM" post explicitly declined git: *"I wasn't comfortable with that however."* |
| **The category has a hard revenue ceiling.** | Editorially, verbatim: *"Even if all of our users paid up, it wouldn't be enough."* LibreOffice earns **€2.18M/yr from 100M+ users ≈ €0.02 per user per year**. Logseq's entire lifetime Open Collective take is **$737k**. CryptPad is **64% grant-funded** and must quadruple self-generated revenue by 2027 to break even. |
| **★ The differentiator deletes the proven revenue line.** | **Obsidian's largest paid SKU is Sync ($48/user/yr). A git-backed product gives sync away for free, on infrastructure the customer already pays GitHub for.** The closest successful analog monetises precisely the thing this design makes free. |
| **Even the best case is small.** | Obsidian: 3–4M users, **7 people**, no investors, ~6 years — and an estimated **$5–12M ARR**. That is an excellent founder outcome and not a venture one. |
| **Venture-scale adjacency has just been repriced downward.** | Airtable raised $1.4B at an $11.7B peak and sold on **2026-08-04 for $1.285B EV ≈ 2.7× ARR** (~89% below peak). Coda raised $240M at $1.4B and exited to Grammarly on undisclosed terms. Skiff: $14M and 2M users, dead in 30 months. |
| **Sheets is the differentiator and it is genuinely unsolved.** | CSV cannot hold formulas. The one serious plaintext-formula attempt (EqualTo Sheet Markup, 120 HN points, 2023) is now an **NXDOMAIN**. A competing builder, verbatim: *"structure is incredibly variable and the data just compresses rather poorly (values, formulas, formatting, charts, pivots)."* |
| **Slides is not a differentiator at all.** | Slidev 48,317★, reveal.js 72,225★, Marp 12,420★. Solved, commoditised, un-monetised. Wrap it; never build it. |
| **Framing is worth more than the product.** | "Karpathy-style LLM wiki your agents maintain" = **260 points**. "Collaborative real-time Markdown editor backed by Git" = **2 points**. Same substrate, 130× difference. |
| **Plaintext ≠ token savings.** | easy-notion-mcp's own benchmark: *"At equal information the two formats cost about the same… the win is metadata omission, not encoding efficiency."* |
| **Agents need to *see* documents, not just parse them.** | OfficeCLI's headline claim is its render engine — *"that's what gives AI eyes."* Multiple verified HN accounts describe Claude rendering slides to PNG in a feedback loop. Plaintext alone does not provide this, and it matters most for the slides layer. |
| **The category's biggest cheer went elsewhere.** | La Suite Docs: **1,952 HN points, 16,754★** — and it is Django + Yjs, not files on disk. What it captured was demand for *sovereignty*, not for plaintext. |

### F.4 The most defensible wedge

Ranked by demonstrated willingness to pay, not by enthusiasm:

**1. The agent-maintained, git-versioned *working record* for technical teams — sold on review,
diff and audit, not on "plaintext."** This is the only positioning with both 2026 attention
(Karpathy → OpenKnowledge → wuphf) *and* a paying-buyer precedent that is repricing upward
(Mintlify $1M→$10M ARR in a year at a $500M valuation, GitBook at $144/user/yr **plus**
$780–$2,988/site/yr, ReadMe ~$10.7M ARR). It is the only segment where git is a benefit rather than
a tax — the buyer already uses it daily — and the only one the incumbents structurally cannot
follow: **Copilot will never give you a pull request on a memo.** Sell "PRs for documents", not
"markdown office suite". Sanity check: $10M ARR ≈ 28,000–42,000 seats ≈ 2,000–4,000 paying teams —
GitBook and ReadMe took ~10 years to get there, Mintlify took ~3.

**2. Sheets specifically — a git-diffable spreadsheet with real formulas an agent can edit
deterministically.** The single unclaimed hard problem in the space, with a verified live pain
quote: *"it didn't have a good way to port formulas over into specific cells, so I basically had a
CSV and a bullet list of formulas to put in by hand."* The engineering path exists (values in
`.csv` + a formula/format sidecar, HyperFormula as the engine — 2,772★, 400+ formulas). **But it
has zero market validation, and the one company that shipped a plaintext formula DSL is a dead
domain.** Highest differentiation, highest risk.

**3. Sovereignty / regulated self-host — real, slow, underrated.** Grist went from **2,000 → 20,000
MAU inside the French state in twelve months**; France is now the largest upstream contributor;
Germany funds ZenDiS/openDesk directly. This buyer pays for support, indemnity, SSO, audit logs and
residency — **never for the editor, and never for the file format.** A $10M sovereignty business
needs 5–10 national-scale logos and a 5+ year enterprise motion. Also note: I found **no HN
evidence at all** of regulated-industry demand for document version control; searches for
compliance / audit-trail / controlled-documents returned essentially nothing.

**4. Prosumer individuals.** Obsidian owns it, at **$30–$90/yr per head**, and the observed
behaviour in the 471-point "Ditching Obsidian and building my own" thread is that these users
*build their own rather than buy*. Viable as a funnel, fatal as a plan: $5M ARR needs ~70k–100k
payers ≈ 1.5–3M free users ≈ replicating Obsidian's entire six-year audience.

**5. Consumer privacy/local-first — avoid.** Skiff (dead), Standard Notes (sold), Logseq (stalled),
CryptPad (grants), Anytype (no disclosed revenue three years after a $13.4M Series A).

### F.5 What I would tell the founder

- **Do not build a suite.** Build the one piece nobody has (a spreadsheet that genuinely diffs and
  that an agent can edit deterministically) and wrap the pieces that are solved (Marp/Slidev for
  slides, an existing markdown WYSIWYG for docs).
- **Do not lead with "git" or "plaintext".** Both are proven repellents outside the developer
  segment, and inside it they invite the killer question already asked verbatim of moment.dev:
  *"If I'm writing markdown and avoiding notion, what does this provide my team that git does not?"*
  You need an answer that is not the file format.
- **Know that the honest answer, per moment.dev's own founders, is multiplayer** — *"Claude Code is
  great for single-player, but it breaks down when you want to share with your team"* — which means
  the hard engineering is CRDT-over-files collaboration, not format design. That is where the moat
  is, and it is expensive.
- **Have a paid SKU that is not sync.** Git makes sync free, which deletes Obsidian's main revenue
  line. Candidates: publishing, review/approval workflows, SSO + audit, spreadsheet compute, agent
  orchestration. Each puts you against a *different* incumbent (Mintlify, Outline, Grist) than you
  expected.
- **Watch OfficeCLI and GenOffice as thesis-killers.** If agents get good enough at OOXML with a
  render loop, "agents need plaintext" evaporates. That risk is already 29,443 stars along.
- **Validate before building.** Publish the sheets format proposal alone as a Show HN. If a
  diffable spreadsheet format with formulas cannot beat 120 points (EqualTo's 2023 number), the
  suite around it will not either.

### F.6 Verdict

**Real opportunity: yes — but not the one in the brief.** The plaintext office *suite* is a trap
with a thirteen-year graveyard, a repellent headline feature, a business model that gives away its
closest analog's main revenue line, and a 2026 market that just voted 29,443-to-2 for the opposite
approach. The git-versioned, agent-maintained *working record* for developer teams — with a
genuinely diffable spreadsheet as the one hard, unclaimed piece — is a real and narrow opportunity
in the **$3–8M ARR by year 3** range if execution is very good. It is a collaboration-and-workflow
business that happens to use plaintext, not a plaintext business.

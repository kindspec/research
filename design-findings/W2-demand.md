# W2 — Does anyone want this? Demand evidence for git-versioned tabular data

Evidence-gathering pass, 2026-08-28. Assignment: test DESIGN.md §1's commercial
thesis — that the value is *storage-and-review* of tabular data under git, on the
grounds that code inspection is the only spreadsheet-error intervention with real
evidence behind it.

All figures observed **2026-08-28** unless stated. Sources are APIs where possible
(GitHub REST/search authenticated, Stack Exchange API, HN Algolia, pypistats,
npm registry, deps.dev) rather than prose pages. Session WebSearch budget was
exhausted early, so a small number of items below are marked *unverified*.

---

## 0. Verdict

**No population has demonstrated the pain this design targets. One population has
demonstrated an *adjacent* pain — shared-file contention on a hand-edited table —
and solved it by routing humans away from the file, not by improving the diff or
the merge.**

Four findings drive the verdict, all negative in the same direction.

1. **The complaint is thin in the public record.** On Hacker News (Algolia API),
   `csv merge conflict` returns **0 stories / 9 comments**; the looser
   `merge conflict csv` returns **9 stories / 127 comments**;
   `spreadsheet merge conflict` returns **1 story / 11 comments**; and
   `diff spreadsheet` returns **7 stories**. Stack Overflow has **9** questions
   matching `[git] csv merge conflict` and **2** tagged `version-control`+`csv`
   (against 189 for `git`+`json`). The volume that *does* exist is a different
   question — "how do I version-control a *binary* Excel file" — is 13–18 years
   old and **declining** (SO `git`+`excel`: 2018:7 → 2021:2 → 2024:1).
   **Not one instance was found, anywhere, of someone reporting a silently wrong
   number produced by a merged CSV** — the failure DESIGN.md exists to remove.

2. **The hack ecosystem is ~23× smaller than the Jupyter control group, and it
   never converged on a winner.** `merge=csv` appears in **6 `.gitattributes`
   files on all of GitHub**; `diff=daff`/`merge=daff` in **121/118**;
   `diff=xlsx` in **28**; `xlsx2csv` in `.pre-commit-config.yaml` in **0**.
   Against `nbstripout` at **4,952 pre-commit configs** and 2.59M PyPI
   installs/month. **The dominant coping strategy is not a hack at all: 3,672
   repos declare `*.xlsx binary` and 2,776 push it into LFS — a give-up-to-hack
   ratio of ~230:1.** GitHub built the productized version of this idea —
   **Flat Data — and archived it.**

3. **The product has been built repeatedly, with capital, and none survived
   standalone.** Datafold's `data-diff` — literally "review the data diff in your
   PR" — is **archived 2024-05-17** at 2,991 stars. Tobiko Data raised **$21.8M**
   and was **acquired by Fivetran 2025-09-03**. Iterative.ai raised **~$24.5M**,
   never raised a B, and **sold DVC to lakeFS (2025-11-18)**; `iterative/dvc` now
   redirects to `treeverse/dvc` and the org logs 17 commits in 90 days. dbt Labs
   merged into Fivetran (closed 2026-06-01). DoltHub — ~$21.0M, the healthiest
   thing here — got healthy by **abandoning data collaboration for an OLTP
   database**.

4. **The regulatory wedge does not exist where the pitch assumes it.** A
   full-text grep of **PCAOB AS 2201** finds **zero occurrences** of
   "spreadsheet", "end-user computing", or "version control". **SR 11-7** names
   spreadsheets but is *guidance* and says "change control", never version
   control. **BCBS 239** contains "lineage", "version" and "audit trail"
   **nowhere**. The **EU AI Act** excludes spreadsheets by recital. **The single
   binding instrument that demands what git provides is 21 CFR Part 11
   §11.10(e) and (k)(2) — and it points at GxP/pharma, not FP&A** (§2.5).

### Ranked candidate audiences

| # | Audience | Demonstrated pain? | Size estimate | Can pay? |
|---|---|---|---|---|
| **1** | **Public reference-data registries** (a table *is* the product) | **Yes — behavioural.** Bots, CI shape-gates, bolded column-count warnings, rows pasted into PR comments | **3,566–4,577** actively-pushed `topic:dataset`/`topic:open-data` repos; **289** repos name a `.csv` in CODEOWNERS | **No.** Volunteer OSS and civic data offices |
| **2** | **GxP / 21 CFR Part 11 regulated records** | **Untested.** The only binding audit-trail law found. No evidence gathered that these teams want git | Unbounded here — not measured | **Yes**, in principle |
| **3** | **Finance / FP&A** | **No.** 41 HN stories all time; dedicated products score 1 point; SO's top questions are from 2008 and 2013 with no winning answer | Large, but 100:1 of the money went to *replacing* spreadsheets ($10.4B Anaplan) not auditing them | Yes — but not for this |
| **4** | **dbt / analytics engineering** | **No — refuted.** 937 seed issues, **zero** about reviewing seed diffs; all seed pain is *ingestion*. dbt docs tell users seeds must be small and static | 80–100k data teams; 28,736 repos with `dbt_project.yml` | Consolidated into Fivetran |
| **5** | **Agent-edited structured data** | **No.** Capability adopted (excel-mcp-server 4,144★), review behaviour **not observed anywhere**. Biggest project by 7× is OfficeCLI, which *keeps* `.xlsx` | — | Unknown |
| **6** | **Research reproducibility** | **No.** `git2rdata` — the purpose-built tool — does **325 CRAN downloads/month**. HN `research data versioning`: **7 story hits total**. Journals mandate *immutable deposit*, which is anti-diff | Negligible | No |

### The one asymmetry that keeps this from being a flat "no"

The tabular hack ecosystem may be small **because the hacks structurally cannot
work**, which is a point DESIGN.md §3(b) already proves: `.gitattributes` travels
and `.git/config` does not, and a bare repo consults neither. Every CSV hack
requires the *reader* to install something; every successful Jupyter hack
requires nothing of anyone downstream. So the absence of adoption is not clean
evidence of absence of need — it is consistent with a need that no available
remedy could serve. **That is the strongest honest case for building this, and it
is an argument from mechanism, not from demand.** §6 is the counterweight: the
one severe cost people actually paid is not fixed by the design either.

---

## 1. Who version-controls tabular data today, and what does it cost them?

### 1.1 The prevalence question — smaller than assumed

Searching the classic "community-curated CSV dataset" candidates, **most turn out
to be pipelines with 1–8 authors, not many humans editing one file**:

| Repo | Stars | File | Commits / distinct authors | Range |
|---|---|---|---|---|
| `iptv-org/database` | 1,629 (parent `iptv-org/iptv`: 136,914) | `data/channels.csv`, 40,834 rows, 3.99 MB | **6,519 / 86** | 2022-02 → 2026-08, active |
| `iptv-org/database` | — | `data/feeds.csv`, 2.7 MB | 609 / 28 | 2025-03 → 2026-08 |
| `datasets/country-codes` | 980 | `data/country-codes.csv`, 134 KB | 57 / 9 | 2013-12 → 2026-05 |
| `datasets/airport-codes` | 378 | `data/airport-codes.csv`, 8.8 MB | 357 / 10 | 2015-02 → 2026-08 |
| `owid/covid-19-data` | 5,659, **archived** | `owid-covid-data.csv` | 7,844 / **8** | 2020-04 → 2024-08 |
| `nytimes/covid-19-data` | 6,964 | `us-states.csv`, 2.2 MB | 1,701 / **2** | 2020-03 → 2023-03 |
| `jpatokal/openflights` | 1,660 | `data/airports.dat`, 1.1 MB | 21 / **1** | 2009-02 → 2019-05 |
| `fivethirtyeight/data` | 17,431 | `airline-safety.csv` | 2 / 2 | 2014 → 2022 |

`nytimes/covid-19-data` has 1,701 commits and two authors. `openflights` has one
author across ten years — the maintainer transcribes community submissions by
hand; contributors never touch the file. The `datasets/` org (153 repos) is
bot-refreshed. **Only `iptv-org/database` and `datasets/country-codes` show
genuine many-human editing of one CSV over years.**

### 1.2 The one real case, and what it tells us

`iptv-org/database` is the strongest single piece of evidence in this report, and
it cuts both ways. 86 humans, 6,519 commits, one 40,834-row CSV. What did they
build in response?

**They built a bot to keep humans out of the file.** From CONTRIBUTING.md,
verbatim:

> "The easiest way is to submit a request using one of the available forms.
> Simply enter all the information you know and click 'Submit'. **Once your
> request is approved, the entry will be automatically added to the database.**"

`iptv-bot[bot]` is the **#2 committer on `channels.csv` (1,033 commits)** and the
**#1 committer on `feeds.csv` (432 of 609)**.

**They built a CI gate on file shape**, not on data meaning —
`.github/workflows/check.yml` runs `kforeverisback/check-crlf-extended@v2` with
`include_pattern: '*.csv'` and `continue-on-error: false`, plus a bespoke
`npm run db:validate`.

**And they warn contributors, in bold, about exactly the failure mode this design
targets:**

> "**IMPORTANT:** Before sending the request, make sure that **the number of
> columns in the file has not changed** and that all rows end with CRLF.
> Otherwise we will not be able to review this request."

Reviewers cannot read the diff, so they **paste raw CSV rows into PR comments**
and cite rows by line number, there being no other addressable unit
(PR #26714, 2026-04-03, 15 comments; `StrangeDrVN`, 2026-04-05):

> "another example- unchanged
> ```csv
> KGWDT1.us,KGW-DT1,,NBC,Tegna Inc,US,general,FALSE,1956-12-15,,,https://www.kgw.com/
> ```"

> "Are these remnants? found a few like this... eg: **line 12377, 15526, 13497**"

Explicit conflicts exist: `repo:iptv-org/database conflict` → 14 issues/PRs, of
which PR #20562 and #20545 (both 2025-08-31) are titled "fix conflicts (Patch
2025.08.2 & bot commit)" — human-vs-bot collisions on the CSV.

**This is the design's thesis observed in the wild — and the observed remedy is
not a better format.** It is (a) remove the human from the write path, (b) gate
on structural invariants in CI, (c) review by pasting rows into a comment box.
Note that (b) is precisely the DESIGN.md "conformance suite / validator" leg,
arrived at independently by a project with no interest in format theory.

### 1.3 Other in-the-wild instances of the pain

GitHub issue search, `"merge conflict" csv in:title type:issue` → **33**;
`"merge conflicts" csv in:title` → **33**; `csv conflict in:title type:issue` →
**122**. Engagement on the top hits by reactions is **0 reactions across all of
them**. The most consequential instance is in the largest OSS repo there is —
`kubernetes/kubernetes#35850`, 2016-10-29, 24 comments:

> "updates to test/test_owners.csv are now required to merge new tests. This
> adds a single file that must be updated for any new test package in the repo.
> **This is causing completely unrelated PRs to have merge conflicts with each
> other.**"

Kubernetes' resolution was, again, not a better table format: the ownership data
moved to per-directory `OWNERS` files — the **one-record-per-file** mitigation.

Two more, both showing the same instinct:
- `talonhub/community` — "Split some lists (homophones) into default &
  user-added csvs to let users more easily add things w/o merge conflicts"
  (2023-03-04)
- `avidrucker/lccjs` — "Research: replace CSV velocity log with a merge-friendly
  store (SQLite?) **to kill rebase-conflict churn**" (2026-05-29)

**Every observed mitigation moves away from one-big-table, toward
one-record-per-file or a database.** None adopts a smarter CSV.

### 1.4 Quantified complaint volume

**Stack Overflow** (exact counts, Stack Exchange API):

| Query | Questions |
|---|---|
| tags `git`+`csv` | 33 |
| tags `git`+`excel` | 38 |
| tags `version-control`+`excel` | 24 |
| tags `version-control`+`csv` | **2** |
| `[git]` q=`csv merge conflict` | **9** |
| `[git]` q=`merge driver` | 167 |
| *scale reference:* tags `git`+`json` | 189 |

Top by engagement — note the dates:

| Question | Score | Views | Answers | Date |
|---|---|---|---|---|
| Best way to do Version Control for MS Excel | 183 | **178,225** | 22 | **2008-09-25** |
| How to perform better document version control on Excel files… | 137 | **134,768** | 10 | **2013-06-13** |
| Version control on excel files in git | 8 | 8,218 | **0** | 2020-05-17 |
| Git merge and ignore all CSV conflicts automatically | **1** | 1,406 | 1 | 2018-05-15 |

Trend for `git`+`excel`: 2012:0 · 2015:2 · 2018:7 · 2021:2 · 2024:1. **Declining.**

**Hacker News** (Algolia, `tags=story`) — hit counts:
`git for data` **925–1,017** · `csv diff` **285** · `version control spreadsheet`
**36** · `diff spreadsheet` **7** · `csv merge conflict` **0 stories / 9
comments** · `merge conflict csv` **9 stories / 127 comments**.

The concept gets enormous engagement; the tools get none:

| Thread | Points | Comments | Date |
|---|---|---|---|
| Dolt is Git for Data (SQL DB you can fork/clone/branch/merge) | **752** | 176 | 2021-03-06 |
| TSV Utilities: command line tools for large tabular data | 467 | 117 | 2019-08-31 |
| Dolt is Git for data | 358 | 191 | 2020-03-30 |
| Dolt is Git for Data | 334 | 134 | 2022-06-23 |
| Difftastic: syntax-aware structured diff | 297 | 61 | 2021-07-08 |
| Show HN: Data Diff — compare tables of any size across databases | 127 | 21 | 2022-06-22 |
| Show HN: csvdiff — a fast diff tool for comparing CSV files | **21** | 2 | 2019-03-01 |
| Show HN: Csvdb — Git-friendly CSV directories → SQLite/DuckDB | **3** | 1 | 2026-02-04 |
| Show HN: VisiGrid CLI — **Git-diff for financial reconciliation** | **1** | 1 | **2026-02-03** |
| Ask HN: How should non-technical users "pull request" data changes? | **3** | 2 | 2023-07-26 |
| *Fivetran Acquires Tobiko Data (SQLMesh)* | **5** | 0 | 2025-09-03 |
| *lakeFS Acquires DVC* | **3** | 0 | 2025-11-18 |

**"Dolt is Git for Data" reached the HN front page three separate times and
totals 1,444 points. `Show HN: VisiGrid CLI – Git-diff for financial
reconciliation`, six months ago, got one point.** That gap is the whole story:
this is an idea people enjoy reading about and do not install.
---

## 2. The candidate audiences, sized and evidenced

Ranked by *demonstrated* pain, not by size.

### 2.1 dbt / analytics engineering — **hypothesis refuted**

Population is large: dbt Labs claims **80,000+ data teams** (Oct 2025), **100,000+**
combined post-merger (Jun 2026). `dbt-labs/dbt-core` 13,709★; `dbt-core` PyPI
**88,107,321 downloads/30d** (CI-inflated by orders of magnitude — use the
80–100k teams figure). **28,736** public repos contain `dbt_project.yml`; **21,792**
of those mention `seed-paths`.

**But dbt itself defines the population out of existence.** From
[docs.getdbt.com/docs/build/seeds](https://docs.getdbt.com/docs/build/seeds),
verbatim:

> "**Good use-cases for seeds:** A list of mappings of country codes to country
> names · A list of test emails to exclude from analysis · A list of employee
> account IDs"
>
> "**Poor use-cases of dbt seeds:** Loading raw data that has been exported to
> CSVs · Any kind of production data containing sensitive information."
>
> "Seeds should **not** be used to load raw data… Seeds are best suited to static
> data which changes infrequently."

dbt co-founder Drew Banin scoped seeds at roughly **1,000 lines / a few kilobytes**
on [Discourse thread 328](https://discourse.getdbt.com/t/why-cant-i-use-dbt-seed-for-large-csv-files/328)
(2019-04-30). **A 40-row country-code table diffs fine in GitHub's existing
renderer.** The files where a better format would help are the files dbt tells
you not to create.

**Complaint volume on seed *review* is zero.** dbt-core issues mentioning "seed":
937; with "seed" in title: 198; "seed"+"diff": 44 (top 25 by reactions read —
**none** about reviewing seed diffs; all node selection / `state:modified` /
unit-test fixtures). `"large seed"`: 18 — **all load performance**
(#9524 "Improve memory performance of `dbt seed`", #11860 compressed seeds,
#5309 "Seeds are considerably slower"). Stack Overflow `dbt seed csv diff`:
**0 results**. Discourse `review seed`: **0 topics**. HN `dbt seed`: 56 hits, top
story **4 points**.

> **Seed pain is entirely ingestion pain — memory, speed, warehouse rate limits.
> Not one complaint is about reading the diff.**

**Do seed PRs get substantive review? Yes — and that argues against the design.**
Sampled `ccao-data/data-architecture` (Cook County Assessor): of 11 PRs touching
seed CSVs, **6 had line-level review comments anchored on a `.csv` file**.
From [PR #1081](https://github.com/ccao-data/data-architecture/pull/1081), 4/4
comments on the CSV:

> "Note for Nicole: The array of numbers in this row represents the townships
> that the new model (`ecstatic-carly`) should apply to…" → "Thanks for the
> context! These towncodes reflect my understanding." → "Nitpick, tiny request to
> put these in numeric order" *(with a GitHub `suggestion` block)*

**Reviewers engaged semantically with the data, and plain CSV + GitHub's existing
diff and suggestion UI was sufficient.** This is the design's "do people review
data diffs when given the chance?" question answered *yes* — and the answer
removes the need for the product, because the existing tooling already clears the
bar for the file sizes that exist.

### 2.2 Research reproducibility — **no demand found**

The purpose-built artifacts in this space are tiny and static:

| Project | Stars | Downloads | Status |
|---|---|---|---|
| `ropensci/git2rdata` (store dataframes in git so they diff) | **104** | **325 CRAN dl/month** (2026-07-29→08-27) | pushed 2026-04-09 |
| `datalad/datalad` | 657 | 35,950 PyPI/30d | active |
| `frictionlessdata/frictionless-py` | 840 | 685,393 PyPI/30d | active, 237 open issues |
| `frictionlessdata/datapackage` (spec) | 583 | — | active since 2011 |

`git2rdata` is the closest thing in existence to this design's thesis, aimed
squarely at researchers, published through rOpenSci, and it moves **325 downloads
a month**.

HN interest is effectively absent: `research data versioning` → **7 story hits
total**, the top being unrelated. `reproducibility data` → 64 hits, top story
2 points. Journals require **data deposit** (Zenodo/Dryad/Figshare), which is
immutable-snapshot publication with a DOI per version — **the deposit model is
explicitly anti-diff**: a new version is a new DOI, and nobody diffs across them.
No evidence found of researchers diffing datasets across revisions as a practice.

### 2.3 Agent-generated changes to structured data — **capability yes, review no**

The *capability* is real and adopted:

| Thing | Stars | Created | Last push |
|---|---|---|---|
| `haris-musa/excel-mcp-server` | 4,144 | 2025-02-12 | **2026-04-12 (4½ months stale)** |
| `negokaz/excel-mcp-server` | 1,017 | 2025-02-16 | **2025-07-19 (13 months stale)** |
| `xing5/mcp-google-sheets` | 991 | 2025-03-22 | 2026-05-14 |
| `domdomegg/airtable-mcp-server` | 456 | 2024-12-12 | 2026-08-11 |
| `iOfficeAI/OfficeCLI` (keeps .docx/.xlsx, gives agents a render loop) | **29,451** | 2026-03-15 | 2026-08-25 |

Note the shape: **the biggest project by an order of magnitude is the one that
keeps the binary format.** OfficeCLI at 29,451★ in five months is the direct
counter-thesis — agents work on `.xlsx` fine, and nobody needed a new format for
it.

**The review step is not observed.** Searching the Claude Code tracker,
`repo:anthropics/claude-code csv in:title` → **8 issues**, of which the top by
reactions are *paste/upload bugs* ("[BUG] CC 'Image cannot be empty' when pasting
a copied selection of a CSV", 7 reactions) — **not one** is "the agent changed my
data and I could not review the diff." HN stories on AI-spreadsheet agents are
uniformly ignored: "Show HN: Open-source AI agent for spreadsheets" (2025-12-14)
**2 points**; "Show HN: Cellect – AI agent for spreadsheets" (2025-10-30)
**1 point**; "Building an AI agent for spreadsheets – 4 months of learnings"
(2026-03-03) **1 point**; "Shortcut.ai Is A Great Excel Agent" (2026-02-12)
**1 point**.

**No product exists whose pitch is "review what the AI changed in your
spreadsheet."** That is either a gap or a non-need; nothing found distinguishes
them. This argument in DESIGN.md is the newest and remains **entirely
unevidenced** — it is a plausible story about the future, not an observation.

### 2.4 Finance / FP&A — where the money actually went

**Not one company reached >$50M ARR or a >$100M disclosed exit selling
spreadsheet error-reduction.** Every audit-side exit was an undisclosed-price
tuck-in. The enterprise-value asymmetry against auditing is roughly **100:1**.

**The audit-the-spreadsheet market:**

| Vendor | Outcome | Date |
|---|---|---|
| **ClusterSeven** | → Mitratech, price undisclosed | **2020-01-29** |
| **Prodiance** | → **Microsoft** (*correction to the brief: not EMC*), price undisclosed | **2011-06-07** |
| **CIMCON** | **Alive, largest survivor.** Founded 1988, ~1,000 customers, **never raised a disclosed round in 38 years**; now repositioning to AI governance | — |
| Mobilise/Finsbury | absorbed into CIMCON | ~2023 |
| Compassoft | dead, site last live ~2008 | — |
| Spreadsheet Advantage | zombie — TLS cert expired **2025-06-18**, never renewed | — |
| Rainbow Analyst | dead, domain does not resolve | — |
| Incisive Software, PerfectXL, Operis OAK | alive, micro, presumed bootstrapped | — |

**No analyst firm sizes this category.** "End-user computing market" reports all
mean VDI/device management. The absence of a Gartner or Forrester number for
spreadsheet controls is itself the finding.

**The replace-the-spreadsheet market, for contrast:**

| Event | Size | Date |
|---|---|---|
| **Anaplan** → Thoma Bravo (announced $10.7B, renegotiated) | **~$10.4B** | announced 2022-03, closed 2022-06 |
| **Adaptive Insights** → Workday | **$1.55B** | 2018-08 |
| **Vena** — Vista growth round; crossed $100M ARR 2024-07 | **$300M** | 2021-04-27 |
| **Pigment** Series D (ICONIQ); ~$100M ARR est. | **$145M** | 2024-04-04 |
| **Causal** → Lucanet, price undisclosed | — | 2024-10-31 |
| **Cube** | ~$49M raised | — |

> **Auditing spreadsheets is a compliance line item bought under regulatory duress
> by a risk officer. Replacing them is a platform bought by a CFO with a budget.**

**Version-control startups specifically are a graveyard.** **EqualTo is dead** —
`www.equalto.com` has no DNS record, last live archive 2023-10-30, GitHub org
404s — and note that **its pitch was "spreadsheets as a service for developers,"
never version control**. Rows → Superhuman (~2026-02). **Equals** raised $16M
then **pivoted away from spreadsheets** to RevOps AI. Quadratic and Sourcetable
took single-digit-million seeds and **neither pitches version control**.
**xltrail is the only "git for Excel" product still trading** (§4.6).

**And finance practitioners are not looking for a tool.** HN Algolia, all time:
"spreadsheet version control" → **41 stories**. Dedicated products score ~1 point:
`spreadgit.com` 2013 (**1 pt, 0 comments**) and 2014 (**1 pt, 0 comments**);
"Show HN: Version Control for Excel" 2014 (**1 pt, 3 comments**) and 2021
(**1 pt, 0 comments**). The single decade-long exception is **xltrail,
2018-02-19 — 95 points, 23 comments**, with six further xltrail posts that year
scoring 2–4. Meanwhile the *problem* framing lands hard: Wired's "Excel warriors
who save governments and companies from spreadsheet errors" (2020-10-15) took
**258 points and 186 comments**, and "88% of spreadsheets have errors"
(2013-04-23) took **4**.

Stack Overflow says the same: "Best way to do Version Control for MS Excel"
(2008-09-25) has **183 votes, 22 answers, 178,225 views**, and "How to perform
better document version control on Excel files…" (2013-06-13) has **137 votes,
134,768 views**. **Hundreds of thousands of people look this up and no tool ever
won the vote.** That is a chronic annoyance, not purchase intent.

*(Not answered: r/FPandA and Wall Street Oasis were unreachable — HTTP 403 to
both curl and WebFetch — so the practitioner-forum quantification is a gap.)*

### 2.5 The regulatory wedge — it does not exist for finance, and does exist for pharma

The brief asked for **actual regulatory text**. Here it is, primary-sourced.
The vendor claim "SOX requires spreadsheet version control" is **false**.

| Instrument | Binding? | Names spreadsheets? | Names version control? |
|---|---|---|---|
| **PCAOB AS 2201** (SOX §404 audit standard) | binding on auditors | **NO — zero occurrences** of "spreadsheet", "end-user computing", or "version control" in a full-text grep | **NO** |
| **SR 11-7** (Fed/OCC, 2011-04-04) | **guidance**, not a rule | **YES** | change control, not version control |
| **Solvency II** Dir. 2009/138/EC Arts. 115, 125 | **binding** | NO | "model change policy", supervisory approval |
| **BCBS 239** ¶36(b) (Jan 2013) | principles | **YES** | **NO** — "lineage", "version" and "audit trail" appear **nowhere** in the document |
| **21 CFR Part 11** §11.10(e), (k)(2) (62 FR 13464, 1997-03-20) | **BINDING LAW** | applies to any electronic record | **YES, explicitly** |
| **EU AI Act** Reg. 2024/1689, Recital 12 | binding | **excludes them by recital** | — |

**SR 11-7, Section V, verbatim** — the strongest finance text found:

> "Computer code implementing the model should be subject to rigorous quality and
> change control procedures to ensure that the code is correct, that it cannot be
> altered except by approved parties, and that **all changes are logged and can be
> audited**. … **User-developed applications, such as spreadsheets or ad hoc
> database applications used to generate quantitative estimates, are particularly
> prone to model risk.**"

§II calls it "guidance" and "supervisory expectations." Examiners enforce it, but
**it never says "version control."**

**21 CFR Part 11 — the one instrument that reads like a specification for git:**

> **§11.10(e)** "Use of secure, computer-generated, time-stamped **audit trails**
> to independently record the date and time of operator entries and actions that
> create, modify, or delete electronic records. **Record changes shall not obscure
> previously recorded information.**"
>
> **§11.10(k)(2)** "**Revision and change control procedures to maintain an audit
> trail that documents time-sequenced development and modification of systems
> documentation.**"

That is binding US law demanding exactly what a commit graph provides. **Its
audience is GxP — pharma, clinical, laboratory — not FP&A.** If a regulated wedge
exists anywhere in this search, it is here and nowhere else. Nothing was found
establishing that GxP teams currently want it in git, so treat this as a lead,
not a finding.

**BCBS 239 correction.** ¶36(b) says only: *"Where a bank relies on manual
processes and desktop applications (eg **spreadsheets**, databases)… it should
have effective mitigants in place (eg **end-user computing policies and
procedures**)."* It is frequently cited as a data-lineage mandate; it is not.

**And the statistic underpinning the whole "spreadsheet errors" framing is
weak.** Panko, *"What We Know About Spreadsheet Errors"* (J. End User Computing
10(2), Spring 1998, rev. May 2008) — the source of the ubiquitous "88% of
spreadsheets contain errors" — reports **113 spreadsheets across 7 studies**,
with per-study samples of **n = 1, 2, 3, 7, 22, 23, 25, 30**. Three of the "100%
error rate" entries rest on n ≤ 3; two are interviews rather than audits; the
newest underlying study is **2007**; and one sample is "the 30 most financially
significant spreadsheets audited by Mercer in the previous year." **Severe
selection bias, two decades stale, and materially over-cited.** DESIGN.md does
not lean on it, and should continue not to.

**Supply-chain note for DESIGN.md §13.** `IronCalc`, the formula engine DESIGN.md
recommends, is **EqualTo's engine**, and **EqualTo is dead** — `www.equalto.com`
has no DNS record, last live archive 2023-10-30, GitHub org 404s. IronCalc now
survives on **EU Horizon / NLnet grants**, not commercial revenue. That is not
disqualifying (grant-funded infrastructure can be durable) but it is a different
risk profile than "Apache-2.0, 4,125★" implies, and it should be recorded.

---

## 3. The hack ecosystem as a demand proxy — measured against Jupyter

The brief's premise: *the size of the hack ecosystem is the best proxy for unmet
demand.* Agreed. Here it is, measured, against the control group — Jupyter
notebooks, a genuinely git-hostile format whose hack ecosystem became universal.

### 3.1 Tabular-data tools

| Tool | Stars | Last **commit** | Downloads/mo | Verdict |
|---|---|---|---|---|
| `BurntSushi/xsv` | 10,761 | 2025-04-24 | crates 5,408/90d | **ARCHIVED** |
| `wireservice/csvkit` | 6,410 | 2026-08-03 | PyPI 491,963 | alive; **no diff command** |
| `dathere/qsv` (has `qsv diff`) | 3,769 | 2026-08-28 | crates **1,659/90d** | alive, tiny |
| `paulfitz/daff` (CSV 3-way diff/merge) | 923 | 2025-05-04 | **npm 14,053** | low energy; git integration effectively unmaintained |
| `xltrail/git-xl` | 605 | **2023-02-19** | — | **abandoned 3.5 yrs**; VBA-only, never diffed cell data |
| `aswinkarthik/csvdiff` | 585 | **2020-02-21** | — | **abandoned 6.5 yrs** |
| `githubocto/flat` — **GitHub's own Flat Data** | 485 | — | — | **ARCHIVED BY GITHUB** |
| `dedupeio/csvdedupe` | 434 | 2020-03-31 | PyPI **71/mo** | **dead** |
| `githubocto/flat-ui` | 379 | — | — | **ARCHIVED** |
| `simonw/csv-diff` | 340 | 2024-09-06 | PyPI 335,688 | dormant ~2 yrs |
| `tokuhirom/git-xlsx-textconv` | 148 | 2025-01-21 | — | marginal |
| `ropensci/git2rdata` | 104 | 2026-04-09 | **325 CRAN/mo** | negligible |
| `yappo/p5-git-xlsx-textconv.pl` | 43 | **2014-06-19** | — | **abandoned 12 yrs** |
| best Sheets→git sync repo found | **45** / **10** | **2021-01-30** | — | abandoned |

**GitHub built the productized version of this idea — Flat Data, 2021 — and
archived it.** That is the closest thing to a controlled experiment available:
the distribution owner shipped it, and it did not take.

**The daff download anomaly, resolved.** PyPI reports ~25.2M non-mirror
downloads/month for `daff`, 99.9% Linux — because **`dbt-core` pins
`daff>=1.3.46`**, and dbt-core does 88.1M downloads/month. Nobody is choosing
daff; dbt is installing it. Human-scale daff usage is the **npm figure: 14,053
per month**. For scale, npm `csv-parse` does **77.1M/mo**, `papaparse` 62.3M/mo,
`xlsx` 51.4M/mo — **the format is roughly 4,000× more popular than the git
tooling for it.** daff's own git-driver bug, issue #68 "Git Diff :: ENOENT
error", has been **open since 2016-06-15 — ten years**.

### 3.2 Repo-level configuration — who actually installs a hack

| Pattern in `.gitattributes` / `.pre-commit-config.yaml` | Repos/files |
|---|---|
| `filter=lfs` | **163,840** |
| `merge=union` | **15,424** |
| `nbstripout` (pre-commit) | **4,952** |
| `merge=ours` | 4,768 |
| `*.xlsx binary` — **gave up** | **3,672** |
| `*.xlsx filter=lfs` — **gave up, hid it in LFS** | **2,776** |
| `nbstripout` (.gitattributes) | 620 |
| `textconv` anywhere | 328 |
| `diff=daff` / `merge=daff` | **121 / 118** |
| `diff=csv` | **112** |
| `diff=xlsx` | **28** |
| `csvdiff` in `.github/workflows` | 20 |
| **`merge=csv`** | **6** |
| `xlsx2csv` (pre-commit) | **0** |

> **Give-up-to-hack ratio for spreadsheets: ~230:1** — 6,448 repos declare
> `.xlsx` binary or push it into LFS, against **28** that try the textconv hack.

*(Baseline: 28,992 `.gitattributes` mention `csv` at all and 9,008 mention
`xlsx` — overwhelmingly `text eol=lf` / `binary` / LFS declarations, not tooling.
**Under 1%** of repos that bother to declare anything about a CSV install a
CSV-aware tool.)*

### 3.3 The control group

| Jupyter hygiene tool | Stars | Last push | PyPI / 30d | Repo installs |
|---|---|---|---|---|
| `mwouts/jupytext` | **7,234** | 2026-08-18 | **3,642,102** | 488 pre-commit |
| `jupyter/nbdime` | **2,841** | 2026-06-10 | 289,559 | 329 `diff=jupyternotebook` |
| `kynan/nbstripout` | **1,479** | 2026-04-11 | **2,591,485** | **4,952** pre-commit + 620 `.gitattributes` |
| **total** | **11,554★** | all active | **6.5M/mo** | **~6,400 repo installs** |

### 3.4 Reading

**Jupyter's unmet-demand signature is ~11,500 stars, 6.5M monthly downloads and
~6,400 repo-level installations across three actively-maintained tools.
Tabular data's equivalent is ~240 repo-level installations, and of the twelve
tools above, six are archived, dead, or untouched for 3–12 years.**

Two structural differences explain it, and only one favours the design:

1. **Jupyter's hacks require nothing of the consumer.** `nbstripout` deletes
   outputs before commit; `jupytext` writes a paired `.py`. The resulting bytes
   are ordinary to everyone downstream. **Every CSV hack requires the *reader*
   to install a merge driver or textconv filter** — which is exactly the
   deployment failure DESIGN.md §3(b) establishes (`.gitattributes` travels,
   `.git/config` does not, a bare repo consults neither). *The tabular hack
   ecosystem is small partly because the hacks structurally cannot work.* That
   is a point for the design's mechanism.
2. **But a real hack ecosystem converges on one winner and appears in thousands
   of repos.** This one never converged: GitHub repo-search totals are `csv diff`
   **668**, `excel diff` **594**, `xlsx diff` **122**, `spreadsheet diff` **85**
   — and the top-starred `xlsx diff` repo has **21 stars**. Hundreds of people
   wrote a tool; almost nobody adopted anyone else's. That is the signature of a
   problem people find *annoying enough to scratch* and not *painful enough to
   standardise on a fix.*

**The dominant observed response is neither hack nor format. It is
`*.xlsx binary` — 3,672 repos deciding the diff is not worth having.**

## 4. The honest counter-case

### 4.1 The concept is loved; the tools are ignored

This is the sharpest pattern in the data. "Dolt is Git for Data" hit the HN front
page **three separate times** (752 + 358 + 334 = 1,444 points, 501 comments,
2020–2022). Dolt today: **24,287★, 868 forks, but only 124 watchers and 705 open
issues.** Meanwhile:

- `Show HN: csvdiff` (2019-03-01): **21 points**
- `Show HN: Csvdb — Git-friendly CSV directories` (2026-02-04): **3 points**
- `Show HN: VisiGrid CLI — Git-diff for financial reconciliation` (2026-02-03):
  **1 point**
- `lakeFS Acquires DVC` (2025-11-18): **3 points**, 0 comments
- `Fivetran Acquires Tobiko Data` (2025-09-03): **5 points**, 0 comments

**People upvote "git for data" as an idea and do not install the artifact.**
This is precisely the confusion RESEARCH.md warns about — "people complain about
X" versus "people would adopt a new format to fix X" — and here even the
complaining is thin.

### 4.2 The most on-target artifact found, and its reception

Ask HN, 2023-07-26, **3 points, 2 replies** — a verbatim description of exactly
the workflow this design serves:

> "We have some configuration data that our non-technical, business employees
> need to update occasionally. That has to be approved to make sure it's
> correctly formatted, and then pulled into our production codebase to run. So
> we've set up a flow: **there's a spreadsheet (CSV) in the github repository.**
> We've taught the non-technical user how to download it, edit it in Excel, and
> then submit a PR. We then have an engineer approve the PR (as usual)…
> **Obviously this is clunky for everyone involved. Has anyone found an
> out-of-the-box solution for this?**"

Both replies told him to **move the data out of git**:

> "Keep the primary copy on server somewhere — in google sheets, or in Airtable,
> or even as Excel file on a shared drive… Create an automation (github action,
> jenkins job, whatever) that takes current version of spreadsheet, exports to…"
> — `theamk`

The market's answer to this person, in 2023, was Airtable. It still is.

### 4.3 Bounding the population

The people who both (a) use git comfortably and (b) hand-maintain tabular data:

| Bound | Count |
|---|---|
| Public repos, `topic:dataset` | 17,896 |
| Public repos, `topic:open-data` | 7,742 |
| Public repos with `dbt_project.yml` | 28,736 (of which most seeds are <1k rows by policy) |
| Repos whose product *is* a hand-edited CSV, star-sorted | tops out at **282★** (`qcif/data-curator`, last pushed 2021-11-25) |
| `.gitattributes` configuring a CSV merge driver (`merge=csv`) | **6** |
| `.gitattributes` mentioning `daff` | **115** |
| `.gitattributes` with `diff=csv` | **112** |
| `.gitattributes` with `textconv` + `xlsx` | **7** |
| `.pre-commit-config.yaml` with `xlsx2csv` | **0** |

Against the Jupyter calibration in the same index — the closest *successful*
analogue, a non-git-friendly format whose hack ecosystem became near-universal:

| Calibration | Count |
|---|---|
| `.gitattributes` with `filter=lfs` | **163,840** |
| `.gitattributes` with `merge=union` | **15,424** |
| `.gitattributes` with `merge=ours` | **4,768** |
| `.pre-commit-config.yaml` with `nbstripout` | **4,952** |
| `.gitattributes` with `nbstripout` | **620** |
| `nbstripout` PyPI | **2,489,477 / 30d** |
| `jupytext` PyPI | **3,642,102 / 30d** |
| `nbdime` PyPI | **289,559 / 30d** |

**Jupyter's unmet-demand signature is 5,572 repo-level configurations and 6.4M
monthly downloads across three tools. Tabular data's equivalent is ~240 repo-level
configurations.** If the hack ecosystem is the demand proxy, the reading is
unambiguous.

*(The one number that appeared to resist this reading is now resolved and does
not: `daff` shows ~25.2M PyPI downloads/month, but **`dbt-core` pins
`daff>=1.3.46`** and dbt-core does 88.1M/month. Those are dbt installs, not daff
users. Human-scale usage is npm's **14,053/month**.)*

### 4.4 The graveyard, extended

Adding to RESEARCH.md's Kova data point ($0.00 raised, 67 releases in 3.7 months):

| Project | Capital / backing | Peak | Outcome |
|---|---|---|---|
| `datafold/data-diff` — "review the data diff in your PR" | Datafold, YC S20; Launch HN 189 pts | 2,991★ | **Archived 2024-05-17**, final commit `Merge pull request #897 from datafold/sunset` |
| Tobiko Data / SQLMesh | **$21.8M** ($4.5M seed + $17.3M A, 2024-06-05, Theory Ventures) | 3,260★ | **Acquired by Fivetran 2025-09-03**, ~15 months post-A; SQLMesh donated to Linux Foundation 2026-03 |
| Iterative.ai / **DVC** | VC-backed | 15,850★, 2.66M PyPI/30d | **Acquired by lakeFS**, announced 2025-11-18 |
| dbt Labs | a16z | 13,709★ | **Merged into Fivetran** (announced 2025-10-13, closed 2026-06-01) |
| `InfuseAI/piperider` | — | 495★ | Dead, last push 2025-01-03 |
| `DataRecce/recce` | independent | **476★** after ~3 years | Alive but tiny |
| `dbt-labs/dbt-audit-helper` (first-party!) | dbt Labs | **422★** vs `dbt_utils` 1,793★ | 4× fewer stars after 7 years |
| `aswinkarthik/csvdiff` | — | 585★ | Last **commit** 2020-02-21 (abandoned 6.5 yrs) |
| `simonw/csv-diff` | — | 340★ | Last commit 2024-09-06 |
| `paulfitz/daff` | — | 923★ | Last commit 2025-05-04; git-driver bug #68 open since **2016** |
| **DoltHub** (dolt) | **~$21.0M** (Form D $5.0M 2019-10-25, $16.0M 2021-08-11, Alpha Edison) | 24,287★ | Operating, **15 people**; pivoted from data-sharing to an OLTP database |
| **Iterative.ai** (DVC) | **~$24.5M** ($3.85M seed 2019; $20.05M A 2021-02-11, 468 Capital). **No Series B** | 15,850★, 2.66M PyPI/mo | **Wound down.** DVC sold to lakeFS 2025-11-18; org has **17 commits in 90 days**, mostly dependabot — a 15.8k-star zombie |
| **Treeverse (lakeFS)** | **$43M** ($8M seed, $15M A 2021, $20M growth 2025-07-29) | 5,499★ | Operating; now the consolidator |
| **Pachyderm** | $28M | — | Acquired by HPE 2023-01-12; repo dormant since 2025-02-03 |
| **XetHub** | $7.5M | — | Acquired by Hugging Face 2024-08-08 |
| **githubocto/flat** (GitHub Flat Data) | GitHub itself | 485★ | **ARCHIVED** |
| `ropensci/git2rdata` | rOpenSci | 104★ | 325 CRAN dl/month |

Datafold's own [sunset post](https://www.datafold.com/blog/sunsetting-open-source-data-diff)
(2024-05-17) gives the reason verbatim — maintaining the OSS tool "required
maintaining two distinct products with different codebases yet significantly
overlapping functionality," with resources going to "increasing demand for
Datafold Cloud" — and publishes **no adoption or conversion metrics at all**.
For a company sunsetting a 3,000-star project, that silence is itself data.

**Read together: >$20M of identified capital went into "review the data change
in a PR" for the exact audience the design names, and produced zero standalone
survivors.** Where the capability lives on, it lives as a feature inside a
data-platform (dbt Cloud "compare changes"/Slim CI, Datafold Cloud) sold to a
platform buyer — never as a format or a diff tool sold to the practitioner.

### 4.4.1 The verbatim record from the best-funded attempt

**Tim Sehn, DoltHub CEO, "The Dolt Timeline" (2024-07-25)** — the
data-collaboration thesis failing in the founder's own words:

> "As hard as we tried to bootstrap a data sharing ecosystem, potential customers
> kept showing up asking if they could run Dolt as their production Online
> Transaction Processing (OLTP) database... **It felt like we were pushing data
> sharing but OLTP was pulling us.**"

**Sehn, "Selling Software: Introduction" (2025-04-01)** — and the collaboration
product is specifically the one that does not earn:

> "Most of our revenue is split evenly between support, Hosted Dolt, and DoltLab
> Enterprise. **DoltHub Pro is not a big money maker for us yet.**"

**Sehn, "20,000 Stars" (2026-02-25):**

> "During the downs, GitHub stars have always carried us."

Dolt raised ~$21.0M, employs 15 people, sells enterprise support from
**$5,000/month**, and holds 24,287 stars with 622 commits in the last 90 days.
It is the healthiest thing in this space, and it got there by **abandoning the
collaboration story for a database**.

Two more, from the demand side:

**Stack Overflow #61854164, "Version control on excel files in git", 8,218 views,
zero accepted answers:**

> "one way is to save .xlsx file as a csv file and use git diff. However, this
> option doesn't work when there are multiple sheets. I'll be able to save only
> the active sheet as csv file."

**Ask HN, 2021-08-16, "How would you best diff two csv-s in 2021?"** — top answer:

> "I would use something like pandas or dplyr." — reply: "**I use these myself on
> a daily basis, but it can turn into quite a grind.**"

*That reply is the honest ceiling of the felt pain in this market: a grind.*

### 4.5 The mitigation people actually choose

Every observed real-world response to CSV-merge pain moves *away* from a shared
table, and none adopts a better table format:

- **Kubernetes** → per-directory `OWNERS` files (one record per file)
- **iptv-org** → a bot writes the rows; humans fill in an issue form
- **talonhub/community** → split the CSV into default + user-added files
- **avidrucker/lccjs** → "replace CSV velocity log with a merge-friendly store
  (SQLite?)"
- **Ask HN 36877992 respondents** → "keep the primary copy in google sheets, or
  in Airtable"
- **OfficeCLI (29,451★ in 5 months)** → keep `.xlsx`, give the agent a render loop

**A refinement on the flagship case, verified independently.** `iptv-org/database`
`data/channels.csv` does have 6,519 commits and 86 distinct authors — but the
distribution is extremely concentrated: the top five committers account for
**5,748 of 6,519 commits (88%)**, and one of those five is the bot:

    Aleksandr Statciuk  3,127
    iptv-bot[bot]       1,033
    sguinetti             978
    AntiPontifex          410
    freearhey             200

So even the single best example of "many humans hand-editing one table in git"
is, on inspection, **three maintainers and a bot**, with a long tail of 81 people
who touched it a handful of times each. The many-writers scenario that motivates
nominal addressing and merge correctness is rarer than the headline number
suggests.

### 4.6 The one alive, priced commercial product — and it is not this design

**xltrail** (Zoomer Analytics, the `xlwings` people) sells "a version control
system for Excel workbooks" that "tracks changes, compares worksheets and VBA,
and provides an audit trail," at **USD 35 per user/month paid yearly** for cloud,
with self-hosted Business and Enterprise tiers (LDAP/AD, project permissions,
air-gapped installs) priced on application. Its own positioning, verbatim:

> "trusted by some of the world's most highly regulated insurance and financial
> services organisations"

This is the single strongest live commercial signal found in the whole search —
**and it validates the opposite architecture.** xltrail keeps `.xlsx` and makes
it diffable *around* git (its open-source git plugin `xltrail/git-xl` is 605★ and its
last **commit** was **2023-02-19** — abandoned 3.5 years, and VBA-only: it never
diffed cell data at all). It does not ask anyone to adopt a new plaintext
table format. The adjacent tool `tokuhirom/git-xlsx-textconv` (148★, last push
2025-01-21) does the same thing more cheaply.

**The observed willingness-to-pay in this space is for an audit trail over the
format finance already uses — not for a better format.**

And it is a very small business. Ownership moved from Zoomer Analytics LLC to
**Pathio Limited** (UK Companies House 09117321), whose every filing is
**micro-entity accounts** — turnover ≤ ~£632k, ≤10 employees. The pricing has
been **$35/user/month unchanged since 2019**, the last self-hosted release was
2026-05-28, and the blog's newest post is **2021-08-26**. Its single strong
public moment was **HN 2018-02-19: 95 points, 23 comments** — the highest score
any spreadsheet-version-control product has ever recorded, by a factor of ~95
over `spreadgit.com` (1 point, twice).

A customer testimonial worth keeping, because it names what the buyer values:

> "the best and the only out of the box solution for Excel source control that
> fully integrates with Git! **No more work-arounds with exporting/importing VBA
> modules or maintaining versioned copies of the same document.**"
> — Natalya Arbit, EDR

### 4.7 One more bound: who governs a CSV like code?

`CODEOWNERS` assigns a required reviewer to a path, so a `CODEOWNERS` entry
naming a `.csv` is a direct proxy for "an organisation that treats tabular data
as reviewable, governed material."

| Search | Files |
|---|---|
| `csv filename:CODEOWNERS` | **289** |
| `"data/" filename:CODEOWNERS` | 2,656 |
| `md filename:CODEOWNERS` *(baseline)* | 28,416 |

**289 repositories on all of public GitHub require a named human to review a CSV
change.** That is the most generous honest estimate of the population that has
already adopted the *behaviour* the design is built around.

### 4.8 The concentration finding — and why it undercuts I2

Checked across every "community-curated CSV" candidate found, author distribution
is dominated by one to three people:

| Repo | Total commits on the table | Top author's share |
|---|---|---|
| `iptv-org/database` `channels.csv` | 6,519 (86 authors) | 3,127 = **48%**; top 5 = **88%** |
| `toolleeo/awesome-cli-apps-in-a-csv` (2,600★) | 2,495 | 1,840 = **74%** |
| `nytimes/covid-19-data` `us-states.csv` | 1,701 | 2 authors total |
| `jpatokal/openflights` `airports.dat` | 21 | 1 author over 10 years |

Actively-maintained public data repos, as an outer bound:
`topic:dataset pushed:>2026-06-01` → **3,566**;
`topic:open-data pushed:>2026-06-01` → **4,577**.

**Concurrent independent edits to the same table by unrelated people — the
scenario that motivates nominal addressing, the 480-vs-660 case, and I2 — is
empirically rare even in the repos that look most like it.** The dominant real
pattern is one maintainer plus a bot plus drive-by contributions that arrive
serially through a PR queue. Serial edits through a queue do not produce the
silent-wrong merge; they produce a review-readability problem, which GitHub's
existing CSV renderer plus inline suggestions already handles for the file sizes
that actually exist (see §2.1, `ccao-data` PR #1081).

### 4.9 The one place this discipline DID win — and what it implies

Localization is the closest thing to a positive precedent, and it is worth
stating because it is the only one found.

GNU gettext `.po` is line-oriented plain text with **nominal addressing** (the
`msgid` is the key, never a coordinate), **one entity per block**, and it merges
under stock git. It exists because localization is a genuine many-writer problem
on structured data — hundreds of translators, one string catalogue per language,
edits arriving concurrently from strangers. The discipline DESIGN.md derives from
first principles is, in this one domain, thirty years old and universal.

Scale, for contrast with §4.3:

| Signal | Count |
|---|---|
| `.gitattributes` mentioning `po` + `merge` *(loose query, approximate)* | **~16,992** |
| Public repos `topic:i18n` | 9,176 |
| Public repos `topic:localization` | 6,438 |
| `WeblateOrg/weblate` | 6,043★, active today (created 2012) |
| `translate/translate` (translate-toolkit) | 973★, active |

**Two lessons, and they point in opposite directions.**

*For the design:* the format discipline is not exotic and it does work at scale
when the many-writer problem is real. `.po` is the existence proof that
line-oriented nominal plaintext beats a positional table for concurrent editing.

*Against the design:* the commercial layer that grew on top of `.po` is **not a
format, a spec, or a conformance suite** — it is a hosted web editor
(Weblate, Crowdin, Lokalise, Transifex, Phrase) whose entire job is to keep
translators out of the file and to commit on their behalf. That is the same
answer `iptv-org` reached with its issue-form bot, and the same answer the Ask HN
respondents gave ("keep the primary copy in Airtable"). **Three independent
populations facing this exact problem all converged on "a UI writes the file,"
not on "a better file."**

### 4.10 Sheets-to-git sync: the hypothesised hack does not exist

The brief expected a population syncing Google Sheets into git. Searching
`google sheets git sync in:name,description`, star-sorted, the entire visible
ecosystem is:

    45★  rupert-git/airtable-to-google-sheets     last push 2021-01-30
    10★  cockroachlabs/gsheet-to-github-issues    last push 2021-02-21
     3★  sr480/gitlab-sync                        last push 2024-03-10
     3★  larsiusprime/loc-sync                    last push 2016-12-30
     2★  sammarks/cloudformation-github-sheets-sync  last push 2023-01-24

Top result is 45 stars and five years stale. **There is no Sheets-to-git hack
ecosystem.** (Note again that two of the five are localization tools.)
---

## 5. What would the first user look like?

**The narrowest population with *demonstrated* (behavioural, not verbal) pain:**

> A **public reference-data registry** whose product *is* a table — one to three
> regular maintainers plus a long tail of drive-by PR contributors, a table
> between roughly 1,000 and 50,000 rows, consumed downstream by software, where
> a wrong row ships to users.

Named instances, all verified: `iptv-org/database` (40,834 rows, 86 authors, 88%
of commits from five accounts, 136,914★ on the parent project),
`datasets/country-codes`, `toolleeo/awesome-cli-apps-in-a-csv` (2,600★, 2,495
commits), `talonhub/community`, `ccao-data/data-architecture`.
Outer bound on the population: **3,566–4,577** actively-pushed public repos under
`topic:dataset` / `topic:open-data`; **289** repos anywhere on GitHub that name a
`.csv` in `CODEOWNERS`.

**What they use today, in their own configuration files:**

1. CSV in git, reviewed through GitHub's built-in CSV diff renderer
2. a **bespoke shape validator** in CI (`npm run db:validate`)
3. a **CRLF / column-count gate** (`check-crlf-extended@v2`,
   `continue-on-error: false`)
4. an **issue-form bot that writes the rows**, so contributors never open the file
5. **PR comments containing pasted raw CSV rows and line numbers**, because
   there is no other way to address a row in review
6. a bolded CONTRIBUTING warning that a text editor will silently change the
   column count

**The uncomfortable implication for DESIGN.md.** Items 2, 3 and 6 are a
hand-rolled, project-specific version of *exactly* the deliverable §17 proposes —
a validator plus a conformance-tested notion of a well-formed table. Item 5 is a
demand for **nominal row addressing** in the *review* channel, expressed as its
absence. But items 1 and 4 say the same population is content with plain CSV
bytes and is actively **removing** humans from the write path.

So the evidence supports the *validator / specified-format* half of the
deliverable and does **not** support the *merge-correctness* half: with a bot and
a PR queue serialising the writes, the concurrent-insert silent-wrong merge that
motivates I2 and the 480-vs-660 case **does not arise for them**.

**And the population cannot pay.** These are volunteer OSS registries and civic
data offices. The only entity found in this whole search that charges money for
adjacent work is xltrail at USD 35/user/month — a micro-entity selling an *audit
trail over `.xlsx`* to regulated finance, i.e. the opposite architecture, to a
different buyer.

### 5.1 The one untested lead worth naming

**GxP-regulated tabular records under 21 CFR Part 11.** §11.10(e) and (k)(2) are
binding US law requiring "secure, computer-generated, time-stamped audit trails"
where "record changes shall not obscure previously recorded information," plus
"revision and change control procedures to maintain an audit trail that documents
time-sequenced development and modification." That is a legal specification a
commit graph satisfies natively, and it is the *only* binding text found in the
entire regulatory sweep that does so.

**But nothing in this pass establishes that GxP teams want it in git.** They
currently buy validated LIMS/eDMS systems that provide the audit trail inside a
database. Treat this as the single highest-value unanswered question from this
track, not as a finding — and note that it points at a *validated-system* sale
(qualification packages, IQ/OQ/PQ, vendor audits), which is a very different
product from a file format and a conformance suite.

### 5.2 If the honest answer is required in one sentence

*The narrowest population with demonstrated pain is a few thousand volunteer
open-data registries who have already built the validator half of this design by
hand, do not experience the merge half, and have no money; the only population
with a legal obligation that matches the design has never been asked.*

*(One more prevalence contrast for §4.5: `"one file per" yaml data in:readme` →
**7,577** public repos, versus **73** for `recutils`/`recfile`, the closest
existing plaintext record format. When people hit table-in-git pain, they
overwhelmingly reach for one-record-per-file, not for a better table format.)*
---

## 6. The Kubernetes case, in full — and the nuance that matters most

`kubernetes/kubernetes#35850` (2016-10-29, 24 comments) is the single most
consequential in-the-wild instance of table-in-git pain found, in the largest
repo there is. The opening report, verbatim:

> "updates to test/test_owners.csv are now required to merge new tests. This adds
> a single file that must be updated for any new test package in the repo. **This
> is causing completely unrelated PRs to have merge conflicts with each other.**"

The exchange that follows is the important part:

> **fejta:** "Any time two commits change the same file one needs to be rebased —
> **even if there are no merge conflicts.**"
>
> **caesarxuchao:** "Does that mean two PRs that add/remove two different tests
> will cause each other to rebase?"
>
> **fejta:** "**Yes** 😞"

**`test/test_owners.csv` no longer exists** in kubernetes/kubernetes (contents API
returns 404); ownership moved to per-directory `OWNERS` files.

**Why this is the most important nuance in the report.** The cost these engineers
actually paid was **file-level contention in a merge queue** — the submit queue
required a rebase whenever two commits touched the same path, *whether or not the
content merged cleanly*. A representation that makes stock git's line merge
correct **does not fix this at all**: git still records that both commits touched
`data/budget.tbl`, and the queue still demands a rebase. Only decomposition —
one record per file — fixes it, which is what Kubernetes did.

So the ranking of real, observed costs of keeping a table in git is:

    1. FILE-LEVEL CONTENTION in a merge queue          observed, severe, and
                                                       NOT fixed by a better format
    2. UNREADABLE DIFFS / no way to address a row      observed (iptv-org PR
       in review                                       comments), fixed by a
                                                       better format
    3. TEXTUAL CONFLICTS on adjacent rows              observed, mild, fixed by
                                                       a better format
    4. SILENT-WRONG MERGE producing a false number     **not observed once**, in
                                                       any forum, issue tracker,
                                                       or Q&A site searched

**DESIGN.md's central technical achievement — turning 480 into 660 — addresses
the one item on this list that nobody has been recorded complaining about.**
That is not proof it does not happen; a silent failure by definition leaves no
complaint, and DESIGN.md §3(a) demonstrates the mechanism is real. But it means
the design's headline benefit cannot be sold on evidence of felt pain, while
items 1–3, which people *do* feel, are addressed either partially or not at all.

---

## 7. Method, gaps, and what would change the verdict

**Method.** Counts come from APIs, not impressions: authenticated GitHub REST
and search (5,000 req/hr), the Stack Exchange API with `filter=total`, the HN
Algolia API (`tags=story` and `tags=comment` reported separately), pypistats.org
(non-mirror series), api.npmjs.org, crates.io, formulae.brew.sh, cranlogs,
deps.dev, SEC EDGAR and UK Companies House. Regulatory text was read from
primary sources (eCFR versioner API, OJ L 335, bis.org, pcaobus.org; SR 11-7 via
an archived copy of the Fed PDF, since the live URLs 404 today).
**GitHub code-search `total_count` is approximate and capped** — treat those
figures as order-of-magnitude and as *ratios*, which is how they are used above.

**Gaps, stated plainly:**

1. **Reddit was unreachable** — r/excel, r/FPandA, r/dataengineering, r/git and
   Wall Street Oasis all returned HTTP 403 to both curl and WebFetch. The
   practitioner-forum quantification the brief asked for is **not answered**.
   This is the largest hole in the report; Reddit is where non-developer
   spreadsheet users actually complain.
2. **Session WebSearch budget was exhausted early** (200/200), so discovery
   relied on APIs and known URLs. Long-tail products with no GitHub presence and
   no HN footprint would be invisible to this method.
3. **No GxP/pharma practitioner evidence was gathered at all** — §5.1 is a legal
   reading, not a demand finding.
4. Unverified and excluded from the argument: the 2004 Big-Four spreadsheet
   whitepapers (not retrievable), Synkronizer's client claim, Quilt Data's raise,
   the `datadiff` GitHub Action's adoption.

**What would change the verdict.** This report would flip from "no demonstrated
demand" to "yes" on any of:

- Evidence of a **silently wrong merged number** actually reported by a
  practitioner — one credible case, anywhere. Zero were found; the design's
  central failure mode has no public witness.
- A **GxP or clinical-data team** already keeping tabular records in git for
  §11.10 audit-trail reasons.
- Reddit evidence (currently missing) that r/excel or r/FPandA discuss CSV merge
  correctness rather than "how do I version a binary file."
- A reversal in the hack ratio — `diff=xlsx` and `merge=csv` rising against
  `*.xlsx binary`. Today that ratio is **~230:1 the wrong way**.

**What would not change it:** more people upvoting "git for data" on HN. That
signal has been maximally positive since 2020 (1,444 points across three Dolt
front pages) while every shipped artifact in the category was archived, sold, or
scored one point.

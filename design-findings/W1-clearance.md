# W1 — Pre-bootstrap clearance: dependencies, licence, name and prior art

Research date: 2026-08-28. Gates repo creation (STATE-OF-PLAY items J and N).

All licences below were verified from a primary source — the LICENSE file in
the canonical repository and/or the package registry's own metadata — not from
a summary site. Where a claim in DESIGN.md is contradicted by the primary
source, the contradiction is stated in the text rather than footnoted.

Method note: `api.github.com` unauthenticated is rate-limited from this host;
authenticated `gh api` was used. `crates.io/api/v1`, `registry.npmjs.org` and
`pypi.org/pypi/<n>/json` were read directly.

---

## Summary — clearance verdicts at a glance

| Item | Licence (VERIFIED from primary source) | Verdict | Reason |
|---|---|---|---|
| **IronCalc** | **`MIT OR Apache-2.0`** — *not* Apache-2.0 as DESIGN.md says; both LICENSE files present, unchanged across all 15 releases since 2023-11-15 | **GO** on licence / **CAUTION** on fit | No CLA, no commercial tier, NLnet/NGI-Zero grant-funded → low rug-pull risk. But **f64 only, no decimal**, and **no grid-free named-binding API** — the whole surface is `(sheet,row,col)`. Grant ended 2026-05. |
| **formualizer** | `MIT OR Apache-2.0` | **CAUTION** | Best licence + only Rust-native alternative, but 1,925 total downloads and one author holds ~1,117/1,300 commits |
| **HyperFormula** | **`GPL-3.0-only`** (LICENSE.txt has no "or later"; npm agrees) | **NO-GO** | Incompatible with permissive distribution; the "free for OSS" exception **could not be verified from any primary source** |
| pycel / `formulas` / LibreOffice `sc` / Grist / zetajs | GPLv3 / EUPL-1.1 / MPL-2.0+LGPLv3 / Apache-2.0 / mixed | **NO-GO** | Copyleft, or inextricable, or wrong paradigm (Grist formulas are Python), or 100 MB+ |
| Univer (`@univerjs/engine-formula`) | `Apache-2.0`; MIT→Apache-2.0 on 2023-12-11 (benign) | **CAUTION** | Real separable engine, but open-core: `@univerjs-pro/*` ships with **no licence field**. TS/JS only — no Rust path |
| **Typst** | `Apache-2.0`, LICENSE + crates.io agree, no change since 2023-03-21 | **GO** | Active, embeddable as a library. Pre-1.0 (0.15.1) — vendor and pin, as §10 already says. No CLA, so Typst GmbH cannot unilaterally relicense |
| **tree-sitter** | MIT | **GO on licence / DO NOT ADOPT** | Its **heuristic** error recovery is incompatible with "exactly one specified outcome per input". Hand-written lexer + recursive descent instead |
| **CodeMirror 6 / ProseMirror** | MIT (registry + LICENSE agree) | **GO** | Archive claim **verified but reframed**: a deliberate move to self-hosted Forgejo (announced 2026-03-18 / 2026-04-02), not abandonment. **npm shipping never paused** — `@codemirror/view` 6.43.9 on 2026-08-16, `prosemirror-view` 1.42.3 on 2026-08-24. Bus factor 1, unchanged by the move |
| **Yjs** | MIT (GitHub's `"Other"` badge is a detector false positive) | **CAUTION** | v14 still pre-release; **pin v13** (`latest = 13.6.32`). Bus factor 1 (28 of last 30 commits) |
| y-codemirror.next | MIT | CAUTION | 0.3.6 (2026-08-18) after a **two-year gap** since 0.3.5. Smoke-test, don't assume |
| Loro / Automerge | MIT / MIT | GO | Rust-native, both pushed within the last 2 days |
| diamond-types (eg-walker) | ISC **declared in Cargo.toml, no LICENSE file in repo** | CAUTION | Fine to cite the algorithm; resolve upstream before depending on it |
| **D2 core** | **MPL-2.0** (`LICENSE.txt`, "Copyright 2022 Terrastruct Inc.") | **GO** (as a CLI) | Repo moved org `terrastruct/d2` → **`d2lang/d2`** (org created 2025-11-05); copyright still Terrastruct. Go only, no Rust bindings |
| **TALA** (D2's premium layout) | **Proprietary — confirmed** | **NO-GO** | Watermarks without a licence; **Enterprise tier auto-assigns diagram IP to the purchasing org, revocably.** D2's bundled Dagro + elk-go avoid it entirely |
| **Graphviz** | **EPL-2.0** — *not* EPL-1.0/CPL; `LICENSE` and `COPYING` on gitlab both say v2.0 | **GO** | Shell `dot`. All Rust bindings are thin or stale (`graphviz-rust` is DOT-text generation only, not FFI) |
| ELK / elkjs | EPL-2.0 / **`EPL-2.0 OR GPL-3.0-or-later`** | GO | Take the EPL-2.0 arm |
| Mermaid | MIT, LICENSE + npm agree, no CLA workflow | GO | Very active |
| Marp / Marpit | MIT across all three repos | CAUTION | Small single team; "Marpit as a library" means a JS runtime in the toolchain |
| Kroki | MIT | GO | Self-hosting is a first-class use case |
| **daff** | MIT — **the alleged README/LICENSE discrepancy did NOT reproduce**; GitHub, npm and PyPI all agree | **CAUTION → NO-GO as a dependency** | **Dormant**: last commit *and* last release both v1.4.2, **2025-05-04**. Bus factor 1. Haxe-transpiled, no Rust target. Fine as the *citation* §3(a) uses it for |
| **`git` binary (GPL-2.0-only)** | GPL-2.0-only | **GO — and say so in the repo** | Invoking git as a **subprocess** creates no copyleft obligation. Since "runs against stock git" is the defining claim, put the reasoning in `NOTICE` before anyone asks |
| `gix` / `git2` | `MIT OR Apache-2.0` (git2 links libgit2, GPL-2.0 **with linking exception**) | GO — but **not in the suite** | Using a Rust git library inside the conformance suite would silently substitute the thing under test |
| `unicode-normalization`, `ulid`, `uuid`, `blake3`, `sha2`, `rust_decimal`, `bigdecimal`, `proptest`, `insta`, `similar`, `imara-diff` | all `MIT`/`Apache-2.0`/`MIT OR Apache-2.0`/`CC0` | GO | See §1.8 |

**Name and extension: both current choices fail.** `gws` is taken on
crates.io, npm and PyPI, and `StreakyCobra/gws` (237★) is a **git-workspace
CLI** — the same semantic slot. `.tbl` matches **158,208 files** on GitHub and
already means roff tables, FreeSpace 2 mod data and StarCraft string tables.
Recommended: **`RowSpec`** (clean on all three registries, 0 GitHub name
matches) and **`.mdtbl`** (0 GitHub matches).

**Licence arrangement, recommended:** spec **CC-BY-4.0**; conformance
fixtures **CC0-1.0**; suite runner **MIT**; reference implementation and
validator **Apache-2.0 OR MIT**; **DCO, no CLA**. Reasoning in Part 2.

**Prior art the earlier passes missed, and that must be credited:** (1)
**Org-mode `#+TBLFM:` with its `!` column-name row** — nominal column
addressing in a plaintext table, shipping ~20 years, with a live markdown
port; (2) **daff/Coopy**, which has shipped id-column-keyed three-way tabular
merge **wired into `git merge`** since 2013 (`--id`, `daff git csv`); (3)
**ClassSheets (ASE 2005)** and **Object Spreadsheets (Onward! 2016)**. None
precludes the project — each *sharpens* it, because each made the opposite
choice on an axis the design has measurements for. Details in §3.5 and §3.6.

**The one thing found that is a real hole:** DESIGN.md requires decimal
arithmetic and adopts an engine that is IEEE-754-doubles-only, in the same
sentence in which it rejects CEL *for being IEEE-754-doubles-only*. That is a
normative spec question, not a dependency question, and it must be settled
before the first fixture is written. See Part 4, Blocker 1.

---

## PART 1 — DEPENDENCY LICENCE AND VIABILITY CLEARANCE

### 1.1 IronCalc — the proposed formula engine

**Verdict: GO on licence. CAUTION on fit. The design's stated requirement of
decimal arithmetic is NOT met, and DESIGN.md contains an internal
contradiction on exactly this point.**

#### Licence — verified, and BETTER than DESIGN.md claims

DESIGN.md §15 says "Wrap IronCalc (Apache-2.0)". That is wrong in the
project's favour. The actual licence is a **dual MIT OR Apache-2.0** grant.

- `base/Cargo.toml` (fetched from `ironcalc/IronCalc@main`):
  `license = "MIT OR Apache-2.0"`
- Repo root carries **two** files: `LICENSE-MIT` (1091 bytes) and
  `LICENSE-Apache-2.0` (10780 bytes).
- `LICENSE-MIT` opens:
  > MIT License
  >
  > Copyright (c) 2023 EqualTo GmbH, 2023 Nicolás Hatcher
- README §License:
  > Licensed under either of
  > * [MIT license](LICENSE-MIT)
  > * [Apache license, version 2.0](LICENSE-Apache-2.0)
  > at your option.

README and LICENSE files **agree**. This is the standard Rust dual-licence
and is maximally compatible with an Apache-2.0 or MIT downstream.

**One cosmetic discrepancy to be aware of:** the GitHub API reports
`license.spdx_id = "Apache-2.0"` for `ironcalc/IronCalc`, because GitHub's
detector picks a single file. Anyone reading the GitHub sidebar badge (or a
summary site derived from it) will conclude Apache-2.0-only. The registry and
the LICENSE files are the authority; the badge is not. This is very likely
where DESIGN.md's "Apache-2.0" came from.

#### Licence change history — NONE. Verified across every published version.

`crates.io/api/v1/crates/ironcalc`, all 15 versions, `license` field:

    0.8.3  2026-07-31  MIT OR Apache-2.0
    0.8.2  2026-07-29  MIT OR Apache-2.0
    0.8.1  2026-07-29  MIT OR Apache-2.0
    0.8.0  2026-07-29  MIT OR Apache-2.0
    0.7.1  2026-01-25  MIT OR Apache-2.0
    0.7.0  2026-01-21  MIT OR Apache-2.0
    0.6.0  2025-10-19  MIT OR Apache-2.0
    0.5.0  2025-02-28  MIT OR Apache-2.0
    0.3.0  2025-01-17  MIT OR Apache-2.0
    0.2.0  2024-09-16  MIT OR Apache-2.0
    0.1.3  2024-02-18  MIT OR Apache-2.0
    0.1.2  2024-02-17  MIT OR Apache-2.0
    0.1.1  2024-02-17  MIT OR Apache-2.0
    0.1.0  2024-02-09  MIT OR Apache-2.0
    0.0.1  2023-11-15  MIT OR Apache-2.0

Same for `ironcalc_base` (0.8.3, 62,569 downloads). Dual-licensed from the
first publish on 2023-11-15. No rug-pull, no relicensing event, no yanks.

#### Funding and commercial model — grant-funded, NOT the Handsontable pattern

This is the material question and the answer is reassuring.

- The MIT copyright names **EqualTo GmbH** (2023). EqualTo was the commercial
  spreadsheet-API company the engine came out of.
- `ironcalc.com` footer now reads **"© 2026 IronCalc GmbH"** — the entity
  was renamed/reconstituted around the open-source project.
- `ironcalc.com` states: *"Backed by the European Commission and the NLnet
  Foundation"* via the *"Horizon Europe programme"* and the *"NGI0 Core
  Fund"*, and *"MIT/Apache 2.0 licensed"*.
- `nlnet.nl/project/IronCalc/` confirms: **Fund: NGI Zero Core**,
  **Period: 2024-02 — 2026-05**, described as an *"Embeddable spreadsheet
  engine written in Rust"*.

**The rug-pull risk profile is structurally different from Handsontable's.**
Handsontable was VC-shaped: a permissive core, a commercial upsell, and the
licence as the lever. IronCalc is grant-funded by NLnet/NGI Zero, whose
funding conditions require open-source licensing, and there is **no dual
"community/commercial" split, no CLA, and no copyright-assignment
mechanism**. `CONTRIBUTING.md` was read in full: it is an ordinary
fork-branch-PR document with **no CLA and no DCO requirement**. Without a
CLA, IronCalc GmbH *cannot* unilaterally relicense contributed code. That is
the single strongest anti-rug-pull property a project can have, and IronCalc
has it by omission rather than by policy.

**The real viability risk is the opposite one: the grant period ENDED
2026-05.** Post-grant runway is unstated and there is no visible revenue
model on the site (no paid tier, no hosted product pricing page found).
Activity has not slowed — v0.8.0/0.8.2/0.8.3 all shipped after the grant
ended, and there are commits from two authors dated 2026-08-27/28 — but a
grant that has expired with no announced successor is a 12-month watch item,
not a 5-year assurance.

#### Maintenance, cadence, bus factor

- Repo `ironcalc/IronCalc`, `archived: false`, `pushed_at: 2026-08-28`
  (today), 4,125 stars, 178 forks, 255 open issues.
- Releases: v0.2.0 (2024-11-15) → v0.3.0/0.3.1 (2025-01) → v0.5.0/0.5.1
  (2025-02) → v0.6.0 (2025-10) → v0.7.0/0.7.1 (2026-01) →
  v0.8.0/0.8.2 (2026-07-29) → v0.8.3 (2026-08-03). Roughly **quarterly, with
  gaps of up to eight months** (2025-02 → 2025-10).
- Contributors: `nhatcher` 939, `dg-ac` 635, `elsaminsut` 186, then a long
  tail (33, 22, 19, 16, 11, 10, 9, 8, 7...). **Bus factor ~2**, effectively a
  small funded team rather than one hobbyist. Better than Yjs, daff, or
  CodeMirror on this axis.

#### Embeddability as a library — YES, and the engine is cleanly separated

The workspace `Cargo.toml` members are `base`, `xlsx`, `bindings/wasm`,
`bindings/python`, `bindings/nodejs`. **`webapp` is not a workspace member**
— the UI is excluded (`exclude` also lists `webapp/app.ironcalc.com/server`).
So there is a genuine calculation-engine crate, `ironcalc_base`, with no UI
in its dependency graph. Its full dependency list is small and clean:

    serde, ryu, chrono, bitcode, csv, statrs
    (wasm32) js-sys, wasm-bindgen, regex-lite
    (native) rand, chrono-tz, regex

Bindings exist for WASM, Python and Node. Rust-native embedding is the
primary path.

#### API stability — this is the weak point, and IronCalc says so itself

`base/src/lib.rs` module documentation states, verbatim:

> until version 1.0.0 you should use the git dependencies as stated

i.e. **the crate's own docs tell you not to depend on the crates.io release.**
The README's example likewise uses `ironcalc = { git = "...", version = "0.8" }`.
docs.ironcalc.com states: *"IronCalc is in its infancy, although we aim at
supporting many of common spreadsheet features you might find some important
features missing in your normal workflow."* ironcalc.com says it is *"still
evolving toward version 1.0"*, with Charts and real-time collaboration named
as missing.

Mitigation is the same one DESIGN.md §10 already prescribes for Typst:
**vendor and pin**. Given the conformance suite is the deliverable, a pinned
engine is not merely acceptable — a *moving* engine would make conformance
results irreproducible, which is a spec-integrity problem, not a convenience
one.

#### Function coverage — ~495 functions

`base/src/functions/mod.rs` is 2,869 lines; its `pub enum Function` has
**495 variants**, with 1,638 `Function::` references in the dispatch. The
tree carries dedicated modules for `financial`, `statistical`,
`math_and_trigonometry`, `text`, `logical`, `date_and_time`, `lookup_and_reference`,
`information`, `engineering`, `database`, plus `xlookup.rs`,
`spill_functions.rs` and `subtotal.rs`.

Against DESIGN.md's own evidence (7% of spreadsheets contain any formula;
76% of Enron formula usage is fifteen functions) this is **massively more
than the project needs**. That inverts the usual conclusion: coverage is not
the reason to take IronCalc, and coverage would not be the reason to drop it.

#### TWO REAL PROBLEMS — neither is a licence problem

**(a) IronCalc is IEEE-754 doubles only. DESIGN.md §13 contradicts itself.**

Verified in source:

- `base/src/calc_result.rs`: `pub(crate) enum CalcResult { String(String), Number(f64), Boolean(bool), ... }`
- `base/src/cell.rs`: `Number(f64)`, `impl From<f64> for CellValue`,
  `pub fn new_number(v: f64, s: i32) -> Cell`

There is no `rust_decimal`, no `bigdecimal`, no fixed-point path anywhere in
`ironcalc_base`'s dependency list.

DESIGN.md §13 reads:

> Take CEL's guarantees but not CEL, which is IEEE-754 doubles only and the
> flagship artifact is a financial table: named-column syntax, IronCalc as
> the engine, evaluation constrained to CEL's contract, **decimal arithmetic**,
> a static cost estimate plus a runtime budget.

CEL is rejected in that sentence *for being f64-only*, and IronCalc is
adopted in the same sentence — but IronCalc is also f64-only. The
requirement "decimal arithmetic" is asserted and then delegated to an engine
that cannot provide it. This must be resolved before the spec is written,
because it is a **normative** question: `0.1 + 0.2` in a conformance test has
exactly one right answer and the spec has to say which.

Three ways out, in order of preference:

1. **Specify binary64 explicitly and be honest about it**, as Excel,
   LibreOffice, Google Sheets, JSON and CEL all effectively do. Add a
   normative rounding/display rule so the *rendered* value is stable, and put
   the float semantics in the "what is deliberately left open / deliberately
   pinned" section §17 already calls for. Cost: a financial table can still
   surprise. Benefit: IronCalc drops straight in, and the conformance suite's
   expected values are computable by any implementation with an IEEE-754
   double.
2. **Specify decimal and do not use IronCalc's evaluator** — use only its
   *parser* (see below), and evaluate the 15–40 functions that actually
   matter over `rust_decimal` (MIT, 1.42.1, 136M downloads) yourself. This is
   the honest reading of "76% of usage is fifteen functions": the reason to
   wrap an engine was coverage, and coverage is not needed.
3. Specify decimal *and* wrap IronCalc — requires patching or forking the
   engine's number type. Not recommended; it makes the pinned engine a
   maintained fork on day one.

**(b) IronCalc has no grid-free, named-binding evaluation API.** The entire
public surface is coordinate-addressed:

    Model::set_user_input(sheet: u32, row: i32, column: i32, value: String)
    Model::get_cell_value_by_index(sheet: u32, row: i32, column: i32)
    Model::get_cell_value_by_ref(cell_ref: &str)   // "Sheet1!A1"
    Model::parse_reference(s: &str) -> Option<CellReferenceIndex>
    Model::evaluate(&mut self)

And in `base/src/lib.rs`, `mod functions;` is **private** — the function
library is reachable *only* through a `Model`, i.e. only through a grid. What
*is* public is `pub mod expressions` (`lexer/`, `parser/`, `token.rs`,
`types.rs`) and `pub mod calc_result`, `cell`, `types`, `formatter`,
`number_format`, `language`, `locale`.

Consequence for this design: `.tbl`'s whole premise is **I2 — no coordinate
syntax at all**. Wrapping IronCalc therefore means building and testing a
nominal→A1→nominal translation layer, materialising a hidden synthetic grid
per table, and mapping results back to column names. That layer is exactly
the kind of coordinate machinery the format exists to abolish, and every
correctness guarantee about *evaluated values* — the thing the conformance
suite is supposed to assert on — flows through code the project writes
itself, not through the vendored engine.

This does not disqualify IronCalc. It reprices it. The realistic best use is
**IronCalc's public `expressions` parser + its function semantics as a
reference oracle**, with the project owning evaluation — which is also what
option (2) above requires. Wrapping the whole `Model` is the option that
looks cheap and is not.

---

### 1.2 Formula engine alternatives, if IronCalc fails clearance

It does not fail clearance on licence, so this is a contingency list. It is
also the list that matters for option (2) above, where the project owns
evaluation and needs only a parser or a semantics oracle.

| Engine | Licence (verified) | Source of truth | Rust-embeddable | Maintained 2026 | Verdict |
|---|---|---|---|---|---|
| **formualizer** (`psu3d0/formualizer`) | `MIT OR Apache-2.0` | crates.io per-version + `LICENSE-MIT` and `LICENSE-APACHE` both present | **Yes, native Rust**, plus Python and WASM bindings | Yes — crate first published 2026-01-30, 27 versions, 0.8.0→0.8.4 inside one week in Aug 2026, last push 2026-08-25 | **CAUTION** — best licence + best embeddability, but only **1,925 total downloads**, 171 stars, and one author holds ~1,117 of ~1,300 commits. Bus factor 1. |
| **formulajs/formulajs** (`@formulajs/formulajs`) | MIT (LICENSE text is unambiguous MIT: Sutoiku 2014 + bundled MIT SheetJS Bessel + MIT jStat) | LICENSE file; npm `license: "MIT"` on the scoped package | No — JS only | Yes, last push 2026-07-28 | CAUTION — function library only, no parser or dependency graph |
| **fast-formula-parser** | MIT | LICENSE file + npm | No — JS only | **Dormant** — last substantive commit 2024-06-07 | CAUTION |
| **xlcalculator** | MIT per PyPI classifier; GitHub detector says `NOASSERTION` | PyPI classifier (discrepancy flagged) | No — Python | Active, pushed 2026-04-13 | CAUTION |
| **HyperFormula** | **GPL-3.0-only** | LICENSE.txt + npm `license: "GPL-3.0-only"` | No | Very active | **NO-GO** |
| **pycel** | GPLv3 per PyPI classifier | PyPI | No | Active | **NO-GO** |
| **`formulas`** (vinci1it2000) | **EUPL-1.1(+)** | PyPI classifier + GitHub | No | Active | **NO-GO** for a permissive downstream |
| **LibreOffice `sc/`** | MPL-2.0 primary, LGPLv3+ secondary | libreoffice.org/about-us/licenses (GitHub mirror's `GPL-3.0` tag is a detector artifact) | No | Very active | **NO-GO on effort** — `sc/` is wired into UNO/VCL/gbuild; nobody has extracted it standalone |
| **Grist (`grist-core`)** | Apache-2.0 | GitHub license field | No | Very active | **NO-GO on paradigm** — formulas are Python, not Excel syntax |
| **zetajs / ZetaOffice (LO-in-WASM)** | Bindings MIT; core still MPL-2.0/LGPLv3+ | repo | No | Active | **NO-GO** — ships the whole office suite (100 MB+) |
| **koala2** | — | — | — | **Dead / unlocatable** | NO-GO |
| **Univer** (`@univerjs/engine-formula`) — *found during this pass, not in the brief* | **Apache-2.0** (npm per-version + repo `LICENSE`) | npm; `dream-num/univer` LICENSE file | No — TS/JS | Very active: 14,235★, pushed 2026-08-28; `@univerjs/engine-formula` 0.25.1 (2026-06-27) | **CAUTION** — see below |

#### Univer — worth knowing about, and a textbook open-core risk shape

`@univerjs/engine-formula` describes itself as *"Formula parsing, dependency
management, and calculation engine for Univer"* — i.e. a **genuinely separable
formula engine**, Apache-2.0, actively maintained, and the successor to
Luckysheet (16,647★, now redirected to Univer).

Two things found by walking the registry:

1. **There was a licence change, and it was benign.** `@univerjs/engine-formula`
   published `0.1.0-alpha.1` on **2023-12-05 under MIT**, then
   `0.1.0-alpha.2` on **2023-12-11 under Apache-2.0**, and Apache-2.0 ever
   since. A permissive→permissive move six days into the first alpha. Not a
   rug-pull.
2. **But the project is open-core, and the structure is visible in the
   registry.** `@univerjs/core`, `@univerjs/sheets-formula` and
   `@univerjs/engine-formula` all declare `Apache-2.0`. **`@univerjs-pro/collaboration`
   declares no licence field at all** — a separate `@univerjs-pro` scope
   holding the commercial line.

That is the same *shape* as Handsontable's business — a permissive core with
a commercial arm — but implemented the honest way: the paid features live in
a distinct package scope rather than being achieved by relicensing the core.
It is not a reason to avoid Univer; it is a reason to watch which scope a
given package comes from, and to note that the incentive to move the line
exists. **For this project it is moot anyway: TS/JS only, no Rust path.**
Listed for completeness and because it is the largest actively-developed
Apache-2.0 formula engine in existence.

#### The HyperFormula finding, stated precisely

`LICENSE.txt` in `handsontable/hyperformula`, quoted:

> This software is dual-licensed, giving you the option to use it under either
> a proprietary license or the GNU General Public License version 3
> (GPLv3)... You are permitted to run, modify, and distribute this software
> under the terms of the GPLv3, as published by the Free Software Foundation.

**No "or later" language anywhere.** npm and `package.json` both declare
`GPL-3.0-only`. GitHub's detector reports `NOASSERTION` (a third
detector-vs-file discrepancy). The commonly-cited "free for open source"
exception — an allowlist of accepted OSS licences — **could not be verified
from any primary source.** The reachable licensing and pricing pages present
exactly two paths: run under GPLv3, or buy a commercial key. **Treat the
allowlist claim as unconfirmed.** For an Apache-2.0/MIT project HyperFormula
is disqualified either way: GPL-3.0-only cannot be distributed inside an
Apache-2.0 work.

#### The Handsontable rug-pull, dated as precisely as the record allows

The full `registry.npmjs.org/handsontable` version timeline was walked, and
the flip is pinned to a **single release boundary**:

    ...
    6.2.1   2018-12-12   license: "MIT"
    6.2.2   2018-12-19   license: "MIT"          <- LAST MIT RELEASE
    7.0.0   2019-03-06   license: "SEE LICENSE IN LICENSE.txt"   <- THE FLIP
    7.0.1   2019-04-08   license: "SEE LICENSE IN LICENSE.txt"
    ...

Every release from 0.23.0 (2016-03-04) through 6.2.2 (2018-12-19) declares
`MIT`. Every release from 7.0.0 (2019-03-06) onward declares
`SEE LICENSE IN LICENSE.txt`, and the LICENSE.txt in the v7.0.0 tarball
already carries the HANDSONCODE proprietary/non-commercial dual licence.

**The rug-pull is therefore dated to the v6.2.2 → v7.0.0 major bump, between
2018-12-19 and 2019-03-06.** Note the shape of it: it rode a major version
number, which is the version-number convention people use to signal *API*
breakage, and it gave existing users no MIT successor line at all.

**`formula.js` was not affected.** It always shipped its own separate MIT
LICENSE and was never under Handsontable's proprietary terms. The original
`handsontable/formula.js` repo is simply **archived** (last push 2021-07-15);
the live line is the community fork `formulajs/formulajs`. The bare
`formulajs` npm package is abandoned at 1.0.8 (2022-06-18, `license: null`).

This is the pattern the brief was right to worry about — and it is worth
naming what makes IronCalc different: Handsontable's licence was the
company's revenue lever, whereas IronCalc has **no commercial tier and no
CLA**, so it has no lever to pull.

---

### 1.3 Typst — rendering

**Verdict: GO on licence. CAUTION on pre-1.0 API churn (as DESIGN.md §10
already says).**

- Licence **Apache-2.0**, verified from `LICENSE` at repo root and from
  crates.io per-version metadata for the `typst` crate (v0.15.1). No
  divergence found across `typst`, `typst-cli`, `typst-pdf`. No licence
  change since the crate was created 2023-03-21.
- Maintenance: repo pushed 2026-08-28. Releases roughly every two months
  through the 0.12→0.15 line; latest **v0.15.1, 2026-07-17**.
- **1.0 has not shipped.** Still 0.15.x. DESIGN.md's prescription — "vendor
  themes and pin the compiler" — is the right one and remains necessary.
- Embeddable: yes, `typst` is the compiler *library*; `typst-cli`,
  `typst-pdf`, `typst-svg`, `typst-render` are separate crates. This is the
  same surface typst.app itself uses. API churns on every 0.x bump.
- **Commercial relationship, assessed:** Typst GmbH runs typst.app on a
  freemium model, but the paid tiers gate **collaboration and org features
  only** (comments, private packages, git sync, LDAP) — not compilation or
  rendering. `CONTRIBUTING.md` states plainly:

  > Typst is also the product of a startup... proposals may have direct
  > impact on our viability as a company, in which case we carefully consider
  > them from the business perspective

  That is an acknowledged conflict of interest, disclosed. **No CLA and no
  copyright-assignment mechanism was found** — so, as with IronCalc, Typst
  GmbH cannot unilaterally relicense contributed code. Residual risk is
  business-priority drift, not a licence bait-and-switch.

---

### 1.4 tree-sitter — and the answer is: DON'T

**Verdict: GO on licence (MIT, `Copyright 2018 Max Brunsfeld`, very active,
v0.26.13 on 2026-08-23). NOT NEEDED — recommend deferring it entirely.**

The design question matters more than the licence, and the answer is a clear
no for the core:

1. **The incremental-reparse value proposition doesn't apply.** tree-sitter
   earns its keep on large, frequently-edited files where edits land
   unpredictably. `.tbl` is line-oriented and a full reparse of a table is
   cheap; the markdown reader is *boundary-parsing by construction* — it
   finds block boundaries and never re-emits content (DESIGN.md §7), which is
   a linear scan, not tree-sitter's problem.
2. **Its error recovery is in direct tension with the spec's hardest
   requirement.** §17 demands *fully specified error recovery — one outcome
   per input, errors signalled separately from handled*, on the explicit
   HTML5 precedent. tree-sitter's recovery is a **heuristic** GLR-style
   repair tuned to give editors a usably-shaped tree for highlighting. It is
   not a documented, reproducible contract, and it has changed across
   versions. A conformance suite that asserts one outcome per input cannot
   rest on a recovery strategy that is explicitly not specified.
3. **Grammar-as-spec is illusory here.** A `grammar.js` compiles to a GLR
   table that is not readable as a specification. §17's own ranking puts the
   formal grammar at position 6 and *for lexical structure only* — a
   hand-written lexer states that more directly.
4. **Cost:** a C runtime dependency, a WASM/native build matrix, and a
   grammar DSL — for a format small enough that recursive descent is
   plausibly less total code with full control over error productions.

Reserve tree-sitter for a possible future editor mode. It is not earned by
the spec, suite, reference implementation or validator.

---

### 1.5 CodeMirror 6 / ProseMirror — the April 2026 move, VERIFIED

**Verdict: GO, with the prior finding materially reframed. This is a
deliberate self-hosting migration, not abandonment, and shipping never
stopped.**

The archive claim is true:

| Repo | `archived` | `pushed_at` |
|---|---|---|
| `codemirror/dev` | true | 2026-04-15 |
| `codemirror/view` | true | 2026-04-15 |
| `codemirror/state` | true | 2026-04-15 |
| `ProseMirror/prosemirror` | true | 2026-04-01 |
| `ProseMirror/prosemirror-model` | true | 2026-04-01 |
| `ProseMirror/prosemirror-view` | true | 2026-04-01 |

The announcements, with dates and reasons in the author's own words:

- CodeMirror, Marijn Haverbeke, **2026-04-02**,
  `discuss.codemirror.net/t/codemirrors-migration-to-forgejo/9706`:
  > I feel rather strongly about reducing my dependence on GitHub and big
  > "free as in you have no recourse" platforms in general.
- ProseMirror, **2026-03-18**,
  `discuss.prosemirror.net/t/prosemirrors-migration-to-forgejo/8974`:
  > Having a big part of my daily workflow tied up to a platform that
  > continues to get slower and buggier, and could ban my account or change
  > their terms on a whim, is something I'm motivated to avoid.

The GitHub repos were **archived rather than deleted, specifically to
preserve issue-number cross-links.**

**Where development happens now:** `code.haverbeke.berlin` — live (HTTP 200,
2026-08-28), running **Forgejo 16.0.3**, self-hosted behind nginx, with an
issue tracker, PRs, and GitHub OAuth2 login for convenience. The
`package.json` `repository` fields for `@codemirror/view` and
`prosemirror-view` now point at `code.haverbeke.berlin/...`, confirming the
npm packages track the new source.

**Licences unchanged, files and registry agree:**

| Package | npm `license` | LICENSE file |
|---|---|---|
| `@codemirror/state`, `/view`, `/commands` | MIT | MIT (Marijn Haverbeke "and others") |
| `prosemirror-model`, `prosemirror-view` | MIT | MIT |

**The risk question — release cadence since the move — is answered
positively.** Publishing never paused:

    @codemirror/view      24 releases in 2026, latest 6.43.9  (2026-08-16)
    @codemirror/state     6.7.1                               (2026-07-05)
    @codemirror/commands  6.11.0                              (2026-08-16)
    prosemirror-model     1.25.11                             (2026-07-11)
    prosemirror-view      1.42.3                              (2026-08-24)

Cadence is roughly weekly-to-biweekly, unchanged either side of the April
archive. The forums show daily traffic through 2026-08-26, including new
language packages. One Forgejo outage was reported (2026-07-03) and resolved.

**Actual risk to a dependant:** `npm install` works normally today; filing a
bug now needs a Forgejo account (GitHub OAuth accepted, low friction);
patch cadence shows no degraded responsiveness. The real risk is the
**pre-existing bus factor of 1** — one person, now also running his own
forge. Because everything is plain MIT TypeScript with no CLA-gated
contribution funnel, a fork of the last good commit is straightforward.
That risk existed before the move and was not increased by it.

**For this project specifically:** none of this is on the critical path.
CodeMirror is an editor concern, and §11 of DESIGN.md has already ruled that
there is **no UI API** and that frontends are Tier 3, "first-party only,
explicitly unstable." Keep it there.

---

### 1.6 Yjs and y-codemirror.next

**Verdict: GO on licence. CAUTION on v14 timing and bus factor.**

- **Yjs**: LICENSE file is MIT (Kevin Jahns + RWTH Aachen Chair of CS5,
  2023); npm `license: "MIT"`. **The GitHub API license field reports
  `"Other"`** — a detector false positive on the two-party copyright header,
  and the fourth detector-vs-file discrepancy in this survey. Repo not
  archived, last push 2026-08-06.
- **v13/v14 situation:** npm dist-tags are `latest = 13.6.32`,
  `next = 14.0.0-8`, `beta = 14.0.0-16`; git tags run further ahead
  (`v14.0.0-rc.24`). **v14 is still pre-release and is not the default
  install; v13 is the maintained production line** and is still getting point
  releases. No announced GA date found. Anyone depending on Yjs today should
  pin v13 and treat v14 as a future migration, not an imminent one.
- **Bus factor:** last 30 commits — Kevin Jahns 28, two others 1 each.
  Effectively one person, same as CodeMirror. Funding is GitHub Sponsors plus
  a support-contract model; README offers *"professional support directly
  from the author... weekly video calls."* No dual-licence or commercial fork
  of yjs core was found. `y-sweet` (jamsocket) is a separate MIT-family
  project.
- **y-codemirror.next:** MIT, not archived, last push 2026-08-18, release
  0.3.6 (2026-08-18) — but the previous release was 0.3.5 in **June 2024**, a
  two-year gap. It still tracks current CodeMirror, but the cadence is
  reactive rather than routine. Smoke-test compatibility rather than assume
  it. Not a licence concern.

**Alternatives, all licence-verified:**

| Project | Licence | Rust-native | 2026 status |
|---|---|---|---|
| **Loro** | MIT | Yes | Active — pushed 2026-08-27, `loro-crdt` 1.15.0 |
| **Automerge** | MIT | Yes | Active — pushed 2026-08-28, `@automerge/automerge` 3.4.1 |
| **diamond-types** (eg-walker) | ISC *declared in Cargo.toml* — **no LICENSE file in the repo** | Yes | Active, pushed 2026-07-31 |
| **collabs** | Apache-2.0 | No (TS) | **Stale** — last push 2025-03-25 |

`diamond-types` is the origin of the eg-walker algorithm DESIGN.md §8 leans
on, and it has a **licensing hygiene gap: a declared ISC licence with no
LICENSE file present**. If the design ever depends on it rather than merely
citing the paper, that must be resolved with upstream first. Citing the
algorithm carries no such obligation.

---

### 1.7 Diagram, layout and diff stack

| Dep | Licence (verified) | Changed? | 2026 activity | Rust-embeddable | Field-of-use | Verdict |
|---|---|---|---|---|---|---|
| **D2 core** | **MPL-2.0** — `LICENSE.txt`: *"Copyright 2022 Terrastruct Inc. / Mozilla Public License Version 2.0"* | No licence change, but **the repo moved org**: `terrastruct/d2` now 301-redirects to **`d2lang/d2`** (org created 2025-11-05). Copyright still held by Terrastruct Inc. — governance moved, IP did not | Active; v0.8.2 released 2026-08-28 | **No — Go only.** No Rust bindings/FFI. Options are shelling the `d2` CLI or a WASM build (`d2js`) | None on the core | **GO** as a delegated CLI, per §10's "delegate, never implement" |
| **TALA** (D2's premium layout engine) | **Proprietary — CONFIRMED.** `terrastruct/tala` README: *"TALA is closed-source... paid layout engine, which requires a license for any commercial use... free to evaluate, but without a license, will render with a watermark."* | n/a | n/a | No | **Yes, and it is sharp.** Two tiers: Personal (IP stays with creator) and **Enterprise, where diagram IP is auto-assigned to the purchasing org and is revocable by Terrastruct** | **NO-GO** — never make it a dependency or a default |
| D2's **free** layout engines | **Dagro** (bundled native Go port of Dagre) and **elk-go** (`github.com/d2lang/elk-go v0.2.0`, native Go port of ELK) — both bundled, no JVM | — | Current | Go | None | GO — these are what the project should use; they make TALA entirely avoidable |
| **Graphviz** | **EPL-2.0.** DESIGN.md-era assumptions of EPL-1.0/CPL are **out of date** — `gitlab.com/graphviz/graphviz/-/raw/main/LICENSE` and `/COPYING` are both Eclipse Public License **v2.0** | Yes, at some point moved 1.0→2.0 | Very active: v16.0.0 (2026-08-14), v15.1.1 (2026-08-05), v15.1.0 (2026-06-18) | C FFI (`libgvc`/`libcgraph`), decades-stable ABI. **Rust bindings are all thin or stale**: `graphviz-rust` 0.9.8 (2026-05) is *DOT-text generation only, not FFI*; `graphviz-ffi` last published 2021; `graphviz-rs` last 2023; `vizoxide` 1.0.5 (2025-03) is the most current real wrapper | None | **GO** — but shell the `dot` binary; do not adopt a Rust binding |
| **ELK** | **EPL-2.0** — `raw.githubusercontent.com/eclipse-elk/elk/master/LICENSE.md`. Canonical org is now `eclipse-elk/elk` | No | Active | No — Java core | None | GO (via D2's `elk-go`) |
| **elkjs** | **`EPL-2.0 OR GPL-3.0-or-later`** (npm metadata) — standard Eclipse dual pattern | No | 0.12.0, 2026-07-17 | No — JS | None | GO — take the EPL-2.0 arm |
| **Mermaid** | **MIT**, `LICENSE` (Copyright 2014–2022 Knut Sveidqvist) and npm agree. **No CLA workflow found** | No | Very active; 11.17.2 on 2026-08-25, pushed 2026-08-28 | No — JS | None | GO |
| **Marp / Marpit** | **MIT** across `marp-team/marpit`, `marp-core`, `marp-cli`; LICENSE text verified for Marpit | No | Active — Marpit 2026-08-03, marp-core 2026-08-09, marp-cli 2026-07-20; `@marp-team/marpit` 3.2.2 (2026-07-04) | No — JS | None | **CAUTION** — small single team; and §10's "Marpit as a library" means a JS runtime in the toolchain |
| **Kroki** | **MIT** — `LICENSE` (Copyright 2020-present Kroki) + GitHub API | No | Active; v0.32.1 (2026-08-12), pushed 2026-08-23 | n/a — HTTP service, self-hostable by design | None | GO |
| **daff** | **MIT — and the alleged discrepancy did NOT reproduce.** GitHub's detected licence, npm `license: "MIT"` and the PyPI classifier `License :: OSI Approved :: MIT License` all independently agree | No | **DORMANT** — last commit and last release both **v1.4.2, 2025-05-04** (~16 months stale). **Bus factor 1** (Paul Fitzpatrick, sole maintainer) | **No.** Haxe transpiled to JS/Java/PHP/Python/C++; embedding means consuming generated code. No Rust target exists | None | **CAUTION → effectively NO-GO as a dependency.** Fine as the *citation* DESIGN.md §3(a) uses it for |

**On daff specifically:** DESIGN.md uses daff as *evidence* — "daff merged the
same file's rows perfectly and produced the identical wrong answer" — which is
a citation, not a dependency, and needs no clearance. If daff were ever
promoted to a real dependency, it would be the weakest link in the estate:
dormant, bus factor 1, and no Rust path.

---

### 1.8 Items DESIGN.md leans on that were not in the brief

| Item | Licence | Note |
|---|---|---|
| **`git` itself (the binary)** | GPL-2.0-only | **This is fine and worth stating explicitly in the repo.** The conformance suite invokes stock `git` as a **subprocess**. GPL-2.0 obligations attach to derivative works and linking, not to running a program and reading its output. A permissively-licensed conformance suite that shells out to git creates no copyleft obligation. Since "runs against a stock git binary" is the project's defining claim, put this reasoning in a `NOTICE` or the spec's licensing section pre-emptively. |
| **`git2` crate** | `MIT OR Apache-2.0` (v0.21.0, 2026-05-18) | Links **libgit2**, which is GPL-2.0 **with a linking exception**. Usable, but the exception has to be understood. |
| **`gix` crate** | `MIT OR Apache-2.0` (v0.87.1, 2026-08-24, 44M downloads) | Pure Rust, no libgit2, no exception to reason about. **Prefer `gix` over `git2` if a git library is ever needed** — but note that for the conformance suite, *neither* should be used: the suite's entire value is that it runs against the **real `git` binary**, not a reimplementation. Using a Rust git library in the suite would silently substitute the thing under test. |
| `unicode-normalization` | `MIT OR Apache-2.0`, v0.1.25 | Required by C4 (NFC-only identifiers). GO |
| `ulid` | MIT, v3.0.0 | The `id: 01J8ZQ4K7X` in §7 is a ULID. GO |
| `uuid` | `Apache-2.0 OR MIT`, v1.26.0 | GO |
| `blake3` | `CC0-1.0 OR Apache-2.0 OR Apache-2.0 WITH LLVM-exception` | For the content-addressed derivation cache. GO |
| `sha2` | `MIT OR Apache-2.0`, v0.11.0 | GO |
| `rust_decimal` | **MIT**, v1.42.1, 136M downloads | The route to decimal arithmetic if option (2) in §1.1 is taken. GO |
| `bigdecimal` | `MIT/Apache-2.0`, v0.4.10 | Alternative. GO |
| `proptest` | `MIT OR Apache-2.0`, v1.11.0 | For I1's property tests (`render(parse(b)) == b`). GO |
| `insta`, `similar`, `imara-diff` | Apache-2.0 | Snapshot testing and diffing. GO — Apache-2.0-only, so a GPL-2.0-only downstream would have a problem, but this project will not be one. |
| **pandoc** | GPL-2.0-or-later | Used in DESIGN.md only as a *measurement oracle* (rendering a conflicted file). Fine as a dev-time subprocess; **must never become a runtime dependency of a permissively-licensed tool that links it**. |
| **LibreOffice** | MPL-2.0 / LGPLv3+ | Used only as a test oracle for the 480-vs-660 result. Subprocess, dev-time. Fine. |
| **jujutsu** | Apache-2.0 | §5 takes *ideas* (`Merge<T>`, `change-id`), explicitly not the dependency. No obligation from ideas. |

---

## PART 2 — LICENCE CHOICE FOR THIS PROJECT

### 2.1 What comparable projects actually did

Verified from LICENSE files, not summaries.

| Project | Spec text | Conformance suite | Reference impl | CLA/DCO |
|---|---|---|---|---|
| **CommonMark** | **CC-BY-SA 4.0** | examples embedded in the CC-BY-SA spec; **runner BSD-2-Clause** | **cmark: BSD-2-Clause** with MIT carve-outs | **Neither** |
| **WHATWG HTML** | **CC-BY-4.0**, with a BSD-3-Clause carve-out for code portions | **web-platform-tests: BSD-3-Clause** | n/a (browsers) | **Real CLA** (Contributor and Workstream Participant Agreement) |
| **JSON Schema** | **BSD-3-Clause + AFL-3.0** (the IETF I-D pairing) | **MIT** (`JSON-Schema-Test-Suite`) | various | Neither |
| **TOML** | **MIT** (prose under a code licence) | **MIT** (`toml-test`) | various | Neither |
| **YAML** | *"may be freely copied, provided it is not modified"* — verbatim-only, no derivative right | **MIT** (`yaml-test-suite`) | various | Neither |
| **djot** | **MIT**, spec and impl together | **none exists** | MIT | Neither |
| **Frictionless (`schemas`)** | **The Unlicense** | — | — | Neither |
| **JSON Canvas** | **MIT**, whole repo | — | — | Neither |
| **SQLite** | Public domain | **TH3 is PROPRIETARY and sold** | Public domain | Affidavits; **refuses outside contributions** |
| **Unicode** | Unicode License v3 (one permissive licence covering data + software) | same terms; `NormalizationTest.txt` has no separate licence | — | — |
| **IETF RFCs** | **No derivative works** outside the IETF process | — | code components carved out under **Revised BSD** | — |

Exact text, CommonMark's `LICENSE` (verified by direct fetch):

> The CommonMark spec (spec.txt) and DTD (CommonMark.dtd) are
> Copyright (C) 2014-16 John MacFarlane
> Released under the Creative Commons CC-BY-SA 4.0 license
>
> ---
>
> The test software in test/ and the programs in tools/ are
> Copyright (c) 2014, John MacFarlane [BSD-2-Clause text follows]

Exact text, `JSON-Schema-Test-Suite/LICENSE` (verified):

> Copyright (c) 2012 Julian Berman
> Permission is hereby granted, free of charge... [MIT]

### 2.2 The finding that changes the recommendation

**CommonMark's arrangement contains a trap this project must not copy.**

CommonMark's 655 conformance examples are **embedded inside `spec.txt`**, and
`spec.txt` is **CC-BY-SA 4.0 — a share-alike licence**. Only the *runner*
(`test/`, `tools/`) is BSD-2-Clause. So an implementer who vendors the
examples into their own fixtures is arguably vendoring CC-BY-SA content into
their repository. In practice nobody has litigated it and ~45 implementations
exist regardless — but the ambiguity is real, and it is exactly the friction
that deters a cautious proprietary implementer, which is the population you
most need and least control.

This project is **more exposed than CommonMark, not less**, because §17
requires the suite to assert on **parsed entity maps, resolved addresses and
evaluated values** — a far larger and more machine-shaped corpus than 655
markdown snippets, one that implementers will certainly vendor rather than
retype.

The structural fix is not a different licence. It is a different **layout**:

> **The conformance suite must live in its own files, under its own
> permissive licence, and must never be embedded inside the CC-licensed spec
> prose.**

That single decision removes the entire ambiguity class, and it is why
JSON Schema's and TOML's arrangements (separate repo, plain MIT) work more
cleanly than CommonMark's despite CommonMark being the more famous precedent.

### 2.3 The two failure modes to name explicitly

**Copyleft on a conformance suite.** A proprietary implementer's CI that runs
a GPL/AGPL suite against a closed binary can be argued into producing a
combined work, triggering disclosure. Nobody wants to find out; the deterrent
operates long before any lawsuit. Every real conformance suite for an open
standard surveyed here lands permissive — JSON-Schema-Test-Suite MIT,
toml-test MIT, yaml-test-suite MIT, web-platform-tests BSD-3-Clause — and that
convergence is the evidence.

**And the mirror-image error: SQLite's TH3.** SQLite is public domain, but its
real test harness is **proprietary and sold separately**. Verified verbatim
from `sqlite.org/th3.html`:

> SQLite itself is in the public domain and can be used for any purpose. But
> TH3 is proprietary and requires a license.

> As of 2018-05-19, the TH3 source tree consists of well over 500,000 lines
> of source code in 1709 separate files. [...] TH3 achieves 100% branch test
> coverage (and 100% MC/DC) over the SQLite core.

> Even though open-source users do not have direct access to TH3, all users
> of SQLite benefit from TH3 indirectly since each version of SQLite is
> validated running TH3 [...] They simply cannot rerun those tests themselves
> without purchasing a TH3 license.

And the contribution policy that goes with it, from `sqlite.org/copyright.html`:

> SQLite is open-source, meaning that you can make as many copies of it as you
> want [...] **But SQLite is not open-contribution.** In order to keep SQLite
> in the public domain and ensure that the code does not become contaminated
> with proprietary or licensed content, the project does not accept patches
> from people who have not submitted an affidavit dedicating their
> contribution into the public domain.

Hwaci additionally **sells a Warranty of Title** for jurisdictions that do not
recognise public-domain dedication (`sqlite.org/purchase/license`; no price is
published on the copyright page).

That is a direct warning, and it is sharper for this project than for any
other precedent, because **SQLite is the project DESIGN.md §17 explicitly
calibrates against** (the 590:1 test-to-code ratio). SQLite's arrangement
works *because* SQLite deliberately does not want independent
implementations — it wants one implementation and a file format guaranteed to
2050. This project wants the opposite. **Copying SQLite's test-suite
economics would defeat the project's entire stated purpose.** Take the ratio,
not the licence.

The corollary, from C2 of DESIGN.md: if the suite *is* the substitute for
plural implementations, then anything that makes the suite less copyable
directly attacks the thesis. The suite must be the **most** permissively
licensed artifact in the repository, not the least.

### 2.4 CC0 vs MIT vs Apache-2.0 vs CC-BY-4.0, decided per artifact

- **Apache-2.0's explicit patent grant and retaliation clause** are worth
  having on anything a company will fork and ship as running code. MIT has
  neither. Cost to a solo author: zero.
- **CC-BY-4.0 on a test suite is the wrong tool.** It carries no patent
  grant, and its "attribution reasonable to the medium" standard is awkward
  to satisfy across thousands of copied fixture files.
- **Code licences on spec prose** (TOML, JSON Canvas) work in practice but
  lack CC-BY's norms for attribution-in-prose, translation, and derivative
  documents. Soft failure, not a blocker.
- **CC-BY-SA on spec prose** (CommonMark) adds share-alike friction for
  anyone writing *documentation* that quotes the spec. Avoid.
- **YAML's "may be freely copied, provided it is not modified"** is the worst
  outcome in the survey: no translations, no derivative editions, no forks
  even when the project stalls. Avoid absolutely.
- **CC0 on raw fixture data** removes even MIT's notice friction. Justified
  for the fixtures specifically — a `.tbl` file containing four rows of
  widgets is data, not authorship, and asserting copyright over it invites an
  argument nobody benefits from.

### 2.5 DCO vs CLA — and what relicensing actually requires

- A **DCO** (`Signed-off-by`, Linux model) gets a signed provenance statement
  while each contributor keeps their copyright. It is enough to defend the
  licence you have. **It is not enough to change it later.**
- Unilateral relicensing requires either a **CLA granting that right**, or
  tracking down every contributor individually. Both Rust and Node ended up
  with broad contributor bases and no full CLA, and accepted that they cannot
  unilaterally relicense old code.
- **SQLite's affidavit model is the maximal version** — and it is why they
  *refuse* outside contributions: *"the project does not accept patches from
  people who have not submitted an affidavit... does not accept patches from
  random people on the internet."* That trade is coherent for SQLite and
  incoherent for a project whose success condition is many implementers.
- **WHATWG requires a real CLA**, because it is a multi-vendor body binding
  patent commitments. Structurally inapplicable to a solo author.

**The asymmetry that decides it:** the artifacts are already going out under
the most permissive terms available. There is no future relicensing move that
a CLA would enable and that anyone would want — you cannot make CC0 fixtures
*more* permissive, and making them less permissive is the rug-pull this
research exists to avoid. A CLA would therefore buy an option whose only use
is the thing the project promises not to do. **DCO.**

### 2.6 Patents and trademark

- **W3C's patent policy does not transplant.** It binds Working Group
  participants to royalty-free licensing; with no members there is nothing to
  bind. The real exposure for a solo author is third-party patents on
  techniques not invented here, and the mitigation for that is Apache-2.0's
  grant on the code, not a policy document.
- **A conformance mark is not needed at v1.** CommonMark shipped for years
  with **no trademark policy at all** (verified — the README carries none),
  despite widespread third-party "CommonMark compliant" claims, and the
  ecosystem's honour-system convention — *conformance is a version number of
  the suite* — is exactly the mechanism DESIGN.md §3(c) identifies as the
  active ingredient. Khronos-style gated certification (paid adopter + passed
  tests + logo licence) is correct for a multi-vendor consortium and absurd
  at this scale.
- **What to do instead, and it costs nothing:** define the conformance claim
  *mechanically* in the spec — "conformant at suite version N" means "passes
  every test in suite version N, including the mutation gate" — so the claim
  is checkable by anyone rather than granted by anyone. Add a short
  `TRADEMARK.md` reserving the format name only if and when third-party
  implementations start appearing.

### 2.7 RECOMMENDED ARRANGEMENT

| Artifact | Licence | Failure mode it avoids |
|---|---|---|
| **Spec text** (prose, grammar, the "deliberately left open" section) | **CC-BY-4.0** | YAML's verbatim-only trap (no translations, no derivative editions, no fork when the project stalls) and CommonMark's CC-BY-**SA** share-alike friction, which discourages third parties from writing documentation that quotes the spec. CC-BY-4.0 is also what WHATWG converged on for exactly this artifact. |
| **Conformance suite — fixtures** (the `.tbl` files, the git scenarios, expected evaluated values) | **CC0-1.0** | The vendoring ambiguity that CommonMark created by embedding examples in CC-BY-SA prose. Implementers *will* copy these files into their repos; CC0 makes that unambiguously free with zero notice obligation. Also avoids asserting authorship over four rows of test data. |
| **Conformance suite — runner, harness, mutation gate** | **MIT** | Same anti-copyleft reasoning as JSON-Schema-Test-Suite and toml-test. MIT (not Apache-2.0) because it is the licence every existing conformance suite uses, and matching the ecosystem's expectation removes a question nobody should have to ask. |
| **Reference implementation** | **Apache-2.0** (optionally `Apache-2.0 OR MIT`, the Rust ecosystem default) | This is the artifact a company forks and ships. Apache-2.0's explicit patent grant and retaliation clause protect both sides at no cost. `OR MIT` additionally removes the friction for GPL-2.0-only downstreams, which Apache-2.0 alone is incompatible with — a real consideration given the whole project runs against GPL-2.0 git. |
| **Validator** | **Apache-2.0 OR MIT** | Same reasoning; consistency avoids a needless fourth licence variant. |
| **Contribution model** | **DCO** (`Signed-off-by`), no CLA | Avoids SQLite's contribution-refusing affidavit model and WHATWG's CLA overhead, neither of which fits a solo author. Records the caveat explicitly for future-you: DCO alone will not permit a unilateral relicense later — and per §2.5, no relicense worth making exists. |

**Repository layout that makes the arrangement real** — the licensing only
works if the files are separated:

    /spec/            CC-BY-4.0        prose, grammar, error-recovery tables
    /conformance/
      fixtures/       CC0-1.0          .tbl files, git scenarios, expected values
      runner/         MIT              harness, mutation gate
    /reference/       Apache-2.0 OR MIT
    /validator/       Apache-2.0 OR MIT
    LICENSE           pointer file naming all four, CommonMark-style
    NOTICE            the git-subprocess reasoning from §1.8
    DCO / CONTRIBUTING.md

Add per-directory `LICENSE` files and SPDX headers (`SPDX-License-Identifier:`)
on every file. The single most common way this arrangement fails is not a
wrong licence choice — it is one `LICENSE` file at the root that says
"MIT" and leaves everyone guessing which artifact it covers.

**Two things to write into the spec on day one, both cheap now and expensive
later:**

1. The **git-subprocess reasoning** (§1.8): the suite invokes GPL-2.0 `git` as
   a subprocess, which creates no copyleft obligation. Say it before anyone
   asks, because "runs against stock git" is the project's defining claim and
   the question will be asked.
2. The **mechanical conformance claim** (§2.6): conformance is a suite version
   number and a passing run, not a badge anyone grants.

---

## PART 3 — NAME AND PRIOR-ART CLEARANCE

### 3.1 `.tbl` — the extension is heavily overloaded. RECOMMEND DROPPING IT.

There is no IANA registration and no trademark blocking `.tbl` (the IANA
media-types registry was fetched directly: **no registered type containing
"tbl" or "table"**). The problem is not legal, it is collision and
discoverability, and it is severe.

**Measured directly** (`gh api search/code -f q="extension:tbl"`, 2026-08-28):

    extension:tbl     158,208 files indexed on GitHub
    extension:ttbl         75
    extension:gtbl          3
    extension:mdtbl         0
    extension:tblm          0

158,208 files is not a theoretical collision. Confirmed existing users:

| Prior use | Status | Detail |
|---|---|---|
| **Unix/groff `tbl`** | Confirmed (man7.org) | `tbl` is troff's **table preprocessor**, still shipped in GNU groff (1.24.1, 2026). It does *not* use a `.tbl` file extension — tables are inline in roff source between `.TS`/`.TE`. So no literal file collision, but **forty years of "tbl" meaning "a table description language for a text formatter"** is the exact semantic space this project occupies. To any Unix reader, `.tbl` reads as roff. |
| **FreeSpace 2 Open** | Confirmed (`scp-fs2open/fs2open.github.com`) | `ships.tbl`, `weapons.tbl`, `ai_profiles.tbl` — **plaintext, tag-based, human-editable, git-versioned today** by a 25-year-old modding community. This is the closest live collision: same extension, same plaintext-table-in-git niche. |
| **Blizzard StarCraft** | Confirmed | `.tbl` inside MPQ archives holds in-game text labels; heavy modding use. |
| GIS/CAD/molecular | Confirmed (file-extensions.org) | Insight II, Pro/Engineer·Creo, Autodesk Civil 3D, ArcGIS/ArcView, PageMaker, OS/2 — all use `.tbl` for "textual semi-database table files." |
| `TRANS.TBL` | Confirmed | ISO9660/Rock Ridge filesystem convention. |
| SS7/telecom | Confirmed (`openss7/openss7`) | `hlr_cost.tbl` cost tables. |
| **Total War DB tables** | **NOT CONFIRMED — do not cite.** | RPFM's manual (the standard Total War pack-file editor) makes no mention of a `.tbl` extension; DB tables are extensionless binary blobs inside `.pack`, exported as `.tsv`. This widely-repeated lead appears to be wrong. |
| SAS/Stata, Windows/Intel firmware | Unverified | Search budget exhausted. SAS uses `.sas7bdat`, Stata `.dta` — `.tbl` is unlikely for either. Low priority: the confirmed collisions already settle it. |

**Verdict: `.tbl` is ambiguous-to-actively-taken.** It survives legally and
fails practically. A format whose entire pitch is *specified, unambiguous,
one-outcome-per-input* should not open with an extension that means six things.

**Recommendation, in order:**

1. **`.mdtbl`** — 0 collisions on GitHub. States the truth: a
   markdown-flavoured table. A reader who has never heard of the project
   guesses correctly, which is the whole job of an extension.
2. **`.gtbl`** — 3 collisions. Ties to git and to a `g*` tool family.
   Slightly more cryptic.
3. **`.tblm`** — 0 collisions, but reads as a typo of `.tbl`, which is the
   collision restated rather than avoided.

**Avoid `.table`** — a real English word; more overloaded than `.tbl`, not
less. **Avoid `.ttbl`** — 75 collisions and visually indistinguishable from
`.tbl` in a directory listing, which is the worst of both.

### 3.2 The working name `gws` — TAKEN on every registry. Do not use it.

| Registry | Status | What holds it |
|---|---|---|
| crates.io | **TAKEN** | `gws` — a JSON-RPC 2.0 websocket client/server (`neogenie/gws`) |
| npm | **TAKEN** | `gws` — "E2E Combinatorial Testing Tool" |
| PyPI | **TAKEN** | `GWS` — a near-empty placeholder package |
| GitHub | **TAKEN, and worst of all in this exact niche** | **`StreakyCobra/gws`** — *"Colorful KISS helper for **git workspaces**"*, 237 stars, with forks and imitators (`emlun/gws2`, `medialo/gogws`). Also `lxzan/gws`, a popular Go websocket library. 2,530+ repos match. |

The `StreakyCobra/gws` collision is disqualifying on its own: it is a
git-workspace CLI named `gws`, which is precisely the semantic slot the
prototype's `gws` binary and `gws-type-<suffix>` handler convention would
occupy. "Google Workspace" turns out to be a **weaker** collision than feared
(the official shorthand was "G Suite", never GWS), but it is still search
noise.

### 3.3 Candidate names, cleared against all three registries

Verified live 2026-08-28 (`crates.io/api/v1`, `registry.npmjs.org`,
`pypi.org/pypi/<n>/json`):

| Candidate | crates.io | npm | PyPI | GitHub name noise | Verdict |
|---|---|---|---|---|---|
| **`rowspec`** | free | free | free | 0 matches | **CLEAN** |
| **`nomtab`** | free | free | free | 0 matches | **CLEAN** |
| **`mergetab`** | free | free | free | 29, all generic, no dominant project | **CLEAN** |
| `rowform` | free | free | free | — | Clean |
| `rowkeyed` | free | free | free | 0 | Clean |
| `idtable` | free | free | free | 8, all obscure | Clean |
| `tabspec` | free | free | free | 5, unrelated | Clean |
| `cellspec` | free | free | free | 13 incl. `CellSpectra` (bio) | Minor noise |
| `opentbl` | free | free | free | `guillemborrell/OpenTBL` — CFD "turbulent boundary layer", 9★, unrelated field | Low risk |
| `plaintable` | free | free | free | `jonathaneunice/plaintable`, 1★, inactive | Same concept space, tiny |
| `formtab` | free | free | free | **157 matches** | Too crowded |
| `gitcell` | free | free | free | 9 incl. exact `gitcell/SWManager` | Minor risk |
| `difftab` | free | **TAKEN** | free | 17 | npm blocked |
| `tabl` | free | **TAKEN** | **TAKEN** | — | Blocked |
| `cellar` | **TAKEN** | **TAKEN** | **TAKEN** | — | Blocked |
| `keytable` | — | — | — | `DataTables/KeyTable`, 36★, real jQuery plugin | **Avoid** |
| `gridspec` | — | — | — | `matplotlib.gridspec` — a very well-known API | **Avoid** |

**Recommendation: adopt the CommonMark/cmark split.** The evidence in
DESIGN.md §3(c) is that the *spec* is the artifact that acquires reputation
and the *implementation* is a companion — so they should not share a name,
and the reference implementation should be visibly not-the-definition
(CommonMark's founding grievance was `Markdown.pl` being the definition).

- **Format / spec name: `RowSpec`.** Clean everywhere. It names the actual
  innovation — row identity plus header formulas — rather than "tables"
  generically, and "-spec" signals that the artifact is a specification.
- **Alternative, if a more distinctive mark is wanted: `NomTab`**, from
  *nominal addressing*, which is invariant I2 and the thing that makes the
  480→660 result work. More distinctive, more opaque without a tagline.
- **CLI / reference implementation: a short typeable binary**, e.g. `rspec`
  (**collides with Ruby's RSpec — avoid**), so prefer `rowc` or `mtbl`. Check
  the final pick against crates.io/npm/PyPI before committing; the three
  format names above are cleared, the binary name is not yet.
- **`mergetab`** is the option that communicates the value proposition
  fastest to the target audience, at the cost of naming the benefit rather
  than the thing.

### 3.4 Concept collision — the product landscape

**The specific quadruple appears to be open**: formula in the column header +
blank cells in that column + opaque row-id column + no coordinate syntax at
all. No hit on GitHub, crates.io, npm or PyPI combines all four.

The nearest published prior art, and it is instructive:

**`cescript/MarkdownFormula`** — *"Use Excel-like formulas in markdown
tables."* Verified via `gh api`: **GPL-3.0**, 31 stars, created 2021-09-25,
**last pushed 2021-10-13** — abandoned after three weeks. It made the
**opposite choice on every axis this design turns on**:

| Axis | MarkdownFormula | this design |
|---|---|---|
| Formula location | **in the cell**, `[value](#formula)` link syntax | **in the column header**, cells blank |
| Addressing | **A1 coordinates** (`C1`, `C1:C2`) | nominal only, no coordinate syntax in the grammar |
| Row identity | none | opaque row-id column |
| Merge behaviour | inherits the 480-vs-660 defect by construction | the defect is unrepresentable |

And a detail worth putting in the spec's rationale section: **MarkdownFormula
is GPL-3.0 because it wraps HyperFormula**, which is GPL-3.0-only (§1.2). The
closest prior art was forced into a copyleft licence by its engine choice.
That is the licensing trap of §1.2 and the design trap of §3(a) in one
abandoned 31-star repository.

**Cite it in the spec as the "why not do it that way" reference.** It is the
cleanest available demonstration that the obvious design — formulas in cells,
coordinates for addressing — has been tried, and it is the negative control
the project's central claim needs.

Other checks:

| Project | Relation | Verdict |
|---|---|---|
| **VisiData** | Computed columns at *view* time; README confirms it converts between existing formats and defines **no diffable save format of its own** | Adjacent tool, not a competing format. IGNORE |
| **`k1LoW/tbls`** | DB schema *documentation* generator; CI-friendly | Naming-adjacent only. Note it when picking a name. |
| Grist, Quadratic, Rows, Airtable, Notion, Obsidian Dataview/Datacore, Logseq | Formula columns exist, but all are **binary/DB-backed or app-embedded** — none is a portable plaintext file format | Already covered in DESIGN.md §2. DIFFERENTIATE |
| `daff`, `csvdiff` | Diff *existing* CSVs; define no formula-bearing format | Cited, not competing |
| Frictionless Table Schema | Describes column **types**, not formulas | Complementary; worth citing as the interop target for STATE-OF-PLAY item L |

**Caveat on completeness:** the session's WebSearch budget (200 calls) was
exhausted before the broadest product-landscape term list could be run. The
registry, GitHub-API and IANA checks above were all made directly against
primary endpoints and are solid; a general-web sweep for a commercial product
with no public repository is the gap. Given DESIGN.md §2 and RESEARCH.md
already covered the product landscape twice, this is a low-probability gap,
but it is a gap.

### 3.5 THE PRIOR ART THE EARLIER PASSES MISSED: Org-mode `#+TBLFM:` and its markdown descendants

This is the most important finding in Part 3, and DESIGN.md does not mention
it anywhere. **Named-column formulas in a plaintext table are not new. Emacs
Org-mode has shipped them for roughly two decades, and there is a live
markdown port.**

#### Org-mode table formulas — verified from the Org manual

Org's manual (`orgmode.org/manual/Advanced-features.html`) documents a `!`
row that **defines column names**:

> The fields in this line define names for the columns, so that you may refer
> to a column as `$Tot` instead of `$6`.

    | ! |         |     P1 |     P2 |     P3 |   Tot |      |

and formulas that reference those names:

    #+TBLFM: $6=vsum($P1..$P3)::$7=10*$Tot/$max;%.1f

**So Org-mode already has:** a plaintext table, nominal column addressing,
formulas that live outside the cells, and column formulas that apply down a
whole column. Four of this design's headline properties, shipped, in a system
with a very large installed base, for about twenty years.

#### The markdown descendant, and it is popular

- **`tgrosinger/md-advanced-tables`** — MIT, 189★, created 2020-10-30, last
  pushed 2024-09-05. *"A text editor independent library to enable formatting
  and Excel-style navigation, and spreadsheet formulas to Markdown tables."*
  This is the engine behind the widely-used Obsidian **Advanced Tables**
  plugin. Descended from **`susisu/mte-kernel`** (MIT, 84★, last pushed
  2020-11-28).
- Its formula syntax is Org's `#+TBLFM:` ported to markdown as an **HTML
  comment below the table**:

      <!-- TBLFM: @>$2=sum(@I..@-1) -->

- Verified from its own `docs/formulas.md`: rows are `@1`, `@>`, `@I`,
  **`@-1` (relative)**; columns are `$1`, `$2`, `$>`, **`$+2` (relative)**;
  ranges are `@I..@-1`. **Numeric column references only — no named columns.**
  And **formulas write computed values into the cells.**

Also found, minor: `yibie/grid-table` (Emacs grid table with formulas,
2025-08), `LaunchPlatform/beangrid` (MIT, 5★, created 2025-07-25, last pushed
2025-07-26 — a two-day experiment).

#### Why this strengthens the design rather than threatening it

`md-advanced-tables` is not a competitor. It is the **negative control the
project's central claim has been missing**, and it fails on precisely the
three axes DESIGN.md derived from measurement:

| DESIGN.md invariant / finding | Org / md-advanced-tables | This design |
|---|---|---|
| **I2 — no coordinate syntax in the grammar** | **Violated.** `@1`, `$2`, `$>`, `@I..@-1` are coordinates. Org offers names as an *option*; md-advanced-tables offers only numbers | No coordinate syntax exists |
| **The `prev.` finding** (§7: removed because it is a coordinate that restores the 480-vs-660 defect and makes aggregates non-commutative) | **Shipped as `@-1` and `$+2`** — relative row and column references are exactly the operator the adversary killed | Not representable |
| **CO-LOCATE A NAMESPACE'S BINDINGS** (§4, and the exact defect the adversary found in the `.tbl` aggregate block, §16 risk 2) | **Violated.** The formula namespace lives in a `#+TBLFM:`/`<!-- TBLFM: -->` line **separate from the table**, so a concurrent edit to a formula and a concurrent edit to the table are different lines and merge clean | Formula is **in the column header**, so a formula collision *is* a line collision that git refuses |
| **I4 — derived values may not be committed** (§9: measured to flip a correct 660 into two distinct failures) | **Violated.** Computed values are written into the cells and committed | Cells in a formula column are blank |
| **Opaque row identity** | Absent | Present |

**This is the single best argument the project has, and it was sitting in
plain sight.** The design's four most contested decisions — no coordinates,
no `prev.`, formula in the header rather than beside the table, and no
committed derived values — are each a *departure from a real, popular,
twenty-year-old system that made the other choice*. That converts them from
assertions into contrasts, and gives the conformance suite an obvious
external corpus: take real `#+TBLFM:` tables, and show what stock git does to
them.

#### It also partially answers an open question

DESIGN.md §18 question 3 asks whether column-formula authoring is usable by
non-developers, and calls the naming evidence "genuinely split." **Org-mode's
`!`-row named columns are twenty years of field evidence that people do
tolerate named-column formulas in a plaintext table** — with the large caveat
that Org's user population is not representative of non-developers. It does
not close the question, but it moves the prior, and it is a far better
starting corpus than a synthetic study.

#### Actions

- **CREDIT explicitly.** Org-mode's `#+TBLFM:` and the `!` name row belong in
  the spec's prior-art section, named as the ancestor. Not crediting a
  twenty-year-old convention that a large community uses would read badly and
  would be wrong.
- **DIFFERENTIATE on the four axes in the table above** — in the spec's
  rationale, with the measurements DESIGN.md already has.
- **ADOPT nothing directly** — `md-advanced-tables` is MIT so adoption would
  be legally trivial, but its design is the one being refuted.
- **Use it as a suite corpus.** Real-world `#+TBLFM:` tables are an
  independent source of test inputs for STATE-OF-PLAY item G (nothing
  validated on a realistic corpus).
- **Naming consequence:** avoid `TBLFM`, `tblfm`, and anything that reads as
  a variant of it.

### 3.6 Academic and hobbyist prior art on the three specific claims

Searched via dblp, arXiv, the Programming Journal, HN Algolia, project
primary sites and the Wayback Machine. (The session's WebSearch budget was
exhausted, so this pass ran on direct fetches — which is the better evidence
but a narrower net.)

#### (a) Formula in the column header, cells derived — a LONG lineage, all of it citable

**Nobody has done it in a plaintext, git-diffable table format. Everybody has
done the underlying idea.**

| Work | Year / venue | What it did | Verdict |
|---|---|---|---|
| **Javelin** | 1984, Javelin Software | *"Models are built on objects called variables, not on data in cells of a report."* Predates Improv by ~7 years | **CREDIT** |
| **Lotus Improv** | 1991, Lotus ATG (Pito Salas), NeXTSTEP | Formulas defined on **named categories**, not coordinates: `Total Sales = Unit Price times Unit Sales` | **CREDIT — the historical root** |
| "Object Oriented Spreadsheets: The Analytic Spreadsheet Package" | OOPSLA 1986 | Early template/class-of-cells formula abstraction | CREDIT |
| **ClassSheets** — Engels & Erwig | ASE 2005 (`conf/kbse/EngelsE05`); extended in *J. Object Technology* 6(9), 2007, doi:10.5381/JOT.2007.6.9.A19 | Classes define labelled table regions; **a formula is attached once to a column/attribute and instantiated per row**. The closest academic match to the exact mechanism | **CREDIT — cite directly** |
| **Object Spreadsheets** — McCutchen, Itzhaky, Jackson (MIT) | Onward! 2016 (`conf/oopsla/McCutchenIJ16`) | Objects with formula-defined fields populate rows; the formula is a property of the class/column | **CREDIT** |
| **Analytica** — Henrion / Lumina (from CMU Demos, 1979–90) | 1996– | One formula per variable node, auto-broadcast across every array dimension ("intelligent array abstraction") with **no cell duplication** | **CREDIT — strong** |
| **Funcalc / sheet-defined functions** — Sestoft | arXiv:1309.5137 (2013) | Sheet regions abstracted into reusable functions over designated input/output cells. Region-scoped, not column-scoped | CREDIT |
| **Forms/3** — Burnett et al. | *J. Funct. Program.* 11(2), 2001 (PPIG 1995) | Declarative formula-graphics forms; one formula governs a family of cells | CREDIT |
| **Calculation View** — Sarkar, Gordon, Peyton Jones (MSR) | VL/HCC 2018 | Formula editable in an alternate **column-keyed** view synced to the grid. Already cited in DESIGN.md §18 for the 37.14%/40.7% figures — note it is *also* prior art for the mechanism, not only evidence for its usability | CREDIT |
| Bakke (MIT) — spreadsheet UI for plural relationships | CHI 2011, doi:10.1145/1978942.1979313 | Precursor to the SIEUFERD nested-relation line | CREDIT |
| Hermans corpus; Miller & Hermans "Gradual structuring" | VL/HCC 2016 and others | Empirical smell/comprehension work — right field, different mechanism | DIFFERENTIATE-FROM |
| Jonathan Edwards, Subtext **"Schematic Tables"** | alarmingdevelopment.org/?p=366 | Confirmed to exist as a talk; **the dedicated post/slides could not be located this pass** | **CREDIT, but chase the primary source before citing specifics** |
| Quantrix Modeler; Erwig's Gencel | — | **Not independently verified.** Do not cite yet | — |

**Combined with §3.5, the honest summary is: the column-formula idea has
thirty-five years of pedigree and at least two direct academic formulations
(ClassSheets 2005, Object Spreadsheets 2016), plus a shipping plaintext
implementation with nominal addressing (Org-mode). What has never been done
is putting it in a *plaintext file whose merge behaviour under stock git is
specified and tested*.** That is a narrower and much more defensible novelty
claim than "column formulas", and the spec should make exactly that claim.

#### (b) Opaque row-id for merge — daff/Coopy already does this, and MUST be cited

**This is the closest prior art in the entire recheck, and DESIGN.md
under-credits it.** §3(a) cites daff only as the thing that "merged the same
file's rows perfectly and produced the identical wrong answer" — true, but
incomplete.

Verified verbatim from `paulfitz/daff`'s own README:

    --id:  specify column to use as primary key (repeat for multi-column key)

    Run `daff git csv` to install daff as a diff and merge handler
    for `*.csv` files in your repository.

So **daff has shipped, since 2013, an id-column-keyed three-way merge wired
into `git merge` as a merge driver.** Its ancestor **Coopy**
(coopy.sourceforge.net, 2010) shipped `csvdiff` / `csvmerge` / `csvpatch` /
`ssfossil`, and Paul Fitzpatrick's theory post — **"Diffing and Patching
Data"**, okfnlabs.org, **2013-08-08** — states the problem in the design's own
terms: *"where's the `diff` and `patch` programs for data? Where's something
like `diff3` for doing 3-way merges?"*

**And the point of departure is a real one, not an oversight.** daff's default
alignment is **content-based** (bag-of-substrings with a Viterbi lattice
across ancestor and both descendants), with the id column an **optional
override**. Coopy's stated theory *chose* content-matching over mandatory
synthetic keys. This design does the opposite — DESIGN.md §7's ablation found
that natural keys lose an edit on rename and overwrite a row on duplication,
content hashes split rows, and **only an opaque id survives all four
scenarios, with every failure silent**.

So the spec's claim must be phrased as a **deliberate divergence from Coopy's
published stance, backed by the ablation** — not as an independent invention.
That framing is stronger anyway: it converts a novelty claim into a
disagreement with a named prior system, supported by measurement.

The second half of the differentiation is §3(b) of DESIGN.md and it is
already proved: **daff's remedy is a merge driver, and merge drivers cannot
be deployed** (`.gitattributes` travels, `merge.<name>.driver` does not; a
bare repo ignores attributes entirely; GitLab.com does not support custom
merge drivers; GitHub "doesn't consider user-defined .gitattributes files").
daff identified the gap correctly in 2013 and prescribed the vehicle that
does not work. **That sentence is the project's thesis in one line, and it
should be in the README.**

Adjacent systems work, all worth a citation and none competing:

| Work | Year / venue | Relation |
|---|---|---|
| **OrpheusDB** — Huang et al. | VLDB 2017, `pvldb/vol10/p1130-huang.pdf` | Bolt-on relational dataset versioning; identity via existing DB primary keys | CREDIT |
| **Decibel** — Maddox, Goehring, Elmore, Madden, Parameswaran, Deshpande | VLDB 2016 | Git-like branching for relational data at the storage-engine level | CREDIT |
| **DataHub** — Bhardwaj et al. | CIDR 2015 / arXiv:1409.0798 | Collaborative dataset version management, git-like semantics | CREDIT |
| ForkBase | arXiv:1802.04949 (2018) | Content-addressed forkable storage; not the plaintext-merge case | DIFFERENTIATE |
| TardisDB (SIGMOD 2021), MusaeusDB (SSDBM 2019) | — | SQL-level versioning for in-memory DBs | DIFFERENTIATE |
| Dolt | — | Already covered in DESIGN.md §2 | — |

**No paper was found arguing that a synthetic opaque id is *required* for
correct merge of tabular text.** Coopy argues the opposite. That gap is real
and the ablation in DESIGN.md §7 is, as far as this search can tell, the only
evidence on the question — which makes it worth writing up properly rather
than leaving in a design report.

#### (c) A conformance suite asserting on evaluated values after a real git merge — GENUINELY OPEN

This is the most novel of the three, and the search actively tried to falsify
it.

| Checked | Finding |
|---|---|
| **jujutsu** (`jj-vcs/jj`) | `lib/tests/test_merge_trees.rs`, `test_merged_tree.rs`, `test_merge_operations.rs` assert on **tree/structural** merge outcomes only. Never evaluates merged file content | DIFFERENTIATE |
| **Pijul** | `pijul.org/manual/theory.html` grounds correctness **purely algebraically** (patch graph, zombie vertices). No semantic verification anywhere | DIFFERENTIATE |
| **Darcs** | Same theory-of-patches lineage; not re-checked this pass | DIFFERENTIATE (assumed) |
| **SemanticMerge / Plastic SCM** | AST-based **structural** merging, not runtime evaluation. Primary domain (semanticmerge.com) is now squatted/defunct — **cite cautiously** | DIFFERENTIATE |
| **nbdime** (Jupyter notebook merge) | **The one unresolved lead.** Notebooks carry *outputs*, so a test asserting on executed cell outputs post-merge would be a direct hit. Whether its suite does this rather than structural source merge **was not confirmed.** Worth one direct look at its test source | **OPEN — check before claiming novelty** |
| **Da Silva, Borba et al. — "Detecting semantic conflicts with unit tests"** | *J. Syst. Softw.* 2024, doi:10.1016/j.jss.2024.112070; preprint arXiv:2310.02395 (2023); precursor **ICSME 2020**, doi:10.1109/ICSME46990.2020.00026 | **The nearest neighbour anywhere.** Merges Java code, then **runs unit tests against the merged result to assert on behaviour**, specifically to catch textually-clean-but-semantically-wrong merges. Same "merge, then execute, then assert" shape | **CREDIT — nearest neighbour** |
| DeltaImpactFinder (arXiv:1509.04207, 2015); "Can PLMs resolve textual and semantic merge conflicts?" (arXiv:2111.11904, 2021); LLM-generated-test variant (arXiv:2507.06762, 2025) | — | Confirm "evaluate after merge" is an **active but strictly code-focused** research niche | CREDIT as context |

**The delta is precise and worth stating precisely in the spec:** the
semantic-conflict literature runs *project-specific unit tests* over
*arbitrary source code* after a merge. This project runs a *fixed, versioned
conformance suite* over a *specified data format*, asserting on *evaluated
values*. Nothing found does the latter. Subject to the nbdime check, claim
(c) is open.

#### Does any prior art mean this should not be built?

**No.** Two calls are close enough to change how the project is *presented*,
neither close enough to change whether it is built:

1. **daff/Coopy** already does id-keyed three-way tabular merge in git, since
   2013 — but via a merge driver, which DESIGN.md §3(b) proves undeployable,
   and with ids optional where this design makes them mandatory on the
   strength of an ablation. **Cite it prominently and differentiate
   explicitly.** Burying it would be the single most damaging omission
   available.
2. **ClassSheets (2005) and Object Spreadsheets (2016)** are real academic
   precedent for "the formula belongs to the column, not the cell" — but both
   are class-generates-spreadsheet systems, not plaintext git-diffable source
   formats. **Cite; the delta is real.**

Add **Org-mode `#+TBLFM:` with the `!` name row** (§3.5) as the third, and
these three together are the prior-art section of the spec.

---

## PART 4 — WHAT BLOCKS BOOTSTRAPPING

**Nothing in this research blocks creating a repository.** Every licence
needed is permissive, no dependency is a NO-GO on the critical path, and
clean names and extensions are available. Four items must be *decided* before
the first commit, and one is a genuine design hole rather than a clerical
choice.

### BLOCKER 1 — the decimal-vs-binary64 contradiction must be resolved before the spec is written

DESIGN.md §13 rejects CEL for being IEEE-754-doubles-only and adopts IronCalc
in the same sentence, while listing "decimal arithmetic" as a requirement.
**IronCalc is IEEE-754 doubles only** (`CalcResult::Number(f64)`,
`CellValue::Number(f64)`, no decimal crate in its dependency graph).

This is not a dependency problem — it is a **normative spec question**, and it
is the kind that cannot be deferred: the conformance suite asserts on
**evaluated values**, so the very first fixture that adds `0.1 + 0.2` needs
the spec to have already decided. Getting it wrong is not a bug, it is a
format edition.

Recommended: **specify binary64 explicitly**, with a normative
rounding/display rule, and record the decision in the "deliberately pinned"
section §17 calls for. If decimal is genuinely required for the financial
framing, then **do not wrap IronCalc's evaluator** — implement the fifteen
functions that 76% of real usage needs over `rust_decimal` (MIT), and use
IronCalc's public `expressions` parser and its function semantics as an
oracle. §1.1's evidence says coverage was never the reason to take the
dependency.

### BLOCKER 2 — `.tbl` and `gws` are both unusable as chosen

- `gws` is **taken on crates.io, npm and PyPI**, and `StreakyCobra/gws` (237★)
  is a **git-workspace CLI** — the same semantic slot.
- `.tbl` matches **158,208 files** on GitHub and already means roff tables,
  FreeSpace 2 mod data, StarCraft string tables, and four CAD/GIS formats.

Neither is a legal problem; both are naming problems that get exponentially
more expensive after the first release. Recommended: **`RowSpec`** for the
format/spec (clean on all three registries and GitHub), **`.mdtbl`** for the
extension (0 GitHub matches), and a separately-cleared short binary name for
the CLI. **Verify the binary name before the first publish** — it is the one
piece not yet cleared, and `rspec` in particular is taken by Ruby's RSpec.

### BLOCKER 3 — the licence split must be laid out in directories, not declared in one root file

The recommendation in §2.7 only works if the artifacts are physically
separated and each carries its own `LICENSE` plus SPDX headers. **The specific
failure to avoid is CommonMark's**: its 655 conformance examples are embedded
inside a **CC-BY-SA** `spec.txt`, so implementers vendoring the examples are
vendoring share-alike content. This project's suite will be larger, more
machine-shaped, and certainly vendored. Keep fixtures in their own tree under
**CC0-1.0** and never inside the spec prose.

Also write, on day one, the two paragraphs in §2.7: the **git-subprocess
reasoning** (invoking GPL-2.0 `git` creates no copyleft obligation) and the
**mechanical conformance claim** (conformance is a suite version plus a
passing run, not a badge anyone grants).

### BLOCKER 4 — three pieces of prior art must be credited in the spec's first draft

Not legal blockers; credibility blockers. Shipping a spec that appears
unaware of any of these would be worse than the omission itself, because each
one, properly cited, *strengthens* the argument.

1. **Org-mode `#+TBLFM:` and its `!` column-name row** (§3.5). Nominal
   column addressing in a plaintext table, shipping for ~20 years, with a
   live markdown port (`md-advanced-tables`, MIT, 189★, plus the Obsidian
   Advanced Tables plugin). The design's four most contested decisions — no
   coordinates, no `prev.`, formula in the header rather than beside the
   table, no committed derived values — are each a departure from it. It is
   the negative control the central claim needs.
2. **daff / Coopy** (§3.6b). Has shipped id-column-keyed three-way tabular
   merge **wired into `git merge`** since 2013. DESIGN.md §3(a) cites it only
   as the tool that produced the identical wrong answer. The full framing —
   *daff identified the gap correctly in 2013 and prescribed a vehicle
   (`merge.<name>.driver`) that cannot be deployed* — is the project's thesis
   in one sentence and belongs in the README.
3. **ClassSheets (ASE 2005) and Object Spreadsheets (Onward! 2016)**
   (§3.6a). Real academic precedent for "the formula belongs to the column,
   not the cell." The delta — plaintext, git-diffable, merge-specified — is
   real, but the novelty claim must be narrowed to it.

**One follow-up before claiming novelty on the conformance suite:** check
**nbdime**'s test suite. Notebooks carry *outputs*, so if nbdime asserts on
executed cell outputs after a merge, it is a direct hit on claim (c). This
was the one lead the search could not resolve.

**One correction to carry forward:** a secondary source described
`md-advanced-tables` as putting formulas *inside body cells*. It does not —
verified from its own `docs/formulas.md`, formulas live in an HTML comment
**below the table** (`<!-- TBLFM: @>$2=sum(@I..@-1) -->`) with numeric column
references only. `MarkdownFormula` is the one that puts them in cells. The
distinction matters, because "below the table" is the *scattered namespace*
defect, and "in the cell" is the *coordinate* defect — two different failures
the design refutes for two different reasons.

### NOT blockers, but decisions worth making now

| Item | Decision |
|---|---|
| **tree-sitter** | Do not adopt. Its heuristic error recovery is incompatible with "one specified outcome per input" (§1.4). Hand-written lexer + recursive descent. |
| **daff** | Citation only, never a dependency. Dormant since 2025-05-04, bus factor 1, no Rust path. |
| **TALA** | Never a dependency or a default. Proprietary, watermarked without a licence, and the Enterprise tier **auto-assigns diagram IP to the purchasing org, revocably**. D2's bundled Dagro and elk-go make it entirely avoidable. |
| **HyperFormula** | Disqualified — GPL-3.0-**only**, and the "free for open source" exception could not be verified from any primary source. |
| **git library vs git binary** | The conformance suite must invoke the **real `git` binary**. Using `gix` or `git2` inside the suite would silently substitute the thing under test. |
| **IronCalc funding watch** | The NLnet NGI Zero grant ran **2024-02 → 2026-05 and has ended**. Development has not slowed, but revisit in 12 months. Pin the version regardless — a moving engine makes conformance results irreproducible, which is a spec-integrity problem, not a convenience one. |
| **CodeMirror / ProseMirror / Yjs** | Not on the critical path. §11 already puts frontends at Tier 3, "first-party only, explicitly unstable." Keep them there. |
| **Contribution model** | DCO, no CLA — and record now that this forecloses a future unilateral relicense, which §2.5 argues is a thing you never want anyway. |

### Research gaps in this pass, stated honestly

- **The session's WebSearch budget (200 calls) was exhausted** partway
  through. Everything above was verified by direct fetch against primary
  endpoints — `crates.io/api/v1`, `registry.npmjs.org`, `pypi.org/pypi`,
  authenticated `api.github.com`, `raw.githubusercontent.com`,
  `gitlab.com`, `iana.org`, `nlnet.nl`, `orgmode.org` — which is the stronger
  evidence anyway. The gap is a **general-web sweep for a commercial product
  with no public repository**. DESIGN.md §2 and RESEARCH.md covered the
  product landscape twice already, so this is a low-probability gap, but it
  is a gap.
- Three secondary `.tbl` leads (SAS/Stata, Windows/Intel firmware) are
  **unverified**. The confirmed collisions already settle the verdict.
- The **Total War `.tbl`** lead, which circulates widely, **did not verify** —
  RPFM's manual makes no mention of it. Do not repeat it.
- The **Refac spreadsheet-formula patent litigation** (early-1990s, against
  Lotus/Borland/Microsoft) is recalled but **not independently verified**.
  Do not cite it.
- The exact date WHATWG moved HTML to CC-BY-4.0 could not be pinned; the
  dedicated LICENSE file appears in git history around **2018-01-12**
  ("Meta: update for new WHATWG copyright"). The mechanism is confirmed; the
  date is approximate.
- The **Unicode License v3 adoption date** could not be pinned. The
  `license.txt` copyright line reads "© 1991-2026 Unicode, Inc.", which is a
  range, not an adoption date.


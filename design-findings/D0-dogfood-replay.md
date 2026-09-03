<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# D0 — the history-replay arm

Every commit of four real CSV-in-git files, replayed through rowspec: **7,446
commits, 112 distinct authors, 2011–2026**, plus **528 real three-way merges
replayed as real `git merge` runs**. Harness and per-commit ledgers in
`experiments/D0-dogfood/`. Nothing was cloned into the rowspec repository and
nothing was committed; the corpora are read-only clones in `/tmp`.

**Verdict in one line.** The identity mechanism, the locality claim and the
merge claim all survive contact with real editing history — and the format's
refusals do not. `.mdtbl` refuses **26.95%** of real commits against a
pre-registered ceiling of 2%, and **95% of those refusals are one thing**: a
`|` inside a value that a human deliberately typed. That is not a defect in the
data. It is the format refusing correct data, and under the pre-registration it
counts against us.

---

## 1. The corpora, and why these

Selection criteria, applied before any measurement: a real public repository,
a CSV edited by more than one person over years, and — deliberately — *not* the
cleanest ones available. Three of the four were picked for a specific kind of
mess.

| corpus | file | commits | authors | span | rows→ | cols→ | why chosen |
| --- | --- | --: | --: | --- | --: | --: | --- |
| `iptv-org/database` | `data/channels.csv` | 7,008 | 93 | 2022‑02 → 2026‑08 | 29,796→40,834 | 11→12 | the high‑churn registry: 1,004 merge commits, mass re‑sorts, whole column set replaced mid‑life, 1,033 bot commits alongside human ones, CRLF throughout |
| `datasets/country-codes` | `data/country-codes.csv` | 74 | 12 | 2013‑12 → 2026‑05 | 249→249 | 20→56 | the wide registry: columns grew 20→56 **and were fully reordered**, 25 of the names contain spaces or parentheses, Arabic/Chinese/Russian values |
| `lukes/ISO-3166-…-Regional-Codes` | `all/all.csv` | 25 | 6 | 2011‑04 → 2024‑06 | 248→249 | 7→11 | the small hand‑edited registry: 15 years, sloppy pastes, columns added twice, three separate ragged‑row defects live for years |
| `iptv-org/database` | `data/blocklist.csv` | 339 | 20 | 2022‑02 → 2026‑08 | 799→1,578 | 2→3 | a column (`reason`) added mid‑life; and a file with **no unique key column at all**, which is the case the sidecar cannot serve |

Two candidates were tried and dropped: `jpatokal/openflights` (headerless `.dat`
files, effectively single‑author) and `owid/covid-19-data` (already measured in
M1; its CSVs are machine‑generated per release, not edited).

**Only one of the four produced a real three-way merge.** `country-codes`,
`all.csv` and `blocklist.csv` have 25, 20 and 1,004 merge commits between them
and **not one** where both sides had changed the file since the merge base:
these projects rebase, squash, or have a single writer. All 528 real content
merges come from `channels.csv`. That is itself a finding about how CSV-in-git
repositories actually work.

## 2. Method

At each commit, in topological order over the full history DAG (`rev-list
--full-history --topo-order`), the real CSV is read and converted to a `.mdtbl`
with an added opaque key column (`rowid`, `key := rowid`) and no `order`
declaration. Row ids are inherited from the commit's first parent by the M1
mechanism — the sidecar's declared key column — and freshly minted otherwise;
a merge commit also inherits from its second parent. Per commit we record the
refusal and its exact reason, ids carried / re-minted, the `.mdtbl` diff against
the CSV diff **for the identical pair of states**, and whether `canon` would
alter bytes a human wrote. Both arms run: `.mdtbl` (converted) and CSV mode
(`rowspec check` on the real `.csv`, zero migration, with a five-line sidecar).

Carriage is **not** scored by the key join that produced it. An independent
witness pairs rows between two commits from content alone — identical lines
matched as a multiset (so a mass re-sort does not read as churn), then the
remainder paired by field overlap through an inverted index. Carriage is then
"of the rows the witness says are the same row, how many kept their id".

## 3. The pre-registered thresholds, one by one

### T1 — refusal rate on real, already-accepted commits. Threshold: >2% fails.

| arm | refused | of | rate | verdict |
| --- | --: | --: | --: | --- |
| `.mdtbl`, column names mangled to legal idents | 2,007 | 7,446 | **26.95%** | **FAIL** (13.5× the ceiling) |
| `.mdtbl`, column names verbatim (SPEC §4.1.9 ABNF) | 2,057 | 7,446 | **27.63%** | **FAIL** |
| `.mdtbl`, column names under the *reference implementation*'s ident rule | 2,093 | 7,446 | **28.11%** | **FAIL** |
| CSV mode, zero migration | 218 | 7,446 | **2.93%** | **FAIL** (1.5× the ceiling) |

Per corpus (`.mdtbl`, mangled names): `channels.csv` 1,993/7,008 = 28.4%;
`iso-3166` 14/25 = 56.0%; `country-codes` 0/74; `blocklist.csv` 0/339.

### T2 — row-id carriage across real edits. Threshold: <95% fails.

**224,343,093 of 224,510,486 row-pairs = 99.925%. PASS.**

Per corpus: `channels.csv` 99.927%, `blocklist.csv` 99.005%,
`iso-3166` 98.256%, `country-codes` 97.198%. Ids re-minted: 306,860 — dominated
by genuinely new rows (`channels.csv` grew by 11,000) and by four commits in
2022 where the header was lost entirely (below), which re-minted 29,700 ids at
once. An id landed on a row the witness says is substantially different
(<50% field overlap) 2,208 times, 0.00098% of pairs.

### T3 — diff size, `.mdtbl` against the same change in CSV. Threshold: >1.5× median fails.

**Median per-commit ratio: 1.0000 lines, 1.3364 bytes. PASS on both.**
p90: 1.000 lines, 1.451 bytes. Aggregate over all 7,443 measured transitions:
1.056× lines, 1.432× bytes.

The byte overhead is structural and constant — `| ` delimiters plus a 12-byte
id column — not a locality failure. Locality itself is exact: on the fifteen
largest real changes in the corpus (78,385-line CSV diffs, 12,000 rows added and
12,000 removed in one commit) the ratio is 1.000, and across 110 mass re-sorts
and column-wide rewrites with no row added or deleted, `.mdtbl` and CSV produce
the same diff to within two lines. The one corpus that exceeds 1.5× on bytes is
`iso-3166` at 1.585 median, where the rows are 7 to 11 two-letter codes and the
delimiters are a large fraction of the line.

### T4 — real merges. Threshold: any silent-wrong is fatal.

**528 replayed, 0 excluded. Silent-wrong: 0 for `.mdtbl`. PASS.**

### T5 — canon churn.

`canon` alters **3,798 cells out of 3,607,903,173 seen (0.000105%)**: 1,586 NFC
renormalisations and 2,212 whitespace trims. Two shapes, both real:

```
channels.csv  'Famalicão'  written NFD (o + U+0303); canon rewrites it to NFC
channels.csv  'https://www.sms.cz/.../chucktv.png '   trailing space, removed
country-codes ' Willemstad', 'Comorian Franc '        leading/trailing space
```

Neither can change a value — rowspec's parser trims and NFC-normalises on read
anyway, so `canon` only makes the bytes agree with the reading. **PASS**, with
one caveat that belongs in the spec rather than in this column: **7,071 of 7,446
commits are CRLF** and the canonical `.mdtbl` is LF, so adoption rewrites every
line of the file exactly once. That is a one-time cost, not ongoing churn, but
§10 does not say so.

## 4. Every refusal, justified or admitted

### 4a. Justified — real defects, with the bytes

**`iso-3166` — 14 of 25 commits, 4 distinct causes, every one real.** The
refusals are not 14 events; they are 4 defects that lived in the file for years.

```
101befc7 2011-04-21 Luke Duncalfe "Filing data"
  header (7): name,alpha-2,sub-region-code,alpha-3,country-code,region-code,iso 3166-2
  row    (5): Åland Islands,AX,ALA,248,ISO 3166-2:AX
  row    (5): Antarctica,AQ,ATA,010,ISO 3166-2:AQ
```
Two fields short. `alpha-3` holds `ALA`… no: `sub-region-code` holds `ALA`,
`alpha-3` holds `248`, `country-code` holds `ISO 3166-2:AX`. **Every value after
position 2 is in the wrong column**, in a repository with thousands of
dependants, for three years. This is §9.6, and it is the check M1 says
maintainers write by hand.

```
56efb650 2014-05-13 jlewis91 "Update all.csv"
  row (8): Bolivia\, Plurinational State of,BO,BOL,068,ISO 3166-2:BO,019,005
  row (8): Bonaire\, Sint Eustatius and Saba,BQ,BES,535,ISO 3166-2:BQ,019,029
```
A **backslash-escaped comma**. RFC 4180 has no backslash escape, so every
conforming reader splits the row into 8 fields. Fixed at HEAD by proper quoting.

The fourth is the column name `iso 3166-2` with a space in it, later renamed to
`iso_3166-2` by the maintainers themselves.

**`country-codes` — 21 commits, 4 causes, every one real.**

```
b9120096 2018-08-06 ewheeler "change Swaziland to Eswatini"
  501 data rows in a 250-row table — the entire file appended to itself,
  header included as a data row. rowspec: duplicate key ISO3166-1-Alpha-3='TWN'
a3463338 2018-08-06 ewheeler "one more Eswatini change"   (the fix)
  rowspec: column name '<U+FEFF>Global Code' contains the invisible character
           U+FEFF (ZERO WIDTH NO-BREAK SPACE)
4c545071 2024-09-30 gradedSystem "[fix][s] Accidentally deleted the data folder"
  253 rows; DNK, ESH, NLD, SYC each appear twice
d4e48954 2016-06-09 ewheeler "update data"
  two rows (Channel Islands, Sark) with an empty ISO3166-1-Alpha-3
```

The whole-file duplication survived two commits. The BOM is *inside* the 15th
column name, so `df["Global Code"]` silently returns nothing.

**`channels.csv` — 115 of the 1,993 `.mdtbl` refusals, and all 183 CSV-mode
refusals, are real defects.**

```
0430fdba, 36afaadf, +3 more:  unresolved conflict marker '<<<<<<< HEAD'
                              — a committed merge conflict, in the live data file
8b32fcd5, 603a42bb, +2 "Add files via upload" (TertoGordez, 2022):
     first line of the file is  AndorraTV.ad,Andorra TV,,,AD,...
     — the header row is gone. rowspec: "declares key 'id' but
       data/channels.csv has no such column"
eea76d8c "Update 1" (AntiPontifex, 2023):
     header ends  ...,website,logo,,,,,,,,,,,,,,,,,,,,,,,,,
     rowspec: "duplicate column name an unnamed column — the header has 27 of it"
UATV.cl has 17 field(s), the header declares 16   (41 commits)
duplicate key id='KpopTVPlay.br' — 2 rows share it (21 commits)
```

CSV mode: **218 refusals, zero false positives.**

### 4b. Admitted false positives

**1,912 of the 2,007 `.mdtbl` refusals — 95% — involve a `|` in a value, and
1,863 of them have no other defect of any kind.**

```
KSTVAction.ua,KS TV | Action,КС ТБ | Action,,Kyivstar,UA,movies,FALSE,,,,https://…
KSTVBeachRelax.ua,KS TV | Beach. Relax,КС ТБ | Пляж. Релакс,,Kyivstar,UA,relax,…
```

93 channels, 184 cells at HEAD. These are the broadcasters' own names. SPEC
§4.1.3: *"A cell can never contain `|`, because no escape exists and none may be
invented."* The first such row lands at `404d508c` (2023-10-16, a bot commit),
and **every one of the 1,912 commits from there to HEAD carries at least one.**
The split is total:

```
channels.csv, commits before the first pipe :   81 refused of 5,094 =   1.6%   (under the 2% ceiling)
channels.csv, commits from the first pipe on: 1,912 refused of 1,912 = 100.0%
```

Before October 2023 this corpus **passes** T1. One channel name ends that.

15 further commits carry a value with an embedded newline
(`https://7tvandalucia.es/portada/\r\n`) — a stray line break inside a quoted
CSV field, which one line per row cannot hold either. I count that as a defect,
not a false positive, but the mechanism is the same.

**25 column names in `country-codes` cannot be written at all**: `UNTERM Spanish
Formal`, `Small Island Developing States (SIDS)`, `Global Code`. Under a
faithful conversion that refuses 48 of its 74 commits. A one-time rename is a
real migration, not zero migration.

**A spec/implementation divergence, found by the data.** SPEC §4.1.9's ABNF
admits `-` and `.` in an identifier; `reference/rowspec/table.py::_check_ident`
does not (with a deliberate comment about `a-b` reading as subtraction). Every
column in `all/all.csv` — `alpha-2`, `alpha-3`, `country-code`, `region-code` —
and 33 in `country-codes` are legal under the spec and refused by the reference.
That is the difference between a 27.63% and a 28.11% refusal rate here, and it
is a straightforward contradiction that a second implementer would hit on their
first real file.

## 5. What the real merges did

528 real three-way merges from `channels.csv`, 2022-02-16 to 2026-07-31, each
replayed twice as a real `git merge` in a fresh repository — no merge driver, no
`.gitattributes`, nothing installed — once on `.mdtbl` and once on the `.csv`
baseline, and judged against a per-row three-way oracle computed independently
in Python.

| oracle | `.mdtbl` | `.csv` | n |
| --- | --- | --- | --: |
| clean | clean | clean | 382 |
| clean | conflict | conflict | 95 |
| conflict | conflict | conflict | 46 |
| clean | **conflict** | clean | 4 |
| clean | clean | **conflict** | 1 |

- **Silent-wrong: 0 for `.mdtbl`.** Also **0 for the CSV baseline.** On a plain
  registry with no computed column, `.mdtbl`'s merge behaviour is
  indistinguishable from CSV's. The format's advantage is in what a formula does
  to a merge, and no real corpus has a formula. This is the honest result and it
  is not the flattering one.
- **197 clean `.mdtbl` merges produced a refused artifact — and in 0 of them
  were the inputs valid.** The merge never turned a representable pair into a
  refused output. The refusals are the pipe rows, already present on both sides.
- **The 4 over-conflicts are caused by the identity mechanism itself.** In
  `1aa47b08d`, 14 rows (`EBS.kr`, `CarrieTV.kr`, …) were added *independently on
  both branches*. In CSV those insertions are byte-identical lines and git
  merges them silently into one. In `.mdtbl` each side minted its own opaque id,
  so the two lines differ and git conflicts. Safe direction, real cost, and a
  consequence of opaque ids that the design record has not stated.
- **`36afaadf6` is the thesis, on real data.** Git merged the CSV cleanly and
  the merged file contains `<<<<<<< HEAD` as a data row. The `.mdtbl` merged
  cleanly too — and the artifact is refused: `row has 2 fields, header has 13`.
- 95 merges conflict in both formats where the oracle says the change was
  disjoint. Git's line granularity over-conflicts, equally, in both.

## 6. Exclusions, harness bugs, and what this could not measure

Three commits excluded of 7,446 (0.04%), all for the same reason: the file did
not exist at that commit (a rename or a deletion the traversal still visits).
No commit was skipped for being hard. Every commit in `git rev-list` gets
exactly one ledger record, and the run asserts it.

**Adversarial checks, and what each caught** (`verify.py`, 26 controls, all
passing after the fixes below):

- *Silently skipping commits*: ledger length is asserted against `rev-list`, and
  every non-excluded record must carry a verdict. Clean.
- *Re-minting counted as carriage*: carriage is scored by the content witness,
  never by the key join. Controls: identical ids score 249/249, shuffled ids
  score 3/249, and the witness refuses to pair a row sharing no field.
- *Comparing diffs of different things*: every `.mdtbl` row must round-trip to
  its CSV row. 182,272 rows checked on `channels.csv`; **93 fail, and all 93
  contain a `|`** — the check found the format's expressiveness limit rather
  than a harness bug. A control confirms `diff_size` separates a one-cell edit
  (2 lines) from a re-sort (256 lines).
- *A detector that cannot fire*: injecting a `|`, a duplicate id, a flipped cell
  and a dropped row into real data all produce the expected verdict.

**Two of my own bugs, both found by the controls, both reported here because an
uncaught one would have flattered the result:**

1. **The merge oracle produced five false "silent-wrong" verdicts.** It stored
   rows as column dictionaries, which padded a ragged row back out to the header
   width, so an untouched short row read as corruption. The same artifact
   appeared in the CSV baseline. Fixed to carry each row's fields verbatim; the
   corrected count is 0 and 0. The buggy run is kept as
   `merge-results-v1-buggy-oracle.jsonl`.
2. **The column mangler was keyed by original name**, so a header with eight
   identically-named (empty) columns emitted one mangled name twice and the file
   was refused for a duplicate column the harness had manufactured. Five commits
   affected. Corrected, they are refused anyway — under a faithful conversion an
   empty column name is not an identifier and eight of them are §9.2 duplicates —
   so no threshold number changes, but five refusal *messages* were mine.
3. A third, caught before it reached a number: I first configured
   `blocklist.csv` with `key: channel`, which M1 explicitly warns is
   legitimately non-unique, and got 324 "duplicate key" refusals — 95.6% of that
   corpus, **all of them my misconfiguration**. Corrected to no declared key,
   the file has 0 refusals. That is a live demonstration of the failure mode M1
   predicted for key inference, produced by a human making the guess by hand.

**What the harness could not do, and it matters most for carriage.** The real
history has no id column. Identity has to be reconstructed from the CSV's own
natural key, so a row whose natural key a human *changed* looks like a delete
plus an add and loses its id — whereas in a real `.mdtbl` the opaque id is in
the file and a rename leaves it alone. **The 99.925% carriage figure is
therefore a lower bound**, and the merge arm inherits the same understatement:
`base_id` is a hash of the natural key, so a rename on one side reads as a
delete/add there too. `blocklist.csv` has no unique key at all, so its rows were
disambiguated by occurrence index — a coordinate, which the format forbids;
its 99.005% is the weakest number here for that reason.

Also not measured: no corpus has a computed column, an aggregate, or a declared
`order`, so refusals 3, 7, 9, 10, 11 and 17 never fired and the evaluator was
never exercised on real data. The `.mdtbl` was built in the CSV's own row order,
so a mass re-sort costs the same in both formats; a stable-order representation
would make 110 of those commits free, and that variant was not measured because
choosing it would have been choosing the flattering answer.

One operational number worth recording: `rowspec.table.parse` takes **4.4
seconds** on a 40,000-row `.mdtbl`, against 0.12 s for the same file in CSV mode
— a 36× gap, and the reason this replay needed eight cores and four and a half
hours. M1's "CI cost is not an adoption objection" was measured in CSV mode
only.

## 7. The single result that would most change a mind

**A `|` in a value.** Not the refusal rate, not the merge table — this one row:

```
KSTVAction.ua,KS TV | Action,КС ТБ | Action,,Kyivstar,UA,movies,FALSE,,,,…
```

Ninety-three channels on a Ukrainian broadcaster use a pipe in their own name.
`.mdtbl` has no escape and §4.1.3 forbids inventing one, on a good argument:
an escape makes the field count differ between readers, which is the silent
corruption the format exists to prevent. So the format is correct, the data is
correct, and they cannot both exist. From October 2023 onward **100% of
`channels.csv`'s commits are unrepresentable**, and the pre-registered
"refusals must be real defects, or they count against us" is decided against the
format by a single character.

Everything else in this run is good news, and this is why it does not matter
yet. A maintainer whose table cannot hold its own rows does not reach the merge
argument. The design record has weighed the escape question as a correctness
trade; it has never weighed it against the frequency of `|` in real registry
data, which here is *every commit for the last three years of the most-cited
candidate corpus*.

The result that would push the other way, and nearly did: **on 528 real merges,
neither `.mdtbl` nor plain CSV ever merged silently wrong.** If the argument for
the format is "stock git merges it correctly or refuses", a real multi-author
registry says stock git already does that for an ordinary sorted CSV. What
`.mdtbl` adds — a value that changes when a merge is wrong — needs a computed
column to demonstrate, and after four years and 7,008 commits, not one of these
maintainers has ever wanted one.

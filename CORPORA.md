<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Corpora — what was measured, and where it came from

The experiments in this repository read 1.9 GB of third-party corpora and
generated git histories. None of it is redistributed here. This file names each
one so a result can be **reproduced rather than trusted**, which is the same
standard the specs themselves are held to.

Sizes are the on-disk size of the working copy at the time of the run.

## Cloned repositories

| corpus | source | size | used by |
|---|---|---|---|
| `rust-book` | `github.com/rust-lang/book` | 38 MB | `D8-identity` — prose block uniqueness |
| `obsidian-help` | `github.com/obsidianmd/obsidian-help` | 677 MB | `D8-identity` — prose block uniqueness |
| `cmspec` | `github.com/commonmark/commonmark-spec` | 1.7 MB | `D8-identity` — control |

Cloned with `--filter=blob:none`. The 40-character uniqueness measurement in
blockspec's design brief comes from the first two.

These three move. `design-findings/D8-identity.md` §3 pins the commit of each
clone the anchor evaluations in `results-anchor*.txt` were run against, because
one of those arms did change when it was re-run against a later clone. That pin
covers the anchor evaluations only — **the 40-character uniqueness measurement
named above is neither pinned nor currently reproducible**, per
kindspec/research#5.

## Benchmark archives

| corpus | source | used by |
|---|---|---|
| SpreadsheetBench 912 | HuggingFace `KAKA22/SpreadsheetBench` | `E1-differential` — evaluator agreement |
| TmplEnron | figshare 5838600, real Enron business workbooks | `E1-differential` — evaluator agreement |
| EUSES / VFUSE | the EUSES spreadsheet corpus | `W3-interop` — formula frequency |
| SB400 | subset of SB912, overlaps it | `E1-differential` — superseded |

The differential's headline figure and its two documented caveats
(kindspec/rowspec#27, #28) come from these.

## Replay corpora — the dogfood run

`D0-dogfood` replayed 7,446 real commits and 528 real three-way merges from four
public CSV-in-git registries. `experiments/D0-dogfood/corpora.json` records the
key and order column used for each; the repositories are:

| ledger | source | file |
|---|---|---|
| `iptv-channels` | `github.com/iptv-org/database` | `data/channels.csv` |
| `iptv-blocklist` | `github.com/iptv-org/database` | `data/blocklist.csv` |
| `country-codes` | `github.com/datasets/country-codes` | `data/country-codes.csv` |
| `iso-3166` | `github.com/lukes/ISO-3166-Countries-with-Regional-Codes` | `all/all.csv` |

`corpora.json` points at `/tmp/d0corpora/...`; clone the four repositories to
those paths, or edit it, before re-running `replay.py`.

rowspec's CSV-mode result — 1,564 CSVs, 16 refused, zero false positives — also
reads `github.com/owid/covid-19-data`, whose thirteen truncated CDC snapshots
are the live defect that result reports.

## Generated state

These are outputs, not inputs. They are recreated by running the experiment and
are excluded because a git repository does not belong inside a git repository.

| path | what it is |
|---|---|
| `W5-server/work*`, `W5-server/work-t*` | server test fixtures, one tree per scenario |
| `V-cas/server.git` | a bare repository built by `writer.sh` |
| `D11-evolution/verrepo` | the version-drift history built by the evolution run |
| `D6-computation/.venv` | duckdb, loro and marimo, for the computation comparison |

## Excluded raw output

Two result files exceed the 2 MB tracking threshold and are regenerable from the
scripts beside them:

- `D0-dogfood/ledger-iptv-channels.jsonl` (7.1 MB) — the per-commit ledger for
  the largest registry. The aggregated `merge-results.jsonl` **is** tracked, and
  it is what the findings quote.
- `E4-if-sum/out/noteval.json` (5.4 MB) — the non-evaluable classification dump.
  `classify.py`'s summary output is tracked.

## The standing caution

`design-findings/E6-formula-ceiling.md` and kindspec/rowspec#28 both record the
same trap, and it applies to every table above: **corpus cell counts are
inflated by replication and fill-down.** 557 of SpreadsheetBench's 2,667
problems ship six files each. The unit that means anything is a *distinct
authored expression*, not a cell.

# D0 history-replay — method notes (working file)

Harness lives beside this file:

- `harness.py`   — CSV reading, `.mdtbl` construction, the independent witness,
                   canon-churn counters, diff measurement.
- `replay.py`    — the per-commit walk. Phase 1 (sequential) carries row ids
                   along the commit DAG; phase 2 (pool of 8) does the
                   per-commit measurement.
- `merges.py`    — replays every real 3-way merge as a real `git merge`, on
                   `.mdtbl` and on the `.csv` baseline, against an independent
                   oracle.
- `verify.py`    — adversarial checks on the harness itself.
- `justify.py`   — prints the offending bytes for every refusal.
- `report.py`    — pools the ledgers into the pre-registered threshold table.
- `find_merges.py` — corpus selection: which merges are real 3-way merges.

Ledgers are `ledger-<corpus>.jsonl`, one JSON record per commit, and
`merge-results.jsonl`, one record per merge.

Nothing is cloned into the rowspec repository; the corpora live in
`/tmp/d0corpora` and are read-only.

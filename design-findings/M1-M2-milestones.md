# M1 and M2 — results

## M2 met: two independent implementations agree on 130 cases

    reference implementation           0 failures
    independent impl (spec-only author) 0 failures
    canon = identity                   correctly rejected
    vacuous {'raw': text} parser       correctly rejected

The second implementation was written by an author forbidden to read
`reference/`, from `SPEC.md` and the fixture tree alone. It reported no
contamination. This is the milestone the plan called "the real test of M0", and
it is met — **after** the spec absorbed the seven behaviours the author's
report showed the prose did not determine.

The suite grew 57 → 130 cases during the build, and the failure count went
0 → 20 → 15 → 5 → 0 as the adversarial cases landed ahead of the implementation
and were then paid off. A suite that never went red would have proved nothing.

## M1: the CSV validator, and the number that changes the pitch

**Run against 1,564 real CSVs from public repositories: 16 refused (1.0%),
ZERO false positives.**

- **`owid/covid-19-data`: 13 files with a live defect.** A 14-column header
  declaring `Doses_Administered` **twice**, over a single 6-field row. pandas
  reads it silently. This is input data to a repository that fed global COVID
  dashboards, and the duplicate-column refusal found it in nineteen seconds.
- **`iptv-org/database`**: the one refusal was their own deliberately-broken
  fixture — in a directory *named after the check*. Their real 40,834-row
  dataset is clean.

### The measurement that changed a rule

**71 of 72 `iptv-org` CSVs are CRLF.** Enforcing §3's original "LF, no BOM"
would have **rejected 98.6% of a well-maintained public registry on first run.**
Both are now warnings, promoted by `--strict`.

That independently confirms the spec amendment already forced by the
contradiction between `roundtrip/crlf` and `parse/crlf-refused`. Two unrelated
routes — a fixture conflict and a real corpus — reached the same conclusion
about the same sentence.

### The honest correction to the adoption pitch

The zero-migration claim is weaker than I stated. The refusal split, precisely:

    bare CSV, no sidecar    4 numbered refusals + 2 encoding checks
    needs the sidecar       4  (including DUPLICATE ROW ID)
    .mdtbl-only             5  (alignment, formulas, aggregates)

**Duplicate row id — the refusal the entire identity argument exists for —
cannot run on a bare CSV**, because nothing says which column is the key. Key
inference was tried and rejected: `blocklist.csv` has a legitimately non-unique
first column, so guessing would have cried wolf on real data.

So the honest sentence is not "no migration" but **"five lines"**: zero
migration buys the conflict-marker and field-count checks; the check the format
exists for costs a five-line sidecar.

### A design detail worth keeping

JSON's repeated-key rule is last-one-wins — **exactly the silent overwrite §9.4
forbids.** The sidecar reintroduced the project's own hazard and had to re-close
it with `object_pairs_hook`. The defect finds its way back in through every new
surface, including the one built to detect it.

### And a near-miss that only real data could teach

WHO's `cases.csv` uses Excel grouped two-row headers, producing seven separate
duplicate-column refusals — *correct and useless*. A wrong explanation, not a
wrong verdict. Now one finding naming the shape. The author's note: "I would not
have found this by reasoning about the spec."

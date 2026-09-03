# Pass 4 — the rule three independent findings converged on

## The convergence

Three results arrived from unrelated directions and say the same thing.

1. **L1 (mine):** a table serialized one row per line, with formulas in the
   column header and no coordinates, merged CORRECTLY under stock git — 660,
   clean, no driver, no `.gitattributes`.

2. **D5 (document models):** two branches inserting a block at the same
   position, in markdown vs Portable Text JSON. Markdown gives two candidate
   paragraphs a human can resolve. The JSON AST is worse in kind: git's line
   matcher aligned the *scaffolding* (`{`, `"_type": "block",`) and split ONE
   logical insertion into TWO conflict hunks inside a single block, so the
   obvious resolution produces Alice's `_key` with Bob's text. Their law:
   *"a line merger's boundaries are the serialization's boundaries, and in a
   serialized AST those don't coincide with the structure's."*

3. **D3 (diff/merge):** custom merge drivers cannot travel — `.gitattributes`
   is tracked but `merge.<name>.driver` is local config, so a fresh clone
   SILENTLY falls back to line merge; and the driver does not run in a bare
   repo at all. GitLab: *"Custom merge drivers are not supported on
   GitLab.com."*

(3) says the line merger is what will actually run. (2) says the line merger's
competence is determined entirely by whether serialization boundaries coincide
with semantic boundaries. (1) shows what happens when they do.

## The rule

    SERIALIZE SO THAT THE UNIT OF MERGE IS THE UNIT OF MEANING.

Git's merge granularity is the line. Therefore one line should be one entity:
one row, one block, one shape, one property. Where that holds, git's "dumb"
line merge is not dumb — it is a correct entity merge, for free, everywhere,
with nothing installed.

Every failure catalogued in this project is a violation of it:

    A1 formula ranges       one line's meaning depends on other lines
    JSON/AST scaffolding    one entity spans many lines; lines span entities
    absolute coordinates    one entity's bytes change when others change
    block separators        a line belongs to a position, not to an entity
    markdown alignment row  one line encodes a property of every other line

## The invariant this forces, which is the sharpest in the design

    I6  STOCK-GIT CORRECTNESS
        An artifact must merge correctly, or fail loudly, under UNMODIFIED git
        with none of our tooling installed. Type-aware merge may only improve
        the EXPERIENCE, never the CORRECTNESS.

This is falsifiable, testable in CI against a plain `git` binary, and it is the
single design constraint that most separates this from every competitor. It
also converts D3's bad news into a design asset: because custom merge is
undeployable, we are forced to make the formats good enough that we do not need
it — which is a better system than one that depends on a driver.

Corollary, from D3's most uncomfortable result: **daff merged an A1-formula
CSV's rows perfectly and produced the identical wrong answer as plain git.**
A structural merger cannot see that a string in a cell encodes a position.
So representation discipline is not merely first in importance; a better merge
algorithm cannot substitute for it at any price.

## What this does to the core

The core is now much smaller than PASS2 claimed, and differently shaped.

    NOT the core: a clever merge algorithm  (undeployable, NP-hard, heuristic,
                  and unable to fix the actual problem)

    THE core:     a representation discipline, expressed as format specs plus
                  an executable conformance suite that runs against stock git

Plus a small runtime: boundary-only parse, name-path resolve, reference
discovery, content-addressed derivation. Type-aware merge sits OUTSIDE the
correctness boundary as an optional accelerator, alongside `-merge` +
resolution from git index stages for the cases the line merger must refuse.

That is a substrate whose most important artifact is a TEST SUITE, not a
program — which is the same shape as CommonMark's spec-tests, and the reason
that spec has independent implementations at all.

---

## Verified: `-merge` gives conflicts-as-data from stock git today

`experiments/V-nomerge/`. `.gitattributes` containing `*.csv -merge`, two
branches editing different cells:

    merge exit=1
    git status --short     ->  UU data.csv
    working-tree data.csv  ->  a,b / 1,2 / 3,77      VALID CSV
    conflict markers       ->  0
    python csv.reader      ->  rows: 3, parses cleanly
    git show :1:data.csv   ->  base
    git show :2:data.csv   ->  ours
    git show :3:data.csv   ->  theirs

The working tree holds one coherent, well-formed artifact. All three versions
are retrievable from the index. `.gitattributes` is a tracked file, so this
travels with the repo and needs **zero local configuration** — unlike a merge
driver, which needs local config and silently degrades without it.

This is I5 ("the working tree always contains valid artifacts") delivered by
stock git, and it is the mechanism Dolt, Automerge and Word all converged on
independently: conflicts in a sidecar, artifact stays openable.

### The cost, stated honestly

`-merge` disables automatic merging entirely for that path. Every concurrent
edit conflicts, including trivially compatible ones. So it must not be applied
everywhere.

### The resulting decision rule

    Format satisfies I6 (line = entity, nominal addressing)
        -> NO -merge. Stock git line merge is CORRECT. Let it run.
           (verified: the L1 table format merges to 660 this way)

    Format cannot satisfy I6 (JSON scene graphs, .fods, OOXML, binary,
    anything where one entity spans many lines)
        -> -merge. Refuse honestly, keep the file well-formed, resolve in-app
           from index stages 1/2/3.

The substrate's native formats are designed into the first category. The escape
hatches for interop live in the second. Nothing in either category depends on
our tooling being installed for its correctness.

---

## A second serialization rule, found by reproducing a silent-wrong in markdown

`experiments/V-mdref/`. Two authors independently cite an API page using the
same reference label `[api]`, each placing the definition next to its use, in
distant sections of a long document:

    git merge          -> exit=0, CLEAN, 0 conflict markers
    definitions in file-> 2
    both links resolve -> https://alice.example/api

CommonMark's first-definition-wins rule means **Bob's citation silently points
at Alice's URL**. No marker, no warning, both definitions sitting in the file.
Markdown itself violates I6.

The mechanism is a NAMESPACE whose bindings are scattered through the file. Git
cannot see a collision between two lines that are far apart, because its unit
of comparison is position.

Contrast the same collision in the L1 table format (`experiments/V-ns/`), where
both authors add a different column that happens to share the name `code`:

    git merge -> exit=1, CONFLICT

It refuses, correctly — because column names are all declared on ONE line, so a
name collision IS a line collision.

    RULE: CO-LOCATE A NAMESPACE'S BINDINGS.
          Declare all names of a kind in one contiguous region, so that a
          collision is a textual collision the line merger can see.

Scattered namespaces are silent-wrong generators: markdown link labels and
footnote labels, YAML/JSON duplicate keys, HTML ids, BibTeX keys. Co-located
namespaces — a table header, a frontmatter block, a single `@layout` section —
are safe.

This also retro-justifies a choice in the L1 format that was made for
readability: putting the formula in the column HEADER rather than beside each
cell co-locates the entire formula namespace on one line.

---

# CORRECTION TO THIS DOCUMENT — `-merge` protects clients, not forges

I claimed above that `-merge` is "repo-portable, needs zero config, behaves
identically everywhere". The last clause is FALSE, and the failure is at the
layer that matters. Verified in `experiments/V-bare/`.

A bare repository has no working tree and no index, and **does not consult
`.gitattributes` at all**, even though the file is right there in the tree:

    $ git --git-dir=server.git cat-file -p main:.gitattributes
    *.csv -merge
    $ git --git-dir=server.git check-attr merge d.csv
    d.csv: merge: unspecified        <-- the declaration is ignored

So the same merge produces opposite outcomes:

    NON-BARE client, `-merge` honoured:
        exit=1, markers=0, file is "a,b / 1,77"     VALID CSV

    BARE repo via `merge-tree --write-tree` (what a forge does):
        a,b
        <<<<<<< main
        1,77
        =======
        1,99
        >>>>>>> feat
      and it PARSES: rows: 6, including ['<<<<<<< main'] as a data row

`attr.tree=HEAD` (git 2.40+) fixes it — `check-attr` then reports
`merge: unset` — but **nothing inside a repository can set it.** It is server
configuration. GitLab documents that custom merge drivers are unsupported on
GitLab.com; GitHub Support says GitHub "doesn't consider user-defined
.gitattributes files" and suggests merging locally instead.

## The architectural consequence, which is significant and must be stated plainly

**Merging via a forge's web UI can silently corrupt artifacts, and no
declaration inside the repository can prevent it.**

This partially undercuts the "it's just git, use any forge you like" promise.
Two honest options, and the design must pick one:

    (a) Accept it. Document that merges must happen in a client that has the
        tooling, and that the green Merge button is unsafe for these types.
        Costs the frictionless-forge story.

    (b) Own the merge. `git merge-tree --write-tree` hands a BARE repo the
        three conflict stages as blobs; a server process reads them, runs any
        merge it likes, and writes the result back with hash-object / mktree /
        commit-tree / update-ref. D9 built this end-to-end: a plain `git clone`
        with NO .gitattributes and NO merge config received a correctly merged,
        valid CSV.

**(b) is the right answer, and it reframes the whole architecture: the merge
driver is the wrong deployment vector; the server is the right one.** Git
remains the distribution and durability format; the version control is ours.

That is a real cost — it means a server component is not optional for correct
collaboration — and it should be priced honestly rather than hidden.

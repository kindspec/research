# Corrections to the prior research pass, with independent reproduction

## CORRECTION 1 — "single writer per repository" is WRONG

RESEARCH.md §4 states: *"The architecture must guarantee a single writer per
repository. Every other decision is downstream of that one."* That was the
prior pass's single hardest constraint. It is an artifact of the WORKING TREE,
not of git.

I reproduced the corrected result independently (`experiments/V-cas/`):
8 concurrent writers x 25 commits each, all appending to **the same file**, in
a **bare** repo, each using a private `GIT_INDEX_FILE` + `read-tree` +
`hash-object` + `update-index` + `write-tree` + `commit-tree` +
`update-ref <new> <old>` compare-and-swap with retry:

    elapsed          : 3.43 s
    commits on main  : 201   (200 + base)
    lines in log.txt : 201
    distinct entries : 200
    LOST WRITES      : 0

The essential detail is that on CAS failure the writer **re-reads the current
content and re-applies its INTENT** ("append my line"), rather than replaying a
diff. `git push` rejection is the same CAS, but the retry is `pull --rebase`,
which replays a *diff* — which is exactly why the prior pass measured 8/8
rebase conflicts and 0% of the second writer's work landing.

**Revised constraint: one writer per WORKING TREE. A bare repository accepts
unlimited concurrent writers via ref CAS.** Every forge independently arrived
at this shape — Gerrit uses JGit `ObjectInserter` + `RefUpdate` CAS and never
uses an index at all; Gitea builds each web commit in a throwaway clone; GitLab
serialises with a per-repository lock in Postgres.

This substantially enlarges the design space: a collaboration server does not
need a global lock, and "git-backed" does not imply "one editor at a time".

## CORRECTION 2 — custom merge drivers are undeployable, so they cannot be a correctness dependency

`.gitattributes` is tracked and travels; `merge.<name>.driver` lives in
`.git/config` and never travels. On a fresh clone the attribute arrives and
the driver is `<UNSET>`, and git **silently falls back to line merge**. Worse,
the driver does not run in a BARE repo even when the server has it configured,
because `check-attr` returns `unspecified` there — only
`$GIT_DIR/info/attributes` works, which is per-repo sysadmin action.

Confirmed externally: GitLab documents *"Custom merge drivers are not supported
on GitLab.com"*; libgit2 registers exactly three built-in drivers and never
reads driver config; jj's compatibility doc says `.gitattributes: No.`

**Consequence for the design: a type-aware merge may be a local ACCELERATOR,
never the thing correctness rests on.** The portable mechanism is the `-merge`
attribute — repo-portable, zero configuration, identical everywhere — which
produces an honest conflict (`UU`, index stages 1/2/3) while leaving the file
in the working tree WELL-FORMED. That is exactly the "conflicts as data beside
the artifact" property I derived independently in PASS3/I5, available from
stock git today.

## CORRECTION 3 — structural merge cannot rescue positional addressing

`daff` merged the rows of an A1-formula CSV case perfectly and produced the
**identical wrong answer** as plain git (3500 vs a correct 5100, confirmed in
LibreOffice). Formulas are opaque strings inside cells; a table-aware merger
has no idea they encode positions.

**This reorders the architecture.** PASS2 claimed the generic entity-map merge
was "where the real work is". It is not. Nominal addressing is a
PREREQUISITE; structural merge is an optimisation on top of it. Representation
discipline first, merge algorithm second.

Reinforced by the accuracy literature: GumTree's move/update actions were
judged inaccurate by experts in >55% of 2,400 cases; ordered tree edit distance
cannot be strongly subcubic unless APSP can; minimum edit script with moves is
NP-hard. Every structural merger is a heuristic on an NP-hard problem, and
github/semantic — a dedicated team, six years — was archived 2025-04-01 with
the diffing half never shipped.

This is good news for a small core: the expensive, unreliable component is the
one we were about to make load-bearing, and it turns out it must not be.

## CORRECTION 4 — my own PASS2 framing of the CRDT question was wrong

I framed it as a fork: plain text canonical (merge may fail) VERSUS CRDT
canonical (opaque but always converges). The published result dissolves it.
Eg-walker (Gentle & Kleppmann, EuroSys 2025): *"we invoke the CRDT only to
perform merges of concurrent operations, and we discard its state as soon as
the merge is complete. We never write the CRDT state to disk."*

So the CRDT is merge MACHINERY, not storage, and it applies at exactly one
layer: the bytes of one open file during a live session. And the thing git
specifically buys is log truncation: a pure-CRDT system can never discard
history because someone may reconnect after six months, whereas **a git commit
IS eg-walker's "critical version"**, after which the op log can be dropped and
three-way merge from the merge base takes over.

Corollary that must be respected: do NOT put a CRDT under tables or canvases.
Ink & Switch, 2026-07: *"The merge replays effects, not intents... any
invariant that spans more than one property or object is invisible to it.
Convergence is not enough."* Their named examples — cached counts, trees,
uniqueness — are precisely a formula result, a slide order, and a z-order.

## CORRECTION 5 — path-based artifact identity is not viable, measured

I had proposed (H9) that paths identify artifacts and IDs are on-demand. The
artifact half of that is wrong. Measured on a 2,000-document repo across two
renames with heavy rewrites:

    git log --follow   ->   3 of 51 commits   (6% of the history)
    UUID scan          ->  51 of 51 commits   (100%, and recovered all four
                                               paths the document had occupied)

Rename detection is a HEURISTIC with a 50% default similarity threshold; the
actual similarity in that case was 20%. A document that is renamed and heavily
edited in the same commit loses its history, silently.

**Revised: identity splits into four questions that every system conflates.**

    which artifact is this?  minted UUID stored in the file (frontmatter `id:`)
    which version?           git blob SHA (free, never user-facing)
    which change?            a `change-id` commit header (jj's convention;
                             valid in plain git, survives clone/push/gc,
                             stripped by rebase/cherry-pick)
    what is it called/where? path and title -- mutable METADATA, not identity

Minted, not derived. Three systems converged on this independently: Perkeep's
permanode is "really just a signed random number"; Unison switched user-defined
types to `unique`, injecting a UUID into the content hash; Datomic's entity ids
are transactor-assigned and never change. Content addressing cannot identify a
MUTABLE thing — a document's hash changes every keystroke, which is precisely
why IPNS had to exist.

The cost at ARTIFACT level is one line per file, which is negligible. The cost
at BLOCK level is thousands of ids in the middle of prose, which is not the
same question and is still open.

## CORRECTION 6 — content-addressed canonical storage is a dead end, and four teams proved it

I entertained "content-addressed immutable objects canonical, git as transport"
as a serious candidate. Every serious team that built it left:

- **Unison** DELETED git support (issue #5013: continuing "would require
  re-implementing most git sync methods") and moved its codebase to SQLite
- **Tezos** started on `irmin-git` and left, for lmdb then leveldb then
  `irmin-pack`
- **bup** kept git's packfile format but had to add non-git midx/bloom indexes:
  "Git isn't actually designed to handle super-huge repositories... The problem
  is the packfile indexes"
- **Noms**' author concluded decentralised merge "wasn't that satisfying and we
  didn't take it any further", and built Replicache, "not decentralized"

Built and measured directly: 2.5x the `.git`, **4.5x the working tree**, 4x the
file count, `grep` returns hashes instead of names, and you inherit a second
garbage collector git cannot help with because every object is reachable from
HEAD. Nix's `ca-derivations` remains EXPERIMENTAL in August 2026, four and a
half years after RFC 62 merged — at a far better-resourced project.

Also: **rule out IPFS.** Interplanetary Shipyard was defunded by Protocol Labs
on 2026-08-24; Kubo, Helia and Boxo work ends 2026-09-30.

## CORRECTION 7 — jujutsu is a source of ideas, not a base, and it has a silent-wrong

Attractive: first-class conflicts, change ids, op log, auto-rebase. But
`.gitattributes` is unsupported (issue #53, open since 2022-01-22), so no merge
drivers and no per-type behaviour at all; `jj resolve --tool` is manual-only
with one global tool; `jj-lib` self-describes as experimental with
"backward-incompatible changes to the on-disk formats before 1.0.0"; no
FFI/wasm; no LFS; no hooks; no rename tracking; bus factor about two.

And a genuine hazard: **a conflicted jj commit exported to git writes side A
into the real path with no markers**, so a plain-git consumer reads an
unresolved conflict as clean content. That is a silent-wrong of exactly the
class this design exists to eliminate.

Take the `change-id` header — it costs nothing and GitHub preserves it (26 of
the 30 most recent jj-vcs/jj commits carry it through a plain `git clone`).
Leave the rest.

## VERIFIED — git's conflict markers are VALID MARKDOWN, and this is worse than it sounds

`experiments/V-markers/`. A conflicted markdown file rendered with pandoc:

    <<<<<<< HEAD
    Our version of the sentence.
    =======
    Their version of the sentence.
    >>>>>>> branch

renders as

    <h1>&lt;&lt;&lt;&lt;&lt;&lt;&lt; HEAD Our version of the sentence.</h1>
    <p>Their version of the sentence.</p>
    <blockquote><blockquote>... seven deep ...<p>branch</p></blockquote>

`=======` is a setext H1 underline; `>>>>>>>` is seven nested blockquotes. In a
live-preview editor a conflict displays as a HEADING followed by ordinary
prose. The user sees a slightly odd document, not a conflict.

**This inverts the usual intuition that plain text degrades more gracefully than
structured formats.** A conflicted JSON canvas throws a parse error — loud,
local, unmissable. A conflicted markdown document renders. Tolerance is a
liability at conflict time.

### The recommended mitigation does not work — tested

D2 recommends `*.md conflict-marker-size=32` and says ship it day one. I tested
it. It does not address this hazard at all:

    <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< HEAD
    Our version.
    ================================
    Their version.
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> branch

still renders as `<h1>` — a 32-character run of `=` is just as valid a setext
underline as a 7-character one — now followed by THIRTY-TWO nested blockquotes.

`conflict-marker-size` exists to avoid collisions with file content that
legitimately contains marker-like sequences. It does nothing about markdown's
willingness to render the markers as formatting.

### The honest resolution, which is not simply "-merge everything"

`-merge` is verified to work (`experiments/V-nomerge/`: file well-formed, zero
markers, all three versions in index stages 1/2/3). But it disables automatic
merging ENTIRELY for that path, and prose is the artifact type where line merge
most often succeeds and where collaboration is most frequent. Paying a conflict
on every concurrent paragraph edit to guard against a rarer hazard is a bad
trade.

So the rule differentiates by FAILURE MODE, not by format:

    Conflicted form fails LOUDLY in its own format
    (JSON, SVG, YAML, .fods -- they throw a parse error)
        -> normal merge is acceptable; the format polices itself

    Conflicted form renders as PLAUSIBLE CONTENT
    (markdown, CSV -- D3 found LibreOffice opens a conflicted CSV with no
     error dialog, rendering `=======` as Err:510)
        -> the tooling must police it, because the format will not

For markdown specifically: keep normal merge, and add two client-side checks —
refuse to RENDER a file containing markers (show the conflict UI instead), and
refuse to COMMIT one.

**State the residual risk plainly rather than papering over it:** those checks
are client-side, and git hooks are not cloned, so a foreign client can commit
an unresolved marker into a markdown file where it will render as a heading
forever. This is a real, unfixable-by-us hole in I6 for prose. It is the price
of markdown's tolerance, and it is one of the strongest arguments in favour of
a stricter syntax (djot's attribute-bearing grammar, or any format that would
reject the markers) for the document leg.

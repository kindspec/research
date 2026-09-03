# D9 — Git as a substrate: capability surface, breaking points, and whether the base is right

Research + empirical testing, 2026-08-28. Environment: **git 2.47.3**, Debian 13,
Linux 6.12. All transcripts reproduce from `experiments/D9-*/`.

This builds on prior measurements and does not repeat them. Established, not
re-derived: 100k markdown files is a non-issue (`git status` < 0.1 s); 12/12
concurrent pushes rejected for a second writer; 8/8 rebases conflicted; 8
concurrent `git add` → 1 succeeded, 7 died on `index.lock`; 21 revisions of a
2 MB image cost 20.6× a single copy; libgit2 and isomorphic-git implement
neither partial clone nor sparse checkout.

Numbers below came out of a command run here, or from a document I read. Claims
I could not verify are marked ⚠.

---

## 0. The verdict, up front

**A type-aware merge cannot be deployed through `.gitattributes`.** The
attribute that *selects* a driver is repo-tracked; the `merge.<name>.driver`
line that *defines* it is local config that is never cloned, never pushed, and
cannot be set from inside the repository. On a clone that lacks it, git does not
error — it silently falls back to line-based merge and writes `<<<<<<<` markers
into the file. For every format in this product (CSV, Markdown tables, `.fods`,
`.calc.md`) that is a **corrupt artifact**, produced silently, by a colleague
who did nothing wrong.

**But type-aware merge is deployable — as a service that owns the repository.**
`git merge-tree --write-tree` hands a bare repo the three conflict stages as
plain blobs. A server can read them, run any merge function it likes, and write
the result back with `hash-object` + `mktree` + `commit-tree` + `update-ref`,
with no working tree, no `.gitattributes`, and no client tooling. Demonstrated
end-to-end in §6. **The merge driver is the wrong deployment vector; the server
is the right one.** That is the same conclusion the concurrent-writer evidence
forces, arrived at independently — which is the strongest thing in this report.

---

## 1. The `.gitattributes` capability surface, precisely

`experiments/D9-gitattributes-surface/TRANSCRIPT-01-surface.txt`

The decisive distinction is not what a mechanism *does* but **where its
configuration lives**. Three tiers:

| Mechanism | What it does | Config lives in | Portable? | On a clone without the tooling |
|---|---|---|---|---|
| `text` / `-text` / `eol=` | line-ending normalisation | **`.gitattributes` only** | ✅ | works, core git implements it |
| `binary` (= `-diff -merge -text`) | refuse to diff/merge | **`.gitattributes` only** | ✅ | works — file kept verbatim, marked `UU` |
| `merge=union` | concatenate both sides | **`.gitattributes` only** | ✅ | works — and see the warning below |
| `export-subst`, `export-ignore` | rewrite/omit in `git archive` | **`.gitattributes` only** | ✅ | works, but **only affects `git archive`** |
| built-in `diff=<lang>` | hunk-header function names | **`.gitattributes` only** | ✅ | works (drivers compiled into git) |
| `diff=<d>` + `textconv` | diff a binary as text | **local `git config`** | ❌ | silent no-op — raw byte diff |
| `diff=<d>` + `wordRegex` | word-diff granularity | **local `git config`** | ❌ | silent no-op |
| **`merge=<d>` + `driver`** | **type-aware 3-way merge** | **local `git config`** | ❌ | **silent fallback to line merge + `<<<<<<<`** |
| `filter=<d>` clean/smudge | rewrite on stage/checkout | **local `git config`** | ❌ | **silent — unfiltered bytes enter history** |

### 1.1 The three config states a cloner can be in

Verified in `experiments/D3-merge-driver-deployment/TRANSCRIPT-03-config-states.txt`
and extended here:

1. **Nothing configured** (the default for anyone who did not install our tool):
   `git merge` → `CONFLICT (content)`, exit 1, `<<<<<<< HEAD` markers written
   into the file. **Fails open, silently, into corruption.**
2. **`merge.<d>.name` set but `driver` missing:** `fatal: custom merge driver
   probe lacks command line.` Hard failure — arguably the *best* outcome, and it
   is unreachable by accident.
3. **Driver declared, binary missing from PATH:** git prints the shell's
   `not found` to stderr, treats the nonzero exit as "conflict", and leaves the
   file at **ours, verbatim, no markers**, staged `UU`. Recoverable, but the
   error is one line in a wall of merge output.

### 1.2 `merge=union` is portable and dangerous

It is the only merge driver that ships in git and needs zero config, so it is
the only one that survives a naive clone. It also **never conflicts** — it
concatenates. On disjoint row inserts that is what you want:

```
name,qty     ours: apple,cherry        theirs: apple,banana
apple,1   ->   name,qty / apple,1 / cherry,3 / banana,2      (clean, correct)
```

On a **same-line** edit it is silently wrong:

```
ours:   total,300
theirs: total,200
union:  total,300
        total,200      <- two rows named 'total'. Valid CSV. Wrong data.
```

This is the same failure class as the 480-instead-of-660 A1-reference result in
prior work: *no marker anywhere*. `merge=union` is a portable footgun, not a
portable solution.

### 1.3 `binary` / `-merge` is the one portable safety net

`binary` is repo-portable, needs no config, and on conflict leaves the file at
**ours, byte-for-byte, with no markers**, staged `UU`:

```
warning: Cannot merge binary files: f.dat (HEAD vs. feat)
CONFLICT (content): Merge conflict in f.dat
$ cat f.dat        $ git status --short
a                  UU f.dat
M
z
```

**The artifact is never invalidated.** For a product whose formats stop parsing
the moment a marker lands in them, this is the single most valuable line
available in a `.gitattributes` file. It converts *silent corruption* into
*loud, well-formed refusal* — and unlike a custom driver, it works on every
clone on earth. It buys nothing toward *resolving* the merge; it only stops the
damage. That is still the right default.

### 1.4 `filter` fails open into history, not just the working tree

Worse than the merge case, because it writes bad *content*:

```
$ git cat-file -p HEAD:a.txt          # committed with the filter configured
value REDACTED here
# fresh clone, no filter config, colleague edits and commits:
$ git cat-file -p HEAD:a.txt
value SECRET here
value SECRET two                       # the clean filter never ran
```

`git status` reports **clean**. Nothing warns. `filter.<d>.required = true`
converts this into `fatal: a.txt: clean filter 'strip' failed` — but `required`
is itself local config, so the person who needs it is exactly the person who
does not have it. Any design that relies on a clean filter to normalise a format
(e.g. stripping `.fods` printer-name churn) must assume it will not run.

### 1.5 Which operations invoke a custom driver

From `experiments/D3-merge-driver-deployment/TRANSCRIPT-01-operations.txt` —
useful because a driver that runs in one operation and not another is a trap:

| Operation | Driver invoked? |
|---|---|
| `git merge` | ✅ |
| `git rebase` | ✅ (note: **ours/theirs are swapped**) |
| `git cherry-pick` | ✅ |
| `git revert` | ✅ |
| `git stash pop` | ✅ |
| `git pull --rebase` | ✅ |
| `git am` / 3-way `git apply` | ✅ |
| `git merge-tree --write-tree` | ✅ — **but only in a non-bare repo** (§2) |
| `git merge-file` | ❌ plumbing, never consults attributes |
| `git checkout -m` / `restore --merge` | ❌ |

The rebase swap is a real hazard: a driver written assuming "ours = the local
user" silently inverts its bias under `pull --rebase`, which is the most common
sync operation in a desktop sync loop.

---

## 2. The bare-repo trap: even portable attributes die server-side

`experiments/D9-bare-attrs/TRANSCRIPT-bare-attrs.txt` — **this is new and it is
the sharpest single result in this report.**

A forge has a **bare** repository: no working tree, and (per `gitattributes(5)`)
*"when the `.gitattributes` file is missing from the work tree, the path in the
index is used as a fall-back"* — a bare repo has neither. So the `.gitattributes`
**sitting in the merged tree is not consulted at all.**

Same three files, same objects, `merge=union` / `binary` / `merge=probe`:

```
### 1. NON-BARE (developer laptop): git merge-tree --write-tree
  conflicts: b.csv, p.csv        # u.csv merged cleanly via union  ✅

### 2. BARE repo (a forge). Same objects. .gitattributes IS in the tree.
  .gitattributes in HEAD tree:
      u.csv merge=union
      b.csv binary
      p.csv merge=probe
  conflicts: b.csv, p.csv, u.csv        # ALL THREE

  -- u.csv (merge=union) --      -- b.csv (binary!) --
  <<<<<<< main                   <<<<<<< main
  total,300                      total,300
  =======                        =======
  total,200                      total,200
  >>>>>>> feat                   >>>>>>> feat
```

**A forge merging in a bare repo writes conflict markers into a file the
repository explicitly declared `binary`.** Every portable protection in §1
evaporates at exactly the layer that matters.

The fix exists and is one config line — `attr.tree` (git 2.40+): *"A reference
to a tree in the repository from which to read attributes, instead of the
`.gitattributes` file in the working tree."*

```
### 3. same bare repo, with attr.tree=HEAD
  conflicts: b.csv, p.csv       # union works again
  -- u.csv --  total,300 / total,200        (union)
  -- b.csv --  total,300                    (ours verbatim, no markers)
```

`$GIT_DIR/info/attributes` on the server works identically. **Nothing in the
repository can cause either to be set.** It is a server-operator action.

### 2.1 What the forges actually do

Corroborated independently by documentation review:

| Forge | Merge mechanism | `merge=union`, `binary` | Custom driver |
|---|---|---|---|
| **GitHub** | undocumented, likely libgit2 | **no evidence it works**; open request since ~2016 | **no** |
| **GitLab.com** | Gitaly, bare `git merge-tree --write-tree`, **no working tree** | yes — *only because* Gitaly scopes `attr.tree` | **no — documented** |
| **GitLab self-managed** | same | yes | yes, if an admin writes it into `gitaly.toml` |
| **Gitea / Forgejo** | real `git merge` in a **temp non-bare worktree** | yes, automatically | yes, if an admin edits the server's `data/home` gitconfig |

Three citations do the work:

- GitHub Support, verbatim: *"GitHub doesn't consider user-defined
  .gitattributes files (normally, we use our own .gitattributes file which you
  can't change) … The only workaround I could suggest is to merge pull requests
  in your local clone (and not via the web UI)."*
  <https://github.com/olivierlacan/keep-a-changelog/issues/56#issuecomment-350291283>
  Still-open request: <https://github.com/orgs/community/discussions/9288>
- GitLab docs, verbatim: *"Custom merge drivers are not supported on
  GitLab.com."* Self-managed config is `gitaly['configuration'] = { git: {
  config: [{ key: "merge.foo.driver", value: "true" }] } }` — i.e. exactly the
  local-config mechanism, hoisted to the server process.
  <https://docs.gitlab.com/user/project/repository/files/git_attributes/>
- Gitaly issue #6064: reading `HEAD:.gitattributes` in bare repos caused a git
  performance regression, so GitLab set **`attr.tree=empty_tree` globally** and
  re-enabled `attr.tree=HEAD` only for `git-diff`, `git-merge`, `git-check-attr`,
  `git-archive`, `git-worktree`. Issue #6193, *"GitLab.com ignores merge=union
  in .gitattributes"* (opened and fixed the same day, July 2024), is proof that
  even the **built-in, config-free** driver is one config regression away from
  silently vanishing on the largest self-hosted forge.
  <https://gitlab.com/gitlab-org/gitaly/-/issues/6064> ·
  <https://gitlab.com/gitlab-org/gitaly/-/issues/6193>

Gitea is the outlier and the reason to keep `binary` in `.gitattributes`
regardless: because it merges in a real worktree
(`services/pull/merge_merge.go` runs `git merge --no-ff --no-commit`), the
portable attributes work there for free. Its *mergeability check*
(`modules/git/merge_tree.go`) uses bare `merge-tree` with no `--attr-source`,
so the check and the merge can disagree.

And `gitattributes(5)` says the quiet part itself:

> *"The definition of a merge driver is done in the `.git/config` file, not in
> the gitattributes file, so strictly speaking this manual page is a wrong place
> to talk about it. However…"*

### 2.2 Conclusion on the deployment question

> **A `.gitattributes` merge driver runs only on a machine whose operator
> installed the tool AND edited local git config.** It does not run for a
> colleague who clones. It does not run on GitHub at all. It does not run on
> GitLab.com. It runs on GitLab self-managed and Gitea only if a server admin
> hand-edits server config. Any architecture in which correctness depends on a
> custom merge driver is **fiction outside our own client** — and worse than
> fiction, because it fails *open* into silently invalid documents rather than
> refusing.

The salvageable part of `.gitattributes` is exactly two lines:

```
*.csv     binary        # never let a marker into a parseable artifact
*.fods    binary
```

plus `text eol=lf` hygiene. Everything else must be enforced somewhere a
non-participant cannot opt out of — which means the server.

---

## 3. Git notes, ref namespaces, and conflicts-as-data

`experiments/D9-notes-refs/TRANSCRIPT-notes-refs.txt`,
`TRANSCRIPT-notes-conflict.txt`

The proposal: store a merge conflict as **structured data beside the artifact**
instead of `<<<<<<<` inside it. Do git refs/notes make a good home?

### 3.1 Nothing outside `refs/heads/*` moves by default

```
-- local refs before push --                 -- refs that landed on the SERVER --
  refs/bugs/abc123                             refs/heads/main
  refs/gws/conflicts/0001                    -- refs in a fresh clone --
  refs/heads/main                              refs/heads/main
  refs/notes/commits                           refs/remotes/origin/HEAD
                                               refs/remotes/origin/main
$ git notes show HEAD
error: no note found for object 1a23056c...
```

Explicit refspecs work in both directions (`git push origin
'refs/notes/*:refs/notes/*'` etc.), and a server that already holds them still
does not hand them to a default clone. **Every participant must configure a
custom refspec.** That is the same failure class as §1: repo-invisible local
config, opt-in per clone, silently absent otherwise. It is survivable *if the
only participant that must see the data is our own client or our own server*,
and fatal if a plain `git clone` is supposed to carry it.

### 3.2 `git notes merge` has no type-aware option and needs a worktree

Strategies are `manual` (default), `ours`, `theirs`, `union`, `cat_sort_uniq`.
That is the whole list — a *line*-oriented set, for a structured-data use case.
On a genuine divergence the default writes markers into the note:

```
$ git notes merge refs/notes/theirs
Automatic notes merge failed. Fix conflicts in .git/NOTES_MERGE_WORKTREE ...
CONFLICT (content): Merge conflict in notes for object 2ac6f8ec...

$ cat .git/NOTES_MERGE_WORKTREE/2ac6f8ec...
<<<<<<< refs/notes/commits
OURS note
=======
THEIRS note
>>>>>>> refs/notes/theirs
```

**Notes reproduce the exact problem they were being considered to solve.** And
`--abort`/`--commit` drive a scratch worktree at `.git/NOTES_MERGE_WORKTREE`,
which a bare server repo has no business creating (it does create it — I ran it
in a bare repo and got the same conflict state — but it is not a server-shaped
API).

### 3.3 Notes evaporate under history rewriting

```
$ git config notes.rewriteRef      # UNSET
$ git commit --amend -m 'two amended'
$ git notes show HEAD
error: no note found for object 1ea6bebe...
```

`git-config(1)`, verbatim: *"notes.rewriteRef … **Does not have a default value;
you must configure this variable to enable note rewriting.** Set it to
`refs/notes/commits` to enable rewriting for the default commit notes."*

With it set, the note survives the amend. So notes attached to commits are lost
by default across `--amend` and `rebase` — and any editor doing autosave-squash
rewrites constantly.

### 3.4 A ref-based op-log is cheap, though

1,000 tiny mutations appended as commits on `refs/gws/oplog`:

```
1000 ops appended in 7149 ms      (≈140 ops/sec via fork-per-op shelling)
loose objects: 3003               du .git: 13M
after git gc:                     du .git: 532K
git rev-list refs/gws/oplog:      4 ms
```

532 KB for 1,000 operations (~545 bytes/op amortised) and a 4 ms full replay.
The *storage* is fine. The 140 ops/sec is an artefact of three `git` forks per
op, not of git — an in-process writer would be orders faster. What is not fine
is that git gives you no merge semantics for it: `git-bug`, the most serious
attempt at this, had to build its own.

### 3.5 git-bug: the honest precedent

`git-bug` (<https://github.com/git-bug/git-bug>, 10,018★) stores each entity as a
**chain of commits under `refs/bugs/<id>`**; each edit session serialises an
`OperationPack` JSON blob into a tree under `/ops`, with attachments under
`/media` and Lamport-clock values encoded as **zero-length blobs named by tree
entry** (e.g. `edit-clock-154`) so clock data costs no transfer. An entity's ID
is the hash of its first operation. Design doc:
<https://github.com/git-bug/git-bug/blob/trunk/doc/design/data-model.md>

Its merge (`entity/dag/entity_actions.go`) has five cases; the interesting one is
"both sides advanced", where it **writes a merge commit with an empty
OperationPack** and orders operations deterministically by Lamport clock, tie-broken
lexicographically on OperationPack id. **There is no conflict state and no
resolution UI.** Concurrent `SetTitle`s both apply, in the same order everywhere,
and the loser is silently discarded.

**This is the load-bearing observation for the conflicts-as-data proposal.** The
most serious prior art in mutable-state-in-git *avoided representing conflicts
altogether* rather than encoding them as first-class objects. That is a gap, not
a solved problem — and git-bug's operations are commutative-ish metadata (title,
labels, comments), which is a far easier domain than a spreadsheet cell.

Adoption is a caution, not an endorsement: releases ran 2018–2022, then **a
~2.5-year gap** (v0.8.0 2022-11-20 → v0.9.0 2025-05-12), three releases in one
week, and **none since** (v0.10.1, still current Aug 2026) despite active
commits. The current maintainer's own "vision" discussion is unusually candid:
*"many users regularly face challenges adopting git-bug for technical reasons,
be it due to a poor user experience, or encountering errors performing what
should be trivial tasks… I want to make git-bug a viable alternative"* —
phrasing that concedes it is not one yet.
<https://github.com/git-bug/git-bug/discussions/1391>

Neighbours: **git-appraise** (Google; review data in notes refs) — 5,309★,
**last push 2023-08-12, dead** (<https://github.com/google/git-appraise>).
**git-dit** — 463★, last push 2025-06-02, low activity.
**ticgit** — 267★, **last push 2014**. **git-issue** — 883★, active, but it
stores issues as *files in the working tree*, not refs.
**Fossil** is the instructive contrast: the one tool that ships issues and wiki
natively still syncs **immutable content-addressed artifacts**, with SQLite as a
rebuildable local cache (`fossil rebuild`), not as the sync payload.
<https://fossil-scm.org/home/doc/trunk/www/theory1.wiki>

### 3.6 Verdict on conflicts-as-data in git

**Yes for storage, no for distribution, and irrelevant for merge.**

- Git objects are a fine content-addressed store for conflict records: 545
  bytes/op, 4 ms replay, and `git gc` compresses well.
- Custom refs are the right *shape* (server-owned, invisible to the working
  tree, cheap to enumerate) and the wrong *distribution mechanism* (no default
  refspec; no forge UI; `git-bug` needed a whole REST "bridge" to get its data
  visible on GitHub at all).
- Notes are strictly worse than a custom ref: same distribution problem, plus a
  worktree-based merge, plus silent loss under `--amend` unless
  `notes.rewriteRef` is set locally.

If our server owns the repository (§5), the conflict record can live in
`refs/gws/*` and everything above is a non-issue, because the only readers are
our server and our client. If the design requires a plain `git clone` to carry
conflict records to a third party, it does not work.

---

## 4. Scale, beyond file count

`experiments/D9-scale-history/TRANSCRIPT-scale.txt`, `TRANSCRIPT-scale-deep.txt`

Prior work established 100k files at one commit is free. The document-app shape
is different: **moderate file count, deep history, many revisions per file.**

### 4.1 Repo A — 2,000 docs × 1,001 commits (20,000 file revisions)

```
.git loose: 234M   ->  packed: 17M   (packfile 15M, worktree 24M)
git log -- one file (12 revisions)      85 ms
git log --follow -- one file            84 ms
git blame one file                      61 ms
git clone (local, full)               1024 ms  -> 16M
git clone --depth=1                    459 ms  -> 13M
```

Loose-vs-packed is 13.8×. **Auto-`gc` is not optional in an autosave-per-commit
product** — an app committing every save accumulates loose objects at exactly the
rate that makes this ratio bite.

### 4.2 Repo B — 200 docs × 50,001 commits

```
=== 50,001 commits, 200 files, pack 17M, 243 revisions of docs/d7.md ===
                                     no graph    with commit-graph + midx
git rev-list --count HEAD               154 ms          17 ms     (9.1x)
git log --oneline -- ONE FILE           940 ms         841 ms     (1.1x)
git log --follow -- ONE FILE            959 ms         827 ms     (1.2x)
git blame ONE FILE                      984 ms         836 ms     (1.2x)
git checkout HEAD~49000 (distant)       169 ms          28 ms     (6.0x)
git log --oneline -1000                   8 ms
commit-graph write --reachable          204 ms  (2.9M)
multi-pack-index write                   40 ms  (5.4M)
git clone (full)                       2164 ms  -> 23M
git clone --depth=1                      25 ms  -> 220K     (104x smaller)
```

**The finding that matters: "history of this file" costs O(total commits), not
O(revisions of this file), and commit-graph barely helps.** 940 ms to find 243
revisions among 50,001 commits, because the walk is a *tree-diff* per commit and
commit-graph only accelerates the *commit* walk. Confirmed by bounding the walk:

```
walk   1000 commits ->  235 revisions of the file :  789 ms
walk   5000 commits ->  213 revisions              :  720 ms
walk  10000 commits ->  189 revisions              :  644 ms
walk  25000 commits ->  133 revisions              :  417 ms
```

Cost tracks *commits traversed*, not results returned. A document app that shows
a per-file version list on open, in a repo with a year of autosave commits, is
looking at a **linear-in-repo-history** operation on its hot path. Extrapolating
the 50k figure: ~1.9 s at 100k commits, ~9 s at 500k. This is the scaling wall,
and it is not the one prior work found.

The mitigation is not a git flag. It is an **index** — the same conclusion
already reached for search (SQLite FTS5, gitignored). File-history and blame
must be served from a derived index the server maintains incrementally, with git
as the durable store behind it.

### 4.3 The large-repo toolkit, honestly assessed

- **commit-graph**: real, cheap (204 ms to write, 2.9 MB), 6–9× on commit walks,
  ~1.1× on the operations we actually need. Write it; don't expect it to save
  file history.
- **multi-pack-index**: 40 ms, 5.4 MB, no measurable effect at this scale.
- **`feature.manyFiles`** (implies `index.version=4`, `core.untrackedCache`,
  `index.skipHash`): `git status` was 4 ms before and after. Nothing to win —
  consistent with prior work finding file count is a non-issue.
- **`core.fsmonitor`**: `fatal: fsmonitor--daemon not supported on this
  platform`. **The built-in daemon is Windows/macOS only.** On Linux servers it
  is unavailable, so a server-side design cannot count on it.
- **sparse-index / sparse-checkout**: works with `--cone --sparse-index`. But
  prior work already established libgit2 and isomorphic-git support neither, so
  it is unavailable in exactly the mobile/browser context that needs it.
- **`scalar`**: present at `/usr/bin/scalar` as a first-class binary (not a git
  subcommand). It is a *configuration bundle plus background maintenance* —
  `scalar run (config|commit-graph|fetch|loose-objects|pack-files)` mostly hands
  off to `git maintenance`. Useful operationally; it invents no capability.
- **Partial clone**: worth stating carefully, because the naive result is
  misleading. On the deep repo `--filter=blob:none` / `--filter=tree:0` gave
  **no win** (16M vs 16M), matching prior work's 22M-vs-22M. A controlled test
  isolates why (`D9-scale-history/pc`, `uploadpack.allowFilter=true`):

  ```
  # 300 markdown docs, 31 commits, HIGHLY deltifiable text (src .git = 216K)
  clone (full)                 -> .git 228K
  clone --filter=blob:none     -> .git 240K     <- LARGER
  clone --filter=tree:0        -> .git 236K     <- LARGER

  # 200 docs of incompressible random text (src .git = 8.7M)
  clone (full)                 -> .git 8.7M
  clone --filter=blob:none     -> .git 2.4M     (3.6x)
  clone --depth=1              -> .git 2.4M     (3.6x)
  clone --filter=blob:none --no-checkout -> .git 220K   (40x)
  ```

  **Blob filtering makes a prose repository *bigger*.** Filtering breaks the
  delta chains that make git's packing efficient for text, so the server must
  send whole objects. It only pays when content does not delta — images,
  attachments — which is exactly the content prior work already decided to move
  to a CAS with pointers. And `--no-checkout` shows where the real 40× lives:
  in *not materialising files*, at the cost of a network round trip per file
  open.

  It also **fails open**. With `uploadpack.allowFilter` unset on the server:

  ```
  warning: filtering not recognized by server, ignoring
  -> .git 232K   promisor=true
  ```

  A full clone, a one-line warning, and `remote.origin.promisor=true` set
  anyway — so the client believes it is partial when it is not.

  `--depth=1` gave **104×** on the 50k-commit repo (23M → 220K). Shallow, not
  filtered, is what actually pays for text, and it forfeits history.

### 4.4 "Who wrote this paragraph" — `git blame` on reflowed prose

`experiments/D9-blame-prose/TRANSCRIPT-blame-prose.txt`

Alice authors a hard-wrapped document. Dave changes **one word** in Bob's
paragraph, and his editor rewraps 72→80 columns:

```
^1cbc43c (Alice  1) # The Report
^1cbc43c (Alice  2)
b99781d8 (Dave   3) Alice wrote this opening sentence about the quarterly results and it runs across
b99781d8 (Dave   4) two wrapped lines because the file is hard wrapped.
^1cbc43c (Alice  5)
b99781d8 (Dave   6) Bob added this second paragraph concerning the logistics network, which also
b99781d8 (Dave   7) happens to wrap onto a second physical line of the source file.
^1cbc43c (Alice  8)
b99781d8 (Dave   9) Carol contributed the closing paragraph summarising the outlook for the coming
b99781d8 (Dave  10) year and the risks that the board should be aware of now.

  4 author Alice          6 author Dave
```

**Dave is credited with 6 of 10 lines including two paragraphs he never
touched.** `git show --numstat` reports `6 6` for a one-word edit.

Neither escape hatch works:

```
-- does -w (ignore whitespace) rescue it?      4 Alice / 6 Dave
-- does -w -M -C -C -C rescue it?              4 Alice / 6 Dave
```

`-w` cannot help because rewrapping moves *words across line boundaries*, so no
pair of lines is whitespace-equivalent. `-M -C -C -C` looks for moved/copied
*lines*, and no line survived intact.

Control, same one-word edit with one-sentence-per-line and no rewrap:

```
^803c7fe (Alice 3) Alice paragraph one.
fee198c7 (Dave  5) Bob paragraph about the logistics network.
^803c7fe (Alice 7) Carol paragraph three.
numstat: 1 1
```

**Correct attribution, 1 line changed.** So the conclusion is not "blame is
useless for prose" — it is **"blame is useless for prose in a hard-wrapped
file, and correct in a semantically-line-broken one."** That is a *format*
decision (never hard-wrap; one block or one sentence per line) with a direct,
measurable payoff on both blame and diff, and it costs nothing. It also aligns
with the already-settled CodeMirror-over-raw-markdown editor decision: the
editor must soft-wrap for display and never rewrap the buffer.

Even so, blame remains **line**-attribution, not **authorship**. It cannot
answer "who wrote this sentence" after any edit that touches the line, and at
50k commits it costs ~840 ms. Real paragraph provenance needs the same derived
index as §4.2.

---

## 5. The concurrent-writer problem — measured solutions

`experiments/D9-worktree-concurrency/TRANSCRIPT-worktree.txt`

Prior work diagnosed the problem. This decomposes it, and the decomposition is
actionable: **git has three storage layers with three different concurrency
properties.**

```
### TEST 4: 64 concurrent workers, 1280 objects via git hash-object -w
workers OK: 64/64, 1280 objects in 326 ms
objects on disk: 1280      errors: 0      fsck: clean
>> the OBJECT store is concurrency-safe (content-addressed, temp+rename).

### TEST 3: 16 concurrent writers sharing ONE worktree/index (the naive server)
git add succeeded: 6 / 16
  10 index.lock / 10 Unable to create / 10 File exists

### TEST 1: 16 concurrent commits, each in its OWN linked worktree + own branch
succeeded: 16 / 16      errors: (none)

### TEST 2: 16 concurrent commits all targeting the SAME branch ref (CAS)
succeeded: 3 / 16
  fatal: cannot lock ref 'refs/heads/main': is at 8ee4707... but expected 9aa5b00...
```

| Layer | Concurrency | Why |
|---|---|---|
| **Object store** | ✅ safe, unlimited | content-addressed; write-temp-then-rename; identical content is identical filename |
| **Index** | ❌ one writer per index file | `index.lock` is `O_EXCL` |
| **Refs** | ❌ one writer per ref | lock file + compare-and-swap |

**`git worktree` genuinely solves the index half.** Each linked worktree gets
its own index at `.git/worktrees/<name>/index`, so 16 concurrent commits on 16
branches over one object store went **16/16 with zero errors**, where the
shared-index version went 6/16. Concurrent `git worktree add` was also 16/16.
The cost is disk: 16 worktrees of a *trivial* repo cost 11 MB, and a worktree is
a full checkout of its branch.

**What worktrees do not solve is the ref**, and the ref is the real constraint.
16 writers doing compare-and-swap on `refs/heads/main` → 3 winners. That number
is not a bug; it is the definition of a serialisable register. Any design where
N users write one branch has a throughput ceiling of one successful update per
round-trip, and retries that must re-merge.

This yields the architecture directly, and it is not "avoid concurrency" — it is
**move the serialisation point off the client**:

1. **One server process owns each repository.** It is the only holder of the ref
   lock, so CAS contention becomes an in-process queue instead of 12/12 rejected
   pushes. This is what Gitaly is (§2.1: an RPC service that owns the repo and
   was built precisely because Rails workers sharing repos over NFS did not
   work).
2. **Per-session worktrees, or better, no worktree at all.** The server-side
   merge in §6 never checks anything out — it reads blobs and writes trees.
   Worktrees are the fallback for operations that genuinely need a filesystem.
3. **The object store is a free lunch.** Content can be written concurrently, at
   scale, from many processes, safely. Ingest can be fully parallel; only the
   final ref update is serialised. 64 workers, 1,280 objects, 326 ms, `fsck`
   clean.
4. **Clients never push to a shared branch.** They submit ops to the server, or
   push to a per-client ref that the server integrates. The 8/8-rebases-conflict
   result is what happens when clients are allowed to race on one branch.

### 5.1 Reftable does not buy concurrency — it buys ref storage

`experiments/D9-worktree-concurrency/TRANSCRIPT-reftable.txt`

Gerrit drove reftable's development because loose-ref + `packed-refs` does not
scale with many refs, and a conflicts-as-data design (§3) creates a lot of refs.
So: does the reftable backend (git 2.45+, `git init --ref-format=reftable`)
relax the write constraint? Measured, both backends, same machine, git 2.47.3:

```
                                            files       reftable
(a) 16 concurrent CAS on ONE ref            3/16          3/16
(b) 16 concurrent writes to 16 refs        16/16         16/16
(c) 20,000 refs created (100/txn)         27,329 ms     28,380 ms
    refs storage size                        79 M         548 K     <- 147x
    for-each-ref over 20k refs               400 ms        248 ms
    one more ref update at 20k refs            2 ms          2 ms
```

**Unambiguous: reftable changes nothing about write concurrency.** 3 of 16 CAS
writers win under both backends, because the constraint is the semantics of
compare-and-swap on a single register, not the storage format.

What it does buy is **147× on ref storage** (79 MB → 548 KB for 20,000 refs) and
~1.6× on enumeration. That matters directly for §3.6: if conflict records live
one-per-ref under `refs/gws/*`, the `files` backend costs ~4 KB per ref in loose
files, and 20,000 of them is 79 MB of tiny files. Under reftable it is 548 KB.
**If the design puts many records in refs, it must use reftable** — or batch
them into a single ref's commit chain, as `git-bug` does (§3.5).

Note also (c): 20,000 refs took ~27 s to create even batched 100 per
transaction, on both backends. Ref creation is not a hot path you can treat as
free.

**Git's own reftable spec says it outright**, which is the cleanest possible
confirmation of the measurement above:

> *"Because a single `tables.list.lock` file is used to manage locking, the
> repository is single-threaded for writers. Application servers wrapped around
> repositories (e.g. Gerrit Code Review) can layer their own lock/wait queue to
> improve fairness to writers."*
> — <https://github.com/git/git/blob/master/Documentation/technical/reftable.adoc>

Note the second sentence. Git's own designers state the remedy: **an
application server in front of the repository, with its own queue.** That is
not a workaround; it is the documented intended architecture.

### 5.2 How production systems actually do it

Documentation review. The evidence converges, with one instructive dissent.

**GitLab / Gitaly — the strongest case, and it is a post-mortem.** GitLab ran
repositories on NFS shared across Rails workers, and it broke in exactly the
place this report has been poking. Their engineering write-up,
*"How we spent two weeks hunting an NFS bug in the Linux kernel"* (Nov 2018),
traces the failure to `git gc`'s `packed-refs.lock` → rename → unlock sequence —
**the very mechanism git uses to serialise ref writes** — because NFS does not
give the rename atomicity local disk does; a second node reading `packed-refs`
mid-rename got `Stale file handle`. Verbatim conclusion:

> *"While we have run NFS on GitLab.com for many years, we have stopped using it
> to access repository data across our application machines. Instead, we have
> abstracted all Git calls to Gitaly."*
> <https://about.gitlab.com/blog/2018/11/14/how-we-spent-two-weeks-hunting-an-nfs-bug/>

Today NFS is not merely discouraged but unsupported: *"For repository data, only
local storage is supported for Gitaly and Gitaly Cluster (Praefect)…
Alternatives such as NFS or cloud-based file systems are not supported."*
<https://docs.gitlab.com/ee/administration/gitaly/>

Praefect coordinates cluster-level writes with a `VoteTransaction` RPC
(`strong` / `primary-wins` / `majority-wins`), and Gitaly bounds in-flight work
per repository with `max_per_repo` plus an AIMD adaptive limiter. ⚠ Note the
limit of the evidence: `max_per_repo` is *admission control*, and the docs do
not state that two mutating RPCs can never be in flight against one repo — the
actual ref serialisation still falls through to git's own lock files. The
defensible claim is therefore narrower than "one process owns the repo": Gitaly
**eliminated the shared-filesystem-across-independent-processes topology**,
which is what breaks git's locking.

**Gitea/Forgejo — they built the queue git's spec recommends.**
`modules/globallock/globallock.go` is an explicit lock abstraction: an
in-process `sync.Mutex` locker by default, **with a Redis-backed distributed
locker** for horizontally-scaled deployments — proof they hit this across app
instances, not merely across goroutines. It is used from `services/pull/`
(`merge.go`, `update.go`, `check.go`) as
`globallock.LockAndDo(ctx, getPullWorkingLockKey(pr.ID), …)` — a per-PR lock
around the shared temp working tree.
<https://github.com/go-gitea/gitea/blob/main/modules/globallock/globallock.go>

It still leaks the failures measured in §5. Open/real issues: *"Many lock file
exists errors"* (<https://github.com/go-gitea/gitea/issues/29673>),
*"commit-graph-chain.lock exists"* (#33239), *"branch lock file exists after
push timeout"* (#34546, open), *"stuck in Merge conflict checking is in
progress"* (#22578). **The forge whose entire product is git has a standing bug
class from git's lock files.**

**GitHub Spokes — the instructive dissent.** DGit keeps three replicas;
*"Writes are synchronously streamed to all three replicas and are only committed
if at least two replicas confirm success"*, and DGit *"must implement its own
serializability, locking, failure detection, and resynchronization."*
<https://github.blog/2016-04-05-introducing-dgit/> The follow-up is sharper:

> *"Spokes simply skips that step and treats every write as an election —
> selecting a winning order and outcome directly, rather than a winning server
> that dictates the write order."* … *"The way Spokes serializes writes is by
> ensuring that every write acquires an exclusive lock on a majority of
> replicas… It's impossible for two writes to acquire a majority at the same
> time, so Spokes eliminates conflicts by eliminating concurrent writes
> entirely."*
> <https://github.blog/2016-09-07-building-resilience-in-spokes/>

**This explicitly rejects a fixed owning process.** GitHub chose an ephemeral
per-write majority election over a standing leader. So the correct statement of
the hypothesis is not *"one process must own the repo"* — it is:

> **Writes to a repository must be totally ordered by something other than the
> filesystem.** Whether that something is a standing owner (Gitaly, Gitea's
> lock) or a per-write election (Spokes) is an availability decision, not a
> correctness one. Every production system serialises; none permits genuinely
> concurrent writers.

**Figma is the same shape outside git:** *"Our servers currently spin up a
separate process for each multiplayer document which everyone editing that
document connects to."*
<https://www.figma.com/blog/how-figmas-multiplayer-technology-works/>

### 5.3 The recommendation

For a product with tens of writers per repository, not thousands, the
availability argument for Spokes-style election does not apply and the standing
owner is simpler:

1. **One server process owns each repository at a time**, holding a per-repo
   queue — literally what git's reftable spec advises and what Gitea's
   `globallock` implements. Ref CAS contention becomes an in-process queue
   rather than 12/12 rejected pushes.
2. **Local disk only.** Not NFS, not EFS, not a cloud filesystem. GitLab's
   two-week kernel hunt is the receipt, and their docs now say *unsupported*.
3. **Parallelise ingest, serialise only the ref update.** Object writes are safe
   at 64 concurrent workers (§5); merges via `merge-tree` need no worktree (§6).
   Only `update-ref` is a critical section, and it is microseconds.
4. **Use the reftable backend** if conflict records live one-per-ref (§5.1) —
   147× on storage, nothing on concurrency, and no illusions about the latter.
5. **Clients never push to a shared branch.** They submit to the server, or push
   to a per-client ref the server integrates. The prior 8/8-rebases-conflict
   result is what happens when clients race on one branch.
6. **Per-session worktrees only where a filesystem is genuinely required** —
   16/16 concurrent commits vs 6/16 on a shared index (§5), at ~1 checkout of
   disk each.

---

## 6. The constructive result: server-side type-aware merge, no drivers

`experiments/D9-server-side-merge/TRANSCRIPT-server-merge.txt`

Given §2 (drivers don't deploy) and §5 (a server must own the repo anyway), the
merge belongs on the server. It is entirely mechanical.

Alice edits `apple` **qty** 1→5. Bob edits `apple` **price** 10→99. Same line.
Stock git conflicts, because git's unit is a line.

**Step 1** — on the bare server, `merge-tree` hands over the three stages:

```
$ git merge-tree --write-tree main alice ; echo exit=$?
ee22d3cb8e066325de2963d991b8a460afcece44
100644 bdb812c4... 1  s.csv        <- base
100644 389cee0d... 2  s.csv        <- ours
100644 a600084d... 3  s.csv        <- theirs
Auto-merging s.csv
CONFLICT (content): Merge conflict in s.csv
exit=1
```

All three are readable with `git cat-file -p` in a bare repo. No working tree.

**Step 2** — the server runs its own cell-level 3-way merge (60 lines of
Python here; `daff` in production, which prior work already validated on every
case tested):

```
item,qty,price
apple,5,99          <- both edits applied
banana,2,20
cherry,3,30
residual cell conflicts: []
```

**Step 3** — write it back with pure plumbing, no checkout:

```
NEWBLOB=$(printf '%s\n' "$MERGED" | git hash-object -w --stdin)
NEWTREE=$(git ls-tree main | sed 's|...s.csv|'$NEWBLOB' s.csv|' | git mktree)
COMMIT=$(git commit-tree "$NEWTREE" -p main -p alice -m "...")
git update-ref refs/heads/main "$COMMIT" "$OLD"      # CAS
```

**Step 4** — a plain `git clone` by someone with no tooling whatsoever:

```
git version 2.47.3
-- s.csv --                          parses as CSV: 4 rows, 3 cols
item,qty,price                       -- .gitattributes present? --
apple,5,99                              No such file or directory
banana,2,20                          -- local merge driver config? --
cherry,3,30                             (none)
```

**The type-aware merge ran with zero client tooling, zero `.gitattributes`, and
zero local git config.** The commit is an ordinary two-parent merge; `git log
--graph` renders it normally; GitHub would display it normally.

Three properties follow, and they are the design:

- **Deployability is decoupled from the client.** Everyone with `git` gets the
  benefit; nobody needs our tool.
- **Residual conflicts are already structured.** The merge function returns
  `(cell, column, base, ours, theirs)` tuples. Nothing forces them into the
  file. They go in `refs/gws/conflicts/*` (§3.6) and the artifact stays valid —
  which is precisely the conflicts-as-data proposal, made deployable by moving
  it server-side.
- **`binary` in `.gitattributes` remains the client-side backstop** for the case
  where a user merges locally anyway. It cannot fix the merge, but it guarantees
  the file is never invalidated.

### 6.1 Conflicts as data, end to end

`experiments/D9-conflicts-as-data/TRANSCRIPT-conflicts-as-data.txt`

First, the client-side backstop, measured on a real conflict in a CSV:

```
--- [(no attribute)] ---
    file: item,qty|<<<<<<< HEAD|apple,3|=======|apple,2|>>>>>>> f|
    parses as CSV? MALFORMED (ragged: [1, 2])      status: UU s.csv
--- [s.csv -merge] ---
    file: item,qty|apple,3|
    parses as CSV? YES                             status: UU s.csv
--- [s.csv binary] ---
    file: item,qty|apple,3|
    parses as CSV? YES                             status: UU s.csv
```

`-merge` and `binary` are equivalent for this purpose and both keep the file
**parseable while conflicted**, still flagged `UU`. The default gives a ragged,
unparseable file. This is the entire justification for those two lines of
`.gitattributes`.

Then the server path, on a genuinely unresolvable cell (alice `10→55`, bob
`10→99`). The server keeps ours in the artifact and records the conflict beside
it:

```
recorded: refs/gws/conflicts/s.csv/apple/price
{"path":"s.csv","row":"apple","column":"price",
 "base":"10","ours":"99","theirs":"55",
 "base_blob":"df2bbae9...","ours_blob":"9b1b823f...","theirs_blob":"14653d03..."}
```

A plain clone sees a **valid** document and nothing else:

```
-- s.csv --                        -- refs the plain clone received --
item,qty,price                        refs/heads/main
apple,1,99
parses as CSV: 2 rows x 3 cols -> VALID
```

Our client fetches `refs/gws/*` explicitly and gets the conflict as structured
data it can render as UI — a two-way cell picker — instead of asking a
non-technical user to edit `<<<<<<<` markers out of a spreadsheet.

The blob SHAs in the record matter: they pin the exact base/ours/theirs content
in the object store, so the conflict stays resolvable indefinitely even after
the branches are deleted, and `git gc` will not collect them while the record
ref exists. That is the property that makes git a good *store* for this, and it
is the one place in the design where git's content-addressing is doing real
work rather than being worked around.

The honest cost: this only works for merges the **server** performs. A user who
runs `git merge` on their laptop gets stock line merge (or a clean refusal, with
`binary`). Offline peer-to-peer merging of these formats is not achievable
through git's extension points. That is a real limitation and should be stated
in the product, not papered over.

---

## 7. Jujutsu (jj) as a substrate — and the conflict question specifically

Source-read and documentation review; **not run here** (installing it would have
been an ad-hoc system install).

### 7.1 The conflict representation, which is the whole reason to look at jj

jj's model is genuinely better than git's. A commit points to an **odd-length
ordered list of trees** — `A, B, C, D, E` means content `A + (C−B) + (E−D)`. The
type is a signed multiset (`lib/src/merge.rs`):

```rust
pub struct Merge<T> {
    /// Alternates between positive and negative terms, starting with positive.
    values: SmallVec<[T; 1]>,
}
```

with the invariant that there is exactly one more "add" than "remove".
`Merge::flatten()` / `simplify()` cancel terms across rebases, so conflicts
**don't nest** and a conflict rebased over an unrelated change stays the same
conflict rather than re-triggering. That is real, and it is a genuine advance
over git, where a conflict has no representation at all outside a working-copy
index.
<https://github.com/jj-vcs/jj/blob/main/docs/technical/conflicts.md>

### 7.2 But it does not solve "a conflicted CSV is not valid CSV"

**Confirmed from source and docs, and this is the answer to the question that
bit prior work three separate times: no.**

When jj puts a conflicted commit in the working copy it **materialises** the
conflict, unconditionally, with literal marker text:

```
<<<<<<< conflict 1 of 1
%%%%%%% diff from base to side #1
-aa
+cc
+++++++ side #2
bb
>>>>>>> conflict 1 of 1 ends
```

docs/conflicts.md: *"when you run `jj new` or `jj edit` on a commit with a
conflict, it will be materialized in the working copy."* The only knob is
`ui.conflict-marker-style` — `diff` (default, above), `snapshot` (full text per
side, no `%%%%%%%`), and `git` (*"replicates Git's diff3 style … to support
external tools"*). **All three are marker styles. There is no setting that
suppresses materialisation.** The on-disk file is not valid CSV, JSON, `.fods`
or anything else, in every mode.

So jj's advantage is precisely and only **storage-side**: the conflict is
lossless in the commit, survives rebase cleanly, and never has to be re-resolved.
The moment a human or a parser needs to look at the file, the format is broken
in the same way git breaks it. **For this product, that is the wrong half of the
problem.** Our formats need the artifact to stay parseable *while conflicted*,
so the app can render a conflict as UI. jj gives durable conflict *storage* and
still hands you an invalid file.

The right lesson to steal is the *algebra*, not the tool: `Merge<T>` as a signed
multiset with simplification is exactly the shape a conflicts-as-data record
should have (§3.6, §6) — and we can implement it in our own store, materialised
as **structured data in `refs/gws/*`** rather than as markers in the file.

### 7.3 What plain git sees

A conflicted commit cannot be a plain git tree, so the git backend
(`lib/src/git_backend.rs`) writes a **synthetic root tree** with whole-subtree
entries named `.jjconflict-base-N/` and `.jjconflict-side-N/`, plus a
`JJ-CONFLICT-README` blob. Per the source comment, this exists *only to prevent
GC of the relevant trees*; the authoritative data is in a **non-standard commit
header `jj:trees`**. A plain `git checkout` of such a commit yields the first
side's file contents plus `.jjconflict-*/` directories and the README strewn
across the working tree. Not corruption, but not something to hand a
non-technical user either — and it is invisible to every forge UI.

git-compatibility.md is candid about colocated repos: interleaving `jj` and
`git` risks conflicted bookmarks and divergent change-ids; `jj git import` runs
on every command and slows down with many refs; *"Git tools will have trouble
with revisions that contain conflicted files … they are stored in a
non-human-readable fashion"*; NFS/Dropbox sharing is *"not currently thoroughly
tested."* jj also creates `refs/jj/` refs specifically to stop `git gc`
collecting its objects.
<https://github.com/jj-vcs/jj/blob/main/docs/git-compatibility.md>

### 7.4 jj-lib as a dependency

`jj-lib` 0.44.0 (2026-08-06), Apache-2.0, 302,568 total downloads. The project's
own FAQ, verbatim:

> *"`jj-lib` is not a stable API, so you may have to make changes to your tool
> when the API changes."*

and, confirming the Google deployment from primary source rather than rumour:

> *"Using the CLI means that your tool will work with custom-built `jj`
> binaries, like the one at Google."*

<https://github.com/jj-vcs/jj/blob/main/docs/FAQ.md>

31,247★, monthly releases (v0.39→v0.44 Mar–Aug 2026), **no 1.0**, 1,213 open
issues. Bus factor is concentrated: the top two contributors hold 3,806 and
3,152 commits against a next tier in the low hundreds. No on-disk format
stability promise beyond git compatibility. Notably, jj's own git backend is
**gitoxide**, not libgit2 and not shelling out.

### 7.5 Verdict

**Do not build on jj.** Reasons, in order of weight:

1. It **does not solve the problem we would adopt it for** (§7.2). Conflicted
   files still materialise as invalid documents.
2. `jj-lib` explicitly disclaims API stability, pre-1.0, with a concentrated bus
   factor — and we would be depending on it at the deepest layer.
3. jj-over-git produces artifacts (`jj:trees` headers, `.jjconflict-*` trees,
   `refs/jj/`) that no forge understands and that leak into plain checkouts.

**Do steal `Merge<T>`.** The signed-multiset-with-simplification representation
is the correct data model for a conflict record, and it is ~200 lines, not a
dependency.

---

## 8. The library landscape, and whether to shell out

| Library | Licence | Latest | Partial clone | Sparse | Worktrees | Notes | **Custom merge driver hook** |
|---|---|---|---|---|---|---|---|
| **libgit2** | GPLv2 + linking exc. | v1.9.7 (2026-08-13) | limited | partial | ✅ | ✅ | ❌ — `merge.h` exposes only a `default_driver` string selecting built-ins; there is `git_filter_register` but **no `git_merge_driver_register`** |
| **gitoxide (gix)** | MIT/Apache-2.0 | v0.58.0 (2026-08-24) | ❌ | partial | ❌ no checkout/switch/reset | ✅ | ❌ (merge/cherry-pick/revert unimplemented) |
| **go-git** | Apache-2.0 | v5.19.2 (2026-07-29) | — | ✅ | ⚠️ partial | ❌ | ❌ (merge is fast-forward-only) |
| **dulwich** | Apache-2.0/GPLv2 | 1.2.14 (2026-08-28) | limited | ❌ | limited | ✅ | ❌ |
| **isomorphic-git** | MIT | v1.41.9 (2026-08-23) | ❌ | ❌ | ❌ | limited | ❌ |
| **JGit** | EDL 1.0 | 7.8.x (Aug 2026) | ✅ | partial | ✅ | ✅ | ✅ via `MergeStrategy` / `ContentMergeStrategy` |
| **pygit2** | GPLv2 + exc. | v1.20.0 (2026-08-08) | as libgit2 | as libgit2 | ✅ | ✅ | ❌ (as libgit2) |

Two findings sharpen this:

**gitoxide is not ready to be a substrate, and says so.** Its own
`crate-status.md` lists as *not done*: `checkout` / `switch` / `restore` /
`reset`, `rebase`, and `merge` / `cherry-pick` / `revert` orchestration, plus
partial clone and reftable. Diff and object plumbing are solid. The tell is
Cargo's own dependency line — `gix = { features = ["sha1", "progress-tree",
"parallel", "dirwalk", "status"] }` — status and directory walking, not merge,
not checkout. Funded largely through Josh Triplett's sponsorship.
<https://github.com/GitoxideLabs/gitoxide/blob/main/crate-status.md>

**libgit2 is being actively removed by its largest known consumer.** GitLab's
tracker: *"migrate it to use plain Git commands instead so that we can deprecate
and remove our reliance on libgit2."*
<https://gitlab.com/gitlab-org/gitlab/-/work_items/422147> A 2026 production
incident makes the FFI case concretely: `rugged`'s statically-linked libgit2
exported `llhttp_*` symbols that collided with an unrelated gem's `llhttp-ffi`,
corrupting HTTP parsing in Geo replication.

### 8.1 Should a substrate shell out to `git`? Both cases

**For linking a library.** No process-spawn cost (our own op-log test hit ~140
ops/sec purely because of three `git` forks per operation); no argv/stdout
parsing and no version-drift in output formats; no dependency on a `git` binary
of unknown version being present, which matters enormously for a desktop app and
is impossible in a browser; type-safe error handling instead of exit codes.

**For shelling out.** The `git` binary is the only implementation with **all**
of: partial clone, sparse-index, worktrees, notes, filters, merge drivers,
`merge-tree --write-tree`, commit-graph, multi-pack-index, reftable, and the ort
strategy. Every library above is missing several. It is also the only
implementation whose behaviour *is* the specification — a merge that differs
from `git`'s in a corner case is a bug users will attribute to us. And the
process boundary is a genuine robustness asset: git's own crash cannot take down
our server, whereas an FFI segfault or a symbol collision (above) can.

**Recommendation: shell out to `git`, and design so it costs nothing.** The
server-side merge in §6 uses `merge-tree`, `cat-file`, `hash-object`, `mktree`,
`commit-tree`, `update-ref` — six plumbing commands, all of which have
`--batch`/`--stdin` modes that amortise the fork away (`git cat-file --batch`,
`git hash-object --stdin-paths`, `git update-ref --stdin`). A long-lived server
process holding batch pipes gets library-like throughput with binary-like
fidelity. The 140 ops/sec figure is an artefact of naive forking, not a ceiling.

Use a library **only for read-side work in constrained environments** — a
browser or mobile client where `git` cannot run at all. There, accept that
partial clone and sparse checkout do not exist (prior work established this for
libgit2 and isomorphic-git) and design the mobile client to talk to our server's
API rather than to git.

---

## 9. The honest case that git is the wrong base

Stated as strongly as it deserves, because most of this document is a list of
things that had to be worked around.

### 9.1 The prosecution

1. **No sub-file identity.** Git's atom is a *line in a snapshot*. There is no
   stable identifier for a paragraph, a cell, a slide, or a row. Every
   correctness problem in this project reduces to this: A1 references merging to
   480-instead-of-660, blame crediting Dave with Carol's paragraph (§4.4),
   `merge=union` producing two rows named `total` (§1.2). Reintroducing identity
   on top — named columns, block IDs — is a workaround for a missing primitive.
2. **The model is filesystem snapshots, and merging is line-based.** Git has no
   notion of "the value of this cell". Its extension point for fixing that (§1)
   is undeployable (§2). This is not incidental; it is the design.
3. **No per-file ACLs.** Prior work established no forge has per-file read
   permissions (Gerrit's are ref-only, Gitea/Forgejo unit-level, CODEOWNERS is
   routing not access). "Share this one document" — the single most basic
   Workspace operation — has no git-native expression at all.
4. **No efficient partial access.** `--filter=blob:none` gave no size win here
   (§4.3) or in prior work; `--depth=1` gives 104× and forfeits history; sparse
   checkout does not exist in libgit2 or isomorphic-git. Opening one document
   means materialising a repository.
5. **Poor binary handling.** 21 revisions of a 2 MB image = 20.6× a single copy.
   Every real document has images.
6. **History-of-one-file is O(total history)** (§4.2): 940 ms to find 243
   revisions among 50k commits, and commit-graph gives 1.1×. The two questions a
   document app asks most are the two git answers worst.
7. **Single-writer at the ref** (§5): 3 of 16 concurrent CAS updates succeed, by
   design.
8. **A UI non-technical users cannot use.** Pithy — which had the right audience
   — shipped the string `"Complete or abort the rebase in a terminal."`

### 9.2 What a purpose-built store looks like

Irmin's model, essentially: an **append-only operation log** + a
**content-addressed blob store** + a **merge function per type**. Concretely:

- Objects have **stable IDs** assigned at creation, not derived from position.
- The unit of change is a **typed operation** (`set-cell(sheet, row-id, col-id,
  value)`), not a line diff. Merge is defined per type, in-process, always
  available — no `.gitattributes`, no local config, no forge cooperation.
- Conflicts are **first-class values** (jj's `Merge<T>`, §7.1) held beside the
  artifact, never inside it. The document is always parseable.
- Blobs are content-defined-chunked, so image revisions cost deltas rather than
  20.6×.
- Per-object ACLs are trivial, because objects have identity.

Every problem in §9.1 dissolves. That is not a coincidence — those problems are
what you get from choosing a source-code tool for documents.

### 9.3 What that loses, and it is a lot

- **GitHub, GitLab, Gitea.** Hosting, auth, backup, PR review, issues, the whole
  estate — free today, all of it to be rebuilt.
- **CI.** Every pipeline in existence triggers on a git push.
- **Code review.** PR-as-document-review is a genuinely good idea we would get
  for free and would have to reinvent.
- **Backups and durability.** `git clone` is a complete, verifiable, offline
  backup that any engineer can restore without our software existing. This is
  the strongest single argument for git, and it is a *trust* argument, not a
  technical one.
- **The market position.** Prior work found the MCP steering group maintains
  exactly two document-substrate reference servers — Filesystem and Git — and
  archived the Google Drive one. "It's just files in a git repo" is the pitch.
- **Muscle memory and the escape hatch.** A user can `git log`, `git diff`, `git
  checkout` a bad save. No lock-in.

### 9.4 Adjudication

**Git is the right storage engine and the wrong versioning engine, and the
architecture should say so explicitly rather than blur it.**

The empirical work separates cleanly along that line:

- **What git is genuinely good at** — a content-addressed, concurrency-safe,
  durable, universally-readable, well-compressed object store. 64 concurrent
  writers, 1,280 objects, 326 ms, zero errors, `fsck` clean (§5). 13.8×
  compression on `gc`. 545 bytes per op-log entry. Complete verifiable backup by
  `clone`. **Keep all of this.**
- **What git is bad at** — merge semantics (§1, §2), sub-file identity (§4.4,
  §9.1), file-scoped history queries (§4.2), and concurrent writes to a ref
  (§5). **Do not use git for any of these. Do them in our own layer.**

The resulting shape is neither "git-backed" in the naive sense nor a rewrite:

1. **Git is the durable substrate.** Objects, trees, commits, refs. Every
   document is a real file in a real repo; `git clone` is a real backup; GitHub
   still works; CI still fires.
2. **Writes to a repository are totally ordered by our server, not by the
   filesystem** (§5.2). A standing per-repo owner with a queue is the simplest
   form — what Gitea's `globallock` implements and what git's own reftable spec
   recommends — though GitHub's Spokes shows a per-write election also works.
   Local disk only; GitLab's NFS post-mortem is the receipt.
3. **Merge happens in that server, on the three blobs `merge-tree` hands it**
   (§6) — not through `.gitattributes`, which does not deploy. Demonstrated
   working against a plain clone with zero client tooling.
4. **Conflicts are data in `refs/gws/*`**, shaped like jj's `Merge<T>`, never
   markers in the artifact (§3.6, §7.5).
5. **A derived index (SQLite) serves file history, blame, and search** (§4.2),
   rebuilt from git and gitignored — the Fossil pattern, where SQLite is a
   rebuildable cache and the artifacts are the truth.
6. **`.gitattributes` carries exactly the portable lines** — `binary` on every
   structured format, `text eol=lf` — as a client-side backstop that turns
   silent corruption into loud refusal for anyone merging outside our server
   (§1.3).

The honest statement of the bet: **git is being used as a distribution and
durability format, not as the version-control system.** The version control is
ours. That is defensible, it is what Gitaly, Gerrit and Fossil each concluded in
their own ways, and it should be written down as a decision rather than
discovered later when a colleague's `git merge` corrupts a spreadsheet.

The residual honest limitation, which should be in the product docs: **offline
peer-to-peer merging of these formats does not work.** A user who merges on
their own laptop gets stock line-based git, or (with `binary`) a clean refusal.
Type-aware merge requires the server. Anyone who says otherwise has not tried it
on a clone that lacks their config.

---

## 10. The sharpest facts, with numbers

1. **A bare repo ignores `.gitattributes` entirely.** A forge merging in bare
   wrote `<<<<<<<` markers into a file the repository declared `binary`. Fixed
   only by `attr.tree=HEAD`, which no repository can set for itself.
   (§2, `D9-bare-attrs/`)
2. **GitLab's own docs: *"Custom merge drivers are not supported on
   GitLab.com."*** GitHub Support: *"GitHub doesn't consider user-defined
   .gitattributes files."* And Gitaly issue #6193 — *"GitLab.com ignores
   merge=union in .gitattributes"* — shows even the built-in, config-free driver
   is one config regression from vanishing. (§2.1)
3. **A server-side type-aware merge works today with zero client tooling.**
   `merge-tree` exposed all three stages in a bare repo; a cell-level merge
   turned a guaranteed line conflict into `apple,5,99`; a plain `git clone` with
   no `.gitattributes` and no merge config got 4 rows × 3 columns of valid CSV.
   (§6, `D9-server-side-merge/`)
4. **`merge=union` is portable and silently wrong.** Concurrent same-line edits
   `total,300` / `total,200` merged clean to *two rows named `total`* — valid
   CSV, wrong data, no marker. Same failure class as the 480-instead-of-660 A1
   result. (§1.2)
5. **`git blame` credits the rewrapper with 6 of 10 lines** after a one-word
   edit that triggered a 72→80 column reflow, including two paragraphs he never
   touched; `-w` and `-M -C -C -C` both fail to recover it. The same edit
   without rewrap: correct attribution, `1 1` numstat. (§4.4, `D9-blame-prose/`)
6. **"History of this file" costs O(total commits), and commit-graph gives
   1.1×.** 940 ms → 841 ms to find 243 revisions among 50,001 commits, while
   `rev-list --count` went 154 ms → 17 ms (9.1×). The two questions a document
   app asks most are the two git answers worst. (§4.2)
7. **The object store is concurrency-safe; the index and refs are not.** 64
   concurrent workers wrote 1,280 objects in 326 ms with zero errors and a clean
   `fsck`. Shared index: 6/16 `git add`. Per-worktree index: **16/16**. Same
   ref: **3/16**. Git's reftable spec confirms it: *"the repository is
   single-threaded for writers… Application servers wrapped around repositories
   (e.g. Gerrit Code Review) can layer their own lock/wait queue."*
   (§5, `D9-worktree-concurrency/`)
8. **Reftable does not help write concurrency — 3/16 under both backends** — but
   cuts ref storage **147×** (79 MB → 548 KB for 20,000 refs). (§5.1) And
   **`--filter=blob:none` makes a prose repo *larger*** (240K vs 228K full),
   because filtering defeats delta compression; it also fails open with a
   one-line warning while still setting `promisor=true`. (§4.3)
9. **GitLab spent two weeks hunting a kernel bug caused by `packed-refs.lock`
   over NFS**, and now documents local storage as the *only* supported option
   for Gitaly. Gitea has a standing bug class from git lock files (#29673,
   #33239, #34546). GitHub's Spokes *"eliminates conflicts by eliminating
   concurrent writes entirely."* (§5.2)
10. **jj does not solve the conflicted-CSV problem.** Conflicts are stored
   losslessly as a signed multiset (`Merge<T>`), but materialisation into the
   working copy is unconditional and always writes markers;
   `ui.conflict-marker-style` chooses among `diff`/`snapshot`/`git` — three
   marker *styles*, no suppression. `jj-lib` also disclaims API stability
   verbatim. (§7)
11. **Nothing outside `refs/heads/*` moves by default**, and `notes.rewriteRef`
    *"does not have a default value"*, so commit notes silently vanish on
    `--amend`. `git notes merge` writes `<<<<<<<` markers into notes — it
    reproduces the exact problem it was being considered to solve. (§3)

---

## Reproduction index

| Experiment | Transcript |
|---|---|
| `.gitattributes` portability matrix | `D9-gitattributes-surface/TRANSCRIPT-01-surface.txt` |
| Bare-repo attribute failure, `attr.tree` | `D9-bare-attrs/TRANSCRIPT-bare-attrs.txt` |
| Notes / custom refs / op-log cost | `D9-notes-refs/TRANSCRIPT-notes-refs.txt`, `TRANSCRIPT-notes-conflict.txt` |
| Many files × long history | `D9-scale-history/TRANSCRIPT-scale.txt` |
| 50,001-commit deep history | `D9-scale-history/TRANSCRIPT-scale-deep.txt` |
| Blame on reflowed prose | `D9-blame-prose/TRANSCRIPT-blame-prose.txt` |
| Worktree / index / ref concurrency | `D9-worktree-concurrency/TRANSCRIPT-worktree.txt` |
| Reftable vs files backend | `D9-worktree-concurrency/TRANSCRIPT-reftable.txt` |
| Server-side type-aware merge | `D9-server-side-merge/TRANSCRIPT-server-merge.txt` |
| Conflicts-as-data, end to end | `D9-conflicts-as-data/TRANSCRIPT-conflicts-as-data.txt` |
| Merge-driver operation coverage (prior) | `D3-merge-driver-deployment/TRANSCRIPT-01-operations.txt` |
| Merge-driver config states (prior) | `D3-merge-driver-deployment/TRANSCRIPT-03-config-states.txt` |

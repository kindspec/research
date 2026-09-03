# D2 — Version control theory and content addressing

Research date 2026-08-28. Feeds the architecture decision for a git-backed
substrate storing documents, tables and canvases as plain files.

Companion to `RESEARCH.md` (landscape pass — not repeated here). Every command
block below was actually run on this machine against **git 2.47.3**; every
external claim carries a URL and, where it matters, a verbatim quote. Anything
unverified is flagged as such.

**Environment note.** Latest git upstream is **v2.55.0** (tags API,
`git/git`). Local git is 2.47.3; where a behaviour might have changed since,
it is called out.

---

## 0. The three decisions, answered up front

| Decision | Answer |
|---|---|
| Git as storage engine, or versioning layer over another canonical store? | **Git is the storage engine.** No candidate canonical store survives contact with the requirements. |
| How should artifact identity work? | **A UUID inside the file** (frontmatter / a reserved column / a canvas root attribute), plus **jj's `change-id` commit header convention** adopted in plain git for change identity. Path and title are metadata. |
| Content-addressed, change-ID, path, or UUID-in-file? | **UUID-in-file for artifact identity. Content hashes for versions. Change IDs for changes. Never paths.** These are three different questions that all four candidates conflate. |

**The five sharpest facts**, each measured or quoted from a primary source:

1. On 2,000 documents over 51 commits with the tracked document renamed twice
   with heavy rewrites, **`git log --follow` returned 3 of 51 commits (6%) while
   a UUID scan returned 51 of 51 (100%)** and recovered all four paths the
   document had occupied. (§8.3)
2. **Git's conflict markers are valid Markdown.** A conflicted file does not
   fail to render — `=======` is a setext H1 underline, so the conflict renders
   as a heading plus seven nested blockquotes, silently. (§2.2)
3. **jj writes its change ID into a standard git commit object as an extra
   header, and GitHub preserves it** — 26 of the 30 most recent commits in
   `jj-vcs/jj`, fetched with plain `git clone`, carry `change-id`. It survives
   clone, push, gc and `--amend`; it is stripped by `rebase` and `cherry-pick`.
   This is a portable plain-git identity mechanism, not a jj feature. (§3.1)
4. **A custom merge driver in stock git keeps a structured file well-formed
   through a conflict** — and runs on merge, rebase, cherry-pick, revert, stash
   pop and `pull --rebase`. jj cannot do this at all (`.gitattributes`
   unsupported, issue #53 open since 2022-01-22). (§2.4, §3.4)
5. **Three independent teams built "content-addressed store, git as the storage
   layer" and all three left git**: Unison deleted git support (issue #5013),
   Tezos moved `irmin-git` → lmdb → leveldb → `irmin-pack`, and bup needed
   non-git `midx`/bloom side-indexes. (§6.1, §5.4, §7.2)

**And the one that decides the table format.** A pure sort concurrent with an
unrelated cell edit **corrupts** a CSV under stock git — row 2 duplicated, one
edit stranded inside conflict markers, a stale row surviving below. With a
stable row ID and a ~40-line ID-keyed merge driver, the identical merge is
clean and correct, and row order becomes irrelevant — Dolt's semantics, in
plain git. (§8.1c)

The rest of this document is the evidence.

---

## 1. Git's object model, precisely

### 1.1 What is actually stored

Four object types, each stored as `<type> SP <bytelen> NUL <payload>`, SHA-1'd
whole, zlib-deflated to `.git/objects/ab/cdef…`:

```
$ printf 'blob 6\0hello\n' | sha1sum
ce013625030ba8dba906f756967f9e9ca394464a  -
$ git rev-parse HEAD:a.txt
ce013625030ba8dba906f756967f9e9ca394464a
$ python3 -c "import zlib;print(repr(zlib.decompress(open('.git/objects/ce/0136…','rb').read())))"
b'blob 6\x00hello\n'
```

A commit is plain text with a fixed header block:

```
tree 2e81171448eb9f2ee3821e3d447aa6b2fe3ddba1
author t <a@b.c> 1787939152 -0400
committer t <a@b.c> 1787939152 -0400

init
```

**Consequence #1: git models *content*, not *artifacts*.** Three semantically
distinct documents with identical bytes are *one object*:

```
$ git ls-tree -r HEAD
100644 blob 9e4bcc53244ae1ffc26c9c78775b0126f6bb584a	q1.md
100644 blob 9e4bcc53244ae1ffc26c9c78775b0126f6bb584a	q2.md
100644 blob 9e4bcc53244ae1ffc26c9c78775b0126f6bb584a	sub/q3.md
```

There is no object in git that means "this document". The only thing that
distinguishes `q1.md` from `q2.md` is the *name in the tree entry* — i.e. the
path. **If you use git's own model, identity is the path, and nothing else.**

### 1.2 Renames are detected, never recorded

The single most consequential fact. A rename commit stores nothing about the
rename — the same blob simply appears under a new name in the new tree:

```
$ git ls-tree HEAD~1; git ls-tree HEAD
100644 blob c4352f8b46de5cdb88d0cc96958316db42dd2398	doc.md
100644 blob c4352f8b46de5cdb88d0cc96958316db42dd2398	renamed.md
```

Rename detection is a **diff-time heuristic** with a **similarity threshold
defaulting to 50%** (`diff.renames` defaults to `true` since git 2.9;
`git help config`). Below the threshold it silently becomes a delete + add:

```
$ git show --stat --format= HEAD          # rename + 13/20 lines rewritten
 doc.md     | 20 --------------------
 renamed.md | 20 ++++++++++++++++++++
$ git show -M20% --stat --format= HEAD
 doc.md => renamed.md | 26 +++++++++++++-------------
$ git diff --find-renames=1% --summary HEAD~1 HEAD
 rename doc.md => renamed.md (20%)
```

**The merge consequence, measured.** With a *pure* rename git does the right
thing and follows the edit across:

```
### Alice renames doc.md -> renamed.md; Bob edits doc.md line 1
$ git merge bob
Merge made by the 'ort' strategy.
 renamed.md | 2 +-
$ head -1 renamed.md
BOB EDITED LINE 1
```

With rename + rewrite below threshold, it does not, and **Bob's edit is
stranded on a path that no longer exists**:

```
$ git merge bob
CONFLICT (modify/delete): doc.md deleted in HEAD and modified in bob.
  Version bob of doc.md left in tree.
$ grep -c "BOB APPENDED" renamed.md
0
$ tail -1 doc.md
BOB APPENDED IMPORTANT NOTE
```

Resolving that conflict the obvious way (`git rm doc.md`) silently discards
Bob's work. There is no marker, no record, nothing to audit.

**Detection also degrades under scale limits.** `diff.renameLimit` defaults to
1000 and `merge.renameLimit` to 7000 (`git help config`, verbatim: *"The number
of files to consider in the exhaustive portion of rename detection during a
merge. If not specified, defaults to the value of diff.renameLimit. If neither
merge.renameLimit nor diff.renameLimit are specified, currently defaults to
7000."*). Above that, detection is abandoned. A workspace with tens of
thousands of documents can cross this.

**History is heuristic too.** The same file has three different histories
depending on a flag:

```
$ git log --oneline -- renamed.md            # 2 commits
$ git log --oneline --follow -- renamed.md   # 2 commits  (threshold missed)
$ git log --oneline --follow -M20% -- renamed.md  # 4 commits
```

`git help log`, verbatim: *"--follow: Continue listing the history of a file
beyond renames (works only for a single file)."* One file at a time, best
effort. This is not a foundation for "show me this document's history".

Directory rename detection (ort) does exist and works, but reports the move as
a conflict class:

```
CONFLICT (file location): olddir/f4.md added in bob inside a directory that was
  renamed in HEAD, suggesting it should perhaps be moved to newdir/f4.md.
```

### 1.3 The merge-base / three-way model

`git merge` is: find the merge base(s), run a three-way text merge per path.
With more than one base, `git help merge` on the default `ort` strategy:

> *"This strategy can only resolve two heads using a 3-way merge algorithm.
> When there is more than one common ancestor that can be used for 3-way merge,
> it creates a merged tree of the common ancestors and uses that as the
> reference tree for the 3-way merge."*

That synthesised base can itself contain conflict markers — which is how you
get committed markers in real repos.

`git merge-file` is the primitive and it is more capable than the porcelain
suggests:

```
$ git merge-file -p --diff3 mine base theirs
a
<<<<<<< mine
MINE
||||||| base
OLD
=======
THEIRS
>>>>>>> theirs
c
$ git merge-file -p --union mine base theirs   # no markers, both sides kept
$ git merge-file -p --ours  mine base theirs   # exit 0, no markers
```

Exit code is the conflict count. `--diff3`/`--zdiff3` preserve the base, so the
three versions are machine-recoverable — relevant below.

### 1.4 What git fundamentally does NOT model

1. **Identity across rename.** Proven above. Git has no artifact identity at
   all; it has paths and content hashes.
2. **Sub-file identity.** There is no object for "this paragraph", "this row",
   "this shape". Blame is a line-level heuristic and it is weak. A pure
   *reorder* of two paragraphs, with zero content change:

   ```
   $ git blame --line-porcelain d.md | grep ^author | sort | uniq -c
         1 author alice
         2 author bob
   $ git blame -M  … same
   $ git blame -C -C … same
   ```
   Bob, who reordered nothing but paragraph positions, is credited with two of
   the three lines. `-M`/`-C` did not recover it at these paragraph lengths.
3. **Non-textual structure.** Git's merge unit is the line. A CSV row, a JSON
   object, a canvas node are invisible to it.
4. **Partial-file authorship** in any durable sense — see (2).
5. **Conflicts.** Git has no representation for a conflict in the object
   database. A conflict exists only in the index and as markers in the working
   tree. This is the deepest difference from jj (§3).

### 1.5 What git gives you for free — and it is a lot

Do not underweight this. On 2,000 markdown documents plus 50 revisions each
touching 40 files (4,153 objects):

```
$ git count-objects -v      # before gc
count: 4153     size: 19040      (≈20 MB loose)
$ git gc -q --aggressive
$ git count-objects -v
in-pack: 4153   packs: 1   size-pack: 391      (391 KiB)
$ du -sh .git ; du -sh --exclude=.git .
748K	.git
7.9M	.
$ time git status --short
real	0m0.010s
```

**Fifty-one revisions of a 7.9 MB corpus cost 748 KB of history.** Delta
compression on text is extraordinary, `status` is instant, and this is
consistent with the measured result already in `RESEARCH.md` §4 (100k markdown
files, `git status` under 0.1 s). Content addressing, integrity, dedup,
compression, transport, signing, and a battle-tested transfer protocol are all
free. Any replacement has to beat this, not just match it.

### 1.5b Garbage collection — git's own answer, and its own caveat

GC in any content-addressed store is reachability-from-roots, and the hard part
is racing a concurrent writer. Git's answer is a **two-week grace period**, and
git's documentation is unusually candid that this is a mitigation, not a
solution. `git help gc`, NOTES section, verbatim:

> *"when git gc runs concurrently with another process, there is a risk of it
> deleting an object that the other process is using but hasn't created a
> reference to. This may just cause the other process to fail or may corrupt
> the repository if the other process later adds a reference to the deleted
> object. Git has two features that significantly mitigate this problem:
> 1. Any object with modification time newer than the --prune date is kept,
> along with everything reachable from it.
> 2. Most operations that add an object to the database update the modification
> time of the object if it is already present so that #1 applies.
> **However, these features fall short of a complete solution, so users who run
> commands concurrently have to live with some risk of corruption (which seems
> to be low in practice).**"*

`gc.pruneExpire` documentation confirms the default: *"it will call prune
--expire 2.weeks.ago… This feature helps prevent corruption when git gc runs
concurrently with another process writing to the repository."*

Two design consequences. First, **never run `git gc --prune=now`** from the app
— the docs say it *"increases the risk of corruption if another process is
writing to the repository concurrently."* Second, this is the strongest
practical argument for the single-writer-per-repository constraint from
`RESEARCH.md` §4: it makes the race unreachable rather than merely unlikely.

**And deletion is not deletion.** This is a product-level consequence that
falls straight out of the object model and deserves naming now rather than at
launch:

```
$ git rm payroll.md && git commit -m "delete the document"
$ git ls-tree HEAD                       # empty — gone from the worktree and HEAD
$ git cat-file -p 8370380…               # the blob
SECRET SALARY DATA
$ git reflog expire --expire=now --all && git gc --prune=now
$ git cat-file -p 8370380…
SECRET SALARY DATA                       # still there
```

Removing a file creates a *new* commit; the old commit still references the
blob and is still reachable from the branch. GC cannot help — nothing is
unreachable. **Genuinely deleting a document means rewriting history
(`git filter-repo` / BFG) and force-pushing to every clone**, which the
single-writer architecture makes tractable but never makes cheap. Any product
promise of "delete" must either mean "hide" or budget for a history rewrite.
`git help gc` also lists what keeps objects alive — *"objects referenced by the
index, remote-tracking branches, reflogs… and anything else in the refs/\*
namespace"* — so even the unreachable case has a 90-day reflog tail by default.

### 1.6 SHA-256 status, 2026

Local `git help init`, verbatim:

> *"Note: At present, there is no interoperability between SHA-256 repositories
> and SHA-1 repositories."*

Demonstrated:

```
$ git init --object-format=sha256 s256 && cd s256 && git commit …
$ git rev-parse HEAD
a99d35b3f9a5b9195bc3554e7b751c58d6c3873ed90bf044cbcf79670f51a6a2
$ cd ../s1 && git fetch ../s256
fatal: mismatched algorithms: client sha1; server sha256
```

Upstream status ([lwn.net/Articles/1042172/](https://lwn.net/Articles/1042172/),
quoting brian m. carlson):

> *"The SHA-256 interoperability work is not done yet. My estimate of this work
> is 200–400 patches, of which about 100 are done."*

> *"Rust will become mandatory for building Git as of the 3.0 release."*

The [hash-function-transition doc](https://git-scm.com/docs/hash-function-transition)
still lists as **not** implemented: *"Add SHA-256 support to Git protocol. This
is valuable and the logical next step but it is out of scope for this initial
design"*, and *"Shallow clones and fetches into a SHA-256 repository."* It also
notes: *"a SHA-256 repository cannot borrow objects from a SHA-1 repository
using objects/info/alternates."*

**Decision impact: none, but plan for it.** Use SHA-1 (the default) for
compatibility. Do not build anything that assumes a 20-byte object ID or parses
40-hex-char strings with a fixed width; git 3.0 is targeted for around end of
2026 and forges will follow. Do not derive *your* artifact identity from a git
object ID — it will change algorithm underneath you.

---

## 2. The conflict-representation problem (the crux for this product)

This is where the entire architecture turns, so it gets its own section with
original experiments.

### 2.1 Conflict markers destroy structured files

```
$ git merge bob        # concurrent edits to "owner" in a JSON doc
CONFLICT (content): Merge conflict in data.json
$ cat data.json
{
  "title": "Q3 plan",
<<<<<<< HEAD
  "owner": "alice.smith",
=======
  "owner": "a.smith@corp",
>>>>>>> bob
  "rows": [1, 2, 3]
}
$ python3 -c "import json;json.load(open('data.json'))"
json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes
```

CSV likewise parses into rows of the wrong arity:

```
3 ['item', 'qty', 'price']
1 ['<<<<<<< HEAD']
3 ['widget', '11', '5']
1 ['=======']
```

### 2.2 The finding I did not expect: conflict markers are *valid Markdown*

A conflicted markdown file does not fail to parse. It parses into something
else entirely. Real CommonMark output (`markdown-it-py`) for a conflicted
paragraph:

```html
<p>Intro paragraph.</p>
<h1>&lt;&lt;&lt;&lt;&lt;&lt;&lt; HEAD
Owner: carol</h1>
<p>Owner: bob</p>
<blockquote><blockquote><blockquote><blockquote><blockquote>
<blockquote><blockquote><p>B</p></blockquote>…
```

`=======` is a **setext H1 underline**, so `<<<<<<< HEAD` plus the "ours" line
becomes an `<h1>`. `>>>>>>> B` is **seven nested blockquotes**. In a live-preview
markdown editor — which is the settled editor decision in `RESEARCH.md` §2 —
**a merge conflict renders as a giant heading followed by a nested quote, with
no indication that anything is wrong.** This is a silent-corruption class
specific to this product and I have not seen it documented anywhere.

Partial mitigation exists and is cheap: `.gitattributes`
`*.md conflict-marker-size=32` widens the markers past any plausible setext
line and past 7-deep blockquote nesting:

```
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< HEAD
Owner: carol
================================
Owner: bob
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> B
```
This is still invalid-as-intended markdown, but it now *looks* broken rather
than looking like a heading. **Ship this attribute on day one regardless of
every other decision.**

### 2.3 Committed markers nest and become unparseable

Committing a conflicted file is routine in the wild. The next merge nests:

```
a
<<<<<<< HEAD
<<<<<<< HEAD
X1
=======
Y1
>>>>>>> Y
=======
Z1
>>>>>>> Z
z
```

Two `<<<<<<<`, two `=======`, two `>>>>>>>`, unbalanced with respect to any
grammar. No conflict-marker parser can recover the sides. Markers are not a
data format; they are a display convention that happens to be persisted.

### 2.4 The fix, in plain git: a custom merge driver

`.gitattributes` maps a path pattern to a named driver; the driver is a program
receiving `%O %A %B` (base, ours, theirs) and writing the result to `%A`. Exit
0 means clean. **The driver can therefore resolve semantically and represent
any residual conflict as well-formed data.** A 15-line proof-of-concept JSON
driver:

```
$ git merge bob
 d.json | 14 +++++++++++++-
$ cat d.json
{
  "title": "Q3",
  "owner": "alice.smith",
  "rows": 4,
  "_conflicts": [
    { "key": "owner", "base": "alice", "ours": "alice.smith", "theirs": "a@corp" }
  ]
}
$ python3 -c "import json;json.load(open('d.json'));print('VALID JSON: yes')"
VALID JSON: yes
```

Both keys merged correctly (`rows` taken from theirs, `owner` flagged), the
file stayed parseable, and the conflict is now queryable structured data that a
UI can render as a per-cell resolution prompt.

**And it runs on every local operation that merges.** I tested each with a
genuinely conflicting change, checking whether the output was still valid JSON:

| Operation | Driver runs? |
|---|---|
| `git merge` | **yes** |
| `git rebase` | **yes** |
| `git cherry-pick` | **yes** |
| `git revert` | **yes** |
| `git stash pop` | **yes** |
| `git pull --rebase` (two real repos through a bare remote) | **yes** |
| `git apply` / `git am` | no — patches apply textually, drivers are never involved |
| forge-side merge (GitHub "Merge pull request") | **no** — see note |

That coverage is the whole ballgame: the merge driver is not a niche hook, it
is the merge machinery. Anything that produces a three-way merge locally goes
through it.

*Note on the forge row:* this is **structural reasoning, not a citation** — a
merge driver is an arbitrary local executable named in `.git/config`, which a
forge does not have and could not safely run. I could not find a GitHub doc
stating this explicitly and it is listed in §9 as unverified. It should be
confirmed with a live test before any design depends on it.

**The catch, and it is serious.** The driver *definition* lives in `.git/config`,
not in the repo. Only the `.gitattributes` mapping is versioned. A fresh clone
silently falls back to text merge:

```
$ git clone md clone && cd clone
$ git config --get merge.jsonm.driver
(nothing)
$ cat .gitattributes
*.json merge=jsonm
$ git merge <branch>
CONFLICT (content): Merge conflict in d.json
$ cat d.json
<<<<<<< HEAD
{"title": "Q3", "owner": "alice.smith", "rows": 3}
=======
…
```

**Git warns about nothing.** Consequences for the architecture:

- The merge driver must be installed by the app on clone/open. This is fine
  when the app owns the working copy; it is a real hazard for a user who clones
  the repo by hand or merges on the forge.
- **Server-side merges (GitHub's "Merge pull request" button) never run the
  driver.** If the product's collaboration story routes through a forge's web
  merge, structured merge does not happen there.
- This is a strong argument for the single-writer-per-repo constraint already
  established in `RESEARCH.md` §4: if the app is the only merger, the driver
  always runs.

`daff` (MIT, 923 stars, v1.4.2 2025-05-04), already identified in
`RESEARCH.md` §4 as doing correct cell-level three-way CSV merges, plugs into
exactly this slot — it is installed precisely this way (`daff git csv`) so that
*"git will suddenly understand about rows and columns, not just lines."*

**One correction to `RESEARCH.md` §4, and it matters.** daff does *not* keep a
conflicted CSV clean. Its conflict representation writes into the cell —
`Merger.hx:204`:

```haxe
return view.toDatum("((( " + view.toString(pcell) + " ))) " +
                    view.toString(lcell) + " /// " + view.toString(rcell));
```

So a conflicted cell becomes the literal string `((( b0 ))) L /// R`. The file
stays syntactically valid CSV, but an integer column now holds prose and every
downstream reader must know an undocumented marker convention. **That is better
than git's markers — the file still parses — but it is not the goal state.** The
goal state is §2.4's `_conflicts` block: conflicts as *typed side data*, with
the cell holding one plausible value. Adopt daff for its diff/merge algorithm,
not its conflict encoding.

**And the mechanism survives the move to a JS stack.** This matters, because
`RESEARCH.md` §4 already established that mobile and browser contexts need
isomorphic-git, and a recommendation that only works with CLI git would be half
a recommendation. isomorphic-git (8,338 stars, last push 2026-08-23) implements
merge drivers as a first-class JS callback. From its own
[`docs/mergeDriver.md`](https://github.com/isomorphic-git/isomorphic-git/blob/main/docs/mergeDriver.md):

> *"The merge driver is a callback which is called for each conflicting file
> during a merge. It takes the file contents on each branch as an array and
> returns the merged result."*
> *"By default the merge command uses the diff3 algorithm to try to solve merge
> conflicts, and throws an error if the conflict cannot be resolved. This is not
> always ideal, so isomorphic-git implements merge drivers so that users may
> implement their own merging algorithm."*

The signature, from `src/typedefs.js`:

```js
/**
 * @callback MergeDriverCallback
 * @param {MergeDriverParams} args     // { branches, contents, path }
 * @return {{cleanMerge: boolean, mergedText: string}
 *          | Promise<{cleanMerge: boolean, mergedText: string}>}
 */
```

Three practical notes, verified in source (`src/api/merge.js`,
`src/api/cherryPick.js`, `src/utils/mergeTree.js`):

- `contents[0]` is always the **merge base**, `contents[1]` is ours,
  subsequent entries are theirs — the same `%O %A %B` contract as CLI git,
  and it generalises to more than two sides.
- **`path` is passed to the callback**, so dispatch by file type happens in
  your own code. You do not need `.gitattributes` at all in this stack — which
  also removes the "driver not installed in a fresh clone" hazard, because the
  driver ships with the app rather than with the repo.
- `mergeDriver` is accepted by both `merge()` and `cherryPick()`. With
  `abortOnConflict: false`, `mergedText` is written even on an unclean merge —
  which is exactly what you want when the driver's "conflict" output is
  well-formed data rather than markers.

So the same design works in CLI git via `.gitattributes` + a driver program,
and in the JS/Electron/mobile stack via a callback. That is unusually good
news for a cross-stack product.

### 2.4b The one driver that needs no installation: `merge=union`

Git ships a **built-in** union driver, so this one *does* travel in
`.gitattributes` alone with nothing in `.git/config`. It is the technique
git-annex uses for its append-only metadata logs, and it is conflict-free by
construction:

```
$ cat .gitattributes
*.log merge=union
$ git merge bob
 1 file changed, 1 insertion(+)          # no conflict
$ cat meta.log
1700000000 alice title="Q3"
1700000100 alice title="Q3 revised"
1700000050 bob tags="finance"
```

Two writers appended concurrently to the same log and both survived with zero
conflict markers. **This is the right shape for any per-artifact metadata that
must never block a merge** — comment threads, presence hints, tag assignments,
"last opened by". Cost: the log only grows (needs compaction), and ordering is
per-side, not global, so entries must carry their own clock and be idempotent
under replay.

**Correction worth making precisely:** git-annex does *not* use git's
`merge=union`. It implements its own union merge in `Git/UnionMerge.hs`, and the
difference matters — see §7.3, which covers the three things git's built-in
driver lacks (set semantics, vector clocks, tombstones). Git's `merge=union` is
the cheap version of the idea; git-annex's is the correct one.

### 2.5 Git merges text correctly and meaning incorrectly

The failure mode nobody has a fix for. Two edits, different lines, clean merge:

```
$ git merge bob
 1 file changed, 1 insertion(+), 1 deletion(-)
$ cat memo.md
# Hiring memo

We will hire 6 engineers in Q3.

The budget is $450,000 (unchanged, approved for 3 heads).
```

Alice doubled the headcount; Bob annotated that the budget was approved for
three. Zero conflicts. This is the document analogue of the CSV `480 vs 660`
result in `RESEARCH.md` §3. **No version control system in this survey fixes
this** — not jj, not Pijul, not Dolt. It is a semantic conflict, and only a
schema or a human catches it.

Adjacent-insert conflicts, by contrast, are pure noise and very common in
list/table documents:

```
$ cat l.md
- alpha
<<<<<<< HEAD
- ALICE
=======
- BOB
>>>>>>> bob
- beta
```

Two independent list items. A list-aware merge driver resolves this trivially;
a text merge cannot.

---

## 3. Jujutsu (jj) — the strongest single finding in this document

`jj-vcs/jj`, Apache-2.0. Verified today via the GitHub API: **v0.44.0 released
2026-08-06**, **31,247 stars**, 1,213 open issues, monthly release cadence,
**no 1.0**. Crate `jj-lib` 0.44.0, 302,353 downloads all-time.

### 3.1 Change IDs — and the fact that changes everything

A change ID is 16 random bytes (`lib/src/settings.rs`, `new_change_id`), not
derived from content, rendered in a "reverse hex" alphabet (z–k) so it can
never be confused with a commit ID. `docs/glossary.md`: *"A change ID is a
unique identifier for a change. They are typically 16 bytes long and are often
randomly generated."*

Demonstrated stability across four rewrites of the same change (one change ID,
four commit IDs):

```
kzunuooqtllo bcee65e14fc7 add data.csv
kzunuooqtllo 2b3c4b7352fb add data.csv
kzunuooqtllo 8f6d00c98220 add data.csv v3
kzunuooqtllo 29aadce80d7d add data.csv v4 REWRITTEN
```

**The crucial part: since jj v0.30.0 the change ID is written into the git
commit object as an extra header**, so it is part of the commit hash and
travels through push/fetch like any other commit content.
`lib/src/git_backend.rs`: `pub const CHANGE_ID_COMMIT_HEADER: &str = "change-id";`
and `write-change-id-header = true` by default.

**I verified this is a portable, plain-git mechanism — not a jj feature.**
Hand-crafting a commit object with an arbitrary extra header using nothing but
`git hash-object`:

```
$ printf 'tree %s\nparent %s\nauthor …\ncommitter …\nchange-id kzunuooqtllozwvlptsvlsvvzykrowss\n\nc2\n' … > obj.txt
$ git hash-object -t commit -w obj.txt
24a160cbe2004d0ce2a9d2b3e7de5ddeb2b3b064
$ git fsck          # silent — no complaints
$ git log --oneline # works normally
```

Survival matrix, measured on git 2.47.3:

| Operation | change-id header |
|---|---|
| `git clone` / `git push` → bare → `git clone` | **preserved** |
| `git gc` / repack | **preserved** |
| `git commit --amend` | **preserved** |
| `git merge` (header stays on the merged-in commits) | **preserved** |
| `git rebase` onto a new base | **STRIPPED** |
| `git cherry-pick` | **STRIPPED** |
| `git format-patch` / `am` | **not carried** |

And it survives GitHub. I cloned `jj-vcs/jj` from GitHub with plain git and
counted headers on the 30 most recent commits:

```
commits with a change-id header in the last 30 of jj-vcs/jj: 26 / 30
$ git cat-file -p HEAD | head -8
tree e4dfea42b5425971b24b5635c97fce0cc7a44df0
parent 2af2ebb051c08919430ba857c7ed9f65887c67b1
author Yuya Nishihara <yuya@tcha.org> 1787915298 +0900
committer Yuya Nishihara <yuya@tcha.org> 1787925901 +0000
change-id lxmwnurlorzuptlotqmkpqlpnkyzqnus
```

jj's own caveat, `docs/git-compatibility.md`, verbatim:

> *"Change IDs are stored in git commit headers as reverse hex encodings. This
> is a non-standard header and is not preserved by all `git` tooling. For
> example, the header is preserved by a `git commit --amend`, but is not
> preserved through a rebase operation. GitHub and other major forges seem to
> preserve them for the most part."*

**One ergonomic cost, measured:** there is no `git log --format` placeholder for
extra headers. `%(trailers)` returns empty. Reading them requires
`git cat-file -p`. For a product that reads the object database directly, that
is a non-issue.

### 3.2 First-class conflicts — what they do and do not buy

Conflicts are stored *in the commit* as `Merge<T>`, an odd-length alternating
list of adds and removes. `core/src/merge.rs`: *"There is exactly one more
`adds()` than `removes()`. When interpreted as a series of diffs, the merge's
(i+1)-st add is matched with the i-th remove."* `docs/technical/conflicts.md`:
*"If the commit has trees A, B, C, D, and E it means that the contents should
be calculated as A+(C-B)+(E-D)."* Algebraic simplification is what lets a
conflict be rebased repeatedly without nesting — the exact failure shown in
§2.3.

jj's materialised markers are richer than git's (one side rendered as a *diff*
against base):

```
id,name,qty
<<<<<<< conflict 1 of 1
%%%%%%% diff from: tmnmnotn 0d9c86ba "base"
\\\\\\\        to: luolqymx a762c78e "sideA"
-1,widget,10
+1,widget,11
+++++++ qnqtzszm eba61e0b "sideB"
1,widget,99
>>>>>>> conflict 1 of 1 ends
2,gadget,20
```

**Direct answer to "does this solve conflicts inside a CSV that must stay
well-formed?" — No.** Materialisation writes markers into the file and the CSV
is as broken as under git. What jj *does* give is that the authoritative form
is a structured value you can read without ever materialising: the 2n+1 sides
are separate, individually well-formed blobs. That is the right primitive for a
semantic merge UI. **But a custom merge driver in plain git (§2.4) reaches the
same end state — a well-formed file with the conflict as data — and does it
with the *app's* schema knowledge, which jj does not have.**

**The git-boundary hazard is severe.** A conflicted jj commit exported to git
writes side A into the real path with *no markers and no warning*:

```
$ git ls-tree -r --name-only <conflicted commit>
.jjconflict-base-0/inv.csv
.jjconflict-side-0/inv.csv
.jjconflict-side-1/inv.csv
JJ-CONFLICT-README
inv.csv
$ git show <commit>:inv.csv
id,name,qty
1,widget,11        # silently side A
2,gadget,20
```

`lib/src/git_backend.rs`: *"The rest of the tree is copied from the first term
of the conflict, which prevents editors with Git support from highlighting all
files as new."* jj ships a `JJ-CONFLICT-README` blob conceding *"The commit
contains file conflicts, and therefore looks wrong when used with plain Git."*
Any plain-git consumer or CI job reading that commit gets one side of an
unresolved conflict presented as resolved content.

### 3.3 The rest of the model

- **Operation log** (`.jj/repo/op_store`): every command records a *view*
  (bookmarks, tags, refs, heads, per-workspace working-copy commit). Gives free
  undo and lock-free concurrency — *"you can run concurrent `jj` commands
  without corrupting the repo, even if you run the commands on different
  machines that access the repo via a distributed file system."* Entirely
  **local**; nothing survives a push. **There is no GC for it** (issue #12) —
  it grows unboundedly.
- **Working copy as a commit**, snapshotted before nearly every command. Files
  are tracked implicitly: *"if you add a new file to the working copy, it will
  be automatically committed once you run e.g. `jj st`."* Guard rail:
  `max-new-file-size = "1MiB"`, above which files are not auto-added.
  `.gitignore` only — *"there's no such thing as a `.jjignore` yet"*.
- **Automatic rebase of descendants**, with descendants keeping their own
  change IDs (`Rebased 1 descendant commits.`).
- **Backend abstraction** (`lib/src/backend.rs`) is real but the git backend is
  the only production one: *"There is currently only one production-ready
  builtin commit backend: the Git backend… Google also has its own cloud-based
  backend."* jj uses **gitoxide (`gix`)**, not libgit2, and shells out to the
  `git` binary for network operations.
- **Wire compatibility is genuine.** Commits and files are ordinary git objects;
  a plain `git clone` of a jj repo works. jj writes `refs/jj/keep/<sha>` refs to
  protect rewritten commits from GC — a repo-bloat vector.

### 3.4 The disqualifier

**jj has no automatic, per-path structured merge.** Stated precisely, because
the distinction matters:

- `.gitattributes` is unsupported. Issue
  [#53](https://github.com/jj-vcs/jj/issues/53), open since **2022-01-22**, 92
  reactions, 27 comments (verified via the GitHub API today).
- Consequently there are **no merge *drivers*** — nothing runs automatically
  during `jj merge`/rebase to resolve a `.csv` or `.canvas` semantically. jj's
  automatic resolution is line-based, tunable only by `merge.hunk-level =
  "line" | "word"`.
- jj *does* have merge **tools** (`jj resolve --tool mergiraf`, with kdiff3,
  meld, mergiraf, smerge, vimdiff, vscode preconfigured). But per the
  [config docs](https://docs.jj-vcs.dev/latest/config/), these run **only on an
  explicit `jj resolve`**, never automatically during a merge or rebase, and
  **tool selection is a single global `ui.merge-editor` with no per-file-type or
  per-path selection.** Issue #5264 ("FR: custom merge drivers", 2025-01-04) was
  closed the next day by pointing the reporter at `jj resolve --tool`; the
  request for the real thing is
  [#8071](https://github.com/jj-vcs/jj/issues/8071), *"FR: Support using
  merge-drivers configured in gitattributes"*, opened 2025-11-19 and still open.

Given §2.4, where an automatic per-path merge driver is the single
highest-leverage mechanism available for keeping structured documents
well-formed, this alone rules jj out as the engine for this product. Git does
this today; jj cannot do it at all.

Supporting reasons, all verified:

- **No Git LFS.** Issue #80, opened 2022-02-24, **325 reactions**, the most
  requested issue in the tracker. Canvases mean binary assets.
- **No hooks** (#405, #3577) — no validation points for file formats.
- **No copy/rename tracking** (#47, open since 2021-12-18). jj inherits git's
  tree model and has no artifact identity either.
- **No submodules**, no partial clone, shallow clone only "kind of".
- **`jj-lib` is explicitly unstable.** Crate description: *"Library for
  Jujutsu — an **experimental** version control system."* README: *"There
  **will** be changes to workflows and backward-incompatible changes to the
  on-disk formats before version 1.0.0."* 23 reverse dependencies, the largest
  being `gg-cli` at 332 downloads. No production embedder.
- **No FFI, no bindings, no wasm** (zero wasm references in the tree). For a
  Node/Electron app the only path is shelling the CLI. The intended fix is an
  unbuilt RPC API: *"We want to provide an RPC API for tools that want to work
  with an unknown build of `jj`… having an RPC API should make it easier for
  tools like VS Code that are not written in Rust."*
- **Bus factor ~2** (yuja 3,806 commits, martinvonz 3,152, then a steep drop).
  Governance has shifted: martinvonz now commits as `martinvonz@ersc.io`.
  [East River Source Control](https://ersc.io/) is a venture-funded startup
  (~$4.86M) building a jj-based *forge* and employing Klabnik and thoughtpolice
  on jj. `docs/paid_contributors.md` lists Alphabet/Google (41), ERSC (8), IMC
  Trading (2). The README's "full-time project at Google" disclaimer is stale.

**What would falsify the "don't use jj" call:** if `.gitattributes`/merge-driver
support landed, if `jj-lib` declared API stability, and if a wasm or FFI story
appeared. Watch #53 specifically.

**What to steal anyway:** the `change-id` header convention (§3.1), because it
is *plain git*, and the `Merge<T>` insight that a conflict should be stored as
n well-formed sides rather than as one broken file.

---

## 4. Patch theory — Darcs and Pijul

### 4.1 Darcs

Model: primitive patches (`hunk`, `addfile`, `move`, `token replace`) plus
**commutation**; merge is filling in a commutation square
([darcs.net/Theory/Conflictors](https://darcs.net/Theory/Conflictors)):

> *"Basic patch theory (addfile/hunk/move etc.) describes the merging two sets
> of primitive patches, by 'filling in' the two missing sides of a commutation
> square, but what should happen if those changes cannot be merged?"*

**The exponential merge problem is real and Darcs 2 did not fix it**
([darcs.net/FAQ/ConflictsDarcs1](https://darcs.net/FAQ/ConflictsDarcs1)):

> *"The time needed to resolve or detect conflicts grows exponentially with
> depth of conflict nesting."*
> *"Recursive conflicts exhibit the exponential time/memory usage in Darcs 2,
> too."*

[darcs.net/FAQ/Performance](https://darcs.net/FAQ/Performance), asked whether it
is fixed, answers **"No."**

**Darcs 3 fixes it on paper and has been UNSTABLE for six years.** Hackage
changelog, darcs **2.16.1 (2020-08-14)**:

> *"Preliminary UNSTABLE support for a new patch theory named 'darcs-3'…"*
> *"It also reduces the worst case asymptotic runtime for commutation and
> merging from exponential to merely quadratic in the number of patches
> involved."*
> *"Please note that this format is not yet officially supported… You should
> NOT use it for any serious work yet."*

No later changelog advances it. Status: latest release **2.18.5, uploaded
2025-01-09** (19 months ago); every release since 2.18.1 is GHC/dependency
maintenance. `bugs.darcs.net` returns **HTTP 500** and
`hub.darcs.net/darcs/darcs` returns **404** as of today. Debian records darcs
being *removed from testing* twice (2022-08-09, 2023-12-13). **Darcs is being
kept compiling, not developed.**

### 4.2 Pijul

The model is a **graph**, not a patch algebra
([pijul.org/manual/theory.html](https://pijul.org/manual/theory.html)):

> *"A repository as a single file represented by a directed graph G=(V,E) of
> lines of text, where each vertex v∈V represents a line of text."*
> *"Vertices are uniquely identified, by the hash of the change that introduced
> them, along with a position in that change."*

Conflicts are first-class graph states (disconnected alive vertices, cycles,
zombies). Renames are modelled properly — *"Each file or directory is
represented by two separate vertices: one is its name, the other one is an
'inode' vertex representing the file itself"* — which is exactly the identity
property this product needs.

Theoretical basis: Mimram & Di Giusto,
[arXiv:1311.3903](https://arxiv.org/abs/1311.3903), *"A Categorical Theory of
Patches"*, submitted 2013-11-13, **v1 only, never revised**. Its first
definition:

> *"A *file* A is a finite sequence of lines."*

**That is the decisive fact.** Patch theory is line-granular by construction.
It changes composition and commutation semantics, not granularity.

**The one real, still-reproducible git failure.** Zooko's badmerge
([tahoe-lafs.org/~zooko/badmerge/simple.html](https://tahoe-lafs.org/~zooko/badmerge/simple.html)):

> *"The git or svn 3-merge algorithm and the GNU diff3 algorithm apply the
> changed line from c1 to the wrong place in b2, resulting in an apparently
> clean but actually wrong result."*
> *"darcs uses information that svn does not use — namely the information
> contained in b1 — to learn that the location has moved and precisely to where
> it has moved."*

**I reproduced this independently against git 2.47.3 with the default
`merge-ort` strategy.** Setup per Zooko's page: base `a = A B C D E`; `b1`
prepends `G G G` (so the original `ABCDE` moves to the end); `b2` prepends a
fresh copy of `A B C D E` (giving `[new ABCDE][GGG][original ABCDE]`); on the
other branch `c1` changes `C → X` in the original. Merging `c1` into `b2`:

```
$ git merge c1 -m m
 1 file changed, 1 insertion(+), 1 deletion(-)
exit=0                              # NO CONFLICT
$ cat f | tr '\n' ' '
A B X D E G G G A B C D E
```

Correct answer (`X` belongs to the *original* `ABCDE`, now at the end):
`A B C D E G G G A B X D E`. **Git edited the wrong copy, silently, with exit
code 0.** `-s recursive` gives the identical wrong answer. **This is live in
2026.** If canvases or tables involve routine block duplication or reordering
while being edited concurrently, this hazard is real — and note it is exactly
the shape of "duplicate this slide / row / group and then edit one of them".

**But it does not help documents.** Verified: Pijul emits git-style conflict
markers into the working file (observed output from
[lukas-prokop.at](https://lukas-prokop.at/articles/2022-07-26-trying-out-pijul)):

```
fn main() {
>>>>>>> 1 [CGJNA7DH]
    println!("Change on main channel");
======= 1 [U5B4QNCA]
    println!("Text from feature branch");
<<<<<<< 1
}
```

**A conflicted CSV in Pijul is exactly as broken as a conflicted CSV in git.**
Its advantage is internal — the *repository* stays consistent and patches can
be applied to a conflicting repo — but the materialised file is not well-formed
and the graph has no schema awareness. On every document case tested (concurrent
CSV row inserts at the same anchor, prose paragraph rewritten on both sides),
Pijul's model yields conflict type 1 — the identical outcome to git.

**Status 2026** (crates.io API):

```
libpijul     1.0.0-beta.11   2026-01-13   176,772 dl
pijul        1.0.0-beta.22   2026-08-23   192,506 dl
pijul-core   1.0.0-beta.22   2026-08-22     2,246 dl   <- the library
sanakirja    2.0.0-beta.3    2026-07-06   243,089 dl
```

Still beta 4.5 years after the [2022-01-08 beta announcement](https://pijul.org/posts/2022-01-08-beta/).
`libpijul` was renamed to `pijul-core` in 2026; **pijul-core has 2,246 total
downloads** — nobody has built anything on it. **docs.rs reports 14.08% of the
crate is documented.** The blog's most recent post is 2025-06-07 and is about a
different tool. Multiple 2026 forum threads report the Nest signup being broken
for weeks. A WordPress git import "took 7 hours" and produced a `.pijul` folder
**three times larger than the original `.git`**
([discourse.pijul.org/t/using-pijul-git/796](https://discourse.pijul.org/t/using-pijul-git/796)).
Sanakirja, the B-tree everything rests on, is itself beta and yanked 1.5.0.
**Largest known user: the Pijul project itself.**

### 4.3 Verdict on patch theory

**Not a real improvement for document merge.** The wins are line-*position*
wins; document conflicts are semantic-content conflicts in the same region,
where the extra information patch theory tracks disambiguates nothing. The one
place patch theory cleanly dominates — **declared rather than inferred
renames** — is obtainable without it, by putting a stable ID in the file.

Cross-check on the "cherry-pick duplicates the fix" claim widely cited against
git: **could not be reproduced on git 2.47.3.** `merge-ort` (git 2.33, 2021)
appears to have closed it. Treat any pijul-vs-git comparison written before 2021
as stale.

**If the actual requirement is commutative/associative merge** — a server
merging changes from N clients in nondeterministic order with a deterministic
result — the answer is not Pijul, it is **CRDTs** (Yjs, Automerge, Loro), which
give those properties *plus* structure awareness, ship at scale, and compose
with a git-backed plain-file store. This is consistent with the CodeMirror +
`y-codemirror.next` decision already made in `RESEARCH.md` §2.

---

## 5. Unison — content addressing where names are metadata

`unisonweb/unison`: **6,719 stars, release 1.4.0 on 2026-08-19**, ~monthly
cadence; **1.0 shipped 2025-11-25**. Genuinely, actively maintained.

### 5.1 The model

[unison-lang.org/docs/the-big-idea](https://www.unison-lang.org/docs/the-big-idea/):

> *"Each Unison definition is identified by a hash of its syntax tree."*
> *"While we've given this function a human-readable name… **names are just
> separately stored metadata that don't affect the function's hash.**"*

The worked example is exact — `increment n = n + 1` hashes as
`increment = ( #arg1 -> #a8s6df921a8 #arg1 1 )`:

> *"So all named arguments are replaced by positionally-numbered variable
> references, and all dependencies… are replaced by their hashes."*

Names live in a versioned namespace tree as a *relation*
`Relation NameSegment Referent` — many names per hash, and transiently many
hashes per name ("conflicted names").

### 5.2 The finding that matters most: Unison put UUIDs back in

Pure structural hashing turned out to be wrong for *nominal* identity. For a
`unique` type, *"Unison will generate a universally unique identifier for the
type and use that identifier when generating the hash"*
([language reference](https://www.unison-lang.org/docs/language-reference/unique-types/)).
Stew O'Connor of the Unison team, [HN 46053818](https://news.ycombinator.com/item?id=46053818)
(2025-11-26):

> *"Originally, if you omitted both and just said: `type Optional a = Some a |
> None` The default was 'structural'. **We switched that a couple of years ago
> so that now the default is 'unique'.**"*

**Unison's default identity for user-defined types is a UUID injected into the
content hash.** Content addressing alone was insufficient even for code.

### 5.3 And names came back through the merge algorithm

Unison's merge is a three-way diff on the `Name → hash` map
(`Unison/Merge/Diff.hs`: `Map Name (DiffOp (Synhashed ref))`) — i.e. git's
rename problem in different coordinates. To make it work they had to invent a
**second, name-dependent hash**. `Unison/Merge/Synhash.hs`, verbatim:

> *"Utilities for computing the 'syntactic hash' of a decl or term, which is a
> hash that is computed **after substituting references to other terms and
> decls with names from a pretty-print environment.**… The merge algorithm
> currently uses syntactic hashes for determining whether an update was
> performed by a human, or was the result of auto-propagation. **(Critically,
> this cannot handle renames very well.)**"*

And the roadmap concedes the fix is not a hash design
([Where Unison is headed](https://www.unison-lang.org/blog/where-unison-is-headed/)):

> *"Some of these are easy while others require **storing more structured
> information in the version history.**"*

**Content addressing does not give you rename-aware merge. Recorded identity
does.**

### 5.4 What it cost — and the git-as-transport datum

**Unison tried git as transport for a content-addressed store and deleted it.**
[Issue #5013](https://github.com/unisonweb/unison/issues/5013), Chris Penner,
2024-05-28:

> *"Git support has long been deprecated in favour of using Unison Share. This
> removes all support for pushing and pulling to git repositories… **This was
> spurred on by the migration to a project-centric approach without a singular
> codebase root branch, since continuing to support git with this model would
> require re-implementing most git sync methods.**"*

And what it felt like, Chiusano's
[experience report](https://www.unison-lang.org/blog/experience-report-unison-in-production/):

> *"Unison Share didn't exist when we first started… **Instead we stashed large
> SQLite database files on GitHub and shared code that way, which was exactly
> as janky as it sounds.**"*

Also: the codebase moved from a directory tree to **SQLite** for performance —
Chiusano, *"Unison used the **file system as a terrible database**, which was
both complicated and led to all sorts of performance problems"*; the migration
gave *"up to 75x less RAM usage, snappier response times, sizes reduced by as
much as 99.5%"*.

The tooling tax, from users:

> *"You don't grep through code to find snippets or anything, you use `ucm`…
> This is not awesome because nothing else knows how to understand this: other
> source control systems will just not work."* — [HN 40709080](https://news.ycombinator.com/item?id=40709080)

LSP support is exactly *"Autocompletion; Inline type and parser error messages;
Format on save; Show type on hover"* — **no go-to-definition, no find-references,
no rename-symbol** ([docs/language-server.markdown](https://github.com/unisonweb/unison/blob/trunk/docs/language-server.markdown)),
and it is **disabled by default on Windows**.

Chiusano, honestly: *"if you'd asked me even a year ago if Unison were a
language I'd recommend for real stuff, **I'd have said probably not!**"* and
*"actually realizing all that potential has been a colossal amount of work"*.

**GC: there is none.** No garbage-collection command exists in the UCM command
reference. `delete` removes a *name*, not a definition; *"Previously deleted
namespaces are still in the codebase's history and can be retrieved with the
`reflog` command."* For documents — which mutate orders of magnitude more than
definitions — unbounded un-GC'd history is the default failure mode of a
content-addressed store.

**Adoption:** self-reported *"1,300+ Unison project authors"* at 1.0; the FAQ's
answer to "is anyone using Unison in prod?" is *"**Yes, we are!**"* — no
independent named production user found. Unison Computing launched a
**consulting arm on 2026-02-19** offering *"Scala, Haskell, Rust, Elm, and of
course Unison"*, with the goal *"to be cash flow positive as a business in the
next 12 months"*.

### 5.5 Transferability to documents

The disanalogies hold, and Unison's own history is the evidence:

1. **Hash cannot be the identity of a mutable artifact.** A Unison definition is
   *finished* when it enters the codebase; `add`/`update` are commit points. A
   document has no commit point — content-addressing it means a new hash per
   keystroke. Unison never needed mutable-artifact identity because it has none:
   it has an immutable value space plus a mutable `Name → hash` relation. The
   mutable identity in Unison **is the name** — and where it needed nominal
   identity, it used **a UUID**.
2. **No typechecker means no reference graph.** Every Unison benefit is
   downstream of *the set of references being complete, machine-derived and
   validated*. Prose has none of that. You would build the compiler-like layer
   yourself, and Unison says how expensive that is.
3. **The transferable lesson is the opposite of the headline.** Content-address
   the *content* (dedup, integrity, immutable version refs, caching). Use a
   **stable per-artifact ID that is not the content hash** as the identity. Path
   and title become metadata.

No substantive public argument applying "names are metadata" to
documents/tables/canvases was found. **This is an unclaimed argument, not a
citable one.**

---

## 6. Versioned databases

### 6.1 Irmin — the "merge function per type" abstraction, read from source

`mirage/irmin`: 1,957 stars, **release 3.11.0 on 2025-06-19**, last push
2026-04-15. I cloned the repo and read the interface files directly.

Irmin is a git-like store parameterised over Contents, Branch and Hash, where
**the content type supplies its own three-way merge**. From
`src/irmin/contents_intf.ml`, verbatim:

```ocaml
module type S = sig
  (** {1 Signature for store contents} *)

  type t [@@deriving irmin]
  (** The type for user-defined contents. *)

  val merge : t option Merge.t
  (** Merge function. Evaluates to [`Conflict msg] if the values cannot be
      merged properly. The arguments of the merge function can take [None] to
      mean that the key does not exists for either the least-common ancestor or
      one of the two merging points. The merge function returns [None] when the
      key's value should be deleted. *)
end
```

And the merge function type itself, from `src/irmin/merge.mli`:

```ocaml
type conflict = [ `Conflict of string ]

type 'a promise = unit -> ('a option, conflict) result Lwt.t
(** An ['a] promise is a function which, when called, will eventually return a
    value type of ['a]. A promise is an optional, lazy and non-blocking value. *)

type 'a f = old:'a promise -> 'a -> 'a -> ('a, conflict) result Lwt.t
(** Signature of a merge function. [old] is the value of the least-common
    ancestor.
            /----> t1 ----\
    ----> old              |--> result
            \----> t2 ----/
*)
```

Three things are worth extracting precisely:

1. **This is the right shape.** `old -> ours -> theirs -> result-or-conflict`
   is exactly the merge-driver contract from §2.4 (`%O %A %B` → `%A`, exit
   code), expressed as a type. Irmin independently arrived at the same
   abstraction git exposes through `.gitattributes`. That is corroboration for
   the recommendation, not a reason to adopt Irmin.
2. **The ancestor is optional and lazy.** `'a promise` returns
   `('a option, conflict) result` — the merge function *must* handle "there is
   no least common ancestor", and computing the ancestor may itself fail. Any
   merge driver written for this product must handle the no-base case (a
   document created independently on two branches with the same identity)
   rather than assuming three inputs.
3. **Merge is allowed to fail, with a string.** `` `Conflict of string ``. There
   is no requirement of commutativity or associativity in the type; Irmin ships
   combinators (`seq`, `like`, `with_conflict`) rather than laws. The algebraic
   guarantees live in the *Mergeable Replicated Data Types* research line built
   on top, not in Irmin's core contract.

**Git compatibility is real but qualified.** The README claims:

> *"**Git Compatibility** - `irmin-git` uses an on-disk format that can be
> inspected and modified using Git"*

> *"**Highly Portable** - runs anywhere from Linux to web browsers and Xen
> unikernels"*

**And here is the decisive datum, from Irmin's own README.** Tezos — the one
genuine at-scale Irmin user — *started on the git backend and left it*:

> *"[Tezos](https://gitlab.com/tezos/tezos/) started using Irmin in 2017 and
> provided a 9p interface to the Irmin API. It was used to manage ledger state.
> **The first prototype used `irmin-git` before switching to `irmin-lmdb` and
> `irmin-leveldb` (and now `irmin-pack`).**"*

That is the third independent instance of the same trajectory in this document:

| Project | Content-addressed store on git | Outcome |
|---|---|---|
| **Unison** | codebase pushed/pulled via git | **removed** git support (issue #5013), moved to Unison Share; codebase moved to SQLite |
| **Tezos / Irmin** | `irmin-git` prototype | **switched off it** → lmdb → leveldb → `irmin-pack` |
| **bup** | writes real git packfiles | needed `midx`/bloom side-indexes because git's object model did not scale (see §7) |

**Three serious teams built "content-addressed objects canonical, git as the
storage/transport layer", and all three moved off git for the canonical
store.** None of them left because git's *model* was wrong — they left because
git's *implementation* was the wrong shape for a high-write-rate object store
that is not a source tree. That is the single strongest empirical argument in
this entire document, and it cuts precisely one way: **use git for what it is
good at — versioning a tree of human-scale text files — and do not promote it
into a general object store, nor demote it beneath one.**

Irmin remains a research-grade artifact for this purpose: OCaml-only (there is
a `libirmin` C binding in-tree, but no JS/TS story despite the browser claim),
one release in 14 months, and its flagship user runs the non-git backend.

### 6.2 Dolt — the most serious competitor to the plaintext-table design

`dolthub/dolt`: **24,286 stars**, v2.3.1 (2026-08-19), pushed today, **17
distinct human authors in the last 100 commits**. Doltgres 1.0 shipped
2026-08-06. This is a going concern, not a demo.

**The merge is genuinely cell-level.** Docs: *"For data, Dolt does a cell-wise
merge of data"*; *"If two operations modify the same row, column pair to be
different values, a conflict is detected."* Source
(`go/libraries/doltcore/merge/merge_prolly_rows.go`):

```go
// TryMerge performs a cell-wise merge given left, right, and base cell value
// tuples. It returns the merged cell value tuple and a bool indicating if a
// conflict occurred.
```

Comparison is **semantic, not bytewise**, which is subtler than it sounds:

> *"We can't just look at the bytes to determine this, because if a cell's byte
> representation changed, but only because of a schema change, we shouldn't
> consider that a conflict. Conversely, if there was a schema change on only one
> side, we shouldn't consider the cells equal even if they have the same bytes.
> Thus, we must convert all cells to the type in the result schema before
> comparing them."*

Verified empirically against a locally-built dolt 2.3.1: base row
`(1,'a0','b0','c0')`, one branch sets `a='LEFT'`, the other sets `b='RIGHT'` →
clean auto-merge to `(1, LEFT, RIGHT, c0)`.

**Conflicts live outside the data.** After a same-cell conflict, the *data table
is still a valid, queryable table* and the conflict sits in
`dolt_conflicts_$TABLE` with `base_a / our_a / their_a / our_diff_type /
their_diff_type` columns. Internally they are *artifacts* in a separate prolly
map (`go/store/prolly/artifact_map.go`, with types for conflicts, FK violations,
unique-key violations, check-constraint violations, null violations). **This is
the architectural idea worth taking, and §2.4 shows it is reachable in plain
git.**

**Prolly trees — and a correction most write-ups get wrong.** The canonical
property is history-independence, stated by Noms (`doc/intro.md`):

> *"A critical invariant of Noms is history-independence: the same Noms value
> will be represented by the same graph of physical chunks, and the same hashes,
> regardless of what past sequence of logical mutations resulted in the value.
> This is what makes fast diff, sync, and merge possible in Noms… The classic
> data structures that enable these features inside databases — B-Trees and LSM
> Trees — can't be used by Noms because they aren't history-independent."*

Noms chose boundaries with a rolling hash over the serialised stream (12 high
bits set → ~4 KB average, 64-byte window). **Dolt no longer does this.**
`go/store/prolly/tree/node_splitter.go`: `var defaultSplitterFactory
splitterFactory = newKeySplitter`. `rollingHashSplitter` (buzhash, 67-byte
window) still exists but is not the default. `keySplitter` hashes **only the
key** (`xxHash32(key, salt)`) against a Weibull CDF threshold (target 4 KB, min
512 B, max 16 KB, per-level salt from `sha512(level)`). DoltHub's reasons
([blog/2022-06-27-prolly-chunker](https://www.dolthub.com/blog/2022-06-27-prolly-chunker/)):
rolling-hash chunking gave a geometric size distribution whose tail chunks were
*"very expensive to copy and mutate"*, and *"popular rolling-hash functions such
as buzhash have poor output quality on sorted or low entropy input"*. The payoff
is that a fixed-width value update never moves a boundary — an update touches
exactly one leaf.

**Storage-format churn is real and total.** `go/store/constants/version.go` now
has only `FormatDoltString = "__DOLT__"`; `GetFormatForVersionString` errors on
anything else. Every pre-1.0 repo had to be rewritten. **Budget for the same if
you ever build chunked content addressing yourself** — this is the same warning
as Nix's four-and-a-half-year `ca-derivations` experiment (§7.4) and Kubo's
"only the fixed-size chunker guarantees the same CID" (§7.5).

**Where Dolt still fails**, and it is instructive that the failure is *identity*:

- **Primary-key changes are a hard stop.** `merge_schema.go`:
  `ErrMergeWithDifferentPks = errorkinds.NewKind("error: cannot merge because
  table %s has different primary keys")`, with a candid TODO: *"We'll remove
  this once it's possible to get diff and merge on different primary key sets."*
  Verified — the merge aborts entirely.
- **Keyless tables barely merge at all.** `TryMerge` returns immediately: `if
  m.keyless { return nil, false, nil }`. Docs: *"conflicts can only be generated
  in keyless tables if one side of the merge deletes a row and the other side
  adds the same row."*
- Incompatible type changes to the same column on both sides →
  `CONFLICT (schema)`, no auto-resolution.
- *"In the case of foreign keys, Dolt can produce invalid merges even after
  conflicts are resolved."*

**Dolt's own hardest problem is stable row identity.** That is the same
conclusion this document reaches from every other direction.

**Measured, and this surprised me: git beat Dolt on storage.** A 100k-row /
7.17 MB CSV plus ~100 commits each modifying 100 rows:

| | after import | after ~102 commits |
|---|---|---|
| git (packed, `gc --aggressive`) | 4,085,556 B | **4,263,123 B** |
| Dolt (`dolt gc`) | 6,702,099 B | **6,130,233 B** |

Git's zlib + xdelta packfile is ~44% smaller. Prolly trees buy O(changed-rows)
*write* cost and O(diff) *reads*, not fewer bytes at this shape and scale. Diff
did favour Dolt — `dolt diff --summary HEAD~50 HEAD` 41 ms vs `git diff` 120 ms
— real, but 3×, not asymptotic, at 100k rows. A point query was *slower* than
`grep` (36 ms vs 7 ms), dominated by process startup.

**Does Dolt already solve "structured information in version control"?**
Partly, and not for this product. It is a MySQL server, not files: the on-disk
state is `.dolt/noms/manifest` plus binary journal and table files — nothing
greppable, `sed`-able, or diffable by any tool that is not Dolt. Its git
compatibility is *analogy*, not wire compatibility: *"Git versions files. Dolt
versions tables."* No git object format, no smart HTTP, no `git clone`. And it
has one data model — SQL tables. No documents, no canvases.

### 6.3 Noms — and the inventor's own retreat

`attic-labs/noms`, README, verbatim: *"**Warning - This project is not
active.** Noms is not being maintained. You shouldn't use it, except maybe for
fun or research. If you are interested in something like Noms, you probably want
Dolt… which is a fork of this project and actively maintained."* Archived, last
push 2021-08-27. Dolt's source still carries `Copyright 2016 Attic Labs, Inc.`
headers.

Aaron Boodman's own statements are the valuable part:

- On what it was for (HN [12213886](https://news.ycombinator.com/item?id=12213886),
  2016): *"we're really more focused more on archival, version control, and
  moving data between systems than being an online transactional database."*
- On the merge algebra ([17224829](https://news.ycombinator.com/item?id=17224829),
  2018): *"The built-in merge strategies are commutative and idempotent, so if
  your operations can be merged using it, then your schema is a (state-based)
  crdt."*
- **The retreat** ([22735544](https://news.ycombinator.com/item?id=22735544),
  2020): *"it is pretty easy to make Noms (or Dolt) into a CRDT by defining a
  merge function that is deterministic. We experimented with this in Noms but
  **the result wasn't that satisfying and we didn't take it any further**."*
- Where he went ([24350000](https://news.ycombinator.com/item?id=24350000),
  2020): *"some of us have started working on https://replicache.dev/ instead,
  which shares some DNA with Noms. **But it's not decentralized.**"*

**The person who coined "prolly tree" concluded that general decentralised merge
was unsatisfying, and his next two companies went server-authoritative.** The
durable idea was content-addressed structural sharing; automatic distributed
merge was not. Read alongside `RESEARCH.md` §4's single-writer constraint, this
is corroboration, not coincidence.

### 6.4 Datomic — right about identity, absent on branching

The datom is `[entity, attribute, value, transaction, op]`, with four indexes
(EAVT ≈ row access, AEVT ≈ column access, AVET for lookup, VAET the reverse
index over refs) and `as-of` / `since` / `history` making time first class.

**The identity discipline is the transferable part.** From
[docs.datomic.com/schema/identity.html](https://docs.datomic.com/schema/identity.html):

> *"Every datom in Datomic includes a database-unique entity id… **Entity ids are
> assigned by the transactor, and never change.**"*
> *"Idents should not be used as unique names or ids on ordinary domain
> entities."*

An opaque, immutable, non-semantic key, with human names as ordinary mutable
attributes. **That is precisely the §8.3 recommendation, arrived at
independently by a system with no relationship to files.**

**But there is no branching and no merge, and Datomic says so** in a doc section
literally titled *"as-of Is Not a Branch"*: *"with plus as-of lets you see a
speculative db with recent datoms filtered out, but **it does not let you branch
the past**."* `d/with` is in-memory only. Single-writer remains explicit: *"**No
per-db write scaling: since transactions are totally serialized, only one
transaction can occur at a time in a given database**"*.

**Correct the licensing prior: free, but not open source.**
[blog.datomic.com/2023/04/datomic-is-free.html](https://blog.datomic.com/2023/04/datomic-is-free.html)
(2023-04-27): *"The Datomic binaries are being released under the Apache 2.0
license"* — and in the same post, *"**Is it Open Source? No. Datomic binaries
are provided under the Apache 2 license which grants all the same rights to a
work delivered in object form.**"* Hard proof: `com.datomic/peer` 1.0.7705's
published `sources.jar` has `content-length: 0` and SHA-1 `da39a3ee…` — the hash
of the empty file. Nubank owns it and ships it (Pro 1.0.7705, 2026-07-10).

**Is an EAVT log a better canonical model than files?** For attribute-level
granularity, perfect history and stable identity — strictly yes. For this
substrate — no: not files, not greppable, no branch/merge model at all, and a
closed-source single-writer server. **Take the identity discipline; leave the
storage.**

### 6.5 TerminusDB — rule it out

The finding that settles it: **there is no three-way merge.** The HTTP surface
(`src/server/routes.pl`) offers `clone, fetch, rebase, push, pull, branch,
squash, reset, patch, diff, apply, migration` — no `merge`.
`src/core/api/api_merge.pl` exports one predicate, `api_concat/6`, limited by
its own man page to commits *"provided they are base layers only"*. `push`/
`pull` are fast-forward-only and throw `error(divergent_history(...))`.
Reconciliation is manual optimistic-concurrency patching
(`src/core/document/patch.pl` returns `conflict(json{'@op':'Conflict',
'@expected':…, '@found':…})`). Field-granular conflicts-as-data is the right
shape, but a human must resolve every one. The CTO's own blog concedes: *"the
use of patches on structured data has not hit prime-time. The tools to make use
of it are not really there yet."*

Project status explains the suspiciously clean issue tracker: **`terminusdb.com`
returns HTTP 404.** The project was handed to DFRNT (dfrnt.com); the README's
*"Project Overview (Updated May 2026)"* credits *"the new DFRNT maintainers"*.
Commits per year: 2023 = 283, **2024 = 27**, 2025 = 651, 2026 = 468. The founder's
last commit was 2025-04-22. 1,049 of 1,059 issues were closed in a bulk sweep.
Worse: the public `terminusdb/terminusdb-store` is frozen at 2024-03-11, and
v12 builds against an **unpinned 0-star fork** (`terminus-store =
{git="https://github.com/terminusdb-org/terminusdb-store"}` — no rev, no tag).
Non-reproducible builds, single-maintainer bus factor.

### 6.6 lakeFS — the negative control that proves the point

lakeFS (5,499 stars, v1.86.0, 2026-08-05) has genuine three-way merge — *"lakeFS
first finds the merge base… and then performs a three-way merge by examining the
presence and identity of files in each commit"* — but at **whole-object**
granularity: *"As a format-agnostic system, lakeFS merges by complete files, and
format-specific or other user-defined merge strategies for handling conflicts
are on the roadmap."*

**Two users editing different rows of one Parquet file conflict.** That is
exactly what you get if you version tables as opaque files with no
format-specific driver — and it is the cleanest possible demonstration that
**the merge driver is the whole product**, not an optimisation.

For completeness: Iceberg (1.11.0) has branches, tags and `fast_forward` but
**no merge**, and *"the schema tracked for a table is valid across all
branches"* so schema cannot be branched. Delta Lake (v4.4.0) is time-travel
only and its history *expires* — `delta.logRetentionDuration` defaults to 30
days. XTDB (v2.1.0) adds bitemporality with **no branching**; its idea worth
stealing is orthogonal — valid-time as a *column convention* in the schema, so
backdated corrections do not require rewriting history.

### 6.7 What Dolt does better than a plaintext design, ranked by difficulty

1. **Conflicts as structured side-data.** Reachable in plain git (§2.4), but you
   must build it; neither daff nor any off-the-shelf driver gives it to you.
2. **Merge-induced constraint violations.** Verified empirically: branch A
   inserts `(1,'dup')`, branch B inserts `(2,'dup')` into a table with a unique
   index. Neither branch alone violates anything; the *merge* does, and Dolt
   catches it. **No per-file text merge driver can ever see this** — it has no
   cross-file view. This is the one gap a plaintext design cannot close without
   a repo-wide post-merge validation pass, i.e. rebuilding part of a database.
3. **Semantic cell comparison across schema change.** A driver comparing strings
   gets both directions wrong.
4. **O(diff) diff.** Real, but the weakest of the four at this scale — and git
   beat Dolt on bytes by 44%.

### 6.8 Irmin, revisited — the interface is right, the vehicle is not

Adding to §6.1: the git-object claim is verified *by Irmin's own test suite*.
`test/irmin-git/test_git.ml`:

```ocaml
let str = pre_hash S.Contents.t "foo" in
Alcotest.(check bin_string) "blob foo" "blob 3\000foo" str;
```

`blob 3\0foo` is byte-for-byte git's blob header (compare §1.1, where I computed
the same thing by hand). Refs are real too — `src/irmin-git/reference.ml` maps
branches to `refs/heads/%s`, tags to `refs/tags/%s`. **Caveat: the one test that
actually shells out to the git CLI is commented out** (`test_git.ml:170`, inside
`(* XXX: re-add … "cd %s && git gc" … *)`). Git-CLI round-tripping is asserted
by design and by object-format tests, but is not covered by a live test.

Two further details from the source that sharpen §6.1: LCA computation is
bounded and can fail (`type lca_error = [ `Max_depth_reached | `Too_many_lcas ]`),
and multiple LCAs from criss-cross merges are returned as a `commit list` rather
than silently collapsed the way git's `ort` synthesises a virtual base (§1.3).
That is arguably more honest than git.

And the status is maintenance mode: `main`'s last commit is **2025-11-28**, the
last release **3.11.0 on 2025-06-19** (14 months), and the 3.11.0 changelog is
entirely housekeeping (*"Add x-maintenance-intent to opam files"*, *"Update
Cmdliner usage for 2.0"*, *"Fix CI issues"*). But `irmin-pack` is genuinely at
scale: `doc/irmin-pack/design/lower_layer.md` — *"unlimited history stores can
have large upper layers (**> 500 GB for Tezos**)"*.

**Verdict: steal the interface, do not take the dependency.** Build Irmin's
`Contents.S` shape over plain files — one merge function per content type,
returning `Ok` or a conflict that carries *structure* rather than Irmin's bare
`` `Conflict of string ``, with the no-common-ancestor case explicit.

---

## 7. Content-addressed storage

### 7.1 Perkeep permanodes — the directly relevant prior art

`perkeep/perkeep`: 7,231 stars, **last push 2026-02-01**, not archived, 413 open
issues. Recent commits are `go.mod` bumps by Brad Fitzpatrick — life support,
not development.

The schema, verbatim from
[perkeep.org/doc/schema/permanode](https://perkeep.org/doc/schema/permanode):

> *"Permanodes are how Perkeep models mutable data on top of an immutable,
> content-addressable datastore."*
> *"A permanode is an anchor from which you build mutable objects. To serve as a
> reliable (consistently nameable) object, it must have no mutable state itself.
> **In fact, a permanode is really just a signed random number.**"*

```json
{"camliVersion": 1,
 "camliType": "permanode",
 // Required.  Any random string, to force the digest of this
 // node to be unique.  Note that the date in the ASCII-armored
 // GPG JSON signature will already help it be unique, so this
 // doesn't need to be a great random.
 "random": "615e05c68c8411df81a2001b639d041f"
<REQUIRED-JSON-SIGNATURE>}
```

Mutation is a separate signed claim blob:

```json
{"camliVersion": 1,
 "camliType": "claim",
 "camliSigner": "....",
 "claimDate": "2010-07-10T17:20:03.9212Z",
 "permaNode": "sha1-xxxxxxx",        // what is being modified
 "claimType": "set-attribute",
 "attribute": "camliContent",
 "value": "sha1-yyyyyyy",
 "camliSig": .........}
```

> *"The state of a permanode is the result of combining all attribute-modifying
> claims which reference it, in order."*
> *"All claims must be signed."*

`claimType` ∈ {`add-attribute`, `set-attribute`, `del-attribute`, `multi`}. Note
`multi` — atomic multi-object mutation — is marked **"NOT IMPLEMENTED YET (see
issue 110)"**, which tells you how far the design got.

**This is the canonical answer to "stable identity for a mutable thing on top
of immutable content addressing", and the answer is: you cannot derive it from
content — you mint a random number and make it addressable.** A permanode is a
UUID with a signature and a hash wrapper. The content pointer
(`camliContent → sha1-…`) is a *claim*, not the identity.

Translated to this product: **a UUID in the document's frontmatter is a
permanode without the ceremony.** The signature buys attribution and
tamper-evidence; git commits already provide both (and optionally GPG/SSH
signing). The claim log buys attribute-level history; git's commit history over
a file already provides that.

### 7.2 bup — where git's object model actually breaks, from the implementers

bup writes *real git packfiles* for backups (7,340 stars, last push
2026-08-22), which makes its `DESIGN.md` the best primary source on git's
scaling limits written by people who chose git's format on purpose. Verbatim:

> *"**Git isn't actually designed to handle super-huge repositories.** Most git
> repositories are small enough that it's reasonable to merge them all into a
> single packfile, which 'git gc' usually does eventually."*

> *"The problematic part of large packfiles isn't the packfiles themselves —
> git is designed to expect the total size of all packs to be larger than
> available memory, and once it can handle that, it can handle virtually any
> amount of data about equally efficiently. **The problem is the packfile
> indexes (.idx) files.**"*

The worked cost, in their words:

> *"Say you have 24 million objects (containing around 200 GB of data) spread
> across 200 packfiles of 1GB each. To look for an object requires you search
> through about 122000 objects per pack; ceil(log2(122000)-7) = 10, so you'll
> have to search 10 times… which makes 600-800 4k pages (2.4-3.6 megs)… every
> single time you want to look for an object."*

And the reason git normally escapes this — a reason that **does** apply to a
document product and **does not** apply to backup:

> *"**git users spend most of their time examining existing objects** (looking
> at logs, generating diffs, checking out branches), which lends itself to the
> above optimization [MRU pack search]. bup isn't so lucky."*

bup's fix (`midx`, then bloom filters) is explicitly outside git:

> *"midx files are a bup-specific optimization and git doesn't know what to do
> with them. However, since they're stored as separate files, they don't
> interfere with git's ability to read the repository."*

**Read against this design:** the failure mode is millions of objects and
write-heavy access patterns. A document workspace has a read-heavy access
pattern and object counts in the thousands-to-low-millions — squarely in the
regime git is optimised for. `RESEARCH.md` §4 already measured 100k markdown
files with `git status` under 0.1 s. bup's warning is a reason not to put
*attachments* in git (which `RESEARCH.md` §4 already concluded: 21 revisions of
a 2 MB image cost 20.6× a single copy), not a reason to avoid git for documents.

bup also flags the directory-shape issue:

> *"git doesn't handle frequently changing large directories well either, since
> they're stored in a single tree object using up 28 bytes plus the length of
> the filename for each entry"*

Measured here: a flat directory of 10,000 realistically-named markdown files
produces a **658,890-byte tree object**, and touching one file produces a
complete new tree of the same size (git then delta-compresses it — observed
delta depth 298). Sharding the same 10,000 files two levels deep cut the packed
repo from 61 KB to 42 KB over 31 commits. **Minor, but free: shard document
directories rather than keeping one flat folder**, which the product wants
anyway for workspace/folder structure.

### 7.3 git-annex — the mature, shipped version of the technique to copy

Latest release **10.20260717**; HEAD commit **2026-08-28** (today); 269 of the
last ~320 commits since 2026-06-01 are Joey Hess's; 48,209 commits since 2010.
**This is the only content-addressing-adjacent system in this survey that is
unambiguously thriving**, and it is not a coincidence that it is the one that
treats content addressing as an implementation detail underneath ordinary
files.

The key format (`doc/internals/key_format.mdwn`):

```
BACKEND[-sNNNN][-mNNNN][-SNNNN-CNNNN]--NAME
SHA256E-s31390--f50d7ac4c6b9…cc0.mp3
```

**The git-annex branch** — an orphan branch of append-only logs
(`doc/internals.mdwn`), verbatim:

> *"This branch is not connected to your master, etc branches. It it used for
> internal tracking of information about git-annex repositories and annexed
> objects."*
> *"The files stored in this branch are all designed to be auto-merged by simply
> concacenating them together. **So each line has a timestamp, to allow the most
> recent information to be identified.**"*

Location log lines look like:

```
1287290776.765152s 1 e605dca6-446a-11e0-8b2a-002170d25c55
1287290767.478634s 0 26339d22-446b-11e0-9101-002170d25c55
```

**Union merge is git-annex's own, and the mechanism is sorted set-union.** From
`Git/UnionMerge.hs`:

```haskell
calcMerge :: [(Ref, [L8.ByteString])] -> Either Ref [L8.ByteString]
calcMerge shacontents = case reusable of
	[] -> Right new
	(r:_) -> Left $ fst r
  where
	reusable = filter (\c -> sorteduniq (snd c) == new) shacontents
	new = sorteduniq $ concat $ map snd shacontents
	sorteduniq = S.toList . S.fromList
```

Set-union is commutative, associative and idempotent, so **merge order cannot
matter and conflicts are structurally impossible.** It stages into a dedicated
`.git/annex/index`, not the working index.

**Three refinements that git's built-in `merge=union` does not give you**, and
all three are load-bearing:

1. **Vector clocks, not wall clocks.** `Annex/VectorClock.hs`:
   > *"These are basically a timestamp. However, when logging a new value, if
   > the old value has a vector clock that is the same or greater than the
   > current vector clock, the old vector clock is incremented. **This way,
   > clock skew does not cause confusion.**"*

   ```haskell
   advanceVectorClock (CandidateVectorClock c) prevs
       | prev >= VectorClock c = case prev of
           VectorClock v -> VectorClock (v + 1)
   ```
   Resolution is still last-write-wins, but on a *monotonic* clock that can only
   advance past what it has already seen. Roughly ten lines of code.

2. **Tombstones.** `doc/design/metadata.mdwn`:
   > *"Two disconnected repositories can make changes to the values of a field…
   > and when this is union merged back together, the changes need to be able to
   > be replayed… To make that work, we log not only when a field is set to a
   > value, **but when a value is unset as well.**"*
   ```
   1287290776.765152s tag +foo +bar
   1291237510.141453s tag -bar
   ```
   Without this, removals resurrect on merge.

3. **Sharded log paths** — `aaa/bbb/<key>.log`, from the first six hex of
   md5(key), *"to avoid issues with too many files in one directory"*
   (`doc/internals/hashing.mdwn`). Same lesson as §7.2's tree-size finding.

**Renames are free, for exactly the reason this document recommends.**
`doc/walkthrough/renaming_files.mdwn`: *"You can use any normal git operations
to move files around, or even make copies or delete them."* Identity lives in
the **key inside the pointer's content**; the path is just a tree entry, so a
rename touches `master` only and the metadata branch is untouched. Substitute
"UUID in frontmatter" for "key in symlink target" and you get the identical
property with none of the hashing — which is precisely the §8.3 recommendation,
validated by a system that has shipped it for fifteen years.

**Cost, stated honestly:** the branch grows forever. git-annex needed journaling
(`.git/annex/journal/`), an append fast path, line compaction, and
`git annex forget` — which writes a `transitions.log` entry that *propagates*:
*"When this rewritten branch is merged into other clones… git-annex will
automatically perform the same rewriting to their local git-annex branches."*
Budget for at least compaction if you adopt this.

### 7.4 Nix — and a correction to my own premise

I went in expecting Nix to demonstrate "opaque hash + free-form human label in
one path". **That is wrong, and the correction matters.** Store path spec
(https://nix.dev/manual/nix/latest/protocols/store-path):

```ebnf
store-path  = store-dir "/" digest "-" name
fingerprint = type ":sha256:" inner-digest ":" store ":" name
```

> *"Note that it includes the location of the store as well as the name to make
> sure that changes to either of those are reflected in the hash."*

Dolstra's thesis (p. 93) is explicit:

> *"both the Nix store path and the symbolic name are part of the hash… sources
> or outputs that are identical except for their symbolic names have different
> hash parts."*

**In Nix the name is inside the identity.** Two byte-identical artifacts with
different names get different digests, and renaming produces a different store
path. That is correct for immutable build outputs and exactly wrong for
documents people rename. The digest is SHA-256 XOR-folded to 160 bits, and even
that is a filesystem-path-length concession, not a security choice. No primary
source was found claiming greppability or `ls` legibility as a design motive —
treat that as folklore.

**The transferable half is the layering, not the path format.** Nix keeps
stable human-meaningful paths on top and content-addressed dedup underneath and
invisible (`nix-store --optimise` hard-links into `.links`, named by content
hash). Apply that shape: human paths above, content hashing only in a side
index. **Do not put a hash in a filename** — it changes on every edit and
breaks every editor, every link, and git's own rename detection.

**And take the warning.** `ca-derivations` is *still* an experimental feature at
Nix HEAD on 2026-08-28 (`src/libutil/experimental-features.cc`), with the
"ca-derivations stabilisation" milestone still open (24 open / 61 closed, last
updated 2026-08-14) — **four and a half years after RFC 62 merged on
2022-01-12.** A well-funded team with strong incentives has not finished making
a store content-addressed. That is the single strongest cautionary datum
against building one here.

### 7.5 IPFS — do not build on it, and the reason is four days old

CID v1 is `<multicodec-cidv1><multicodec-content-type><multihash>`
(https://specs.ipfs.tech/cid/). IPLD's data model adds a `Link` kind
implemented as CIDs. Kubo's default chunker is **fixed-size 256 KiB**, and the
config doc says why:

> *"Only the fixed-size chunker (`size-<bytes>`) guarantees that the same data
> will always produce the same CID. The `rabin` and `buzhash` chunkers may
> change their internal parameters in a future release."*

**That is the most important sentence in this section for anyone tempted to
build a CAS: your chunker becomes part of your identity function, permanently.**
Content addressing is only stable if the chunking is deterministic and frozen by
spec.

IPNS exists because *"Each time a file is modified, its content address
changes"* — the same admission as Perkeep's permanode, from the other direction.
Kubo defaults: `Ipns.RecordLifetime` 48 h, `Ipns.RepublishPeriod` 4 h. The
official docs concede *"publishing and resolving IPNS names using the DHT can be
slow"*.

Measured, from Trautwein et al., SIGCOMM '22
([arXiv:2208.05877](https://arxiv.org/abs/2208.05877)):

> *"The overall publication process across all regions takes **33.8 s, 112.3 s,
> and 138.1 s** in the 50th, 90th, and 95th percentiles… On average, the DHT
> walk covers 87.9 % of the overall delay."*
> *"The majority of content retrieval operations take at least **four times as
> long as the equivalent HTTPS request**… This could be characterized as the
> 'cost of decentralization'."*

**And the governance answer, published four days before this research.**
Interplanetary Shipyard, **2026-08-24**,
[ipshipyard.com/blog/2026-the-end-of-ipfs-at-shipyard/](https://ipshipyard.com/blog/2026-the-end-of-ipfs-at-shipyard/):

> *"Protocol Labs has informed us that it will not be renewing Shipyard's
> funding."*
> *"Our final day of our IPFS related work will be **September 30, 2026**."*
> *"Projects maintained by Shipyard will no longer have dedicated maintainers
> responsible for new features, bug fixes, releases, or long-term stewardship.
> These include: Kubo, Helia, Boxo, Rainbow, IPFS Desktop, IPFS Companion…"*

Corroborated in-repo: a Kubo commit dated **2026-08-25**, `chore: remove @lidel
from CODEOWNERS`, citing that post. Kubo commits since 2026-06-01: lidel 61,
gammazero 13, dependabot 12 — the two humans carrying the reference
implementation lose funding in about a month. Shipyard was itself the 2024
spinout following Protocol Labs' 2023 layoffs of *"89 roles (approximately
21%)"*.

The gateway retrospective, blog.ipfs.tech, **2026-08-25**:

> *"IPFS gateways were always meant to be a stepping stone… Over time,
> **hardcoded gateway URLs spread across the web and traffic re-centralized
> around a small number of public gateways.**"*
> *"**Rate limiting** has begun on ipfs.io and dweb.link…"*

**Verdict: rule IPFS out.** Not on ideology — on measured latency and a bus
factor that goes to zero on 2026-09-30.

### 7.6 Chunking and backup systems — the scale calibration

- **bup**: 8 KiB average chunks via a 64-byte rolling window (*"Why 64? No
  reason. Literally. We picked it out of the air."*) → 24 M objects for 200 GB,
  and two bespoke index layers to survive it.
- **restic** (`doc/design.rst`): Rabin CDC, 64-byte window, *"Files smaller than
  512 KiB are not split, Blobs are of 512 KiB to 8 MiB in size. The
  implementation aims for 1 MiB Blob size on average."* Default pack 16 MiB. The
  polynomial is randomised per repository and stored in `config` *"so that
  watermark attacks are much harder"*. 35,762 stars, v0.19.1 (2026-07-05).
- **casync**: 64 KiB avg / 16 KiB min / 256 KiB max, buzhash. **Dormant** — last
  release `v2` on 2017-07-26.

**Calibration:** bup at 8 KiB needs `midx` + bloom; restic at 1 MiB needs
neither. 128× fewer objects removes the problem entirely. **For documents,
tables and canvases, whole-file addressing is right; sub-file CDC buys nothing
until you have large binary attachments** — which is exactly where
`RESEARCH.md` §4 already put it (21 revisions of a 2 MB image at 20.6× a single
copy).

### 7.7 GC — four systems, four answers, two of them admittedly unsound

- **Git**: mtime + two-week grace period, and it says so (§1.5b). Cruft packs
  (default-on since 2.41.0) exist because the grace period would otherwise
  strand unreachable objects loose; `gitformat-pack.adoc` warns that *"given
  enough unreachable objects, this can lead to inode starvation and degrade the
  performance of the whole system."*
- **Nix**: `/nix/var/nix/temproots` per-process files, a global GC lock, and a
  Unix-socket handshake so a running evaluator can register a new root
  mid-collection — with a live acknowledged race
  ([NixOS/nix#11923](https://github.com/NixOS/nix/issues/11923)).
- **restic**: an exclusive lock plus strict write ordering (packs → index →
  snapshot), read top-down, 30-minute staleness window.
- **Perkeep**: none at all. `pkg/gc/gc.go` is dead code — nothing imports it.
  Brad Fitzpatrick, issue #792 (2018-03-20): *"Just play with it and see. Hint:
  it won't. :) I've been using it for years and my disks keep getting larger
  faster than I acquire data. **And also I never delete anything, so a GC would
  be kinda useless.**"* `doc/principles.md`: *"Disk is cheap and getting
  cheaper. No need to delete in general."* The recurring user objection is
  exactly this — HN 18008932: *"> no delete support / Yeah that's a show
  stopper"*.

**The decision consequence is blunt: if documents are ordinary tracked files in
a git tree, you inherit git's GC for free. If they are blobs in a side CAS, you
must build a second reachability collector, and every system here that tried
either got it wrong or gave up.**

### 7.8 Perkeep, revisited — the permanode's actual flaws

Two things I would have copied naively, and should not:

1. **Claim ordering is last-write-wins on a client-supplied timestamp with no
   defence.** The schema doc says `claimDate` *"takes precedence over any date
   inferred from camliSig"*. State is `sort.Sort(ClaimPtrsByDate)` then fold
   (`pkg/index/corpus.go`), and `sort.Sort` is not stable, so equal dates fold
   in unspecified order. Signature verification on permanodes was missing until
   2022 — issue #1328: *"I modified a permanode by just changing its `claimDate`
   to 1970-01-02 … I expected the server to complain about a signature check
   failure, but nothing bad happened."* Anyone holding the key — including your
   own device with a wrong clock — wins every future race by writing
   `claimDate: 2999-…`. **git-annex's vector clock (§7.3) is the fix, and it is
   ten lines.**
2. **State requires an indexer.** The good news is that the index is fully
   rebuildable (`doc/overview.md`: *"you can lose your index at any time… just
   delete it all and re-replicate"*, implemented as `Index.Reindex()`). The bad
   news is that you cannot read an object's current state with `cat`.

**Project status:** funding ended in 2019 (Brad, on the mailing list: *"I can't
afford to pay Mathieu what he's worth… you should probably stop or at least
pause your donations, as I have nobody to send the money to."*), v0.12 shipped
2025-11-11 after a five-year gap with the release note *"I guess I got
distracted at my new job (Tailscale) (and kids)"*, and `doc/status.md` still
reads *"Last updated: 2013-02-02"*.

**Net: the permanode idea is right and Perkeep's implementation of it is not the
one to copy.** Take the idea (a minted, meaningless, stable ID for a mutable
thing), take git-annex's mechanics (append-only log, set-union merge, vector
clocks, tombstones), and skip the GPG ceremony and the mandatory indexer.

---

## 8. Synthesis — the architecture question

### 8.1 Is there a coherent "content-addressed canonical, git as transport" design?

Yes, and three projects built it. Their outcomes:

- **Unison** built it, used git as transport, found it janky ("stashed large
  SQLite database files on GitHub"), and **deleted git support** rather than
  reimplement sync (issue #5013). It then moved its canonical store from a
  directory tree to **SQLite** for performance.
- **Perkeep** built it, and is on life support — no GC at all, a five-year
  release gap, and claim ordering with a backdating hole (§7.1, §7.8).
- **Irmin** built it as a *library*, correctly (§6.1, §6.8) — and its flagship
  user, Tezos, **started on `irmin-git` and moved off it** to lmdb, then
  leveldb, then `irmin-pack`.
- **bup** built it on git's actual packfile format and had to add non-git
  `midx` and bloom side-indexes to survive (§7.2).
- **Noms/Dolt** built the storage half brilliantly and abandoned the
  decentralised-merge half: *"the result wasn't that satisfying and we didn't
  take it any further"* — and its author's next company was explicitly *"not
  decentralized"* (§6.3).

The recurring pattern: the content-addressed store wins on identity and
integrity, then loses on *sync, GC, and tooling*, and ends up reimplementing
the parts of git it bypassed. Unison's own words are the cleanest statement of
the failure mode: continuing to support git *"would require re-implementing most
git sync methods."*

### 8.1b I built the thing, and measured it

Rather than argue, I implemented the minimal honest version of
"content-addressed objects canonical, git as transport": documents stored as
`objects/<aa>/<sha256>` with a `names/<human-name>` index holding the current
hash, versus the same corpus as plain files at human paths. 500 documents, 41
revisions, 25 documents edited per revision, `git gc --aggressive` on both.

|  | plain files | CAS-in-git | ratio |
|---|---|---|---|
| `.git` (packed) | 368K | 936K | **2.5×** |
| working tree | 2.0M | 8.9M | **4.5×** |
| files in working tree | 500 | 2000 | **4.0×** |
| git objects | 1623 | 4332 | **2.7×** |

`git status` and `git grep` stayed fast in both (0.01 s) — performance is not
the problem at this scale. **The problem is that the working tree accumulates
every version forever and you now own a second GC.** Git's own GC cannot help:
every object is reachable because `objects/` is a tracked directory in HEAD.
You must write a mark-and-sweep over `names/`, decide a retention policy, and
delete tracked files — which is itself a commit, which is more history.

And the human-facing failure is immediate:

```
# plain files
$ grep -rl "doc 42" docs/
docs/d429.md
$ $EDITOR docs/d42.md

# CAS-in-git
$ grep -rl "doc 42" objects/
objects/5e/5e8145217e3dd0e7f086dedec494248b5279d03dadff2fd2510d447798fc5d82
$ $EDITOR objects/$(cat names/d42.md | cut -c1-2)/$(cat names/d42.md)
```

`grep`, `rg`, `fzf`, an editor's file switcher, GitHub's blob view, and the MCP
Filesystem server all return the hash. **The name is no longer in the data; it
is in a side table, and every tool that does not know about the side table is
now useless.** That is precisely the Unison outcome (§5.4) reproduced in
miniature, and it took forty lines of Python to reproduce it.

### 8.1c The table case, settled empirically

lakeFS proves that whole-file merge is useless for tables (§6.6); Dolt proves
cell-keyed merge works (§6.2). The open question was whether plain git plus a
driver reaches Dolt's behaviour. **It does.**

The hardest ordinary case is a *pure sort* — an operation that changes no data
at all — concurrent with an unrelated cell edit. Under stock git:

```
$ git merge bob
Automatic merge failed; fix conflicts and then commit the result.
$ cat t.csv
id,name,qty
<<<<<<< HEAD
=======
1,widget,11
2,gadget,20
>>>>>>> bob
3,doohickey,30
2,gadget,20
1,widget,10
```

Not merely conflicted — **corrupt**: row 2 appears twice, and Bob's edit
(`qty 10→11`) sits inside a marker block while a stale `1,widget,10` survives
below it. Any user who resolves this by deleting markers loses data.

With a stable `id` column and a ~40-line id-keyed merge driver, the same merge:

```
$ git merge bob
 1 file changed, 2 insertions(+), 2 deletions(-)
$ cat t.csv
id,name,qty
1,widget,11
2,gadget,20
3,doohickey,30
```

Clean, correct, and **row order has become irrelevant — exactly Dolt's
semantics.** The driver matches rows by ID, merges per-column against the base,
and re-emits in canonical ID order. That is the entire mechanism, and it closes
three of Dolt's four advantages (§6.7) in code you can write in an afternoon.

**The one it does not close is #2: merge-induced constraint violations.** Two
individually-valid branches inserting the same unique value is invisible to a
per-file driver. The mitigation is a repo-wide post-merge validation pass — and
naming it now is the honest thing to do, because it is the point at which this
design starts growing a database engine.

### 8.2 What specifically breaks

**Human-readable filenames.** In a pure CAS the filename is a lookup in a side
index. Nix's pattern —
`/nix/store/<hash>-<name>` — shows you can have both, and it is worth copying
*in the opposite direction*: keep the human name as the path, put the opaque ID
*inside* the file. That way the path is the affordance and the ID is the truth,
and neither depends on the other.

**Normal tools.** This is where the CAS designs die. Unison users cannot grep;
`ucm` replaces the shell. For a product whose entire pitch is "your documents
are files you own", a store that `grep`, `rg`, `$EDITOR` and GitHub cannot read
is a contradiction of the premise. `RESEARCH.md` §7 already established that the
MCP steering group maintains exactly two document-substrate reference servers —
**Filesystem and Git** — and archived the Google Drive one. A CAS breaks both.

**Garbage collection.** Every CAS in this survey either has no GC (Unison:
none; jj: none for its own data, issue #12) or has a hard concurrency problem.
Git at least has an answer (`gc.pruneExpire`, a two-week grace period). Building
a CAS means owning this problem, and documents mutate far more than code
definitions.

**Reimplementing git badly.** The honest test: what would the CAS layer add that
git's object store does not already provide? Content addressing — git has it.
Dedup — git has it, and §1.5 measured 51 revisions of a 7.9 MB corpus at 748 KB.
Integrity — git has it. Immutable version references — git has it. The only
thing git lacks is **artifact identity**, and that is one UUID in a file, not a
new storage engine.

### 8.3 Does anything here mean we should NOT use plain files in git?

**No.** Nothing in this research falsifies plain files in git. What it does is
identify four things the design must add on top, and one thing it must stop
relying on.

**Must add:**

1. **A UUID in every artifact.** Frontmatter for `.md`, a reserved column or
   header comment for tables, a root attribute for canvases. This is the
   permanode pattern, it is what Unison arrived at for nominal types, and it is
   what makes rename a non-event. Verified on a single file:

   ```
   $ git show --stat --format= HEAD     # rename + total rewrite
    doc.md                    | 6 ------
    totally-different-name.md | 6 ++++++
   $ git grep -l "8c6d1570-8eed-4822-9e9f-c621c4336f3d" HEAD
   HEAD:totally-different-name.md
   ```
   Rename detection failed completely; the identity survived, and it is
   greppable by any tool.

   **And verified at scale.** A repo of 2,000 markdown documents, 51 commits,
   ~250 renames, with the tracked document renamed twice with a heavy rewrite
   each time (defeating the 50% similarity threshold). The document ended up at
   `docs/renamed_45_T30.md` having started at `docs/d0.md`:

   ```
   -- path-based: git log --follow on the final path --
   3                             # THREE of fifty-one commits
   real	0m0.069s

   -- identity-based: scan every commit for the UUID --
   51                            # ALL of them
   real	0m0.639s

   -- distinct paths this document has occupied --
   docs/d0.md
   docs/T10.md
   docs/T30.md
   docs/renamed_45_T30.md
   ```

   **`git log --follow` silently returned 6% of the document's history. The
   UUID scan returned 100% of it, and recovered all four paths.** This single
   result is the strongest argument in the document for UUID-in-file identity,
   and it is a complete answer to "isn't the path good enough?".

   Cost: the scan is O(commits × repo grep) — 0.64 s at 51 commits here, so it
   needs a derived index at 10k+ commits. That index is rebuildable from the
   repo and belongs in the **gitignored** SQLite FTS5 store already specified in
   `RESEARCH.md` §6, alongside search. It is a cache, not a source of truth,
   which is the property that kills every "canonical store beside git" design.

   **The honest objection, tested: copying breaks it.** A UUID in the file is
   duplicated by anything that duplicates bytes — `cp`, Finder "Duplicate",
   "Save As", instantiating a template, or a user-side script:

   ```
   $ cp plan.md plan-copy.md && git add . && git commit -m "duplicated outside the app"
   $ git grep -l "11111111-2222-3333-4444-555555555555" HEAD
   HEAD:plan-copy.md
   HEAD:plan.md
   ```

   Two files now claim one identity. This is the real cost of UUID-in-file, and
   it has no elegant fix — but it has a cheap and complete one: **detection is a
   one-liner and can run on every open and every commit.**

   ```
   $ git grep -h '^id: ' HEAD -- '*.md' | sort | uniq -d
   id: 11111111-2222-3333-4444-555555555555
   ```

   Policy: on detecting a duplicate, the app re-mints an ID for the file with
   the later mtime and records the provenance (`derived-from: <uuid>`). Note
   Perkeep has the identical exposure — copying a permanode blob copies its
   identity — and Unison's `unique` types have it too (copy-pasting a type
   definition copies its UUID); neither has a better answer. This is a known,
   bounded cost of minted identity, not a defect specific to this design.

   **And the ID line does not create merge noise**, verified: because it never
   changes, it never participates in a conflict. Concurrent edits to the title
   and to two different paragraphs merged cleanly with the `id:` line untouched.

2. **Custom merge drivers, installed by the app.** §2.4 proves this is the only
   mechanism that keeps a structured file well-formed through a conflict, and it
   works in stock git including during rebase. `daff` for CSV; a small
   schema-aware driver for the sheet/canvas formats.

3. **`conflict-marker-size=32` in `.gitattributes` for markdown.** §2.2. Cheap,
   and it converts a silent rendering corruption into a visible one.

4. **The `change-id` commit header convention.** §3.1. Sixteen bytes, writable
   with any git library, survives GitHub, and gives change identity across
   rewriting — which is what makes "this edit" a durable thing to comment on,
   review, or link to. Free interop bonus: a user who points jj at the repo gets
   correct change tracking.

5. **A stable row ID in tables, and an ID-keyed merge driver.** §8.1c. Without
   it a sort corrupts the file; with it, tables merge with Dolt's semantics.
   This is the same conclusion Dolt reaches from the other side — its one hard
   stop is `ErrMergeWithDifferentPks` (§6.2) — and the same one Datomic reaches
   independently: *"Entity ids are assigned by the transactor, and never
   change"*, names are ordinary mutable attributes (§6.4).

6. **An orphan metadata branch with set-union merge, vector clocks and
   tombstones**, for anything that must never block a merge. git-annex's design
   (§7.3), which is fifteen years mature. Not Perkeep's per-claim signed blobs
   (§7.8).

**Must stop relying on:** `git log --follow`, `git blame` for authorship
attribution, and rename detection generally. All three are heuristics whose
answers change with a flag (§1.2, §1.4). Compute document history by scanning
for the UUID, not by following paths.

**Must accept as unfixed:** semantic conflicts that merge cleanly (§2.5), and
merge-induced cross-file constraint violations (§6.7). No system surveyed
solves the first; only a real database solves the second.

### 8.3b The identity design, concretely

Four different questions get conflated by every system surveyed. Separate them
and each has an easy answer.

| Question | Mechanism | Why |
|---|---|---|
| **Which artifact is this?** | UUIDv4/v7 minted at creation, stored **inside the file** | Survives rename, rewrite, move, and copy-detection failure (§8.3). Greppable by every tool. This is Perkeep's permanode without the ceremony (§7.1) and what Unison converged on for `unique` types (§5.2). |
| **Which version of it is this?** | the git blob SHA | Free, already exists, already deduplicated, already integrity-checked. Never expose it as the artifact's identity — it changes on every keystroke. |
| **Which change is this?** | 16 random bytes in a `change-id` commit header | Survives amend/rewrite; portable through GitHub (§3.1). Gives durable anchors for comments, review, and "what changed in this edit". |
| **What is it called / where does it live?** | path + `title:` | **Metadata.** Free to change, never referenced by anything durable. |

Concretely, per artifact type:

```yaml
# document.md — YAML frontmatter
---
id: 018f3a7c-9b2e-7c41-a0d3-4f21b8e6c5aa   # UUIDv7: sortable by creation time
title: Q3 hiring plan
---
```

For tables, the ID belongs on a **row** as well as the sheet, because
`RESEARCH.md` §3 already established that positional row addressing merges into
silently wrong numbers. A reserved first column solves identity and merge at
once — a cell-level merge driver can then match rows by ID rather than by
position, which is exactly the correspondence that made named columns win:

```csv
_id,item,qty,unit
r-01J8Z,widget,10,5
r-01J90,gadget,20,3
```

For canvases, the same on each node — which every canvas format already has,
since shapes need stable references for edges.

**Cross-artifact links must be `[title](id:018f3a7c-…)` or equivalent, not
paths.** This is the single decision that makes rename genuinely free, and it
is the one place where the design deliberately pays an ergonomic cost: a raw
`.md` file viewed on GitHub shows an opaque link. Mitigation is the Nix pattern
(§8.2) applied to links rather than paths — carry both, with the human part
first and the ID as the authority: `[Q3 hiring plan](id:018f3a7c-…)` reads
correctly in any markdown renderer, and the resolver ignores the label.

**Three invariants the app must enforce**, each cheap:

1. **Mint on create, never on save.** An ID that changes is worse than no ID.
2. **Detect duplicates on open and on commit**
   (`git grep -h '^id: ' | sort | uniq -d`, §8.3). Re-mint the later copy and
   record `derived-from`.
3. **Never delete an ID from a file.** Treat frontmatter `id:` as immutable in
   the editor — it must not be user-editable text in the live-preview surface.

### 8.4 Adversarial summary — what would falsify each option

| Option | Falsified if… | Status |
|---|---|---|
| **Plain files in git** | conflicts in structured files could not be kept well-formed | **survives** — merge drivers do it (§2.4) |
| | artifact identity could not survive rename | **survives** — UUID-in-file (§8.3) |
| | history/size costs were prohibitive | **survives** — 748 KB for 51 revisions of 7.9 MB (§1.5) |
| | forge-side merges were essential | **partially wounded** — merge drivers don't run on GitHub's merge button (§2.4). Mitigated by the single-writer constraint. |
| **jj as the engine** | no automatic per-path merge drivers | **falsified** — #53 open since 2022, #8071 open (§3.4) |
| | library API unstable, no JS/mobile story | **falsified** — explicitly experimental, no wasm (§3.4) |
| **Pijul / patch theory** | conflicts still materialise as broken files | **falsified** (§4.2) |
| | library unadopted and undocumented | **falsified** — 2,246 downloads, 14% documented (§4.2) |
| **Content-addressed canonical store** | it breaks grep/editors/forges | **falsified** — measured, 4.5× working tree and hashes in every tool (§8.1b, §8.2) |
| | prior art tried git-as-transport and abandoned it | **falsified** — Unison #5013, Tezos left irmin-git, bup needed midx (§5.4, §6.1, §7.2) |
| **Darcs** | exponential merge unfixed in a supported format | **falsified** — darcs-3 "UNSTABLE… NOT for serious work" since 2020 (§4.1) |
| **Dolt as the substrate** | it is not files; no documents or canvases | **falsified for this product** — opaque `.dolt/noms/*`, SQL tables only (§6.2) |
| **Plaintext tables specifically** | a sort concurrent with an edit corrupts the file | **survives, conditionally** — stock git corrupts it; an id-keyed driver merges it correctly (§8.1c). **Conditional on a stable row ID.** |
| | merge-induced constraint violations undetectable | **wounded, not fatal** — needs a repo-wide post-merge validation pass (§6.7, §8.1c) |
| **IPFS as any part of this** | maintainers defunded | **falsified** — Shipyard IPFS work ends 2026-09-30 (§7.5) |
| **TerminusDB** | no three-way merge exists | **falsified** — no `merge` endpoint at all (§6.5) |

---

## 9. What could not be verified

- Any figure for Google-internal jj adoption. Only that Google funds 41
  contributors and runs a private cloud backend.
- Whether GitLab still strips the `change-id` header (jj's own v0.30.0
  changelog claims it did; not tested against a live GitLab). GitHub verified
  to preserve it, 26/30 recent commits.
- `jj-lib` compiling to `wasm32` — inferred impossible from zero wasm references
  plus the `gix`/filesystem/fsmonitor surface; not attempted.
- Jacobson, *"A formalization of Darcs patch theory using inverse semigroups"*
  (UCLA CAM 09-83, 2009) — cited in the darcs bibliography, but the UCLA URLs no
  longer resolve. Existence confirmed; contents not read.
- Pijul's behaviour on Zooko's badmerge — not tested empirically (pijul is not
  installed; per the machine's global rules, no ad-hoc installs). The
  darcs-correct result is Zooko's claim, not a measurement here.
- Pijul large-repo performance (Linux kernel import: "approximately 41 minutes"
  to record, "over 305 minutes" to switch channels) — from a search snippet
  only; the Nest discussion page 404s.
- darcs issue1401 / issue2605 current status — `bugs.darcs.net` returns HTTP 500.
- Any independent, non-vendor production user of Unison.
- DoltHub's funding, revenue or headcount — no primary source found. Treat
  "well funded" as unestablished; the 17-human commit log and shipping cadence
  are the evidence that stands.
- The Attic Labs → Salesforce acquisition date, from a primary source.
- TerminusDB Ltd's legal disposition — no filing, press release or handover
  announcement found, only the README's DFRNT attribution and a 404 homepage.
- Irmin's git-CLI round-trip end to end. Asserted by design and proven at the
  object-format level (`blob 3\0foo` in its own tests); the live `git gc` test
  is commented out and no OCaml was built here.
- Datomic's July-2020 Cognitect acquisition announcement (original post 404s).
- git-annex's rename behaviour empirically — documented and read from source,
  not executed (git-annex is not installed and per this machine's rules it was
  not installed ad hoc). Worth a five-minute confirmation before relying on it.
- Perkeep's two suspected corpus bugs (future-dated claims taking effect via the
  `valuesAtSigner` fast path; `cacheAttrClaim` ignoring `IsDeleted`) were read
  from code, not reproduced.
- Nix greppability as a *documented* design motive — **not found; treat as
  folklore.** The documented motives are dependency hash-scanning and preventing
  sources from impersonating outputs.
- Storage and latency comparisons against Dolt come from a single 100k-row
  synthetic workload on this machine. Do not generalise without re-measuring at
  real scale.
- **That GitHub's server-side merge does not run custom merge drivers.** This is
  structurally near-certain (a driver is a local executable named in
  `.git/config`), but I found no GitHub documentation stating it and did not run
  a live test. Confirm before relying on it.
- Whether git 2.55 (current upstream) changes any rename-detection or merge
  behaviour measured here on 2.47.3. The `.gitattributes`, merge-driver and
  conflict-marker mechanisms are long-stable; the rename heuristics are the
  plausible drift risk.

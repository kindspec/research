# W5 — THE MERGE SERVER: built, deployed, and attacked

Code and transcripts: `experiments/W5-server/`. Everything below was run on
git 2.47.3, Python 3.13.5, 12 cores. `bash experiments/W5-server/run_all.sh`
regenerates every transcript.

---

## 0. Verdict

**The core claim holds, and it survived the attack — but only after the attack
found two ways to make it silently wrong, one of them a hole in the mechanism
itself rather than in my implementation of it.**

The decisive adoption question also resolves better than DESIGN §8 assumed:
**a github.com-hosted deployment is possible today**, via a GitHub App plus an
organisation-level ruleset. It does not require self-hosting. §4 has the
receipts, and this should change the report.

The honest headline defect: **`git merge-tree` only tells the server about paths
where stock git *failed*.** Where stock git merges *cleanly and wrongly* — an
unescaped pipe, a duplicated row id, a duplicate aggregate name, a file that
already contained conflict markers — there are no conflict stages, the
type-aware merger is never invoked, and the server publishes stock git's wrong
answer verbatim. The prototype in `experiments/D9-server-side-merge/` has this
hole. The proposed mechanism, stated as "merge the three stages", is
**not sufficient**; the server must additionally *validate every path it
publishes*. That is a change to the architecture, not to the code.

---

## 1. The core claim: verified

> A plain `git clone` — no `.gitattributes`, no merge config, none of our
> tooling — must receive a correctly merged, valid artifact.

`experiments/W5-server/t1_core_claim.sh` → `TRANSCRIPT-t1-core-claim.txt`.

Setup: `budget.tbl`, a GFM table. Alice changes `r_0002`'s **qty** 20→25; Bob
changes the same row's **unit** 6.00→6.50. Different cells, **same line**.

What the forge's merge button produces (stock `merge-tree` on the bare repo):

```
merge-tree exit=1  (1 = conflicted)
    | id     | item     | qty | unit  |
    | ------ | -------- | --: | ----: |
    | r_0001 | widget   |  10 | 12.00 |
    <<<<<<< main
    | r_0002 | gadget   |  20 |  6.50 |
    =======
    | r_0002 | gadget   |  25 |  6.00 |
    >>>>>>> alice
    | r_0003 | sprocket |   8 | 15.00 |
```

The server merge, then a plain clone:

```
{ "status": "merged", "attempts": 1, "git_calls": 17,
  "resolved": ["budget.tbl"], "unresolved": 0 }

### PROOF: a PLAIN clone. No tooling. No config. No .gitattributes.
git version of the naive client: git version 2.47.3
--- .gitattributes present? ---
    ls: cannot access '.gitattributes': No such file or directory
--- any merge driver configured? ---
    (none)
--- is any gws tool on PATH? ---
    (none)

--- budget.tbl AS RECEIVED BY THE PLAIN CLONE ---
    | id     | item     | qty | unit  |
    | ------ | -------- | --: | ----: |
    | r_0001 | widget   |  10 | 12.00 |
    | r_0002 | gadget   |  25 |  6.50 |
    | r_0003 | sprocket |   8 | 15.00 |

    grand := sum(total)

--- verification ---
    parses as a table : 3 rows x 4 cols
    zero conflict markers: True
    r_0002 qty  = 25 (alice's edit)  OK
    r_0002 unit = 6.50 (bob's edit)  OK
    core-claim verification exit=0

--- is it a real merge commit with both parents? ---
    *   e68cd16 Merge alice into main
    |\
    | * 6b2e940 alice: gadget qty 20 -> 25
    * | 6c4238d bob: gadget unit 6.00 -> 6.50
    |/
    * 1e5de0d base
```

**Conflicts as data in a custom ref namespace, and a plain clone does not fetch
them** — verified. On a genuinely unresolvable cell (both sides set the same
cell to different values) the server refuses, leaves the ref where it was, and
writes the conflict to `refs/gws/conflicts/…`:

```
{ "status": "conflict", "conflict_ref": "refs/gws/conflicts/main/5de2373a9cdd-798f24e3f357",
  "records": [{"kind":"cell","path":"budget.tbl","row":"r_0002","column":"qty",
               "base":"25","ours":"99","theirs":"40"}] }

--- refs the plain clone received ---
      refs/heads/main
      refs/remotes/origin/HEAD
      refs/remotes/origin/alice
      refs/remotes/origin/main
    refs/gws/* NOT fetched by default: CONFIRMED
--- our client fetches them explicitly ---
    refs/gws/conflicts/main/5de2373a9cdd-798f24e3f357
```

**A policy correction.** The `D9-conflicts-as-data` prototype's policy on an
unresolvable cell was *keep ours, record the conflict beside it, move the ref*.
That is a **silent lost update** for everyone who does not fetch `refs/gws/*` —
which is every client by default, as the transcript above proves. This server
defaults to `--policy=refuse`: an unresolvable cell means the ref does not move
and the caller is told. `--policy=ours-wins` exists only to make the difference
demonstrable.

---

## 2. Stress and adversarial results

### 2.1 Concurrency — converges to 128, livelocks beyond, and the fix is measured

`t2_concurrency.py` → `TRANSCRIPT-t2-concurrency.txt`. N processes each merge
their own topic branch into the *same* ref, released from a spin barrier. Every
worker contributes one row; a missing row is a lost write.

```
### BARE CAS RETRY LOOP
   N  elapsed  merges/s  att/mean  att/max  att/tot   p50 s   max s  lost  fsck
-------------------------------------------------------------------------------
   2    0.053      37.7      1.50        2        3   0.044   0.044     0    ok
   8    0.332      24.1      4.50        8       36   0.162   0.324     0    ok
  16    0.848      18.9      7.06       11      113   0.395   0.833     0    ok
  32    1.932      16.6     10.38       18      332   1.138   1.899     0    ok
  64    5.008      12.8     16.05       32     1027   3.194   4.953     0    ok
 128   15.657       8.2     25.27       50     3235  10.019  15.486     6    ok
 192   30.244       6.3     29.56       50     5676  20.450  29.898    37    ok
 256   39.258       6.5     29.96       50     7671  26.053  38.995    69    ok
```

- **Zero loss through 64**, confirming and extending the prior 8-writer result.
- **Degradation begins at 128** (6/128 exhaust the 50-retry ceiling) and is
  severe at 192–256 (**19 % and 27 % of writers fail**).
- The failures are **loud** — `status: "error", reason: "CAS livelock"` — and
  the ref is never corrupted. `fsck` is clean at every level. This is a
  throughput collapse, not a correctness failure.
- Throughput **falls** as concurrency rises (38 → 6.5 merges/s): a thundering
  herd, because each retry re-runs the whole `merge-tree` + merge.

DESIGN §5.3 recommends a standing per-repo owner with a queue. I implemented it
(a per-ref `flock`, ~15 lines) and measured it:

```
### QUEUED (flock per ref) -- DESIGN 5.3 standing owner
   N  elapsed  merges/s  att/mean  att/max  att/tot   p50 s   max s  lost  fsck
-------------------------------------------------------------------------------
   2    0.052      38.2      1.00        1        2   0.043   0.043     0    ok
   8    0.241      33.1      1.00        1        8   0.140   0.232     0    ok
  16    0.497      32.2      1.00        1       16   0.258   0.477     0    ok
  32    1.037      30.9      1.00        1       32   0.509   1.001     0    ok
  64    2.183      29.3      1.00        1       64   1.038   2.121     0    ok
 128    4.772      26.8      1.00        1      128   2.124   4.639     0    ok
 192    8.030      23.9      1.00        1      192   3.391   7.833     0    ok
 256   11.664      21.9      1.00        1      256   4.895  11.359     0    ok
```

**Exactly 1.00 attempts at every level, zero loss at 256, and 3.4× the
throughput** (21.9 vs 6.5 merges/s). §5.3's recommendation is now measured, not
asserted. **The bare CAS retry loop should not be shipped**; the queue is
strictly better everywhere, including at N=2.

### 2.2 Correctness under adversarial input — and the hole in the mechanism

`t4_adversarial.py` → `TRANSCRIPT-t4-adversarial.txt`. Every R1 red-team case,
fed to the *server*, with stock git run on the same inputs as a control.

**The first run found four silently-wrong results.** Not from bad merge logic —
from the mechanism. `git merge-tree` reported **zero conflicted paths** for all
four, so the type-aware merger never ran, and the server committed stock git's
output unexamined. Most damningly, it published a file **containing conflict
markers** and moved the ref:

```
### input file is ALREADY CONFLICTED
  stock git (the forge button): exit=0 markers=1
  gws server: status=merged
  ref moved: True
  --- artifact the server wrote ---
      | r_0001 | widget   |  11 | 12.00 |
      <<<<<<< HEAD
      | r_0002 | gadget   |  20 |  6.00 |
      =======
      | r_0002 | gadget   |  99 |  6.00 |
      >>>>>>> other
```

Same shape for the unescaped pipe (R1 a2), the duplicated row id (T2a) and the
duplicate aggregate name (T1a). **This is the load-bearing finding of W5.**

The fix is `validate_result()`: after computing the merged tree, diff it against
`ours` and re-parse **every changed path that has a registered format**,
refusing the whole merge if any fails its invariants. Merging only the
conflicted paths is not enough; the server must validate everything it
publishes.

**A second silent corruption, in my own merger**, found by the same test:
delete/modify. Stock git correctly conflicts. The server *resolved* it by
deleting the row and discarding the other side's edit — status `merged`, no
conflict record. The cause was dead code: `merge_seq` drops a row deleted on
either side *before* the conflict check could see it. Exactly the PASS4/I6
violation R1 warned about, reintroduced independently.

After both fixes:

```
  REFUSED     T2a duplicate row id (copy-paste)            [stock git exit=0]
  REFUSED     T2b both sides mint the same id              [stock git exit=0]
  REFUSED     T2c invisible character splits one row id    [stock git exit=1]
  REFUSED     T1a duplicate AGGREGATE name                 [stock git exit=0]
  REFUSED     T1b NFC/NFD aggregate-name collision         [stock git exit=0]
  REFUSED     T1c NFC/NFD COLUMN-name collision            [stock git exit=1]
  MERGED      column RENAMED on one side                   [stock git exit=0]
  REFUSED     input file is ALREADY CONFLICTED             [stock git exit=0]
  REFUSED     unescaped PIPE inside a cell                 [stock git exit=0]
  CORRECT     CONTROL: two cells on one line               [stock git exit=1]
  REFUSED     row DELETED on one side, MODIFIED on other   [stock git exit=1]

SILENTLY WRONG CASES: NONE
```

R1's `key := id` was a declared invariant nothing enforced. It is now enforced
at parse time on **all three stages**, with ids folded through NFC and
invisible-character stripping so two ids that render identically cannot compare
unequal. The single `MERGED` case (a column renamed on one side) is correct:
git merged it cleanly and the result validates.

**The cost of that honesty:** six of eleven red-team cases now *refuse*. Four of
them are cases where stock git merges cleanly. So on this corpus the type-aware
server **blocks merges the forge would have let through** — correctly, but a
user experiences it as "the robot won't let me merge". That is the real price of
I6, and it should be in the product docs.

### 2.3 Crash safety — clean at every point

`t3_crash.py` → `TRANSCRIPT-t3-crash.txt`. `os._exit(137)` — uncatchable, no
`finally`, no flush — immediately after each git verb, then two retries.

```
VERDICT: CRASH SAFE at every point
```

For **every** kill point (`merge-tree`, `hash-object`, `update-index`,
`write-tree`, `commit-tree`, `update-ref`):

- `fsck --strict` rc=0 immediately after the kill and after retries.
- The ref moved **only** when the kill was after `update-ref`. No torn writes.
- **No duplicate commit.** `tip_after_retry1 == tip_after_retry2`, and
  `merge_commits_on_main = 1` in all six cases. Retry 1 completes the merge;
  retry 2 reports `already-merged`.
- Merged content correct in all six.
- **No `.lock` files left behind.**

Orphans: 2–5 unreachable loose objects per crash — normal git behaviour,
collected by `gc --prune`, `fsck` exit 0. Worth noting only because forges often
disable auto-gc.

One real leak found and bounded: a temp index file left in `GIT_DIR` when killed
between `read-tree` and `write-tree`. A `SIGKILL` bypasses every `finally`, so
the only fix is a sweep. It now lives in `GIT_DIR/gws-tmp/` and is swept after
1 h (verified). It is not a ref, not an object; `fsck` and `clone` are
unaffected.

Idempotence (`t8_idempotent.sh`): the same request issued 10 times gives
`merged` once then `already-merged` nine times, `merge commits on main : 1`.

### 2.4 Malicious input — contained, plus a real DoS in git itself

`t5_malicious.py` → `TRANSCRIPT-t5-malicious.txt`. Trees built with `mktree` and,
where git's own plumbing refuses the name, with
`hash-object -t tree --literally`, which writes anything.

```
SECURITY FAILURES: NONE
```

All 17 cases contained: 100 MB blob, `..` components, absolute paths, newline
and ANSI-escape paths, symlinks, gitlinks, `.gitattributes`, `.git/` `.GIT/`
`.git./` paths, 50 000 columns, NUL bytes, invalid UTF-8, a 20 MB single line.
The ref never moved, nothing escaped the repo, no uncaught exception.

Three findings worth the design's attention:

**(a) A security bug in my own fast-forward path.** The server's
fast-forward shortcut published content it had never inspected — it advanced
`main` to a pushed commit containing a malformed tree. **A fast-forward is a
publish and must be validated like any other.** Fixed; `t5b` now shows a clean
refusal with the ref held.

**(b) `git merge-tree` aborts on a C assertion.** Not an error return — SIGABRT:

```
git: merge-ort.c:3772: record_entry_for_tree:
     Assertion `strchr(basename, '/') == NULL' failed.
  exit=134
```

and for a gitlink with a null oid, `merge-ort.c:1299`. Our server survives
because it shells out (a killed child is just a non-zero exit) — a direct
argument for `subprocess` over linking libgit2/JGit in-process, where this
would take the server down.

**(c) The poison is pushable by default, and that is an operational
requirement.** `t5b_push_poison.sh`:

```
### push to a bare repo with receive.fsckObjects=false   <-- git's DEFAULT
  PUSH ACCEPTED (exit 0)
### push to a bare repo with receive.fsckObjects=true
  remote: error: object 414f7b91…: fullPathname: contains full pathnames
  PUSH REJECTED (exit 1)
```

One crafted push permanently breaks merges on that ref. **`receive.fsckObjects
= true` is mandatory on any self-hosted deployment.** (github.com already fscks
on receive; this bites the self-hosted path only.)

### 2.5 Interaction with normal git — all four correct

`t6_normal_git.py` → `TRANSCRIPT-t6-normal-git.txt`. Interference injected in
the CAS window: after the merged tree is computed, before `update-ref`.

| Event mid-merge | Result |
|---|---|
| Normal push to the same branch | CAS rejects, retries (`attempts=2`), final tree contains **both** the racer's edit and the merge. Correct. |
| Force-push rewinds the branch | CAS rejects, re-merges onto the rewritten history. No corruption. The discarded work stays discarded — **the server neither prevents nor detects force-push data loss.** |
| Source branch deleted | Merge completes against the already-resolved commit; the work is preserved as a parent of the merge. Correct. |
| Target branch deleted | CAS fails → `error: no such ref`. The server does **not** resurrect a deleted branch. Correct. |

### 2.6 Local vs forge — identical bytes; and the backstop does not fire

`t7_local_vs_forge.sh` → `TRANSCRIPT-t7-local-vs-forge.txt`. The same two
commits merged three ways:

```
  server blob : 29ae15e3939f3de9a00699154129b42998c03a2b
  local  blob : 29ae15e3939f3de9a00699154129b42998c03a2b
  IDENTICAL -- a local merge and a server merge produce the same bytes.
```

Because both call the same function. Worth stating as a design constraint: **the
merge function must be the shared artifact**, not the server.

The third case is the one that matters. A colleague who clones, with
`.gitattributes` present but no driver configured:

```
  git merge exit=1
  NOTE: .gitattributes says 'merge=gws' but no such driver is configured.
        git does NOT fail; it silently falls back to the default text merge:
    <<<<<<< HEAD
    | r_0002 | gadget   |  20 |  6.50 |
    =======
```

**Git does not warn or fail on a missing merge driver — it falls back to the
text merge.** This confirms D9 §2.2's "fails *open*". And that user can commit a
marker-bearing file and push it to a bare repo, which accepts it:

```
  push accepted by a bare repo: 09ffc86
```

**The server mediates only the merges it performs.** It cannot stop a direct
push of an already-corrupt artifact. That needs a pre-receive hook — GitHub
Enterprise Server only (§4).

### 2.7 Review churn — found, and fixed

`t9_churn.sh`. The type-aware merger re-renders the table from its parsed model.
Rendering at minimal column width produced, for a **one-cell** merge on a 40-row
table:

```
   b.tbl | 84 +++++-----
   1 file changed, 42 insertions(+), 42 deletions(-)
```

Every line rewritten. That destroys `git blame` on the artifact (every row
attributed to the merge commit) and makes the merge unreviewable. Fixed by
inheriting the incoming file's column widths; now:

```
  changed lines: 2
  -| r_0007 | item7  |  21 | 99.50 |
  +| r_0007 | item7  |  77 | 99.50 |
```

Generalisable rule: **a type-aware merger that re-serialises must reproduce the
incoming file's formatting exactly where the content did not change.**
Round-tripping is not enough; byte-stability is the requirement. Alignment
markers (`--:`) were also being destroyed and had to be preserved explicitly —
they are semantic in GFM.

---

## 3. Was the stress testing any good?

Mixed, and I want to be precise about which.

**Strong**: the adversarial suite (§2.2) and the malicious suite (§2.4). They
found four silently-wrong merges from a structural hole in the proposed
mechanism, one silent lost update in my merger, one security bug in my
fast-forward path, a git DoS, and a mandatory config requirement. That is a test
that found things.

**Strong**: concurrency. It found the exact degradation point and quantified the
fix.

**Weaker than it looks**: crash safety passed cleanly at every point on the
first attempt. I believe that is a **genuine result rather than a weak test** —
git's `update-ref` is the only mutating step and it is atomic by construction
(lockfile + rename), so the design has little room to be wrong. But the test
only covers kills *between* git invocations. It does not cover a kill *inside*
`update-ref`, power loss with unflushed page cache, or a filesystem that
reorders renames. Those are git's guarantees, not ours, and I did not verify
them.

**Not tested**: anything but `.tbl`; multi-file merges under concurrency; more
than one repository; sustained load over time; a real network transport in front
of the merge function; recursive merges with multiple merge bases
(criss-cross), which is where merge-tree's own semantics get subtle.

---

## 4. The forge-deployment answer — the decisive one

**A github.com-hosted deployment is possible today and does not require
self-hosting.** DESIGN §8's implicit assumption that the server must own the
repository is **too pessimistic**, and the report should be corrected.

**The mechanism** — three parts, all documented:

1. **The App can write the merge itself.** `POST /git/blobs`, `POST /git/trees`,
   `POST /git/commits`, `PATCH /git/refs/{ref}`. Two parents are explicitly
   supported: *"for a merge commit, an array of more than one should be
   provided"* (<https://docs.github.com/en/rest/git/commits>). No documented
   write-side size caps. An App can equally push over HTTPS with an installation
   token and skip the API entirely.

2. **The PR still shows as merged.** GitHub Docs, *Pull request merges →
   Indirect merges*: *"A pull request can be marked as merged if its head branch
   commits become reachable from the base branch outside that pull request…
   Pull requests merged indirectly are marked as `merged` even if branch
   protection rules on that pull request were not satisfied."*
   (<https://docs.github.com/en/pull-requests/reference/pull-request-merges#indirect-merges>)
   **bors** has relied on exactly this for years. Kodiak, Mergify and Graphite
   instead call the merge API — i.e. stock git — so bors is the only precedent
   for our model, and it is the right one.

3. **Humans can be locked out of the green button — with rulesets, not classic
   branch protection.** Classic protection is useless here: *"People and apps
   with admin permissions to a repository are always able to push to a protected
   branch."* Rulesets fix it: the **Restrict updates** rule means *"only users
   with bypass permissions can push to branches you specify"*, and the bypass
   list explicitly includes **GitHub Apps**, with admins bypassing only if
   added. A web-UI merge *is* a push to the base branch, so a non-bypass human's
   Merge button is refused.

**What does not work, and should not be attempted:**

- **Required status checks** only gate whether the button is *clickable*. The
  merge GitHub then performs is still stock git. They cannot fix content.
- **The merge queue is unusable.** GitHub builds the `gh-readonly-queue/` branch
  and merges it itself; third parties may only report pass/fail. There is no
  hook to substitute a merge result.
- **Pre-receive hooks are GitHub Enterprise Server only.** GitLab server hooks
  are Self-Managed only; Bitbucket Cloud offers webhooks only. **No cloud forge
  lets you validate a push.** This is why §2.6's direct-push hole cannot be
  closed on github.com.
- Nothing changed 2023–2026: `.gitattributes` appears in GitHub's docs only for
  line endings, LFS and diff/linguist display. `merge=union` / `binary` still do
  not affect the merge button.

**The residual, unclosable hole.** Indirect merges bypass that PR's branch
protections entirely, so the App becomes the *sole* enforcement point — and
anyone who can edit the ruleset (a repo admin on a repo-level ruleset, an org
owner otherwise) can add themselves to the bypass list and land a stock merge.
Mitigation: pin the ruleset at the highest org/enterprise scope available and
audit bypass-list changes. It cannot be eliminated.

**Net:** the adoption story is *"install a GitHub App and apply one org
ruleset"*, not *"host your own git server"*. That is a dramatically better
answer than DESIGN §8 gives, and it is the single most important correction in
this pass. Self-hosting remains required only if you also need to stop **direct
pushes** of corrupt artifacts.

---

## 5. The honest cost

### Lines

```
total lines                 708
  blank                      96
  comment-only lines         60
  docstring lines            53
  EXECUTABLE (approx)       499
```

Stdlib only (`argparse contextlib fcntl json os re subprocess sys time
unicodedata`). 13 git verbs: `merge-tree cat-file hash-object mktree read-tree
update-index write-tree commit-tree update-ref rev-parse merge-base diff-tree
for-each-ref`.

The split is the interesting number:

| | executable lines |
|---|---|
| **git plumbing + CAS + queue + conflict refs + CLI** | **~235** |
| **one format's merger, validator and safety checks** | **~265** |

**The server mechanism is genuinely small — about 235 lines.** DESIGN §8's
"implemented entirely through an interface stable since 2005" survives contact.

**But correctness is not in the server; it is per-format, and it is the larger
half.** ~265 lines bought *one* format, and most of that is refusal logic
extracted from one red-team pass. Every additional format pays that again, and
the R1 corpus suggests each will surface defects the format's designer did not
anticipate. The design's cost estimate should be *per format*, not for the
server.

### Operational burden

| Requirement | github.com App | Self-hosted |
|---|---|---|
| Run as the git user | no | yes |
| Same machine as the repo | no | **yes** — local disk only (GitLab's NFS post-mortem) |
| `receive.fsckObjects=true` | already on | **mandatory** (§2.4c) |
| Per-ref queue | yes (§2.1) | yes |
| `gc --prune` for crash orphans | GitHub's | yours |
| Sweep `GIT_DIR/gws-tmp/` | n/a | yes |
| Can block direct pushes of corrupt artifacts | **no** | yes (pre-receive) |
| Secrets | App private key, webhook secret | ssh/host keys |

The App path removes almost all of it, at the cost of never being able to reject
a bad push.

---

## 6. What this forces on the design

1. **§8 must say "merge and then VALIDATE", not "merge the three stages".**
   `merge-tree` reports only where stock git *failed*. The clean-and-wrong cases
   — which are R1's entire (a2)/(b1)/(T1a) class — arrive with zero conflict
   stages. A server that merges only the conflicted paths publishes stock git's
   wrong answer. This invalidates the `D9-server-side-merge` prototype as a
   template.

2. **A fast-forward is a publish.** Any path that moves a ref must validate,
   including the ones that look like they are not merging anything.

3. **Conflicts-as-data must not be paired with "ours wins".** Recording a
   conflict in `refs/gws/*` while moving the ref is a silent lost update,
   because a plain clone does not fetch those refs — proved in §1. Refusal must
   be the default.

4. **Ship the queue, not the bare CAS loop.** §5.3's standing owner is now
   measured: 1.00 attempts and 3.4× throughput at 256 writers, versus 27 %
   loud failures without it.

5. **The correct claim is "the merge FUNCTION is the shared artifact."** Local
   and server merges are byte-identical because they call the same code (§2.6).
   The design should require this, not merely observe it.

6. **Type-aware mergers must be byte-stable.** Re-rendering at minimal width
   rewrote 84 lines for a one-cell merge and destroyed blame. Round-tripping is
   insufficient; formatting must be preserved where content did not change.

7. **Price refusal honestly.** Six of eleven red-team cases refuse, four of them
   where the forge would have merged cleanly. I6 compliance means the tool
   blocks merges users expect to succeed. That is the correct trade and it is a
   product-documentation problem.

8. **`receive.fsckObjects=true`, and shell out to git.** One crafted push
   otherwise breaks merges permanently, and `merge-tree` responds to malformed
   trees with `abort()`. Process isolation is load-bearing.

9. **Correct §8's adoption claim.** "A hosted or self-hosted component is not
   optional for teams" is right, but "self-hosted" is not required: a GitHub App
   plus an org ruleset with `Restrict updates` works on github.com today. The
   one thing self-hosting still buys is the ability to reject a direct push of
   an already-corrupt artifact, because no cloud forge offers pre-receive hooks.

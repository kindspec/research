# D10 — Interface architecture

What the stable interface is, so that implementations stay replaceable.

Research date 2026-08-28. Every number below was produced by fetch of a primary
source or by an experiment run locally and pasted verbatim. Experiments live in
`experiments/D10-agent-edit/`. Claims I could not verify are marked
**[UNVERIFIED]**.

Written against PASS5 including revisions R1–R7 and PASS3 including I7. Where
those revisions landed while this pass was running, §3.4 re-runs the
measurements against the revised formats rather than the ones I started with.

---

## 0. The finding, up front

The interface question has one dominant answer and three subordinate ones.

**Dominant:** the stable interface is **the file formats plus a plumbing CLI**,
not a protocol and not a library API. The formats are already the contract —
D3/PASS4 established that correctness must hold under stock git with none of our
tooling installed (I6), which means *the bytes on disk are the only thing every
consumer is guaranteed to share*. Any protocol layered above that is a
convenience for latency, not a correctness boundary. A document-server protocol
is the right *implementation* for interactive clients and the wrong *contract*
for the ecosystem.

**Three subordinate answers:**

1. **Agents should edit through the same text path humans do**, with the
   substrate contributing *addressability* and *validation*, not a structured
   edit RPC. The empirical case is in §3 and it is strong in both directions;
   the deciding evidence is that every measured attempt to move agents off text
   and onto structured/positional edit operations made things worse, while every
   measured attempt to make *the text itself* more locatable made things better.
2. **Extensions should be out-of-process, over a line-oriented protocol, with a
   four-function surface** — the `parse/render/resolve/refs` contract from PASS5
   is already the right size. WASM is not required and is not ready enough to be
   a founding dependency.
3. **One address language: the name path already in PASS5.** Not JSONPath, not
   XPath, not tree-sitter queries. Those are *query* languages; we need an
   *identity* language, and conflating them is how systems acquire coordinates.

The single sharpest reframing this pass produced:

> **PASS5's four-function type contract is not an extension API. It is the
> plumbing layer.** `parse`/`render`/`resolve`/`refs` are `hash-object` /
> `cat-file` / `rev-parse` / `for-each-ref`. Ship them as commands with a
> stability guarantee, and every other surface — CLI, TUI, GUI, MCP, CI — is a
> porcelain built on them, exactly as git intended and exactly as git delivered.

---

## 1. Plumbing and porcelain

### 1.1 What git actually promises

Git's most durable architectural decision is written down, in one paragraph, in
`Documentation/git.adoc`. Fetched verbatim from
`https://raw.githubusercontent.com/git/git/master/Documentation/git.adoc`
(lines 294–307):

> Low-level commands (plumbing)
> -----------------------------
>
> Although Git includes its own porcelain layer, its low-level commands are
> sufficient to support development of alternative porcelains.  Developers of
> such porcelains might start by reading about linkgit:git-update-index[1] and
> linkgit:git-read-tree[1].
>
> **The interface (input, output, set of options and the semantics) to these
> low-level commands are meant to be a lot more stable than Porcelain level
> commands, because these commands are primarily for scripted use.  The
> interface to Porcelain commands on the other hand are subject to change in
> order to improve the end user experience.**

That is the whole rule. Three things are worth noticing about how it is phrased.

- The stability promise is attached to **audience** (scripts), not to
  **layer** (low-level). Plumbing is stable *because* machines consume it.
- The promise covers "input, output, set of options and the semantics" — not
  just the output format. Options and semantics are in the contract.
- Porcelain is explicitly promised *instability*, as a feature, so that UX can
  improve. Git did not try to make one interface serve both masters.

Pro Git gives the origin
(`https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain`):

> because Git was initially a toolkit for a version control system rather than a
> full user-friendly VCS, it has a number of subcommands that do low-level work
> and were designed to be chained together UNIX-style or called from scripts

The local install agrees with the docs. `git help -a` on git 2.47.3 splits the
command set into *Main Porcelain*, *Ancillary*, *Low-level / Manipulators*,
*Low-level / Interrogators*, *Low-level / Syncing*, *Low-level / Internal
helpers* — the taxonomy is in the binary, not just the prose:

```
Low-level Commands / Manipulators
   apply, checkout-index, commit-graph, commit-tree, hash-object, index-pack,
   merge-file, merge-index, mktag, mktree, multi-pack-index, pack-objects,
   prune-packed, read-tree, replay, symbolic-ref, unpack-objects,
   update-index, update-ref, write-tree
Low-level Commands / Interrogators
   cat-file, cherry, diff-files, diff-index, diff-tree, for-each-ref, ...
```

### 1.2 The four mechanisms that made plumbing survive 20 years

I ran each of these locally (`git version 2.47.3`) rather than asserting them.

**(a) Content addressing is the whole data model, and it is exposed raw.**

```
$ printf 'hello\n' | git hash-object --stdin
ce013625030ba8dba906f756967f9e9ca394464a
```

`hash-object` is a pure function from bytes to name. Nothing about the
repository, the branch, the user, or the version of git changes its answer.
That is why every tool built on git for two decades still works: the *identity
function is stable*, so anything expressed in terms of it is stable.

**(b) An explicit machine format, versioned, distinct from the human format.**

`git status` documents the split precisely
(`Documentation/git-status.adoc`):

> `--porcelain[=<version>]`: Give the output in an easy-to-parse format for
> scripts. This is similar to the short output, but will remain stable across
> Git versions and regardless of user configuration.

and

> Version 1 porcelain format is guaranteed not to change in a
> backwards-incompatible way between Git versions or based on user
> configuration.

Note the second clause — *regardless of user configuration*. A machine format
that a user's `.gitconfig` can perturb is not a machine format. This is a rule
most CLIs get wrong (colour, locale, pagers, aliases all leak).

**(c) `-z`: an escape-free encoding, so parsing cannot be defeated by data.**

```
$ git status --porcelain=v2 -z | tr '\0' '\n'
1 .A N... 000000 000000 100644 000...0 000...0 weird name.txt

$ git status --short
 A "weird name.txt"
```

The human format quotes and escapes; the `-z` format does not, because the
delimiter cannot occur in a path. Every filename bug in every git wrapper ever
written came from parsing the first form. The doc: *"Terminate entries with NUL,
instead of LF. This implies the --porcelain=v1 output format if no other format
is given."*

**(d) User-specified output templates, so the caller owns the schema.**

```
$ git for-each-ref --format='%(refname:short)|%(objecttype)|%(objectname:short)'
master|commit|db6bacc
origin/master|commit|db6bacc
```

This is the underrated one. `--format` means git never has to guess what fields
a consumer wants, never has to add fields to a fixed record (which would break
positional parsers), and never has to version the record layout. The consumer
declares its own projection. `for-each-ref`, `log --format`, `cat-file
--batch-check` and `ls-tree` all work this way. **A format-string interface is
forward-compatible by construction**: new fields are additive and invisible to
old callers.

### 1.3 What git got wrong, at porcelain

Git's porcelain is the most-criticised widely-used developer UI in existence,
and the criticism has an academic form, not just a rant form.

The primary research is Perez De Rosso & Jackson (MIT CSAIL): *"What's Wrong
with Git? A Conceptual Design Analysis"* (Onward! 2013) and *"Purposes,
Concepts, Misfits, and a Redesign of Git"* (Onward! 2016), which produced
**Gitless** as a redesign that kept git's object model unchanged and replaced
only the interface. The ACM page returned 403 to my fetcher and the CSAIL PDF
mirror 404'd, so I am not quoting them verbatim; the load-bearing claim is
recoverable from the project's own framing and is not controversial:
**Gitless is a wrapper over stock git that changes no storage semantics.** That
fact alone is the finding I need, and it is verifiable from the artifact rather
than the paper: the redesign was possible *because git's plumbing is a stable,
complete, separable layer*. You cannot rewrite the UI of a system whose UI is
its API.

That is the strongest available evidence for the plumbing/porcelain split:
**git's porcelain was bad enough to motivate an academic redesign, and the split
meant the redesign cost a wrapper instead of a fork.** Our porcelain will also
be wrong on the first three attempts. The split is what makes that survivable.

Two specific porcelain sins worth naming because they are easy to repeat:

- **Overloaded verbs.** `git checkout` moved branches *and* restored files *and*
  created branches. Git eventually split it into `switch` and `restore` — 15
  years late, and both are still marked experimental-ish in muscle memory.
  `git.adoc` now carries an entire section titled "Reset, restore and revert"
  whose only purpose is to disambiguate three commands with similar names. **A
  documentation section that exists to explain why your commands are confusable
  is a design bug report.**
- **The word "porcelain" itself is overloaded.** `--porcelain` is the
  *machine-readable* flag, named for the audience that consumes it (porcelain
  authors), which is the exact opposite of what the word means in the command
  taxonomy. Even git's own vocabulary leaked.

### 1.4 The same split, in six other systems

| System | Stable machine layer | Explicitly unstable human layer | Verified |
|---|---|---|---|
| **git** | plumbing cmds; `--porcelain=v1`; `-z`; `--format` | porcelain cmds | `git.adoc`, `git-status.adoc` |
| **Bazel** | Build Event Protocol (protobuf; `--build_event_binary_file`, `--bes_backend`) | console output | BEP doc's stated goal is *"making parsing Bazel's command line output a thing of the past"* |
| **kubectl** | the REST API + `-o json/jsonpath/custom-columns` | the table output | K8s deprecation policy: user-facing CLI elements must work ≥2 releases after deprecation; *"Output format of administrative commands must be stable and machine-parseable"* |
| **ffmpeg** | `libavcodec`/`libavformat` with a written major/minor/deprecation-guard policy (`FF_API_<FOO>` macros, removal only on major bump) | the `ffmpeg` CLI — `developer.html` grants it **no** compatibility commitment at all | ffmpeg.org/developer.html |
| **pandoc** | the JSON AST, version-stamped in band | the CLI flags | see below |
| **Nix** | `nix-store`, `nix-instantiate`, the store path hash | the `nix` v3 CLI | see below |
| **jq** | the value language + `paths`/`getpath`/`setpath` | (jq is nearly all machine layer) | run locally |

**Pandoc deserves a close look, because it is the closest analogue to what we
are building** — a library with a CLI, over a document AST, with third-party
filters as the extension mechanism. Its trick, run locally:

```
$ pandoc -f markdown -t json t.md | jq '."pandoc-api-version"'
[ 1, 23, 1 ]
```

**The version of the interface is inside every payload.** A filter reads the
version before it reads the document and can refuse. That is the cheapest
possible version-negotiation mechanism — no handshake, no capability exchange,
one field — and it is available to a file format as well as to a protocol.

Pandoc also shows the failure mode we must avoid. Its AST addresses everything
positionally once serialized:

```
$ pandoc -f markdown -t json t.md | jq -c 'paths | select(length<5)'
["blocks",0]
["blocks",0,"t"]
["blocks",0,"c",2]
["blocks",1,"c",3]
```

`["blocks",1,"c",3]` is exactly the coordinate that I2 forbids. Pandoc gets away
with it because a filter runs on one snapshot and exits; a *persisted* address
of that shape would be wrong the moment anyone inserted a paragraph. **A
transient query path and a durable reference are different objects and must not
share a syntax** — see §4.

**Nix is the cautionary tale for the porcelain half.** `nix.dev`'s manual on
experimental features:

> Experimental features are considered unstable, which means that they can be
> changed or removed at any time. Users must explicitly enable them by toggling
> the associated experimental feature flags.

`nix-command` (the entire `nix <verb>` CLI) and `flakes` have been behind those
flags since Nix 2.4, released late 2021 — **roughly five years of the primary
user interface being formally unstable**, while the plumbing (`nix-store`,
`nix-instantiate`, store-path hashing) stayed rock stable and everything kept
working. Nix survived a permanently-unstable porcelain *because* the plumbing
was separate. It is the natural experiment for git's rule.

### 1.5 Transferable rules

Extracted, in priority order, with the source that earns each one:

1. **Split by audience, not by abstraction level.** Promise stability to
   machine consumers; promise *change* to humans. (git.adoc)
2. **The machine format must be immune to user configuration.** (git-status
   `--porcelain`)
3. **Use an escape-free framing for anything containing user data.** (`-z`)
4. **Let the caller declare the projection** (`--format`/`-o jsonpath`) so
   records can grow without breaking parsers.
5. **Stamp the interface version into the payload**, not into a handshake.
   (pandoc `pandoc-api-version`)
6. **Never make the human output the API**, even accidentally — no colour, no
   locale, no pager, no aliases in the machine path. (Bazel BEP's stated goal)
7. **Deprecation is a schedule, not an event.** Kubernetes: user-facing CLI
   elements survive ≥2 releases past deprecation; ffmpeg: removal only at major
   bump, behind a compile-time guard macro so callers can test both worlds.
8. **A stable identity function is worth more than a stable API.**
   `hash-object` outlived every wrapper written against it.

---

## 2. LSP as the model for replaceable implementations

### 2.1 What LSP actually collapsed

LSP's M×N→M+N claim is real but narrower than the folklore. DAP's overview page
states the same problem for debuggers
(`https://microsoft.github.io/debug-adapter-protocol/overview`):

> Typically this work must be repeated for each development tool, as each tool
> uses different APIs for implementing its user interface.

The mechanisms that made it work, in order of how much they matter to us:

- **Capability negotiation instead of versioning.** DAP is explicit that it
  chose flags over versions: the *"open-ended set of all features flags is
  called DAP's 'capabilities'"*, exchanged in `initialize`, enabling new
  features without breaking existing implementations. LSP does the same with
  `ClientCapabilities`/`ServerCapabilities` plus dynamic registration. **This is
  the single most reusable idea in the whole protocol family** and it is
  independent of JSON-RPC, of sockets, and of protocols generally — it is just
  "declare what you can do, and never assume".
- **Document lifecycle with explicit ownership.** `didOpen` transfers ownership
  of the buffer's content from disk to the client; while a document is open,
  the client's in-memory version is truth and the file on disk is ignored.
  This is exactly the two-clocks split in PASS5 (session CRDT vs git), and LSP
  arrived at it for the same reason: two writers to one byte range need a
  declared owner.
- **Incremental sync as an optimisation, not a semantic.** `TextDocumentSync`
  can be `Full` or `Incremental`; the server must handle both. The incremental
  path exists purely for bandwidth. It is not part of the meaning.

And the one thing LSP got badly, instructively wrong:

### 2.2 The UTF-16 position-encoding disaster — the details

This is the cautionary tale, and it is worse than usually told.

**The defect.** LSP 3.0–3.16 defined `Position.character` as an offset in
**UTF-16 code units**, while the transport encodes documents in UTF-8. From the
3.17 spec:

> Prior to 3.17 the offsets were always based on a UTF-16 string
> representation. So in a string of the form `a𐐀b` the character offset of the
> character `a` is 0, the character offset of `𐐀` is 1 and the character offset
> of b is 3 since `𐐀` is represented using two code units in UTF-16.

**Why.** clangd's extension docs say it in one line
(`https://clangd.llvm.org/extensions`): offsets are in UTF-16 code units as

> a legacy of VSCode's JavaScript implementation

That is the whole causal story. **An implementation detail of the first client —
that JavaScript strings are UTF-16 — became the wire format for every language
server in the world, in every language, for a decade.**

**The cost.** Every server not written in a UTF-16 language pays a transcoding
cost on every position in every message, in both directions. clangd's own
justification for inventing a protocol extension: clients that are "UTF-8
native" face *"unnecessary transcoding (which may be slow if implemented in e.g.
vimscript)"*. Rust-analyzer, gopls, clangd and others all carry line-index
structures whose only job is UTF-8↔UTF-16 column conversion. Get it wrong by one
and you corrupt a file, silently, only for users who typed an emoji or a CJK
character — the worst failure profile there is: rare, data-destroying, and
correlated with non-Anglophone users.

**The timeline, which is the actual lesson.** GitHub issue
`microsoft/language-server-protocol#376` was opened **13 January 2018**, titled
around exactly this mismatch, with the original poster noting the peculiarity:

> Text document offsets are based on a UTF-16 string representation. This is
> strange enough in that text contents are transmitted in UTF-8.

It was fixed by `PositionEncodingKind` in **LSP 3.17 (May 2022)** — negotiated
via `general.positionEncodings` on the client and `capabilities.positionEncoding`
on the server, with UTF-16 remaining **mandatory** for every server forever. So:
**a known, agreed, articulated defect took over four years to get a fix, and the
fix could not remove the defect — only add an alternative beside it.** Every
conforming server must still implement the broken encoding.

**The three transferable lessons:**

1. **A position encoding, once shipped, is unfixable.** Not hard to fix —
   *unfixable*. M+N cuts both ways: the same property that lets any editor talk
   to any server means no one can change the wire format unilaterally, ever.
2. **The defect was in the addressing scheme, not in the protocol.** JSON-RPC
   was fine. Capability negotiation was fine. The thing that could not be
   changed was *how you name a location in a document*.
3. **Negotiation can add options but cannot remove obligations.** The escape
   hatch LSP built still requires every server to support UTF-16. Capability
   flags are a ratchet.

**This directly threatens any offset-based addressing in our design, and
vindicates PASS5's address grammar.** I2 says references name things, never
places. LSP is the industrial-scale proof of what the alternative costs. Our
name paths (`budget.tbl#q3.revenue`) have no encoding to get wrong — a name is a
byte string, identical in UTF-8, UTF-16 and UTF-32, and unaffected by what
precedes it in the file.

I demonstrated the underlying drift directly with tree-sitter
(`experiments/D10-agent-edit/ts_demo.py`, tree-sitter 0.25 + tree-sitter-python):

```
--- v1 ---
  name=total    byte_range=  4-9   point=<Point row=0, column=4>
  name=grand    byte_range= 67-72  point=<Point row=3, column=4>
--- v2 (one function inserted at top) ---
  name=header   byte_range=  4-10  point=<Point row=0, column=4>
  name=total    byte_range= 35-40  point=<Point row=3, column=4>
  name=grand    byte_range= 98-103 point=<Point row=6, column=4>
```

Inserting one unrelated function moved `total` from byte 4 to byte 35 and row 0
to row 3, and `grand` from 67 to 98. The *name* `total` was invariant. Every
position was not. This is the same experiment as L4's canvas coordinates, run on
source code, and it produces the same answer.

### 2.3 The prior art on document/knowledge protocols

| Protocol | Domain | Status | What it teaches |
|---|---|---|---|
| **LSP** | code intelligence | dominant | capability negotiation; document lifecycle; the position-encoding trap |
| **DAP** | debugging | dominant | the *adapter* indirection — the protocol talks to a shim that talks to a native debugger, so the debugger never has to change |
| **BSP** (Build Server Protocol) | build tooling ↔ IDE | niche; scala/bazel/mill | narrow adoption despite a good design. The lesson: a protocol succeeds when the M and the N are both large and *already exist*. |
| **LSIF** | precomputed code intelligence | **abandoned by Sourcegraph in favour of SCIP** | see below |
| **MCP** | LLM ↔ tools | dominant, 2 years old | §2.4 |
| Web Annotation | annotating documents | W3C Rec, low uptake | §4 |

**LSIF → SCIP is the most relevant failure**, because LSIF is the closest thing
to "LSP for a document index" that anyone shipped, and it was replaced. My fetch
of Sourcegraph's announcement returned 403 so I will not quote it; the
uncontested public facts are that Sourcegraph designed LSIF, adopted it,
concluded it was the wrong shape, and replaced it with SCIP — a protobuf format
with symbol *names* rather than a graph of position ranges. **[Partly
UNVERIFIED — the specific stated reasons are from memory, not a fetched
source.]** The direction of travel is the point and it is verifiable from the
artifacts: LSIF's core is a graph whose vertices are `{document, range}`; SCIP's
core is a string symbol grammar. **They moved from positional identity to
nominal identity.** That is the third independent instance of the same
correction in this document (LSP 3.17, SCIP, our own L1/L4).

### 2.4 Should the core be a document server speaking a protocol?

**The honest case for yes:** interactive clients need cheap incremental reads
against a warm parse. Reparsing a 3 MB table on every keystroke to answer "what
is the value of `#grand`" is absurd; a resident process with a cached
`EntityMap` and a content-addressed derivation cache is the obvious
implementation. The two-clocks model in PASS5 already implies a session-scoped
resident thing.

**The case for no, which I find stronger as a *contract*:**

1. **I6 forbids it from being the correctness boundary.** Stock git with none of
   our tooling installed must produce correct results. If the protocol were the
   contract, a repo opened without our daemon would have no contract at all.
   The formats are the only thing that is always present.
2. **A protocol is the hardest thing to un-ship** — §2.2 is 400 words on exactly
   how hard. Protocol surface should be the *last* thing we commit to, not the
   first.
3. **The M and the N do not exist yet.** BSP is the counterexample: a
   well-designed protocol with a small M and a small N stayed niche. We have one
   implementation and zero third-party clients. Designing an M×N solution before
   M>1 is speculative generality.
4. **A CLI is already a protocol**, with a much better compatibility story:
   process boundary, no session state, no handshake, testable from a shell,
   greppable, and pipeable into tools that will exist in 2040.

**Recommendation: build the resident server, but do not publish it as the
contract.** Publish the plumbing commands. Let the CLI transparently connect to
a daemon if one is running and fall back to cold execution if not — exactly the
`gopls`/`ripgrep`/`watchman` pattern. If a third client ever appears, promote
the daemon's wire format then, with the CLI's semantics already pinned down by
years of use. **The CLI is the specification; the daemon is an optimisation.**

**R5 makes this concrete and, I think, settles it.** PASS5's R5 concluded that
because `.gitattributes` is not consulted in a bare repo (which I reproduced
independently, §6.1), forge-side merges ignore every protection the repository
declares — so the substrate needs a server component that merges with
`git merge-tree --write-tree` and writes back with `hash-object` / `mktree` /
`commit-tree` / `update-ref`.

Notice what that server's public interface is: **it is git.** A client speaks
`git clone`, `git push`, `git fetch` and receives correctly merged artifacts.
There is no new protocol, no capability handshake, no versioned wire format, and
nothing an old client fails to understand. R5's server is the strongest possible
instance of the thesis in §0 — *the required server component was implementable
entirely in terms of an interface that has been stable since 2005*, and its
absence degrades to "stock git's line merge", which is exactly what I6
guarantees is still correct or loud.

So the daemon in this design has two halves with different statuses: a
**collaboration server** whose interface is the git wire protocol (required for
teams, contract already fixed by git), and an **editor daemon** whose interface
is latency-only (optional, never published). Neither is a new protocol. That is
the outcome §2.4 was arguing for, arrived at independently by D9.

### 2.5 MCP, assessed honestly

**What MCP does well.**

- **It won.** In two years it became the default way agents reach tools. An
  interface nobody implements is worth nothing, and this is the one that gets
  implemented. RESEARCH.md §7 already noted that the MCP steering group
  maintains exactly two document-substrate reference servers — Filesystem and
  Git — and archived the Google Drive one. The gravity is toward files.
- **Capability negotiation, inherited from the LSP family.** Per the spec's
  architecture page: *"clients and servers explicitly declare their supported
  features during initialization"*, and *"Features can be added to servers and
  clients progressively"*.
- **Strong isolation principles.** The spec states servers *"should not be able
  to read the whole conversation, nor 'see into' other servers"*. That is a
  better default than most plugin systems in §5 manage.
- **Three primitives, not thirty:** tools (model-controlled), resources
  (app-controlled), prompts (user-controlled). The split by *who decides* is
  genuinely good design.

**What MCP does badly: the schema tax is real and quantified.**

Anthropic's own engineering post *Code execution with MCP*
(`anthropic.com/engineering/code-execution-with-mcp`) states the problem in the
first person:

> as the number of connected tools grows, loading all tool definitions upfront
> and passing intermediate results through the context window slows down agents
> and increases costs

> Tool descriptions occupy more context window space, increasing response time
> and costs. In cases where agents are connected to thousands of tools, they'll
> need to process hundreds of thousands of tokens before reading a request.

and, for their worked example:

> This reduces the token usage from 150,000 tokens to 2,000 tokens—a time and
> cost saving of 98.7%.

That is a **75×** reduction, from the vendor, in public. It corroborates the
prior finding in RESEARCH.md §7 (~21,411 tokens of Notion tool schemas per
session) and generalises it: **the cost is not Notion's schema, it is the
architecture of shipping every schema up front.**

Cloudflare's *Code Mode* post attacks the same problem from the model side:

> The special tokens used in tool calls are things LLMs have never seen in the
> wild.

> With the traditional approach, the output of each tool call must feed into the
> LLM's neural network, just to be copied over to the inputs of the next call,
> wasting time, energy, and tokens.

and claims agents *"handle many more tools, and more complex tools, when those
tools are presented as a TypeScript API"*. Both vendors independently converged
on: **stop enumerating tools; give the model a code surface and let it
compose.**

**The design consequence for us is direct and it is favourable.**

If the agent surface is *a CLI plus a file format*, the token cost of "schema
discovery" is a `--help` the agent reads once, or nothing at all, because the
agent already knows how to use a shell. A 12-tool MCP server for
open/read/write/insert-row/set-cell/resolve/refs/render/deps/validate/diff/
commit would cost thousands of tokens per session, forever, on every session,
whether used or not. **The same capability as `wsx` subcommands costs zero
tokens until invoked.**

**Recommendation on MCP: yes, ship one, thin, and make it a strict adapter.**

- It should expose **≤5 tools**, not 20. Candidates: `wsx_read` (resolve an
  address to content), `wsx_edit` (apply an edit), `wsx_refs` (what depends on
  this), `wsx_validate`, `wsx_exec` (run a plumbing command). Nothing else.
- Everything it does must be expressible as a plumbing invocation, so that MCP
  is provably not a parallel surface. If a capability exists only in MCP, that
  is a bug.
- Prefer **resources** over tools for reads. Resources are app-controlled and
  do not cost schema tokens per tool.
- **Do not build MCP first.** Build the CLI first, then wrap. A wrapper over a
  good CLI is a weekend; a CLI reverse-engineered from an MCP server is a
  rewrite.

---

## 3. How agents actually edit text — the empirical section

This is the most important section and the evidence is unusually good, because
Paul Gauthier ran the ablations in public for three years.

### 3.1 Aider's edit-format benchmarks — the actual numbers

**Round 1 (July 2023), `aider.chat/2023/07/02/benchmarks.html`.** 133 Exercism
Python exercises; four edit formats: `whole`, `diff`, `whole-func`, `diff-func`
(the `-func` variants use the OpenAI function-calling API).

- GPT-3.5 `whole`: 46% first attempt (0301), ~39% (0613).
- GPT-3.5 `diff`: 30% (0301) declining to ~19% (0613).
- **The function-call formats performed worse than the text formats across
  every model tested.**
- Conclusion, verbatim: *"Plain text edit formats worked best"*, and
  *"Asking GPT to return an updated copy of the whole file in a standard
  markdown fenced code block proved to be the most reliable and effective edit
  format."*
- The mechanism they propose: *"It's beneficial to minimize the 'cognitive
  overhead' of formatting the response, allowing GPT to concentrate on the
  coding task at hand."*

**This is the first datum and it is inconvenient for structured-edit
enthusiasts: a JSON function-call edit API measured *worse* than markdown.**

**Round 2 (December 2023), `aider.chat/2023/12/21/unified-diffs.html` — "Unified
diffs make GPT-4 Turbo 3X less lazy".** Benchmark: 89 Python refactoring tasks
drawn from 9 open-source repos, designed to *provoke and quantify* laziness.

| Model | SEARCH/REPLACE baseline | Unified diff | Lazy comments (of 89) |
|---|---|---|---|
| `gpt-4-1106-preview` | **20%** | **61%** | 12 → 4 |
| `gpt-4-0613` | **26%** | **59%** | — |

Verbatim from the post:

> **GPT-4 Turbo only scored 20% as a baseline** using aider's existing
> "SEARCH/REPLACE block" edit format. It outputs "lazy comments" on 12 of the
> tasks.
>
> **Aider's new unified diff edit format raised the score to 61%**. Using this
> format reduced laziness by 3X, with GPT-4 Turbo only using lazy comments on 4
> of the tasks.

**A 3× swing in task success from changing nothing but the edit format.** Same
model, same tasks, same prompt content — only the shape of the edit changed.

Two further ablations in the same post, both quantified:

> **Experiments without "high level diff" prompting produce a 30-50% increase in
> editing errors,** where diffs fail to apply or apply incorrectly and produce
> invalid code.

> **Experiments where flexible patching is disabled show a 9X increase in
> editing errors** on aider's original Exercism benchmark.

That last one is the most important number in this document. "Flexible patching"
is aider's cascade of recovery heuristics when a hunk does not apply cleanly —
re-diffing minus/space against space/plus lines, inferring forgotten `+`
markers, matching on *relative* leading whitespace, splitting a hunk into
overlapping sub-hunks, varying the context window size. **Removing the fuzz
multiplies edit failures by nine.** Any edit protocol that demands exactness
without a recovery ladder is designing for a model that does not exist.

**Round 3: the line-number verdict.** Verbatim, and this is the sentence that
should govern our address grammar:

> The one complicated piece is the line numbers found at the start of each hunk.
> They look something like this: `@@ -2,4 +3,5 @@`. **GPT is terrible at working
> with source code line numbers. This is a general observation about *any* use
> of line numbers in editing formats, backed up by many quantitative benchmark
> experiments.**

Aider therefore instructs the model to emit `@@ ... @@` with no numbers and
interprets each hunk as a search-and-replace.

Their four stated design principles for an agent edit format, verbatim:

> - FAMILIAR - Choose an edit format that GPT is already familiar with.
> - SIMPLE - Choose a simple format that avoids escaping, syntactic overhead and
>   brittle specifiers like line numbers or line counts.
> - HIGH LEVEL - Encourage GPT to structure edits as new versions of substantive
>   code blocks (functions, methods, etc), not as a series of surgical/minimal
>   changes to individual lines of code.
> - FLEXIBLE - Strive to be maximally flexible when interpreting GPT's edit
>   instructions.

and the empathy test:

> Would you want to hand type a properly escaped json data structure to invoke
> surgical insert, delete, replace operations on specific code line numbers?
> Do you want to use a brittle format, where any mistake causes an error that
> discards all your work?

**Round 4: the current state (2026 leaderboard, `aider.chat/docs/leaderboards/`,
225 Exercism exercises across C++/Go/Java/JS/Python/Rust).** The column that
matters is *"Correct Edit Format"* — the fraction of responses that were
well-formed edits at all:

| Model | % correct | **% correct edit format** | Format |
|---|---|---|---|
| gpt-5 (high) | 88.0% | **91.6%** | diff |
| gpt-5 (medium) | 86.7% | **88.4%** | diff |
| o3-pro (high) | 84.9% | 97.8% | diff |
| gemini-2.5-pro (32k think) | 83.1% | 99.6% | diff-fenced |
| gpt-5 (low) | 81.3% | **86.7%** | diff |
| o3 (high) | 81.3% | 94.7% | diff |
| grok-4 (high) | 79.6% | 97.3% | diff |
| gemini-2.5-pro (default think) | 79.1% | 100.0% | diff-fenced |
| o3 (high) + gpt-4.1 | 78.2% | 100.0% | architect |
| claude-opus-4 (32k thinking) | 72.0% | 97.3% | diff |

**In 2026, the top-scoring model on this benchmark still emits a malformed edit
8.4% of the time.** The best model on the list scores 91.6% on *producing a
syntactically valid edit* — a task with no reasoning content whatsoever. Edit
formatting is not a solved problem that better models will absorb; it is a
persistent tax that varies by format (86.7%–100% across the same table).

Note also that **`diff-fenced` exists solely because Gemini could not conform to
`diff`'s fencing** — per aider's docs, it *"is primarily used with the Gemini
family of models, which often fail to conform to the fencing approach specified
in the diff format."* Format conformance is model-specific and unstable across
model generations. **Never bet a data format on model behaviour.**

**Round 5: architect/editor separation (`aider.chat/2024/09/26/architect.html`).**

- o1-preview alone: **79.7%**
- o1-preview (architect) + o1-mini (editor), whole format: **85.0%**
- o1-preview + deepseek, whole: **85.0%**
- o1-preview + claude-3.5-sonnet, diff: **82.7%**

Stated mechanism: *"The model has to split its attention between solving the
coding problem and conforming to the edit format."* Several models improved when
paired **with themselves** — the same weights, split into two turns, beat one
turn. That is direct evidence that **edit-format conformance consumes model
capacity that would otherwise go to the task.**

### 3.2 What the other labs shipped, and why

**OpenAI's `apply_patch` / V4A format** (GPT-4.1 prompting guide,
`developers.openai.com/cookbook/examples/gpt4-1_prompting_guide`):

```
*** Begin Patch
*** [ACTION] File: [path/to/file]
[context_before]
- [old_code]
+ [new_code]
[context_after]
*** End Patch
```

with `@@ class ClassName` / `@@ def method_name()` as *semantic* context markers
for disambiguation and 3 lines of context by default. The rationale, verbatim:

> Note, then, that we do not use line numbers in this diff format, as the
> context is enough to uniquely identify code.

and the general rule they extracted:

> both the exact code to be replaced, and the exact code with which to replace
> it, with clear delimiters between the two

**Anthropic's text editor tool** (`str_replace_based_edit_tool`): commands
`view`, `str_replace`, `create`, `insert`. `str_replace` takes `old_str`/
`new_str` — exact strings, must match uniquely. `insert` is the exception that
proves the rule: it takes `insert_line`, a line number, and it is the one
command whose failure mode is silent misplacement rather than a hard error.

**Convergent evidence.** Four independent teams — Aider, OpenAI, Anthropic,
Cursor/Morph — landed on the same shape: **a content-anchored, context-bearing,
plain-text edit with no coordinates.** Nobody who measured shipped line numbers.
Nobody who measured shipped a JSON edit AST. Aider measured JSON function-call
edits and found them worse in 2023 and never revisited.

**Fast-apply models** (Morph, `morphllm.com`, `docs.morphllm.com`) are the
industrialisation of the *repair* step:

> Your agent writes a lazy edit snippet — changed lines plus
> `// ... existing code ...` markers — and Fast Apply merges it into the file.

Claimed **98% accuracy** at **10,500 tok/s**. Morph's docs also cite a figure of
a coding agent going *"from 6.7% to 68.3%"* on a benchmark from an edit-format
change alone with no retraining — **[UNVERIFIED: I could not reach a primary
source for that pair of numbers; Morph does not cite one. Treat as marketing
until traced.]** The verified structural fact stands regardless: **a commercial
category exists whose entire product is repairing agent edits, which means the
edit-application failure rate is high enough to monetise.**

### 3.3 SWE-agent: the ACI ablations

`arxiv.org/abs/2405.15793`, HTML version fetched. This is the only published
controlled study I found of *interface design* for agents, and every number is
relevant.

| Condition | pass@1 (SWE-bench Lite) |
|---|---|
| Full ACI | **18.0%** |
| **w/o edit linting** (no syntax check on edit) | **15.0%** (−3.0) |
| File viewer 30 lines | 14.3% (−3.7) |
| File viewer 100 lines | **18.0%** |
| File viewer showing whole file | 12.7% (−5.3) |
| Summarized search | **18.0%** |
| Iterative search | 12.0% (−6.0) |
| No search | 15.7% (−2.3) |

And the failure statistics, verbatim:

> 51.7% of SWE-agent w/ GPT-4 Turbo trajectories have 1+ failed edits

> any attempt at editing has a 90.5% chance of eventually being successful

Their four stated ACI design principles:

> 1. Actions should be simple and easy to understand for agents
> 2. Actions should be compact and efficient
> 3. Environment feedback should be informative but concise
> 4. Guardrails mitigate error propagation and hasten recovery

**Three findings here are load-bearing for our design:**

- **Validate on write and it is worth 3 points of task success.** The "edit
  linting" ablation is a syntax check run *after* the agent's edit, rejecting
  the edit if it breaks the file. That is I5 ("the working tree never holds a
  file its own format cannot parse") measured as a 20% relative improvement in
  end-to-end task success. **I5 is not just a merge property; it is an agent
  performance feature.**
- **Showing the whole file was the *worst* condition (12.7%)** — worse than
  showing too little. Cheap partial reads are not a nicety; unbounded context
  actively degrades agents.
- **Half of all trajectories contain a failed edit.** The recovery path is not
  an edge case; it is the median experience.

### 3.4 My own experiment: does line-oriented structure make targets locatable?

The published work measures *formats of edits*. Nobody has published the
measurement I actually need, which is about *formats of documents*: given the
edit protocols the industry converged on (anchor by exact content, no
coordinates), **which document representation makes a target cheapest and least
ambiguous to anchor?**

I built four representations of the same 8-row table
(`experiments/D10-agent-edit/gen.py`): our `.tbl` (one row per line, named
columns, `key := item`), a nested JSON AST in the Portable-Text/tldraw style,
CSV with A1 formulas, and nested YAML.

**Measurement 1 — what fraction of non-blank lines are unique within the file?**
A line that is not unique cannot be used as a search anchor at all, because
aider's own rule is that a SEARCH block *"will only replace the first match
occurrence"*.

```
file             lines  uniq  uniq%  bytes  sample duplicated lines
a_tbl.tbl           12    12  100.0    513  []
b_nested.json      148    19   12.8   1837  ['{', '},', '}', ']']
c_a1.csv             9     9  100.0    194  []
d_nested.yaml       39    17   43.6    636  ['total: null', 'qty: 10', 'unit: 12.00']
```

**100% vs 12.8%.** In the nested JSON, 87% of lines are structural scaffolding
that repeats. This is the same defect D5 found for merge — *"a line merger's
boundaries are the serialization's boundaries, and in a serialized AST those
don't coincide with the structure's"* — showing up in a completely different
consumer. **Line-oriented serialization is not a git optimisation. It is an
addressability property, and agents are a second beneficiary.**

**Measurement 2 — the minimum unique anchor.** Task: *set flange's unit price
from 12.00 to 15.00.* For each representation I computed the smallest window of
contiguous lines containing the target that occurs exactly once in the file
(`experiments/D10-agent-edit/anchor.py`):

```
TASK: set flange's unit price 12.00 -> 15.00

--- a_tbl.tbl ---
  line 6: minimum unique anchor = 1 line(s)
    '| flange   |   5 | 12.00 |                    |'

--- b_nested.json : the value to change is `"v": 12.0` ---
  lines containing the literal target value: [28, 76, 140]  (3 ambiguous matches)
  line 28: minimum unique anchor = 4 line(s)
  line 76: minimum unique anchor = 7 line(s)
  line 140: minimum unique anchor = 7 line(s)

--- d_nested.yaml ---
  lines equal to 'unit: 12.00': [10, 22, 38]  (3 ambiguous matches)
  line 10: minimum unique anchor = 2 line(s)
  line 22: minimum unique anchor = 3 line(s)
  line 38: minimum unique anchor = 3 line(s)

--- c_a1.csv (line-oriented but POSITIONAL formulas) ---
  line 5: minimum unique anchor = 1 line(s): 'flange,5,12.00,=B5*C5'
```

Read the qualitative difference, not just the 1-vs-7:

- In `.tbl` the minimum anchor **is the row itself, and it contains the row's
  own identity** (`flange`). The agent anchors on the thing it is talking about.
  Anchor construction requires no counting and no structural reasoning.
- In the nested JSON the anchor is 4–7 lines of `{`, `}`, `"v":` **that do not
  contain the word `flange` at all**. To build it the agent must count structural
  nesting — which is exactly the operation aider says models fail at, and
  exactly the operation that makes anchors fragile when a sibling changes.
- The three ambiguous matches are the same failure mode as `str_replace`'s
  "old_str must be unique": three rows share the value 12.00, so the naive
  anchor silently edits the wrong row. In `.tbl` the naive anchor cannot be
  wrong because the identity is on the line.

**Measurement 3 — the separation of two properties.** `c_a1.csv` scores
identically to `.tbl` on both measurements (100% unique lines, 1-line anchor) —
and L1 already proved it merges to 480 instead of 660. So:

> **Line-orientation buys edit locatability. Nominal addressing buys merge
> correctness. They are different properties and you need both.**

That is a genuinely new conclusion from this pass. PASS4's rule ("serialize so
that the unit of merge is the unit of meaning") and I2 ("names, not places") were
previously justified only by merge evidence. §3.4 shows the first rule has an
independent agent-ergonomics justification, and that the second rule is *not*
implied by the first.

**Measurement 4 — re-run against R1's opaque row ids.** R1 replaced the natural
key with a machine-managed `id` column, so I regenerated both representations
with ids (steelmanning the nested form by giving it ids too):

```
file                   lines  uniq  uniq%  bytes
e_tbl_r1.tbl              10    10  100.0    570
f_nested_id.json         155    26   16.8   1984

  e_tbl_r1.tbl      line 6: anchor = 1 line(s)
      '| r_2d15 | flange   |   5 | 12.00 |                    |'
  f_nested_id.json  literal '"v": 12.0' occurs at lines [28, 79, 147] (3 ambiguous)
  f_nested_id.json  line 28: anchor = 4 line(s)
  f_nested_id.json  line 79: anchor = 7 line(s)
  f_nested_id.json  line 147: anchor = 7 line(s)
```

R1 **improves** the agent story rather than complicating it. The anchor is still
one line, and it now carries *both* the durable machine identity (`r_2d15`) and
the human-meaningful one (`flange`) on the same line the agent is editing. Giving
the nested form ids did not help it at all — 16.8% unique lines, 4–7 line
anchors, still no `flange` anywhere in the anchor. **Identity helps only when it
is co-located with the content it identifies**, which is the same co-location
argument R1 makes for column formulas and PASS5 makes for namespace collisions.

**Measurement 5 — the metric that actually matters: does the anchor survive an
unrelated edit?** Static uniqueness turned out to be the wrong test. R6 adopted
one-sentence-per-line prose for `git blame` reasons; measured for *uniqueness*
it looks worse than reflowed prose (66.7% vs 100% unique lines) because I seeded
a repeated sentence and reflowing chops the duplicate into non-identical
fragments. That is spurious uniqueness. The real test for an agent is whether an
anchor it captured is still valid after somebody else edits elsewhere — the
long-horizon case, and the concurrent-edit case.

Adding **one word to the first sentence** of a six-sentence paragraph:

```
--- wrapped, BEFORE ---            (agent's anchor, line 4)
  4: placed twice and one instance has been cancelled. Finance has asked for
--- wrapped, AFTER ---
  4: flange order was placed twice and one instance has been cancelled.

--- semantic lines, BEFORE ---     (agent's anchor, line 4)
  4: The flange order was placed twice and one instance has been cancelled.
--- semantic lines, AFTER ---
  4: The flange order was placed twice and one instance has been cancelled.

agent's wrapped anchor still present after upstream edit?  False
agent's semantic anchor still present after upstream edit? True
wrapped:  lines changed by the one-word upstream edit = 6 of 6
semantic: lines changed by the one-word upstream edit = 1 of 6
```

**One unrelated word invalidated the agent's anchor and rewrote every line of
the paragraph.** With semantic line breaks, one line changed and the anchor
survived. Note also that the wrapped anchor was a *sentence fragment spanning
two sentences* — an anchor with no semantic unit behind it, which is why it was
fragile.

This retro-justifies R6 on a second, independent axis. R6 was adopted for blame
attribution; it is also the difference between an agent's edit landing and an
agent's edit failing after any concurrent change. And it identifies the correct
metric to use for the rest of this design:

> **The right measure of an addressing or anchoring scheme is not "is it unique
> now" but "does it survive an unrelated edit". Both L4's coordinates, LSP's
> UTF-16 offsets, and reflowed prose fail that test for the same reason: their
> bytes are coupled to content that is not theirs (PASS3's one defect).**

### 3.5 Should the substrate expose a structured edit API? Both sides.

**The case FOR a structured edit API** (`insert_row_after(id)`, `set_cell(addr,
value)`, `move_block(id, before=id)`):

1. **It makes invalid states unrepresentable.** No agent can produce a table with
   ragged columns or a canvas with a dangling edge. SWE-agent's linting ablation
   says validity is worth 3 points; a typed API is validity by construction.
2. **It makes edits idempotent and retryable.** `set_cell(#q3.revenue, 500)` is
   the same operation whether or not a previous attempt half-applied. An anchored
   text edit is not — a partially applied search/replace leaves a file whose
   anchors no longer match.
3. **It gives the derivation engine exact invalidation for free.** The operation
   names the entity it touched; no diffing required.
4. **It closes the "worked textually, wrong semantically" gap.** The `c_a1.csv`
   result is the canonical instance: a perfectly-applied text edit producing a
   silently wrong document.
5. **The address is stable and the anchor is not.** `budget.tbl#flange.unit`
   survives every concurrent edit; the 7-line JSON anchor survives none of them.
6. Anthropic and OpenAI both ship structured tools already (`str_replace`,
   `insert`, `apply_patch`) — so the "agents only do text" position is already
   false in practice; the question is only how structured.

**The case AGAINST — this is the stronger prosecution and it must be taken
seriously:**

1. **Every measurement of a schema-shaped edit API came back worse.** Aider's
   2023 benchmark tested exactly this — `whole-func` and `diff-func`, edits via
   the function-calling API — and the conclusion was *"Plain text edit formats
   worked best"* with function-call formats *"consistently performed worse than
   text-based formats across all models tested"*. That is a direct, published,
   negative result on the exact proposal.
2. **Familiarity is a measured variable, not a preference.** Aider's FAMILIAR
   principle and Cloudflare's *"special tokens used in tool calls are things
   LLMs have never seen in the wild"* say the same thing: models are good at
   markdown and diffs because the training corpus is full of them, and bad at
   bespoke APIs because it is not. Our API will be the least-familiar interface
   any model has ever seen: zero training data, forever.
3. **Schema tax.** §2.5: a 12-tool surface costs thousands of tokens per session
   whether used or not. Anthropic measured 150,000 → 2,000 for the analogous
   collapse.
4. **N operations is N chances to be incomplete.** The moment an agent needs
   something the API lacks — reorder two columns, split a cell, fix a typo in a
   header — it must fall back to text anyway, and now the system has two edit
   paths with different validation, different concurrency, and different bugs.
5. **It couples us to a document model.** PASS5's whole insight is that
   `parse` never re-emits, so the *syntax is replaceable* and "should we move to
   djot" stays a later decision. A published `insert_row_after` API re-introduces
   exactly the semantic commitment that boundary-only parsing was designed to
   avoid. **A structured edit API is a schema, and schemas are the thing this
   project has spent five passes refusing to commit to.**
6. **Humans and agents diverge**, and then the human path is under-tested. If
   agents write through an RPC and humans write through an editor, the two paths
   will drift, and the rarely-exercised one will rot. Single path, single set of
   bugs.

### 3.6 Recommendation on the agent edit protocol

**Agents edit text. The substrate contributes addressing, validation, and
recovery — not an edit RPC.**

Concretely, four mechanisms, in descending order of confidence:

1. **Make the format the interface.** One entity per line, identity on the line,
   no coordinates in the grammar. §3.4 measures this as a 1-line self-identifying
   anchor vs a 7-line identity-free one. This costs nothing extra: PASS4 already
   requires it for merge. **The single highest-leverage thing we can do for
   agents is a format decision we already made for git.**
2. **Validate on write, always, and reject loudly.** SWE-agent: +3.0 points
   pass@1 (18.0% vs 15.0%) from a syntax check on edit. This is I5 + I7, and it
   must be enforced at the *write* boundary, not only at merge — a pre-write
   parse in the CLI, and a `pre-commit` hook for the git path (see §6 for why the
   hook is belt-and-braces, not the mechanism). Error messages must name the
   entity, not a byte offset: *"row `r_2d15` (flange): column `unit` expects a
   number, got `15.oo`"*.

   **I7 (strict parsing) is the interface-layer requirement that most directly
   serves agents, and it is the one most likely to be softened under pressure.**
   Its own evidence is an agent-shaped failure: a lenient parser that skipped
   lines it did not recognise summed both sides of a conflict and returned 960
   where the candidates were 480 and 720. An agent reading that number has no way
   to know. SWE-agent's linting ablation is the same finding from the other side
   — the guardrail is worth 3 points *because* the alternative is the agent
   proceeding confidently on a broken file. Both say: **reject, never skip.**
   The temptation to be permissive will come from wanting the GUI to open a
   half-merged file; the answer is that the GUI opens the *conflict record*
   (§6.3), not a degraded parse.
3. **Provide addressed reads, not addressed writes.** `wsx read
   budget.tbl#flange` is the cheap partial read SWE-agent shows is worth ~5
   points against dumping the file. It is also the natural way to hand an agent
   the exact anchor text it needs. **Reads are where deterministic addressing
   pays; writes are where it costs.**
4. **Offer exactly two structured writes, and only where text genuinely cannot
   express the intent:**
   - `wsx set <address> <value>` — a scalar assignment to a named cell or
     property. This is the one operation where the textual form (aligning a
     padded markdown table) is real work with a real failure rate, and where the
     nominal address already exists in the grammar. It is `set_cell` and nothing
     more.
   - `wsx apply <patch>` — the *repair* endpoint. Accept aider-grade fuzzy
     application: relative-whitespace matching, forgotten-`+` inference, hunk
     splitting, context-window widening. The 9× number says this is not
     optional. Where a repaired application is ambiguous, refuse and report the
     candidates rather than guessing.

   Do **not** ship `insert_row_after`, `move_block`, `split_cell`, or a typed
   canvas mutation API. Those are the schema, and the schema is what ages.

5. **Address stability is the agent's superpower and it is free.** Because
   `budget.tbl#flange.unit` contains no coordinate, an agent can hold an address
   across a long-running task, across a merge, across another agent's concurrent
   edit, and it stays valid or fails loudly (I3). No other document substrate can
   promise that — LSP could not, and spent four years failing to fix it.

**What would change my mind:** a controlled ablation — same model, same tasks,
one arm editing `.tbl` as text and one arm calling `set_cell`/`insert_row` —
showing the structured arm wins by more than the schema-token cost. That
experiment is cheap (aider's benchmark harness is public and the polyglot suite
is 225 exercises) and nobody has run it for *document* editing. **It is the
single most valuable experiment left in this design, and it should be run before
any structured edit API is shipped.** Until then the published evidence points
one way.

---

## 4. Addressing

### 4.1 The taxonomy that matters

Every scheme below answers one of two different questions, and the design error
is treating them as one.

| | **Query**: "find the things matching this shape" | **Identity**: "the thing I mean, still, later" |
|---|---|---|
| Examples | XPath, CSS selectors, JSONPath (RFC 9535), JMESPath, jq paths, tree-sitter queries, SQL/Datalog over files | Obsidian `^block-id`, HTML `#id`, git object SHA, SCIP symbols, W3C `TextQuoteSelector`, our name paths |
| Stability under concurrent edit | none required | absolute requirement |
| Result | a set, possibly empty, possibly large | one node, or a loud failure |
| Correct failure mode | empty set | error |
| Belongs in | the *tool*, transiently | the *file*, durably |

**The single rule:** *a query language may appear in a command line; only an
identity language may be written into a file.* Every disaster in §2.2 and every
L1–L4 failure came from persisting a query.

### 4.2 The evidence for each

**JSONPath.** RFC 9535, February 2024, Standards Track — **seventeen years after
Goessner's 2007 article**, precisely because implementations diverged. The RFC's
own account: expressions *"became decreasingly portable. For example, regular
expression processing was often delegated to a convenient regular expression
engine"*, and the WG's design principle was adopting *"consensus between
implementations even if rough"*. It also concedes *"backwards compatibility is
not always achieved"*. **A syntax that is easy to invent and hard to standardise
is a bad candidate for a persisted address.** Its *Normalized Paths* are the
useful part — a canonical form for a location — and they are, of course,
positional: `$['blocks'][1]['c'][3]`.

**tree-sitter queries** are the best *query* language of the set: S-expression
patterns over a real grammar, with named captures. My run (§2.2) shows why they
cannot be an identity language: the query `(function_definition name: (identifier)
@fn.name)` is stable and correct in both file versions, and every byte range it
returns changed. **The query is durable; its results are not.** That is the
correct division of labour and we should copy it — capture by name, never
persist the range.

**W3C Web Annotation Data Model** is the most directly relevant prior art
because it is the only standard that had to solve "point at part of a document
that will change". It defines eight selectors, and the design is an explicit
admission that no single one works:

> Multiple Selectors can be given to describe the same Segment in different ways
> in order to maximize the chances that it will be discoverable later, and that
> the consuming user agent will be able to use at least one of the Selectors.

and on the positional one specifically:

> Any edits or dynamically transcluded content may change the selection, thus it
> is RECOMMENDED that a State be additionally used to help identify the correct
> representation.

So the W3C's answer to positional addressing was: keep it, but pair it with a
`TextQuoteSelector` (content + prefix/suffix — i.e. an *anchor*, exactly what
aider and OpenAI converged on) and a snapshot of the resource. **A W3C
Recommendation independently reached "positions are unreliable, anchor on
content, and layer redundant selectors".** Low uptake, high validity.

**XPointer** is the cautionary tale of the family: a scheme so complex it was
split into a framework plus schemes, largely unimplemented, and effectively
dead. It is what happens when an addressing language tries to be a query
language, an identity language, and a range language at once.

**SQL over files (Datasette/DuckDB) and Datalog** are a different axis entirely
and belong in the *derivation* layer, not the address layer. DuckDB can read a
directory of CSVs; Datasette can serve a SQLite index. Both are excellent for
"ask a question across many artifacts" and neither produces a durable reference
to a part of a document. PASS5 already scopes search as a gitignored FTS5 index;
the same reasoning applies here.

**Obsidian is the strongest positive datum**, because it is the most successful
product in this exact category and it independently invented our scheme. From
`obsidian.md/help/Linking notes and files/Internal links`: block links are
`[[Note#^block-identifier]]`; the identifier is written **into the file** at the
end of the block; *"Block identifiers can only consist of Latin letters,
numbers, and dashes."* And, honestly:

> Block references are specific to Obsidian and not part of the standard
> Markdown format. Links containing block references won't work outside of
> Obsidian.

That last line is the price and we will pay it too: PASS5's `{#findings}` is
pandoc/djot-compatible, which is a strictly better position than Obsidian's, but
it is still a convention that only our tooling fully honours. The mitigating fact
is that an unrecognised `{#findings}` degrades to visible literal text, not to a
wrong answer — I3 holds even for foreign tools.

### 4.3 Recommendation: one address language, and it is already written

**Keep exactly the PASS5 grammar. Add nothing.**

```
budget.tbl#grand              an aggregate
budget.tbl#q3.revenue         a named cell
q3-review.md#findings         a named block
arch.canvas#api               a named shape
```

Justification, now with external corroboration:

- **One grammar across prose, tables and canvases is achievable** because all
  three reduce to `file#name(.name)*`, and the four-function contract already
  requires each type to implement `resolve : EntityMap, NamePath -> Node`. The
  type-specific meaning lives behind `resolve`, not in the syntax. This is the
  same move LSP made with `TextDocumentIdentifier` + a type-agnostic position —
  except ours is nominal, so it does not have LSP's problem.
- **It is already a URI fragment.** `file#name` is the oldest identity scheme on
  the web, is what W3C's `FragmentSelector` wraps, and requires no new parser in
  any client.
- **It has no encoding.** A name path is bytes; there is no UTF-16 question, no
  line-ending question, no tab-width question. §2.2 says this is worth more than
  anything else on the list.
- **It cannot express a coordinate**, which is I2 enforced by grammar rather
  than by discipline. PASS3 already made this argument; §2.2 and §3.4 now supply
  two independent industrial confirmations.

**Do add, as a separate and clearly-marked thing:** a *query* facility in the
CLI only, never persisted — `wsx query 'budget.tbl rows where qty > 10'` or a
tree-sitter-style pattern. Enforce the separation mechanically: **the query
language's output must be name paths, never offsets.** That single rule keeps
the two worlds from leaking into each other, and it is testable.

**Do not add:** a second grammar for ranges ("from block A to block B"). Ranges
are where every scheme in §4.2 got complicated, and where W3C had to introduce
`RangeSelector` composing two other selectors. If ranges are ever needed, express
them as a pair of name paths in a command argument, not as a syntax in a file.

---

## 5. Extension architecture

### 5.1 The three models, and who actually ships each

| Model | Ships in | Cost | Benefit |
|---|---|---|---|
| **In-process** | Obsidian (JS), Emacs (elisp), Datasette (pluggy/Python), VS Code *renderer*-adjacent APIs | version-locked to the host; a bad plugin crashes/hangs the app; you can never refactor an internal that a plugin reached | fastest to build, richest access, zero IPC |
| **Out-of-process RPC** | Neovim (msgpack-RPC), LSP/DAP servers, VS Code's extension **host**, git subcommands (`git-foo` on PATH) | serialization cost; async everywhere | crash isolation; any language; the interface is forced to be explicit and therefore versionable |
| **WASM** | Zed, Extism, Spin, Envoy (proxy-wasm), Shopify Functions | immature tooling; the component model's async/threads story is unfinished; no filesystem/network without WASI plumbing | sandboxing + portability + near-native speed, in one artifact |

### 5.2 What each one locked its host into

**Obsidian** — the most successful plugin API in this space, so its lock-in is
the most instructive. The published `obsidian.d.ts` exports ~150 classes and
interfaces: `App`, `Vault`, `Workspace`, `MetadataCache`, `Editor`,
`MarkdownView`, `TFile`, plus a full UI component kit (`Modal`, `SuggestModal`,
`Setting`, `ButtonComponent`…). Two observations:

- **The document model they exposed is deliberately thin.** `Vault` gives
  `read`, `write`, `modify`, `process` (atomic read-modify-write) and
  `processFrontMatter`; `MetadataCache` gives a *parsed index* — headings,
  links, tags, blocks, frontmatter — and that is all. **There is no document AST
  in the public API.** Files are strings; structure is a derived, rebuildable
  cache. That is remarkably close to PASS5's `parse → EntityMap` with
  boundary-only parsing, and it is why Obsidian could change its editor
  internals (the Live Preview rewrite on CodeMirror 6) without breaking the
  plugin ecosystem wholesale.
- **The UI kit is the lock-in.** Exposing `Modal`, `Setting`, `ButtonComponent`
  and the DOM means every plugin is welded to Electron and to Obsidian's own
  widget lifecycle. That is the part they can never change and the part that
  makes a non-Electron Obsidian impossible. **The document API was designed for
  replaceability; the UI API was not, and the UI API is what pins them.**

**Emacs** — durable: everything is a buffer; every command is callable from
elisp; the extension language is the implementation language. Fatal: 40 years of
in-process dynamic-scope global mutation means the boundary between "Emacs" and
"a package" does not exist, so nothing can be deprecated and single-threaded
blocking is architectural. The instructive detail is that **Emacs needed native
JSON parsing added to the C core (Emacs 27) before LSP clients were usable** —
the extension surface was fast enough for extensions written in 1990 and not for
extensions that talk to a modern protocol. In-process does not save you from
performance cliffs; it just moves them somewhere you cannot fix.

**VS Code** got this right and said why
(`code.visualstudio.com/api/advanced-topics/extension-host`):

> VS Code aims to deliver a stable and high performance editor to users, and
> misbehaving extensions should not impact the user experience. The Extension
> Host in VS Code prevents extensions from: Impacting startup performance,
> Slowing down UI operations, Modifying the UI

**Extensions cannot touch the DOM.** That single prohibition is why VS Code
could ship a browser build, a remote/SSH build, and a WebWorker build with the
same extensions — the same extensions Obsidian could never move off Electron. It
is also why VS Code needed to invent contribution points and a notebook API
rather than letting people render whatever they wanted: **denying direct UI
access forces every extension capability to be an explicit, versionable
declaration.**

**Neovim's API contract is the best-written stability policy I found anywhere,**
and it should be copied nearly verbatim. From `runtime/doc/api.txt`:

> As Nvim evolves the API may change in compliance with this CONTRACT:
>
> - New functions and events may be added.
>   - Any such extensions are OPTIONAL: old clients may ignore them.
> - Function signatures will NOT CHANGE after release, except as follows:
>   - Map/list parameters/results may be EXTENDED (new fields may be added).
>     - Such new fields are OPTIONAL: old clients MAY ignore them.
>     - Existing fields will not be removed.
>   - Return type MAY CHANGE from void to non-void.
>   - An optional `opts` parameter may be ADDED.
> - Event parameters will not be removed or reordered (after release).
> - Deprecated functions will not be removed until Nvim 2.0.
>
> "Private" interfaces are NOT covered by this contract:
> - Undocumented (not in :help) functions or events of any kind
> - nvim__x ("double underscore") functions
>
> The idea is "versionless evolution", in the words of Rich Hickey:
> - Relaxing a requirement should be a compatible change.
> - Strengthening a promise should be a compatible change.

Three things to steal outright: (a) **an `opts` dict on every function**, so
parameters can be added forever without a signature change; (b) **a naming
convention that marks the private surface** (`nvim__`), so "we never promised
that" is checkable rather than arguable; (c) **machine-readable API metadata** —
`nvim_get_api_info` returns `api_level`, `api_compatible`, `api_prerelease`, and
per-function `since`/`deprecated_since`. That is capability negotiation without
a protocol handshake, and it is the same idea as pandoc's in-band version stamp.

Neovim also independently invented the thing §4 argues for. `extmarks`:

> Extended marks (extmarks) represent buffer annotations that track text changes
> in the buffer. They can represent cursors, folds, misspelled words, anything
> that needs to track a logical location in the buffer over time.

with "forward gravity" on insertion. **Neovim built a whole subsystem whose only
purpose is that raw positions do not survive edits.** Every serious text system
eventually builds this; we get it for free by never storing a position.

**Datasette** shows the low-ceremony end. ~26 pluggy hooks, in-process Python,
each hook free to accept any subset of the documented parameters — *"When you
implement a plugin hook you can accept any or all of the parameters that are
documented as being passed to that hook"*. That parameter-subset rule is the
Python equivalent of Neovim's `opts` dict, and it gets the same property:
**hooks can grow parameters forever without breaking existing plugins.** Some
hooks carry an explicit *"The design of this plugin hook is unstable and may
change"* warning — an honest, cheap, per-hook stability marker. Worth copying.

**SilverBullet** is the closest architectural cousin: markdown files as truth, a
client that *"runs 90%+ of the logic"*, a server that is *"otherwise a dumb file
store"*, and sandboxed "plugs". The shape — smart client, dumb file server — is
exactly what a git-backed substrate wants, since git *is* the dumb file store.

### 5.3 Is WASM ready in 2026?

**Who ships it:** Zed (extensions are *"written in Rust and compiled to
WebAssembly"*, `wasm32-wasip2` target, versioned via the `zed_extension_api`
crate — *"Make sure it's still compatible with Zed versions you want to
support"*), Envoy (proxy-wasm), Shopify Functions, Spin, Extism as a
general-purpose embedder. That is real production usage, not a demo.

**The state of the component model:** the Bytecode Alliance's own introduction
page still leads with *"The current stable release of WASI is WASI 0.2.0, which
was released on January 25, 2024"*. WASI 0.3 — the release that brings native
async into the component model — has been the headline in-flight item for the
last two years. **[UNVERIFIED as of 2026-08: I could not fetch a current
roadmap page stating 0.3's status; treat "async is not yet stable" as probable
but unconfirmed.]**

**Assessment.** WASM's value proposition for us is sandboxing untrusted
third-party type handlers. That is a real future need and a fake present one: we
have zero third-party extensions, and the first ten will be written by us or by
people we can read the source of. Meanwhile the cost is concrete — the ABI for
passing a whole document across the boundary is exactly the part of the
component model that is least settled, and Zed's compatibility note shows even a
committed adopter is managing version skew by hand.

Note also what Zed's docs say: *"Most extensions will work properly without any
Rust code present. In particular, only language server, context server and
debugger extensions require custom Rust."* **Zed's most-used extension category —
languages — is data (a grammar plus queries plus config), not code.** That is
the single best architectural idea in the whole section, and §5.4 applies it.

### 5.4 Recommendation

**Three tiers, and most extensions never leave tier 1.**

**Tier 1 — data, not code.** A type is a *declaration*: a grammar (a
tree-sitter grammar or equivalent), a set of named queries that identify
entities and references, and a render template. No executable code, no sandbox,
no ABI, no version skew. Zed proves this covers the majority of the real demand.
This should be the *default and documented* way to add a type, and every
first-party type should be built this way so it stays honest.

**Tier 2 — an out-of-process program implementing four commands.** When a type
needs real computation, it is a program on `PATH` named `wsx-type-<suffix>`,
speaking newline-delimited JSON on stdin/stdout, implementing exactly:

```
parse   bytes    -> EntityMap        (boundaries only; never re-emits)
render  EntityMap-> bytes            (render . parse == id)
resolve EntityMap, NamePath -> Node
refs    EntityMap-> [Reference]
```

This is git's `git-foo`-on-PATH subcommand mechanism, which has survived twenty
years with no registry, no manifest, no ABI and no version negotiation. It
matches PASS5's "no manifest and no registry — type is the filename suffix". Any
language, crash-isolated, trivially testable from a shell, and — critically —
**identical in shape to the plumbing commands the core itself exposes**, so
there is one mental model rather than two.

Adopt Neovim's contract verbatim: an `opts` object on every call, additive
fields only, a `__`-prefixed private namespace, and machine-readable metadata
(`wsx api-info` returning per-command `since`/`deprecated_since`). Adopt
pandoc's in-band version stamp on every payload.

**Tier 3 — in-process, for the first-party frontends only, explicitly
unstable.** The GUI needs a resident parse and a CodeMirror integration; that is
an internal API and should be marked as such (`wsx__`-style), never documented as
public, and freely broken.

**Explicitly do not ship, in this order of importance:**

- **No UI API.** This is the Obsidian lesson and it is the one that would
  actually kill us. The moment an extension can render a widget, our frontend
  choice is permanent. If extensions must contribute UI, they contribute
  *declarations* (a command name, an icon, a settings schema) that the frontend
  renders — VS Code's contribution points, not Obsidian's `Modal`.
- **No WASM, yet.** Revisit when there are third-party extensions we do not
  trust, or when WASI async is stable, whichever is later. Nothing in tiers 1–2
  forecloses it: a WASM host is a fourth way to run the same four functions.
- **No document AST in the public interface.** `EntityMap` should be exposed as
  *boundaries and names* — offsets into the original bytes plus name paths — not
  as a typed tree of content nodes. The instant we publish a node type
  vocabulary we have published a schema, and PASS5's whole "the substrate is not
  married to markdown" property evaporates. (Obsidian's `MetadataCache` is
  exactly the right precedent: an index, not a tree.)

**What irreversibly couples you to your first implementation** — the general
answer, ranked, from this whole section:

1. A UI API (Obsidian).
2. A position encoding (LSP).
3. Anything in-process that touches internals (Emacs).
4. A persisted schema of node types.
5. A protocol handshake, once there are two implementations.

Note that (1)–(4) are all things you can avoid at zero present cost, and (5) is
the one §2.4 recommends deferring.

---

## 6. Automation surface

### 6.1 Hooks are not cloned — verified

```
$ git init origin && cd origin
$ printf '#!/bin/sh\necho "HOOK RAN"\n' > .git/hooks/pre-commit && chmod +x ...
$ printf '*.tbl merge=tblmerge\n*.md diff=md\n' > .gitattributes
$ git add -A && git commit -m init
HOOK RAN                                     <- runs in the origin

$ git clone origin clone1
--- hooks in ORIGIN ---
pre-commit
--- hooks in CLONE (non-sample) ---
(none)                                       <- NOT cloned
--- gitattributes travelled? ---
*.tbl merge=tblmerge
*.md diff=md                                 <- tracked file, travels
--- check-attr in clone ---
x.tbl: merge: tblmerge                        <- attribute resolves
y.md:  diff:  md
--- driver configured? ---
merge.tblmerge.driver = <UNSET>               <- driver does not
```

(git 2.47.3.) This reproduces D3/V-CORRECTION-2 exactly and adds the hook half.

**And in a bare repo the attribute does not even resolve:**

```
$ git clone --bare origin bare1 && cd bare1
$ git check-attr merge -- x.tbl
x.tbl: merge: unspecified
$ git show HEAD:.gitattributes
*.tbl merge=tblmerge                          <- it IS in the tree; git won't look
```

So: `.gitattributes` is in the object database, and a bare repo — every forge —
declines to consult it. Only `$GIT_DIR/info/attributes` works there, which is
per-repo sysadmin action.

### 6.2 The security reasoning, stated properly

Two separate reasons, often conflated:

**(a) Structural.** Hooks live in `$GIT_DIR/hooks`, which is not part of the
tree, not part of any commit, and therefore not part of what the wire protocol
transfers. A clone transfers objects and refs. Hooks are *not data git has*, so
there is nothing to send. `git init` may seed them from a template directory
(`git-init`'s TEMPLATE DIRECTORY section), which is local configuration.

**(b) Security, and it is not hypothetical.** If hooks travelled, `git clone` of
an untrusted repository would be arbitrary code execution on the next git
command. That this is the live concern is confirmed by CVE-2024-32465 (git
advisory `GHSA-vm9j-46j9-qvq4`, patched 2024-05-14, CVSS 7.3, affecting
everything up to v2.45.0): the advisory concerns cloning archived repositories
(e.g. `.zip` files) from untrusted sources where *"hooks could be configured to
run within the context of that repository"*, and git's recommendation is to use
`git clone --no-local` for untrusted repositories. **Git treats "a repository
you obtained can make your machine run code" as a vulnerability requiring a
coordinated release across seven maintenance branches.** Hooks-don't-clone is
not an oversight; it is the boundary that CVE was about defending.

Git also states the policy consequence directly, in `gitfaq.adoc`:

> The only safe place to make these changes is on the remote repository (i.e.,
> the Git server), usually in the `pre-receive` hook or in a continuous
> integration (CI) system.  These are the locations in which policy can be
> enforced effectively.
>
> ... using hooks on a developer machine is not effective as a policy control
> because a user can bypass these hooks with `--no-verify` without being
> noticed (among various other ways). Git assumes that the user is in control of
> their local repositories and doesn't try to prevent this or tattle on the
> user.

**"Git assumes that the user is in control of their local repositories" is the
sentence to design against.** A local hook is an affordance for the user's own
benefit. It can never be a correctness mechanism — which is the same conclusion
I6 already reached about merge drivers, arrived at from a different direction.

**How the ecosystem copes**: `pre-commit` ships `.pre-commit-config.yaml` as a
tracked file and requires every developer to run `pre-commit install` once —
*"this cannot be automated through git alone, making it an essential onboarding
requirement"* — plus `pre-commit run --all-files` in CI as the actual enforcement
point, plus pre-commit.ci for hosted enforcement. **Config travels; execution
does not; enforcement lives on the server.** That three-part split is the only
shape that works and we should adopt it unchanged.

### 6.3 What the portable mechanism actually is

The good news, verified: there is exactly one automation-adjacent behaviour that
travels with a repository and needs zero configuration, and it happens to be the
one we need. `-merge` in `.gitattributes`, no driver installed anywhere:

```
$ printf '*.tbl -merge\n' > .gitattributes
  ... concurrent row insertions on two branches ...
$ git merge alice
warning: Cannot merge binary files: b.tbl (HEAD vs. alice)
CONFLICT (content): Merge conflict in b.tbl

$ cat b.tbl                       <- working tree file: STILL A VALID TABLE
| item | qty |
| ---- | --: |
| a    |  1 |
| bob  |  7 |
key := item

$ git ls-files -u                 <- the conflict, as data, out of band
100644 e77ec42... 1  b.tbl
100644 8a94c7f... 2  b.tbl
100644 71e6cfb... 3  b.tbl

$ git cat-file -p :3:b.tbl        <- retrieve any version with pure plumbing
| item | qty |
| ---- | --: |
| a    |  1 |
| alice|  9 |
key := item
```

The gitattributes docs confirm the semantics: unset merge means *"Take the
version from the current branch as the tentative merge result, and declare that
the merge has conflicts."* And on drivers, verbatim: *"The definition of a merge
driver is done in the `.git/config` file, not in the `gitattributes` file."*

**Caveat, and it is why R5 exists.** This mechanism only fires where a working
tree and an index exist. §6.1 shows a bare repo returns `merge: unspecified` even
though `.gitattributes` is demonstrably in the tree — so a forge-side merge
button ignores `-merge` entirely and will happily write conflict markers into a
`.tbl`, violating I5 on the server. R5's answer — merge server-side with
`git merge-tree --write-tree` and write the result back with plumbing — is
therefore not an enhancement but the repair for a hole this section would
otherwise leave open. **The interface for that repair is, again, plumbing:
`merge-tree` yields the three stages as blobs in a bare repo, the same three
things `ls-files -u` / `cat-file -p :N:path` yield in a working tree.** One
conceptual model, two entry points, both pre-existing.

**This is PASS3's I5 ("conflicts are data stored beside the artifact, never
markers inside it") available from stock git today, everywhere, with a
one-line tracked file.** And the read interface for the conflicting versions is
`git cat-file -p :N:path` — plumbing, stable since 2005.

### 6.4 The automation recommendation

**Ship four mechanisms and refuse to build a fifth.**

1. **Validation as a pure function, exposed as a command.** `wsx check [paths]`
   — exit non-zero, structured errors on stdout. Everything else calls this: the
   editor before write, the optional local hook, CI, the server-side
   `pre-receive`. One implementation, four call sites, no policy anywhere.
2. **Derivation as a build, driven by discovered dependencies.** PASS5's
   content-addressed engine already is this. `wsx build` is Make with automatic
   dependency discovery via `refs`, which is strictly better than Make (no
   hand-written prerequisites to go stale) and strictly less than a policy
   engine (no rules language, no conditions, no hooks-in-the-build).
3. **A watcher that is a loop over (1) and (2)**, and nothing else. `wsx watch`
   is `while inotify: build`. It must have no configuration file. The instant a
   watcher gains a rules file it has become a policy engine.
4. **Server-side enforcement documented but not implemented by us.** Ship a
   `pre-receive` script and a CI workflow as *examples in the docs*. Per
   `gitfaq.adoc`, that is where policy can actually be enforced, and per
   pre-commit's model, that is where the ecosystem already puts it.

**The line between mechanism and policy, stated once:**

> **Mechanism answers "is this artifact valid, and what does it derive to?"
> Policy answers "what should happen when it isn't." We ship the first, expose
> it as an exit code and a structured error stream, and ship zero of the
> second.**

Concretely, that means: no rule DSL, no `.wsxrc` with `on_save:` handlers, no
event bus, no scheduled tasks, no notification config. Those are the features
that turn a substrate into a framework, and every one of them is available to
the user in three lines of shell over `wsx check` — which is the whole point of
having a plumbing layer.

---

## 7. Agent-native without agent-dependent

### 7.1 What each party actually needs

| Need | Agent | Human | In tension? |
|---|---|---|---|
| Deterministic addressing | **critical** — an address held across a long task must stay valid | mild (links, TOCs) | **No.** §3.4 shows the same property gives humans 1-line diffs. |
| Cheap partial reads | **critical** — SWE-agent: whole-file view scored 12.7% vs 18.0% for a 100-line window | moderate (scrolling, folding) | **No.** Same mechanism: `resolve` + byte ranges. |
| Schema discovery | **critical** — must learn the format at runtime | low — learns once, from docs | Mild: costs tokens if pushed, free if pulled. `--help` and `wsx check`'s error text resolve it. |
| Dry run | **critical** — cannot undo a bad write across a long horizon | low — has undo, and a `git checkout` | **No.** `--dry-run` on every mutating command; the derivation cache makes it nearly free. |
| Structured errors | **critical** — must parse and act | harmful if it displaces prose | **Yes, mildly.** Solved by two renderings of one error object, not two error systems. |
| Loud failure (I3) | **critical** — cannot notice a plausible-but-wrong number | **critical** — same reason | **No.** Identical need. |
| Byte-stable round-trip (I1) | **critical** — a whole-file rewrite destroys the agent's own anchors *and* the review diff | **critical** — the product premise | **No.** |
| Anchors that survive unrelated edits (R6) | **critical** — long-horizon tasks hold anchors across other writers | moderate — wants correct `git blame` | **No.** Same convention, two payoffs (§3.4 m5). |
| Strict parsing (I7) | **critical** — cannot detect a plausible-but-wrong parse | moderate — sees the mess | **No**, and it is the requirement most likely to be softened. |
| Visual layout / WYSIWYG | none | high | **Yes** — but it is a *frontend* concern, and PASS5 already puts rendering outside the core. |
| Terse output | wants dense, complete | wants sparse, prioritized | **Yes** — `--porcelain`/`-z` vs human output, i.e. §1's rule, unchanged. |

**The striking result of building this table is how little tension there is.**
Seven of ten needs are identical, and the three genuine divergences are all
solved by git's twenty-year-old answer: *two renderings of one thing, split by
audience, with the machine rendering stable and the human rendering free to
change.*

There is one asymmetry worth naming that does not appear above: **agents are the
only consumer that benefits from the format being boring.** A human can be
taught a clever syntax once. An agent's competence with a syntax is a function of
how much of it was in the training corpus, which is Aider's FAMILIAR principle
and Cloudflare's *"never seen in the wild"* observation. That is a strong,
independent argument for markdown tables over any bespoke grammar, and it
arrives from a completely different direction than PASS5's "the file is the UI".

### 7.2 Who got the balance right and wrong

**Right — git.** The `--porcelain` guarantee (*"stable across Git versions and
regardless of user configuration"*) plus `-z` plus `--format` is a
machine-facing surface built decades before agents, and it is the reason an LLM
can drive git today with no adapter at all. **A well-designed script interface
turned out to be a well-designed agent interface, for free.** This is the single
best argument that "agent-native" is mostly a synonym for "properly plumbed".

**Right — the SWE-agent ACI principles**, which are just good CLI design
restated: simple actions, compact actions, *"Environment feedback should be
informative but concise"*, and guardrails that *"mitigate error propagation and
hasten recovery"*. Note that #3 and #4 are exactly what `--porcelain` and a
non-zero exit code do.

**Wrong — the Office/JSON API path**, quantified in RESEARCH.md §7: 410,053
tokens for a 500×20 Excel read as JSON. An interface designed for a program with
a parser is not an interface for a consumer that pays per token. Verbosity is
free for programs and expensive for agents; that is a genuine new axis and it
argues for the terse, line-oriented format we already chose.

**Wrong — MCP's default posture**, per §2.5: schema push instead of schema pull.
Anthropic's own 150,000 → 2,000 measurement is the correction.

**Wrong, instructively — Nimbalyst's CSV metadata line** (RESEARCH.md §3):
`# nimbalyst: {...}` on line 1, whose embedded commas widen the sheet to three
columns. Agent-hostile and human-hostile simultaneously, because it broke the
format's own contract. **The best test of "agent-native without agent-dependent"
is whether a naive consumer that knows nothing about you still gets a correct,
if impoverished, answer.** That is I6 restated for tools other than git.

### 7.3 The rule

> **Everything an agent needs, a script needed first. Build the script
> interface, make it complete, make it stable, and the agent interface is a
> `--help` away. Anything you would build only for agents is either a token-cost
> optimisation (legitimate, put it in an adapter) or a schema (illegitimate, it
> will age badly).**

---

## 8. The adversarial case: this is all over-engineering

Stated as strongly as I can, because it is close to right.

**The prosecution.**

1. **The formats are the product; everything else is a wrapper.** PASS4 already
   concluded that the core is *"a representation discipline, expressed as format
   specs plus an executable conformance suite"*. A conformance suite is not a
   binary. If the formats are right, `cat`, `grep`, `awk`, `git` and an LLM
   already do 90% of the work, today, with no install.
2. **Every layer we add is a layer that must be present for correctness to
   hold — and I6 forbids that.** A protocol, a daemon, an extension host, an MCP
   server: each is a thing that can be absent. The design's own strongest
   invariant argues against its own runtime.
3. **The agent surface is already solved by the shell.** Claude Code and Codex
   drive `git`, `jq`, `rg` and `sed` natively. A `wsx` binary is a thing to
   discover, install, and learn; a markdown table is a thing they already know.
   §3's evidence — FAMILIAR, the function-call formats scoring worst, the
   training-corpus argument — is evidence *against* our own CLI as much as
   against a structured API.
4. **BSP is the warning.** A good protocol with M=small and N=small stays niche
   forever. We have M=1 and N=0.
5. **Every project in RESEARCH.md §7 that failed, failed at distribution, not at
   architecture.** Kova shipped 67 releases in 3.7 months, an apt/rpm/AUR/Nix/
   Flatpak estate, and raised $0.00. Interface architecture is not the binding
   constraint and time spent here is time not spent on the binding one.
6. **A thin MCP shim is a weekend and covers the agent case.** Five tools over
   `read`/`write`/`glob` and you are done.

**The defence, point by point.**

1. **Conceded, and it is the recommendation.** §0 says the formats are the
   contract. The disagreement is only about whether *anything* should be shipped
   beside them, and the answer is yes for four specific things — validation,
   derivation, resolution, reference discovery — because none of them is
   expressible in `awk`. `wsx check` is the one that earns its place on
   measured evidence: SWE-agent's +3.0 points, and I5's requirement that a
   conflicted or half-written file never sits in the tree.
2. **Conceded, and it is why the recommendation is a CLI rather than a
   protocol.** A CLI's absence degrades to "you have plain files with visible
   syntax", which is exactly I6's promise. A daemon's absence, if the daemon were
   the contract, would degrade to nothing. That asymmetry is the whole reason to
   prefer the CLI.
3. **Half conceded.** Agents *are* better at markdown than at `wsx`, which is
   precisely why §3.6 recommends they edit text and not call an API. But the
   things `wsx` does — "what does `#grand` evaluate to", "what breaks if I rename
   this column", "is this file valid" — are not things the shell can answer at
   any level of cleverness, because they require the type's own parser. And
   §3.4's measurement says the agent's *anchor* quality comes from the format,
   not the tool, so the tool's absence costs capability, not correctness.
4. **Conceded, fully.** This is why §2.4 recommends building the daemon and not
   publishing it, and why §5.4 puts extensions on PATH with no registry. Nothing
   in the recommendation assumes a second implementation exists.
5. **Conceded, and it is the strongest point in the prosecution.** It argues for
   the *smallest* interface that is complete, not for none — and the
   recommendation here is smaller than PASS2's, smaller than a protocol, and
   deliberately reuses git's plumbing (`cat-file -p :3:path`) instead of
   inventing a conflict API.
6. **Rejected on measured grounds.** A five-tool MCP shim is fine as an
   *adapter* and bad as *the* surface: it costs schema tokens every session
   (Anthropic's own 150,000→2,000), it cannot be scripted from a shell, it cannot
   run in CI, it cannot be tested with `sh`, and it is useless to the TUI and GUI.
   §2.5 already recommends shipping it — as a wrapper over the CLI, ≤5 tools,
   with no capability that exists only there.

**Adjudication.** The prosecution wins on scope and loses on existence. The
correct conclusion is not "build no interface" but:

> **The interface budget for this project is: four plumbing commands, one
> validation command, one build command, one watch command, a type-handler
> convention that is just PATH, and an MCP wrapper with five tools. No protocol,
> no registry, no manifest, no plugin host, no rules language, no UI API. If a
> capability cannot be reached from `sh`, it does not exist.**

That is materially smaller than what PASS2 imagined and it is the honest reading
of the evidence.

---

## 9. The recommended architecture

### 9.1 The layers

```
  CONTRACT (never breaks, versioned by the format spec + conformance suite)
  ├─ the file formats: .md / .tbl / .canvas
  │    one entity per line; opaque row ids (R1); long not wide (R2);
  │    one sentence per line for prose (R6); no coordinates anywhere
  ├─ .gitattributes: `-merge` on structured types      [portable, verified §6.3]
  ├─ the git wire protocol, for the R5 merge server    [stable since 2005]
  └─ the address grammar: file#name(.name)*            [no coordinates, no encoding]

  PLUMBING (stable interface; audience = machines; git's rules apply)
  ├─ wsx parse   <file>                -> entity boundaries + names  (-z, --format)
  ├─ wsx resolve <address>             -> value / bytes / loud error
  ├─ wsx refs    <file|address>        -> dependencies + dependents
  ├─ wsx render  <file>                -> bytes                      (render∘parse == id)
  ├─ wsx check   <paths>               -> exit code + structured errors
  ├─ wsx build   [targets]             -> derived values, content-addressed
  └─ wsx set     <address> <value>     -> the one structured write
     (+ wsx apply <patch>, the fuzzy repair endpoint)

  PORCELAIN (explicitly unstable; audience = humans)
  ├─ GUI (CodeMirror 6 + decorations)   ├─ TUI   ├─ human-facing CLI verbs
  └─ all of it may be rewritten; none of it is anyone's dependency

  ADAPTERS (thin, no unique capability)
  ├─ MCP server: ≤5 tools, all delegating to plumbing
  ├─ daemon: same semantics as the CLI, for latency only, never published
  └─ example pre-receive / CI workflow: docs, not product
```

### 9.2 What is in the core

**In:** the four type functions (`parse`/`render`/`resolve`/`refs`); the address
resolver; the content-addressed derivation engine; the validator; the conformance
suite that runs the formats against a stock `git` binary (I6).

**Out** — everything PASS5 already excluded, plus three additions from this pass:
**a UI API** (§5.4, the Obsidian lesson), **a published document AST / node-type
vocabulary** (it is a schema, and it un-does boundary-only parsing's replaceability
property), and **a protocol as contract** (§2.4).

### 9.3 The stability rules, adopted verbatim from measured winners

1. Plumbing is stable in *input, output, options and semantics*; porcelain is
   explicitly not. **[git]**
2. Machine output is immune to user configuration; `-z` for anything containing
   user data; `--format` so the caller declares its own projection. **[git]**
3. Every payload carries an in-band interface version. **[pandoc]**
4. Every command takes an `opts` object; fields are additive and never removed;
   a `__` prefix marks the private surface; `wsx api-info` is machine-readable
   with per-command `since`/`deprecated_since`. **[Neovim]**
5. Per-item instability markers are allowed and encouraged
   (*"The design of this hook is unstable and may change"*). **[Datasette]**
6. Deprecation is a schedule with a compile-time or runtime guard so callers can
   test both worlds. **[Kubernetes, ffmpeg]**
7. **Never publish a position encoding.** **[LSP]**

---

## 10. What is still unproven

1. **The structured-vs-textual edit ablation has not been run for documents.**
   §3.6 names it as the highest-value remaining experiment. Everything in §3 is
   inference from *code*-editing benchmarks to *document* editing, and tables are
   more schematic than code — the one place the structured argument might win.
2. **Whether `wsx check` is worth installing.** The +3.0 points is from
   SWE-agent's in-harness linter, which is always present. Ours is a separate
   binary that may be absent, so the realised benefit is bounded by adoption.
3. **Whether a name path can address a canvas usefully.** §4 asserts one grammar
   spans three types; L4 tested only merge, not resolution ergonomics.
4. **The daemon/CLI equivalence claim.** §2.4 recommends "same semantics, two
   entry points". Nobody has built that and had it stay true; gopls and the
   `go` command have drifted.
5. **The "conflict as data" read path assumes the index.** §6.3's `cat-file -p
   :3:path` only exists mid-merge in a working tree. R5 specifies
   `git merge-tree --write-tree` for the bare-repo case; I did not test it this
   pass, and the equivalence of the two read paths (same three blobs, same
   presentation to the client) is asserted, not measured.

6. **R6's semantic line breaks are now load-bearing for two unrelated
   properties** (blame attribution, and agent anchor survival — §3.4
   measurement 5) but they are a *convention*, not something the format can
   enforce, and nothing in the design detects a violation. An imported document,
   or any editor with auto-wrap on, silently reintroduces the coupling. This is
   the weakest link in the anchoring story and it probably needs a `wsx check`
   lint rather than a hope.

---

## Sources

**Primary, fetched:**
`raw.githubusercontent.com/git/git/master/Documentation/git.adoc` ·
`.../git-status.adoc` · `.../gitattributes.adoc` · `.../gitfaq.adoc` ·
`git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain` ·
`git-scm.com/docs/githooks` ·
`github.com/git/git/security/advisories/GHSA-vm9j-46j9-qvq4` (CVE-2024-32465) ·
`aider.chat/2023/07/02/benchmarks.html` ·
`aider.chat/2023/12/21/unified-diffs.html` (+ the post source in the aider repo) ·
`aider.chat/2024/09/26/architect.html` · `aider.chat/docs/leaderboards/` ·
`aider.chat/docs/more/edit-formats.html` ·
`raw.githubusercontent.com/Aider-AI/aider/main/aider/coders/{editblock,udiff,patch}_prompts.py` ·
`arxiv.org/html/2405.15793v2` (SWE-agent) ·
`developers.openai.com/cookbook/examples/gpt4-1_prompting_guide` (apply_patch / V4A) ·
`platform.claude.com/docs/en/agents-and-tools/tool-use/text-editor-tool` ·
`morphllm.com` · `docs.morphllm.com/introduction` ·
`anthropic.com/engineering/code-execution-with-mcp` · `blog.cloudflare.com/code-mode/` ·
`microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/` ·
`github.com/microsoft/language-server-protocol/issues/376` · `clangd.llvm.org/extensions` ·
`microsoft.github.io/debug-adapter-protocol/overview` ·
`modelcontextprotocol.io/specification/2025-06-18/architecture` ·
`rfc-editor.org/rfc/rfc9535.html` · `w3.org/TR/annotation-model/` ·
`obsidian.md/help/Linking+notes+and+files/Internal+links` ·
`raw.githubusercontent.com/obsidianmd/obsidian-api/master/obsidian.d.ts` ·
`docs.obsidian.md/Plugins/Getting+started/Anatomy+of+a+plugin` ·
`code.visualstudio.com/api/advanced-topics/extension-host` ·
`zed.dev/docs/extensions/developing-extensions` ·
`raw.githubusercontent.com/neovim/neovim/master/runtime/doc/api.txt` ·
`docs.datasette.io/en/stable/plugin_hooks.html` · `silverbullet.md/Architecture` ·
`extism.org/docs/overview` · `component-model.bytecodealliance.org/introduction.html` ·
`nix.dev/manual/nix/2.24/development/experimental-features.html` ·
`bazel.build/remote/bep` · `kubernetes.io/docs/reference/using-api/deprecation-policy/` ·
`ffmpeg.org/developer.html` · `pre-commit.com`

**Experiments run locally (git 2.47.3, Python 3.13.5, pandoc 3.1.11.1, jq 1.7,
tree-sitter 0.25):** `experiments/D10-agent-edit/{gen,measure,anchor}.py` (line
uniqueness and minimum-anchor measurements); `ts_demo.py` (tree-sitter query
stability vs offset drift); hook-cloning and bare-repo `check-attr` reproduction;
the `-merge` conflict-as-data demonstration; pandoc AST version stamp.

**Could not verify:** Perez De Rosso & Jackson Onward! papers (ACM 403, CSAIL
mirror 404) — cited for the existence and shape of Gitless, not for quotes;
Sourcegraph's SCIP announcement (403) — LSIF→SCIP direction asserted from the
artifacts, stated reasons marked unverified; Morph's 6.7%→68.3% figure (no
source given by Morph); WASI 0.3 status as of mid-2026.

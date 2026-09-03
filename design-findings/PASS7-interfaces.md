# Pass 7 — interfaces

## The contract is the file formats plus a plumbing CLI. Not a protocol.

I6 says correctness must hold under stock git with nothing installed.
Therefore **the bytes on disk are the only thing every consumer is guaranteed
to share**, and anything above them is convenience, not contract. This kills
the "document server protocol" idea I had been carrying since Pass 1.

The reframing that does the most work: **PASS5's four type functions are not an
extension API, they are the plumbing layer.**

    parse   ~  git hash-object
    render  ~  git cat-file
    resolve ~  git rev-parse
    refs    ~  git for-each-ref

Ship them as commands with git's stability promise, and every GUI, TUI, CLI and
MCP surface is porcelain above them. Git's own docs state the rule, and it is
about audience rather than layer: plumbing interfaces "are meant to be a lot
more stable than Porcelain level commands, because these commands are primarily
for scripted use."

Interface budget: four plumbing commands, plus `check`, `build`, `watch`; type
handlers as programs on PATH; an MCP wrapper with at most five tools.
**If a capability cannot be reached from `sh`, it does not exist.**

And R5's required merge server turns out to reinforce rather than complicate
this: its public interface *is* git — `merge-tree --write-tree`, then
`hash-object` / `mktree` / `commit-tree` / `update-ref`. A required server
component implementable entirely through an interface stable since 2005 is the
strongest available instance of the thesis.

## Agents edit text. There is no structured edit API.

I had been inclined toward `insert_row_after(id)` / `set_cell`. There is a
published negative result against exactly that: Aider's 2023 benchmark tested
structured edit APIs via function calling and found **"Plain text edit formats
worked best"**, with function-call formats worst across all models.

The rest of the evidence says the edit FORMAT dominates everything:

    changing only the edit format          GPT-4 Turbo 20% -> 61%
    disabling fuzzy patch recovery         9x increase in editing errors
    no "high level diff" prompting         30-50% increase in editing errors
    SWE-agent without edit linting         18.0% -> 15.0% pass@1
    SWE-agent with a whole-file viewer     12.7% (worse than a 30-line window)
    gpt-5(high), 2026                      still 8.4% malformed edits

And on line numbers, which several designs here could have leaned on:
**"GPT is terrible at working with source code line numbers... backed up by
many quantitative benchmark experiments."** OpenAI's V4A format omits them
deliberately.

### The measurement that had not been made

Nobody had published the document-format version, so D10 ran it — the same
8-row table in four representations:

    lines usable as an edit anchor     .tbl 100%   vs nested JSON 12.8%
                                                    (16.8% even with row ids)
    minimum unique anchor for one edit .tbl 1 line vs JSON 4-7 lines,
                                                    3 ambiguous, no 'flange'
                                                    anywhere in the anchor
    anchor survival under an unrelated upstream edit:
      reflowed prose                   6 of 6 lines changed, anchor DESTROYED
      R6 semantic line breaks          1 of 6, anchor SURVIVES

**R6 was adopted so `git blame` would stop crediting the reflower. It turns out
to be independently load-bearing for agent editing.** Two unrelated
requirements selected the same convention, which is the strongest kind of
evidence a design decision can get.

### A distinction the design was blurring

    line-orientation      buys edit LOCATABILITY
    nominal addressing    buys merge CORRECTNESS

They are different properties and both are needed. The proof they are
independent: an A1-formula CSV scores perfectly on locatability and still
merges to 480 instead of 660.

### What to ship

1. The format IS the interface. The highest-leverage agent decision is one
   already made for git.
2. Validate on write (I5 + I7), with errors that name ENTITIES, not offsets.
3. **Addressed reads, not addressed writes.** Deterministic addressing pays on
   reads; writes should stay textual with aider-grade fuzzy repair.
4. Exactly two structured writes: `set <address> <value>` and `apply <patch>`.
   No `insert_row_after`, no `move_block`, no typed canvas mutations — those
   are a schema, and the schema is what ages badly.
5. Before ever shipping a structured edit API, run the ablation nobody has run:
   one arm editing `.tbl` as text, one calling `set_cell`.

## Addressing: keep the grammar, add nothing

The taxonomy that settles it:

    query language      transient, may return empty   (JSONPath, XPath,
                                                       tree-sitter, jq)
    identity language   durable, must fail loudly     (our name paths)

    A query language may appear on a command line.
    Only an identity language may be written into a file.

Enforced mechanically: query output must be name paths, never offsets.

Corroboration from three directions: W3C Web Annotation's positional selector
carries an explicit warning that "any edits or dynamically transcluded content
may change the selection" and recommends pairing it with a content quote;
Obsidian independently shipped in-file `^block-id`; LSIF moved to SCIP,
replacing position ranges with string symbols. And a tree-sitter run shows the
query staying valid while every byte range it returns drifts — `total` moved
from byte 4 to 35 after one insertion above it.

**The cautionary tale: LSP's UTF-16 position encoding is "a legacy of VSCode's
JavaScript implementation".** The issue was opened January 2018 and fixed in
3.17 in May 2022 — and the fix could only ADD an alternative. UTF-16 remains
mandatory for every server forever. *A position encoding, once shipped, cannot
be removed.* This is the single best argument for having no coordinates in the
grammar at all.

## Extensions: three tiers, and no UI API

    Tier 1  DATA, not code -- a type is a grammar + named queries + a template
    Tier 2  a program on PATH (`gws-type-<suffix>`, NDJSON, the four functions)
            -- git's own `git-foo` mechanism: 20 years, no registry, no ABI
    Tier 3  in-process, first-party frontends only, explicitly unstable

Zed's own docs support tier 1 being the bulk: "only language server, context
server and debugger extensions require custom Rust."

**No UI API. This is the one that would be unrecoverable.** Obsidian's document
API is thin — `Vault` is strings, `MetadataCache` is an index, no AST — and it
survived a whole CodeMirror 6 rewrite. Its `Modal`/`Setting`/DOM surface is
what welds it to Electron permanently. VS Code made the opposite choice, which
is why the same extensions run in a browser, over SSH, and in a WebWorker.

No WASM yet. WASI 0.2.0 remains the cited stable release, and nothing in tiers
1-2 forecloses adding it later.

Adopt Neovim's API contract nearly verbatim (an `opts` dict everywhere,
additive-only fields, a private namespace convention, machine-readable `since`
and `deprecated_since`), plus pandoc's in-band version stamp.

## MCP

A thin adapter over the same plumbing, not a parallel surface, and capped at
five tools. Anthropic's own measurement of the alternative — code execution
against an API instead of shipping every tool schema up front — is **150,000
tokens to 2,000, "a time and cost saving of 98.7%"**. The cost is shipping
schemas eagerly, not any one vendor's schema.

---

## Independently reproduced: the anchor-survival result

`experiments/L8-anchors/`. Same paragraph, two serializations. The edit is an
UNRELATED insertion by someone else at the top — the ordinary case, not an
adversarial one:

    reflowed prose (72 col)   4 lines,  5+/4-  anchor line intact: False
    semantic line breaks      4 lines,  1+/0-  anchor line intact: True

Reflowing destroys every line and with it every anchor an agent or a comment
was holding. Semantic line breaks add one line and touch nothing else.

**R6 now rests on three independent measurements**: `git blame` correctness
(D9: the rewrapper credited with 6 of 10 lines, including two paragraphs he
never touched), agent edit-anchor survival (D10, and reproduced here), and
standoff-annotation reanchoring (D5's OHCO argument that comments must live in
a sidecar keyed to stable block anchors).

One convention, adopted for one reason, turns out to be required by three
unrelated parts of the system. That is the pattern to look for when deciding
which conventions are real and which are taste.

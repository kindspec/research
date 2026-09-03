# Pass 8 — sub-artifact identity: no minted ids

## The tension dissolves, and my H9 was not radical enough

The conflict was: L3 showed block correspondence can be COMPUTED by similarity
(no ids in the file); D5's OHCO result showed comments must live in a standoff
sidecar, which appeared to require STORED ids. I proposed a hybrid — ids
materialised on demand when something references a block.

The resolution is that these are **three problems that have been conflated**,
and none of the three wants a minted id:

    job              question                        mechanism           in file?
    correspondence   which block in v2 is this one?  similarity matching no
    reference        what do I write to point here?  a name the AUTHOR   only where a
                                                     chose (heading slug human named
                                                     or region marker)   something
    anchoring        where is the span this comment  W3C quote +         no
                     is about?                       prefix/suffix,
                                                     two-stage

The OHCO argument rests on a hidden premise — that a standoff sidecar must
point at an *identifier*. It need not. It can point at a **quote**.

## The measurement that settles it

Two-stage quote anchoring (block first, then span), resolved across 25 commits
of real editing history on real corpora (`rust-lang/book`, `obsidian-help`,
`commonmark-spec`):

    92.9% correct     7.1% loud refusal     0.00% silent-wrong

Exactly the failure profile I3 demands. And the decisive comparison:

**A stored id under stock git survives only when the block's bytes did not
change — precisely the case an exact-quote match already handles.**

So under stock git a stored id buys nothing over a quote anchor. The pro-id
case is correct for a system with a deployable merge driver or a database.
I6 says this is neither.

## The framing that makes it obvious in retrospect

    A minted sub-file id is the prose form of `col_a7f3`.

RESEARCH.md already rejected exactly this shape for tables: "in a plaintext
format the file is the UI; `=col_a7f3 * col_9b21` is positional addressing with
the ergonomics removed." `^7c475260-a227-4869-a31f-cb5f341b6ffe` is that same
sentence, in a document. It is a coordinate with the coordinates hidden. I2
does not merely permit this conclusion — it requires it.

## Block ids are the worst case of the design's own known defect

PASS4 established that scattered namespaces are silent-wrong generators. Block
ids are one binding per block scattered across every line of every file.
Reproduced: two branches each add a DIFFERENT new block, each minting the same
id, in distant parts of one file —

    exit=0   markers=0   occurrences of ^a3f91c2b: 2

And it does not take two people. One author **copy-pastes** an id-bearing
paragraph into an appendix while another retitles the document far away: clean
merge, two identical ids, every reference to it silently ambiguous. Copy-paste
is the commonest operation in a document editor.

## The refinement this forces on PASS4's rule

PASS4 said: co-locate a namespace's bindings so a collision is a line
collision. That is one way to make collisions visible. There is a stronger one,
and the design already has it:

    I7 STRICT PARSING makes a SCATTERED namespace safe, because the parser
    reads the whole artifact and can reject duplicates wherever they sit.

Markdown's link labels are unsafe not because they are scattered but because
**nothing validates them**. Our formats parse the whole file and refuse
duplicates, so scattering costs visibility in `git diff` but not correctness.

    co-location  -> git can see the collision      (cheap, partial)
    validation   -> the parser sees the collision  (complete, needs the tool)

Both are wanted. Co-location protects a user who never installs anything;
validation protects everyone else.

## Where this leaves the table row id

D6's ablation showed that for TABLE ROWS an opaque id column is the only
identity function surviving all four scenarios — natural keys lose an edit on
rename and overwrite a row on duplication; content hashes split rows.

Not a contradiction, because the criterion is *the cheapest mechanism that
yields 0% silent-wrong for that data shape*:

    prose blocks   large, distinctive     -> similarity matching works
    table rows     short, near-identical  -> similarity fails; needs a key

And the asymmetry D6 identified holds the line: **a human writes column NAMES
into formulas; a human never writes a row id into anything.** The row id is a
correspondence mechanism, never a reference — machine-managed noise in a column
the reader ignores, not an address anyone types, and not something another
artifact points at.

Duplicate row ids are caught by I7 at parse time, per the refinement above.

## The rule that falls out for transclusion

**A referrer never writes to the target.** Materialising an id into a file
because someone else read it is a write caused by an act of reading: it dirties
a file another person may have open, produces a diff nobody made, and lets two
concurrent referrers mint two different ids for the same block.

References therefore point at names the author already chose. If a block has no
name, it cannot be referenced until a human names it — the correct incentive,
and it keeps unreferenced prose completely clean.

## Honest limits, recorded

- A deliberate search for published prior art preferring computed anchoring
  over stored ids in a plaintext note system **found nothing**. The conclusion
  has no located precedent agreeing with it and should be held accordingly.
- The 92.9% / 7.1% / 0.00% figures come from one pass over three corpora. The
  0.00% silent-wrong is the load-bearing number and deserves independent
  replication before it is relied on.

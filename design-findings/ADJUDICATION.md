# Adjudicating the prosecution

D1 returns "do not build it — not descope, not not-yet." Its concession is a
table format plus a merge driver plus an IronCalc binding: "Build the merge
driver." Taking each kill-shot against the evidence the other tracks produced.

## 1. "Git does not need plain text — textconv gives semantic diff on .docx"

**Partly conceded.** 22 lines of glue does give readable `git diff` on binary
Office files, and git's own manual uses a word processor document as the
example. This genuinely weakens "you need plain text to use git".

**But it is a DIFF, not a merge**, which D1 concedes only in the residual — and
three things it does not address: you cannot grep it, cannot edit it with any
tool, and cannot resolve a conflict with it.

**And the rebuttal has the defendant's own disease.** `textconv` is configured
in `.git/config`. It is exactly as undeployable as the merge drivers D3 and D9
found cannot travel: it does not survive a fresh clone, and a bare repo does
not consult `.gitattributes` at all. D1's alternative fails the same
portability test it never applies to itself.

## 2. "Git does not merge documents; it conflicts or corrupts"

**Conceded in full, and it is the strongest point in the document.** Two
writers changing different sentences produce a clean merge whose result says
14 days in one line and 30 days in another. No representation fixes this. My
design does not fix it. D2 found the same class independently.

Two qualifications that matter for the verdict, neither of which rescues the
merge story:

- **It is not git-specific.** Google Docs takes both edits too. This is an
  argument against "merge solves collaboration", not against git.
- **It argues against the CRDT alternative more strongly than against git.**
  D1's own citation — Kleppmann et al., PaPoC '19, `Hello Al Ciharcliee!` and
  "we are not aware of any published work that fully explains or addresses it"
  — is evidence against CRDT-as-storage, which is the main competing design.

Conclusion: **semantic conflict is a universal limit and must be stated as
one. "Correct merges" cannot be a headline claim.** What survives is narrower
and still real: eliminating merges that are wrong for MECHANICAL reasons — a
range that failed to widen, a coordinate that shifted, a namespace collision
git could not see.

## 3. "Branching for writers is a negative result, not an absence"

**Conceded.** Upwelling built git-style dependent branches, user-tested them,
and deleted them. Overleaf hard-codes exactly one branch named `main`.
Penflip's founder wrote that non-developers "don't understand branches, forks,
commits, rebasing, cloning... and they don't care to learn", then removed git
from his own homepage within a month. D4 found Patchwork's surviving design is
deliberately anti-git: edit on main by default, no branching from branches,
merge deletes the branch.

This does not damage the design; it sharpens it. **Branching is not a value
proposition and must not be sold as one.** History, review, attribution,
offline and portability are.

## 4. "Git destroys the attribution it is credited with"

**Answered.** D9 measured the same failure — blame credited the reflower with
6 of 10 lines, including two paragraphs he never touched — and measured the
fix: the identical edit on semantically line-broken text blames correctly with
a `1 1` numstat. It is a format decision, not a git limitation.

**With an honest tension:** one sentence per line is also what makes kill-shot
2's clean-but-contradictory merge easier. Both are true. Attribution improves;
semantic conflict does not.

## 5. "Plain text is not the durable open format"

**The ambiguity half lands.** pandoc treats Markdown as nine formats;
CommonMark cannot express a table and is still 0.x after twelve years; and its
own site says the divergence "often isn't discovered right away" because
nothing counts as a syntax error. D5 reached the same verdict independently
and harder: jgm on his own spec, "I despair, at times, of getting to a spec
that is worth calling 1.0."

**This is an argument for the deliverable, not against the project.** The
answer to "no unambiguous spec" is a specification with an executable
conformance suite — which is what L6 is, and what separates CommonMark (many
independent implementations) from org-mode (none, because its spec is
descriptive of `org-element.el`).

**The size half is noise.** 145,584 bytes of markdown against 28,457 of .docx
compares uncompressed text to a ZIP. Git delta-compresses text extremely well
and D9 measured 13.8x on `gc`.

**The ODF point is a real MARKET argument** — ISO-standardised, vendor-backed,
legally mandated, and it lost anyway when Massachusetts changed "must" to
"may". It belongs in the risk section, not the architecture section.

## 6. "Sixty-six years of graveyard, and Hipp says the core problem is open"

**Graveyard conceded** — Xanadu, OpenDoc, Chandler, Groove, Beaker, Solid at
+1,186 accounts in year eight. It is the reason the verdict cannot be "build a
suite".

**The Hipp quote is misapplied.** He says there are no good ways to merge
"these kinds of BINARY artifacts". That is an argument for plaintext, not
against it, and it is quoted here as though it condemned the whole enterprise.

## The decisive point: D1's own remedy is refuted by a parallel track

D1 concedes the residual gap and prescribes: ship it "as a `git merge` driver
and a library, the way `daff` did."

Both halves of that prescription were measured false this week.

- **`daff` does not solve it.** D3: daff merged the rows of an A1-formula CSV
  perfectly and produced the IDENTICAL WRONG ANSWER as plain git (3500 vs a
  correct 5100, confirmed in LibreOffice). A structural merger cannot see that
  a string in a cell encodes a position.
- **A merge driver cannot be deployed.** D3 and D9: `.gitattributes` travels,
  `merge.<name>.driver` does not; a fresh clone silently falls back to line
  merge; a BARE repo ignores `.gitattributes` entirely and writes conflict
  markers into a file declared `binary`; GitLab.com does not support custom
  merge drivers; GitHub Support says GitHub "doesn't consider user-defined
  .gitattributes files."

**So the prosecution correctly identifies the gap and prescribes a vehicle
that does not work.** The gap is real; the remedy is not a merge driver.

## What the evidence actually supports

Correctness cannot come from a merge algorithm — undeployable, NP-hard,
heuristic, and unable to fix positional addressing at any price. It has to
come from the REPRESENTATION, and a representation is only real if it is
specified and testable.

    The deliverable is a format specification plus an executable conformance
    suite that runs against stock git, plus a reference implementation small
    enough to be credible.

Where D1's scoping is too narrow: it declares the sequential leg solved
(pandoc, Typst, every editor) and the spatio-visual leg solved (draw.io XML,
D2, Graphviz — "one-line diffs"). That conflates diff with merge, the same
conflation it convicts the proposal of. L4 measured that a full-coordinate
scene graph — which is what draw.io's `<mxCell>` XML is — both conflicts AND
produces unparseable output.

Where D1's scoping is right: the STRENGTH of the gap is very uneven.

    tables     strongest. Measured silent-wrong, formal backing, and
               unclaimed -- Google shipped Tables in 2024 and explicitly
               declined the per-row case.
    canvas     real but narrow. Structured diagrams are largely text already;
               freeform is excluded by its own nature.
    documents  the reserialization problem is real but only bites STRUCTURED
               editors; a plain text editor never had it. And markdown has an
               I6 violation I cannot fully close.

**Verdict shape: build a missing layer, not a suite — the layer being the
representation discipline, specified and tested, with tables as the beachhead
because that is where the defect is measurable and the ground is unclaimed.**

Held open pending R1, the red team assigned to break the table format itself.
If R1 finds a silent-wrong in the design's own beachhead, the verdict changes.

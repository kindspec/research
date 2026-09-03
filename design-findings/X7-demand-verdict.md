# The demand finding, and what it does to the verdict

## The result

**No population has demonstrated the pain this design targets.**

The single most damaging sentence in the research: *not one instance was found,
anywhere, of a practitioner reporting a silently wrong number produced by a
merged CSV.* That is the exact failure DESIGN.md exists to remove.

    HN "csv merge conflict"              0 stories
    SO [git] csv merge conflict          9 questions
    SO version-control + csv             2   (git + json: 189)
    SO git+excel trend                   2018: 7 -> 2021: 2 -> 2024: 1

## The strongest single datum: people do not hack around it, they give up

    *.xlsx binary declared        3,672 repos
    *.xlsx in Git LFS             2,776 repos
    diff=xlsx attempted              28 repos

**A give-up-to-hack ratio of roughly 230:1.** The prior brief argued that the
size of a hack ecosystem is the best proxy for unmet demand. By that measure the
demand is not merely unproven — the measurement was taken and it came back
negative. Tabular git tooling shows ~240 repo-level installations against ~6,400
for the Jupyter equivalents, and six of twelve tools surveyed are archived or
untouched for three to twelve years.

## The incumbents tried and left

- **GitHub built the productised version — Flat Data — and archived it.**
- **Over $65M of capital, zero standalone survivors.** Datafold's `data-diff`,
  literally this product, archived 2024-05-17. Iterative.ai sold DVC.
- **DoltHub became healthy by abandoning data collaboration.** Its founder:
  *"It felt like we were pushing data sharing but OLTP was pulling us."*
- Money went to *replacing* spreadsheets at roughly 100:1 — Anaplan ~$10.4B,
  Adaptive $1.55B — against audit-side tuck-ins at undisclosed prices.

## And there is no regulatory wedge

Full-text search of **PCAOB AS 2201**: zero occurrences of "spreadsheet",
"end-user computing", or "version control". **BCBS 239** contains "lineage",
"version" and "audit trail" nowhere. The one binding text found is 21 CFR
Part 11 §11.10(e)/(k)(2) for GxP, which a commit graph satisfies natively — but
no evidence was gathered that those teams want git.

## The finding that hurts most

The narrowest population with any behavioural evidence — public reference-data
registries whose product *is* a table — **does not experience the problem the
design solves.** They serialise writes through a bot and a PR queue, so the
concurrent-insert silent-wrong merge that motivates I2, and the 480-vs-660 case
itself, never arises for them. They also have no money.

And the one severe cost anyone was documented paying is not fixed by this
design. Kubernetes #35850: *"This is causing completely unrelated PRs to have
merge conflicts with each other"* — and then, decisively: *"Any time two commits
change the same file one needs to be rebased, even if there are no merge
conflicts."* That is merge-queue file contention, which correct merging does not
touch. They deleted the CSV and moved to one record per file.

**Every observed mitigation moves away from the shared table**, not toward
better tooling for it.

## The inverse finding, which is the one to act on

What those registries actually built for themselves, in their own repositories:
a CI check with `continue-on-error: false`, a bespoke `db:validate` script, a
CONTRIBUTING file warning contributors in bold to *"make sure that the number of
columns in the file has not changed"*, and PR comments containing pasted raw
rows with line numbers.

That is a hand-rolled version of this design's **validator and conformance
suite**, arrived at independently by people who had never read it. And the
pasted-rows-with-line-numbers habit is demand for nominal row addressing *in the
review channel*.

    Demand exists for the VALIDATOR. It does not exist for the MERGE.

That fits the namespace audit exactly: 9 of 11 namespaces are protected by
validation rather than co-location, and CI is the only portable enforcement
point. The thing with observed demand and the thing the architecture actually
needs are the same artifact.

## What this does to the verdict

The architecture is unchanged and still holds. What changes is the claim made
for it.

    WAS: build a representation discipline so that git merges tabular data
         correctly, because positional addressing merges silently wrong.

    NOW: build a specified, conformance-tested format and a validator, because
         teams maintaining tabular data in git are already hand-rolling
         validators and getting them wrong. Correct merging is a PROPERTY of
         the design, not the reason anyone will adopt it.

Stated plainly: **the merge story is the theory; the validator is the product.**
Leading with 480-vs-660 sells a problem nobody reports having. Leading with
"your CSV contract, checked in CI" sells something four registries built by hand.

## Two honest caveats, in both directions

**For the design.** A silent failure leaves no complaint by definition, so
absence of complaint is genuinely weak evidence. The 480-vs-660 case would be
invisible to whoever suffered it. But the 230:1 give-up ratio is *not* subject
to that objection: it measures whether people try, not whether they notice.

**Against the research.** Reddit returned 403 to every method attempted, and the
search budget was exhausted at 200/200. Reddit is precisely where non-developer
spreadsheet users complain, so the largest single hole sits over the most likely
population. This finding should be treated as strong but not closed.

## Consequence for scope

Build it as infrastructure, not as a product, and expect adoption to be slow and
driven by the validator. Do not build a business plan on the merge story. And
before writing a line of production code, get the spec and suite in front of one
of the four named registries and find out whether they would replace their
hand-rolled check with it.

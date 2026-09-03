# The mutation gate disarmed itself, silently

Found while scaffolding the repository, and it is the most on-thesis bug of the
whole project.

## What happened

`ruff format` ran for the first time as part of wiring up `just check`. It
changed quote style, rewrapped some lines, and I renamed an ambiguous `l` to
`line` to satisfy E741. All cosmetic. Then:

    before formatting   27 killed, 0 survived
    after  formatting   10 killed, 0 survived, 23 STALE

The mutants were exact source-text patches. Reformatting invalidated the
patterns, so the gate could no longer apply them — **and it reported this as a
harmless `??` note while still exiting 0.**

## Why it matters more than the fix

A verification tool that quietly stops verifying is precisely the failure this
project exists to eliminate. It is the same shape as every silent-wrong merge in
the research: the operation reports success, the output looks plausible, and
nothing anywhere says the check did not happen.

And the mechanism is the one the design already names — **coupled
representation**. The mutant patterns were coupled to the *formatting* of the
code they test, which is state that changes for reasons unrelated to behaviour.
The gate had exactly the defect its own project is organised against.

It also failed the design's own I3: a broken reference must fail loudly and
locally, never as a plausible-looking success. `??  PATTERN NOT FOUND` printed
to stdout and exited 0 is the tooling equivalent of `#REF!` rendering as zero.

## Fixes

1. **A stale mutant is now a hard failure**, exiting non-zero, with an
   explanation naming the cause. If the gate cannot apply a mutant it is not
   measuring anything and must say so.
2. **Matching is normalised** for whitespace and quote style, so the commonest
   reformats no longer stale a pattern. This narrowed 23 stale to a smaller set;
   durable matching is being finished separately.

## The rule this yields

    Any tool whose job is to detect a failure must itself fail loudly when it
    cannot run. "Skipped" and "passed" must never share an exit code.

That belongs in the spec's neighbourhood, not just this repository: it is the
same argument as `gws doctor` making a missing merge driver loud rather than
letting git silently fall back to a line merge.

## Fourth instance of the standing pattern

The gate was written by the person who wrote the implementation it tests, and
its staleness was invisible until something external — a formatter — perturbed
it. Repairing it has therefore been handed to a different author, per
CONTRIBUTING.md's standing rule.

---

# Two more instances of the same pattern, found during the first commit

## The linter deleted the evidence of an unwired safety check

I wrote `order_declared = True` in the parser, intending it to catch a duplicate
`order` declaration, and never wired it up. Ruff's `F841` correctly reported it
as an unused variable. I ran `ruff check --fix --unsafe-fixes`, and **the
autofix deleted it.**

The lint rule was saying *"you wrote a check and never used it."* The autofix
read that as *"delete the dead code."* The bug it was meant to catch was live:
`order := none()` followed by `order := by(date)` was silently accepted, because
the actual guard tested `if order is not None` and `none()` sets order to
`None`.

Found by the mutation-gate author, not by me, and not by the linter — which had
the information and discarded it.

## The first commit would have destroyed a fixture

`git add` warned:

    warning: in the working copy of 'conformance/cases/roundtrip/crlf/input.mdtbl',
    CRLF will be replaced by LF the next time Git touches it

The dev-toolbox `.gitattributes` sets `* text=auto eol=lf`. That would have
rewritten the **one fixture whose entire purpose is to assert that CRLF is
preserved byte-exactly.** The case would still have passed, because after
normalisation it would have been testing LF against LF.

Fixed with `conformance/cases/** -text`, verified 9 CR bytes in the working
tree and 9 in the index, and re-verified on a fresh clone.

## The count so far

Five instances, in five different subsystems, of one pattern:

    1. `#REF!` rendering as zero                     (the format)
    2. the mutation gate going stale on a reformat   (the gate)
    3. the gate counting a kill against a red baseline (the gate again)
    4. `canon = identity` passing a fixture with no runner branch (the runner)
    5. git normalising the bytes a fixture asserts on (the VCS itself)

Every one is the same shape: **a check that cannot fail, reporting a pass.** The
project's own tooling reproduced its subject matter five times, and in four
cases the person who wrote the check was not the person who found it could not
fail.

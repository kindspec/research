# L7 — making absence loud (my own work)

`experiments/L7-loud-absence/`. The security research reframed the design's
biggest risk: git's split between DECLARING a capability (`.gitattributes`,
tracked, travels) and BINDING it (`.git/config`, local, never travels) is not
a defect — it is the boundary that stops a cloned repository from executing
code. Keep the boundary; fix the silence.

## The prototype

`gws doctor`, ~30 lines: read the declarations, resolve each against local
config, refuse if any is unbound.

    === fresh clone, nothing installed (the dangerous default) ===
      .gitattributes:1  *.tbl   merge=gws-table  -> NOT BOUND
      .gitattributes:2  *.md    diff=gws-prose   -> NOT BOUND

      REFUSING: 2 declared capability(ies) are not available.
        - *.tbl declares merge=gws-table, but merge.gws-table.driver is unset.
          git would SILENTLY fall back. Install the tool, or pass --force.
    exit=1

    === after binding one locally ===
      .gitattributes:1  *.tbl   merge=gws-table  -> BOUND
      .gitattributes:2  *.md    diff=gws-prose   -> NOT BOUND
    exit=1

It also detects the case D9 found and I reproduced: in a **bare** repository
`.gitattributes` is not consulted at all, so every declaration is inert and a
forge-side merge writes conflict markers into files the repo declared
protected.

## Why this is the right shape

- **It does not weaken git's security property.** The repository still cannot
  bind anything. `doctor` only reports the gap; a human still installs the tool.
- **It converts the worst failure mode into the most visible one.** The silent
  downgrade to line merge is where every catalogued silent-wrong merge actually
  reaches a user. Refusing is strictly better than degrading.
- **It is I3 applied to the toolchain.** The same rule that says a broken
  reference must never resolve to a plausible value says a missing merge driver
  must never resolve to a plausible merge.
- **It composes with I6.** Because the FORMATS are correct under stock git,
  `doctor` failing is an inconvenience, not a blocker — the artifacts still
  merge correctly without the tool. If correctness depended on the driver, a
  loud refusal would be the only safe behaviour and the system would be
  unusable without installation. This is the payoff of putting correctness in
  the representation.

## The general rule

    Every capability a repository declares must be verifiable, and the absence
    of a declared capability must be an error, never a downgrade.

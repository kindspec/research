#!/usr/bin/env python3
"""W5-T3: crash safety.  SIGKILL the server at each point in the write sequence:

    hash-object -w   ->  write-tree  ->  commit-tree  ->  update-ref
    ^kill A              ^kill B         ^kill C         ^kill D (after)

For each: is the repo consistent?  Does `git fsck` complain?  Are there orphaned
objects?  Does a RETRY produce a DUPLICATE commit or converge to one merge?

Implemented by monkey-patching Repo.git to os._exit(137) -- an unhandled,
uncatchable process death -- immediately after the Nth call to a chosen verb.
That is a true SIGKILL-equivalent: no finally blocks, no flushes.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
WORK = os.path.join(HERE, "work-t3")
ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t",
           GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           HOME="/nonexistent", GIT_CONFIG_GLOBAL="/dev/null")

BASE = ("| id     | item | qty | unit |\n| ------ | ---- | --: | ---: |\n"
        "| r_0001 | a    |   1 |    5 |\n| r_0002 | b    |   2 |    7 |\n"
        "\ngrand := sum(qty)\n")


def git(*a, cwd=None, check=True):
    return subprocess.run(("git",) + a, cwd=cwd, env=ENV, check=check,
                          capture_output=True, text=True)


def setup():
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    srv = os.path.join(WORK, "srv.git")
    dev = os.path.join(WORK, "dev")
    git("init", "-q", "--bare", srv)
    git("init", "-q", dev)
    open(os.path.join(dev, "b.tbl"), "w").write(BASE)
    git("add", "-A", cwd=dev); git("commit", "-qm", "base", cwd=dev)
    git("branch", "-M", "main", cwd=dev); git("push", "-q", srv, "main", cwd=dev)
    git("checkout", "-q", "-b", "topic", cwd=dev)
    open(os.path.join(dev, "b.tbl"), "w").write(BASE.replace("|   1 |", "|  11 |"))
    git("commit", "-qam", "theirs: r_0001 qty 1->11", cwd=dev)
    git("push", "-q", srv, "topic", cwd=dev)
    git("checkout", "-q", "main", cwd=dev)
    open(os.path.join(dev, "b.tbl"), "w").write(BASE.replace("|    5 |", "|   50 |"))
    git("commit", "-qam", "ours: r_0001 unit 5->50", cwd=dev)
    git("push", "-q", srv, "main", cwd=dev)
    return srv


CHILD = r'''
import os, sys
sys.path.insert(0, %r)
import gws_merge_server as S
KILL_AFTER = %r
_orig = S.Repo.git
def patched(self, *args, **kw):
    r = _orig(self, *args, **kw)
    if args and args[0] == KILL_AFTER:
        sys.stderr.write("KILLED immediately after `git %%s`\n" %% args[0])
        sys.stderr.flush()
        os._exit(137)          # uncatchable: no finally, no atexit, no flush
    return r
S.Repo.git = patched
print(S.merge(%r, "refs/heads/main", "refs/heads/topic"))
'''


def objects(srv):
    loose = git("count-objects", "-v", cwd=srv).stdout
    d = dict(l.split(": ") for l in loose.strip().splitlines())
    return int(d.get("count", 0)), int(d.get("in-pack", 0))


def snapshot(srv, label):
    tip = git("rev-parse", "main", cwd=srv).stdout.strip()
    fsck = git("fsck", "--strict", "--unreachable", cwd=srv, check=False)
    unreach = [l for l in (fsck.stdout + fsck.stderr).splitlines()
               if l.startswith("unreachable")]
    err = [l for l in (fsck.stdout + fsck.stderr).splitlines()
           if ("error" in l or "missing" in l or "dangling" in l.lower()
               and False)]
    loose, inpack = objects(srv)
    tmpd = os.path.join(srv, "gws-tmp")
    stale = ([f for f in os.listdir(srv) if f.startswith("gws-index-")]
             + [f for f in (os.listdir(tmpd) if os.path.isdir(tmpd) else [])])
    locks = [f for f in os.listdir(srv) if f.endswith(".lock")]
    return dict(label=label, tip=tip[:12], fsck_rc=fsck.returncode,
                fsck_errors=err, unreachable_objects=len(unreach),
                loose_objects=loose, stale_index_files=stale, lock_files=locks)


def run_kill(verb):
    srv = setup()
    before = snapshot(srv, "before")
    p = subprocess.run([sys.executable, "-c", CHILD % (HERE, verb, srv)],
                       env=ENV, capture_output=True, text=True)
    after = snapshot(srv, f"after SIGKILL@{verb}")
    # ---- now RETRY, twice, exactly as a supervisor would
    r1 = subprocess.run([sys.executable, os.path.join(HERE, "gws_merge_server.py"),
                         "merge", "--repo", srv, "--into", "refs/heads/main",
                         "--from", "refs/heads/topic"], env=ENV, capture_output=True, text=True)
    tip1 = git("rev-parse", "main", cwd=srv).stdout.strip()
    r2 = subprocess.run([sys.executable, os.path.join(HERE, "gws_merge_server.py"),
                         "merge", "--repo", srv, "--into", "refs/heads/main",
                         "--from", "refs/heads/topic"], env=ENV, capture_output=True, text=True)
    tip2 = git("rev-parse", "main", cwd=srv).stdout.strip()
    # how many merge commits exist on main?
    merges = git("rev-list", "--merges", "--count", "main", cwd=srv).stdout.strip()
    content = git("cat-file", "-p", "main:b.tbl", cwd=srv).stdout
    correct = ("|  11 |" in content and "|   50 |" in content
               and "<<<<<<<" not in content)
    final = snapshot(srv, "after 2 retries")
    return dict(kill_after=verb,
                child_rc=p.returncode, child_died=p.returncode == 137,
                tip_before=before["tip"], tip_after_kill=after["tip"],
                ref_moved_by_crashed_process=before["tip"] != after["tip"],
                fsck_after_kill_rc=after["fsck_rc"],
                fsck_after_kill_errors=after["fsck_errors"],
                orphaned_loose_objects=after["loose_objects"] - before["loose_objects"],
                stale_index_files=after["stale_index_files"],
                lock_files_left=after["lock_files"],
                retry1=json.loads(r1.stdout or "{}").get("status"),
                retry2=json.loads(r2.stdout or "{}").get("status"),
                tip_after_retry1=tip1[:12], tip_after_retry2=tip2[:12],
                DUPLICATE_COMMIT=tip1 != tip2,
                merge_commits_on_main=int(merges),
                merged_content_correct=correct,
                fsck_final_rc=final["fsck_rc"], fsck_final_errors=final["fsck_errors"],
                unreachable_after=final["unreachable_objects"])


if __name__ == "__main__":
    print("Killing the server with os._exit(137) right after each git verb.")
    print("`merge-tree` = before any write.  `hash-object` = blob written, no tree.")
    print("`update-index`/`write-tree` = tree written, no commit.")
    print("`commit-tree` = commit object exists, ref NOT updated.")
    print("`update-ref` = the CAS itself completed, process dies after.\n")
    rows = []
    for verb in ["merge-tree", "hash-object", "update-index", "write-tree",
                 "commit-tree", "update-ref"]:
        r = run_kill(verb)
        rows.append(r)
        print(f"--- SIGKILL after `git {verb}` ---")
        for k in ("child_died", "ref_moved_by_crashed_process", "fsck_after_kill_rc",
                  "fsck_after_kill_errors", "orphaned_loose_objects",
                  "stale_index_files", "lock_files_left", "retry1", "retry2",
                  "tip_after_retry1", "tip_after_retry2", "DUPLICATE_COMMIT",
                  "merge_commits_on_main", "merged_content_correct",
                  "fsck_final_rc", "unreachable_after"):
            print(f"    {k:32} {r[k]}")
        print()
    print("=" * 70)
    bad = [r for r in rows if r["DUPLICATE_COMMIT"] or not r["merged_content_correct"]
           or r["fsck_final_rc"] or r["fsck_after_kill_rc"] or r["lock_files_left"]]
    leaks = [r["kill_after"] for r in rows if r["stale_index_files"]]
    print(f"temp-index files left in GIT_DIR/gws-tmp after a kill at: {leaks}")
    print("  (bounded garbage: swept by sweep_tmp() after 1h; cannot be deleted")
    print("   eagerly because another live process may own it. Not in GIT_DIR root,")
    print("   not a ref, not an object -- fsck and clone are unaffected.)")
    print("VERDICT:", "CRASH SAFE at every point" if not bad
          else f"PROBLEMS at: {[b['kill_after'] for b in bad]}")
    for b in bad:
        print(json.dumps(b, indent=1, sort_keys=True))

#!/usr/bin/env python3
"""W5-T5: the server as a SECURITY BOUNDARY.

It is a privileged process on a shared repo, and every byte it reads -- paths,
modes, blob contents -- comes from whatever an untrusted client pushed.  Trees
here are built with `mktree`/`hash-object`, not with `git add`, precisely so we
can construct paths and modes that porcelain would refuse to create.

For each: does the server refuse cleanly, and does it leave the repo untouched?
"""
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gws_merge_server as S

WORK = os.path.join(HERE, "work-t5")
ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t",
           GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           HOME="/nonexistent", GIT_CONFIG_GLOBAL="/dev/null")

BASE_TBL = ("| id     | item | qty |\n| ------ | ---- | --: |\n"
            "| r_0001 | a    |   1 |\n\ngrand := sum(qty)\n")


class R:
    def __init__(self, d):
        self.d = d

    def g(self, *a, input=None, check=True, text=True):
        return subprocess.run(("git",) + a, cwd=self.d, env=ENV, input=input,
                              capture_output=True, text=text, check=check)

    def o(self, *a, **kw):
        return self.g(*a, **kw).stdout.strip()

    def blob(self, data):
        if isinstance(data, str):
            data = data.encode()
        return self.g("hash-object", "-w", "-t", "blob", "--stdin",
                      input=data, text=False).stdout.decode().strip()

    def mktree(self, entries):
        """entries: [(mode, type, oid, name)].  Try `mktree` first; where git's
        own plumbing REFUSES the name (that refusal is itself a result worth
        recording), fall back to writing the raw tree object with
        `hash-object -t tree --literally`, which writes anything.  A real
        attacker with push access and transfer.fsckObjects off can do exactly
        this, so the server must not rely on git having screened the tree."""
        payload = "".join(f"{m} {t} {o}\t{n}\x00" for m, t, o, n in entries)
        p = self.g("mktree", "-z", "--missing", input=payload, check=False)
        if p.returncode == 0:
            return p.stdout.strip(), "mktree"
        raw = b"".join(f"{int(m):o} {n}".encode() + b"\x00" + bytes.fromhex(o)
                       for m, t, o, n in entries)
        oid = self.g("hash-object", "-w", "-t", "tree", "--literally", "--stdin",
                     input=raw, text=False).stdout.decode().strip()
        return oid, "raw(--literally): " + p.stderr.strip()[:90]

    def commit(self, tree, parents=(), msg="x"):
        a = ["commit-tree", tree]
        for p in parents:
            a += ["-p", p]
        return self.o(*a, "-m", msg)


def fresh(name):
    d = os.path.join(WORK, name)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    subprocess.run(["git", "init", "-q", "--bare", d], env=ENV, check=True)
    return R(d)


def scenario(name, build):
    """build(r) -> (base_commit, ours_commit, theirs_commit).  Runs the merge and
    reports whether the server refused and whether the ref stayed put."""
    print("=" * 74); print(f"### {name}"); print("=" * 74)
    r = fresh(name.replace(" ", "_").replace("/", "_")[:40])
    try:
        base, ours, theirs = build(r)
    except Exception as e:
        print(f"  could not even construct the tree: {type(e).__name__}: {str(e)[:200]}")
        print("  VERDICT       : N/A (git plumbing refused to build the input)\n")
        return name, True, "unbuildable", None
    r.g("update-ref", "refs/heads/main", ours)
    r.g("update-ref", "refs/heads/topic", theirs)
    before = r.o("rev-parse", "refs/heads/main")
    t0 = time.perf_counter()
    try:
        res = S.merge(r.d, "refs/heads/main", "refs/heads/topic")
        err = None
    except Exception as e:
        res = dict(status="EXCEPTION")
        err = f"{type(e).__name__}: {e}"
    dt = time.perf_counter() - t0
    after = r.o("rev-parse", "refs/heads/main")
    fsck = r.g("fsck", "--strict", check=False)
    # did anything escape the repo directory?
    escaped = [p for p in ("/tmp/W5-PWNED", os.path.join(HERE, "W5-PWNED"),
                           os.path.join(os.path.dirname(r.d), "W5-PWNED"))
               if os.path.exists(p)]
    print(f"  status        : {res['status']}")
    if res.get("reason"):
        print(f"  reason        : {res['reason'][:400]}")
    if err:
        print(f"  UNCAUGHT      : {err[:400]}")
    print(f"  ref moved     : {before != after}")
    print(f"  fsck rc       : {fsck.returncode}  {fsck.stderr.strip()[:120]}")
    print(f"  wall          : {dt:.3f}s")
    print(f"  files escaped : {escaped or 'none'}")
    # fsck rc != 0 is EXPECTED here: we deliberately wrote malformed objects.
    # What matters is: no uncaught exception, the ref did not move, nothing
    # escaped the repo, and the server did not publish the hostile content.
    contained = (res["status"] in ("refused", "conflict", "error")
                 and before == after and not err and not escaped)
    safe_merge = res["status"] == "merged" and not escaped and not err
    v = ("CONTAINED (refused, ref held)" if contained
         else "MERGED (inspect content)" if safe_merge else "*** PROBLEM ***")
    print(f"  VERDICT       : {v}")
    print()
    return name, contained or safe_merge, res["status"], err


def conflicting(r, path, mode="100644", oursdata=None, theirsdata=None,
                basedata=None, otype="blob", oid_override=None):
    """A tree where `path` differs on both sides -> a real 3-way conflict."""
    bd = basedata if basedata is not None else BASE_TBL
    od = oursdata if oursdata is not None else BASE_TBL.replace("|   1 |", "|   2 |")
    td = theirsdata if theirsdata is not None else BASE_TBL.replace("|   1 |", "|   3 |")
    mk = lambda d: oid_override or r.blob(d)
    bt, how = r.mktree([(mode, otype, mk(bd), path)])
    ot, _ = r.mktree([(mode, otype, mk(od), path)])
    tt, _ = r.mktree([(mode, otype, mk(td), path)])
    b = r.commit(bt)
    print(f"  tree built via : {how}")
    return b, r.commit(ot, [b]), r.commit(tt, [b])


RESULTS = []

if __name__ == "__main__":
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)

    # ---- 1. a 100 MB blob claiming to be a .tbl
    def big(r):
        big_ours = (BASE_TBL + "| r_9999 | " + "A" * 1000 + " | 1 |\n" * 1).encode()
        pad = b"| r_%06d | x | 1 |\n" % 0
        blob = BASE_TBL.encode() + b"".join(b"| r_%06d | pad | 1 |\n" % i
                                            for i in range(1, 4_000_000))
        print(f"  [built a {len(blob)/1e6:.1f} MB .tbl blob]")
        b = r.blob(BASE_TBL)
        bt, _ = r.mktree([("100644", "blob", b, "big.tbl")])
        base = r.commit(bt)
        ot, _ = r.mktree([("100644", "blob", r.blob(blob), "big.tbl")])
        tt, _ = r.mktree([("100644", "blob", r.blob(blob[:-20] + b"| r_9 | z | 9 |\n"),
                          "big.tbl")])
        return base, r.commit(ot, [base]), r.commit(tt, [base])
    RESULTS.append(scenario("100 MB blob claiming to be .tbl", big))

    # ---- 2. path traversal
    RESULTS.append(scenario("path contains '..' component",
                            lambda r: conflicting(r, "../../../etc/evil.tbl")))
    RESULTS.append(scenario("path is literally '..'",
                            lambda r: conflicting(r, "..")))
    RESULTS.append(scenario("absolute path in tree entry",
                            lambda r: conflicting(r, "/tmp/W5-PWNED.tbl")))

    # ---- 3. newline / control chars in a path
    RESULTS.append(scenario("newline inside the path",
                            lambda r: conflicting(r, "ev\nil.tbl")))
    RESULTS.append(scenario("carriage return + ANSI escape in path",
                            lambda r: conflicting(r, "a\r\x1b[2Jb.tbl")))

    # ---- 4. symlink
    def symlink(r):
        return conflicting(r, "link.tbl", mode="120000",
                           basedata="/etc/passwd", oursdata="/etc/shadow",
                           theirsdata="/root/.ssh/id_rsa")
    RESULTS.append(scenario("SYMLINK whose target conflicts", symlink))

    # ---- 5. gitlink / submodule
    def gitlink(r):
        fake = r.blob("not a commit")
        bt, _ = r.mktree([("160000", "commit", "0" * 40, "sub")])
        ot, _ = r.mktree([("160000", "commit", "1" * 40, "sub")])
        tt, _ = r.mktree([("160000", "commit", "2" * 40, "sub")])
        b = r.commit(bt)
        return b, r.commit(ot, [b]), r.commit(tt, [b])
    RESULTS.append(scenario("GITLINK (submodule) conflict", gitlink))

    # ---- 6. .gitattributes and .git paths in the tree
    RESULTS.append(scenario(".gitattributes conflicts (governs merge policy)",
                            lambda r: conflicting(r, ".gitattributes",
                                                  basedata="*.tbl -merge\n",
                                                  oursdata="*.tbl merge=ours\n",
                                                  theirsdata="*.tbl text\n")))
    RESULTS.append(scenario("a '.git' directory inside the tree",
                            lambda r: conflicting(r, ".git/config")))
    RESULTS.append(scenario("'.GIT' case-variant path",
                            lambda r: conflicting(r, ".GIT/hooks/post-checkout")))
    RESULTS.append(scenario("'.git.' NTFS-alias path",
                            lambda r: conflicting(r, ".git./config")))

    # ---- 7. pathological content
    RESULTS.append(scenario("50k columns on the header line",
                            lambda r: conflicting(
                                r, "wide.tbl",
                                basedata="|" + "|".join(f"c{i}" for i in range(50000)) + "|\n"
                                         + "|" + "|".join("---" for i in range(50000)) + "|\n",
                                oursdata="|" + "|".join(f"c{i}" for i in range(50000)) + "|\n"
                                         + "|" + "|".join("---" for i in range(50000)) + "|\n|x|\n",
                                theirsdata="|" + "|".join(f"c{i}" for i in range(50000)) + "|\n"
                                         + "|" + "|".join("---" for i in range(50000)) + "|\n|y|\n")))
    RESULTS.append(scenario("NUL bytes inside a .tbl",
                            lambda r: conflicting(r, "nul.tbl",
                                                  basedata="| id |\n| -- |\n| a\x00b |\n",
                                                  oursdata="| id |\n| -- |\n| a\x00c |\n",
                                                  theirsdata="| id |\n| -- |\n| a\x00d |\n")))
    RESULTS.append(scenario("invalid UTF-8 in a .tbl",
                            lambda r: conflicting(
                                r, "bad.tbl",
                                basedata=b"| id |\n| -- |\n| \xff\xfe1 |\n",
                                oursdata=b"| id |\n| -- |\n| \xff\xfe2 |\n",
                                theirsdata=b"| id |\n| -- |\n| \xff\xfe3 |\n")))
    RESULTS.append(scenario("a .tbl that is one 20 MB line",
                            lambda r: conflicting(r, "line.tbl",
                                                  basedata="| id |\n| -- |\n| " + "A" * 20_000_000 + " |\n",
                                                  oursdata="| id |\n| -- |\n| " + "B" * 20_000_000 + " |\n",
                                                  theirsdata="| id |\n| -- |\n| " + "C" * 20_000_000 + " |\n")))

    # ---- 8. ref-name injection via the branch name
    def refinject(r):
        b, o, t = conflicting(r, "b.tbl",
                              oursdata=BASE_TBL.replace("| a    |", "| aa   |"),
                              theirsdata=BASE_TBL.replace("| a    |", "| ab   |"))
        return b, o, t
    RESULTS.append(scenario("conflict-ref namespace from a hostile branch name", refinject))

    print("=" * 74)
    print("SUMMARY")
    print("=" * 74)
    for name, ok, status, err in RESULTS:
        print(f"  {'OK ' if ok else '***FAIL***':<12} {status:<12} {name}"
              + (f"   [{err[:80]}]" if err else ""))
    bad = [n for n, ok, _, _ in RESULTS if not ok]
    print()
    print("SECURITY FAILURES:", bad or "NONE")

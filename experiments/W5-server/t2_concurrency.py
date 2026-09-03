#!/usr/bin/env python3
"""W5-T2: concurrency.  N processes each merge their own topic branch into the
SAME ref, simultaneously.  Does the CAS retry loop converge?  Where does it
livelock?  Measure throughput and retry counts at 2 / 8 / 32 / 64.

Every worker contributes ONE row.  The final table must contain ALL N rows and
every worker commit must be an ancestor of the final tip.  A missing row is a
LOST WRITE and is a hard failure.
"""
import json
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gws_merge_server as S

WORK = os.path.join(HERE, "work-t2")
ENV = None


def git(*a, cwd=None, **kw):
    return subprocess.run(("git",) + a, cwd=cwd, env=ENV, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout


def setup(n):
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    srv = os.path.join(WORK, "srv.git")
    git("init", "-q", "--bare", srv)
    dev = os.path.join(WORK, "dev")
    git("init", "-q", dev)
    base = ("| id     | item | qty |\n| ------ | ---- | --: |\n"
            "| r_0000 | seed |   1 |\n\ngrand := sum(qty)\n")
    open(os.path.join(dev, "b.tbl"), "w").write(base)
    git("add", "-A", cwd=dev); git("commit", "-qm", "base", cwd=dev)
    git("branch", "-M", "main", cwd=dev)
    git("push", "-q", srv, "main", cwd=dev)
    # one topic branch per worker, each adding a distinct row
    for i in range(n):
        git("checkout", "-q", "-b", f"w{i}", "main", cwd=dev)
        txt = base.replace("| r_0000 | seed |   1 |\n",
                           f"| r_0000 | seed |   1 |\n| r_{i+1:04d} | item{i} | {i+1:3d} |\n")
        open(os.path.join(dev, "b.tbl"), "w").write(txt)
        git("commit", "-qam", f"w{i}", cwd=dev)
        git("push", "-q", srv, f"w{i}", cwd=dev)
    git("checkout", "-q", "main", cwd=dev)
    return srv


QUEUE = os.environ.get("W5_QUEUE") == "1"


def worker(args):
    srv, i, barrier_file = args
    # spin until the start file exists, so all workers really do collide
    while not os.path.exists(barrier_file):
        pass
    t0 = time.perf_counter()
    r = S.merge(srv, "refs/heads/main", f"refs/heads/w{i}", message=f"merge w{i}",
                queue=QUEUE)
    r["wall"] = time.perf_counter() - t0
    r["worker"] = i
    return r


def run(n):
    global ENV
    srv = setup(n)
    barrier = os.path.join(WORK, "GO")
    t0 = time.perf_counter()
    with mp.Pool(n) as pool:
        async_res = pool.map_async(worker, [(srv, i, barrier) for i in range(n)])
        time.sleep(0.35)          # let every process reach the spin loop
        open(barrier, "w").close()
        res = async_res.get(timeout=600)
    elapsed = time.perf_counter() - t0 - 0.35

    tip = subprocess.run(["git", "--git-dir", srv, "rev-parse", "main"],
                         capture_output=True, text=True).stdout.strip()
    txt = subprocess.run(["git", "--git-dir", srv, "cat-file", "-p", "main:b.tbl"],
                         capture_output=True, text=True).stdout
    ids = {l.split("|")[1].strip() for l in txt.splitlines() if l.strip().startswith("|")}
    want = {f"r_{i+1:04d}" for i in range(n)} | {"r_0000"}
    lost = sorted(want - ids)
    # every worker commit reachable?
    unreach = []
    for i in range(n):
        rc = subprocess.run(["git", "--git-dir", srv, "merge-base", "--is-ancestor",
                             f"refs/heads/w{i}", "main"]).returncode
        if rc != 0:
            unreach.append(f"w{i}")
    att = [r.get("attempts", 0) for r in res]
    statuses = {}
    for r in res:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
    gc = [r.get("git_calls", 0) for r in res]
    fsck = subprocess.run(["git", "--git-dir", srv, "fsck", "--strict"],
                          capture_output=True, text=True)
    return dict(n=n, elapsed=round(elapsed, 3),
                throughput=round(n / elapsed, 1),
                statuses=statuses,
                attempts_min=min(att), attempts_max=max(att),
                attempts_mean=round(sum(att) / len(att), 2),
                attempts_total=sum(att),
                git_calls_total=sum(gc),
                rows_expected=len(want), rows_found=len(ids & want),
                LOST_WRITES=lost, unreachable=unreach,
                p50_wall=round(sorted(r["wall"] for r in res)[len(res)//2], 3),
                max_wall=round(max(r["wall"] for r in res), 3),
                fsck_rc=fsck.returncode, fsck_out=fsck.stderr.strip()[:300])


if __name__ == "__main__":
    ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t",
               GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t", HOME="/nonexistent",
               GIT_CONFIG_GLOBAL="/dev/null")
    levels = [int(x) for x in sys.argv[1:]] or [2, 8, 32, 64]
    print(f"MODE={'QUEUED (flock per ref)' if os.environ.get('W5_QUEUE')=='1' else 'BARE CAS RETRY'}")
    print(f"cpus={mp.cpu_count()}  git={subprocess.run(['git','--version'],capture_output=True,text=True).stdout.strip()}")
    print()
    hdr = f"{'N':>4} {'elapsed':>8} {'merges/s':>9} {'att/mean':>9} {'att/max':>8} {'att/tot':>8} {'p50 s':>7} {'max s':>7} {'lost':>5} {'fsck':>5}"
    print(hdr); print("-" * len(hdr))
    out = []
    for n in levels:
        r = run(n)
        out.append(r)
        print(f"{r['n']:>4} {r['elapsed']:>8.3f} {r['throughput']:>9.1f} "
              f"{r['attempts_mean']:>9.2f} {r['attempts_max']:>8} {r['attempts_total']:>8} "
              f"{r['p50_wall']:>7.3f} {r['max_wall']:>7.3f} "
              f"{len(r['LOST_WRITES']):>5} {'ok' if r['fsck_rc']==0 else 'FAIL':>5}")
    print()
    for r in out:
        print(json.dumps(r, sort_keys=True))
    bad = [r for r in out if r["LOST_WRITES"] or r["unreachable"] or r["fsck_rc"]]
    print()
    print("VERDICT:", "ALL CONVERGED, ZERO LOSS" if not bad else f"FAILURES: {bad}")

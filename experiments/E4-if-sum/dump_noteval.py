#!/usr/bin/env python3
"""Dump EVERY expression E1 classified NOTEVAL, not the 40-sample cap.

E1 counts how many corpus cells translate to .mdtbl's surface and then fall
outside SPEC 4.2. To decide what grammar those cells actually need, the
expressions themselves are required -- and E1 keeps only 40. This re-runs E1's
own pipeline with the cap lifted, so the grammar is designed against the real
distribution rather than against whichever 40 happened to be first.

e1.py is imported, never edited: it is the pinned harness that produced the
published figures.
"""
import sys, os, json, collections

E1 = os.path.dirname(os.path.abspath(__file__)) + "/../E1-differential"
sys.path.insert(0, E1)
os.chdir(E1)                      # e1.py resolves corpora relative to itself
import e1

# Lift the cap for NOTEVAL only. Every other sample list keeps E1's behaviour,
# so nothing about the published run changes shape.
_orig = e1.samp


def samp(k, rec, cap=40):
    _orig(k, rec, cap=10**7 if k == "NOTEVAL" else cap)


e1.samp = samp

if __name__ == "__main__":
    out = sys.argv[-1]
    e1.main(sys.argv[1:-1], None, out)
    d = json.load(open(out))
    n = d["samples"].get("NOTEVAL", [])
    print(f"\nNOTEVAL expressions captured: {len(n)}", file=sys.stderr)
    print(f"counter says NOTEVAL = {d['counts'].get('NOTEVAL')}", file=sys.stderr)

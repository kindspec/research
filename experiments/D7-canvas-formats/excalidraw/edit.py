#!/usr/bin/env python3
"""Faithfully simulate Excalidraw edits on a real .excalidraw file.

Excalidraw's mutateElement (packages/element/src/mutateElement.ts) does, for
elements that actually changed:
    element.version      = element.version + 1
    element.versionNonce = randomInteger()
    element.updated      = getUpdatedTimestamp()
and nothing at all for elements that did not change (`if (!didChange) return`).
Serialization is JSON.stringify(data, null, 2)  (data/json.ts serializeAsJSON),
which Python's json.dumps(indent=2) reproduces byte-for-byte on these files.
"""
import json, random, sys, copy

NOW = 1756000000000


def load(p):
    return json.loads(open(p).read())


def dump(d, p):
    open(p, "w").write(json.dumps(d, indent=2))


def bump(el, seedval):
    el["version"] = el.get("version", 1) + 1
    el["versionNonce"] = random.Random(seedval).randint(0, 2**31 - 1)
    el["updated"] = NOW


def move(d, idx, dx, dy, seedval=1):
    el = d["elements"][idx]
    el["x"] += dx
    el["y"] += dy
    bump(el, seedval)
    return el["id"]


def add_rect(d, x, y, seedval=99):
    r = random.Random(seedval)
    el = {
        "type": "rectangle", "version": 1,
        "versionNonce": r.randint(0, 2**31 - 1), "isDeleted": False,
        "id": "NEWSHAPE0000000000001", "fillStyle": "solid", "strokeWidth": 2,
        "strokeStyle": "solid", "roughness": 1, "opacity": 100, "angle": 0,
        "x": x, "y": y, "strokeColor": "#000000",
        "backgroundColor": "#ced4da", "width": 100, "height": 60,
        "seed": r.randint(0, 2**31 - 1), "groupIds": [], "roundness": None,
        "boundElements": [], "updated": NOW, "link": None, "locked": False,
    }
    d["elements"].append(el)
    return el


def relayout(d, seedval=7):
    """What an auto-layout tool that PERSISTS coordinates does: every element
    gets a new position when the graph changes."""
    r = random.Random(seedval)
    for i, el in enumerate(d["elements"]):
        el["x"] = round(el["x"] + r.uniform(-40, 40), 4)
        el["y"] = round(el["y"] + r.uniform(-40, 40), 4)
        bump(el, seedval * 1000 + i)


if __name__ == "__main__":
    cmd = sys.argv[1]
    src, dst = sys.argv[2], sys.argv[3]
    d = load(src)
    if cmd == "move":
        move(d, int(sys.argv[4]), 37, -21, int(sys.argv[5]))
    elif cmd == "add":
        add_rect(d, 900, 900)
    elif cmd == "addrelayout":
        add_rect(d, 900, 900)
        relayout(d)
    elif cmd == "relayout":
        relayout(d)
    dump(d, dst)

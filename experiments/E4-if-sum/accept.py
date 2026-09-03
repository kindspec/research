#!/usr/bin/env python3
"""Does the REAL parser accept what classify.py predicted it would?

classify.py used regexes to predict 6,640 "cheap" IF cells. A regex prediction
about a grammar is a guess. This feeds every one of the 21,165 NOTEVAL
expressions through rowspec's actual §4.2 parser, after the one mechanical
rewrite Excel->rowspec syntax needs, and counts what it really accepts.
"""
import sys, json, re, collections

sys.path.insert(0, '/home/cam/repos_kindspec/rowspec/reference')
import rowspec.table as RT

C = collections.Counter()
S = collections.defaultdict(list)


def to_rowspec(e):
    """Excel surface -> §4.2 surface. Deliberately minimal and mechanical."""
    # Function names are case-insensitive in Excel and lowercase in §4.2.
    e = re.sub(r"(?<![A-Za-z0-9_.])IF\s*\(", "if(", e)
    return e


def main(path):
    recs = json.load(open(path))["samples"]["NOTEVAL"]
    C["total"] = len(recs)
    for r in recs:
        e = (r.get("expr") or "").strip()
        if not e:
            C["empty"] += 1
            continue
        has_if = bool(re.search(r"(?<![A-Za-z0-9_.])IF\s*\(", e))
        try:
            RT._ast(to_rowspec(e), "x")
            C["ACCEPTED"] += 1
            C["accepted.with-if" if has_if else "accepted.without-if"] += 1
            S["ACCEPTED"].append(e[:100])
        except RT.Malformed as ex:
            C["refused"] += 1
            msg = str(ex)
            # bucket by the reason, which is what tells us what is still missing
            for tag, pat in (
                ("string-branch-or-arg", "not part of an expression"),
                ("unknown-function", "unknown function"),
                ("refusal-24-ident-rhs", "§9.24"),
                ("comparison-outside-if", "not an operator of an expression"),
                ("if-shape", "if()"),
                ("ordering-vs-text", "compares numbers, never text"),
                ("second-spelling", "not in §4.2; equality"),
            ):
                if pat in msg:
                    C["refused." + tag] += 1
                    S["refused." + tag].append(e[:100])
                    break
            else:
                C["refused.other"] += 1
                S["refused.other"].append(e[:100])
        except Exception as ex:
            C["crash." + type(ex).__name__] += 1
            S["crash"].append(e[:100])

    for k, v in sorted(C.items(), key=lambda kv: -kv[1]):
        print(f"{v:8d}  {k}")
    json.dump({"counts": dict(C), "samples": {k: v[:15] for k, v in S.items()}},
              open("out/accept.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1])

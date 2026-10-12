#!/usr/bin/env python3
"""
analyze_properties.py - Class Property Report (deterministic)

Input : JSON array from get_class_property_descriptions (stdin or --file PATH).
        Per item only these keys are used: symbolic_name, display_name,
        data_type, cardinality, is_searchable, is_system_owned, is_hidden.
Output: the FINAL markdown report on stdout, to be shown verbatim.

Exit codes
  0  success
  2  bad input (invalid JSON, not an array, missing key, non-boolean flag,
     blank/duplicate symbolic_name). Offending items are listed on stderr.
  4  --expected N does not match the number of properties received
"""
import argparse
import json
import re
import sys

KEYS = ("symbolic_name", "display_name", "data_type", "cardinality")
FLAGS = ("is_searchable", "is_system_owned", "is_hidden")
SYM_OK = re.compile(r"^[A-Za-z_][A-Za-z0-9_.$-]*$")


def die(code, lines):
    print("ERROR: " + "\n".join(lines[:20]), file=sys.stderr)
    if len(lines) > 20:
        print(f"... and {len(lines) - 20} more", file=sys.stderr)
    sys.exit(code)


def load(args):
    raw = open(args.file, encoding="utf-8").read() if args.file else sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        die(2, [f"invalid JSON ({e}) - input was not passed through intact"])
    if not isinstance(data, list) or not data:
        die(2, ["input must be a non-empty JSON array"])
    problems, seen = [], set()
    for i, p in enumerate(data):
        if not isinstance(p, dict):
            problems.append(f"item {i}: not an object")
            continue
        for k in KEYS:
            if not isinstance(p.get(k), str) or not p[k].strip():
                problems.append(f"item {i} ({p.get('symbolic_name')!r}): '{k}' missing or blank")
        for k in FLAGS:
            if not isinstance(p.get(k), bool):
                problems.append(f"item {i} ({p.get('symbolic_name')!r}): '{k}' must be true/false, got {p.get(k)!r}")
        sym = p.get("symbolic_name")
        if isinstance(sym, str):
            if not SYM_OK.match(sym):
                problems.append(f"item {i}: suspicious symbolic_name {sym!r}")
            if sym in seen:
                problems.append(f"item {i}: duplicate symbolic_name {sym!r}")
            seen.add(sym)
    if problems:
        die(2, problems)
    return data


def esc(s):
    return str(s).replace("|", "\\|")


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--expected", type=int, help="property count reported independently by the source")
    ap.add_argument("--class", dest="cls", default="", help="resolved class symbolic name (shown in the heading)")
    args = ap.parse_args()

    props = load(args)                     # API order is preserved
    n = len(props)
    if args.expected is not None and args.expected != n:
        die(4, [f"received {n} properties but source reported {args.expected}"])

    system = [p for p in props if p["is_system_owned"]]
    custom = [p for p in props if not p["is_system_owned"]]
    search = [p for p in props if p["is_searchable"]]
    nosearch = [p for p in props if not p["is_searchable"]]
    hidden = [p for p in props if p["is_hidden"]]
    visible = [p for p in props if not p["is_hidden"]]
    assert len(system) + len(custom) == len(search) + len(nosearch) == len(hidden) + len(visible) == n

    owned = lambda p: "system" if p["is_system_owned"] else "custom"
    srch = lambda p: "yes" if p["is_searchable"] else "no"
    hid = lambda p: "yes" if p["is_hidden"] else "no"

    src = (f"API reported: {args.expected}" if args.expected is not None
           else "API count not independently available")
    SP = ("&nbsp;", "&nbsp;")  # spacer row between the three pairs
    out = ["## Class Property Report" + (f": {args.cls}" if args.cls else ""), "",
           "### Summary", ""]
    out += ["| Metric | Count |", "|:---|---:|",
            "| **Ownership** | |",
            f"| Custom / business | {len(custom)} |",
            f"| System-owned | {len(system)} |",
            f"| {SP[0]} | {SP[1]} |",
            "| **Searchability** | |",
            f"| Searchable | {len(search)} |",
            f"| Not searchable | {len(nosearch)} |",
            f"| {SP[0]} | {SP[1]} |",
            "| **Visibility** | |",
            f"| Hidden | {len(hidden)} |",
            f"| Visible | {len(visible)} |", ""]

    # One list: custom first, then system; API order kept within each group.
    ordered = custom + system
    out += ["### All properties (custom first, then system)", ""]
    out += table(["#", "Symbolic Name", "Display Name", "Data Type", "Cardinality", "Owned", "Searchable", "Hidden"],
                 [(i, p["symbolic_name"], p["display_name"], p["data_type"], p["cardinality"],
                   owned(p), srch(p), hid(p)) for i, p in enumerate(ordered, 1)])
    out += ["", f"### Total: {n} properties", "",
            f"\n*Counts computed from {n} properties received ({src}).*"]
    print("\n".join(out))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
group_classes.py - Document Class Inventory (deterministic)

Input : JSON array from list_all_classes (stdin, or --file PATH).
        Only `symbolic_name` and `display_name` are used; other keys
        (e.g. descriptive_text) are ignored.
Output: the FINAL markdown to present, verbatim (stdout).
        Diagnostics go to stderr.

Exit codes
  0  success - markdown on stdout
  2  bad input (invalid JSON, not an array, missing/blank fields,
     duplicate symbolic_name, suspicious characters)
  3  unclassified classes found (rules need updating) - nothing is guessed
  4  --expected N does not match the number of classes received
"""
import argparse
import json
import re
import sys

# --- Classification rules (edit here, nowhere else) -------------------------
# Matching is on symbolic_name, case-insensitive, evaluated top to bottom.
HR_RE = re.compile(r"^HR(?![a-z])")                 # case-sensitive: HRDocument, HR_Foo; not "HRef"/"Hrx"
CONTRACT_RE = re.compile(r"^Contract", re.I)
TAX_PREFIXES = (
    "Aangifte", "Aanslag", "BTW", "Belasting", "Bezwaar", "Beroep",
    "Correctie", "Douane", "Fiscaal", "Invoer", "Jaarrekening", "Kwartaal",
    "Loonbelasting", "Motorrijtuigen", "Origine", "Transit", "Uitvoer",
    "Vereenvoudigde", "Voorlopig", "Voortaxatie", "Winst",
)
# System classes are an explicit list: an unknown class is flagged, not
# silently filed under System.
SYS_NAMES = {
    "CodeModule", "Document", "Email", "EntryTemplate", "FormData",
    "FormPolicy", "FormTemplate", "MsResource", "PreferencesDocument",
    "RecordsTemplate", "ScenarioDefinition", "Simulation", "StoredSearch",
    "WebContentTemplate", "WebFormTemplate", "WorkflowDefinition",
    "XMLPropertyMappingScript",
}
# ----------------------------------------------------------------------------

SECTIONS = [  # key, markdown heading
    ("hr", "HR"),
    ("contracts", "Contracts / Legal"),
    ("tax", "Tax Administration"),
    ("sys", "System / Technical"),
]
SYM_OK = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def die(code, msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def classify(sym):
    if HR_RE.match(sym):
        return "hr"
    if CONTRACT_RE.match(sym):
        return "contracts"
    if sym.lower().startswith(tuple(p.lower() for p in TAX_PREFIXES)):
        return "tax"
    if sym in SYS_NAMES:
        return "sys"
    return "unclassified"


def load(args):
    raw = open(args.file, encoding="utf-8").read() if args.file else sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        die(2, f"invalid JSON ({e}) - input was not passed through intact")
    if not isinstance(data, list) or not data:
        die(2, "input must be a non-empty JSON array")
    seen, rows = set(), []
    for i, c in enumerate(data):
        sym = c.get("symbolic_name") if isinstance(c, dict) else None
        dsp = c.get("display_name") if isinstance(c, dict) else None
        if not sym or not dsp or not str(sym).strip() or not str(dsp).strip():
            die(2, f"item {i}: symbolic_name/display_name missing or blank")
        if not SYM_OK.match(sym):
            die(2, f"item {i}: suspicious symbolic_name {sym!r} (transcription damage?)")
        if sym in seen:
            die(2, f"duplicate symbolic_name {sym!r}")
        seen.add(sym)
        rows.append((dsp.strip(), sym))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="read JSON from this path instead of stdin")
    ap.add_argument("--expected", type=int,
                    help="class count reported independently by the source")
    args = ap.parse_args()

    rows = load(args)
    total = len(rows)
    if args.expected is not None and args.expected != total:
        die(4, f"received {total} classes but source reported {args.expected}")

    groups = {k: [] for k, _ in SECTIONS}
    groups["unclassified"] = []
    for dsp, sym in rows:
        groups[classify(sym)].append((dsp, sym))

    if groups["unclassified"]:
        names = ", ".join(s for _, s in groups["unclassified"])
        die(3, f"{len(groups['unclassified'])} unclassified class(es): {names}. "
               "Add a rule in scripts/group_classes.py; do not guess.")

    counts = {k: len(groups[k]) for k, _ in SECTIONS}
    assert sum(counts.values()) == total  # holds by construction; guard against edits

    out = ["## Document Class Inventory", ""]
    for key, title in SECTIONS:
        out += [f"### {title} ({counts[key]})", "",
                "| Display Name | Symbolic Name |", "|---|---|"]
        for dsp, sym in sorted(groups[key], key=lambda r: (r[0].lower(), r[1])):
            out.append(f"| {dsp.replace('|', chr(92) + '|')} | {sym} |")
        out.append("")
    src = (f"API reported: {args.expected}" if args.expected is not None
           else "API count not independently available")
    out.append(
        f"✅ Verification: {counts['hr']} (HR) + {counts['contracts']} (Contracts / Legal) + "
        f"{counts['tax']} (Tax Administration) + {counts['sys']} (System / Technical) "
        f"= **{total} total** "
        f"\n\n*({src}; {total} classes received)*")
    print("\n".join(out))


if __name__ == "__main__":
    main()

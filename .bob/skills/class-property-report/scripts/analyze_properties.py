#!/usr/bin/env python3
"""
analyze_properties.py — Class Property Report
Usage: python3 analyze_properties.py < all_props.json
       OR: echo '<json>' | python3 analyze_properties.py

Reads a single JSON array from stdin — the raw output of get_class_property_descriptions.
Each object must have: symbolic_name, display_name, data_type, cardinality,
is_searchable, is_system_owned, is_hidden.

Computes all counts using len() on filtered sublists, verifies all splits sum to
the total, then prints a structured report for Bob to present to the user.
"""

import json
import sys


def main():
    raw = sys.stdin.read()
    try:
        all_props = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON on stdin — {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(all_props, list):
        print("ERROR: stdin must contain a JSON array.", file=sys.stderr)
        sys.exit(1)

    total = len(all_props)

    # --- Split: system vs custom ---
    system_props = [p for p in all_props if p.get("is_system_owned") is True]
    custom_props  = [p for p in all_props if p.get("is_system_owned") is False]
    assert len(system_props) + len(custom_props) == total, \
        f"SPLIT ERROR system+custom: {len(system_props)}+{len(custom_props)} != {total}"

    # --- Split: searchable flag vs not ---
    searchable_props     = [p for p in all_props if p.get("is_searchable") is True]
    not_searchable_props = [p for p in all_props if p.get("is_searchable") is False]
    assert len(searchable_props) + len(not_searchable_props) == total, \
        f"SPLIT ERROR searchable flag: {len(searchable_props)}+{len(not_searchable_props)} != {total}"

    # --- Split: hidden vs visible ---
    hidden  = [p for p in all_props if p.get("is_hidden") is True]
    visible = [p for p in all_props if p.get("is_hidden") is False]
    assert len(hidden) + len(visible) == total, \
        f"SPLIT ERROR hidden: {len(hidden)}+{len(visible)} != {total}"

    # --- Emit verified counts ---
    print("=== VERIFIED COUNTS ===")
    print(f"total={total}")
    print(f"system_owned={len(system_props)}")
    print(f"custom={len(custom_props)}")
    print(f"system_plus_custom={len(system_props) + len(custom_props)}")
    print(f"searchable={len(searchable_props)}")
    print(f"not_searchable={len(not_searchable_props)}")
    print(f"searchable_plus_not={len(searchable_props) + len(not_searchable_props)}")
    print(f"hidden={len(hidden)}")
    print(f"visible={len(visible)}")
    print(f"hidden_plus_visible={len(hidden) + len(visible)}")

    # --- Flat numbered list: ALL properties ---
    print("\n=== FLAT LIST ===")
    for i, p in enumerate(all_props, start=1):
        sym     = p.get("symbolic_name", "")
        display = p.get("display_name", "")
        dtype   = p.get("data_type", "")
        card    = p.get("cardinality", "")
        owned   = "system" if p.get("is_system_owned") else "custom"
        srch    = "searchable" if p.get("is_searchable") else "not_searchable"
        vis     = "hidden" if p.get("is_hidden") else "visible"
        print(f"{i}|{sym}|{display}|{dtype}|{card}|{owned}|{srch}|{vis}")

    print(f"\n=== TOTAL: {total} ===")

    # --- System properties list ---
    print(f"\n=== SYSTEM PROPERTIES ({len(system_props)}) ===")
    for i, p in enumerate(system_props, start=1):
        sym     = p.get("symbolic_name", "")
        display = p.get("display_name", "")
        dtype   = p.get("data_type", "")
        srch    = "searchable" if p.get("is_searchable") else "not_searchable"
        vis     = "hidden" if p.get("is_hidden") else "visible"
        print(f"{i}|{sym}|{display}|{dtype}|{srch}|{vis}")

    # --- Custom properties list ---
    print(f"\n=== CUSTOM PROPERTIES ({len(custom_props)}) ===")
    for i, p in enumerate(custom_props, start=1):
        sym     = p.get("symbolic_name", "")
        display = p.get("display_name", "")
        dtype   = p.get("data_type", "")
        srch    = "searchable" if p.get("is_searchable") else "not_searchable"
        vis     = "hidden" if p.get("is_hidden") else "visible"
        print(f"{i}|{sym}|{display}|{dtype}|{srch}|{vis}")

    # --- Searchable properties list ---
    print(f"\n=== SEARCHABLE PROPERTIES ({len(searchable_props)}) ===")
    for i, p in enumerate(searchable_props, start=1):
        sym     = p.get("symbolic_name", "")
        display = p.get("display_name", "")
        dtype   = p.get("data_type", "")
        card    = p.get("cardinality", "")
        owned   = "system" if p.get("is_system_owned") else "custom"
        vis     = "hidden" if p.get("is_hidden") else "visible"
        print(f"{i}|{sym}|{display}|{dtype}|{card}|{owned}|{vis}")


if __name__ == "__main__":
    main()

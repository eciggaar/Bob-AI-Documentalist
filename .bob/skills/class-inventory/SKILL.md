---
name: class-inventory
description: Use when the user wants a complete inventory of document classes in the IBM Content Services repository, grouped by domain (HR, Contracts/Legal, Tax Administration, System/Technical) with verified counts. Activate on "document class inventory", "list all classes", "what classes do we have", "class overview".
---

# Document Class Inventory

The script does all grouping, counting, sorting and formatting. You only move data
into it and relay its output. You never count, sort, group or do arithmetic.

## Step 1 - Fetch
Call `list_all_classes` (`mcp__property-extraction-cs-mcp-server__list_all_classes`)
with `root_class: "Document"`. If the result is not a complete JSON array (error,
cut-off, or the tool says more pages exist), report that and stop.
If the result reports its own total or count, remember it as `EXPECTED`.

## Step 2 - Run the script
If the tool result was saved to a file, use `--file <path>`. Otherwise:

- **macOS / Linux:** Pass the JSON through a **quoted heredoc** (never `echo '...'` - apostrophes such as "personenauto's" break the shell, and `echo` can alter backslashes):
  ```
  .venv/bin/python .bob/skills/class-inventory/scripts/group_classes.py [--expected EXPECTED] <<'JSON'
  <JSON array>
  JSON
  ```
- **Windows:** Save the JSON to a temporary file (e.g. `tmp_classes.json`) and run:
  ```
  .venv\Scripts\python.exe .bob\skills\class-inventory\scripts\group_classes.py --file tmp_classes.json [--expected EXPECTED]
  ```

- Keep only `symbolic_name` and `display_name` for each item (drop `descriptive_text`).
  Copy values exactly; do not reorder, shorten, fix spelling or skip items.
- Add `--expected EXPECTED` only if Step 1 produced one. Do not invent it by counting.

## Step 3 - Check the exit code
- `0`: continue.
- `2`: bad or damaged input. Re-run Step 1 and 2 once; if it fails again, report the error.
- `3`: unclassified classes. Show the script's error text to the user and stop.
  They need a new rule in `scripts/group_classes.py`. Never place them yourself.
- `4`: count mismatch. Report it and stop.
- Any other failure or missing script: report it and stop. Do not count manually.

## Step 4 - Present
Output the script's stdout **verbatim** (heading, four tables, verification line).
No added tables, summaries, re-sorting or recalculated numbers. Any comment goes
after the verbatim block and may not contain counts of your own.

## Maintenance
Rules (prefixes, known system classes) live only in `scripts/group_classes.py`.

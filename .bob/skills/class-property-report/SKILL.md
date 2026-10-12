---
name: class-property-report
description: Use when the user wants to see all properties of a document class - their data types, searchability, and which are system-owned vs custom business properties - with verified counts.
---

# Class Property Report

Division of labour: MCP tools supply the data, the script validates, counts, numbers and
formats it. You never count, number, sort or do arithmetic, and you never retype tables.

## Step 1 - Resolve the class (never guess)
If the user gave no class name, ask for it.
Call `determine_class` (`mcp__core-cs-mcp-server__determine_class`) with `root_class`
`"Document"` (or the root the user named; call `list_root_classes` only if you need to
check that root exists) and `keywords` = up to 3 words from the user's class name.
- Use a result only if its `display_name` or `symbolic_name` equals the user's input
  (case-insensitive), or it is the only result.
- Otherwise do not pick one. Ask the user to choose from the top 3 candidates.
- Remember the chosen `symbolic_name` as `CLASS`.

## Step 2 - Retrieve the properties
Call `get_class_property_descriptions` (`mcp__core-cs-mcp-server__get_class_property_descriptions`)
with `class_symbolic_name: CLASS`. If the result is not a complete JSON array (error,
cut-off, more pages exist), report that and stop. If the result reports its own total,
remember it as `EXPECTED`. State no numbers yet.

## Step 3 - Run the script
If the tool result was saved to a file, use `--file <path>`. Otherwise:

- **macOS / Linux:** Pass the JSON through a **quoted heredoc** (never `echo '...'`: apostrophes and backslashes break it):
  ```
  .venv/bin/python .bob/skills/class-property-report/scripts/analyze_properties.py --class CLASS [--expected EXPECTED] <<'JSON'
  [ ... ]
  JSON
  ```
- **Windows:** Save the JSON to a temporary file (e.g. `tmp_props.json`) and run:
  ```
  .venv\Scripts\python.exe .bob\skills\class-property-report\scripts\analyze_properties.py --class CLASS --file tmp_props.json [--expected EXPECTED]
  ```

- Include per property only: `symbolic_name`, `display_name`, `data_type`, `cardinality`,
  `is_searchable`, `is_system_owned`, `is_hidden`. Keep boolean flags as true/false
  (not strings). Copy values exactly, in the order received; do not skip or fix anything.
- Add `--expected` only when Step 2 provided a count. Never derive it by counting.

## Step 4 - Check the exit code
- `0`: continue.
- `2`: input problem (the error names the items). Re-run Steps 2-3 once; if it fails
  again, report the error.
- `4`: count mismatch. Report and stop.
- Script missing or any other failure: report and stop. Never count manually.

## Step 5 - Present
Output the script's stdout **verbatim**: a summary table (Ownership, Searchability and
Visibility, separated by spacer rows), then one numbered list of all properties (custom
first, then system), then the total as the last heading. Do not re-sort, re-number,
re-format or restate counts. Anything you add goes after it and contains no numbers of
your own.

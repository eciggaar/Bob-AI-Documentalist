---
name: class-property-report
description: Use when the user wants to see all properties of a document class — their data types, searchability, and which are system-owned vs custom business properties.
---

# Class Property Report

Follow these steps exactly and in order. Do not present any counts or property tables until the
Python script has run and its output has been read.

## Step 1 — Resolve the class name

If the user has not provided a class name, ask for it using `ask_followup_question`.

Call `list_root_classes` (MCP tool `mcp__core-cs-mcp-server__list_root_classes`) to confirm
root classes are available, then call `determine_class` with:
- `root_class`: `"Document"` (or whatever root class the user specifies)
- `keywords`: up to 3 words from the user's class name

Use the top-scored result's `symbolic_name` as the class identifier for the next step.

## Step 2 — Retrieve all properties

Call `get_class_property_descriptions` (MCP tool
`mcp__core-cs-mcp-server__get_class_property_descriptions`) with the `class_symbolic_name`
resolved in Step 1.

Do NOT count, summarise, or categorise anything yet. Do NOT state any numbers.
Proceed immediately to Step 3.

## Step 3 — Run the analysis script

Pipe the raw JSON array from Step 2 directly into the analysis script via stdin using `execute_command`:

```
echo '<raw JSON array>' | python3 .bob/skills/class-property-report/scripts/analyze_properties.py
```

Replace `<raw JSON array>` with the JSON returned by `get_class_property_descriptions`.
Do NOT write it to a file first.

If the command fails, report the error and stop.

## Step 4 — Read and validate the script output

The script prints four sections:

### `=== VERIFIED COUNTS ===`
Key=value lines, including:
- `total=N`
- `system_owned=A`, `custom=B`, `system_plus_custom=C` → verify A + B = C = total
- `searchable=D`, `not_searchable=E`, `searchable_plus_not=F` → verify D + E = F = total
- `hidden=G`, `visible=H`, `hidden_plus_visible=I` → verify G + H = I = total

If any verification equation does not hold, report the discrepancy and stop.

### `=== FLAT LIST ===`
Pipe-delimited rows: `N|symbolic_name|display_name|data_type|cardinality|owned|searchable|visibility`

### `=== SYSTEM PROPERTIES (A) ===` and `=== CUSTOM PROPERTIES (B) ===`
Sub-lists in the same pipe-delimited format.

### `=== SEARCHABLE PROPERTIES (D) ===`
Flat numbered list of searchable properties derived from the `is_searchable` flag.

### `=== TOTAL: N ===`
Authoritative total line. Use this value — not any other number — as the total for all output.

## Step 5 — Present results to the user

Only after the script has completed successfully, present the following in order:

### Summary table

| Metric | Count | Equation check |
|---|---|---|
| **Total properties** | N | — |
| System-owned | A | A + B = N ✓ |
| Custom / business | B | |
| Searchable | D | D + E = N ✓ |
| Not searchable | E | |
| Hidden | G | G + H = N ✓ |
| Visible | H | |

All values come from the `=== VERIFIED COUNTS ===` section. Do not write any number that is not
present in the script output.

### Complete flat numbered list — ALL properties

Use the `=== FLAT LIST ===` rows. Present as a numbered markdown table:

| # | Symbolic Name | Display Name | Data Type | Cardinality | Owned | Searchable | Hidden |
|---|---|---|---|---|---|---|---|

The last row number must equal `total`. State the total after the table: "Total: N properties."

### System-owned properties

Use the `=== SYSTEM PROPERTIES ===` rows. Present as a numbered markdown table. State the count
after: "Total system-owned: A properties."

### Custom / business properties

Use the `=== CUSTOM PROPERTIES ===` rows. Present as a numbered markdown table. State the count
after: "Total custom: B properties."

Verify explicitly: A (system) + B (custom) = N (total). State this equation in the response.

### Searchable properties

Use the `=== SEARCHABLE PROPERTIES ===` rows. Present as a numbered markdown table. State the
count after: "Total searchable: D properties."

## Rules that must never be broken

- Never state a count that is not taken directly from the script's `=== VERIFIED COUNTS ===`
  output or verified by the equation checks embedded in that output.
- Never present a grouped or categorised view before the flat numbered list.
- Never derive a total by summing category sub-counts — always use `total=N` from the script.
- If the script is not available or fails to run, do not fall back to manual counting. Report the
  failure and ask the user to check the skill directory.


## Supporting files in this skill directory:
- `scripts/analyze_properties.py`

Use the read_file tool with paths relative to: .bob/skills/class-property-report/

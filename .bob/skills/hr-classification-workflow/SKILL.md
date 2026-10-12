---
name: hr-classification-workflow
description: >-
  Audit and fix HR document classification in a FileNet namespace (/BOB_LAB/<LASTNAME>/).
  Use for: classification audit, missing or invalid EmployeeID, class mismatch or misclassified
  documents, triage of a document filed under the base Document class (what is it, who does it
  belong to), reclassifying or fixing HR documents, and a classification health report.
---

# HR Classification Workflow

Four independent phases. Pick the one that matches the request; each phase gathers its own data
and does not depend on earlier phases.

| The user wants… | Phase | Changes the repository? |
|---|---|---|
| Find bad EmployeeIDs and/or wrong classes | 1 Audit | No |
| Know what a specific document is and where it belongs | 2 Triage | No |
| Reclassify / fix one or all documents | 3 Fix | **Yes — only after the user confirms** |
| A final health report | 4 Report | No (writes a local file only) |

## Step 0 — Verify the virtual environment

All Python commands in this skill MUST use the project virtual environment.
Before running anything, confirm the virtual environment Python interpreter exists:

- **macOS / Linux:**
  ```
  test -f .venv/bin/python && echo "venv OK" || echo "venv MISSING"
  ```
  If missing: `python3 -m venv .venv`

- **Windows (PowerShell / Command Prompt):**
  ```
  if exist .venv\Scripts\python.exe (echo venv OK) else (echo venv MISSING)
  ```
  If missing: `python -m venv .venv`

Do not proceed until the virtual environment Python is confirmed available.

## Common setup

`LASTNAME` comes from the user's message (`/BOB_LAB/DUPONT/` → `DUPONT`). If unclear, ask.
`PREFIX` is the first 3 characters of `LASTNAME` unless the user says otherwise.

The scan script uses only the Python standard library and never modifies the repository. Run from the **project root**:

- **macOS / Linux:**
  ```
  .venv/bin/python .bob/skills/hr-classification-workflow/scripts/hr_audit.py --user {LASTNAME} [--prefix {PREFIX}] [--insecure]
  ```
- **Windows:**
  ```
  .venv\Scripts\python.exe .bob\skills\hr-classification-workflow\scripts\hr_audit.py --user {LASTNAME} [--prefix {PREFIX}] [--insecure]
  ```

Add `--insecure` only if TLS verification fails on a lab server with a self-signed certificate.
It prints JSON to stdout: `totalDocuments`, `hrDocumentCount`, `classBreakdown`, `propertyIssues`
(HRDocuments with a bad EmployeeID) and `classIssues` (any document in the namespace that is not
an `HRDocument`). If the script fails, show the error and stop; do not estimate numbers.

An EmployeeID is **valid** only if it matches `{PREFIX}` + exactly 3 digits and is not `{PREFIX}000`.
Null, empty, other formats and `{PREFIX}000` are all invalid, with equal severity.

## Phase 1 — Audit

Run the script. Show only what the user asked for:

- EmployeeID issues → table `Document | EmployeeID found | Issue | ID`, then "N HRDocument(s) with missing or invalid EmployeeID." (none: "✅ All HRDocuments have a valid EmployeeID.")
- Class issues → table `Document | Actual class | Expected class | ID`, then "N document(s) with the wrong class." (none: "✅ All documents are HRDocument.")
- Both, or an unspecific "audit" → both tables.

Take every count from the script output.

## Choice-list properties

Some `HRDocument` properties only accept values from a choice list (DocType, Department, JobRole,
Location, JobStatus, EmploymentType, CurrentStatus, DocumentCategory, ClassDocType). The allowed
values are in `references/choice-lists.md`; read it before proposing values. For each such property:

1. Take the value from the document content, as for any property.
2. Pick the **best matching allowed value** and label the match:
   - **Exact** — same value, ignoring case, spaces and punctuation ("Disciplinary Record" → `DisciplinaryRecord`).
   - **Mapped** — different wording, same meaning; give the reason ("Permanent (CDI)", 35 h/week → `Full Time`).
   - **No match** — no allowed value fits; leave the property unset and mark it `needs manual review`. Never force a value.
3. Show the raw text and the chosen value side by side. **Mapped** values always need explicit user
   confirmation (Phase 3 step 3); never apply them silently.

If the repository still rejects a value as "not within the range of permitted values", the list in
`references/choice-lists.md` is out of date: show the error, do not guess another value, and ask the user.

## Phase 2 — Triage (read-only)

1. Get the document ID. If the user gave only a name, call `mcp__core-cs-mcp-server__lookup_documents_by_name`.
2. Call `mcp__property-extraction-cs-mcp-server__property_extraction` for the class, properties and text.
3. Call `mcp__ai-document-insight-cs-mcp-server__document_qa_specific` with: "What type of HR document is this? Who is the employee (name and ID)? Which department? What is the document date?"
4. Present, and change nothing:

```
Document: {name}   Current class: {class}   Recommended class: HRDocument
Proposed values (each with the text it came from):
  EmployeeID: {value}   ← "{quote}"
  Department: {value}   ← "{quote}"
  DocType:    {value}   ← "{quote}"
Confidence: High / Medium / Low (say why if not High)
```

For choice-list properties, show `{allowed value} (Exact|Mapped from "{raw text}")` as described in
*Choice-list properties*. If a value is not in the content, write `not found — needs manual review`.
Never infer it from the file name.

## Phase 3 — Fix (changes the repository)

1. **Select targets.** One document: the one the user named. "All"/"remaining": run the script and take `classIssues` + `propertyIssues`.
2. **Read each target** as in Phase 2 steps 2–3. Call `mcp__core-cs-mcp-server__get_class_property_descriptions` for `HRDocument` once to get the exact property identifiers. A target whose class or EmployeeID cannot be established from its content is marked `⚠️ needs manual review` and left out of the plan.
3. **Show the change plan and ask for confirmation. Make no change before the answer.**

```
## Proposed changes — {LASTNAME}
| # | Document | Class: now → new | EmployeeID: now → new | Department | DocType | Evidence |
|---|---|---|---|---|---|---|
| 1 | … | Document → HRDocument | (none) → DUP004 | … | … | "…quote…" |

Choice-list mappings (need your confirmation):
| # | Document | Property | Text in document | Proposed value | Match | Other allowed values |
|---|---|---|---|---|---|---|
| 1 | … | EmploymentType | "Permanent (CDI)" | Full Time | Mapped | Part Time, Contractor, Intern, Temporary |

Not included (needs manual review): {name — reason}
```

   List every **Mapped** choice-list value in the mappings table (Exact matches go only in the main
   table). Then ask: "Apply these N changes to the repository?" with the options **Apply all**,
   **Apply only some (tell me which)**, **Cancel**. If there are mapped values, the question must say
   that applying confirms them too, and the user can pick a different allowed value instead. Wait for the answer. If the user adjusts a value, show the updated plan and ask again.
4. **Apply only what was approved.** Per document: `mcp__core-cs-mcp-server__update_document_class` (if the class changes) first, then `mcp__core-cs-mcp-server__update_document_properties` with `{identifier, value}` pairs. If one document fails, record the error and continue with the rest.
5. **Verify.** Call `mcp__core-cs-mcp-server__get_document_properties` for each changed document and compare `className` and `EmployeeID` with the approved values.
6. **Report** every processed document:

```
| Document | Previous class | New class | EmployeeID set | Status |
|---|---|---|---|---|
| … | Document | HRDocument | DUP004 | ✅ Fixed and verified |
| … | … | … | … | ❌ Error: {reason} / ⚠️ Needs manual review / ⏭ Not approved |
Fixed: X | Errors: Y | Skipped: Z | Total: N
```

## Phase 4 — Health report (read-only on the repository)

1. Run the script; use `totalDocuments`, `hrDocumentCount`, `classBreakdown`, `classIssues`, `propertyIssues`.
2. Fill in `references/report-template.md`. Resolved issues are those the user tells you were fixed in this session, or that you can see from the audit; otherwise leave "resolved" at 0 rather than guess.
3. Save to `audits/{LASTNAME}_{YYYYMMDD}/classification_health_report.md` (today's date) and tell the user the path. The report stays in the local workspace; it is not uploaded to FileNet.

## Rules

1. Never change a class or property before the user has confirmed the plan shown in Phase 3.
2. Never base a class or property value on the file name; only on the document content, and show the evidence.
3. Set the class before the properties.
4. Every number you state must come from the script output or a tool response.
5. Choice-list properties get only values from `references/choice-lists.md`; mapped values need user confirmation, and if nothing fits the property stays unset.
6. Changing the class (e.g. `Contract` → `HRDocument`) can clear properties that look shared, such as EmployeeID. Always set every planned property after the class change, including values that already existed.

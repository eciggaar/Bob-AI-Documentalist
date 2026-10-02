---
name: hr-classification-workflow
description: >-
  Use when the user wants to audit HR document classification in a FileNet
  namespace (/BOB_LAB/<LASTNAME>/). Covers: finding HRDocuments with missing
  or invalid EmployeeID, detecting class mismatches (e.g. DUP001 documents),
  triaging base Document objects to determine their correct class, reclassifying
  and fixing individual or all misclassified documents, and generating a final
  classification health report. Activate on phrases like "classification audit",
  "missing EmployeeID", "misclassified documents", "reclassify HR document",
  "class mismatch", or "classification health report".
---

# HR Classification Workflow

This skill guides Bob through a complete HR document classification lifecycle
across six phases. Each phase can be invoked independently — you do not need
to run all phases in sequence.

---

## Prerequisites — verify the virtual environment

Before running any Python command, confirm `.venv/bin/python` exists:

```
test -f .venv/bin/python && echo "venv OK" || echo "venv MISSING"
```

If missing:

```
python -m venv .venv && .venv/bin/pip install requests
```

All Python commands below use `.venv/bin/python`. Run from the project root.

---

## Phase 1 — Classification Audit

**Trigger phrases**: "classification audit", "missing EmployeeID", "invalid EmployeeID",
"find documents with wrong EmployeeID", "run a classification audit"

### Steps

**Step 1 — Resolve the namespace**

Extract `LASTNAME` from the user's message (e.g. `DUPONT` from `/BOB_LAB/DUPONT/`).
If not clear, ask: "Which namespace (last name) should I audit? For example: DUPONT."

**Step 2 — Run the audit script**

```
.venv/bin/python .bob/skills/hr-classification-workflow/scripts/audit_hr_documents.py --user {LASTNAME}
```

Read the stdout carefully. The script always collects both:
- `property_issues` — HRDocuments with null, empty, or non-matching EmployeeID
  (including `{PREFIX}000` which is also invalid)
- `class_issues` — docs with prefix `{LASTNAME[:3]}` that are not `HRDocument`
- A saved file: `audit_results_{lastname}.json`

**Step 3 — Present only what the user asked for**

**Answer the user's question exactly — do not surface information they did not ask for.**

- If the user asked about **EmployeeID issues only**, show only the property issues table:

  | Document Name | EmployeeID found | Issue | Document ID |
  |---|---|---|---|
  | … | … | … | … |

  State: `N HRDocument(s) with missing or invalid EmployeeID.`
  If none: "✅ All HRDocuments have a valid EmployeeID."

- If the user asked about **class mismatches only**, show only the class issues table:

  | Document Name | Actual Class | Expected Class | Document ID |
  |---|---|---|---|
  | … | … | … | … |

  State: `N document(s) found with the wrong class.`
  If none: "✅ All documents are correctly classified as HRDocument."

- If the user asked about **both**, show both tables and both totals.

Do **not** volunteer the other table unless directly asked. The full results are
always saved to `audit_results_{lastname}.json` for use by later phases.

### EmployeeID validation rules

An EmployeeID is **invalid** when it is:
- `null` or not set
- An empty string
- Does not match the pattern `{PREFIX}\d{3}` (e.g. `DUP001`, `DUP005`)
- The value `{PREFIX}000` (all-zeros suffix — seeded misclassification)

All four cases are treated with equal severity — no tiers.

---

## Phase 2 — Class-Mismatch Check

**Trigger phrases**: "check document classes", "class mismatch", "documents starting with DUP001",
"wrong class for DUP001"

### Steps

**Step 1 — Identify the prefix**

Extract the employee ID prefix from the user's message (e.g. `DUP` from `DUP001`).
If the audit script was already run in Phase 1, reuse `audit_results_{lastname}.json` —
do not re-run the script.

If the script has not been run yet, run it:

```
.venv/bin/python .bob/skills/hr-classification-workflow/scripts/audit_hr_documents.py --user {LASTNAME} --prefix {PREFIX}
```

**Step 2 — Parse `class_issues` from the JSON**

Read `audit_results_{lastname}.json` and extract the `class_issues` array.

**Step 3 — Present the class mismatch table**

| Document Name | Actual Class | Expected Class | Document ID |
|---|---|---|---|
| … | … | … | … |

For each row, call `mcp__core-cs-mcp-server__get_document_properties` with the document ID
to confirm the actual class is accurate (the GraphQL query already returns className, so
this is a verification step only — skip if results are clearly unambiguous).

State: "`N` of `M` documents starting with `{PREFIX}` are misclassified."

---

## Phase 3 — Document Triage

**Trigger phrases**: "filed under base Document class", "what is this document",
"who does it belong to", "what class should it have", "read its content and tell me"

### Steps

**Step 1 — Identify the document**

The user will name a specific document (by name or ID). If they only give a name,
look it up:

Call `mcp__core-cs-mcp-server__lookup_documents_by_name` with keywords from the document name.

Use the returned ID for all subsequent calls.

**Step 2 — Extract properties and content**

Call `mcp__property-extraction-cs-mcp-server__property_extraction` with the document identifier.

This returns:
- The document's current class
- All available properties for that class
- The document's text extract content

**Step 3 — Analyse the content**

Call `mcp__ai-document-insight-cs-mcp-server__document_qa_specific` with:
- `document_id`: the document ID
- `prompt`: "What type of HR document is this? Who is the employee (name and ID)? What department are they in? What is the document date?"

**Step 4 — Determine the correct classification**

Based on content analysis, determine:

| Question | Answer |
|---|---|
| **What is it?** | e.g. Payslip, Employment Contract, Performance Review … |
| **Who does it belong to?** | Employee name + EmployeeID extracted from content |
| **Correct class** | Almost always `HRDocument` for HR content |
| **Required properties** | `EmployeeID`, `Department`, `DocType`, and any others found in content |

**Step 5 — Present the recommendation**

Present a clear recommendation block:

```
Document: {name}
Current class: Document  ← WRONG
Recommended class: HRDocument

Recommended properties:
  EmployeeID:  {value from content}
  Department:  {value from content}
  DocType:     {value from content}
  [any other HRDocument properties found]

Confidence: High / Medium / Low  (state why if not High)
```

Do NOT apply any changes in this phase. Triage only.

---

## Phase 4 — Fix One Document

**Trigger phrases**: "fix document", "reclassify it", "go ahead and fix", "reclassify as HRDocument"

### Steps

**Step 1 — Confirm the target document**

If Phase 3 was just completed, the document ID is already known. Otherwise ask the user
for the document name or ID. Look it up with `lookup_documents_by_name` if needed.

**Step 2 — Announce what you will do**

State exactly what you are about to do:
```
I will:
  1. Change class: Document → HRDocument
  2. Set EmployeeID = {value}
  3. Set Department = {value}
  4. Set DocType = {value}

Proceeding…
```

Do not ask for confirmation — just state it and proceed.

**Step 3 — Change the class**

Call `mcp__core-cs-mcp-server__update_document_class`:
- `identifier`: document ID
- `class_identifier`: `HRDocument`

**Step 4 — Set the properties**

Call `mcp__core-cs-mcp-server__get_class_property_descriptions` with `HRDocument`
to get the exact property identifiers, then call
`mcp__core-cs-mcp-server__update_document_properties` with:
- `identifier`: document ID
- `document_properties.properties`: array of `{identifier, value}` objects for
  `EmployeeID`, `Department`, `DocType` (and any others identified in Phase 3)

**Step 5 — Confirm success**

Call `mcp__core-cs-mcp-server__get_document_properties` on the document ID and verify:
- `className` is now `HRDocument`
- `EmployeeID` matches the value set

Present a one-line confirmation:
```
✅ {document name} — reclassified as HRDocument, EmployeeID={value}, Department={value}, DocType={value}
```

### Rules
- Never reclassify without having read the document content first (Phase 3 or equivalent)
- Never set properties to a value not found in the document content

---

## Phase 5 — Fix All Remaining Misclassified Documents

**Trigger phrases**: "fix the remaining", "fix all misclassified", "fix all documents",
"reclassify all", "bulk fix"

### Steps

**Step 1 — Load the audit results**

Read `audit_results_{lastname}.json`. Combine:
- `class_issues` array (wrong-class documents)
- `property_issues` array (HRDocuments with invalid EmployeeID)

These are the documents that need remediation.

If the audit JSON does not exist, run Phase 1 first to generate it.

**Step 2 — For each document in `class_issues`**

For each entry:
1. Call `mcp__property-extraction-cs-mcp-server__property_extraction` to get content
2. Call `mcp__ai-document-insight-cs-mcp-server__document_qa_specific` with prompt:
   "What HR document type is this, what is the employee's ID, department, and document date?"
3. Call `mcp__core-cs-mcp-server__update_document_class` → `HRDocument`
4. Call `mcp__core-cs-mcp-server__update_document_properties` with extracted values
5. Record result in the running summary

**Step 3 — For each document in `property_issues`**

For each entry (already class `HRDocument` but invalid EmployeeID):
1. Call `mcp__property-extraction-cs-mcp-server__property_extraction` to get content
2. Call `mcp__ai-document-insight-cs-mcp-server__document_qa_specific` with prompt:
   "What is the correct employee ID for this person? What is their department?"
3. Call `mcp__core-cs-mcp-server__update_document_properties` with corrected values
4. Record result in the running summary

**Step 4 — Present the summary table**

```
## Remediation Summary — {LASTNAME}

| Document | Previous Class | New Class | EmployeeID set | Status |
|---|---|---|---|---|
| {name} | {old} | HRDocument | {value} | ✅ Fixed |
| {name} | HRDocument | HRDocument | {value} | ✅ Fixed |
| {name} | … | … | … | ❌ Error: {reason} |

**Fixed:** X  |  **Errors:** Y  |  **Total:** Z
```

List any errors explicitly below the table.

### Rules
- Always read content before setting property values — never guess
- Always show the summary table, even if all documents were fixed successfully
- If a document cannot be read (text extract unavailable), flag it as `⚠️ Skipped — no content`

---

## Phase 6 — Classification Health Report

**Trigger phrases**: "classification health report", "final report", "are all documents correctly classified",
"governance recommendations", "generate a report"

### Steps

**Step 1 — Count all HR documents in the namespace**

Run the health check script:

```
.venv/bin/python .bob/skills/hr-classification-workflow/scripts/health_check_hr_documents.py --user {LASTNAME}
```

Read the stdout and `health_check_{lastname}.json` to get the total document count,
correctly classified `HRDocument` count, and any remaining misclassified documents.

**Step 2 — Check for remaining EmployeeID issues**

If `audit_results_{lastname}.json` exists and was generated after the last remediation,
use its `summary` block. Otherwise re-run the audit script (Phase 1) to get fresh counts.

**Step 3 — Create the output folder and write the report**

Create the output folder:

```
audits/{LASTNAME}_{YYYYMMDD}/
```

Where `{YYYYMMDD}` is today's date (e.g. `DUPONT_20250115`).

Write the report to:

```
audits/{LASTNAME}_{YYYYMMDD}/classification_health_report.md
```

Use this template:

```markdown
# HR Document Classification Health Report

**Namespace:** /BOB_LAB/{LASTNAME}/
**Report Date:** {YYYY-MM-DD}
**Generated by:** Bob (AI Documentalist)

---

## Executive Summary

| Metric | Count |
|---|---|
| Total HR documents in namespace | N |
| Correctly classified (HRDocument) | N |
| Remaining classification issues | N |
| EmployeeID issues resolved | N |
| Documents still needing attention | N |

**Overall health:** 🟢 Good / 🟡 Needs attention / 🔴 Critical

---

## Classification Breakdown

### Documents by Class

| Class | Count | Expected? |
|---|---|---|
| HRDocument | N | ✅ Yes |
| Document | N | ❌ No — misclassified |
| Contract | N | ❌ No — wrong domain class |
| {other} | N | … |

---

## Issues Found and Resolved

### Property Issues (EmployeeID)

| Document | Issue | Resolution |
|---|---|---|
| … | … | … |

### Class Issues

| Document | Old Class | New Class | Resolution |
|---|---|---|---|
| … | … | … | … |

---

## Remaining Issues

List any documents that could NOT be fixed, with the reason.

If none: "✅ All issues resolved — no remaining classification problems."

---

## Governance Recommendations

Based on the audit findings, the following governance measures are recommended:

1. **Mandatory EmployeeID validation** — enforce at upload time; reject documents
   without a valid 6-digit EmployeeID at the ingestion layer.

2. **Class enforcement policy** — HR documents must always be filed as `HRDocument`,
   never as base `Document`. Consider disabling direct `Document` class creation
   in the `/BOB_LAB/` namespace.

3. **Regular classification audits** — run this skill's Phase 1 audit monthly to
   catch misclassification early.

4. **Required property checklist** — ensure `EmployeeID`, `Department`, and `DocType`
   are marked as required fields in the `HRDocument` class definition.

5. **Training** — ensure all document submitters understand that HR documents must
   use the `HRDocument` class with all mandatory properties populated.

---

*Report generated by the `hr-classification-workflow` Bob skill.*
*Source namespace: /BOB_LAB/{LASTNAME}/*
```

**Step 4 — Confirm report location**

Tell the user:
```
✅ Classification health report saved to:
   audits/{LASTNAME}_{YYYYMMDD}/classification_health_report.md
```

The report is saved to the local workspace only — it is NOT uploaded to the FileNet repository.

---

## Rules that must never be broken

1. **Never reclassify a document without first reading its content** (via `property_extraction`
   or `document_qa_specific`). Class changes based on filename alone are forbidden.

2. **Never set an EmployeeID to a value not found in the document content.** If the
   correct ID cannot be determined from the content, flag the document as `⚠️ needs manual review`.

3. **Never skip the summary table** after any bulk operation (Phase 5). Always show
   every document processed, even if all succeeded.

4. **Never state counts that have not been verified** by the script output or MCP tool
   response. Do not estimate or guess document totals.

5. **Never update properties without first confirming the class** is correct. If a
   document's class is still wrong, fix the class first (Phase 4 Step 3), then set
   properties (Phase 4 Step 4).

---

## Supporting files in this skill directory

- `scripts/audit_hr_documents.py` — GraphQL-based bulk audit for Phases 1 & 2

Run from the project root using `.venv/bin/python`.

## Related skills

- `hr-document-upload` — bulk-upload HR documents with seeded misclassification seeds
- `class-property-report` — inspect all properties of a document class in detail

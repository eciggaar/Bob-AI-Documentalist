---
name: hr-document-upload
description: Use when the user wants to bulk-upload HR documents for multiple employees (2 or more) to the FileNet content repository from a local HR folder (e.g. HR_DUPONT/). Skips documents already in the repository, applies Lab 3 misclassification seeds, and produces a clear per-employee upload summary. Do NOT use for single-employee or single-document uploads.
---

# HR Document Upload

Upload all HR documents from a local folder to the FileNet repository,
skipping any documents that already exist. Output a clear summary per employee.

## Step 0 — Verify the virtual environment

All Python commands in this skill MUST use the project virtual environment.
Before running anything, confirm `.venv/bin/python` exists:

```
test -f .venv/bin/python && echo "venv OK" || echo "venv MISSING"
```

If the venv is missing, create and populate it first:

```
python -m venv .venv && .venv/bin/pip install requests
```

If `pip` is not present (uv-managed venv), use:

```
uv pip install requests
```

Do not proceed until `.venv/bin/python` is confirmed available.

The supporting scripts for this skill live at:
- `.bob/skills/hr-document-upload/scripts/bulk_upload_employees.py`
- `.bob/skills/hr-document-upload/scripts/execute_bulk_upload.py`

All `python` commands below reference these paths. Run them from the **project root**.

## Step 1 — Identify the namespace

Extract the lab namespace (LASTNAME in uppercase) from the user's message.
The local source folder is `HR_{LASTNAME}/` and the repository target is `/BOB_LAB/{LASTNAME}/`.

If the namespace is not clear, ask:
> "Which namespace (last name) should I use? For example: DUPONT, CIGGAAR."

## Step 2 — Generate the upload plan

Run the plan generator using the venv Python. It connects to the repository,
checks which documents already exist per folder, and writes only the missing
ones into the plan JSON — documents already in the repository are excluded.

```
.venv/bin/python .bob/skills/hr-document-upload/scripts/bulk_upload_employees.py --user {LASTNAME}
```

Read the stdout to confirm:
- How many documents are **to upload** vs **already in the repository**
- Which employees have seeded misclassification errors and which error type

## Step 3 — Execute the upload

If `Documents to upload` is **0** in the plan output, skip this step —
nothing needs to be uploaded.

Otherwise run using the venv Python:

```
.venv/bin/python .bob/skills/hr-document-upload/scripts/execute_bulk_upload.py --user {LASTNAME}
```

Capture the stdout. Note any lines containing `❌ Error` — these are upload failures.

## Step 4 — Output the summary

Present a clear summary table in this exact format:

```
## Upload Summary — {LASTNAME}

| Employee | Uploaded | Already in repo | Seeded error |
|---|---|---|---|
| {ID} {Name} | {n} | {n} | {description or —} |
...

**Total uploaded:** X  |  **Already in repo:** Y  |  **Errors:** Z
```

Use these human-readable descriptions for each seeded error type:

| `seeded_error` value | Description |
|---|---|
| `Document` on a payslip | Bare `Document` class — no `EmployeeID` or HR metadata |
| `Contract` | Wrong class (`Contract` instead of `HRDocument`) — `Department` missing |
| `wrong_employee_id` | `HRDocument` with `EmployeeID = 000000` (should be the real ID) |
| `Document` on disciplinary | Bare `Document` class — no metadata at all |
| `missing_properties` | `HRDocument` but missing `Department` and `DocType` |

If any `❌ Error` lines appeared in Step 3, list them explicitly below the table.

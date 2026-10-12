---
name: hr-document-upload
description: Use when the user wants to bulk-upload HR documents for multiple employees (2 or more) to the FileNet content repository from a local HR folder (e.g. HR_DUPONT/). Skips documents already in the repository, applies Lab 3 misclassification seeds, and produces a clear per-employee upload summary. Do NOT use for single-employee or single-document uploads.
---

# HR Document Upload

Upload all HR documents from a local folder to the FileNet repository,
skipping any documents that already exist. Output a clear summary per employee.

## Prerequisites

Before running this skill, ensure the following are configured:
- **Repository connection**: `.bob/mcp.json` contains valid `core-cs-mcp-server` environment variables (`SERVER_URL`, `OBJECT_STORE`, `USERNAME`, `PASSWORD`).
- **Repository structure & classes**:
  - The repository has the `HRDocument`, `Document`, and `Contract` classes defined.
  - The upload process automatically creates `/BOB_LAB` and `/BOB_LAB/{LASTNAME}` in the repository if they do not exist.
- **Local directory structure**:
  - Source folder: `HR_{LASTNAME}/` (e.g. `HR_DUPONT/`).
  - Employee folders follow `{PREFIX}00N_First Last` convention (e.g. `DUP001_John Doe`, where `PREFIX` is the first 3 uppercase letters of `LASTNAME`).
  - Standard category folders (`01_Recruitment`, `02_Employment_Contract`, ..., `08_Exit`).
  - Text documents (`.txt`) containing embedded key-value pairs under a `DOCUMENT METADATA` header.

## Step 0 — Verify the virtual environment

All Python commands in this skill MUST use the project virtual environment.
Before running anything, confirm the virtual environment Python interpreter exists:

- **macOS / Linux:**
  ```
  test -f .venv/bin/python && echo "venv OK" || echo "venv MISSING"
  ```
  If missing, create and populate it:
  ```
  python3 -m venv .venv && .venv/bin/pip install requests
  ```
- **Windows (PowerShell / Command Prompt):**
  ```
  if exist .venv\Scripts\python.exe (echo venv OK) else (echo venv MISSING)
  ```
  If missing, create and populate it:
  ```
  python -m venv .venv && .venv\Scripts\pip.exe install requests
  ```

If `pip` is not present (uv-managed venv), use:
```
uv pip install requests
```

Do not proceed until the virtual environment Python is confirmed available.

The supporting scripts for this skill live at:
- `.bob/skills/hr-document-upload/scripts/bulk_upload_employees.py`
- `.bob/skills/hr-document-upload/scripts/execute_bulk_upload.py`

All python commands below reference these paths. Run them from the **project root**.

## Step 1 — Identify the namespace

Extract the lab namespace (LASTNAME in uppercase) from the user's message.
The local source folder is `HR_{LASTNAME}/` and the repository target is `/BOB_LAB/{LASTNAME}/`.

If the namespace is not clear, ask:
> "Which namespace (last name) should I use? For example: DUPONT, CIGGAAR."

## Step 2 — Generate the upload plan

Run the plan generator using the venv Python. It automatically removes any stale plan files,
queries the repository to identify existing documents per folder,
and writes only missing documents into the plan JSON:

- **macOS / Linux:**
  ```
  .venv/bin/python .bob/skills/hr-document-upload/scripts/bulk_upload_employees.py --user {LASTNAME}
  ```
- **Windows:**
  ```
  .venv\Scripts\python.exe .bob\skills\hr-document-upload\scripts\bulk_upload_employees.py --user {LASTNAME}
  ```

*(Optional: add `--verbose` to inspect per-folder repository query responses).*

Check the exit code:
- If Step 2 exits with a **non-zero status** (e.g. source folder missing or repository query failure), **stop immediately** and report the error.
- If Step 2 succeeds, confirm from stdout:
  - How many documents are **to upload** vs **already in the repository**
  - Which employees have seeded misclassification errors and which error type

## Step 3 — Execute the upload

If `Documents to upload` is **0** in the plan output (all documents already exist), skip execution and inform the user with a single sentence:
> "All {N} documents for namespace {LASTNAME} already exist in the repository; no new files were uploaded."

Otherwise run using the venv Python:

- **macOS / Linux:**
  ```
  .venv/bin/python .bob/skills/hr-document-upload/scripts/execute_bulk_upload.py --user {LASTNAME}
  ```
- **Windows:**
  ```
  .venv\Scripts\python.exe .bob\skills\hr-document-upload\scripts\execute_bulk_upload.py --user {LASTNAME}
  ```

Check the command exit code and captured stdout:
- An exit code of **0** indicates all operations completed successfully.
- An exit code of **1** indicates one or more folder creation or document upload operations failed.
- Execution metrics are saved to `upload_result_{lastname.lower()}.json`.

## Step 4 — Output the summary

Present a clear report showing what documents were added and for which employee:

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
| `Contract` | Wrong class (`Contract` instead of `HRDocument`) — uploaded with no HR properties |
| `wrong_employee_id` | `HRDocument` with invalid `EmployeeID = 000000` (should be the real ID) |
| `Document` on disciplinary | Bare `Document` class — no metadata at all |
| `missing_properties` | `HRDocument` with omitted `EmployeeID`, `Department`, and `DocType` |

Populate the summary columns reflecting the upload batch performed:
- **Uploaded**: Number of documents uploaded during this run (from `upload_result_{lastname.lower()}.json` or Step 3 stdout).
- **Already in repo**: Documents that were already in the repository prior to this upload run (from `upload_plan_{lastname.lower()}.json`).
- **Seeded error**: The intentional classification seed applied to that employee.

If an idempotency verification check is performed afterwards, mention it in a single concluding sentence (e.g. *"Verification confirmed all {Total} documents are present in the repository and subsequent runs will skip them."*) rather than printing a second table showing 0 uploads.

If any errors occurred in Step 3 (non-zero exit code or upload failures in stdout), list them explicitly below the table.

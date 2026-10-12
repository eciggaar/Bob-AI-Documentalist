# HR Document Classification Health Report

**Namespace:** /BOB_LAB/{LASTNAME}/
**Report date:** {YYYY-MM-DD}

## Executive summary

| Metric | Count |
|---|---|
| Total documents in namespace | {totalDocuments} |
| Correctly classified (HRDocument) | {hrDocumentCount} |
| Wrong class | {len(classIssues)} |
| HRDocuments with invalid EmployeeID | {len(propertyIssues)} |

**Overall health:** 🟢 no issues / 🟡 issues remain / 🔴 more than 10% of documents affected

## Documents by class

| Class | Count | Expected? |
|---|---|---|
| HRDocument | N | ✅ |
| {other class} | N | ❌ |

## Remaining issues

Table of documents still wrong, with the reason. If none: "✅ No remaining classification problems."

## Fixed in this session (only if known)

| Document | Issue | Resolution |
|---|---|---|

## Recommendations

1. Validate EmployeeID (`{PREFIX}` + 3 digits) at upload time.
2. File HR documents as `HRDocument`, never as base `Document`.
3. Mark `EmployeeID`, `Department` and `DocType` as required on `HRDocument`.
4. Re-run the audit regularly (e.g. monthly).

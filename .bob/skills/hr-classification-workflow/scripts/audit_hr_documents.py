#!/usr/bin/env python3
"""
HR Document Classification Audit Script.

Connects to the FileNet repository via GraphQL and produces a structured
audit report for a given namespace (/BOB_LAB/<LASTNAME>/):

  1. property_issues  — HRDocument records with a missing or invalid EmployeeID
                        (null, empty, or not exactly 6 digits; "000000" is also invalid)
  2. class_issues     — Documents filed under the wrong class for a given prefix
                        (e.g. DUP001–DUP005 that are NOT HRDocument)

Auth config is read from .bob/mcp.json (same pattern as bulk_upload_employees.py).

Usage:
    .venv/bin/python .bob/skills/hr-classification-workflow/scripts/audit_hr_documents.py --user DUPONT
    .venv/bin/python .bob/skills/hr-classification-workflow/scripts/audit_hr_documents.py --user DUPONT --prefix DUP
"""

import argparse
import json
import re
import sys
import warnings
from pathlib import Path

import requests

warnings.filterwarnings("ignore")  # suppress SSL warnings on self-signed certs

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def is_valid_employee_id(value, prefix: str) -> bool:
    """Return True only when value starts with the 3-char prefix (e.g. 'DUP')
    followed by exactly 3 digits — e.g. DUP001, CIG003."""
    if value is None or str(value).strip() == "":
        return False
    s = str(value).strip()
    expected_re = re.compile(r"^" + re.escape(prefix) + r"\d{3}$", re.IGNORECASE)
    return bool(expected_re.match(s))


# ---------------------------------------------------------------------------
# Auth helpers  (identical pattern to bulk_upload_employees.py)
# ---------------------------------------------------------------------------

def load_mcp_config():
    """Load ZenIAM connection config from .bob/mcp.json."""
    mcp_path = Path(".bob/mcp.json")
    if not mcp_path.exists():
        return None
    try:
        env = json.loads(mcp_path.read_text())["mcpServers"]["core-cs-mcp-server"]["env"]
        return {
            "SERVER_URL":     env["SERVER_URL"],
            "OBJECT_STORE":   env["OBJECT_STORE"],
            "ZEN_URL":        env["ZENIAM_ZEN_URL"],
            "IAM_URL":        env["ZENIAM_IAM_URL"],
            "IAM_GRANT_TYPE": env["ZENIAM_IAM_GRANT_TYPE"],
            "IAM_SCOPE":      env["ZENIAM_IAM_SCOPE"],
            "IAM_USER":       env["ZENIAM_IAM_USER"],
            "IAM_PASSWORD":   env["ZENIAM_IAM_PASSWORD"],
        }
    except Exception as exc:
        print(f"❌ Error reading .bob/mcp.json: {exc}", file=sys.stderr)
        return None


def get_bearer_token(cfg) -> str:
    """Exchange username/password for a ZenIAM Bearer token."""
    iam = requests.post(
        cfg["IAM_URL"],
        data={
            "grant_type": cfg["IAM_GRANT_TYPE"],
            "username":   cfg["IAM_USER"],
            "password":   cfg["IAM_PASSWORD"],
            "scope":      cfg["IAM_SCOPE"],
        },
        verify=False,
        timeout=30,
    )
    iam.raise_for_status()
    zen = requests.get(
        cfg["ZEN_URL"],
        headers={
            "iam-token": iam.json()["access_token"],
            "username":  cfg["IAM_USER"],
        },
        verify=False,
        timeout=30,
    )
    zen.raise_for_status()
    return zen.json()["accessToken"]


def gql(cfg, token, query, variables=None):
    """Execute a GraphQL query and return the parsed JSON response."""
    resp = requests.post(
        cfg["SERVER_URL"],
        json={"query": query, "variables": variables or {}},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        verify=False,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# GraphQL queries
# ---------------------------------------------------------------------------

QUERY_HRDOCUMENTS = """
query($repo: String!, $where: String) {
  documents(
    repositoryIdentifier: $repo,
    from: "HRDocument",
    where: $where,
    pageSize: 100
  ) {
    documents {
      id
      name
      className
      properties(includes: ["EmployeeID"]) {
        alias
        value
      }
    }
  }
}
"""

QUERY_DOCS_BY_NAME_PREFIX = """
query($repo: String!, $where: String) {
  documents(
    repositoryIdentifier: $repo,
    from: "Document",
    where: $where,
    pageSize: 100
  ) {
    documents {
      id
      name
      className
    }
  }
}
"""


def fetch_hrdocuments(cfg, token, lastname):
    """
    Return all HRDocument records under /BOB_LAB/{lastname}/ (INSUBFOLDER).
    Each item includes id, name, className, and a flat property dict keyed by alias.
    """
    where = f"This INSUBFOLDER '/BOB_LAB/{lastname}'"
    data = gql(cfg, token, QUERY_HRDOCUMENTS, {"repo": cfg["OBJECT_STORE"], "where": where})
    raw_docs = (
        (data.get("data") or {})
        .get("documents", {})
        .get("documents", [])
    ) or []

    results = []
    for doc in raw_docs:
        props = {}
        for p in doc.get("properties") or []:
            props[p.get("alias", "")] = p.get("value")
        results.append({
            "id":        doc.get("id"),
            "name":      doc.get("name"),
            "className": doc.get("className"),
            "props":     props,
        })
    return results


def fetch_docs_by_prefix(cfg, token, lastname, prefix):
    """
    Return all documents whose name starts with {prefix} under /BOB_LAB/{lastname}/.
    Uses INSUBFOLDER and client-side prefix filter (ODQL LIKE not always available).
    """
    where = f"This INSUBFOLDER '/BOB_LAB/{lastname}'"
    data = gql(cfg, token, QUERY_DOCS_BY_NAME_PREFIX, {"repo": cfg["OBJECT_STORE"], "where": where})
    raw_docs = (
        (data.get("data") or {})
        .get("documents", {})
        .get("documents", [])
    ) or []
    return [
        {
            "id":        d.get("id"),
            "name":      d.get("name"),
            "className": d.get("className"),
        }
        for d in raw_docs
        if (d.get("name") or "").upper().startswith(prefix.upper())
    ]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def audit_property_issues(hrdocs, prefix):
    """
    Flag HRDocument records with a missing or invalid EmployeeID.
    Valid EmployeeID must start with {prefix} followed by 3 digits (e.g. DUP001).
    Returns a list of issue dicts.
    """
    issues = []
    for doc in hrdocs:
        emp_id = doc["props"].get("EmployeeID")
        if not is_valid_employee_id(emp_id, prefix):
            if emp_id is None or str(emp_id).strip() == "":
                reason = "missing"
            else:
                reason = f"invalid value '{emp_id}'"
            issues.append({
                "id":          doc["id"],
                "name":        doc["name"],
                "className":   doc["className"],
                "EmployeeID":  emp_id,
                "issue":       f"EmployeeID {reason}",
            })
    return issues


def audit_class_issues(prefix_docs, expected_class="HRDocument"):
    """
    Flag documents that do NOT have the expected class.
    Returns a list of issue dicts.
    """
    issues = []
    for doc in prefix_docs:
        if doc["className"] != expected_class:
            issues.append({
                "id":            doc["id"],
                "name":          doc["name"],
                "actualClass":   doc["className"],
                "expectedClass": expected_class,
                "issue":         f"Class is '{doc['className']}', expected '{expected_class}'",
            })
    return issues


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def print_section(title, rows, columns):
    width = 80
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")
    if not rows:
        print("  ✅ No issues found.")
        return
    col_widths = {c: max(len(c), max((len(str(r.get(c, "") or "")) for r in rows), default=0)) for c in columns}
    header = "  " + "  |  ".join(c.ljust(col_widths[c]) for c in columns)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for row in rows:
        line = "  " + "  |  ".join(str(row.get(c, "") or "").ljust(col_widths[c]) for c in columns)
        print(line)
    print(f"\n  Total issues: {len(rows)}")


def save_results(lastname, property_issues, class_issues):
    output = {
        "namespace":        f"/BOB_LAB/{lastname}",
        "property_issues":  property_issues,
        "class_issues":     class_issues,
        "summary": {
            "property_issue_count": len(property_issues),
            "class_issue_count":    len(class_issues),
            "total_issues":         len(property_issues) + len(class_issues),
        },
    }
    filename = f"audit_results_{lastname.lower()}.json"
    Path(filename).write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n✅ Full results saved to {filename}")
    return filename


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="HR document classification audit for a FileNet namespace.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  .venv/bin/python audit_hr_documents.py --user DUPONT
  .venv/bin/python audit_hr_documents.py --user DUPONT --prefix DUP
        """,
    )
    parser.add_argument(
        "--user",
        required=True,
        metavar="LASTNAME",
        help="Namespace last name (e.g. DUPONT, CIGGAAR)",
    )
    parser.add_argument(
        "--prefix",
        metavar="PREFIX",
        default=None,
        help="3-char employee ID prefix for class-mismatch check (default: first 3 chars of --user)",
    )
    args = parser.parse_args()

    lastname = args.user.upper().strip()
    prefix   = (args.prefix or lastname[:3]).upper()

    print("=" * 80)
    print(f"  HR CLASSIFICATION AUDIT  —  /BOB_LAB/{lastname}/")
    print("=" * 80)

    cfg = load_mcp_config()
    if not cfg:
        print("❌ Could not load .bob/mcp.json. Run from the project root.", file=sys.stderr)
        sys.exit(1)

    print("  🔑 Authenticating …", end=" ", flush=True)
    token = get_bearer_token(cfg)
    print("OK")

    print(f"  📂 Fetching HRDocument records in /BOB_LAB/{lastname}/ …", end=" ", flush=True)
    hrdocs = fetch_hrdocuments(cfg, token, lastname)
    print(f"{len(hrdocs)} found")

    print(f"  📂 Fetching documents with prefix '{prefix}' …", end=" ", flush=True)
    prefix_docs = fetch_docs_by_prefix(cfg, token, lastname, prefix)
    print(f"{len(prefix_docs)} found")

    property_issues = audit_property_issues(hrdocs, prefix)
    class_issues    = audit_class_issues(prefix_docs)

    print_section(
        f"PROPERTY ISSUES — HRDocuments with missing/invalid EmployeeID  ({len(property_issues)} issues)",
        property_issues,
        ["name", "EmployeeID", "issue", "id"],
    )
    print_section(
        f"CLASS ISSUES — Documents with prefix '{prefix}' not classified as HRDocument  ({len(class_issues)} issues)",
        class_issues,
        ["name", "actualClass", "expectedClass", "id"],
    )

    save_results(lastname, property_issues, class_issues)

    print(f"\n{'=' * 80}")
    print(f"  SUMMARY: {len(property_issues)} property issue(s)  |  {len(class_issues)} class issue(s)")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()

# Made with Bob

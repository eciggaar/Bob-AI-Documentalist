#!/usr/bin/env python3
"""
HR Document Classification Health Check Script.

Connects to the FileNet repository via GraphQL and counts documents
in /BOB_LAB/<LASTNAME>/ by class — giving reliable totals for the
Phase 6 Classification Health Report.

Reports:
  - Total HRDocument count
  - Total non-HRDocument count (by class) — these are misclassified
  - Total documents with prefix {PREFIX} across all classes

Auth config is read from .bob/mcp.json (same pattern as audit_hr_documents.py).

Usage:
    .venv/bin/python .bob/skills/hr-classification-workflow/scripts/health_check_hr_documents.py --user DUPONT
    .venv/bin/python .bob/skills/hr-classification-workflow/scripts/health_check_hr_documents.py --user DUPONT --prefix DUP
"""

import argparse
import json
import sys
import warnings
from collections import Counter
from pathlib import Path

import requests

warnings.filterwarnings("ignore")  # suppress SSL warnings on self-signed certs


# ---------------------------------------------------------------------------
# Auth helpers  (identical pattern to audit_hr_documents.py)
# ---------------------------------------------------------------------------

def load_mcp_config():
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

# Count all HRDocument records in the namespace
QUERY_HRDOCUMENT_COUNT = """
query($repo: String!, $where: String) {
  documents(
    repositoryIdentifier: $repo,
    from: "HRDocument",
    where: $where,
    pageSize: 200
  ) {
    documents {
      id
      name
      className
    }
  }
}
"""

# Count all documents in the namespace regardless of class —
# using base Document so subclasses are included too
QUERY_ALL_DOCS_COUNT = """
query($repo: String!, $where: String) {
  documents(
    repositoryIdentifier: $repo,
    from: "Document",
    where: $where,
    pageSize: 200
  ) {
    documents {
      id
      name
      className
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="HR document classification health check for a FileNet namespace.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  .venv/bin/python health_check_hr_documents.py --user DUPONT
  .venv/bin/python health_check_hr_documents.py --user DUPONT --prefix DUP
        """,
    )
    parser.add_argument("--user", required=True, metavar="LASTNAME",
                        help="Namespace last name (e.g. DUPONT)")
    parser.add_argument("--prefix", metavar="PREFIX", default=None,
                        help="3-char employee ID prefix (default: first 3 chars of --user)")
    args = parser.parse_args()

    lastname = args.user.upper().strip()
    prefix   = (args.prefix or lastname[:3]).upper()
    where    = f"This INSUBFOLDER '/BOB_LAB/{lastname}'"

    print("=" * 80)
    print(f"  HR CLASSIFICATION HEALTH CHECK  —  /BOB_LAB/{lastname}/")
    print("=" * 80)

    cfg = load_mcp_config()
    if not cfg:
        print("❌ Could not load .bob/mcp.json. Run from the project root.", file=sys.stderr)
        sys.exit(1)

    print("  🔑 Authenticating …", end=" ", flush=True)
    token = get_bearer_token(cfg)
    print("OK")

    # --- HRDocument count ---
    print(f"  📂 Counting HRDocument records in /BOB_LAB/{lastname}/ …", end=" ", flush=True)
    hr_data = gql(cfg, token, QUERY_HRDOCUMENT_COUNT, {"repo": cfg["OBJECT_STORE"], "where": where})
    hr_docs = (hr_data.get("data") or {}).get("documents", {}).get("documents", []) or []
    print(f"{len(hr_docs)} found")

    # --- All documents count (by class) ---
    print(f"  📂 Counting all documents in /BOB_LAB/{lastname}/ …", end=" ", flush=True)
    all_data = gql(cfg, token, QUERY_ALL_DOCS_COUNT, {"repo": cfg["OBJECT_STORE"], "where": where})
    all_docs = (all_data.get("data") or {}).get("documents", {}).get("documents", []) or []
    print(f"{len(all_docs)} found")

    # Count by class
    class_counts = Counter(d.get("className", "Unknown") for d in all_docs)
    misclassified = {cls: cnt for cls, cnt in class_counts.items() if cls != "HRDocument"}
    misclassified_total = sum(misclassified.values())

    # Filter to prefix
    prefix_docs = [d for d in all_docs if (d.get("name") or "").upper().startswith(prefix.upper())]

    # --- Output ---
    print(f"\n{'=' * 80}")
    print(f"  RESULTS")
    print(f"{'=' * 80}")
    print(f"  Total documents in namespace : {len(all_docs)}")
    print(f"  Correctly classified (HRDoc) : {len(hr_docs)}")
    print(f"  Misclassified (non-HRDoc)    : {misclassified_total}")
    print(f"  Documents with prefix '{prefix}'  : {len(prefix_docs)}")

    print(f"\n  Class breakdown:")
    for cls, cnt in sorted(class_counts.items()):
        ok = "✅" if cls == "HRDocument" else "❌"
        print(f"    {ok}  {cls}: {cnt}")

    if misclassified_total == 0:
        print(f"\n  🟢 All documents are correctly classified as HRDocument.")
    else:
        print(f"\n  🔴 {misclassified_total} document(s) are NOT classified as HRDocument:")
        for d in all_docs:
            if d.get("className") != "HRDocument":
                print(f"       - {d.get('name')}  [{d.get('className')}]  {d.get('id')}")

    # Save JSON output for report generation
    output = {
        "namespace": f"/BOB_LAB/{lastname}",
        "total_documents": len(all_docs),
        "hrdocument_count": len(hr_docs),
        "misclassified_count": misclassified_total,
        "class_breakdown": dict(class_counts),
        "misclassified_documents": [
            {"id": d.get("id"), "name": d.get("name"), "className": d.get("className")}
            for d in all_docs if d.get("className") != "HRDocument"
        ],
    }
    filename = f"health_check_{lastname.lower()}.json"
    Path(filename).write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n✅ Full results saved to {filename}")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()

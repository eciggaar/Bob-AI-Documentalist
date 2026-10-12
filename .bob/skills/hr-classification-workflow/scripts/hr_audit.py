#!/usr/bin/env python3
"""Read-only classification scan of a FileNet namespace (/BOB_LAB/<LASTNAME>/).

Prints one JSON document to stdout (progress/errors go to stderr). Never modifies the repository.

Usage (from the project root):
    .venv/bin/python .bob/skills/hr-classification-workflow/scripts/hr_audit.py --user DUPONT [--prefix DUP] [--insecure]

Credentials come from .bob/mcp.json (server "core-cs-mcp-server"): basic auth if USERNAME/PASSWORD
are present, otherwise the ZENIAM_* bearer-token flow. TLS is verified unless --insecure is given
(use it only for lab servers with self-signed certificates). Standard library only.
"""
import argparse
import base64
import json
import re
import ssl
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

PAGE_SIZE = 100
QUERY_INITIAL = """
query($repo: String!, $where: String) {
  documents(repositoryIdentifier: $repo, from: "Document", where: $where, pageSize: %d) {
    documents { id name className properties(includes: ["EmployeeID"]) { alias value } }
    pageInfo { token }
  }
}
""" % PAGE_SIZE

QUERY_MORE = """
query($token: String!) {
  moreDocuments(token: $token) {
    documents { id name className properties(includes: ["EmployeeID"]) { alias value } }
    pageInfo { token }
  }
}
"""


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_env():
    p = Path(".bob/mcp.json")
    if not p.exists():
        fail("'.bob/mcp.json' not found. Run from the project root.")
    try:
        return json.loads(p.read_text(encoding="utf-8"))["mcpServers"]["core-cs-mcp-server"]["env"]
    except (KeyError, ValueError) as exc:
        fail(f"cannot read core-cs-mcp-server env from .bob/mcp.json: {exc!r}")


def make_opener(insecure):
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))


def send(opener, req):
    with opener.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def auth_header(env, opener):
    if env.get("USERNAME") and env.get("PASSWORD"):
        raw = f'{env["USERNAME"]}:{env["PASSWORD"]}'.encode()
        return "Basic " + base64.b64encode(raw).decode()
    try:
        iam = send(opener, urllib.request.Request(
            env["ZENIAM_IAM_URL"],
            data=urllib.parse.urlencode({
                "grant_type": env["ZENIAM_IAM_GRANT_TYPE"], "username": env["ZENIAM_IAM_USER"],
                "password": env["ZENIAM_IAM_PASSWORD"], "scope": env["ZENIAM_IAM_SCOPE"]}).encode()))
        zen = send(opener, urllib.request.Request(
            env["ZENIAM_ZEN_URL"],
            headers={"iam-token": iam["access_token"], "username": env["ZENIAM_IAM_USER"]}))
        return "Bearer " + zen["accessToken"]
    except KeyError as exc:
        fail(f"missing credential key in .bob/mcp.json: {exc}")


def fetch_all(env, opener, auth, lastname):
    docs, token = [], None
    where = f"This INSUBFOLDER '/BOB_LAB/{lastname}'"
    while True:
        if token is None:
            body = json.dumps({"query": QUERY_INITIAL, "variables": {
                "repo": env["OBJECT_STORE"], "where": where}}).encode()
        else:
            body = json.dumps({"query": QUERY_MORE, "variables": {
                "token": token}}).encode()
        resp = send(opener, urllib.request.Request(
            env["SERVER_URL"], data=body,
            headers={"Content-Type": "application/json", "Authorization": auth}))
        if resp.get("errors"):
            fail(f"GraphQL error: {resp['errors']}")
        data = resp.get("data") or {}
        page = data.get("documents") if token is None else data.get("moreDocuments")
        page = page or {}
        docs.extend(page.get("documents") or [])
        token = (page.get("pageInfo") or {}).get("token")
        if not token:
            return docs


def valid_employee_id(value, prefix):
    s = "" if value is None else str(value).strip()
    return bool(re.fullmatch(re.escape(prefix) + r"\d{3}", s, re.IGNORECASE)) \
        and not s.upper().endswith("000")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", required=True, help="namespace last name, e.g. DUPONT")
    ap.add_argument("--prefix", help="EmployeeID prefix (default: first 3 chars of --user)")
    ap.add_argument("--insecure", action="store_true", help="skip TLS verification (lab only)")
    args = ap.parse_args()

    lastname = args.user.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_-]+", lastname):
        fail("--user may only contain letters, digits, '_' and '-'")
    prefix = (args.prefix or lastname[:3]).upper()

    env = load_env()
    opener = make_opener(args.insecure)
    docs = fetch_all(env, opener, auth_header(env, opener), lastname)

    property_issues, class_issues, counts = [], [], Counter()
    for d in docs:
        cls = d.get("className") or "Unknown"
        counts[cls] += 1
        if cls != "HRDocument":
            class_issues.append({"id": d["id"], "name": d["name"], "actualClass": cls,
                                 "expectedClass": "HRDocument"})
            continue
        props = {p.get("alias"): p.get("value") for p in d.get("properties") or []}
        emp = props.get("EmployeeID")
        if not valid_employee_id(emp, prefix):
            missing = emp is None or str(emp).strip() == ""
            property_issues.append({"id": d["id"], "name": d["name"], "EmployeeID": emp,
                                    "issue": "missing" if missing else f"invalid value '{emp}'"})

    json.dump({
        "namespace": f"/BOB_LAB/{lastname}", "employeeIdPrefix": prefix,
        "totalDocuments": len(docs), "hrDocumentCount": counts.get("HRDocument", 0),
        "classBreakdown": dict(counts),
        "propertyIssues": property_issues, "classIssues": class_issues,
    }, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()

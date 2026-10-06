#!/usr/bin/env python3
"""
Bulk upload script for HR documents to FileNet repository.
Generates an upload plan that only includes documents not yet present in the
repository. Handles the 5 seeded misclassifications for Lab 3 training.

Usage:
    python bulk_upload_employees.py --user CIGGAAR
    python bulk_upload_employees.py --user DUPONT
"""

import os
import sys
import json
import re
import argparse
import requests
from pathlib import Path

# Document categories
CATEGORIES = [
    "01_Recruitment",
    "02_Employment_Contract",
    "03_Personal_Administration",
    "04_Payroll",
    "05_Performance",
    "06_Training",
    "07_Disciplinary",
    "08_Exit"
]

# Seeded misclassifications (dynamically generated based on namespace)
# Pattern: {PREFIX}001, {PREFIX}002, etc. where PREFIX is first 3 UPPERCASE chars of --user
def get_seeded_errors(prefix):
    """Generate seeded errors for the given namespace prefix (first 3 uppercase chars)"""
    prefix = prefix[:3].upper()  # Ensure uppercase and only first 3 chars
    return {
        f"{prefix}001": {"Payslip_2024_01": "Document"},  # Base Document class, no EmployeeID
        f"{prefix}002": {"Employment_Contract": "Contract"},  # Wrong domain class
        f"{prefix}003": {"Performance_Review_2024": "wrong_employee_id"},  # Wrong EmployeeID (000000)
        f"{prefix}004": {"Disciplinary_Record": "Document"},  # Base Document class, no metadata
        f"{prefix}005": {"Exit_Notes": "missing_properties"}  # Correct class but missing Department and DocType
    }

def parse_metadata_from_file(filepath):
    """Extract metadata from document file"""
    metadata = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find metadata section
        if "DOCUMENT METADATA" in content:
            lines = content.split('\n')
            in_metadata = False
            for line in lines:
                if "DOCUMENT METADATA" in line:
                    in_metadata = True
                    continue
                if in_metadata and ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if key and value:
                            metadata[key] = value
    except Exception as e:
        print(f"  ⚠️  Error parsing metadata from {filepath}: {e}")
    
    return metadata

def check_seeded_error(employee_id, filename, seeded_errors):
    """Check if this document should have a seeded error"""
    emp_id = employee_id.split('_')[0] if '_' in employee_id else employee_id
    
    if emp_id in seeded_errors:
        for doc_key, error_type in seeded_errors[emp_id].items():
            if doc_key in filename:
                return error_type
    return None

# ─────────────────────────────────────────────────────────────────────────────
# REPOSITORY AUTH & EXISTENCE CHECK
# ─────────────────────────────────────────────────────────────────────────────

def load_mcp_config():
    """Load Basic Auth connection config from .bob/mcp.json."""
    mcp_path = Path('.bob/mcp.json')
    if not mcp_path.exists():
        return None
    try:
        env = json.loads(mcp_path.read_text())['mcpServers']['core-cs-mcp-server']['env']
        return {
            'SERVER_URL':   env['SERVER_URL'],
            'OBJECT_STORE': env['OBJECT_STORE'],
            'USERNAME':     env['USERNAME'],
            'PASSWORD':     env['PASSWORD'],
        }
    except Exception:
        return None


def fetch_existing_doc_names(cfg, folder_path):
    """
    Return a set of document names already filed under folder_path in the
    repository. Matches the stem of local .txt filenames. Returns empty set
    on any error (folder not found, network issue, etc.).
    """
    query = """
    query($repo: String!, $folder: String!) {
        folder(repositoryIdentifier: $repo, identifier: $folder) {
            containedDocuments {
                documents {
                    name
                }
            }
        }
    }
    """
    try:
        resp = requests.post(
            cfg['SERVER_URL'],
            json={'query': query, 'variables': {'repo': cfg['OBJECT_STORE'], 'folder': folder_path}},
            auth=(cfg['USERNAME'], cfg['PASSWORD']),
            headers={'Content-Type': 'application/json'},
            verify=False,
            timeout=15,
        )
        data = resp.json()
        docs = (data.get('data') or {}).get('folder') or {}
        contained = (docs.get('containedDocuments') or {}).get('documents') or []
        return {d['name'] for d in contained if d.get('name')}
    except Exception:
        return set()


def get_employee_folders(base_source_path):
    """Get list of employee folders from source directory"""
    source_path = Path(base_source_path)
    if not source_path.exists():
        print(f"❌ Source directory {base_source_path} not found!")
        return []
    
    employees = []
    for item in source_path.iterdir():
        if item.is_dir():
            employees.append(item.name)
    
    return sorted(employees)

def generate_upload_plan(lastname):
    """Generate upload plan containing only documents not yet in the repository.

    For each employee folder, queries the repository for already-uploaded
    document names and excludes them from the plan. Folders are only included
    in the command list when at least one document in that category still needs
    uploading.
    """
    base_source_path = f"HR_{lastname}"
    base_target_path = f"/BOB_LAB/{lastname}"

    prefix = lastname[:3].upper()
    seeded_errors = get_seeded_errors(prefix)

    # ── connect to repository ─────────────────────────────────────────────────
    cfg = load_mcp_config()
    if cfg:
        print("  🔑 Repository connection established — checking existing documents.")
    else:
        print("  ⚠️  .bob/mcp.json not found. All documents will be included.")

    plan = {
        "namespace": lastname,
        "prefix": prefix,
        "base_target_path": base_target_path,
        "employees": [],
        "skipped_employees": [],
    }

    employees = get_employee_folders(base_source_path)
    total_docs = 0
    skipped_docs = 0
    seeded_count = 0

    for employee_name in employees:
        employee_id = employee_name.split('_')[0]
        employee_data = {
            "name": employee_name,
            "id": employee_id,
            "folders": [],
            "documents": [],
            "skipped_documents": [],
        }

        for category in CATEGORIES:
            category_path = Path(base_source_path) / employee_name / category
            if not category_path.exists():
                continue

            # Fetch document names already in this repository folder
            repo_folder = f"{base_target_path}/{employee_name}/{category}"
            existing_names = set()
            if cfg:
                existing_names = fetch_existing_doc_names(cfg, repo_folder)

            new_docs = []
            for doc_file in sorted(category_path.glob("*.txt")):
                # Repository name is the stem (filename without .txt extension)
                doc_name = doc_file.stem
                if doc_name in existing_names:
                    employee_data["skipped_documents"].append({
                        "filename": doc_file.name,
                        "reason": "Already exists in repository",
                    })
                    skipped_docs += 1
                    continue

                metadata = parse_metadata_from_file(doc_file)
                seeded_error = check_seeded_error(employee_id, doc_file.name, seeded_errors)
                new_docs.append({
                    "filename": doc_file.name,
                    "source_path": str(doc_file),
                    "target_folder": repo_folder,
                    "metadata": metadata,
                    "seeded_error": seeded_error,
                    "is_seeded": seeded_error is not None,
                })
                total_docs += 1
                if seeded_error:
                    seeded_count += 1

            if new_docs:
                # Only include the folder command when there are docs to upload into it
                employee_data["folders"].append({
                    "name": category,
                    "path": repo_folder,
                })
                employee_data["documents"].extend(new_docs)

        # Only include employee folder command when at least one sub-folder needs creating
        if employee_data["folders"]:
            employee_data["folders"].insert(0, {
                "name": employee_name,
                "path": f"{base_target_path}/{employee_name}",
            })

        if employee_data["documents"] or employee_data["skipped_documents"]:
            plan["employees"].append(employee_data)

    plan["total_documents"] = total_docs
    plan["skipped_documents"] = skipped_docs
    plan["seeded_errors"] = seeded_count

    return plan

def print_upload_plan(plan):
    """Print the upload plan for review"""
    print("\n" + "=" * 70)
    print(f"UPLOAD PLAN FOR {plan['namespace']}")
    print("=" * 70)
    print(f"Target Path: {plan['base_target_path']}")
    print(f"Documents to upload : {plan['total_documents']}")
    print(f"Already in repo     : {plan.get('skipped_documents', 0)}")
    print(f"Seeded Errors       : {plan['seeded_errors']}")
    print()

    for emp in plan['employees']:
        to_upload = len(emp['documents'])
        skipped   = len(emp.get('skipped_documents', []))
        print(f"\n📁 {emp['name']} ({emp['id']})")
        print(f"   To upload : {to_upload}   Already in repo : {skipped}")

        seeded_docs = [d for d in emp['documents'] if d['is_seeded']]
        if seeded_docs:
            print(f"   ⚠️  Seeded Errors: {len(seeded_docs)}")
            for doc in seeded_docs:
                print(f"      - {doc['filename']}: {doc['seeded_error']}")

def generate_mcp_commands(plan):
    """Generate MCP commands for Bob to execute"""
    commands = []
    base_target_path = plan['base_target_path']
    
    # Commands to create employee folders and subfolders
    for emp in plan['employees']:
        # Create employee folder
        commands.append({
            "type": "create_folder",
            "employee": emp['name'],
            "path": f"{base_target_path}/{emp['name']}"
        })
        
        # Create category subfolders
        for folder in emp['folders']:
            commands.append({
                "type": "create_folder",
                "employee": emp['name'],
                "category": folder['name'],
                "path": folder['path']
            })
    
    # Commands to upload documents
    for emp in plan['employees']:
        for doc in emp['documents']:
            cmd = {
                "type": "upload_document",
                "employee": emp['name'],
                "filename": doc['filename'],
                "source_path": doc['source_path'],
                "target_folder": doc['target_folder'],
                "metadata": doc['metadata'],
                "seeded_error": doc['seeded_error']
            }
            commands.append(cmd)
    
    return commands


def main():
    parser = argparse.ArgumentParser(
        description="Generate bulk upload plan for HR documents to FileNet repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bulk_upload_employees.py --user CIGGAAR
  python bulk_upload_employees.py --user DUPONT
        """
    )
    parser.add_argument(
        "--user",
        type=str,
        required=True,
        metavar="LASTNAME",
        help="Your last name, used as the lab namespace (e.g., CIGGAAR, DUPONT)"
    )

    args = parser.parse_args()
    lastname = args.user.upper().strip()

    print("=" * 70)
    print(f"BULK UPLOAD PREPARATION FOR {lastname}")
    print("=" * 70)

    plan = generate_upload_plan(lastname)

    print_upload_plan(plan)

    commands = generate_mcp_commands(plan)

    plan_filename = f"upload_plan_{lastname.lower()}.json"
    commands_filename = f"upload_commands_{lastname.lower()}.json"

    with open(plan_filename, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Upload plan saved to {plan_filename}")

    with open(commands_filename, 'w', encoding='utf-8') as f:
        json.dump(commands, f, indent=2, ensure_ascii=False)
    print(f"✅ Upload commands saved to {commands_filename}")

    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print(f"1. Review the upload plan in upload_plan_{lastname.lower()}.json")
    print(f"2. Bob will execute the commands from upload_commands_{lastname.lower()}.json")
    print("3. The script handles all seeded misclassifications automatically")
    print(f"4. Total operations: {len(commands)} (folders + documents)")
    if plan.get('skipped_documents', 0) > 0:
        print(f"5. Skipped {plan['skipped_documents']} document(s) already in repository")
    print()
    print("Ready to proceed with upload!")
    print("=" * 70)

if __name__ == "__main__":
    main()

# Made with Bob

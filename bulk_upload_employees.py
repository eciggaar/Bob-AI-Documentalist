#!/usr/bin/env python3
"""
Bulk upload script for HR documents to FileNet repository.
This script uploads all documents for a specified namespace with proper metadata handling.
Handles the 5 seeded misclassifications for Lab 3 training.

Usage:
    python bulk_upload_employees.py --user CIGGAAR
    python bulk_upload_employees.py --user DUPONT
"""

import os
import sys
import json
import re
import argparse
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

def create_mcp_command(action, **kwargs):
    """Create MCP command for Bob to execute"""
    return {
        "action": action,
        "params": kwargs
    }

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

def generate_upload_plan(lastname, skip_first_employee=True):
    """Generate complete upload plan with all documents and metadata
    
    Args:
        lastname: The namespace/lastname for this upload
        skip_first_employee: If True, skip {PREFIX}001 (already processed)
    """
    base_source_path = f"HR_{lastname}"
    base_target_path = f"/BOB_LAB/{lastname}"
    
    # Generate seeded errors based on namespace prefix (first 3 uppercase chars)
    prefix = lastname[:3].upper()
    seeded_errors = get_seeded_errors(prefix)
    
    plan = {
        "namespace": lastname,
        "prefix": prefix,
        "base_target_path": base_target_path,
        "employees": [],
        "skipped_employees": []
    }
    
    employees = get_employee_folders(base_source_path)
    total_docs = 0
    seeded_count = 0
    
    for employee_name in employees:
        # Skip first employee if already processed (e.g., CIG001, DUP001, etc.)
        if skip_first_employee and employee_name.startswith(f"{prefix}001"):
            plan["skipped_employees"].append({
                "name": employee_name,
                "reason": "Already processed - folders created and first document uploaded"
            })
            continue
        employee_id = employee_name.split('_')[0]
        employee_data = {
            "name": employee_name,
            "id": employee_id,
            "folders": [],
            "documents": []
        }
        
        # Add category folders
        for category in CATEGORIES:
            employee_data["folders"].append({
                "name": category,
                "path": f"{base_target_path}/{employee_name}/{category}"
            })
        
        # Process documents in each category
        for category in CATEGORIES:
            category_path = Path(base_source_path) / employee_name / category
            if not category_path.exists():
                continue
            
            for doc_file in category_path.glob("*.txt"):
                metadata = parse_metadata_from_file(doc_file)
                seeded_error = check_seeded_error(employee_id, doc_file.name, seeded_errors)
                
                doc_info = {
                    "filename": doc_file.name,
                    "source_path": str(doc_file),
                    "target_folder": f"{base_target_path}/{employee_name}/{category}",
                    "metadata": metadata,
                    "seeded_error": seeded_error,
                    "is_seeded": seeded_error is not None
                }
                
                employee_data["documents"].append(doc_info)
                total_docs += 1
                if seeded_error:
                    seeded_count += 1
        
        plan["employees"].append(employee_data)
    
    plan["total_documents"] = total_docs
    plan["seeded_errors"] = seeded_count
    
    return plan

def print_upload_plan(plan):
    """Print the upload plan for review"""
    print("\n" + "=" * 70)
    print(f"UPLOAD PLAN FOR {plan['namespace']}")
    print("=" * 70)
    print(f"Target Path: {plan['base_target_path']}")
    print(f"Total Documents: {plan['total_documents']}")
    print(f"Seeded Errors: {plan['seeded_errors']}")
    print()
    
    for emp in plan['employees']:
        print(f"\n📁 {emp['name']} ({emp['id']})")
        print(f"   Documents: {len(emp['documents'])}")
        
        # Show seeded errors for this employee
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
      Generate upload plan for CIGGAAR namespace (skips CIG001 if already processed)
  
  python bulk_upload_employees.py --user DUPONT
      Generate upload plan for DUPONT namespace
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
    
    # Set configuration based on user input
    lastname = args.user.upper().strip()
    
    print("=" * 70)
    print(f"BULK UPLOAD PREPARATION FOR {lastname}")
    print("=" * 70)
    
    # Generate upload plan (skip first employee if CIG001)
    plan = generate_upload_plan(lastname, skip_first_employee=True)
    
    # Print plan
    print_upload_plan(plan)
    
    # Generate MCP commands
    commands = generate_mcp_commands(plan)
    
    # Save plan with namespace in filename
    plan_filename = f"upload_plan_{lastname.lower()}.json"
    commands_filename = f"upload_commands_{lastname.lower()}.json"
    
    with open(plan_filename, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Upload plan saved to {plan_filename}")
    
    # Save commands
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
    if plan.get('skipped_employees'):
        print(f"5. Skipped {len(plan['skipped_employees'])} employee(s) already processed")
    print()
    print("Ready to proceed with upload!")
    print("=" * 70)

if __name__ == "__main__":
    main()

# Made with Bob

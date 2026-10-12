#!/usr/bin/env python3
"""
Execute bulk upload to FileNet repository using MCP server GraphQL API.
This script reads the upload plan and executes all operations efficiently.

Usage:
    python execute_bulk_upload.py --user CIGGAAR
"""

import argparse
import json
import sys
import uuid
import warnings
from pathlib import Path

import requests
import urllib3

warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

def load_mcp_config():
    """Load Basic Auth configuration from .bob/mcp.json."""
    mcp_config_path = Path('.bob/mcp.json')

    if not mcp_config_path.exists():
        print("❌ Error: .bob/mcp.json not found")
        print("Please ensure you're running from the project root directory")
        sys.exit(1)

    try:
        with open(mcp_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        env = config['mcpServers']['core-cs-mcp-server']['env']

        return {
            'SERVER_URL':   env['SERVER_URL'],
            'OBJECT_STORE': env['OBJECT_STORE'],
            'USERNAME':     env['USERNAME'],
            'PASSWORD':     env['PASSWORD'],
        }
    except Exception as e:
        print(f"❌ Error loading MCP config: {e}")
        sys.exit(1)


# Load configuration at module level
MCP_CONFIG = load_mcp_config()


def create_graphql_session():
    """Create authenticated session for GraphQL using HTTP Basic Auth."""
    session = requests.Session()
    session.auth = (MCP_CONFIG['USERNAME'], MCP_CONFIG['PASSWORD'])
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    })
    session.verify = False
    return session

def create_folder_graphql(session, folder_name, parent_path):
    """Create folder using GraphQL mutation"""
    mutation = """
    mutation createFolder($repo:String!, $id:ID!, $className:String, $folderProperties:FolderPropertiesInput!) {
        createFolder(
            repositoryIdentifier: $repo,
            classIdentifier: $className,
            id: $id
            folderProperties: $folderProperties
        ) {
            id
            className
        }
    }
    """
    
    folder_id = "{" + str(uuid.uuid4()).upper() + "}"
    
    variables = {
        "repo": MCP_CONFIG['OBJECT_STORE'],
        "id": folder_id,
        "className": "Folder",
        "folderProperties": {
            "name": folder_name,
            "parent": {"identifier": parent_path}
        }
    }
    
    try:
        response = session.post(MCP_CONFIG['SERVER_URL'], json={"query": mutation, "variables": variables})
        result = response.json()
        
        if 'errors' in result:
            error_msg = str(result['errors'])
            if 'uniqueness' in error_msg.lower() or 'not unique' in error_msg.lower():
                print(f"  ℹ️  Folder already exists: {folder_name}")
                return "exists"
            print(f"  ❌ Error: {result['errors'][0].get('message', 'Unknown error')[:100]}")
            return "error"
        
        print(f"  ✅ Created: {folder_name}")
        return "created"
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        return "error"

def upload_document_graphql(session, doc_info):
    """Upload document using GraphQL mutation with base64-encoded content"""
    
    metadata = doc_info['metadata']
    seeded_error = doc_info.get('seeded_error')
    
    # Determine class and properties based on seeded error
    if seeded_error == "Document":
        class_id = "Document"
        properties = []  # Base Document class with no HR properties
    elif seeded_error == "Contract":
        class_id = "Contract"
        properties = []  # Wrong domain class
    else:
        class_id = "HRDocument"
        properties = []
        
        # Build properties list - format: {PropertyName: "value"}
        if seeded_error == "wrong_employee_id":
            properties.append({"EmployeeID": "000000"})
        elif seeded_error != "missing_properties":
            if 'EmployeeID' in metadata:
                properties.append({"EmployeeID": metadata['EmployeeID']})
        
        # Add other properties (skip for missing_properties error)
        if 'FirstName' in metadata:
            properties.append({"FirstName": metadata['FirstName']})
        if 'LastName' in metadata:
            properties.append({"LastName": metadata['LastName']})
        
        if seeded_error != "missing_properties":
            if 'DocType' in metadata:
                properties.append({"DocType": metadata['DocType']})
            if 'Department' in metadata:
                properties.append({"Department": metadata['Department']})
        
        if 'JobRole' in metadata:
            properties.append({"JobRole": metadata['JobRole']})
        if 'Company' in metadata:
            properties.append({"Company": metadata['Company']})
        if 'CompanyCode' in metadata:
            properties.append({"CompanyCode": metadata['CompanyCode']})
        if 'CostCenter' in metadata:
            properties.append({"CostCenter": metadata['CostCenter']})
        if 'Location' in metadata:
            properties.append({"Location": metadata['Location']})
        if 'StartDate' in metadata:
            date_str = metadata['StartDate']
            if 'T' not in date_str:
                date_str = f"{date_str}T00:00:00.000Z"
            properties.append({"StartDate": date_str})
    
    # Build properties array for inline inclusion
    props_array = "[]"
    if properties:
        props_list = []
        for prop in properties:
            prop_str = "{"
            items = []
            for key, value in prop.items():
                if isinstance(value, str):
                    # Escape quotes and backslashes
                    escaped_value = value.replace('\\', '\\\\').replace('"', '\\"')
                    items.append(f'{key}:"{escaped_value}"')
                else:
                    items.append(f'{key}:{value}')
            prop_str += ", ".join(items) + "}"
            props_list.append(prop_str)
        props_array = "[" + ", ".join(props_list) + "]"
    
    try:
        # Read file content as binary
        with open(doc_info['source_path'], 'rb') as f:
            file_content = f.read()

        # Build mutation matching the TypeScript example
        mutation = """
        mutation ($contvar: String) {
            createDocument(
                repositoryIdentifier: "%s"
                classIdentifier: "%s"
                fileInFolderIdentifier: "%s"
                checkinAction: {}
                documentProperties: {
                    name: "%s"
                    properties: %s
                    content: $contvar
                }
            ) {
                id
                name
            }
        }
        """ % (
            MCP_CONFIG['OBJECT_STORE'],
            class_id,
            doc_info['target_folder'],
            doc_info['filename'].replace('"', '\\"'),
            props_array
        )

        # Build FormData exactly like the TypeScript example
        operation = {
            "query": mutation,
            "variables": {"contvar": None}
        }
        
        # Create multipart form data with operations and file content
        files = {
            'operations': (None, json.dumps(operation), 'application/json'),
            'contvar': (doc_info['filename'], file_content, 'text/plain')
        }
        
        response = requests.post(
            MCP_CONFIG['SERVER_URL'],
            files=files,
            auth=(MCP_CONFIG['USERNAME'], MCP_CONFIG['PASSWORD']),
            verify=False,
        )
        result = response.json()
        
        if 'errors' in result:
            error_msg = result['errors'][0].get('message', 'Unknown error')
            print(f"  ❌ Error: {error_msg[:150]}")
            return False
        
        status = "✅"
        if seeded_error:
            status = f"⚠️  SEEDED ({seeded_error})"
        print(f"  {status} Uploaded: {doc_info['filename']}")
        return True
        
    except Exception as e:
        print(f"  ❌ Exception: {str(e)[:100]}")
        return False

def execute_upload_plan(lastname):
    """Execute the complete upload plan"""
    
    plan_file = f'upload_plan_{lastname.lower()}.json'
    commands_file = f'upload_commands_{lastname.lower()}.json'
    
    # Load files
    try:
        with open(plan_file, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        with open(commands_file, 'r', encoding='utf-8') as f:
            commands = json.load(f)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print(f"Please run: python .bob/skills/hr-document-upload/scripts/bulk_upload_employees.py --user {lastname}")
        return False
    
    print("\n" + "=" * 70)
    print(f"EXECUTING BULK UPLOAD FOR {plan['namespace']}")
    print("=" * 70)
    print(f"Total Documents: {plan['total_documents']}")
    print(f"Seeded Errors: {plan['seeded_errors']}")
    print(f"Total Operations: {len(commands)}")
    
    if plan.get('skipped_employees'):
        print(f"Skipped Employees: {len(plan['skipped_employees'])}")
        for skipped in plan['skipped_employees']:
            print(f"  - {skipped['name']}: {skipped['reason']}")
    print()
    
    session = create_graphql_session()
    
    folders_created = 0
    folders_existing = 0
    documents_uploaded = 0
    errors = 0
    seeded_count = 0
    failed_folders = set()
    emp_stats = {emp['name']: {"uploaded": 0, "errors": 0} for emp in plan['employees']}
    
    for i, cmd in enumerate(commands, 1):
        print(f"[{i}/{len(commands)}] ", end="")
        
        if cmd['type'] == 'create_folder':
            path_parts = cmd['path'].split('/')
            folder_name = path_parts[-1]
            parent_path = '/'.join(path_parts[:-1])
            if not parent_path:
                parent_path = '/'
            
            print(f"Creating folder: {folder_name} (parent: {parent_path})")
            status = create_folder_graphql(session, folder_name, parent_path)
            if status == "created":
                folders_created += 1
            elif status == "exists":
                folders_existing += 1
            else:
                failed_folders.add(cmd['path'])
                errors += 1
        
        elif cmd['type'] == 'upload_document':
            target_folder = cmd['target_folder']
            emp_name = cmd.get('employee')
            # Check if target folder failed creation
            if any(target_folder == ff or target_folder.startswith(ff + '/') for ff in failed_folders):
                print(f"  ❌ Skipping: target folder failed creation ({target_folder})")
                errors += 1
                if emp_name in emp_stats:
                    emp_stats[emp_name]["errors"] += 1
                continue

            print(f"Uploading: {cmd['filename']}")
            if upload_document_graphql(session, cmd):
                documents_uploaded += 1
                if emp_name in emp_stats:
                    emp_stats[emp_name]["uploaded"] += 1
                if cmd.get('seeded_error'):
                    seeded_count += 1
            else:
                errors += 1
                if emp_name in emp_stats:
                    emp_stats[emp_name]["errors"] += 1
    
    print("\n" + "=" * 70)
    print("UPLOAD COMPLETE")
    print("=" * 70)
    print(f"✅ Folders created: {folders_created} ({folders_existing} already existed)")
    print(f"✅ Documents uploaded: {documents_uploaded}")
    if seeded_count > 0:
        print(f"⚠️  Seeded errors applied: {seeded_count}")
    if errors > 0:
        print(f"❌ Errors encountered: {errors}")
    print("=" * 70)

    # Save execution results
    result_summary = {
        "namespace": plan['namespace'],
        "folders_created": folders_created,
        "folders_existing": folders_existing,
        "documents_uploaded": documents_uploaded,
        "seeded_count": seeded_count,
        "errors": errors,
        "employee_stats": emp_stats
    }
    result_filename = f"upload_result_{lastname.lower()}.json"
    try:
        with open(result_filename, 'w', encoding='utf-8') as f:
            json.dump(result_summary, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  Warning: could not write execution summary {result_filename}: {e}", file=sys.stderr)
    
    return errors == 0

def main():
    parser = argparse.ArgumentParser(
        description="Execute bulk upload of HR documents to FileNet repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python execute_bulk_upload.py --user CIGGAAR
      Execute upload plan for CIGGAAR namespace
        """
    )
    parser.add_argument(
        "--user",
        type=str,
        required=True,
        metavar="LASTNAME",
        help="Your last name / namespace (e.g., CIGGAAR, DUPONT)"
    )
    
    args = parser.parse_args()
    lastname = args.user.upper().strip()
    
    success = execute_upload_plan(lastname)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

# Made with Bob

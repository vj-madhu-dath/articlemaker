#!/usr/bin/env python3
"""
Fetch workflow from n8n instance using N8NLOCAL API key.
Run locally: python3 fetch_workflow.py <workflow-name-or-id> <output-file>
"""

import os
import sys
import json
import requests

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 fetch_workflow.py <workflow-name-or-id> <output-file.json>")
        print("       N8NLOCAL env var must be set with n8n API key")
        sys.exit(1)

    workflow_identifier = sys.argv[1]
    output_file = sys.argv[2]

    api_key = os.environ.get('N8NLOCAL')
    if not api_key:
        print("Error: N8NLOCAL environment variable not set")
        sys.exit(1)

    # n8n API base URL (adjust if different)
    base_url = os.environ.get('N8N_BASE_URL', 'http://localhost:5678')
    headers = {'X-N8N-API-KEY': api_key}

    try:
        # First, find workflow by name if it's not an ID
        if not workflow_identifier.startswith('workflow:'):
            # Search for workflow by name
            resp = requests.get(f'{base_url}/api/v1/workflows', headers=headers)
            resp.raise_for_status()
            workflows = resp.json().get('data', [])
            
            match = None
            for wf in workflows:
                if wf.get('name') == workflow_identifier:
                    match = wf
                    break
            
            if not match:
                print(f"Workflow '{workflow_identifier}' not found")
                print("Available workflows:")
                for wf in workflows:
                    print(f"  - {wf.get('name')} (id: {wf.get('id')})")
                sys.exit(1)
            
            workflow_id = match['id']
        else:
            workflow_id = workflow_identifier

        # Fetch full workflow
        resp = requests.get(f'{base_url}/api/v1/workflows/{workflow_id}', headers=headers)
        resp.raise_for_status()
        workflow = resp.json()

        # Save
        with open(output_file, 'w') as f:
            json.dump(workflow, f, indent=2)
        
        print(f"✅ Fetched workflow '{workflow.get('name')}' (id: {workflow.get('id')})")
        print(f"   Saved to: {output_file}")

    except requests.exceptions.RequestException as e:
        print(f"Error calling n8n API: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
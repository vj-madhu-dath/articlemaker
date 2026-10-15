#!/usr/bin/env python3
"""
n8n Workflow Validator - Checks workflow against best practices and critic rules.
Run: python3 validate_workflow.py articles/<name>/workflow.json
"""

import json
import sys
import os
from typing import List, Dict, Any

class WorkflowValidator:
    def __init__(self, workflow_path: str):
        self.workflow_path = workflow_path
        with open(workflow_path, 'r') as f:
            self.workflow = json.load(f)
        self.nodes = {n['name']: n for n in self.workflow.get('nodes', [])}
        self.connections = self.workflow.get('connections', {})
        self.errors = []
        self.warnings = []
        self.info = []

    def add_error(self, msg: str):
        self.errors.append(f"❌ {msg}")

    def add_warning(self, msg: str):
        self.warnings.append(f"⚠️  {msg}")

    def add_info(self, msg: str):
        self.info.append(f"ℹ️  {msg}")

    def get_node_type(self, name: str) -> str:
        return self.nodes.get(name, {}).get('type', '')

    def get_node_params(self, name: str) -> dict:
        return self.nodes.get(name, {}).get('parameters', {})

    def find_nodes_by_type(self, type_substring: str) -> List[str]:
        return [name for name, node in self.nodes.items() if type_substring in node.get('type', '')]

    def validate(self):
        print(f"\n🔍 Validating: {self.workflow_path}")
        print("=" * 60)

        self._check_split_out()
        self._check_merge_for_diffing()
        self._check_sort_before_delete()
        self._check_field_mapping()
        self._check_code_nodes()
        self._check_credentials()
        self._check_connections()
        self._check_schedule_vs_manual()
        self._check_google_sheets_ops()

        self._print_results()

    def _check_split_out(self):
        """Rule 1: Must have Item Lists (Split Out) node for arrays like search_results"""
        split_nodes = self.find_nodes_by_type('itemLists')
        if not split_nodes:
            self.add_error("Missing Item Lists (Split Out) node - needed to split arrays like search_results")
        else:
            for name in split_nodes:
                params = self.get_node_params(name)
                field = params.get('fieldToSplitOut', '')
                if field:
                    self.add_info(f"Split Out node '{name}' splits field: {field}")
                else:
                    self.add_warning(f"Split Out node '{name}' has no fieldToSplitOut configured")

    def _check_merge_for_diffing(self):
        """Rule 2: Should use Merge node (keepNonMatches) for finding stale rows"""
        merge_nodes = self.find_nodes_by_type('merge')
        has_keep_non_matches = False
        for name in merge_nodes:
            params = self.get_node_params(name)
            if params.get('joinMode') == 'keepNonMatches':
                has_keep_non_matches = True
                self.add_info(f"Merge node '{name}' uses keepNonMatches (correct for stale detection)")
            elif params.get('mode') == 'combine':
                self.add_warning(f"Merge node '{name}' uses combine mode - consider keepNonMatches for stale detection")
        
        # Check if there's a delete operation that would need stale detection
        delete_nodes = self.find_nodes_by_type('googleSheets')
        has_delete = False
        for name in delete_nodes:
            params = self.get_node_params(name)
            if params.get('operation') == 'delete':
                has_delete = True
                break
        
        if has_delete and not has_keep_non_matches:
            self.add_error("Has Delete operation but no Merge (keepNonMatches) for stale row detection")

    def _check_sort_before_delete(self):
        """Rule 3: Must Sort by row_number descending before Delete"""
        sort_nodes = self.find_nodes_by_type('sort')
        delete_nodes = self.find_nodes_by_type('googleSheets')
        
        has_delete = any(self.get_node_params(n).get('operation') == 'delete' for n in delete_nodes)
        
        if has_delete and not sort_nodes:
            self.add_error("Has Delete operation but no Sort node - must sort by row_number descending before delete")
        elif sort_nodes:
            for name in sort_nodes:
                self.add_info(f"Sort node '{name}' found - verify it sorts by row_number descending")

    def _check_field_mapping(self):
        """Rule 4: Should map snake_case API fields to Title Case before Sheets"""
        set_nodes = self.find_nodes_by_type('set')
        sheets_nodes = self.find_nodes_by_type('googleSheets')
        
        has_upsert = any(
            self.get_node_params(n).get('operation') in ('appendOrUpdate', 'upsert') 
            for n in sheets_nodes
        )
        
        if has_upsert and not set_nodes:
            self.add_warning("Has upsert/appendOrUpdate but no Set (Edit Fields) node for field mapping")
        
        for name in set_nodes:
            params = self.get_node_params(name)
            assignments = params.get('assignments', {}).get('assignments', [])
            if assignments:
                mapped_fields = [a.get('name', '') for a in assignments]
                snake_case = [f for f in mapped_fields if '_' in f and f.islower()]
                if snake_case:
                    self.add_warning(f"Set node '{name}' maps snake_case fields: {snake_case} - consider Title Case")
                else:
                    self.add_info(f"Set node '{name}' maps {len(mapped_fields)} fields")

    def _check_code_nodes(self):
        """Rule 5: Avoid Code nodes where standard nodes work"""
        code_nodes = self.find_nodes_by_type('code')
        if code_nodes:
            for name in code_nodes:
                self.add_warning(f"Code node '{name}' found - consider replacing with standard nodes (Merge, Set, Filter, etc.)")

    def _check_credentials(self):
        """Check credential references"""
        for name, node in self.nodes.items():
            creds = node.get('credentials', {})
            for cred_type, cred_info in creds.items():
                cred_id = cred_info.get('id', '')
                cred_name = cred_info.get('name', '')
                if 'YOUR_CREDENTIAL' in str(cred_id) or 'YOUR_CREDENTIAL' in str(cred_name):
                    self.add_warning(f"Node '{name}' uses placeholder credential: {cred_type}")
                if 'YOUR_DOCUMENT_ID' in str(cred_info):
                    self.add_warning(f"Node '{name}' uses placeholder document ID")

    def _check_connections(self):
        """Basic connection validity"""
        for source_name, conns in self.connections.items():
            if source_name not in self.nodes:
                self.add_warning(f"Connection from unknown node: {source_name}")
            for conn_type, branches in conns.items():
                for branch in branches:
                    for conn in branch:
                        target = conn.get('node')
                        if target and target not in self.nodes:
                            self.add_error(f"Connection to unknown node: {target} (from {source_name})")

    def _check_schedule_vs_manual(self):
        """Check trigger type"""
        triggers = self.find_nodes_by_type('trigger')
        if not triggers:
            self.add_warning("No trigger node found")
        else:
            for name in triggers:
                ntype = self.get_node_type(name)
                if 'manualTrigger' in ntype:
                    self.add_info(f"Uses Manual Trigger: {name}")
                elif 'scheduleTrigger' in ntype:
                    self.add_info(f"Uses Schedule Trigger: {name}")

    def _check_google_sheets_ops(self):
        """Check Google Sheets operations make sense"""
        sheets_nodes = self.find_nodes_by_type('googleSheets')
        ops = {}
        for name in sheets_nodes:
            params = self.get_node_params(name)
            op = params.get('operation', 'unknown')
            sheet = params.get('sheetName', '')
            ops.setdefault(op, []).append((name, sheet))
        
        for op, nodes in ops.items():
            for name, sheet in nodes:
                self.add_info(f"Google Sheets [{op}]: {name} -> sheet: {sheet}")

    def _print_results(self):
        print(f"\n📋 RESULTS:")
        if self.errors:
            print(f"\n  ERRORS ({len(self.errors)}):")
            for e in self.errors:
                print(f"    {e}")
        if self.warnings:
            print(f"\n  WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"    {w}")
        if self.info:
            print(f"\n  INFO ({len(self.info)}):")
            for i in self.info:
                print(f"    {i}")
        
        print(f"\n  Summary: {len(self.errors)} errors, {len(self.warnings)} warnings, {len(self.info)} info")
        print("=" * 60)

        if self.errors:
            sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_workflow.py <workflow.json>")
        sys.exit(1)
    
    workflow_path = sys.argv[1]
    if not os.path.exists(workflow_path):
        print(f"File not found: {workflow_path}")
        sys.exit(1)
    
    validator = WorkflowValidator(workflow_path)
    validator.validate()

if __name__ == '__main__':
    main()
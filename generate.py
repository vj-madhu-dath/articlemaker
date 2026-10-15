import json
import sys
import os
import argparse
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(ROOT_DIR, "templates")
ARTICLES_DIR = os.path.join(ROOT_DIR, "articles")

def generate_n8n_workflow(config):
    """Generates a skeleton n8n workflow JSON based on the config."""
    sh_config = config.get("scrapehero", {})
    
    # Extract keys from the sample JSON to map to Google Sheets
    sample_json = sh_config.get("api_json_output_sample", {})
    fields = list(sample_json.keys()) if isinstance(sample_json, dict) else []
    
    workflow = {
        "name": f"Automate {config['platform']} with ScrapeHero",
        "nodes": [
            {
                "parameters": {},
                "name": "Manual Trigger",
                "type": "n8n-nodes-base.manualTrigger",
                "typeVersion": 1,
                "position": [0, 0]
            },
            {
                "parameters": {
                    "operation": "getAll",
                    "documentId": "YOUR_DOCUMENT_ID",
                    "sheetName": "Queries"
                },
                "name": "Get Queries",
                "type": "n8n-nodes-base.googleSheets",
                "typeVersion": 4,
                "position": [200, 0]
            },
            {
                "parameters": {"options": {}},
                "name": "Loop Over Items",
                "type": "n8n-nodes-base.splitInBatches",
                "typeVersion": 3,
                "position": [400, 0]
            },
            {
                "parameters": sh_config.get("node_parameters", {}),
                "name": "ScrapeHero",
                "type": "n8n-nodes-scrapehero.scrapeHero", 
                "typeVersion": 1,
                "position": [600, 0],
                "credentials": {
                    "scrapeHeroApi": {
                        "id": "YOUR_CREDENTIAL_ID",
                        "name": "ScrapeHero account"
                    }
                }
            },
            {
                "parameters": {
                    "assignments": {
                        "assignments": [
                            {"id": i, "name": f, "value": f"{{{{ $json.{f} }}}}"} for i, f in enumerate(fields)
                        ]
                    }
                },
                "name": "Edit Fields",
                "type": "n8n-nodes-base.set",
                "typeVersion": 3,
                "position": [800, 0]
            },
            {
                "parameters": {
                    "operation": "appendOrUpdate",
                    "documentId": "YOUR_DOCUMENT_ID",
                    "sheetName": "Results",
                    "columns": {
                        "mappingMode": "defineBelow",
                        "value": {
                            f: f"{{{{ $json.{f} }}}}" for f in fields
                        },
                        "matchingColumns": [sh_config.get("unique_identifier", "id")]
                    }
                },
                "name": "Update Sheets",
                "type": "n8n-nodes-base.googleSheets",
                "typeVersion": 4,
                "position": [1000, 0]
            }
        ],
        "connections": {
            "Manual Trigger": {
                "main": [[{"node": "Get Queries", "type": "main", "index": 0}]]
            },
            "Get Queries": {
                "main": [[{"node": "Loop Over Items", "type": "main", "index": 0}]]
            },
            "Loop Over Items": {
                "main": [
                    [],
                    [{"node": "ScrapeHero", "type": "main", "index": 0}]
                ]
            },
            "ScrapeHero": {
                "main": [[{"node": "Edit Fields", "type": "main", "index": 0}]]
            },
            "Edit Fields": {
                "main": [[{"node": "Update Sheets", "type": "main", "index": 0}]]
            },
            "Update Sheets": {
                "main": [[{"node": "Loop Over Items", "type": "main", "index": 0}]]
            }
        },
        "active": False,
        "settings": {}
    }
    
    return workflow

def generate_article_prompt(config, workflow_json):
    """Generates the prompt for the LLM to write the article."""
    sh_config = config.get("scrapehero", {})
    
    # Summarize workflow nodes dynamically
    nodes = workflow_json.get("nodes", [])
    node_summaries = []
    for i, node in enumerate(nodes, 1):
        name = node.get("name", f"Node {i}")
        ntype = node.get("type", "unknown")
        params = node.get("parameters", {})
        node_summaries.append(f"{i}. **{name}** (`{ntype}`)\n   Parameters: {json.dumps(params)}")
    node_flow_text = "\n".join(node_summaries) if node_summaries else "Follow the workflow JSON attached."

    prompt = f"""
You are an expert technical content writer for the ScrapeHero blog.
Write a highly structured, instructional SEO article in a **tutorial style** based on the provided configuration and reference workflow.

### Tone & Style Guide
- **Practical Mentor:** Conversational, hands-on senior engineer walkthrough.
- **Pronoun Rules:**
  - Never use "we" in the tutorial, explanation, or overview sections. Use phrasing like "this guide shows", "this workflow uses", or imperative steps.
  - Never use "you will learn".
  - DO use "we" ONLY in the final CTA paragraph when referencing ScrapeHero's enterprise data services.
- **Tone & Language to Avoid:**
  - Avoid fluff, buzzwords, and academic lecturing.
  - Do NOT use: "not only... but also...", em dashes (—), "it's important to note", "delve", "robust", "seamless", "leverage", "unlock", "in today's...", "whether you're...", "in conclusion", "ultimately", "at the end of the day".
- **Instructional Steps:** Use imperative instructions with specific n8n UI actions (e.g., "Click the **plus icon** (+)", "Search for **[Node Name]**", "Under Action, select...", "Set parameter X to...").
- **Code & Expressions:** Wrap all n8n expressions in ```javascript ``` code blocks.
- **Screenshot Placeholders:** Include markdown image placeholders with descriptive alt text (`![Descriptive alt text](add-image-url)`) after each major configuration step.
- **Tables:** Use markdown tables for prerequisites, field mappings, and input data formats.
- **Reference Accuracy:** Reference the exact node names, types, and versions from the reference workflow JSON.

### Mandatory Article Structure
1.  **Title & Metadata:**
    - H1 Title: `# How to [Action/Goal] With n8n and ScrapeHero`
    - Bold metadata lines directly below H1 (do NOT use YAML `---` blocks):
      `**SEO title:** [Title with brackets or primary keyword]`
      `**Meta description:** [Active voice description under 160 characters]`
      `**Category:** ScrapeHero Cloud Resources > n8n`
2.  **Table of Contents:**
    - Heading: `#### Table of contents`
    - Flat bulleted list linking only to the top-level H2 (`##`) sections. Do not list H3 step subsections.
3.  **Introduction:** Exactly two paragraphs.
    - Paragraph 1: Business problem + primary SEO keyword + automated solution overview.
    - Paragraph 2: Lead-in ("This tutorial shows how to build an n8n workflow that:") followed by a 4-point numbered list summarizing the pipeline.
4.  **Key Takeaways:**
    - Heading: `### Key Takeaways` immediately following the intro numbered list.
    - 5-6 practical takeaway bullet points.
5.  **Before You Begin:**
    - Prerequisites list/table (n8n instance, credentials, input data source, ScrapeHero API key).
    - Sample markdown tables showing the required Google Sheet or database structure (headers and sample row). If using separate tabs (e.g. input queries vs output results), provide distinct tables for both tabs.
6.  **Workflow Construction (Dynamic Multi-Phase Grouping):**
    Organize the steps based on the workflow's architecture:
    - **For Linear Pipelines (Extract -> Transform -> Load)**: Organize into 4 logical H2 sections:
      - **Phase 1: `## Create the Workflow`** (Trigger, Reading input data, Loop node, ScrapeHero node with Pin Data tip).
        * For ScrapeHero node: Specify dedicated `n8n-nodes-scrapehero.scrapeHero` community node. Provide the standard 8-step credential setup:
          1. Go to app.scrapehero.com -> 2. Sign in -> 3. Profile icon -> 4. Open API Key -> 5. Copy key -> 6. Return to n8n -> 7. Paste key -> 8. Save credentials.
      - **Phase 2: `## [Transformation Phase]`** (Split Out, Edit Fields with markdown mapping table, Filter, Sort, in-step type parsing).
      - **Phase 3: `## [Destination Phase]`** (Append/Update, target mapping, matching keys, Execute Once).
      - **Phase 4: `## Test and Complete the Loop`** (Loopback wiring, test checklist).
    - **For Two-Way Sync / Diff Workflows (Extract -> Format -> Read Existing -> Merge -> Upsert -> Delete)**: Organize into 3 logical H2 sections:
      - **Phase 1: `## Create the Workflow`** (Trigger, Input Source, Loop, ScrapeHero node with 8-step credential walkthrough and Pin Data tip, Split Out, Edit Fields with markdown mapping table).
      - **Phase 2: `## [Compare & Sync Phase]`** (e.g., `## Compare and Update the Rankings` - Read Existing, Merge non-matches, compound-key upsert, bottom-up sort and delete).
      - **Phase 3: `## Test and Complete the Loop`** (Loopback connection, zero-match loop guardrail using Always Output Data + Filter, test checklist).

    *Nodes in this workflow to incorporate into these phases in execution order:*
{node_flow_text}
7.  **Business Benefits:**
    - Heading: `## What This Unlocks for Your Business`
    - Exactly 5 concrete business use cases formatted as bullet points with bold lead-ins, closing with a link to ScrapeHero Cloud / Marketplace.
8.  **Next Steps:**
    - Heading: `## Next Steps` (3-4 actionable extension ideas with direct action titles).
9.  **Wrapping Up:** Exactly three to four paragraphs:
    - Paragraph 1: Value of the automated DIY workflow.
    - Paragraph 2: CTA to get ScrapeHero API key + offer to build custom APIs.
    - Paragraph 3: Managed enterprise scraping service pitch using "we" (link to scrapehero.com).
10. **Frequently Asked Questions:** (Absolute last section).
    - Heading: `## Frequently Asked Questions`
    - 3-6 practical questions using `###` headers, addressing the reader with "you" (answering PAA and technical queries without filler).

### SEO Requirements
Please ensure the following SEO keywords, phrases, or guidelines are organically sprinkled throughout the headings and body text:

{config.get('seo_suggestions_content', '')}

### Reference n8n Workflow JSON
(Extract node names, types, parameters, connections from here)
```json
{json.dumps(workflow_json, indent=2)}
```

### Reference ScrapeHero API Output
(Use this to accurately describe the fields extracted)
```json
{json.dumps(sh_config.get('api_json_output_sample', {}), indent=2)}
```

Generate the Markdown article below:
"""
    return prompt.strip()

def slugify(name):
    """Convert a name to a URL-friendly slug."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = slug.strip('-')
    return slug

def cmd_new_article(args):
    """Scaffold a new article folder with config template and placeholder files."""
    article_slug = slugify(args.name)
    article_dir = os.path.join(ARTICLES_DIR, article_slug)
    
    if os.path.exists(article_dir):
        print(f"Error: Article '{article_slug}' already exists at {article_dir}")
        sys.exit(1)
    
    os.makedirs(article_dir, exist_ok=True)
    
    # Copy config template
    template_path = os.path.join(TEMPLATES_DIR, "config_template.json")
    config_path = os.path.join(article_dir, "config.json")
    shutil.copy2(template_path, config_path)
    
    # Copy SEO suggestions template to article folder (per-article)
    seo_template_path = os.path.join(TEMPLATES_DIR, "seo_suggestions.md")
    seo_article_path = os.path.join(article_dir, "seo_suggestions.md")
    if os.path.exists(seo_template_path):
        shutil.copy2(seo_template_path, seo_article_path)
    
    # Update config.json with article-specific paths
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    config["platform"] = args.platform or "Platform"
    config["automation_tool"] = args.tool or "n8n"
    config["storage"] = args.storage or "Google Sheets"
    config["scrapehero"]["api_json_output_file"] = "api_sample.json"
    config["scrapehero"]["unique_identifier"] = args.unique_id or "id"
    config["seo_suggestions_file"] = "seo_suggestions.md"
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    # Create placeholder api_sample.json
    api_sample_path = os.path.join(article_dir, "api_sample.json")
    placeholder_api = {
        "query": {"keyword": "example", "page": 1},
        "search_results": [
            {"id": "1", "name": "Example Product", "price": "99.99", "currency": "USD"}
        ]
    }
    with open(api_sample_path, 'w', encoding='utf-8') as f:
        json.dump(placeholder_api, f, indent=2)
    
    print(f"✅ Created new article: {article_dir}")
    print(f"   - config.json (edit this with your details)")
    print(f"   - api_sample.json (replace with real ScrapeHero API output)")
    print(f"\nNext steps:")
    print(f"  1. Edit {config_path} with your workflow details")
    print(f"  2. Replace {api_sample_path} with real API sample")
    print(f"  3. Run: python generate.py generate {config_path}")
    
    if args.generate:
        # Run generation immediately
        print(f"\n🔄 Running generation...")
        cmd_generate(argparse.Namespace(config_file=config_path, output_dir=article_dir))

def cmd_generate(args):
    """Generate workflow.json and article_prompt.txt from config."""
    config_file = args.config_file
    output_dir = getattr(args, 'output_dir', None)
    if not output_dir or output_dir == "output":
        config_dir = os.path.dirname(config_file)
        if config_dir and os.path.basename(config_file) == "config.json":
            output_dir = config_dir
        else:
            output_dir = output_dir or "output"
    
    if not os.path.exists(config_file):
        print(f"Error: Config file {config_file} not found.")
        sys.exit(1)
        
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    sh_config = config.get("scrapehero", {})
    api_file_path = sh_config.get("api_json_output_file")
    if api_file_path:
        if not os.path.isabs(api_file_path):
            api_file_path = os.path.normpath(os.path.join(os.path.dirname(config_file), api_file_path))
        
        if os.path.exists(api_file_path):
            with open(api_file_path, 'r', encoding='utf-8') as f:
                sh_config["api_json_output_sample"] = json.load(f)
        else:
            print(f"Warning: API JSON file {api_file_path} not found.")
            sh_config["api_json_output_sample"] = {}
            
    seo_file_path = config.get("seo_suggestions_file")
    if seo_file_path:
        if not os.path.isabs(seo_file_path):
            seo_file_path = os.path.normpath(os.path.join(os.path.dirname(config_file), seo_file_path))
        
        if os.path.exists(seo_file_path):
            with open(seo_file_path, 'r', encoding='utf-8') as f:
                config["seo_suggestions_content"] = f.read().strip()
        else:
            print(f"Warning: SEO file {seo_file_path} not found.")
            config["seo_suggestions_content"] = ""
            
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine workflow source
    workflow = None
    workflow_source = None
    
    if getattr(args, 'workflow', None) and os.path.exists(args.workflow):
        workflow_source = args.workflow
    else:
        candidates = [
            os.path.join(output_dir, "corrected_workflow.json"),
            os.path.join(os.path.dirname(config_file), "corrected_workflow.json")
        ]
        for c in candidates:
            if os.path.exists(c):
                workflow_source = c
                break
                
    if workflow_source:
        print(f"Using existing workflow: {workflow_source}")
        with open(workflow_source, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
    else:
        existing_wf = os.path.join(output_dir, "workflow.json")
        if getattr(args, 'prompt_only', False) and os.path.exists(existing_wf):
            print(f"Using existing workflow: {existing_wf}")
            with open(existing_wf, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
        else:
            workflow = generate_n8n_workflow(config)
            workflow_path = os.path.join(output_dir, "workflow.json")
            with open(workflow_path, 'w', encoding='utf-8') as f:
                json.dump(workflow, f, indent=2)
            print(f"Generated n8n workflow: {workflow_path}")
    
    # Generate Prompt
    prompt = generate_article_prompt(config, workflow)
    prompt_path = os.path.join(output_dir, "article_prompt.txt")
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f"Generated LLM prompt: {prompt_path}")
    print("\nTo generate the article, you can either:")
    print("1. Copy the contents of article_prompt.txt into ChatGPT/Gemini.")
    print("2. Ask your AI assistant to run it for you!")

def cmd_validate(args):
    """Validate workflow.json against critic rules."""
    workflow_file = args.workflow_file
    
    if not os.path.exists(workflow_file):
        print(f"Error: Workflow file {workflow_file} not found.")
        sys.exit(1)
    
    with open(workflow_file, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    nodes = {n['name']: n for n in workflow.get('nodes', [])}
    connections = workflow.get('connections', {})
    errors = []
    warnings = []
    info = []
    
    def find_nodes_by_type(type_substring):
        return [name for name, node in nodes.items() if type_substring in node.get('type', '')]
    
    def get_node_params(name):
        return nodes.get(name, {}).get('parameters', {})
    
    def get_node_type(name):
        return nodes.get(name, {}).get('type', '')
    
    # Rule 1: Split Out node
    split_nodes = find_nodes_by_type('itemLists')
    if not split_nodes:
        errors.append("Missing Item Lists (Split Out) node - needed to split arrays like search_results")
    else:
        for name in split_nodes:
            params = get_node_params(name)
            field = params.get('fieldToSplitOut', '')
            if field:
                info.append(f"Split Out node '{name}' splits field: {field}")
            else:
                warnings.append(f"Split Out node '{name}' has no fieldToSplitOut configured")
    
    # Rule 2: Merge keepNonMatches for stale detection
    merge_nodes = find_nodes_by_type('merge')
    has_keep_non_matches = False
    for name in merge_nodes:
        params = get_node_params(name)
        if params.get('joinMode') == 'keepNonMatches':
            has_keep_non_matches = True
            info.append(f"Merge node '{name}' uses keepNonMatches (correct for stale detection)")
        elif params.get('mode') == 'combine':
            warnings.append(f"Merge node '{name}' uses combine mode - consider keepNonMatches for stale detection")
    
    delete_nodes = find_nodes_by_type('googleSheets')
    has_delete = any(get_node_params(n).get('operation') == 'delete' for n in delete_nodes)
    if has_delete and not has_keep_non_matches:
        errors.append("Has Delete operation but no Merge (keepNonMatches) for stale row detection")
    
    # Rule 3: Sort before Delete
    sort_nodes = find_nodes_by_type('sort')
    if has_delete and not sort_nodes:
        errors.append("Has Delete operation but no Sort node - must sort by row_number descending before delete")
    elif sort_nodes:
        for name in sort_nodes:
            info.append(f"Sort node '{name}' found - verify it sorts by row_number descending")
    
    # Rule 4: Field mapping snake_case -> Title Case
    set_nodes = find_nodes_by_type('set')
    sheets_nodes = find_nodes_by_type('googleSheets')
    has_upsert = any(get_node_params(n).get('operation') in ('appendOrUpdate', 'upsert') for n in sheets_nodes)
    if has_upsert and not set_nodes:
        warnings.append("Has upsert/appendOrUpdate but no Set (Edit Fields) node for field mapping")
    for name in set_nodes:
        params = get_node_params(name)
        assignments = params.get('assignments', {}).get('assignments', [])
        if assignments:
            mapped_fields = [a.get('name', '') for a in assignments]
            snake_case = [f for f in mapped_fields if '_' in f and f.islower()]
            if snake_case:
                warnings.append(f"Set node '{name}' maps snake_case fields: {snake_case} - consider Title Case")
            else:
                info.append(f"Set node '{name}' maps {len(mapped_fields)} fields")
    
    # Rule 5: Avoid Code nodes
    code_nodes = find_nodes_by_type('code')
    if code_nodes:
        for name in code_nodes:
            warnings.append(f"Code node '{name}' found - consider replacing with standard nodes")
    
    # Credential placeholders
    for name, node in nodes.items():
        creds = node.get('credentials', {})
        for cred_type, cred_info in creds.items():
            cred_id = cred_info.get('id', '')
            cred_name = cred_info.get('name', '')
            if 'YOUR_CREDENTIAL' in str(cred_id) or 'YOUR_CREDENTIAL' in str(cred_name):
                warnings.append(f"Node '{name}' uses placeholder credential: {cred_type}")
            if 'YOUR_DOCUMENT_ID' in str(cred_info):
                warnings.append(f"Node '{name}' uses placeholder document ID")
    
    # Connection validity
    for source_name, conns in connections.items():
        if source_name not in nodes:
            warnings.append(f"Connection from unknown node: {source_name}")
        for conn_type, branches in conns.items():
            for branch in branches:
                for conn in branch:
                    target = conn.get('node')
                    if target and target not in nodes:
                        errors.append(f"Connection to unknown node: {target} (from {source_name})")
    
    # Trigger type
    triggers = find_nodes_by_type('trigger')
    if not triggers:
        warnings.append("No trigger node found")
    else:
        for name in triggers:
            ntype = get_node_type(name)
            if 'manualTrigger' in ntype:
                info.append(f"Uses Manual Trigger: {name}")
            elif 'scheduleTrigger' in ntype:
                info.append(f"Uses Schedule Trigger: {name}")
    
    # Google Sheets ops
    for name in sheets_nodes:
        params = get_node_params(name)
        op = params.get('operation', 'unknown')
        sheet = params.get('sheetName', '')
        info.append(f"Google Sheets [{op}]: {name} -> sheet: {sheet}")
    
    # Print results
    print(f"\n🔍 Validating: {workflow_file}")
    print("=" * 60)
    
    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    ❌ {e}")
    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    ⚠️  {w}")
    if info:
        print(f"\n  INFO ({len(info)}):")
        for i in info:
            print(f"    ℹ️  {i}")
    
    print(f"\n  Summary: {len(errors)} errors, {len(warnings)} warnings, {len(info)} info")
    print("=" * 60)
    
    if errors:
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="ScrapeHero Article Generator - Manage articles and generate workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to run")
    
    # new-article command
    new_parser = subparsers.add_parser("new-article", help="Scaffold a new article folder")
    new_parser.add_argument("name", help="Article name (e.g., 'Amazon Product Scraper')")
    new_parser.add_argument("--platform", default="Amazon", help="Platform name (default: Amazon)")
    new_parser.add_argument("--tool", default="n8n", help="Automation tool (default: n8n)")
    new_parser.add_argument("--storage", default="Google Sheets", help="Storage backend (default: Google Sheets)")
    new_parser.add_argument("--unique-id", dest="unique_id", default="asin", help="Unique identifier field (default: asin)")
    new_parser.add_argument("--generate", action="store_true", help="Also run generation immediately")
    
    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate workflow and prompt from config")
    gen_parser.add_argument("config_file", help="Path to the JSON configuration file")
    gen_parser.add_argument("--output-dir", default=None, help="Directory to save generated files (defaults to config directory)")
    gen_parser.add_argument("--workflow", default=None, help="Path to an existing workflow JSON to use")
    gen_parser.add_argument("--prompt-only", action="store_true", help="Only generate article_prompt.txt without overwriting workflow.json")
    
    # prompt command (convenience alias for prompt-only)
    prompt_parser = subparsers.add_parser("prompt", help="Regenerate only article_prompt.txt from config and existing/corrected workflow")
    prompt_parser.add_argument("config_file", help="Path to the JSON configuration file")
    prompt_parser.add_argument("--output-dir", default=None, help="Directory to save generated files (defaults to config directory)")
    prompt_parser.add_argument("--workflow", default=None, help="Path to an existing workflow JSON to use")
    
    # validate command
    val_parser = subparsers.add_parser("validate", help="Validate workflow.json against critic rules")
    val_parser.add_argument("workflow_file", help="Path to the workflow.json file")
    
    args = parser.parse_args()
    
    if args.command == "new-article":
        cmd_new_article(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "prompt":
        args.prompt_only = True
        cmd_generate(args)
    elif args.command == "validate":
        cmd_validate(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
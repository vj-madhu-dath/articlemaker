const fs = require('fs');

const workflowPath = 'd:\\Document\\articlemaker\\output\\workflow.json';
let workflow = JSON.parse(fs.readFileSync(workflowPath, 'utf8'));

// Remove old nodes: "Code (Find Old Items)", "Check if Dummy", "Code (Prepare New Items)"
workflow.nodes = workflow.nodes.filter(n => !["Code (Find Old Items)", "Check if Dummy", "Code (Prepare New Items)"].includes(n.name));

// Add new nodes
workflow.nodes.push({
    "parameters": {
        "fieldToSplitOut": "search_results",
        "options": {}
    },
    "name": "Prepare New Items",
    "type": "n8n-nodes-base.splitOut",
    "typeVersion": 1,
    "position": [ 800, 200 ]
});

workflow.nodes.push({
    "parameters": {
        "mode": "removeKeyMatches",
        "propertyName1": "asin",
        "propertyName2": "asin"
    },
    "name": "Find Old Items",
    "type": "n8n-nodes-base.merge",
    "typeVersion": 2.1,
    "position": [ 1000, 100 ]
});

// Update positions for clarity
const getNode = name => workflow.nodes.find(n => n.name === name);
getNode("ScrapeHero").position = [600, 100];
getNode("Get Existing Listings").position = [800, 0];
getNode("Delete Old Listings").position = [1200, 100];
getNode("Upsert New Listings").position = [1200, 200];
getNode("Loop Over Items").position = [400, 100];

// Redo connections
workflow.connections = {
    "Manual Trigger": { "main": [ [ { "node": "Get Queries", "type": "main", "index": 0 } ] ] },
    "Get Queries": { "main": [ [ { "node": "Loop Over Items", "type": "main", "index": 0 } ] ] },
    "Loop Over Items": { "main": [ [], [ { "node": "ScrapeHero", "type": "main", "index": 0 } ] ] },
    "ScrapeHero": {
        "main": [
            [
                { "node": "Get Existing Listings", "type": "main", "index": 0 },
                { "node": "Prepare New Items", "type": "main", "index": 0 }
            ]
        ]
    },
    "Get Existing Listings": {
        "main": [
            [
                { "node": "Find Old Items", "type": "main", "index": 0 }
            ]
        ]
    },
    "Prepare New Items": {
        "main": [
            [
                { "node": "Find Old Items", "type": "main", "index": 1 },
                { "node": "Upsert New Listings", "type": "main", "index": 0 }
            ]
        ]
    },
    "Find Old Items": {
        "main": [
            [
                { "node": "Delete Old Listings", "type": "main", "index": 0 }
            ]
        ]
    },
    "Upsert New Listings": {
        "main": [
            [
                { "node": "Loop Over Items", "type": "main", "index": 0 }
            ]
        ]
    }
};

fs.writeFileSync(workflowPath, JSON.stringify(workflow, null, 2));
console.log("Workflow updated successfully.");

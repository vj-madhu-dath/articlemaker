# Workflow Update Changelog

1. **Replaced `Code (Prepare New Items)`**: Replaced the custom JavaScript code with n8n's native visual `Item Lists` (Split Out) node (`n8n-nodes-base.splitOut`). This efficiently splits the `search_results` array from the ScrapeHero API response into individual items without requiring manual coding.
2. **Replaced `Code (Find Old Items)`**: Removed the JavaScript logic and the subsequent `Check if Dummy` node. Replaced them with the `Merge` node (`n8n-nodes-base.merge`) set to the `removeKeyMatches` mode. This visually diffs the existing listings against the new listings by matching the `asin` field, successfully separating outdated items for deletion.
3. **Improved Graph Flow**: Reconfigured the workflow so that processing branches into parallel tracks for deleting old listings and upserting new ones, removing dummy item checks and leveraging n8n loop-batch safe execution limits. All logic is now correctly handled via visual nodes.

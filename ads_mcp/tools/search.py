# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for exposing the API Search method to the MCP server."""

import json
from typing import Any, Dict, List
from ads_mcp.coordinator import mcp
import ads_mcp.utils as utils

# Max rows returned to the client to avoid flooding the context window
_MAX_RESPONSE_ROWS = 100
# Default LIMIT applied to GAQL queries when none is specified
_DEFAULT_LIMIT = 500


def search(
    customer_id: str,
    fields: List[str],
    resource: str,
    conditions: List[str] = None,
    orderings: List[str] = None,
    limit: int | str = None,
) -> Dict[str, Any]:
    """Fetches data from the Google Ads API using the search method

    Args:
        customer_id: The id of the customer
        fields: The fields to fetch
        resource: The resource to return fields from
        conditions: List of conditions to filter the data, combined using AND clauses
        orderings: How the data is ordered
        limit: The maximum number of rows to return (default: 500)

    """

    ga_service = utils.get_googleads_service("GoogleAdsService")

    query_parts = [f"SELECT {','.join(fields)} FROM {resource}"]

    if conditions:
        query_parts.append(f" WHERE {' AND '.join(conditions)}")

    if orderings:
        query_parts.append(f" ORDER BY {','.join(orderings)}")

    # Apply default limit if none specified
    effective_limit = int(limit) if limit else _DEFAULT_LIMIT
    query_parts.append(f" LIMIT {effective_limit}")

    query = "".join(query_parts)
    utils.logger.info(f"ads_mcp.search query {query}")

    query_result = ga_service.search_stream(
        customer_id=customer_id, query=query
    )

    final_output: List = []
    for batch in query_result:
        for row in batch.results:
            final_output.append(
                utils.format_output_row(row, batch.field_mask.paths)
            )

    total_rows = len(final_output)

    # Truncate response to avoid flooding the context window
    if total_rows > _MAX_RESPONSE_ROWS:
        return {
            "rows": final_output[:_MAX_RESPONSE_ROWS],
            "total_rows": total_rows,
            "returned_rows": _MAX_RESPONSE_ROWS,
            "truncated": True,
            "message": f"Showing first {_MAX_RESPONSE_ROWS} of {total_rows} rows. Use 'conditions' to filter or 'limit' to control the result size.",
        }

    return {
        "rows": final_output,
        "total_rows": total_rows,
        "returned_rows": total_rows,
        "truncated": False,
    }


def _describe_resource(resource_name: str) -> Dict[str, Any]:
    """Look up the selectable, filterable, and sortable fields for a specific GAQL resource."""
    try:
        with open(utils.get_gaql_resources_filepath(), "r") as f:
            resources = json.load(f)
        for r in resources:
            if r["resource"] == resource_name:
                return r
        return {"error": f"Resource '{resource_name}' not found. Use list_gaql_resources to see available resources."}
    except FileNotFoundError:
        return {"error": "gaql_resources.json not found."}


def _list_resources() -> List[str]:
    """List all available GAQL resource names."""
    try:
        with open(utils.get_gaql_resources_filepath(), "r") as f:
            resources = json.load(f)
        return [r["resource"] for r in resources]
    except FileNotFoundError:
        return []


_SEARCH_DESCRIPTION = """Fetches data from the Google Ads API using GAQL (Google Ads Query Language).

### Hints
- Grammar: https://developers.google.com/google-ads/api/docs/query/grammar
- All resources: https://developers.google.com/google-ads/api/fields/v21/overview
- customer_id must be a string of numbers without punctuation (e.g. 1234567890, NOT 123-456-7890)
- Dates must be YYYY-MM-DD with dashes. Date literals from the Grammar must NEVER be used. Date ranges must have start AND end.
- Default LIMIT is 500. Responses are truncated to 100 rows max. Use conditions to filter.
- change_event requires LIMIT <= 10000
- For conversion issues try offline_conversion_upload_conversion_action_summary
- Conversions docs: https://developers.google.com/google-ads/api/docs/conversions/upload-summaries

### IMPORTANT: Use list_gaql_resources and describe_gaql_resource tools
Before writing a query, use `list_gaql_resources` to see available resources and `describe_gaql_resource` to get the exact field names for the resource you want to query. Fields must match exactly — no wildcards or partial names.

### Common resources
campaign, ad_group, ad_group_ad, keyword_view, search_term_view, campaign_budget, ad_group_criterion, customer, bidding_strategy, conversion_action, campaign_criterion, geographic_view, gender_view, age_range_view, change_event

### Common metric fields (prefix with metrics.)
impressions, clicks, cost_micros, conversions, conversions_value, ctr, average_cpc, average_cpm, all_conversions, all_conversions_value, cost_per_conversion, interaction_rate, video_views, search_impression_share, search_top_impression_percentage

### Common segment fields (prefix with segments.)
date, device, ad_network_type, conversion_action, conversion_action_name, click_type, slot, day_of_week, month, quarter, year
"""


# Register the search tool with a compact description instead of embedding the full 400KB JSON
mcp.add_tool(
    search,
    title="Fetches data from the Google Ads API using the search method",
    description=_SEARCH_DESCRIPTION,
)


@mcp.tool()
def list_gaql_resources() -> List[str]:
    """Lists all available GAQL resource names that can be used in the 'resource' parameter of the search tool."""
    return _list_resources()


@mcp.tool()
def describe_gaql_resource(resource_name: str) -> Dict[str, Any]:
    """Returns the selectable, filterable, and sortable fields for a specific GAQL resource.
    Use this before writing a search query to get the exact field names.

    Args:
        resource_name: The GAQL resource name (e.g. 'campaign', 'ad_group', 'ad_group_ad')
    """
    return _describe_resource(resource_name)

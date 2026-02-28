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

"""Write tools for mutating Google Ads resources via the MCP server."""

from typing import List
from ads_mcp.coordinator import mcp
import ads_mcp.utils as utils

from google.api_core import protobuf_helpers


@mcp.tool()
def add_negative_keywords(
    customer_id: str,
    campaign_id: str,
    keywords: List[str],
    match_type: str = "BROAD",
) -> str:
    """Adds negative keywords to a campaign.

    Args:
        customer_id: The customer ID (digits only, no hyphens).
        campaign_id: The campaign ID to add negative keywords to.
        keywords: List of keyword texts to add as negatives.
        match_type: BROAD, PHRASE, or EXACT (default BROAD).

    Returns:
        Summary of added negative keywords.
    """
    campaign_criterion_service = utils.get_googleads_service(
        "CampaignCriterionService"
    )

    operations = []
    for keyword_text in keywords:
        operation = utils.get_googleads_type("CampaignCriterionOperation")
        criterion = operation.create
        criterion.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
        criterion.negative = True
        criterion.keyword.text = keyword_text
        criterion.keyword.match_type = getattr(
            utils.get_googleads_type("KeywordMatchTypeEnum").KeywordMatchType,
            match_type.upper(),
        )
        operations.append(operation)

    response = campaign_criterion_service.mutate_campaign_criteria(
        customer_id=customer_id, operations=operations
    )

    added = [r.resource_name for r in response.results]
    return f"Added {len(added)} negative keyword(s): {', '.join(keywords)}"


@mcp.tool()
def update_campaign_status(
    customer_id: str,
    campaign_id: str,
    status: str,
) -> str:
    """Updates a campaign's status (pause or enable).

    Args:
        customer_id: The customer ID (digits only, no hyphens).
        campaign_id: The campaign ID to update.
        status: ENABLED or PAUSED.

    Returns:
        Confirmation of the status change.
    """
    campaign_service = utils.get_googleads_service("CampaignService")

    operation = utils.get_googleads_type("CampaignOperation")
    campaign = operation.update
    campaign.resource_name = (
        f"customers/{customer_id}/campaigns/{campaign_id}"
    )
    campaign.status = getattr(
        utils.get_googleads_type("CampaignStatusEnum").CampaignStatus,
        status.upper(),
    )

    field_mask = protobuf_helpers.field_mask(None, campaign._pb)
    operation.update_mask.CopyFrom(field_mask)

    response = campaign_service.mutate_campaigns(
        customer_id=customer_id, operations=[operation]
    )

    return f"Campaign {campaign_id} status updated to {status.upper()}. Resource: {response.results[0].resource_name}"


@mcp.tool()
def update_campaign_budget(
    customer_id: str,
    campaign_id: str,
    budget_amount: float,
) -> str:
    """Updates the daily budget for a campaign.

    Args:
        customer_id: The customer ID (digits only, no hyphens).
        campaign_id: The campaign ID whose budget to update.
        budget_amount: New daily budget in the account's currency (e.g. 50.00 for $50).

    Returns:
        Confirmation of the budget change.
    """
    ga_service = utils.get_googleads_service("GoogleAdsService")
    query = (
        f"SELECT campaign.campaign_budget FROM campaign "
        f"WHERE campaign.id = {campaign_id} LIMIT 1"
    )
    response = ga_service.search_stream(
        customer_id=customer_id, query=query
    )

    budget_resource_name = None
    for batch in response:
        for row in batch.results:
            budget_resource_name = row.campaign.campaign_budget
            break

    if not budget_resource_name:
        return f"Error: Could not find budget for campaign {campaign_id}"

    budget_service = utils.get_googleads_service("CampaignBudgetService")

    operation = utils.get_googleads_type("CampaignBudgetOperation")
    budget = operation.update
    budget.resource_name = budget_resource_name
    budget.amount_micros = int(budget_amount * 1_000_000)

    field_mask = protobuf_helpers.field_mask(None, budget._pb)
    operation.update_mask.CopyFrom(field_mask)

    result = budget_service.mutate_campaign_budgets(
        customer_id=customer_id, operations=[operation]
    )

    return f"Campaign {campaign_id} daily budget updated to {budget_amount}. Resource: {result.results[0].resource_name}"


@mcp.tool()
def update_bidding_strategy(
    customer_id: str,
    campaign_id: str,
    bidding_strategy: str,
    target_value: float = None,
) -> str:
    """Updates the bidding strategy for a campaign.

    Args:
        customer_id: The customer ID (digits only, no hyphens).
        campaign_id: The campaign ID to update.
        bidding_strategy: One of TARGET_CPA, TARGET_ROAS, MAXIMIZE_CONVERSIONS, MAXIMIZE_CONVERSION_VALUE.
        target_value: Optional target value. For TARGET_CPA: target CPA in currency (e.g. 10.00).
                      For TARGET_ROAS: target ROAS as a ratio (e.g. 4.0 for 400%).

    Returns:
        Confirmation of the bidding strategy change.
    """
    campaign_service = utils.get_googleads_service("CampaignService")

    operation = utils.get_googleads_type("CampaignOperation")
    campaign = operation.update
    campaign.resource_name = (
        f"customers/{customer_id}/campaigns/{campaign_id}"
    )

    strategy = bidding_strategy.upper()

    if strategy == "TARGET_CPA":
        if target_value is not None:
            campaign.target_cpa.target_cpa_micros = int(
                target_value * 1_000_000
            )
        else:
            campaign.target_cpa.target_cpa_micros = 0
    elif strategy == "TARGET_ROAS":
        if target_value is not None:
            campaign.target_roas.target_roas = target_value
        else:
            campaign.target_roas.target_roas = 0.0
    elif strategy == "MAXIMIZE_CONVERSIONS":
        if target_value is not None:
            campaign.maximize_conversions.target_cpa_micros = int(
                target_value * 1_000_000
            )
        else:
            campaign.maximize_conversions.SetInParent()
    elif strategy == "MAXIMIZE_CONVERSION_VALUE":
        if target_value is not None:
            campaign.maximize_conversion_value.target_roas = target_value
        else:
            campaign.maximize_conversion_value.SetInParent()
    else:
        return f"Error: Unknown bidding strategy '{bidding_strategy}'. Use TARGET_CPA, TARGET_ROAS, MAXIMIZE_CONVERSIONS, or MAXIMIZE_CONVERSION_VALUE."

    field_mask = protobuf_helpers.field_mask(None, campaign._pb)
    operation.update_mask.CopyFrom(field_mask)

    response = campaign_service.mutate_campaigns(
        customer_id=customer_id, operations=[operation]
    )

    target_info = f" (target: {target_value})" if target_value else ""
    return f"Campaign {campaign_id} bidding strategy updated to {strategy}{target_info}. Resource: {response.results[0].resource_name}"


@mcp.tool()
def update_ad_group_status(
    customer_id: str,
    ad_group_id: str,
    status: str,
) -> str:
    """Updates an ad group's status (pause or enable).

    Args:
        customer_id: The customer ID (digits only, no hyphens).
        ad_group_id: The ad group ID to update.
        status: ENABLED or PAUSED.

    Returns:
        Confirmation of the status change.
    """
    ad_group_service = utils.get_googleads_service("AdGroupService")

    operation = utils.get_googleads_type("AdGroupOperation")
    ad_group = operation.update
    ad_group.resource_name = (
        f"customers/{customer_id}/adGroups/{ad_group_id}"
    )
    ad_group.status = getattr(
        utils.get_googleads_type("AdGroupStatusEnum").AdGroupStatus,
        status.upper(),
    )

    field_mask = protobuf_helpers.field_mask(None, ad_group._pb)
    operation.update_mask.CopyFrom(field_mask)

    response = ad_group_service.mutate_ad_groups(
        customer_id=customer_id, operations=[operation]
    )

    return f"Ad group {ad_group_id} status updated to {status.upper()}. Resource: {response.results[0].resource_name}"


@mcp.tool()
def update_ad_status(
    customer_id: str,
    ad_group_id: str,
    ad_id: str,
    status: str,
) -> str:
    """Updates an ad's status (pause or enable).

    Args:
        customer_id: The customer ID (digits only, no hyphens).
        ad_group_id: The ad group ID containing the ad.
        ad_id: The ad ID to update.
        status: ENABLED or PAUSED.

    Returns:
        Confirmation of the status change.
    """
    ad_group_ad_service = utils.get_googleads_service("AdGroupAdService")

    operation = utils.get_googleads_type("AdGroupAdOperation")
    ad_group_ad = operation.update
    ad_group_ad.resource_name = (
        f"customers/{customer_id}/adGroupAds/{ad_group_id}~{ad_id}"
    )
    ad_group_ad.status = getattr(
        utils.get_googleads_type("AdGroupAdStatusEnum").AdGroupAdStatus,
        status.upper(),
    )

    field_mask = protobuf_helpers.field_mask(None, ad_group_ad._pb)
    operation.update_mask.CopyFrom(field_mask)

    response = ad_group_ad_service.mutate_ad_group_ads(
        customer_id=customer_id, operations=[operation]
    )

    return f"Ad {ad_id} status updated to {status.upper()}. Resource: {response.results[0].resource_name}"

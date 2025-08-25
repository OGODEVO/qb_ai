import os
import json
from typing import Literal, Optional, Dict, Any, List
import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# --- Pydantic Models for Type-Safe Arguments ---

class MetaAdsFilters(BaseModel):
    campaign_id: Optional[str] = None
    ad_set_id: Optional[str] = None
    ad_id: Optional[str] = None
    # Add other relevant filters here

class MetaAdsQueryArgs(BaseModel):
    level: Literal["ad", "adset", "campaign", "account"]
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    fields: List[str]
    filters: Optional[MetaAdsFilters] = None

# --- Live Meta Ads API Call ---

@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(0.6),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
)
def make_meta_ads_request(validated_args: MetaAdsQueryArgs) -> Dict[str, Any]:
    """Makes a real HTTP request to the Meta Ads API."""
    base_url = f"https://graph.facebook.com/v18.0"
    ad_account_id = os.getenv("META_AD_ACCOUNT_ID")
    access_token = os.getenv("META_ACCESS_TOKEN")

    if not all([ad_account_id, access_token]):
        raise ConnectionError("Meta Ads credentials (META_AD_ACCOUNT_ID, META_ACCESS_TOKEN) are missing.")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    url = f"{base_url}/act_{ad_account_id}/insights"
    
    # Basic parameter mapping
    meta_params = {
        "level": validated_args.level,
        "time_range": json.dumps({'since': validated_args.start_date, 'until': validated_args.end_date}),
        "fields": ",".join(validated_args.fields),
    }

    if validated_args.filters:
        filtering = []
        if validated_args.filters.campaign_id:
            filtering.append({'field': 'campaign.id', 'operator': 'EQUAL', 'value': validated_args.filters.campaign_id})
        if validated_args.filters.ad_set_id:
            filtering.append({'field': 'adset.id', 'operator': 'EQUAL', 'value': validated_args.filters.ad_set_id})
        if validated_args.filters.ad_id:
            filtering.append({'field': 'ad.id', 'operator': 'EQUAL', 'value': validated_args.filters.ad_id})
        meta_params['filtering'] = json.dumps(filtering)

    with httpx.Client() as client:
        try:
            res = client.get(url, headers=headers, params=meta_params, timeout=10.0)
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [401, 403]:
                raise ConnectionRefusedError(
                    "Meta Ads authentication failed (401/403). "
                    "Your META_ACCESS_TOKEN may be expired or invalid. Please refresh it."
                )
            raise e

# --- Response Normalization ---

def _normalize_response(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes the raw Meta Ads API response into a consistent format."""
    
    if "data" not in raw_data or not raw_data["data"]:
        return {"data": []}

    return {"data": raw_data["data"]}


# --- Main Tool Function ---

def meta_ads_query(
    level: str,
    start_date: str,
    end_date: str,
    fields: List[str],
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Queries Meta Ads for advertising data.

    Args:
        level: The level to aggregate results at (ad, adset, campaign, account).
        start_date: The start date for the report (YYYY-MM-DD).
        end_date: The end date for the report (YYYY-MM-DD).
        fields: A list of fields to retrieve.
        filters: Optional dictionary of filters (e.g., campaign_id, ad_set_id).

    Returns:
        A dictionary containing the query result.
    """
    try:
        # Validate arguments with Pydantic
        validated_args = MetaAdsQueryArgs(
            level=level,
            start_date=start_date,
            end_date=end_date,
            fields=fields,
            filters=MetaAdsFilters(**filters) if filters else None,
        )

        raw_result = make_meta_ads_request(validated_args)
        result = _normalize_response(raw_result)

        return result

    except (ConnectionError, ConnectionRefusedError) as e:
        return {"error": str(e)}
    except Exception as e:
        # Catch-all for other unexpected errors, including Pydantic validation
        return {"error": f"An unexpected error occurred: {str(e)}"}
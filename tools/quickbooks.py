import os
import json
from typing import Literal, Optional, Dict, Any, List
import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# --- Pydantic Models for Type-Safe Arguments ---

class QBFilters(BaseModel):
    account: Optional[str] = None
    vendor: Optional[str] = None
    category: Optional[str] = None
    search: Optional[str] = None
    limit: Optional[int] = None
    group_by: Optional[Literal["vendor", "category"]] = None
    compare: Optional[Literal["prior_period"]] = None

class QBQueryArgs(BaseModel):
    report: Literal["pnl", "by_category", "expenses_by_vendor", "trial_balance", "custom"]
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    filters: Optional[QBFilters] = None

# --- Stub Data for Local Development ---

def get_stub_data(validated_args: QBQueryArgs) -> Dict[str, Any]:
    """Returns deterministic stub data based on the query."""
    filters = validated_args.filters or QBFilters()
    report_type = validated_args.report
    
    response: Dict[str, Any] = {
        "report": report_type,
        "start_date": validated_args.start_date,
        "end_date": validated_args.end_date,
        "filters": filters.model_dump(exclude_none=True),
        "totals": {},
        "lines": [],
    }

    if report_type == "by_category" and filters.category == "Advertising":
        response["totals"] = {"total_expenses": 1250.75}
        response["lines"] = [
            {"vendor": "Google Ads", "amount": 800.50},
            {"vendor": "Facebook Ads", "amount": 450.25},
        ]
    elif report_type == "by_category" and filters.limit == 5:
        response["totals"] = {"total_expenses": 5800.00}
        response["lines"] = [
            {"category": "Contractors", "amount": 2500.00},
            {"category": "Software", "amount": 1500.00},
            {"category": "Advertising", "amount": 1250.00},
            {"category": "Utilities", "amount": 350.00},
            {"category": "Office Supplies", "amount": 200.00},
        ]
    elif report_type == "pnl":
        response["totals"] = {"total_revenue": 15000.00, "total_expenses": 7500.00, "net_income": 7500.00}
    elif report_type == "expenses_by_vendor" and filters.vendor == "Stripe":
         response["totals"] = {"total_expenses": 280.00}
         response["lines"] = [
            {"category": "Software", "amount": 150.00},
            {"category": "Transaction Fees", "amount": 130.00},
        ]
    else:
        response["totals"] = {"total_expenses": 0, "total_revenue": 0}
        response["lines"] = []
        
    return response

# --- Live QuickBooks API Call ---

@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(0.6),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
)
def make_qbo_request(report_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Makes a real HTTP request to the QuickBooks Sandbox API."""
    base_url = "https://sandbox-quickbooks.api.intuit.com/v3/company"
    realm_id = os.getenv("QB_REALM_ID")
    access_token = os.getenv("QB_ACCESS_TOKEN")

    if not all([realm_id, access_token]):
        raise ConnectionError("QuickBooks credentials (QB_REALM_ID, QB_ACCESS_TOKEN) are missing.")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    # Map report types to actual QBO report endpoints
    report_endpoints = {
        "pnl": "reports/ProfitAndLoss",
        "by_category": "reports/ExpenseDistribution",
        "expenses_by_vendor": "reports/VendorExpenses",
        "trial_balance": "reports/TrialBalance",
        "custom": "reports/CustomReport", # This would need more specific handling
    }

    endpoint = report_endpoints.get(report_type)
    if not endpoint:
        raise ValueError(f"Invalid report type: {report_type}")

    url = f"{base_url}/{realm_id}/{endpoint}"
    
    # Basic parameter mapping
    qbo_params = {
        "start_date": params.get("start_date"),
        "end_date": params.get("end_date"),
    }
    
    # Add report-specific parameters
    if report_type == "by_category":
        qbo_params["group_by"] = "category"
    elif report_type == "expenses_by_vendor":
        qbo_params["group_by"] = "vendor"


    with httpx.Client() as client:
        try:
            res = client.get(url, headers=headers, params=qbo_params, timeout=10.0)
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [401, 403]:
                raise ConnectionRefusedError(
                    "QuickBooks authentication failed (401/403). "
                    "Your QB_ACCESS_TOKEN may be expired or invalid. Please refresh it."
                )
            raise e

# --- Response Normalization ---

def _normalize_response(report_type: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes the raw QBO API response into a consistent format."""
    
    # Note: This is a simplified normalization. A real-world implementation
    # would need to be much more robust to handle the variety of QBO responses.
    
    if not raw_data.get("Rows") or not raw_data.get("Header"):
        # If there's no data, return an empty structure
        return {"totals": {}, "lines": []}

    header = raw_data.get("Header", {})
    rows = raw_data.get("Rows", {}).get("Row", [])

    if report_type == "pnl":
        total_revenue = 0
        total_expenses = 0
        header_rows = header.get("Rows", [])
        if len(header_rows) > 1:
            if len(header_rows[0].get("ColData", [])) > 1:
                total_revenue = header_rows[0]["ColData"][1].get("value", 0)
            if len(header_rows[1].get("ColData", [])) > 1:
                total_expenses = header_rows[1]["ColData"][1].get("value", 0)
        
        return {
            "totals": {
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
            },
            "lines": rows,
        }
    elif report_type == "by_category":
        lines = []
        for row in rows:
            if row.get("ColData") and len(row["ColData"]) > 1:
                lines.append({
                    "category": row["ColData"][0].get("value"),
                    "amount": row["ColData"][1].get("value"),
                })
        
        total_expenses = 0
        summary = header.get("Summary", {})
        if len(summary.get("ColData", [])) > 1:
            total_expenses = summary["ColData"][1].get("value", 0)

        return {
            "totals": {
                "total_expenses": total_expenses
            },
            "lines": lines,
        }
    # Add normalization for other reports here...
    else:
        # Default fallback
        return {
            "totals": {},
            "lines": rows,
        }


# --- Main Tool Function ---

def qb_query(
    report: str,
    start_date: str,
    end_date: str,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Queries QuickBooks for financial data.

    Args:
        report: The type of report to generate.
        start_date: The start date for the report (YYYY-MM-DD).
        end_date: The end date for the report (YYYY-MM-DD).
        filters: Optional dictionary of filters (e.g., category, vendor, limit).

    Returns:
        A dictionary containing the query result.
    """
    try:
        # Validate arguments with Pydantic
        validated_args = QBQueryArgs(
            report=report,
            start_date=start_date,
            end_date=end_date,
            filters=QBFilters(**filters) if filters else None,
        )

        use_stub = os.getenv("QB_USE_STUB", "true").lower() == "true"

        if use_stub:
            result = get_stub_data(validated_args)
        else:
            api_params = validated_args.model_dump(exclude_none=True)
            raw_result = make_qbo_request(validated_args.report, api_params)
            
            normalized_data = _normalize_response(validated_args.report, raw_result)
            
            result = {
                "report": validated_args.report,
                "start_date": start_date,
                "end_date": end_date,
                "filters": filters,
                **normalized_data,
            }

        return result

    except (ConnectionError, ConnectionRefusedError) as e:
        return {"error": str(e)}
    except Exception as e:
        # Catch-all for other unexpected errors, including Pydantic validation
        return {"error": f"An unexpected error occurred: {str(e)}"}

def get_tools() -> list[dict]:
    """Returns the tool definition for the qb_query function."""
    return [
        {
            "type": "function",
            "function": {
                "name": "qb_query",
                "description": "Query QuickBooks for financial data like expenses, revenue, and reports.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "report": {
                            "type": "string",
                            "enum": ["pnl", "by_category", "expenses_by_vendor", "trial_balance", "custom"],
                            "description": "The type of report to generate."
                        },
                        "start_date": {
                            "type": "string",
                            "format": "date",
                            "description": "The start date for the report (YYYY-MM-DD)."
                        },
                        "end_date": {
                            "type": "string",
                            "format": "date",
                            "description": "The end date for the report (YYYY-MM-DD)."
                        },
                        "filters": {
                            "type": "object",
                            "properties": {
                                "account": {"type": "string"},
                                "vendor": {"type": "string"},
                                "category": {"type": "string"},
                                "search": {"type": "string"},
                                "limit": {"type": "integer"},
                                "group_by": {"type": "string", "enum": ["vendor", "category"]},
                                "compare": {"type": "string", "enum": ["prior_period"]},
                            },
                            "description": "Optional filters to apply to the query."
                        }
                    },
                    "required": ["report", "start_date", "end_date"],
                },
            },
        }
    ]
from typing import Any, Dict

from actions import (
    suggest_cancellation,
    suggest_downgrade,
    suggest_duplicate_dispute,
)


def _df_to_records(df) -> list[dict]:
    if df is None or df.empty:
        return []
    return df.to_dict(orient="records")


def get_recurring_subscriptions(customer_result: Dict[str, Any], customer_id: int) -> Dict[str, Any]:
    records = _df_to_records(customer_result["recurring"])
    return {
        "tool_name": "get_recurring_subscriptions",
        "customer_id": customer_id,
        "result_type": "data",
        "records": records,
        "message": f"Found {len(records)} recurring subscriptions for customer {customer_id}.",
    }


def get_duplicate_subscriptions(customer_result: Dict[str, Any], customer_id: int) -> Dict[str, Any]:
    records = _df_to_records(customer_result["duplicates"])
    return {
        "tool_name": "get_duplicate_subscriptions",
        "customer_id": customer_id,
        "result_type": "data",
        "records": records,
        "message": f"Found {len(records)} possible duplicate patterns for customer {customer_id}.",
    }


def get_price_changes(customer_result: Dict[str, Any], customer_id: int) -> Dict[str, Any]:
    records = _df_to_records(customer_result["price_changes"])
    return {
        "tool_name": "get_price_changes",
        "customer_id": customer_id,
        "result_type": "data",
        "records": records,
        "message": f"Found {len(records)} price change patterns for customer {customer_id}.",
    }


def get_overlapping_plans(customer_result: Dict[str, Any], customer_id: int) -> Dict[str, Any]:
    records = _df_to_records(customer_result["overlaps"])
    return {
        "tool_name": "get_overlapping_plans",
        "customer_id": customer_id,
        "result_type": "data",
        "records": records,
        "message": f"Found {len(records)} overlapping plan signals for customer {customer_id}.",
    }


def get_monthly_spend(customer_result: Dict[str, Any], customer_id: int) -> Dict[str, Any]:
    records = _df_to_records(customer_result["monthly_spend"])
    spend = None
    if records:
        spend = records[0].get("total_estimated_monthly_spend")

    return {
        "tool_name": "get_monthly_spend",
        "customer_id": customer_id,
        "result_type": "data",
        "records": records,
        "message": f"Estimated monthly spend for customer {customer_id} is {spend}.",
    }


def create_duplicate_dispute_action(customer_result: Dict[str, Any], customer_id: int) -> Dict[str, Any]:
    duplicates_df = customer_result["duplicates"]
    if duplicates_df.empty:
        return {
            "tool_name": "create_duplicate_dispute_action",
            "customer_id": customer_id,
            "result_type": "action",
            "created_action": None,
            "message": "No duplicate issue available to create a dispute action.",
        }

    row = duplicates_df.iloc[0]
    action = suggest_duplicate_dispute(
        customer_id,
        str(row["normalized_merchant"]),
        str(row["year_month"]),
    )
    return {
        "tool_name": "create_duplicate_dispute_action",
        "customer_id": customer_id,
        "result_type": "action",
        "created_action": action,
        "message": f"Created a suggested duplicate dispute action for {row['normalized_merchant']}.",
    }


def create_downgrade_action(customer_result: Dict[str, Any], customer_id: int) -> Dict[str, Any]:
    recurring_df = customer_result["recurring"]
    if recurring_df.empty:
        return {
            "tool_name": "create_downgrade_action",
            "customer_id": customer_id,
            "result_type": "action",
            "created_action": None,
            "message": "No subscription available to create a downgrade action.",
        }

    row = recurring_df.iloc[0]
    action = suggest_downgrade(customer_id, str(row["normalized_merchant"]))
    return {
        "tool_name": "create_downgrade_action",
        "customer_id": customer_id,
        "result_type": "action",
        "created_action": action,
        "message": f"Created a suggested downgrade action for {row['normalized_merchant']}.",
    }


def create_cancellation_action(customer_result: Dict[str, Any], customer_id: int) -> Dict[str, Any]:
    recurring_df = customer_result["recurring"]
    if recurring_df.empty:
        return {
            "tool_name": "create_cancellation_action",
            "customer_id": customer_id,
            "result_type": "action",
            "created_action": None,
            "message": "No subscription available to create a cancellation action.",
        }

    row = recurring_df.iloc[0]
    action = suggest_cancellation(customer_id, str(row["normalized_merchant"]))
    return {
        "tool_name": "create_cancellation_action",
        "customer_id": customer_id,
        "result_type": "action",
        "created_action": action,
        "message": f"Created a suggested cancellation action for {row['normalized_merchant']}.",
    }


TOOL_REGISTRY = {
    "get_recurring_subscriptions": get_recurring_subscriptions,
    "get_duplicate_subscriptions": get_duplicate_subscriptions,
    "get_price_changes": get_price_changes,
    "get_overlapping_plans": get_overlapping_plans,
    "get_monthly_spend": get_monthly_spend,
    "create_duplicate_dispute_action": create_duplicate_dispute_action,
    "create_downgrade_action": create_downgrade_action,
    "create_cancellation_action": create_cancellation_action,
}


def get_tool_descriptions() -> list[dict]:
    return [
        {
            "name": "get_recurring_subscriptions",
            "description": "Returns recurring subscriptions for the current customer.",
        },
        {
            "name": "get_duplicate_subscriptions",
            "description": "Returns possible duplicate charges for the current customer.",
        },
        {
            "name": "get_price_changes",
            "description": "Returns subscription price changes for the current customer.",
        },
        {
            "name": "get_overlapping_plans",
            "description": "Returns overlapping subscription plan signals for the current customer.",
        },
        {
            "name": "get_monthly_spend",
            "description": "Returns estimated monthly recurring subscription spend.",
        },
        {
            "name": "create_duplicate_dispute_action",
            "description": "Creates a suggested duplicate dispute action for the current customer.",
        },
        {
            "name": "create_downgrade_action",
            "description": "Creates a suggested downgrade review action for the current customer.",
        },
        {
            "name": "create_cancellation_action",
            "description": "Creates a suggested cancellation review action for the current customer.",
        },
    ]
from datetime import datetime
import uuid


def _base_action(customer_id: int, merchant: str, action_type: str, message: str) -> dict:
    return {
        "action_id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "customer_id": customer_id,
        "merchant": merchant,
        "action_type": action_type,
        "status": "suggested",
        "message": message,
    }


def suggest_cancellation(customer_id: int, merchant: str) -> dict:
    return _base_action(
        customer_id,
        merchant,
        "cancellation_request",
        f"Suggested cancellation review for {merchant}.",
    )


def suggest_duplicate_dispute(customer_id: int, merchant: str, year_month: str) -> dict:
    action = _base_action(
        customer_id,
        merchant,
        "duplicate_dispute",
        f"Suggested duplicate dispute review for {merchant} in {year_month}.",
    )
    action["year_month"] = year_month
    return action


def suggest_downgrade(customer_id: int, merchant: str) -> dict:
    return _base_action(
        customer_id,
        merchant,
        "downgrade_recommendation",
        f"Suggested downgrade review for {merchant}.",
    )


def approve_action(action: dict) -> dict:
    updated = action.copy()
    updated["status"] = "approved"
    updated["message"] = f"Approved action for {updated['merchant']}."
    return updated


def reject_action(action: dict) -> dict:
    updated = action.copy()
    updated["status"] = "rejected"
    updated["message"] = f"Rejected action for {updated['merchant']}."
    return updated


def execute_action(action: dict) -> dict:
    updated = action.copy()
    updated["status"] = "executed"

    if updated["action_type"] == "cancellation_request":
        updated["message"] = f"Executed mock cancellation workflow for {updated['merchant']}."
    elif updated["action_type"] == "duplicate_dispute":
        updated["message"] = f"Executed mock duplicate dispute workflow for {updated['merchant']}."
    elif updated["action_type"] == "downgrade_recommendation":
        updated["message"] = f"Executed mock downgrade recommendation workflow for {updated['merchant']}."
    else:
        updated["message"] = f"Executed action for {updated['merchant']}."

    return updated
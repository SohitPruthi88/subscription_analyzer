def generate_agent_decision(customer_result: dict, customer_id: int) -> dict:
    duplicates = customer_result["duplicates"]
    overlaps = customer_result["overlaps"]
    price_changes = customer_result["price_changes"]
    monthly_spend = customer_result["monthly_spend"]
    recurring = customer_result["recurring"]

    monthly_spend_value = 0.0
    if not monthly_spend.empty:
        monthly_spend_value = float(
            monthly_spend["total_estimated_monthly_spend"].iloc[0]
        )

    if not duplicates.empty:
        merchant = str(duplicates.iloc[0]["normalized_merchant"])
        year_month = str(duplicates.iloc[0]["year_month"])
        return {
            "priority": "high",
            "decision_type": "suggest_action",
            "title": "Possible duplicate charge detected",
            "message": (
                f"Customer {customer_id} appears to have a duplicate charge for "
                f"{merchant} in {year_month}. The best next step is to suggest a "
                f"duplicate dispute review."
            ),
            "recommended_action": "duplicate_dispute",
            "merchant": merchant,
            "year_month": year_month,
        }

    if not overlaps.empty:
        return {
            "priority": "high",
            "decision_type": "suggest_action",
            "title": "Overlapping plans detected",
            "message": (
                f"Customer {customer_id} may be paying for overlapping plans. "
                f"The best next step is to suggest a downgrade or consolidation review."
            ),
            "recommended_action": "downgrade_review",
            "merchant": None,
            "year_month": None,
        }

    if not price_changes.empty:
        merchant = str(price_changes.iloc[0]["normalized_merchant"])
        return {
            "priority": "medium",
            "decision_type": "ask_question",
            "title": "Price change detected",
            "message": (
                f"{merchant} changed price for customer {customer_id}. "
                f"The agent should ask whether the subscription is still actively used."
            ),
            "recommended_action": "ask_usage_question",
            "merchant": merchant,
            "year_month": None,
        }

    if monthly_spend_value >= 40:
        return {
            "priority": "medium",
            "decision_type": "ask_question",
            "title": "High recurring spend",
            "message": (
                f"Customer {customer_id} spends about ${monthly_spend_value:.2f} per month "
                f"on recurring subscriptions. The agent should ask which subscriptions are "
                f"used regularly and identify optimization opportunities."
            ),
            "recommended_action": "ask_spend_review_question",
            "merchant": None,
            "year_month": None,
        }

    if not recurring.empty:
        return {
            "priority": "low",
            "decision_type": "inform",
            "title": "Subscriptions detected",
            "message": (
                f"Customer {customer_id} has recurring subscriptions, but there is no urgent "
                f"risk signal. The agent should summarize the subscriptions and offer help."
            ),
            "recommended_action": "summarize_only",
            "merchant": None,
            "year_month": None,
        }

    return {
        "priority": "low",
        "decision_type": "inform",
        "title": "No subscription issue detected",
        "message": (
            f"No major subscription optimization signal was detected for customer {customer_id}."
        ),
        "recommended_action": "none",
        "merchant": None,
        "year_month": None,
    }
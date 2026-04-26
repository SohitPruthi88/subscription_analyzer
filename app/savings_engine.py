from typing import Dict


def calculate_savings_opportunity(customer_result: Dict) -> Dict:
    monthly_spend = 0.0
    if not customer_result["monthly_spend"].empty:
        monthly_spend = float(
            customer_result["monthly_spend"]["total_estimated_monthly_spend"].iloc[0]
        )

    duplicate_waste = 0.0
    if not customer_result["duplicates"].empty:
        duplicate_waste = len(customer_result["duplicates"]) * 15  # mock avg

    overlap_waste = 0.0
    if not customer_result["overlaps"].empty:
        overlap_waste = len(customer_result["overlaps"]) * 10

    total_waste = duplicate_waste + overlap_waste

    return {
        "monthly_spend": monthly_spend,
        "estimated_waste": total_waste,
        "annual_savings": total_waste * 12,
    }


def generate_top_issues(customer_result: Dict) -> list[str]:
    issues = []

    if not customer_result["duplicates"].empty:
        issues.append("Duplicate subscription charges detected")

    if not customer_result["overlaps"].empty:
        issues.append("Overlapping subscription plans detected")

    if not customer_result["price_changes"].empty:
        issues.append("Subscription price increases detected")

    if not issues:
        issues.append("No major issues detected")

    return issues


def generate_recommended_actions(customer_result: Dict) -> list[str]:
    actions = []

    if not customer_result["duplicates"].empty:
        actions.append("Review and dispute duplicate charges")

    if not customer_result["overlaps"].empty:
        actions.append("Review overlapping plans and consolidate")

    if not customer_result["price_changes"].empty:
        actions.append("Review subscriptions with price increases")

    if not actions:
        actions.append("No immediate action required")

    return actions
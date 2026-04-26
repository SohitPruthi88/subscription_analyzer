def generate_insights(customer_result: dict, customer_id: int) -> str:
    insights = []

    insights.append(f"Customer {customer_id} subscription summary")

    if not customer_result["monthly_spend"].empty:
        spend = customer_result["monthly_spend"]["total_estimated_monthly_spend"].iloc[0]
        insights.append(f"- Estimated recurring monthly spend: ${spend:.2f}")

    recurring = customer_result["recurring"]
    if not recurring.empty:
        merchants = ", ".join(recurring["normalized_merchant"].tolist())
        insights.append(f"- Active recurring subscriptions: {merchants}")

    if not customer_result["duplicates"].empty:
        dup_merchants = ", ".join(
            customer_result["duplicates"]["normalized_merchant"].astype(str).unique()
        )
        insights.append(f"- Possible duplicate charges detected for: {dup_merchants}")

    if not customer_result["price_changes"].empty:
        changed = ", ".join(
            customer_result["price_changes"]["normalized_merchant"].astype(str).unique()
        )
        insights.append(f"- Price changes detected for: {changed}")

    if not customer_result["overlaps"].empty:
        insights.append("- Overlapping subscription plans detected. Review whether both are needed.")

    if (
        customer_result["duplicates"].empty
        and customer_result["price_changes"].empty
        and customer_result["overlaps"].empty
    ):
        insights.append("- No immediate optimization issue detected.")

    insights.append("- Recommended next action: review duplicate or overlapping subscriptions first.")

    return "\n".join(insights)
def answer_user_question(question: str, customer_result: dict, customer_id: int) -> str:
    q = question.lower().strip()

    monthly_spend_df = customer_result["monthly_spend"]
    recurring_df = customer_result["recurring"]
    duplicates_df = customer_result["duplicates"]
    price_changes_df = customer_result["price_changes"]
    overlaps_df = customer_result["overlaps"]

    if "spend" in q or "monthly" in q or "how much" in q:
        if monthly_spend_df.empty:
            return f"I could not find monthly spend data for customer {customer_id}."
        spend = monthly_spend_df["total_estimated_monthly_spend"].iloc[0]
        return f"Customer {customer_id} is spending about ${spend:.2f} per month on recurring subscriptions."

    if "duplicate" in q or "charged twice" in q or "double charged" in q:
        if duplicates_df.empty:
            return f"I did not find duplicate subscription charges for customer {customer_id}."
        merchants = ", ".join(duplicates_df["normalized_merchant"].astype(str).unique())
        return f"I found possible duplicate charges for customer {customer_id}: {merchants}."

    if "price" in q or "increase" in q or "changed" in q:
        if price_changes_df.empty:
            return f"I did not detect any subscription price changes for customer {customer_id}."
        merchants = ", ".join(price_changes_df["normalized_merchant"].astype(str).unique())
        return f"I found price changes for customer {customer_id} in: {merchants}."

    if "overlap" in q or "overlapping" in q or "similar" in q:
        if overlaps_df.empty:
            return f"I did not detect overlapping subscription plans for customer {customer_id}."
        return f"I found overlapping subscription plan activity for customer {customer_id}. This may indicate duplicated value across similar services."

    if "subscription" in q or "active" in q or "what do i have" in q:
        if recurring_df.empty:
            return f"I did not detect recurring subscriptions for customer {customer_id}."
        merchants = ", ".join(recurring_df["normalized_merchant"].astype(str).tolist())
        return f"Customer {customer_id} has these recurring subscriptions: {merchants}."

    if "cancel" in q or "which one should i cancel" in q or "recommend" in q:
        suggestions = []

        if not duplicates_df.empty:
            dup_merchants = ", ".join(duplicates_df["normalized_merchant"].astype(str).unique())
            suggestions.append(f"review duplicate charges for {dup_merchants}")

        if not overlaps_df.empty:
            suggestions.append("review overlapping plans first")

        if not price_changes_df.empty:
            changed = ", ".join(price_changes_df["normalized_merchant"].astype(str).unique())
            suggestions.append(f"review recent price increases in {changed}")

        if suggestions:
            return f"My recommendation for customer {customer_id}: " + "; ".join(suggestions) + "."

        return f"I do not see an urgent cancellation signal for customer {customer_id}, but reviewing low-usage subscriptions would be the next step."

    return (
        f"I can help with spend, duplicates, price changes, overlaps, active subscriptions, "
        f"and cancellation recommendations for customer {customer_id}."
    )
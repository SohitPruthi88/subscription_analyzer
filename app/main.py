from data_loader import load_transactions
from analyzer import (
    analyze_customer,
    detect_recurring_subscriptions,
    detect_same_month_duplicates,
    detect_price_changes,
    estimate_monthly_subscription_spend,
)


def print_section(title: str):
    print(f"\n{'=' * 12} {title} {'=' * 12}")


def print_dataframe(df, empty_message="No records found."):
    if df.empty:
        print(empty_message)
    else:
        print(df.to_string(index=False))


def main():
    df = load_transactions("data/transactions.csv")

    print_section("ALL CUSTOMERS - RECURRING SUBSCRIPTIONS")
    print_dataframe(detect_recurring_subscriptions(df))

    print_section("ALL CUSTOMERS - SAME MONTH DUPLICATES")
    print_dataframe(detect_same_month_duplicates(df))

    print_section("ALL CUSTOMERS - PRICE CHANGES")
    print_dataframe(detect_price_changes(df))

    print_section("ALL CUSTOMERS - ESTIMATED MONTHLY SPEND")
    print_dataframe(estimate_monthly_subscription_spend(df))

    for customer_id in sorted(df["customer_id"].unique()):
        print_section(f"CUSTOMER {customer_id} SUMMARY")
        result = analyze_customer(df, customer_id)

        print("\nRecurring subscriptions:")
        print_dataframe(result["recurring"])

        print("\nPossible same-month duplicates:")
        print_dataframe(result["duplicates"])

        print("\nPrice changes:")
        print_dataframe(result["price_changes"])

        print("\nOverlapping plan types:")
        print_dataframe(result["overlaps"])

        print("\nEstimated monthly spend:")
        print_dataframe(result["monthly_spend"])

if __name__ == "__main__":
    main()
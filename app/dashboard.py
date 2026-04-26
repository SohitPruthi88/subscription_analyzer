import streamlit as st
import pandas as pd

from data_loader import load_transactions
from analyzer import (
    analyze_customer,
    detect_recurring_subscriptions,
    detect_same_month_duplicates,
    detect_price_changes,
    estimate_monthly_subscription_spend,
)


st.set_page_config(
    page_title="Subscription Analyzer",
    page_icon="💳",
    layout="wide",
)


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def render_dataframe(df: pd.DataFrame, empty_message: str):
    if df.empty:
        st.info(empty_message)
    else:
        st.dataframe(df, use_container_width=True)


def main():
    st.title("💳 Subscription Analyzer")
    st.caption("Analyze recurring payments, duplicate subscriptions, and monthly spend from mock banking transactions.")

    df = load_transactions("data/transactions.csv")

    st.sidebar.header("Controls")
    customer_ids = sorted(df["customer_id"].unique().tolist())
    selected_customer = st.sidebar.selectbox("Select customer", customer_ids)

    st.sidebar.markdown("---")
    show_all_customers = st.sidebar.checkbox("Show all-customer summary", value=True)

    st.subheader("Overview")

    all_monthly_spend = estimate_monthly_subscription_spend(df)
    customer_result = analyze_customer(df, selected_customer)

    col1, col2, col3, col4 = st.columns(4)

    recurring_count = len(customer_result["recurring"])
    duplicate_count = len(customer_result["duplicates"])
    price_change_count = len(customer_result["price_changes"])

    monthly_spend_value = 0.0
    if not customer_result["monthly_spend"].empty:
        monthly_spend_value = customer_result["monthly_spend"]["total_estimated_monthly_spend"].iloc[0]

    col1.metric("Customer ID", str(selected_customer))
    col2.metric("Recurring subscriptions", recurring_count)
    col3.metric("Duplicate patterns", duplicate_count)
    col4.metric("Estimated monthly spend", format_currency(monthly_spend_value))

    st.markdown("---")

    if show_all_customers:
        st.subheader("All Customers Summary")

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("**Estimated Monthly Spend by Customer**")
            render_dataframe(all_monthly_spend, "No spend data found.")

        with col_right:
            st.markdown("**All Customers - Price Changes**")
            render_dataframe(detect_price_changes(df), "No price changes found.")

        st.markdown("**All Customers - Same Month Duplicates**")
        render_dataframe(
            detect_same_month_duplicates(df),
            "No same-month duplicate charges found.",
        )

        st.markdown("---")

    st.subheader(f"Customer {selected_customer} Analysis")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Recurring Subscriptions",
            "Duplicates",
            "Price Changes",
            "Overlapping Plans",
            "Recommendations",
        ]
    )

    with tab1:
        st.markdown("### Recurring Subscriptions")
        render_dataframe(
            customer_result["recurring"],
            "No recurring subscriptions detected.",
        )

    with tab2:
        st.markdown("### Same-Month Duplicates")
        render_dataframe(
            customer_result["duplicates"],
            "No duplicate charges detected.",
        )

    with tab3:
        st.markdown("### Price Changes")
        render_dataframe(
            customer_result["price_changes"],
            "No price changes detected.",
        )

    with tab4:
        st.markdown("### Overlapping Subscription Types")
        render_dataframe(
            customer_result["overlaps"],
            "No overlapping plan types detected.",
        )

    with tab5:
        st.markdown("### Recommendation Preview")
        st.write(generate_recommendation(customer_result, selected_customer))


def generate_recommendation(customer_result: dict, customer_id: int) -> str:
    messages = [f"Customer {customer_id} summary:"]

    if not customer_result["monthly_spend"].empty:
        spend = customer_result["monthly_spend"]["total_estimated_monthly_spend"].iloc[0]
        messages.append(f"- Estimated monthly recurring spend is ${spend:.2f}.")

    if not customer_result["duplicates"].empty:
        messages.append("- There are possible duplicate charges that should be reviewed first.")

    if not customer_result["price_changes"].empty:
        messages.append("- One or more subscriptions have changed price over time.")

    if not customer_result["overlaps"].empty:
        messages.append("- There may be overlapping plans that provide similar benefits.")

    if (
        customer_result["duplicates"].empty
        and customer_result["price_changes"].empty
        and customer_result["overlaps"].empty
    ):
        messages.append("- No major optimization signals detected yet.")

    messages.append("- Next step: ask the customer which subscriptions they actively use each month.")

    return "\n".join(messages)


if __name__ == "__main__":
    main()
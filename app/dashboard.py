import streamlit as st
import pandas as pd

from assistant import answer_user_question
from ai_insights import generate_insights
from data_loader import load_transactions
from analyzer import (
    analyze_customer,
    detect_recurring_subscriptions,
    detect_same_month_duplicates,
    detect_price_changes,
    estimate_monthly_subscription_spend,
)
from actions import (
    suggest_cancellation,
    suggest_duplicate_dispute,
    suggest_downgrade,
    approve_action,
    reject_action,
    execute_action,
)
from action_store import (
    initialize_action_store,
    add_action,
    get_action_log,
    get_actions_for_customer,
    update_action,
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
    initialize_action_store()

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

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "Recurring Subscriptions",
            "Duplicates",
            "Price Changes",
            "Overlapping Plans",
            "Recommendations",
            "Ask AI",
            "Action Center",
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

    #with tab5:
    #    st.markdown("### Recommendation Preview")
    #    st.write(generate_insights(customer_result, selected_customer))

    with tab5:
        st.markdown("### Recommendation Preview")
        insights = generate_insights(customer_result, selected_customer)
        st.success(insights)

    with tab6:
        st.markdown("### Ask AI About This Customer")

        example_questions = [
            "How much am I spending per month?",
            "Do I have duplicate subscriptions?",
            "What subscriptions do I have?",
            "What changed this month?",
            "Which one should I cancel first?",
        ]

    with tab7:
        st.markdown("### Action Center")

            recurring_options = []
            if not customer_result["recurring"].empty:
                recurring_options = customer_result["recurring"]["normalized_merchant"].astype(str).unique().tolist()

            duplicate_options = []
            if not customer_result["duplicates"].empty:
                duplicate_options = customer_result["duplicates"]["normalized_merchant"].astype(str).unique().tolist()

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Draft Cancellation Request")
                if recurring_options:
                    cancel_merchant = st.selectbox(
                        "Choose subscription to cancel",
                        recurring_options,
                        key="cancel_merchant"
                    )
                    if st.button("Draft Cancellation", key="draft_cancel"):
                        action = create_cancellation_request(selected_customer, cancel_merchant)
                        add_action(action)
                        st.success(action["message"])
                else:
                    st.info("No recurring subscriptions available for cancellation review.")

                st.markdown("#### Recommend Downgrade")
                if recurring_options:
                    downgrade_merchant = st.selectbox(
                        "Choose subscription to review for downgrade",
                        recurring_options,
                        key="downgrade_merchant"
                    )
                    if st.button("Recommend Downgrade", key="recommend_downgrade"):
                        action = create_downgrade_recommendation(selected_customer, downgrade_merchant)
                        add_action(action)
                        st.success(action["message"])
                else:
                    st.info("No subscriptions available for downgrade review.")

            with col2:
                st.markdown("#### Flag Duplicate Charge")
                if not customer_result["duplicates"].empty:
                    duplicate_row_labels = [
                        f"{row['normalized_merchant']} ({row['year_month']})"
                        for _, row in customer_result["duplicates"].iterrows()
                    ]
                    selected_duplicate = st.selectbox(
                        "Choose duplicate charge",
                        duplicate_row_labels,
                        key="duplicate_choice"
                    )
                    if st.button("Flag Duplicate", key="flag_duplicate"):
                        selected_row = customer_result["duplicates"].iloc[
                            duplicate_row_labels.index(selected_duplicate)]
                        action = create_duplicate_dispute(
                            selected_customer,
                            selected_row["normalized_merchant"],
                            selected_row["year_month"],
                        )
                        add_action(action)
                        st.success(action["message"])
                else:
                    st.info("No duplicate charges available for dispute review.")

            st.markdown("---")
            st.markdown("#### Action History")
            action_log_df = get_action_log()
            if action_log_df.empty:
                st.info("No actions recorded yet.")
            else:
                st.dataframe(action_log_df, use_container_width=True)

        selected_example = st.selectbox("Try an example question", [""] + example_questions)

        user_question = st.text_input(
            "Or type your own question",
            value=selected_example
        )

        if st.button("Get Answer"):
            if user_question.strip():
                answer = answer_user_question(user_question, customer_result, selected_customer)
                st.info(answer)
            else:
                st.warning("Please enter a question.")

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
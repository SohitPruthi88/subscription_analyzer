import pandas as pd
import streamlit as st

from action_store import (
    add_action,
    get_action_log,
    get_actions_for_customer,
    initialize_action_store,
    update_action,
)
from actions import (
    approve_action,
    execute_action,
    reject_action,
    suggest_cancellation,
    suggest_downgrade,
    suggest_duplicate_dispute,
)
from ai_insights import generate_insights
from analyzer import (
    analyze_customer,
    detect_price_changes,
    detect_same_month_duplicates,
    estimate_monthly_subscription_spend,
)
from assistant import answer_user_question
from data_loader import load_transactions
from orchestrator import generate_agent_decision

from llm_client import answer_with_llm, generate_llm_recommendation


st.set_page_config(
    page_title="Subscription Analyzer",
    page_icon="💳",
    layout="wide",
)


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def render_dataframe(df: pd.DataFrame, empty_message: str) -> None:
    if df.empty:
        st.info(empty_message)
    else:
        st.dataframe(df, use_container_width=True)


def get_monthly_spend_value(customer_result: dict) -> float:
    monthly_spend_df = customer_result["monthly_spend"]
    if monthly_spend_df.empty:
        return 0.0
    return float(monthly_spend_df["total_estimated_monthly_spend"].iloc[0])


def main() -> None:
    st.title("💳 Subscription Analyzer")
    st.caption(
        "Analyze recurring payments, duplicate subscriptions, price changes, "
        "and mock follow-up actions from banking-style transaction data."
    )

    df = load_transactions("data/transactions.csv")
    initialize_action_store()

    st.sidebar.header("Controls")
    customer_ids = sorted(df["customer_id"].unique().tolist())
    selected_customer = st.sidebar.selectbox("Select customer", customer_ids)

    st.sidebar.markdown("---")
    show_all_customers = st.sidebar.checkbox(
        "Show all-customer summary",
        value=True,
    )

    customer_result = analyze_customer(df, selected_customer)
    all_monthly_spend = estimate_monthly_subscription_spend(df)
    agent_decision = generate_agent_decision(customer_result, selected_customer)

    st.subheader("Overview")

    recurring_count = len(customer_result["recurring"])
    duplicate_count = len(customer_result["duplicates"])
    price_change_count = len(customer_result["price_changes"])
    monthly_spend_value = get_monthly_spend_value(customer_result)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Customer ID", str(selected_customer))
    metric_col2.metric("Recurring subscriptions", recurring_count)
    metric_col3.metric("Duplicate patterns", duplicate_count)
    metric_col4.metric("Estimated monthly spend", format_currency(monthly_spend_value))

    st.markdown("---")

    if show_all_customers:
        st.subheader("All Customers Summary")

        summary_col1, summary_col2 = st.columns(2)

        with summary_col1:
            st.markdown("**Estimated Monthly Spend by Customer**")
            render_dataframe(all_monthly_spend, "No spend data found.")

        with summary_col2:
            st.markdown("**All Customers - Price Changes**")
            render_dataframe(detect_price_changes(df), "No price changes found.")

        st.markdown("**All Customers - Same Month Duplicates**")
        render_dataframe(
            detect_same_month_duplicates(df),
            "No same-month duplicate charges found.",
        )

        st.markdown("---")

    st.subheader(f"Customer {selected_customer} Analysis")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
        [
            "Recurring Subscriptions",
            "Duplicates",
            "Price Changes",
            "Overlapping Plans",
            "Recommendations",
            "Ask AI",
            "Action Center",
            "Agent Decision",
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

        selected_example = st.selectbox(
            "Try an example question",
            [""] + example_questions,
        )

        user_question = st.text_input(
            "Or type your own question",
            value=selected_example,
        )

        if st.button("Get Answer"):
            if user_question.strip():
                answer = answer_user_question(
                    user_question,
                    customer_result,
                    selected_customer,
                )
                st.info(answer)
            else:
                st.warning("Please enter a question.")

    with tab7:
        st.markdown("### Action Center")
        st.caption(
            "Suggest actions first, then approve or reject them, and execute only approved actions."
        )

        recurring_options = []
        if not customer_result["recurring"].empty:
            recurring_options = (
                customer_result["recurring"]["normalized_merchant"]
                .astype(str)
                .unique()
                .tolist()
            )

        action_col1, action_col2 = st.columns(2)

        with action_col1:
            st.markdown("#### Suggest Cancellation Review")
            if recurring_options:
                cancel_merchant = st.selectbox(
                    "Choose subscription",
                    recurring_options,
                    key="suggest_cancel_merchant",
                )
                if st.button("Suggest Cancellation Action", key="suggest_cancel"):
                    action = suggest_cancellation(selected_customer, cancel_merchant)
                    add_action(action)
                    st.success(action["message"])
            else:
                st.info("No recurring subscriptions available.")

            st.markdown("#### Suggest Downgrade Review")
            if recurring_options:
                downgrade_merchant = st.selectbox(
                    "Choose subscription to review",
                    recurring_options,
                    key="suggest_downgrade_merchant",
                )
                if st.button("Suggest Downgrade Action", key="suggest_downgrade"):
                    action = suggest_downgrade(selected_customer, downgrade_merchant)
                    add_action(action)
                    st.success(action["message"])
            else:
                st.info("No subscriptions available.")

        with action_col2:
            st.markdown("#### Suggest Duplicate Dispute")
            if not customer_result["duplicates"].empty:
                duplicate_row_labels = [
                    f"{row['normalized_merchant']} ({row['year_month']})"
                    for _, row in customer_result["duplicates"].iterrows()
                ]
                selected_duplicate = st.selectbox(
                    "Choose duplicate issue",
                    duplicate_row_labels,
                    key="suggest_duplicate_choice",
                )
                if st.button("Suggest Duplicate Dispute", key="suggest_duplicate"):
                    selected_row = customer_result["duplicates"].iloc[
                        duplicate_row_labels.index(selected_duplicate)
                    ]
                    action = suggest_duplicate_dispute(
                        selected_customer,
                        str(selected_row["normalized_merchant"]),
                        str(selected_row["year_month"]),
                    )
                    add_action(action)
                    st.success(action["message"])
            else:
                st.info("No duplicate issues available.")

        st.markdown("---")
        st.markdown("### Pending and Historical Actions")

        customer_actions = get_actions_for_customer(selected_customer)

        if not customer_actions:
            st.info("No actions recorded yet for this customer.")
        else:
            for action in customer_actions:
                st.markdown(
                    f"**Action ID:** {action['action_id']} | "
                    f"**Merchant:** {action['merchant']} | "
                    f"**Type:** {action['action_type']} | "
                    f"**Status:** {action['status']}"
                )
                st.write(action["message"])

                button_col1, button_col2, button_col3 = st.columns(3)

                if action["status"] == "suggested":
                    with button_col1:
                        if st.button(
                            f"Approve {action['action_id']}",
                            key=f"approve_{action['action_id']}",
                        ):
                            updated = approve_action(action)
                            update_action(action["action_id"], updated)
                            st.rerun()

                    with button_col2:
                        if st.button(
                            f"Reject {action['action_id']}",
                            key=f"reject_{action['action_id']}",
                        ):
                            updated = reject_action(action)
                            update_action(action["action_id"], updated)
                            st.rerun()

                elif action["status"] == "approved":
                    with button_col3:
                        if st.button(
                            f"Execute {action['action_id']}",
                            key=f"execute_{action['action_id']}",
                        ):
                            updated = execute_action(action)
                            update_action(action["action_id"], updated)
                            st.rerun()

                st.markdown("---")

        st.markdown("#### Full Action Log")
        action_log_df = get_action_log()
        if action_log_df.empty:
            st.info("No actions recorded yet.")
        else:
            st.dataframe(action_log_df, use_container_width=True)

    with tab8:
        st.markdown("### Agent Decision")
        st.markdown(f"**Priority:** {agent_decision['priority'].upper()}")
        st.markdown(f"**Decision Type:** {agent_decision['decision_type']}")
        st.markdown(f"**Title:** {agent_decision['title']}")
        st.info(agent_decision["message"])

        if agent_decision["recommended_action"] != "none":
            st.markdown(
                f"**Recommended Next Step:** `{agent_decision['recommended_action']}`"
            )

        auto_col1, auto_col2 = st.columns(2)

        with auto_col1:
            if agent_decision["recommended_action"] == "duplicate_dispute":
                if st.button("Auto-suggest duplicate dispute"):
                    action = suggest_duplicate_dispute(
                        selected_customer,
                        agent_decision["merchant"],
                        agent_decision["year_month"],
                    )
                    add_action(action)
                    st.success("Duplicate dispute action suggested and added to Action Center.")

            elif agent_decision["recommended_action"] == "downgrade_review":
                recurring_df = customer_result["recurring"]
                if not recurring_df.empty:
                    merchant = str(recurring_df.iloc[0]["normalized_merchant"])
                    if st.button("Auto-suggest downgrade review"):
                        action = suggest_downgrade(selected_customer, merchant)
                        add_action(action)
                        st.success("Downgrade review action suggested and added to Action Center.")

        with auto_col2:
            if agent_decision["recommended_action"] == "ask_usage_question":
                st.warning(
                    "Suggested follow-up question: Are you still actively using this subscription every month?"
                )

            elif agent_decision["recommended_action"] == "ask_spend_review_question":
                st.warning(
                    "Suggested follow-up question: Which of these subscriptions do you use at least once a week?"
                )


if __name__ == "__main__":
    main()
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
from agent_controller import (
    answer_agent_question,
    build_suggested_action_from_decision,
    decide_next_step,
    generate_agent_summary,
    get_follow_up_question,
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
from llm_client import answer_with_llm, generate_llm_recommendation
from memory import (
    add_agent_trace,
    add_chat_message,
    clear_agent_trace,
    clear_chat_history,
    get_agent_trace,
    get_chat_history,
    initialize_memory_store,
)
from planner_agent import run_planner_agent
from savings_engine import (
    calculate_savings_opportunity,
    generate_recommended_actions,
    generate_top_issues,
)
from tool_agent import run_tool_agent
from upload_utils import normalize_columns, validate_mapping


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


def load_active_dataframe() -> pd.DataFrame:
    if "uploaded_df" in st.session_state:
        return st.session_state["uploaded_df"]
    return load_transactions("data/transactions.csv")


def main() -> None:
    st.title("💳 Subscription Analyzer")
    st.caption(
        "Analyze recurring payments, duplicate subscriptions, price changes, "
        "and mock follow-up actions from banking-style transaction data."
    )

    initialize_action_store()
    initialize_memory_store()

    df = load_active_dataframe()

    st.sidebar.header("Controls")

    if "uploaded_df" in st.session_state:
        st.sidebar.success("Using uploaded dataset for analysis")
        st.sidebar.info("Go to '💰 Savings Opportunity' to view updated insights.")
        if st.sidebar.button("Reset to default demo dataset"):
            st.session_state.pop("uploaded_df", None)
            st.session_state.pop("data_uploaded", None)
            st.rerun()

    customer_ids = sorted(df["customer_id"].unique().tolist())
    selected_customer = st.sidebar.selectbox("Select customer", customer_ids)

    st.sidebar.markdown("---")
    show_all_customers = st.sidebar.checkbox(
        "Show all-customer summary",
        value=True,
    )

    use_llm = st.sidebar.checkbox(
        "Use Azure OpenAI for Recommendations and Ask AI",
        value=False,
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Session Tools")

    if st.sidebar.button("Clear chat history for this customer"):
        clear_chat_history(selected_customer)
        st.sidebar.success("Chat history cleared.")

    if st.sidebar.button("Clear trace for this customer"):
        clear_agent_trace(selected_customer)
        st.sidebar.success("Agent trace cleared.")

    customer_result = analyze_customer(df, selected_customer)
    all_monthly_spend = estimate_monthly_subscription_spend(df)
    agent_decision = decide_next_step(customer_result, selected_customer)

    if "data_uploaded" in st.session_state:
        st.warning("Viewing insights for uploaded dataset")

    st.subheader("Overview")

    recurring_count = len(customer_result["recurring"])
    duplicate_count = len(customer_result["duplicates"])
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

    (
        tab_upload,
        tab0,
        tab1,
        tab2,
        tab3,
        tab4,
        tab5,
        tab6,
        tab7,
        tab8,
        tab9,
        tab10,
        tab11,
    ) = st.tabs(
        [
            "📂 Upload Data",
            "💰 Savings Opportunity",
            "Recurring Subscriptions",
            "Duplicates",
            "Price Changes",
            "Overlapping Plans",
            "Recommendations",
            "Ask AI",
            "Action Center",
            "Agent Decision",
            "Memory & Trace",
            "Tool Agent",
            "Planner Agent",
        ]
    )

    with tab_upload:
        st.markdown("## 📂 Upload Bank Statement")
        st.caption(
            "Upload a CSV, map the key columns, and the rest of the app will automatically switch to the uploaded dataset."
        )

        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

        if uploaded_file:
            raw_df = pd.read_csv(uploaded_file)

            st.markdown("### Preview Data")
            st.dataframe(raw_df.head(), use_container_width=True)

            st.markdown("### Map Columns")
            columns = raw_df.columns.tolist()

            date_col = st.selectbox("Date column", columns, key="upload_date_col")
            merchant_col = st.selectbox("Merchant column", columns, key="upload_merchant_col")
            amount_col = st.selectbox("Amount column", columns, key="upload_amount_col")

            mapping = {
                date_col: "date",
                merchant_col: "merchant",
                amount_col: "amount",
            }

            if st.button("Process Data", key="process_uploaded_data"):
                if validate_mapping(mapping):
                    processed_df = normalize_columns(raw_df, mapping)
                    st.session_state["uploaded_df"] = processed_df
                    st.session_state["data_uploaded"] = True
                    st.success("Data loaded successfully. Navigate to '💰 Savings Opportunity' to view insights.")
                    st.info("The entire app will now use the uploaded dataset.")
                    st.rerun()
                else:
                    st.error("Please map all required fields.")

        if "uploaded_df" in st.session_state:
            st.success("Using uploaded dataset for analysis")
            st.info("Go to '💰 Savings Opportunity' tab to see insights")

            st.markdown("### Processed Data Preview")
            st.dataframe(st.session_state["uploaded_df"].head(), use_container_width=True)

    with tab0:
        st.markdown("## 💰 Subscription Savings Opportunity")

        savings = calculate_savings_opportunity(customer_result)
        issues = generate_top_issues(customer_result)
        actions = generate_recommended_actions(customer_result)

        savings_col1, savings_col2, savings_col3 = st.columns(3)
        savings_col1.metric("Monthly Spend", f"${savings['monthly_spend']:.2f}")
        savings_col2.metric("Potential Monthly Waste", f"${savings['estimated_waste']:.2f}")
        savings_col3.metric("Annual Savings Opportunity", f"${savings['annual_savings']:.2f}")

        st.markdown("---")
        st.markdown("### ⚠️ Key Issues Identified")
        for issue in issues:
            st.warning(issue)

        st.markdown("### 🚀 Recommended Actions")
        for action in actions:
            st.success(action)

        st.markdown("---")
        st.markdown("### 💡 What This Means")
        st.info(
            "This customer has opportunities to reduce recurring spend by reviewing duplicate, "
            "overlapping, or increased-cost subscriptions. Immediate action can unlock measurable savings."
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

        if use_llm:
            try:
                llm_text = generate_llm_recommendation(customer_result, selected_customer)
                add_agent_trace(
                    selected_customer,
                    "recommendation",
                    "Generated recommendation using Azure OpenAI.",
                    {"mode": "llm"},
                )
                st.success(llm_text)
            except Exception as exc:
                st.error(f"Azure OpenAI recommendation failed: {exc}")
                fallback_text = generate_insights(customer_result, selected_customer)
                add_agent_trace(
                    selected_customer,
                    "recommendation_fallback",
                    "Recommendation fallback used after Azure OpenAI failure.",
                    {"mode": "rule_based", "error": str(exc)},
                )
                st.info("Showing rule-based fallback recommendation.")
                st.success(fallback_text)
        else:
            insights = generate_insights(customer_result, selected_customer)
            add_agent_trace(
                selected_customer,
                "recommendation_rule_based",
                "Generated recommendation using rule-based logic.",
                {"mode": "rule_based"},
            )
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
                add_chat_message(selected_customer, "user", user_question)

                if use_llm:
                    try:
                        answer = answer_agent_question(
                            user_question,
                            customer_result,
                            selected_customer,
                            use_llm=True,
                        )
                        add_chat_message(selected_customer, "assistant", answer)
                        add_agent_trace(
                            selected_customer,
                            "ask_ai_llm",
                            f"Answered user question with Azure OpenAI: {user_question}",
                            {"mode": "llm"},
                        )
                        st.info(answer)
                    except Exception as exc:
                        st.error(f"Azure OpenAI answer failed: {exc}")
                        fallback_answer = answer_user_question(
                            user_question,
                            customer_result,
                            selected_customer,
                        )
                        add_chat_message(selected_customer, "assistant", fallback_answer)
                        add_agent_trace(
                            selected_customer,
                            "ask_ai_fallback",
                            f"Fallback answer used for question: {user_question}",
                            {"mode": "rule_based", "error": str(exc)},
                        )
                        st.info("Showing rule-based fallback answer.")
                        st.info(fallback_answer)
                else:
                    answer = answer_agent_question(
                        user_question,
                        customer_result,
                        selected_customer,
                        use_llm=False,
                    )
                    add_chat_message(selected_customer, "assistant", answer)
                    add_agent_trace(
                        selected_customer,
                        "ask_ai_rule_based",
                        f"Answered user question with rule-based logic: {user_question}",
                        {"mode": "rule_based"},
                    )
                    st.info(answer)
            else:
                st.warning("Please enter a question.")

        st.markdown("---")
        st.markdown("### Conversation History")

        chat_history = get_chat_history(selected_customer)
        if not chat_history:
            st.info("No conversation history yet for this customer.")
        else:
            for msg in chat_history:
                if msg["role"] == "user":
                    st.markdown(f"**You:** {msg['content']}")
                else:
                    st.markdown(f"**Assistant:** {msg['content']}")

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
                    add_agent_trace(
                        selected_customer,
                        "manual_action_suggested",
                        f"Manually suggested cancellation action for {cancel_merchant}.",
                        {"action_type": "cancellation_request"},
                    )
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
                    add_agent_trace(
                        selected_customer,
                        "manual_action_suggested",
                        f"Manually suggested downgrade review for {downgrade_merchant}.",
                        {"action_type": "downgrade_review"},
                    )
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
                    add_agent_trace(
                        selected_customer,
                        "manual_action_suggested",
                        f"Manually suggested duplicate dispute for {selected_row['normalized_merchant']}.",
                        {"action_type": "duplicate_dispute"},
                    )
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
                            add_agent_trace(
                                selected_customer,
                                "action_approved",
                                f"Approved action {action['action_id']} for {action['merchant']}.",
                                {"action_type": action["action_type"]},
                            )
                            st.rerun()

                    with button_col2:
                        if st.button(
                            f"Reject {action['action_id']}",
                            key=f"reject_{action['action_id']}",
                        ):
                            updated = reject_action(action)
                            update_action(action["action_id"], updated)
                            add_agent_trace(
                                selected_customer,
                                "action_rejected",
                                f"Rejected action {action['action_id']} for {action['merchant']}.",
                                {"action_type": action["action_type"]},
                            )
                            st.rerun()

                elif action["status"] == "approved":
                    with button_col3:
                        if st.button(
                            f"Execute {action['action_id']}",
                            key=f"execute_{action['action_id']}",
                        ):
                            updated = execute_action(action)
                            update_action(action["action_id"], updated)
                            add_agent_trace(
                                selected_customer,
                                "action_executed",
                                f"Executed action {action['action_id']} for {action['merchant']}.",
                                {"action_type": action["action_type"]},
                            )
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
        st.caption("This is the central controller view for the next best action.")

        st.markdown(f"**Priority:** {agent_decision['priority'].upper()}")
        st.markdown(f"**Decision Type:** {agent_decision['decision_type']}")
        st.markdown(f"**Title:** {agent_decision['title']}")
        st.info(agent_decision["message"])

        if agent_decision["recommended_action"] != "none":
            st.markdown(
                f"**Recommended Next Step:** `{agent_decision['recommended_action']}`"
            )

        st.markdown("---")
        st.markdown("### Controller-Generated Summary")

        controller_summary = generate_agent_summary(
            customer_result,
            selected_customer,
            use_llm=use_llm,
        )
        st.success(controller_summary)

        st.markdown("---")
        st.markdown("### Controller Follow-Up")

        follow_up_question = get_follow_up_question(agent_decision)
        if follow_up_question:
            st.warning(follow_up_question)
            add_agent_trace(
                selected_customer,
                "follow_up_question",
                f"Suggested follow-up question: {follow_up_question}",
                {"recommended_action": agent_decision["recommended_action"]},
            )
        else:
            st.info("No follow-up question required right now.")

        st.markdown("---")
        st.markdown("### Controller Suggested Action")

        if st.button("Create Suggested Action From Decision"):
            action = build_suggested_action_from_decision(
                agent_decision,
                selected_customer,
            )
            if action:
                add_action(action)
                add_agent_trace(
                    selected_customer,
                    "controller_action_created",
                    f"Controller created action for {action['merchant']}.",
                    {"action_type": action["action_type"]},
                )
                st.success("Controller-created suggested action added to Action Center.")
            else:
                add_agent_trace(
                    selected_customer,
                    "controller_no_action",
                    "Controller decision did not create an action.",
                    {"recommended_action": agent_decision["recommended_action"]},
                )
                st.info("This decision does not create an action automatically.")

    with tab9:
        st.markdown("### Memory & Trace")

        history_col, trace_col = st.columns(2)

        with history_col:
            st.markdown("#### Chat Memory")
            chat_history = get_chat_history(selected_customer)
            if not chat_history:
                st.info("No chat history stored yet.")
            else:
                for msg in chat_history:
                    st.markdown(f"**{msg['role'].title()}:** {msg['content']}")

        with trace_col:
            st.markdown("#### Agent Trace")
            trace_df = get_agent_trace(selected_customer)
            if trace_df.empty:
                st.info("No trace events recorded yet.")
            else:
                st.dataframe(trace_df, use_container_width=True)

    with tab10:
        st.markdown("### Tool Agent")
        st.caption(
            "The model selects one tool, the app executes it, and the agent summarizes the result."
        )

        example_tool_questions = [
            "Do I have duplicate subscriptions?",
            "What am I spending every month?",
            "What changed this month?",
            "Create a dispute for the duplicate charge.",
            "Create a downgrade recommendation for me.",
            "What subscriptions do I have?",
        ]

        selected_tool_example = st.selectbox(
            "Try a tool-agent example",
            [""] + example_tool_questions,
            key="tool_agent_example",
        )

        tool_agent_question = st.text_input(
            "Ask the tool agent",
            value=selected_tool_example,
            key="tool_agent_question",
        )

        if st.button("Run Tool Agent"):
            if tool_agent_question.strip():
                result = run_tool_agent(
                    tool_agent_question,
                    customer_result,
                    selected_customer,
                    use_llm=use_llm,
                )

                add_agent_trace(
                    selected_customer,
                    "tool_agent_run",
                    f"Tool agent selected {result['tool_choice']['tool_name']}.",
                    {
                        "selection_mode": result["selection_mode"],
                        "answer_mode": result["answer_mode"],
                        "reason": result["tool_choice"]["reason"],
                    },
                )

                st.markdown("#### Selected Tool")
                st.code(result["tool_choice"]["tool_name"])

                st.markdown("#### Why This Tool")
                st.info(result["tool_choice"]["reason"])

                st.markdown("#### Agent Answer")
                st.success(result["final_answer"])

                st.markdown("#### Raw Tool Result")
                st.json(result["tool_result"])

                if (
                    result["tool_result"]["result_type"] == "action"
                    and result["tool_result"].get("created_action") is not None
                ):
                    if st.button("Add Created Action to Action Center", key="add_tool_action"):
                        add_action(result["tool_result"]["created_action"])
                        add_agent_trace(
                            selected_customer,
                            "tool_agent_action_added",
                            f"Added tool-created action for {result['tool_result']['created_action']['merchant']}.",
                            {"action_type": result["tool_result"]["created_action"]["action_type"]},
                        )
                        st.success("Tool-created action added to Action Center.")
            else:
                st.warning("Please enter a question for the tool agent.")

    with tab11:
        st.markdown("### Planner Agent")
        st.caption(
            "The planner inspects the customer state, creates a workflow plan, runs the first inspection step, and optionally prepares an action."
        )

        if st.button("Run Planner Agent"):
            planner_result = run_planner_agent(
                customer_result,
                selected_customer,
                use_llm=use_llm,
            )

            plan = planner_result["plan"]
            inspection_result = planner_result["inspection_result"]
            action_result = planner_result["action_result"]

            add_agent_trace(
                selected_customer,
                "planner_run",
                f"Planner agent ran for issue type {plan['issue_type']}.",
                {
                    "priority": plan["priority"],
                    "recommended_tool": plan["recommended_tool"],
                    "recommended_action_tool": plan["recommended_action_tool"],
                },
            )

            st.markdown("#### Plan Summary")
            st.markdown(f"**Title:** {plan['title']}")
            st.markdown(f"**Priority:** {plan['priority'].upper()}")
            st.markdown(f"**Issue Type:** {plan['issue_type']}")

            st.markdown("#### Planned Steps")
            for idx, step in enumerate(plan["steps"], start=1):
                st.write(f"{idx}. {step}")

            st.markdown("#### Final Recommendation")
            st.success(plan["final_recommendation"])

            st.markdown("#### Follow-Up Question")
            if plan["follow_up_question"]:
                st.warning(plan["follow_up_question"])
            else:
                st.info("No follow-up question needed.")

            st.markdown("#### Inspection Result")
            st.code(inspection_result["tool_choice"]["tool_name"])
            st.info(inspection_result["final_answer"])

            st.markdown("#### Inspection Raw Output")
            st.json(inspection_result["tool_result"])

            if action_result is not None:
                st.markdown("#### Planned Action Result")
                st.code(action_result["tool_choice"]["tool_name"])
                st.info(action_result["final_answer"])
                st.json(action_result["tool_result"])

                if (
                    action_result["tool_result"]["result_type"] == "action"
                    and action_result["tool_result"].get("created_action") is not None
                ):
                    if st.button("Add Planner Action to Action Center"):
                        add_action(action_result["tool_result"]["created_action"])
                        add_agent_trace(
                            selected_customer,
                            "planner_action_added",
                            f"Planner action added for {action_result['tool_result']['created_action']['merchant']}.",
                            {"action_type": action_result["tool_result"]["created_action"]["action_type"]},
                        )
                        st.success("Planner-created action added to Action Center.")
        else:
            st.info("Click 'Run Planner Agent' to generate a workflow plan.")


if __name__ == "__main__":
    main()
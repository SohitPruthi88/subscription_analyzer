from typing import Any, Dict, List

from tool_agent import run_tool_agent


def build_plan_steps(issue_type: str) -> List[str]:
    if issue_type == "duplicate":
        return [
            "Inspect duplicate subscription signals",
            "Summarize the duplicate issue for the customer",
            "Create a duplicate dispute action",
            "Send the action to Action Center for approval",
        ]

    if issue_type == "overlap":
        return [
            "Inspect overlapping subscription plans",
            "Ask whether both plans are actively used",
            "Recommend downgrade or consolidation",
            "Create a downgrade action if appropriate",
        ]

    if issue_type == "price_change":
        return [
            "Inspect price change patterns",
            "Explain which subscription changed price",
            "Ask whether the subscription is still worth keeping",
            "Recommend review before cancellation",
        ]

    if issue_type == "high_spend":
        return [
            "Calculate monthly recurring spend",
            "Summarize major recurring subscriptions",
            "Ask which subscriptions are used weekly",
            "Suggest optimization review",
        ]

    return [
        "Inspect recurring subscriptions",
        "Summarize current subscription footprint",
        "Offer next-step help if needed",
    ]


def detect_primary_issue(customer_result: Dict[str, Any]) -> Dict[str, str]:
    if not customer_result["duplicates"].empty:
        return {
            "issue_type": "duplicate",
            "priority": "high",
            "title": "Duplicate subscription issue detected",
        }

    if not customer_result["overlaps"].empty:
        return {
            "issue_type": "overlap",
            "priority": "high",
            "title": "Overlapping plans detected",
        }

    if not customer_result["price_changes"].empty:
        return {
            "issue_type": "price_change",
            "priority": "medium",
            "title": "Price change detected",
        }

    monthly_spend_df = customer_result["monthly_spend"]
    if not monthly_spend_df.empty:
        spend = float(monthly_spend_df["total_estimated_monthly_spend"].iloc[0])
        if spend >= 40:
            return {
                "issue_type": "high_spend",
                "priority": "medium",
                "title": "High recurring spend detected",
            }

    return {
        "issue_type": "general_review",
        "priority": "low",
        "title": "General subscription review",
    }


def get_follow_up_question_for_issue(issue_type: str) -> str | None:
    if issue_type == "duplicate":
        return "Would you like me to create a duplicate dispute action for review?"

    if issue_type == "overlap":
        return "Are you actively using both subscription plans, or should I prepare a downgrade review?"

    if issue_type == "price_change":
        return "Do you still use this subscription enough to justify the new price?"

    if issue_type == "high_spend":
        return "Which of these subscriptions do you use at least once a week?"

    return None


def get_recommended_tool_for_issue(issue_type: str) -> str:
    if issue_type == "duplicate":
        return "get_duplicate_subscriptions"

    if issue_type == "overlap":
        return "get_overlapping_plans"

    if issue_type == "price_change":
        return "get_price_changes"

    if issue_type == "high_spend":
        return "get_monthly_spend"

    return "get_recurring_subscriptions"


def get_recommended_action_tool(issue_type: str) -> str | None:
    if issue_type == "duplicate":
        return "create_duplicate_dispute_action"

    if issue_type == "overlap":
        return "create_downgrade_action"

    return None


def generate_planner_summary(
    customer_result: Dict[str, Any],
    customer_id: int,
) -> Dict[str, Any]:
    issue = detect_primary_issue(customer_result)
    issue_type = issue["issue_type"]

    steps = build_plan_steps(issue_type)
    follow_up_question = get_follow_up_question_for_issue(issue_type)
    recommended_tool = get_recommended_tool_for_issue(issue_type)
    recommended_action_tool = get_recommended_action_tool(issue_type)

    recommendation_map = {
        "duplicate": "Review and dispute the duplicate charge first.",
        "overlap": "Review overlapping plans and consider consolidating them.",
        "price_change": "Confirm whether the price increase is acceptable before keeping the subscription.",
        "high_spend": "Review high-value subscriptions and identify low-usage services.",
        "general_review": "Summarize current subscriptions and offer optimization help.",
    }

    return {
        "customer_id": customer_id,
        "issue_type": issue_type,
        "priority": issue["priority"],
        "title": issue["title"],
        "steps": steps,
        "follow_up_question": follow_up_question,
        "recommended_tool": recommended_tool,
        "recommended_action_tool": recommended_action_tool,
        "final_recommendation": recommendation_map[issue_type],
    }


def run_planner_agent(
    customer_result: Dict[str, Any],
    customer_id: int,
    use_llm: bool = False,
) -> Dict[str, Any]:
    plan = generate_planner_summary(customer_result, customer_id)

    inspection_question_map = {
        "duplicate": "Do I have duplicate subscriptions?",
        "overlap": "Do I have overlapping subscription plans?",
        "price_change": "What changed this month?",
        "high_spend": "What am I spending every month?",
        "general_review": "What subscriptions do I have?",
    }

    inspection_question = inspection_question_map.get(
        plan["issue_type"],
        "What subscriptions do I have?",
    )

    inspection_result = run_tool_agent(
        inspection_question,
        customer_result,
        customer_id,
        use_llm=use_llm,
    )

    action_result = None
    if plan["recommended_action_tool"] is not None:
        action_question_map = {
            "create_duplicate_dispute_action": "Create a dispute for the duplicate charge.",
            "create_downgrade_action": "Create a downgrade recommendation for me.",
        }

        action_question = action_question_map.get(
            plan["recommended_action_tool"],
            "",
        )

        if action_question:
            action_result = run_tool_agent(
                action_question,
                customer_result,
                customer_id,
                use_llm=use_llm,
            )

    return {
        "plan": plan,
        "inspection_result": inspection_result,
        "action_result": action_result,
    }
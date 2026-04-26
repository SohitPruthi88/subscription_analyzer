from typing import Any, Dict

from assistant import answer_user_question
from llm_client import choose_tool_with_llm, summarize_tool_result_with_llm
from tools import TOOL_REGISTRY, get_tool_descriptions


def _heuristic_tool_selection(user_question: str) -> dict:
    q = user_question.lower().strip()

    if "duplicate" in q or "charged twice" in q or "double charge" in q or "dispute" in q:
        if "create" in q or "flag" in q or "dispute" in q:
            return {
                "tool_name": "create_duplicate_dispute_action",
                "reason": "User asked for duplicate review or dispute action.",
            }
        return {
            "tool_name": "get_duplicate_subscriptions",
            "reason": "User asked about duplicate charges.",
        }

    if "price" in q or "increase" in q or "changed" in q:
        return {
            "tool_name": "get_price_changes",
            "reason": "User asked about price changes.",
        }

    if "overlap" in q or "similar" in q or "family" in q or "individual" in q:
        return {
            "tool_name": "get_overlapping_plans",
            "reason": "User asked about overlapping plans.",
        }

    if "spend" in q or "monthly" in q or "how much" in q:
        return {
            "tool_name": "get_monthly_spend",
            "reason": "User asked about monthly spend.",
        }

    if "cancel" in q and ("create" in q or "suggest" in q or "action" in q):
        return {
            "tool_name": "create_cancellation_action",
            "reason": "User explicitly asked to create a cancellation action.",
        }

    if "downgrade" in q and ("create" in q or "suggest" in q or "action" in q):
        return {
            "tool_name": "create_downgrade_action",
            "reason": "User explicitly asked to create a downgrade action.",
        }

    if "subscription" in q or "recurring" in q or "what do i have" in q:
        return {
            "tool_name": "get_recurring_subscriptions",
            "reason": "User asked about subscriptions.",
        }

    return {
        "tool_name": "get_recurring_subscriptions",
        "reason": "Default fallback tool.",
    }


def run_tool_agent(
    user_question: str,
    customer_result: Dict[str, Any],
    customer_id: int,
    use_llm: bool = False,
) -> Dict[str, Any]:
    if use_llm:
        try:
            tool_choice = choose_tool_with_llm(
                user_question,
                customer_result,
                customer_id,
                get_tool_descriptions(),
            )
            selection_mode = "llm"
        except Exception as exc:
            tool_choice = _heuristic_tool_selection(user_question)
            tool_choice["reason"] = f"LLM tool selection failed. {tool_choice['reason']} Error: {exc}"
            selection_mode = "heuristic_fallback"
    else:
        tool_choice = _heuristic_tool_selection(user_question)
        selection_mode = "heuristic"

    tool_name = tool_choice["tool_name"]

    if tool_name not in TOOL_REGISTRY:
        tool_name = "get_recurring_subscriptions"

    tool_fn = TOOL_REGISTRY[tool_name]
    tool_result = tool_fn(customer_result, customer_id)

    if use_llm:
        try:
            final_answer = summarize_tool_result_with_llm(
                user_question,
                tool_result,
                customer_id,
            )
            answer_mode = "llm"
        except Exception as exc:
            final_answer = (
                f"{tool_result['message']}\n\n"
                f"Fallback summary used after LLM failure.\nError: {exc}"
            )
            answer_mode = "fallback"
    else:
        if tool_result["result_type"] == "action":
            if tool_result.get("created_action"):
                final_answer = tool_result["message"]
            else:
                final_answer = tool_result["message"]
        else:
            final_answer = answer_user_question(user_question, customer_result, customer_id)
        answer_mode = "rule_based"

    return {
        "tool_choice": tool_choice,
        "selection_mode": selection_mode,
        "tool_result": tool_result,
        "answer_mode": answer_mode,
        "final_answer": final_answer,
    }
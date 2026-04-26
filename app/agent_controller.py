from typing import Any, Dict

from actions import (
    suggest_cancellation,
    suggest_downgrade,
    suggest_duplicate_dispute,
)
from ai_insights import generate_insights
from assistant import answer_user_question
from llm_client import answer_with_llm, generate_llm_recommendation
from orchestrator import generate_agent_decision


def generate_agent_summary(
    customer_result: Dict[str, Any],
    customer_id: int,
    use_llm: bool = False,
) -> str:
    if use_llm:
        try:
            return generate_llm_recommendation(customer_result, customer_id)
        except Exception as exc:
            fallback = generate_insights(customer_result, customer_id)
            return f"LLM unavailable, using fallback summary.\n\n{fallback}\n\nError: {exc}"

    return generate_insights(customer_result, customer_id)


def answer_agent_question(
    question: str,
    customer_result: Dict[str, Any],
    customer_id: int,
    use_llm: bool = False,
) -> str:
    if use_llm:
        try:
            return answer_with_llm(question, customer_result, customer_id)
        except Exception as exc:
            fallback = answer_user_question(question, customer_result, customer_id)
            return f"LLM unavailable, using fallback answer.\n\n{fallback}\n\nError: {exc}"

    return answer_user_question(question, customer_result, customer_id)


def decide_next_step(
    customer_result: Dict[str, Any],
    customer_id: int,
) -> Dict[str, Any]:
    return generate_agent_decision(customer_result, customer_id)


def build_suggested_action_from_decision(
    agent_decision: Dict[str, Any],
    customer_id: int,
) -> Dict[str, Any] | None:
    recommended_action = agent_decision.get("recommended_action")

    if recommended_action == "duplicate_dispute":
        merchant = agent_decision.get("merchant")
        year_month = agent_decision.get("year_month")
        if merchant and year_month:
            return suggest_duplicate_dispute(customer_id, merchant, year_month)

    if recommended_action == "downgrade_review":
        merchant = agent_decision.get("merchant")
        if merchant:
            return suggest_downgrade(customer_id, merchant)

    if recommended_action == "cancellation_request":
        merchant = agent_decision.get("merchant")
        if merchant:
            return suggest_cancellation(customer_id, merchant)

    return None


def get_follow_up_question(agent_decision: Dict[str, Any]) -> str | None:
    recommended_action = agent_decision.get("recommended_action")

    if recommended_action == "ask_usage_question":
        return "Are you still actively using this subscription every month?"

    if recommended_action == "ask_spend_review_question":
        return "Which of these subscriptions do you use at least once a week?"

    return None
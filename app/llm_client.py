import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def _get_client() -> OpenAI:
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

    if not api_key:
        raise ValueError(
            "AZURE_OPENAI_API_KEY is not set. Add it to your .env file."
        )

    if not endpoint:
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT is not set. Add it to your .env file."
        )

    base_url = endpoint.rstrip("/") + "/openai/v1/"

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
    )


def _get_deployment_name() -> str:
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not deployment:
        raise ValueError(
            "AZURE_OPENAI_DEPLOYMENT is not set. Add it to your .env file."
        )
    return deployment


def build_customer_context(customer_result: Dict[str, Any], customer_id: int) -> str:
    recurring = customer_result["recurring"]
    duplicates = customer_result["duplicates"]
    price_changes = customer_result["price_changes"]
    overlaps = customer_result["overlaps"]
    monthly_spend = customer_result["monthly_spend"]

    context = {
        "customer_id": customer_id,
        "monthly_spend": (
            monthly_spend.to_dict(orient="records") if not monthly_spend.empty else []
        ),
        "recurring_subscriptions": (
            recurring.to_dict(orient="records") if not recurring.empty else []
        ),
        "duplicate_patterns": (
            duplicates.to_dict(orient="records") if not duplicates.empty else []
        ),
        "price_changes": (
            price_changes.to_dict(orient="records") if not price_changes.empty else []
        ),
        "overlapping_plans": (
            overlaps.to_dict(orient="records") if not overlaps.empty else []
        ),
    }

    return json.dumps(context, default=str, indent=2)


def generate_llm_recommendation(customer_result: Dict[str, Any], customer_id: int) -> str:
    client = _get_client()
    deployment_name = _get_deployment_name()
    context = build_customer_context(customer_result, customer_id)

    prompt = f"""
You are a careful banking subscription assistant.

Your job:
- explain findings clearly
- avoid making up facts
- only use the provided structured data
- prioritize duplicate charges, overlapping plans, and price increases
- keep the answer concise but useful
- end with a recommended next action

Customer structured analysis:
{context}
"""

    response = client.responses.create(
        model=deployment_name,
        input=prompt,
    )

    return response.output_text.strip()


def answer_with_llm(
    user_question: str,
    customer_result: Dict[str, Any],
    customer_id: int,
) -> str:
    client = _get_client()
    deployment_name = _get_deployment_name()
    context = build_customer_context(customer_result, customer_id)

    prompt = f"""
You are a banking subscription assistant answering questions about one customer.

Rules:
- answer only from the structured analysis provided
- do not invent transactions or subscriptions
- if the answer is not supported by the data, say so
- keep answers clear and practical

Customer structured analysis:
{context}

User question:
{user_question}
"""

    response = client.responses.create(
        model=deployment_name,
        input=prompt,
    )

    return response.output_text.strip()
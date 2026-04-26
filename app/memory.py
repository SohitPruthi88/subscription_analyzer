import pandas as pd
import streamlit as st


def initialize_memory_store() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "agent_trace" not in st.session_state:
        st.session_state.agent_trace = []


def add_chat_message(customer_id: int, role: str, content: str) -> None:
    st.session_state.chat_history.append(
        {
            "customer_id": customer_id,
            "role": role,
            "content": content,
        }
    )


def get_chat_history(customer_id: int) -> list:
    return [
        msg
        for msg in st.session_state.chat_history
        if msg["customer_id"] == customer_id
    ]


def clear_chat_history(customer_id: int) -> None:
    st.session_state.chat_history = [
        msg
        for msg in st.session_state.chat_history
        if msg["customer_id"] != customer_id
    ]


def add_agent_trace(
    customer_id: int,
    event_type: str,
    message: str,
    metadata: dict | None = None,
) -> None:
    st.session_state.agent_trace.append(
        {
            "customer_id": customer_id,
            "event_type": event_type,
            "message": message,
            "metadata": metadata or {},
        }
    )


def get_agent_trace(customer_id: int) -> pd.DataFrame:
    rows = [
        row
        for row in st.session_state.agent_trace
        if row["customer_id"] == customer_id
    ]

    if not rows:
        return pd.DataFrame(columns=["customer_id", "event_type", "message", "metadata"])

    return pd.DataFrame(rows)


def clear_agent_trace(customer_id: int) -> None:
    st.session_state.agent_trace = [
        row
        for row in st.session_state.agent_trace
        if row["customer_id"] != customer_id
    ]
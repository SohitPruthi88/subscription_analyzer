import streamlit as st
import pandas as pd


def initialize_action_store():
    if "action_log" not in st.session_state:
        st.session_state.action_log = []


def add_action(action: dict):
    st.session_state.action_log.append(action)


def get_action_log() -> pd.DataFrame:
    if not st.session_state.action_log:
        return pd.DataFrame(
            columns=[
                "action_id",
                "timestamp",
                "customer_id",
                "merchant",
                "action_type",
                "status",
                "message",
                "year_month",
            ]
        )
    return pd.DataFrame(st.session_state.action_log)


def get_actions_for_customer(customer_id: int) -> list:
    return [
        action
        for action in st.session_state.action_log
        if action["customer_id"] == customer_id
    ]


def update_action(action_id: str, updated_action: dict):
    for i, action in enumerate(st.session_state.action_log):
        if action["action_id"] == action_id:
            st.session_state.action_log[i] = updated_action
            break
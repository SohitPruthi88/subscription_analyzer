from app.data_loader import load_transactions
from app.analyzer import (
    detect_recurring_subscriptions,
    detect_same_month_duplicates,
    detect_price_changes,
)


def test_recurring_detection():
    df = load_transactions("data/transactions.csv")
    recurring = detect_recurring_subscriptions(df)
    assert not recurring.empty


def test_duplicate_detection():
    df = load_transactions("data/transactions.csv")
    duplicates = detect_same_month_duplicates(df)
    assert not duplicates.empty


def test_price_change_detection():
    df = load_transactions("data/transactions.csv")
    price_changes = detect_price_changes(df)
    assert not price_changes.empty
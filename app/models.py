from dataclasses import dataclass


@dataclass
class SubscriptionSummary:
    customer_id: int
    merchant: str
    normalized_merchant: str
    amount: float
    occurrence_count: int
    first_seen: str
    last_seen: str
    frequency: str
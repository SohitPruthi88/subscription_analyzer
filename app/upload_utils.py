import pandas as pd


REQUIRED_FIELDS = [
    "date",
    "merchant",
    "amount",
]


def normalize_columns(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    renamed_df = df.rename(columns=mapping).copy()

    if "date" in renamed_df.columns:
        renamed_df["date"] = pd.to_datetime(renamed_df["date"], errors="coerce")

    if "amount" in renamed_df.columns:
        renamed_df["amount"] = pd.to_numeric(renamed_df["amount"], errors="coerce")

    renamed_df = renamed_df.dropna(subset=["date", "merchant", "amount"]).copy()

    if "type" not in renamed_df.columns:
        renamed_df["type"] = "debit"

    if "customer_id" not in renamed_df.columns:
        renamed_df["customer_id"] = 9999

    if "txn_id" not in renamed_df.columns:
        renamed_df["txn_id"] = range(1, len(renamed_df) + 1)

    if "category" not in renamed_df.columns:
        renamed_df["category"] = "unknown"

    if "description" not in renamed_df.columns:
        renamed_df["description"] = ""

    renamed_df["customer_id"] = renamed_df["customer_id"].astype(int)
    renamed_df["amount"] = renamed_df["amount"].astype(float)
    renamed_df["type"] = renamed_df["type"].astype(str).str.lower()

    renamed_df["abs_amount"] = renamed_df["amount"].abs()
    renamed_df["year_month"] = renamed_df["date"].dt.to_period("M").astype(str)

    return renamed_df


def validate_mapping(mapping: dict) -> bool:
    return all(field in mapping.values() for field in REQUIRED_FIELDS)
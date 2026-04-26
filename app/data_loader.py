import pandas as pd


def load_transactions(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    df["date"] = pd.to_datetime(df["date"])
    df["customer_id"] = df["customer_id"].astype(int)
    df["amount"] = df["amount"].astype(float)

    # Keep only debit transactions for subscription-style analysis
    df = df[df["type"].str.lower() == "debit"].copy()

    # Helpful derived fields
    df["abs_amount"] = df["amount"].abs()
    df["year_month"] = df["date"].dt.to_period("M").astype(str)

    return df
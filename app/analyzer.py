import pandas as pd


MERCHANT_NORMALIZATION = {
    "NETFLIX.COM": "Netflix",
    "SPOTIFY USA": "Spotify",
    "SPOTIFY FAMILY": "Spotify Family",
    "SPOTIFY INDIVIDUAL": "Spotify Individual",
    "ADOBE *CREATIVE": "Adobe Creative Cloud",
    "AMAZON PRIME ANNUAL": "Amazon Prime",
    "APPLE.COM/BILL": "Apple",
    "YOUTUBE PREMIUM": "YouTube Premium",
    "GYM PRO": "Gym Pro",
    "DUOLINGO": "Duolingo",
    "CANVA": "Canva",
    "HULU": "Hulu",
    "DISNEYPLUS": "Disney Plus",
    "MICROSOFT 365": "Microsoft 365",
}


def normalize_merchant(merchant: str) -> str:
    merchant = merchant.strip()
    return MERCHANT_NORMALIZATION.get(merchant, merchant.title())


def prepare_transactions(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    prepared["normalized_merchant"] = prepared["merchant"].apply(normalize_merchant)
    return prepared


def detect_recurring_subscriptions(df: pd.DataFrame) -> pd.DataFrame:
    prepared = prepare_transactions(df)

    recurring = (
        prepared.groupby(["customer_id", "normalized_merchant"])
        .agg(
            occurrence_count=("txn_id", "count"),
            months_active=("year_month", "nunique"),
            avg_amount=("abs_amount", "mean"),
            min_amount=("abs_amount", "min"),
            max_amount=("abs_amount", "max"),
            first_seen=("date", "min"),
            last_seen=("date", "max"),
            categories=("category", lambda x: ", ".join(sorted(set(x)))),
        )
        .reset_index()
    )

    recurring = recurring[recurring["months_active"] >= 2].copy()
    recurring["frequency"] = recurring["months_active"].apply(
        lambda x: "monthly" if x >= 2 else "unknown"
    )

    return recurring.sort_values(
        by=["customer_id", "occurrence_count"],
        ascending=[True, False]
    )


def detect_same_month_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    prepared = prepare_transactions(df)

    grouped = (
        prepared.groupby(["customer_id", "normalized_merchant", "year_month"])
        .agg(
            charge_count=("txn_id", "count"),
            avg_amount=("abs_amount", "mean"),
        )
        .reset_index()
    )

    duplicates = grouped[grouped["charge_count"] > 1].copy()
    return duplicates.sort_values(by=["customer_id", "year_month", "charge_count"], ascending=[True, True, False])


def detect_price_changes(df: pd.DataFrame) -> pd.DataFrame:
    prepared = prepare_transactions(df)

    grouped = (
        prepared.groupby(["customer_id", "normalized_merchant"])
        .agg(
            min_amount=("abs_amount", "min"),
            max_amount=("abs_amount", "max"),
            months_active=("year_month", "nunique"),
        )
        .reset_index()
    )

    price_changes = grouped[
        (grouped["months_active"] >= 2) & (grouped["min_amount"] != grouped["max_amount"])
    ].copy()

    return price_changes.sort_values(by=["customer_id", "normalized_merchant"])


def estimate_monthly_subscription_spend(df: pd.DataFrame) -> pd.DataFrame:
    recurring = detect_recurring_subscriptions(df).copy()

    recurring["estimated_monthly_amount"] = recurring["avg_amount"].round(2)

    monthly_summary = (
        recurring.groupby("customer_id")
        .agg(total_estimated_monthly_spend=("estimated_monthly_amount", "sum"))
        .reset_index()
    )

    monthly_summary["total_estimated_monthly_spend"] = monthly_summary[
        "total_estimated_monthly_spend"
    ].round(2)

    return monthly_summary


def detect_overlapping_subscription_types(df: pd.DataFrame) -> pd.DataFrame:
    prepared = prepare_transactions(df)

    spotify_rows = prepared[
        prepared["normalized_merchant"].isin(["Spotify Family", "Spotify Individual"])
    ].copy()

    overlap = (
        spotify_rows.groupby(["customer_id", "year_month"])["normalized_merchant"]
        .nunique()
        .reset_index(name="spotify_plan_count")
    )

    overlap = overlap[overlap["spotify_plan_count"] > 1].copy()
    return overlap


def analyze_customer(df: pd.DataFrame, customer_id: int) -> dict:
    customer_df = df[df["customer_id"] == customer_id].copy()

    recurring = detect_recurring_subscriptions(customer_df)
    duplicates = detect_same_month_duplicates(customer_df)
    price_changes = detect_price_changes(customer_df)
    overlaps = detect_overlapping_subscription_types(customer_df)
    monthly_spend = estimate_monthly_subscription_spend(customer_df)

    return {
        "recurring": recurring,
        "duplicates": duplicates,
        "price_changes": price_changes,
        "overlaps": overlaps,
        "monthly_spend": monthly_spend,
    }
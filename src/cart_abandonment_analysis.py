"""
Module 2 cart abandonment fact table builder.

Inputs:
    data_cleaned/user_events.csv
    data_cleaned/orders.csv
    data_cleaned/order_items.csv
    data_cleaned/products.csv

Outputs:
    outputs/module2/cart_attempt_fact.csv
    outputs/module2/cart_abandonment_summary_*.csv
    outputs/module2/module2_cart_report.txt

The output fact table is designed for Power BI. Each row is one cart attempt:
customer_id + session_id + product_id.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data_cleaned"
OUTPUT_DIR = BASE_DIR / "outputs" / "module2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONVERSION_WINDOW_DAYS = 7
VALID_PURCHASE_STATUSES = {"paid", "refunded", "chargeback"}


def normalize_text(value: object, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, float) and np.isnan(value):
        return fallback
    if pd.isna(value):
        return fallback
    text = str(value).strip().lower()
    if text in {"", "nan", "none", "null"}:
        return fallback
    return text


def normalize_series(series: pd.Series, fallback: str = "") -> pd.Series:
    return series.map(lambda value: normalize_text(value, fallback=fallback))


def first_nonempty(values: Iterable[object], fallback: str = "") -> str:
    for value in values:
        text = normalize_text(value, fallback="")
        if text:
            return text
    return fallback


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return np.where(denominator.ne(0), numerator / denominator, np.nan)


def load_data() -> dict[str, pd.DataFrame]:
    return {
        "user_events": pd.read_csv(
            DATA_DIR / "user_events.csv",
            parse_dates=["event_timestamp"],
            low_memory=False,
        ),
        "orders": pd.read_csv(
            DATA_DIR / "orders.csv",
            parse_dates=["order_date"],
            low_memory=False,
        ),
        "order_items": pd.read_csv(DATA_DIR / "order_items.csv", low_memory=False),
        "products": pd.read_csv(DATA_DIR / "products.csv", low_memory=False),
    }


def clean_user_events(user_events: pd.DataFrame) -> pd.DataFrame:
    df = user_events.copy()
    initial_rows = len(df)

    df = df.drop_duplicates()
    if "event_id" in df.columns:
        df = df.drop_duplicates(subset=["event_id"], keep="first")

    for col in ["customer_id", "session_id", "event_type", "product_id", "device_type", "traffic_source"]:
        if col in df.columns:
            df[col] = normalize_series(df[col], fallback="")

    df["traffic_source"] = df["traffic_source"].replace("", "direct")
    df["device_type"] = df["device_type"].replace("", "unknown")
    df["page_url"] = df["page_url"].fillna("").astype(str)

    df = df.dropna(subset=["event_timestamp"])
    df = df[df["customer_id"].ne("") & df["session_id"].ne("")]

    df.attrs["initial_rows"] = initial_rows
    df.attrs["deduped_rows"] = len(df)
    return df


def build_session_features(events: pd.DataFrame) -> pd.DataFrame:
    event_counts = (
        events.pivot_table(
            index=["customer_id", "session_id"],
            columns="event_type",
            values="event_id",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    expected_event_cols = [
        "page_view",
        "product_view",
        "add_to_cart",
        "checkout_start",
        "payment_info",
        "purchase",
    ]
    for col in expected_event_cols:
        if col not in event_counts.columns:
            event_counts[col] = 0

    event_counts = event_counts.rename(
        columns={
            "page_view": "page_view_count",
            "product_view": "product_view_count",
            "add_to_cart": "session_add_to_cart_count",
            "checkout_start": "checkout_start_count",
            "payment_info": "payment_info_count",
            "purchase": "purchase_event_count",
        }
    )

    base = (
        events.sort_values(["customer_id", "session_id", "event_timestamp"])
        .groupby(["customer_id", "session_id"], as_index=False)
        .agg(
            session_start_time=("event_timestamp", "min"),
            session_end_time=("event_timestamp", "max"),
            event_count=("event_id", "count"),
            device_type=("device_type", lambda x: first_nonempty(x, fallback="unknown")),
            traffic_source=("traffic_source", lambda x: first_nonempty(x, fallback="direct")),
            landing_page_url=("page_url", lambda x: next((str(v) for v in x if str(v).strip()), "")),
            distinct_products_viewed=("product_id", lambda x: x[(x != "") & (x != "unknown")].nunique()),
        )
    )

    timing = (
        events[events["event_type"].isin(["checkout_start", "payment_info", "purchase"])]
        .pivot_table(
            index=["customer_id", "session_id"],
            columns="event_type",
            values="event_timestamp",
            aggfunc="min",
        )
        .reset_index()
        .rename_axis(None, axis=1)
        .rename(
            columns={
                "checkout_start": "first_checkout_start_time",
                "payment_info": "first_payment_info_time",
                "purchase": "first_purchase_event_time",
            }
        )
    )

    session = base.merge(event_counts, on=["customer_id", "session_id"], how="left")
    session = session.merge(timing, on=["customer_id", "session_id"], how="left")

    count_cols = [
        "page_view_count",
        "product_view_count",
        "session_add_to_cart_count",
        "checkout_start_count",
        "payment_info_count",
        "purchase_event_count",
    ]
    session[count_cols] = session[count_cols].fillna(0).astype(int)

    session["session_duration_min"] = (
        (session["session_end_time"] - session["session_start_time"]).dt.total_seconds() / 60.0
    ).clip(lower=0)
    session["reached_checkout_start"] = session["checkout_start_count"].gt(0).astype(int)
    session["reached_payment_info"] = session["payment_info_count"].gt(0).astype(int)
    session["has_purchase_event"] = session["purchase_event_count"].gt(0).astype(int)
    return session


def build_cart_attempts(events: pd.DataFrame, session_features: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    add_to_cart = events[events["event_type"].eq("add_to_cart")].copy()
    total_add_to_cart_events = len(add_to_cart)

    valid_product_mask = add_to_cart["product_id"].ne("") & add_to_cart["product_id"].ne("unknown")
    invalid_product_events = int((~valid_product_mask).sum())
    add_to_cart = add_to_cart[valid_product_mask].copy()

    cart = (
        add_to_cart.sort_values(["customer_id", "session_id", "product_id", "event_timestamp"])
        .groupby(["customer_id", "session_id", "product_id"], as_index=False)
        .agg(
            add_to_cart_time=("event_timestamp", "min"),
            last_add_to_cart_time=("event_timestamp", "max"),
            add_to_cart_event_count=("event_id", "count"),
        )
    )
    cart["cart_key"] = (
        cart["customer_id"].astype(str)
        + "|"
        + cart["session_id"].astype(str)
        + "|"
        + cart["product_id"].astype(str)
    )

    cart = cart.merge(session_features, on=["customer_id", "session_id"], how="left")
    cart["minutes_from_session_start_to_cart"] = (
        (cart["add_to_cart_time"] - cart["session_start_time"]).dt.total_seconds() / 60.0
    ).clip(lower=0)
    cart["minutes_after_cart_in_session"] = (
        (cart["session_end_time"] - cart["add_to_cart_time"]).dt.total_seconds() / 60.0
    ).clip(lower=0)

    cart["reached_checkout_after_cart"] = (
        cart["first_checkout_start_time"].notna()
        & cart["first_checkout_start_time"].ge(cart["add_to_cart_time"])
    ).astype(int)
    cart["reached_payment_after_cart"] = (
        cart["first_payment_info_time"].notna()
        & cart["first_payment_info_time"].ge(cart["add_to_cart_time"])
    ).astype(int)
    cart["purchase_event_after_cart"] = (
        cart["first_purchase_event_time"].notna()
        & cart["first_purchase_event_time"].ge(cart["add_to_cart_time"])
    ).astype(int)

    diagnostics = {
        "total_add_to_cart_events": total_add_to_cart_events,
        "invalid_product_add_to_cart_events": invalid_product_events,
        "cart_attempt_rows": len(cart),
    }
    return cart, diagnostics


def build_purchase_items(orders: pd.DataFrame, order_items: pd.DataFrame) -> pd.DataFrame:
    orders_df = orders.copy()
    items_df = order_items.copy()

    for col in ["customer_id", "order_id", "payment_status", "coupon_code", "utm_source", "utm_medium", "utm_campaign"]:
        if col in orders_df.columns:
            orders_df[col] = normalize_series(orders_df[col], fallback="")
    for col in ["order_id", "product_id", "category", "sku"]:
        if col in items_df.columns:
            items_df[col] = normalize_series(items_df[col], fallback="")

    purchases = items_df.merge(
        orders_df[
            [
                "order_id",
                "customer_id",
                "order_date",
                "payment_status",
                "shipping_country",
                "total_amount",
                "discount_amount",
                "coupon_code",
                "utm_source",
                "utm_medium",
                "utm_campaign",
            ]
        ],
        on="order_id",
        how="left",
    )
    purchases = purchases.dropna(subset=["order_date"])
    purchases = purchases[purchases["customer_id"].ne("") & purchases["product_id"].ne("")]
    purchases = purchases[purchases["payment_status"].isin(VALID_PURCHASE_STATUSES)]

    purchases["line_revenue"] = purchases["quantity"].astype(float) * purchases["unit_price"].astype(float)
    purchases["coupon_used_on_order"] = purchases["coupon_code"].ne("").astype(int)
    return purchases


def match_cart_attempts_to_orders(cart: pd.DataFrame, purchases: pd.DataFrame) -> pd.DataFrame:
    cart_for_match = cart[["cart_key", "customer_id", "product_id", "add_to_cart_time"]].copy()

    candidate_matches = cart_for_match.merge(
        purchases,
        on=["customer_id", "product_id"],
        how="left",
        suffixes=("", "_purchase"),
    )
    candidate_matches = candidate_matches[
        candidate_matches["order_date"].notna()
        & candidate_matches["order_date"].ge(candidate_matches["add_to_cart_time"])
        & candidate_matches["order_date"].le(
            candidate_matches["add_to_cart_time"] + pd.Timedelta(days=CONVERSION_WINDOW_DAYS)
        )
    ].copy()

    if candidate_matches.empty:
        matched = pd.DataFrame(columns=["cart_key"])
    else:
        candidate_matches["minutes_to_purchase"] = (
            (candidate_matches["order_date"] - candidate_matches["add_to_cart_time"]).dt.total_seconds() / 60.0
        )
        matched = (
            candidate_matches.sort_values(["cart_key", "order_date", "order_id"])
            .groupby("cart_key", as_index=False)
            .first()
        )

    keep_cols = [
        "cart_key",
        "order_id",
        "order_date",
        "payment_status",
        "quantity",
        "unit_price",
        "line_revenue",
        "total_amount",
        "discount_amount",
        "coupon_code",
        "coupon_used_on_order",
        "shipping_country",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "minutes_to_purchase",
    ]
    for col in keep_cols:
        if col not in matched.columns:
            matched[col] = np.nan

    return matched[keep_cols].rename(
        columns={
            "order_date": "purchase_time",
            "quantity": "matched_order_quantity",
            "unit_price": "matched_order_unit_price",
            "line_revenue": "matched_order_line_revenue",
            "total_amount": "matched_order_total_amount",
            "discount_amount": "matched_order_discount_amount",
            "coupon_code": "matched_order_coupon_code",
            "shipping_country": "matched_order_shipping_country",
            "utm_source": "matched_order_utm_source",
            "utm_medium": "matched_order_utm_medium",
            "utm_campaign": "matched_order_utm_campaign",
        }
    )


def add_product_attributes(cart: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    products_df = products.copy()
    for col in ["product_id", "sku", "product_name", "category"]:
        if col in products_df.columns:
            products_df[col] = normalize_series(products_df[col], fallback="")

    products_df = products_df.rename(
        columns={
            "sku": "product_sku",
            "unit_price": "product_unit_price",
            "cost_price": "product_cost_price",
        }
    )
    keep_cols = [
        "product_id",
        "product_sku",
        "product_name",
        "category",
        "product_unit_price",
        "product_cost_price",
        "weight_kg",
        "is_active",
        "launch_date",
    ]
    keep_cols = [col for col in keep_cols if col in products_df.columns]
    out = cart.merge(products_df[keep_cols], on="product_id", how="left")

    price = pd.to_numeric(out["product_unit_price"], errors="coerce")
    out["price_band"] = pd.cut(
        price,
        bins=[-np.inf, 25, 50, 100, 150, np.inf],
        labels=["0-25", "25-50", "50-100", "100-150", "150+"],
    ).astype("string")
    out["price_band"] = out["price_band"].fillna("unknown")
    return out


def add_outcome_fields(cart: pd.DataFrame) -> pd.DataFrame:
    out = cart.copy()
    out["converted"] = out["order_id"].notna().astype(int)
    out["abandoned"] = out["converted"].eq(0).astype(int)
    out["paid_conversion"] = out["payment_status"].eq("paid").astype(int)
    out["outcome"] = np.where(out["converted"].eq(1), "completed", "abandoned")

    out["minutes_to_abandon_proxy"] = np.where(
        out["abandoned"].eq(1),
        out["minutes_after_cart_in_session"],
        np.nan,
    )
    out["minutes_to_outcome"] = np.where(
        out["converted"].eq(1),
        out["minutes_to_purchase"],
        out["minutes_to_abandon_proxy"],
    )

    out["abandon_time_bucket"] = pd.cut(
        out["minutes_to_abandon_proxy"],
        bins=[-np.inf, 5, 15, 30, 60, np.inf],
        labels=["0-5 min", "5-15 min", "15-30 min", "30-60 min", "60+ min"],
    ).astype("string")
    out["abandon_time_bucket"] = out["abandon_time_bucket"].fillna("")

    out["conversion_window_days"] = CONVERSION_WINDOW_DAYS
    out["cart_date"] = out["add_to_cart_time"].dt.date
    out["cart_week_start"] = out["add_to_cart_time"].dt.to_period("W").dt.start_time.dt.date
    out["cart_month"] = out["add_to_cart_time"].dt.to_period("M").astype(str)
    return out


def build_summary(fact: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    summary = (
        fact.groupby(group_cols, dropna=False)
        .agg(
            cart_attempts=("cart_key", "nunique"),
            converted_attempts=("converted", "sum"),
            abandoned_attempts=("abandoned", "sum"),
            paid_conversions=("paid_conversion", "sum"),
            avg_session_duration_min=("session_duration_min", "mean"),
            avg_page_view_count=("page_view_count", "mean"),
            avg_product_view_count=("product_view_count", "mean"),
            checkout_after_cart_rate=("reached_checkout_after_cart", "mean"),
            payment_after_cart_rate=("reached_payment_after_cart", "mean"),
            avg_minutes_to_abandon_proxy=("minutes_to_abandon_proxy", "mean"),
            avg_minutes_to_purchase=("minutes_to_purchase", "mean"),
        )
        .reset_index()
    )
    summary["cart_abandonment_rate"] = safe_divide(summary["abandoned_attempts"], summary["cart_attempts"])
    summary["cart_conversion_rate"] = safe_divide(summary["converted_attempts"], summary["cart_attempts"])
    summary["paid_conversion_rate"] = safe_divide(summary["paid_conversions"], summary["cart_attempts"])
    return summary


def write_outputs(fact: pd.DataFrame, diagnostics: dict[str, int]) -> None:
    fact_path = OUTPUT_DIR / "cart_attempt_fact.csv"
    fact.to_csv(fact_path, index=False, encoding="utf-8-sig")

    build_summary(fact, ["category"]).to_csv(
        OUTPUT_DIR / "cart_abandonment_summary_by_category.csv",
        index=False,
        encoding="utf-8-sig",
    )
    build_summary(fact, ["price_band"]).to_csv(
        OUTPUT_DIR / "cart_abandonment_summary_by_price_band.csv",
        index=False,
        encoding="utf-8-sig",
    )
    build_summary(fact, ["device_type"]).to_csv(
        OUTPUT_DIR / "cart_abandonment_summary_by_device.csv",
        index=False,
        encoding="utf-8-sig",
    )
    build_summary(fact, ["traffic_source"]).to_csv(
        OUTPUT_DIR / "cart_abandonment_summary_by_traffic_source.csv",
        index=False,
        encoding="utf-8-sig",
    )
    build_summary(fact, ["outcome"]).to_csv(
        OUTPUT_DIR / "cart_behavior_summary_by_outcome.csv",
        index=False,
        encoding="utf-8-sig",
    )

    total_attempts = fact["cart_key"].nunique()
    converted_attempts = int(fact["converted"].sum())
    abandoned_attempts = int(fact["abandoned"].sum())
    abandonment_rate = abandoned_attempts / total_attempts if total_attempts else np.nan

    report = [
        "Module 2 cart abandonment fact table completed.",
        f"Conversion window days: {CONVERSION_WINDOW_DAYS}",
        f"Total add_to_cart events: {diagnostics['total_add_to_cart_events']:,}",
        f"Invalid product add_to_cart events excluded: {diagnostics['invalid_product_add_to_cart_events']:,}",
        f"Cart attempt rows: {total_attempts:,}",
        f"Converted attempts: {converted_attempts:,}",
        f"Abandoned attempts: {abandoned_attempts:,}",
        f"Cart abandonment rate: {abandonment_rate:.4f}",
        "",
        f"Main output: {fact_path}",
    ]
    (OUTPUT_DIR / "module2_cart_report.txt").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    tables = load_data()
    events = clean_user_events(tables["user_events"])
    session_features = build_session_features(events)
    cart, diagnostics = build_cart_attempts(events, session_features)
    purchases = build_purchase_items(tables["orders"], tables["order_items"])
    matched_orders = match_cart_attempts_to_orders(cart, purchases)

    fact = cart.merge(matched_orders, on="cart_key", how="left")
    fact = add_product_attributes(fact, tables["products"])
    fact = add_outcome_fields(fact)

    preferred_columns = [
        "cart_key",
        "customer_id",
        "session_id",
        "product_id",
        "add_to_cart_time",
        "last_add_to_cart_time",
        "cart_date",
        "cart_week_start",
        "cart_month",
        "converted",
        "abandoned",
        "paid_conversion",
        "outcome",
        "conversion_window_days",
        "purchase_time",
        "minutes_to_purchase",
        "minutes_to_abandon_proxy",
        "minutes_to_outcome",
        "abandon_time_bucket",
        "category",
        "product_sku",
        "product_name",
        "product_unit_price",
        "product_cost_price",
        "price_band",
        "device_type",
        "traffic_source",
        "landing_page_url",
        "session_start_time",
        "session_end_time",
        "session_duration_min",
        "minutes_from_session_start_to_cart",
        "minutes_after_cart_in_session",
        "event_count",
        "page_view_count",
        "product_view_count",
        "distinct_products_viewed",
        "add_to_cart_event_count",
        "session_add_to_cart_count",
        "checkout_start_count",
        "payment_info_count",
        "purchase_event_count",
        "reached_checkout_start",
        "reached_payment_info",
        "has_purchase_event",
        "reached_checkout_after_cart",
        "reached_payment_after_cart",
        "purchase_event_after_cart",
        "order_id",
        "payment_status",
        "matched_order_quantity",
        "matched_order_unit_price",
        "matched_order_line_revenue",
        "matched_order_total_amount",
        "matched_order_discount_amount",
        "matched_order_coupon_code",
        "coupon_used_on_order",
        "matched_order_shipping_country",
        "matched_order_utm_source",
        "matched_order_utm_medium",
        "matched_order_utm_campaign",
    ]
    preferred_columns = [col for col in preferred_columns if col in fact.columns]
    remaining_columns = [col for col in fact.columns if col not in preferred_columns]
    fact = fact[preferred_columns + remaining_columns].sort_values(["add_to_cart_time", "cart_key"])

    write_outputs(fact, diagnostics)

    print("Module 2 cart abandonment fact table completed.")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Cart attempt rows: {fact['cart_key'].nunique():,}")
    print(f"Abandonment rate: {fact['abandoned'].sum() / fact['cart_key'].nunique():.2%}")


if __name__ == "__main__":
    main()

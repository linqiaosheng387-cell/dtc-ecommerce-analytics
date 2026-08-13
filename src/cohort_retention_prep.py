"""
Module 3 cohort retention prep.

Inputs:
    data_cleaned/orders.csv

Outputs:
    outputs/module3/cohort_paid_orders_month_level.csv
    outputs/module3/cohort_paid_customer_month_level.csv
    outputs/module3/cohort_prep_report.md

This script prepares the base tables needed for purchase cohort retention analysis.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data_cleaned"
OUTPUT_DIR = BASE_DIR / "outputs" / "module3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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


def period_ordinal(series: pd.Series) -> pd.Series:
    return series.map(lambda p: p.ordinal if pd.notna(p) else pd.NA).astype("Int64")


def load_orders() -> pd.DataFrame:
    orders = pd.read_csv(
        DATA_DIR / "orders.csv",
        parse_dates=["order_date"],
        low_memory=False,
    )
    for col in [
        "order_id",
        "customer_id",
        "payment_status",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "shipping_country",
        "coupon_code",
    ]:
        if col in orders.columns:
            orders[col] = orders[col].map(lambda x: normalize_text(x, fallback=""))

    for col in ["subtotal", "shipping_fee", "discount_amount", "total_amount"]:
        if col in orders.columns:
            orders[col] = pd.to_numeric(orders[col], errors="coerce").fillna(0.0)

    orders = orders.dropna(subset=["customer_id", "order_date"])
    orders["payment_status"] = orders["payment_status"].replace("", "unknown")
    return orders


def build_paid_order_month_table(orders: pd.DataFrame) -> pd.DataFrame:
    paid = orders[orders["payment_status"].eq("paid")].copy()
    paid = paid.sort_values(["customer_id", "order_date", "order_id"])

    paid["order_month_period"] = paid["order_date"].dt.to_period("M")
    paid["order_month"] = paid["order_month_period"].astype(str)

    first_month_map = paid.groupby("customer_id")["order_month_period"].min()
    paid["first_paid_order_month_period"] = paid["customer_id"].map(first_month_map)
    paid["first_paid_order_month"] = paid["first_paid_order_month_period"].astype(str)

    paid["order_month_ordinal"] = period_ordinal(paid["order_month_period"])
    paid["first_paid_order_month_ordinal"] = period_ordinal(paid["first_paid_order_month_period"])
    paid["month_index"] = paid["order_month_ordinal"] - paid["first_paid_order_month_ordinal"]

    columns = [
        "customer_id",
        "order_id",
        "order_date",
        "payment_status",
        "total_amount",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "first_paid_order_month",
        "order_month",
        "month_index",
    ]
    return paid[columns].copy()


def build_paid_customer_month_table(order_month_table: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        order_month_table.sort_values(["customer_id", "order_month", "order_date", "order_id"])
        .groupby(["customer_id", "order_month"], as_index=False)
        .agg(
            first_paid_order_month=("first_paid_order_month", "first"),
            payment_status=("payment_status", "first"),
            first_order_in_month=("order_date", "min"),
            last_order_in_month=("order_date", "max"),
            orders_in_month=("order_id", "nunique"),
            month_revenue=("total_amount", "sum"),
            first_utm_source=("utm_source", "first"),
            first_utm_medium=("utm_medium", "first"),
            first_utm_campaign=("utm_campaign", "first"),
        )
    )
    monthly["order_month_period"] = pd.PeriodIndex(monthly["order_month"], freq="M")
    monthly["first_paid_order_month_period"] = pd.PeriodIndex(monthly["first_paid_order_month"], freq="M")
    monthly["month_index"] = (
        period_ordinal(monthly["order_month_period"]) - period_ordinal(monthly["first_paid_order_month_period"])
    )

    monthly = monthly[
        [
            "customer_id",
            "first_paid_order_month",
            "order_month",
            "month_index",
            "payment_status",
            "first_order_in_month",
            "last_order_in_month",
            "orders_in_month",
            "month_revenue",
            "first_utm_source",
            "first_utm_medium",
            "first_utm_campaign",
        ]
    ].copy()
    return monthly


def write_report(order_month_table: pd.DataFrame, customer_month_table: pd.DataFrame) -> None:
    paid_customers = order_month_table["customer_id"].nunique()
    paid_orders = len(order_month_table)
    paid_month_rows = len(customer_month_table)
    repeat_customers = customer_month_table.groupby("customer_id")["order_month"].nunique().gt(1).sum()
    repeat_order_rows = order_month_table.groupby("customer_id")["order_month"].nunique().gt(1).sum()

    report = [
        "# Cohort 留存基础表准备完成",
        "",
        f"- paid 用户数: {paid_customers:,}",
        f"- paid 订单行数: {paid_orders:,}",
        f"- customer-month 行数: {paid_month_rows:,}",
        f"- 至少跨 2 个月购买的用户数: {repeat_customers:,}",
        f"- 至少跨 2 个月有订单月份的用户数: {repeat_order_rows:,}",
        "",
        "说明：留存分析后续应该优先使用 customer-month 表，避免同一用户同月多单重复计数。",
    ]
    (OUTPUT_DIR / "cohort_prep_report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    orders = load_orders()
    order_month_table = build_paid_order_month_table(orders)
    customer_month_table = build_paid_customer_month_table(order_month_table)

    order_month_table.to_csv(
        OUTPUT_DIR / "cohort_paid_orders_month_level.csv",
        index=False,
        encoding="utf-8-sig",
    )
    customer_month_table.to_csv(
        OUTPUT_DIR / "cohort_paid_customer_month_level.csv",
        index=False,
        encoding="utf-8-sig",
    )
    write_report(order_month_table, customer_month_table)

    print("Cohort retention prep completed.")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Paid order rows: {len(order_month_table):,}")
    print(f"Customer-month rows: {len(customer_month_table):,}")


if __name__ == "__main__":
    main()

"""
Module 3 RFM segmentation for the cross-border DTC project.

Inputs:
    data_cleaned/customers.csv
    data_cleaned/orders.csv
    data_cleaned/order_items.csv

Outputs:
    outputs/module3/rfm_user_segments.csv
    outputs/module3/rfm_segment_summary.csv
    outputs/module3/rfm_segment_by_category.csv
    outputs/module3/rfm_segment_by_channel.csv
    outputs/module3/rfm_category_recency_rules.csv
    outputs/module3/rfm_monetary_thresholds_by_category.csv
    outputs/module3/module3_rfm_report.md

This script uses business rules instead of equal-width cuts:
    - Recency is scored with category-specific repurchase-cycle thresholds.
    - Frequency is scored with lifecycle steps because repeat purchase is a long-tail behavior.
    - Monetary is scored within the user's primary category to reduce category price bias.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data_cleaned"
OUTPUT_DIR = BASE_DIR / "outputs" / "module3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PAID_STATUS = "paid"

# Recency thresholds are category-specific because natural replenishment cycles differ.
# Tuple meaning: score 5 <= first threshold, score 4 <= second, score 3 <= third,
# score 2 <= fourth, otherwise score 1.
CATEGORY_RECENCY_RULES: Dict[str, Tuple[int, int, int, int]] = {
    "beauty": (45, 90, 150, 240),
    "fashion": (60, 120, 210, 300),
    "sports": (90, 180, 300, 450),
    "home": (120, 240, 365, 540),
    "electronics": (180, 365, 540, 720),
    "unknown": (90, 180, 300, 450),
}

CATEGORY_CYCLE_LABELS = {
    "beauty": "short_consumption_cycle",
    "fashion": "seasonal_cycle",
    "sports": "medium_replacement_cycle",
    "home": "long_replacement_cycle",
    "electronics": "very_long_replacement_cycle",
    "unknown": "default_medium_cycle",
}

SEGMENT_ORDER = [
    "重要价值用户",
    "重要挽留用户",
    "重要发展用户",
    "重要唤回用户",
    "一般价值用户",
    "一般挽留用户",
    "一般发展用户",
    "低价值流失用户",
]


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


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return np.where(denominator.ne(0), numerator / denominator, np.nan)


def load_data() -> dict[str, pd.DataFrame]:
    return {
        "customers": pd.read_csv(DATA_DIR / "customers.csv", low_memory=False),
        "orders": pd.read_csv(DATA_DIR / "orders.csv", parse_dates=["order_date"], low_memory=False),
        "order_items": pd.read_csv(DATA_DIR / "order_items.csv", low_memory=False),
    }


def clean_customers(customers: pd.DataFrame) -> pd.DataFrame:
    df = customers.copy()
    for col in ["customer_id", "first_touch_channel", "first_touch_campaign_id", "country", "device_type", "customer_segment"]:
        if col in df.columns:
            df[col] = normalize_series(df[col], fallback="")
    return df


def clean_orders(orders: pd.DataFrame) -> pd.DataFrame:
    df = orders.copy()
    for col in ["order_id", "customer_id", "payment_status", "shipping_country", "coupon_code", "utm_source", "utm_medium", "utm_campaign"]:
        if col in df.columns:
            df[col] = normalize_series(df[col], fallback="")
    for col in ["subtotal", "shipping_fee", "discount_amount", "total_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df = df.dropna(subset=["order_date"])
    return df


def clean_order_items(order_items: pd.DataFrame) -> pd.DataFrame:
    df = order_items.copy()
    for col in ["order_id", "product_id", "sku", "category"]:
        if col in df.columns:
            df[col] = normalize_series(df[col], fallback="")
    for col in ["quantity", "unit_price", "cost_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["line_revenue"] = df["quantity"] * df["unit_price"]
    df["line_profit"] = df["quantity"] * (df["unit_price"] - df["cost_price"])
    df["category"] = df["category"].replace("", "unknown")
    return df


def build_paid_purchase_frames(orders: pd.DataFrame, order_items: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    paid_orders = orders[orders["payment_status"].eq(PAID_STATUS)].copy()

    paid_items = order_items.merge(
        paid_orders[
            [
                "order_id",
                "customer_id",
                "order_date",
                "shipping_country",
                "total_amount",
                "discount_amount",
                "coupon_code",
                "utm_source",
            ]
        ],
        on="order_id",
        how="inner",
    )
    return paid_orders, paid_items


def build_primary_category(paid_items: pd.DataFrame) -> pd.DataFrame:
    category_spend = (
        paid_items.groupby(["customer_id", "category"], as_index=False)
        .agg(
            category_revenue=("line_revenue", "sum"),
            category_profit=("line_profit", "sum"),
            category_quantity=("quantity", "sum"),
            category_orders=("order_id", "nunique"),
        )
    )

    primary_category = (
        category_spend.sort_values(
            ["customer_id", "category_revenue", "category_quantity", "category_orders", "category"],
            ascending=[True, False, False, False, True],
        )
        .groupby("customer_id", as_index=False)
        .first()
        .rename(
            columns={
                "category": "primary_category",
                "category_revenue": "primary_category_revenue",
                "category_profit": "primary_category_profit",
                "category_quantity": "primary_category_quantity",
                "category_orders": "primary_category_orders",
            }
        )
    )
    return primary_category


def build_user_rfm_base(
    paid_orders: pd.DataFrame,
    paid_items: pd.DataFrame,
    customers: pd.DataFrame,
    analysis_date: pd.Timestamp,
) -> pd.DataFrame:
    order_metrics = (
        paid_orders.groupby("customer_id", as_index=False)
        .agg(
            first_order_date=("order_date", "min"),
            last_order_date=("order_date", "max"),
            frequency=("order_id", "nunique"),
            monetary=("total_amount", "sum"),
            avg_order_value=("total_amount", "mean"),
            total_discount_amount=("discount_amount", "sum"),
            coupon_order_count=("coupon_code", lambda x: x.ne("").sum()),
            distinct_shipping_countries=("shipping_country", "nunique"),
            first_order_channel=("utm_source", lambda x: next((v for v in x if v), "")),
            last_order_channel=("utm_source", lambda x: next((v for v in reversed(list(x)) if v), "")),
        )
    )

    item_metrics = (
        paid_items.groupby("customer_id", as_index=False)
        .agg(
            total_items=("quantity", "sum"),
            gross_item_revenue=("line_revenue", "sum"),
            gross_item_profit=("line_profit", "sum"),
            distinct_categories=("category", "nunique"),
            distinct_products=("product_id", "nunique"),
        )
    )

    category = build_primary_category(paid_items)

    rfm = order_metrics.merge(item_metrics, on="customer_id", how="left")
    rfm = rfm.merge(category, on="customer_id", how="left")
    rfm = rfm.merge(
        customers[
            [
                "customer_id",
                "first_touch_channel",
                "first_touch_campaign_id",
                "country",
                "device_type",
                "is_subscribed",
            ]
        ],
        on="customer_id",
        how="left",
    )

    rfm["primary_category"] = rfm["primary_category"].fillna("unknown")
    rfm["category_cycle_label"] = rfm["primary_category"].map(CATEGORY_CYCLE_LABELS).fillna("default_medium_cycle")
    rfm["recency_days"] = (analysis_date - rfm["last_order_date"]).dt.days.clip(lower=0)
    rfm["customer_age_days"] = (analysis_date - rfm["first_order_date"]).dt.days.clip(lower=0)
    rfm["purchase_span_days"] = (rfm["last_order_date"] - rfm["first_order_date"]).dt.days.clip(lower=0)
    rfm["repeat_purchase_flag"] = rfm["frequency"].ge(2).astype(int)
    rfm["discount_usage_rate"] = safe_divide(rfm["coupon_order_count"], rfm["frequency"])
    rfm["profit_margin"] = safe_divide(rfm["gross_item_profit"], rfm["gross_item_revenue"])
    return rfm


def score_recency(row: pd.Series) -> int:
    category = normalize_text(row["primary_category"], fallback="unknown")
    thresholds = CATEGORY_RECENCY_RULES.get(category, CATEGORY_RECENCY_RULES["unknown"])
    recency = row["recency_days"]

    if recency <= thresholds[0]:
        return 5
    if recency <= thresholds[1]:
        return 4
    if recency <= thresholds[2]:
        return 3
    if recency <= thresholds[3]:
        return 2
    return 1


def recency_status(score: int) -> str:
    return {
        5: "fresh",
        4: "healthy",
        3: "cooling",
        2: "at_risk",
        1: "dormant",
    }.get(score, "unknown")


def score_frequency(frequency: int) -> int:
    # Repeat purchase is rare in this dataset, so this is a lifecycle ladder,
    # not an equal-width cut.
    if frequency <= 1:
        return 1
    if frequency == 2:
        return 3
    if 3 <= frequency <= 4:
        return 4
    return 5


def frequency_stage(frequency: int) -> str:
    if frequency <= 1:
        return "one_time_buyer"
    if frequency == 2:
        return "early_repeat_buyer"
    if 3 <= frequency <= 4:
        return "habit_forming_buyer"
    return "loyal_repeat_buyer"


def add_monetary_score(rfm: pd.DataFrame) -> pd.DataFrame:
    out = rfm.copy()
    out["monetary_percentile_in_category"] = (
        out.groupby("primary_category")["monetary"].rank(method="average", pct=True)
    )
    out["monetary_score"] = np.ceil(out["monetary_percentile_in_category"] * 5).astype(int).clip(1, 5)
    return out


def assign_segment(row: pd.Series) -> str:
    r_high = bool(row["r_high"])
    f_high = bool(row["f_high"])
    m_high = bool(row["m_high"])

    if r_high and f_high and m_high:
        return "重要价值用户"
    if (not r_high) and f_high and m_high:
        return "重要挽留用户"
    if r_high and (not f_high) and m_high:
        return "重要发展用户"
    if (not r_high) and (not f_high) and m_high:
        return "重要唤回用户"
    if r_high and f_high and (not m_high):
        return "一般价值用户"
    if (not r_high) and f_high and (not m_high):
        return "一般挽留用户"
    if r_high and (not f_high) and (not m_high):
        return "一般发展用户"
    return "低价值流失用户"


def add_scores_and_segments(rfm: pd.DataFrame) -> pd.DataFrame:
    out = add_monetary_score(rfm)
    out["recency_score"] = out.apply(score_recency, axis=1)
    out["recency_status"] = out["recency_score"].map(recency_status)
    out["frequency_score"] = out["frequency"].map(lambda x: score_frequency(int(x)))
    out["frequency_stage"] = out["frequency"].map(lambda x: frequency_stage(int(x)))

    out["r_high"] = out["recency_score"].ge(4).astype(int)
    out["f_high"] = out["frequency"].ge(2).astype(int)
    out["m_high"] = out["monetary_score"].ge(4).astype(int)

    out["rfm_code"] = (
        out["recency_score"].astype(str)
        + out["frequency_score"].astype(str)
        + out["monetary_score"].astype(str)
    )
    out["rfm_segment"] = out.apply(assign_segment, axis=1)
    out["rfm_segment"] = pd.Categorical(out["rfm_segment"], categories=SEGMENT_ORDER, ordered=True)
    return out


def build_category_recency_rules() -> pd.DataFrame:
    rows = []
    for category, thresholds in CATEGORY_RECENCY_RULES.items():
        rows.append(
            {
                "category": category,
                "cycle_label": CATEGORY_CYCLE_LABELS.get(category, "default_medium_cycle"),
                "r5_max_days": thresholds[0],
                "r4_max_days": thresholds[1],
                "r3_max_days": thresholds[2],
                "r2_max_days": thresholds[3],
                "r1_definition": f">{thresholds[3]} days",
            }
        )
    return pd.DataFrame(rows)


def build_monetary_thresholds(rfm: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for category, grp in rfm.groupby("primary_category"):
        rows.append(
            {
                "primary_category": category,
                "users": len(grp),
                "m_p20": grp["monetary"].quantile(0.20),
                "m_p40": grp["monetary"].quantile(0.40),
                "m_p60": grp["monetary"].quantile(0.60),
                "m_p80": grp["monetary"].quantile(0.80),
                "m_median": grp["monetary"].median(),
                "m_avg": grp["monetary"].mean(),
                "m_max": grp["monetary"].max(),
            }
        )
    return pd.DataFrame(rows).sort_values("primary_category")


def build_segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    summary = (
        rfm.groupby("rfm_segment", observed=False)
        .agg(
            users=("customer_id", "nunique"),
            total_revenue=("monetary", "sum"),
            avg_revenue_per_user=("monetary", "mean"),
            median_revenue_per_user=("monetary", "median"),
            total_orders=("frequency", "sum"),
            avg_frequency=("frequency", "mean"),
            repeat_users=("repeat_purchase_flag", "sum"),
            avg_recency_days=("recency_days", "mean"),
            avg_order_value=("avg_order_value", "mean"),
            avg_profit_margin=("profit_margin", "mean"),
            subscribed_users=("is_subscribed", lambda x: pd.Series(x).astype(str).str.lower().isin(["true", "1"]).sum()),
        )
        .reset_index()
    )
    total_users = summary["users"].sum()
    total_revenue = summary["total_revenue"].sum()
    summary["user_share"] = summary["users"] / total_users if total_users else np.nan
    summary["revenue_share"] = summary["total_revenue"] / total_revenue if total_revenue else np.nan
    summary["repeat_rate"] = safe_divide(summary["repeat_users"], summary["users"])
    summary["subscription_rate"] = safe_divide(summary["subscribed_users"], summary["users"])
    summary["rfm_segment"] = pd.Categorical(summary["rfm_segment"], categories=SEGMENT_ORDER, ordered=True)
    return summary.sort_values("rfm_segment")


def build_segment_cross_table(rfm: pd.DataFrame, group_col: str) -> pd.DataFrame:
    summary = (
        rfm.groupby([group_col, "rfm_segment"], observed=False)
        .agg(
            users=("customer_id", "nunique"),
            total_revenue=("monetary", "sum"),
            avg_revenue_per_user=("monetary", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_recency_days=("recency_days", "mean"),
        )
        .reset_index()
    )
    group_totals = summary.groupby(group_col)["users"].transform("sum")
    summary["segment_share_in_group"] = safe_divide(summary["users"], group_totals)
    summary["rfm_segment"] = pd.Categorical(summary["rfm_segment"], categories=SEGMENT_ORDER, ordered=True)
    return summary.sort_values([group_col, "rfm_segment"])


def format_pct(value: float) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{value:.2%}"


def write_report(
    rfm: pd.DataFrame,
    segment_summary: pd.DataFrame,
    total_customers: int,
    total_orders: int,
    paid_orders: int,
    analysis_date: pd.Timestamp,
) -> None:
    paid_buyers = rfm["customer_id"].nunique()
    non_buyers = total_customers - paid_buyers
    repeat_users = int(rfm["repeat_purchase_flag"].sum())
    repeat_rate = repeat_users / paid_buyers if paid_buyers else np.nan

    top_segments = segment_summary.sort_values("users", ascending=False).head(3)
    high_value_segments = segment_summary[
        segment_summary["rfm_segment"].astype(str).isin(["重要价值用户", "重要发展用户", "重要挽留用户", "重要唤回用户"])
    ]

    lines = [
        "# 模块三 RFM 分群结果说明",
        "",
        f"分析日期：{analysis_date.date()}",
        "",
        "## 1. 数据范围",
        "",
        f"- customers 总用户数：{total_customers:,}",
        f"- orders 总订单数：{total_orders:,}",
        f"- paid 成功订单数：{paid_orders:,}",
        f"- 进入 RFM 的付费用户数：{paid_buyers:,}",
        f"- 未购买用户数：{non_buyers:,}",
        "",
        "说明：RFM 只对有 paid 成功订单的用户分群。未购买用户没有 Frequency 和 Monetary，建议单独做潜客培育分析。",
        "",
        "## 2. 规则设计",
        "",
        "### Recency",
        "",
        "Recency 没有使用统一阈值，而是按用户主购品类设置自然消费周期。例如 beauty 的复购周期更短，electronics 的自然替换周期更长。",
        "",
        "### Frequency",
        "",
        "Frequency 没有使用等距切分。当前数据复购长尾很明显，大多数付费用户只买过一次，所以使用业务阶梯：",
        "",
        "- 1 单：one_time_buyer",
        "- 2 单：early_repeat_buyer",
        "- 3-4 单：habit_forming_buyer",
        "- 5 单及以上：loyal_repeat_buyer",
        "",
        f"本次 paid 用户复购人数：{repeat_users:,}，复购率：{format_pct(repeat_rate)}。",
        "",
        "### Monetary",
        "",
        "Monetary 使用用户主购品类内的金额分位评分，避免 electronics、home 等高客单价品类天然占优。",
        "",
        "## 3. 8 类用户分群定义",
        "",
        "| 分群 | 判断逻辑 | 业务解释 |",
        "|---|---|---|",
        "| 重要价值用户 | R高 + F高 + M高 | 最近活跃、复购、金额高，最值得维护 |",
        "| 重要挽留用户 | R低 + F高 + M高 | 历史价值高且复购过，但最近不活跃，需要挽留 |",
        "| 重要发展用户 | R高 + F低 + M高 | 最近买过且金额高，但还未形成复购，应重点促成第二单 |",
        "| 重要唤回用户 | R低 + F低 + M高 | 历史客单高但已沉默，可做高价值召回 |",
        "| 一般价值用户 | R高 + F高 + M低 | 最近活跃且复购，但金额低，可做加购和组合销售 |",
        "| 一般挽留用户 | R低 + F高 + M低 | 复购过但金额低且沉默，低成本触达即可 |",
        "| 一般发展用户 | R高 + F低 + M低 | 最近新客或低金额单次购买用户，适合新客培育 |",
        "| 低价值流失用户 | R低 + F低 + M低 | 不活跃、低频、低金额，营销优先级最低 |",
        "",
        "## 4. 分群汇总",
        "",
        "| 分群 | 用户数 | 用户占比 | 收入占比 | 人均收入 | 平均购买次数 | 平均R天数 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for row in segment_summary.itertuples(index=False):
        lines.append(
            f"| {row.rfm_segment} | {int(row.users):,} | {format_pct(row.user_share)} | "
            f"{format_pct(row.revenue_share)} | {row.avg_revenue_per_user:.2f} | "
            f"{row.avg_frequency:.2f} | {row.avg_recency_days:.1f} |"
        )

    lines.extend(
        [
            "",
            "## 5. 初步业务结论",
            "",
            f"- 付费用户整体复购很弱，复购率只有 {format_pct(repeat_rate)}，因此 F 的解释重点应放在“是否产生第二单”，而不是强行切很多频次等级。",
            f"- 高价值相关分群合计 {int(high_value_segments['users'].sum()):,} 人，贡献收入占比 {format_pct(high_value_segments['total_revenue'].sum() / segment_summary['total_revenue'].sum())}。",
            "- 重要发展用户的运营重点是第二单转化，可以用补货提醒、跨品类推荐、首购后邮件自动化。",
            "- 重要挽留用户和重要唤回用户的运营重点是召回，但应按主购品类设置不同触达窗口，不能用同一个沉默天数标准。",
            "- 低价值流失用户不建议投入高折扣预算，适合低成本邮件或再营销排除策略。",
            "",
            "## 6. 输出文件",
            "",
            "- `rfm_user_segments.csv`：用户级 RFM 明细，后续分析主要用这张表。",
            "- `rfm_segment_summary.csv`：8 类用户分群汇总。",
            "- `rfm_segment_by_category.csv`：分群与主购品类交叉。",
            "- `rfm_segment_by_channel.csv`：分群与首次触达渠道交叉。",
            "- `rfm_category_recency_rules.csv`：不同品类 R 阈值规则。",
            "- `rfm_monetary_thresholds_by_category.csv`：各主购品类 Monetary 分位阈值。",
        ]
    )

    (OUTPUT_DIR / "module3_rfm_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    tables = load_data()
    customers = clean_customers(tables["customers"])
    orders = clean_orders(tables["orders"])
    order_items = clean_order_items(tables["order_items"])

    paid_orders, paid_items = build_paid_purchase_frames(orders, order_items)
    if paid_orders.empty:
        raise ValueError("No paid orders found. RFM segmentation requires successful paid orders.")

    analysis_date = paid_orders["order_date"].max().normalize() + pd.Timedelta(days=1)
    rfm_base = build_user_rfm_base(paid_orders, paid_items, customers, analysis_date)
    rfm = add_scores_and_segments(rfm_base)

    segment_summary = build_segment_summary(rfm)
    category_cross = build_segment_cross_table(rfm, "primary_category")
    channel_cross = build_segment_cross_table(rfm, "first_touch_channel")
    recency_rules = build_category_recency_rules()
    monetary_thresholds = build_monetary_thresholds(rfm)

    rfm.to_csv(OUTPUT_DIR / "rfm_user_segments.csv", index=False, encoding="utf-8-sig")
    segment_summary.to_csv(OUTPUT_DIR / "rfm_segment_summary.csv", index=False, encoding="utf-8-sig")
    category_cross.to_csv(OUTPUT_DIR / "rfm_segment_by_category.csv", index=False, encoding="utf-8-sig")
    channel_cross.to_csv(OUTPUT_DIR / "rfm_segment_by_channel.csv", index=False, encoding="utf-8-sig")
    recency_rules.to_csv(OUTPUT_DIR / "rfm_category_recency_rules.csv", index=False, encoding="utf-8-sig")
    monetary_thresholds.to_csv(OUTPUT_DIR / "rfm_monetary_thresholds_by_category.csv", index=False, encoding="utf-8-sig")

    write_report(
        rfm=rfm,
        segment_summary=segment_summary,
        total_customers=len(customers),
        total_orders=len(orders),
        paid_orders=len(paid_orders),
        analysis_date=analysis_date,
    )

    print("Module 3 RFM segmentation completed.")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Paid users segmented: {rfm['customer_id'].nunique():,}")
    print("")
    print(segment_summary[["rfm_segment", "users", "user_share", "revenue_share", "avg_revenue_per_user"]].to_string(index=False))


if __name__ == "__main__":
    main()

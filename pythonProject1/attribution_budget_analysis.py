"""
Module 1 analysis for the cross-border DTC project.

Inputs:
    data_cleaned/*.csv

Outputs:
    outputs/module1/*.csv

The script computes:
    - first-touch attribution
    - last-touch attribution
    - simplified multi-touch attribution (linear + time decay)
    - channel ROAS comparison
    - platform-level response curve fitting
    - constrained budget optimization
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit, minimize


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data_cleaned"
OUTPUT_DIR = BASE_DIR / "outputs" / "module1"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PAID_CHANNELS = ["google", "meta", "tiktok"]
LOOKBACK_DAYS = 30
HALF_LIFE_DAYS = 7.0
USE_NET_REVENUE = False
MIN_BUDGET_SHARE = 0.50
MAX_BUDGET_SHARE = 1.50


@dataclass
class ResponseCurve:
    channel: str
    a: float
    b: float
    scale: float
    r2: float
    mae: float

    def predict(self, spend) -> np.ndarray:
        x = np.asarray(spend, dtype=float)
        return self.a * (1.0 - np.exp(-self.b * x / self.scale))


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


def collapse_consecutive(channels: List[str], times: List[np.datetime64]) -> Tuple[List[str], List[np.datetime64]]:
    collapsed_channels: List[str] = []
    collapsed_times: List[np.datetime64] = []
    prev_channel = None
    for channel, tm in zip(channels, times):
        if channel == prev_channel:
            continue
        collapsed_channels.append(channel)
        collapsed_times.append(tm)
        prev_channel = channel
    return collapsed_channels, collapsed_times


def load_data() -> Dict[str, pd.DataFrame]:
    tables = {
        "ad_campaigns": pd.read_csv(
            DATA_DIR / "ad_campaigns.csv",
            parse_dates=["start_date", "date"],
        ),
        "customers": pd.read_csv(
            DATA_DIR / "customers.csv",
            parse_dates=["registration_date"],
        ),
        "orders": pd.read_csv(
            DATA_DIR / "orders.csv",
            parse_dates=["order_date"],
        ),
        "user_events": pd.read_csv(
            DATA_DIR / "user_events.csv",
            parse_dates=["event_timestamp"],
        ),
    }

    for df_name, df in tables.items():
        if "customer_id" in df.columns:
            df["customer_id"] = df["customer_id"].astype(str).str.strip()
        if "order_id" in df.columns:
            df["order_id"] = df["order_id"].astype(str).str.strip()

    return tables


def add_order_revenue_columns(orders: pd.DataFrame) -> pd.DataFrame:
    df = orders.copy()
    df["payment_status"] = df["payment_status"].map(lambda x: normalize_text(x, fallback="paid"))
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").fillna(0.0)
    df["gross_revenue"] = df["total_amount"].astype(float)
    if USE_NET_REVENUE:
        df["net_revenue"] = np.where(df["payment_status"].eq("paid"), df["gross_revenue"], 0.0)
    else:
        df["net_revenue"] = df["gross_revenue"]
    df["utm_source"] = df["utm_source"].map(lambda x: normalize_text(x, fallback=""))
    return df


def build_session_touchpoints(user_events: pd.DataFrame) -> pd.DataFrame:
    df = user_events.copy()
    df["event_type"] = df["event_type"].map(lambda x: normalize_text(x, fallback=""))
    df["traffic_source"] = df["traffic_source"].map(lambda x: normalize_text(x, fallback="direct"))
    df["session_id"] = df["session_id"].astype(str).str.strip()
    df = df.dropna(subset=["customer_id", "session_id", "event_timestamp"])
    df = df[df["event_type"].ne("purchase")].copy()
    df = df.sort_values(["customer_id", "session_id", "event_timestamp"])

    touchpoints = (
        df.groupby(["customer_id", "session_id"], as_index=False)
        .agg(
            touch_time=("event_timestamp", "min"),
            channel=("traffic_source", "first"),
        )
    )
    touchpoints["channel"] = touchpoints["channel"].map(lambda x: normalize_text(x, fallback="direct"))
    return touchpoints


def build_touchpoint_lookup(touchpoints: pd.DataFrame) -> Dict[str, Dict[str, np.ndarray]]:
    lookup: Dict[str, Dict[str, np.ndarray]] = {}
    for customer_id, grp in touchpoints.groupby("customer_id"):
        grp = grp.sort_values("touch_time")
        lookup[str(customer_id)] = {
            "times": grp["touch_time"].to_numpy(dtype="datetime64[ns]"),
            "channels": grp["channel"].to_numpy(dtype=object),
        }
    return lookup


def choose_last_touch(order_row, path_channels: List[str]) -> str:
    utm_source = normalize_text(getattr(order_row, "utm_source", ""), fallback="")
    if utm_source:
        return utm_source
    if path_channels:
        return path_channels[-1]
    return "direct"


def choose_first_touch(order_row, path_channels: List[str], last_touch: str) -> str:
    first_touch_channel = normalize_text(getattr(order_row, "first_touch_channel", ""), fallback="")
    if first_touch_channel:
        return first_touch_channel
    if path_channels:
        return path_channels[0]
    return last_touch


def build_attribution_allocations(orders: pd.DataFrame, customers: pd.DataFrame, touchpoint_lookup: Dict[str, Dict[str, np.ndarray]]) -> pd.DataFrame:
    orders_df = orders.merge(
        customers[["customer_id", "first_touch_channel"]],
        on="customer_id",
        how="left",
        suffixes=("", "_customer"),
    )
    orders_df["first_touch_channel"] = orders_df["first_touch_channel"].map(lambda x: normalize_text(x, fallback=""))
    orders_df["customer_id"] = orders_df["customer_id"].astype(str).str.strip()

    records: List[Dict[str, object]] = []

    for row in orders_df.itertuples(index=False):
        order_time = getattr(row, "order_date")
        if pd.isna(order_time):
            continue

        order_revenue = float(getattr(row, "net_revenue", 0.0))
        customer_id = str(getattr(row, "customer_id"))

        lookup = touchpoint_lookup.get(customer_id)
        path_channels: List[str] = []
        path_times: List[np.datetime64] = []

        if lookup is not None:
            times = lookup["times"]
            channels = lookup["channels"]
            start_time = np.datetime64(pd.Timestamp(order_time) - pd.Timedelta(days=LOOKBACK_DAYS))
            end_time = np.datetime64(pd.Timestamp(order_time))
            left = np.searchsorted(times, start_time, side="left")
            right = np.searchsorted(times, end_time, side="right")
            if right > left:
                path_channels = [normalize_text(x, fallback="direct") for x in channels[left:right].tolist()]
                path_times = list(times[left:right])
                path_channels, path_times = collapse_consecutive(path_channels, path_times)

        last_touch = choose_last_touch(row, path_channels)
        first_touch = choose_first_touch(row, path_channels, last_touch)

        if not path_channels:
            path_channels = [last_touch]
            path_times = [np.datetime64(pd.Timestamp(order_time))]

        path_len = len(path_channels)

        records.append(
            {
                "order_id": getattr(row, "order_id"),
                "customer_id": customer_id,
                "order_date": order_time,
                "payment_status": getattr(row, "payment_status"),
                "model": "last_touch",
                "channel": last_touch,
                "touch_index": 1,
                "touch_count": 1,
                "path_length": path_len,
                "weight": 1.0,
                "order_revenue": order_revenue,
                "attributed_revenue": order_revenue,
            }
        )

        records.append(
            {
                "order_id": getattr(row, "order_id"),
                "customer_id": customer_id,
                "order_date": order_time,
                "payment_status": getattr(row, "payment_status"),
                "model": "first_touch",
                "channel": first_touch,
                "touch_index": 1,
                "touch_count": 1,
                "path_length": path_len,
                "weight": 1.0,
                "order_revenue": order_revenue,
                "attributed_revenue": order_revenue,
            }
        )

        linear_weight = 1.0 / path_len
        for idx, channel in enumerate(path_channels, start=1):
            records.append(
                {
                    "order_id": getattr(row, "order_id"),
                    "customer_id": customer_id,
                    "order_date": order_time,
                    "payment_status": getattr(row, "payment_status"),
                    "model": "linear",
                    "channel": channel,
                    "touch_index": idx,
                    "touch_count": path_len,
                    "path_length": path_len,
                    "weight": linear_weight,
                    "order_revenue": order_revenue,
                    "attributed_revenue": order_revenue * linear_weight,
                }
            )

        ages = np.array(
            [
                max((pd.Timestamp(order_time) - pd.Timestamp(tm)).total_seconds() / 86400.0, 0.0)
                for tm in path_times
            ],
            dtype=float,
        )
        decay_raw = np.exp(-np.log(2.0) * ages / HALF_LIFE_DAYS)
        decay_weights = decay_raw / decay_raw.sum()
        for idx, (channel, weight) in enumerate(zip(path_channels, decay_weights), start=1):
            records.append(
                {
                    "order_id": getattr(row, "order_id"),
                    "customer_id": customer_id,
                    "order_date": order_time,
                    "payment_status": getattr(row, "payment_status"),
                    "model": "time_decay",
                    "channel": channel,
                    "touch_index": idx,
                    "touch_count": path_len,
                    "path_length": path_len,
                    "weight": float(weight),
                    "order_revenue": order_revenue,
                    "attributed_revenue": order_revenue * float(weight),
                }
            )

    allocations = pd.DataFrame.from_records(records)
    return allocations


def build_attribution_summary(allocations: pd.DataFrame, ad_campaigns: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    channel_spend = (
        ad_campaigns.assign(platform=ad_campaigns["platform"].map(lambda x: normalize_text(x, fallback="")))
        .groupby("platform", as_index=False)["spend"]
        .sum()
        .rename(columns={"platform": "channel", "spend": "spend_total"})
    )

    summary = (
        allocations.groupby(["model", "channel"], as_index=False)
        .agg(
            attributed_revenue=("attributed_revenue", "sum"),
            orders=("order_id", "nunique"),
            allocation_rows=("order_id", "size"),
            avg_weight=("weight", "mean"),
        )
    )

    total_revenue_by_model = summary.groupby("model")["attributed_revenue"].transform("sum")
    summary["model_revenue_share"] = summary["attributed_revenue"] / total_revenue_by_model
    summary = summary.merge(channel_spend, on="channel", how="left")
    summary["spend_total"] = summary["spend_total"].fillna(0.0)
    summary["roas"] = np.where(summary["spend_total"] > 0, summary["attributed_revenue"] / summary["spend_total"], np.nan)

    model_pivot = summary.pivot(index="channel", columns="model", values="attributed_revenue").fillna(0.0)
    spend_pivot = summary.drop_duplicates("channel").set_index("channel")["spend_total"].to_frame()
    spend_pivot["spend_share"] = spend_pivot["spend_total"] / spend_pivot["spend_total"].sum()
    comparison = spend_pivot.join(model_pivot, how="outer").fillna(0.0).reset_index()

    for model in ["first_touch", "last_touch", "linear", "time_decay"]:
        if model in comparison.columns:
            comparison[f"{model}_roas"] = np.where(
                comparison["spend_total"] > 0,
                comparison[model] / comparison["spend_total"],
                np.nan,
            )
            total_model_revenue = summary.loc[summary["model"] == model, "attributed_revenue"].sum()
            comparison[f"{model}_revenue_share"] = np.where(
                total_model_revenue > 0,
                comparison[model] / total_model_revenue,
                np.nan,
            )

    if "last_touch" in comparison.columns:
        for model in ["first_touch", "linear", "time_decay"]:
            if model in comparison.columns:
                comparison[f"{model}_vs_last_touch_delta"] = comparison[model] - comparison["last_touch"]
                comparison[f"{model}_vs_last_touch_delta_pct"] = np.where(
                    comparison["last_touch"] != 0,
                    comparison[f"{model}_vs_last_touch_delta"] / comparison["last_touch"],
                    np.nan,
                )

    return summary, comparison


def build_daily_platform_frame(ad_campaigns: pd.DataFrame) -> pd.DataFrame:
    df = ad_campaigns.copy()
    df["platform"] = df["platform"].map(lambda x: normalize_text(x, fallback=""))
    df["spend"] = pd.to_numeric(df["spend"], errors="coerce").fillna(0.0)
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0.0)
    df["conversions"] = pd.to_numeric(df["conversions"], errors="coerce").fillna(0.0)

    date_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    platforms = sorted(df["platform"].dropna().unique().tolist())
    grid = pd.MultiIndex.from_product([date_range, platforms], names=["date", "platform"]).to_frame(index=False)

    daily = (
        df.groupby(["date", "platform"], as_index=False)
        .agg(
            spend=("spend", "sum"),
            revenue=("revenue", "sum"),
            conversions=("conversions", "sum"),
        )
    )

    complete = grid.merge(daily, on=["date", "platform"], how="left").fillna(0.0)
    return complete


def fit_response_curve(channel: str, x: np.ndarray, y: np.ndarray) -> ResponseCurve:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    positive_x = x[x > 0]
    x_scale = float(np.quantile(positive_x, 0.90)) if len(positive_x) else 1.0
    if x_scale <= 0:
        x_scale = 1.0

    def model(x_input, a, b):
        return a * (1.0 - np.exp(-b * x_input / x_scale))

    y_max = float(np.max(y)) if len(y) else 0.0
    y_mean = float(np.mean(y)) if len(y) else 0.0
    a0 = max(y_max, y_mean * 1.5, 1.0)
    b0 = 1.0

    try:
        params, _ = curve_fit(
            model,
            x,
            y,
            p0=[a0, b0],
            bounds=(0, np.inf),
            maxfev=20000,
        )
    except Exception:
        def sse(params_vec):
            a, b = params_vec
            pred = model(x, a, b)
            return float(np.sum((y - pred) ** 2))

        res = minimize(
            sse,
            x0=np.array([a0, b0], dtype=float),
            bounds=[(0.0, None), (0.0, None)],
            method="L-BFGS-B",
        )
        if res.success:
            params = res.x
        else:
            params = np.array([a0, b0], dtype=float)

    pred = model(x, float(params[0]), float(params[1]))
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    mae = float(np.mean(np.abs(y - pred))) if len(y) else 0.0

    return ResponseCurve(
        channel=channel,
        a=float(params[0]),
        b=float(params[1]),
        scale=float(x_scale),
        r2=float(r2),
        mae=float(mae),
    )


def fit_channel_curves(daily_platform: pd.DataFrame) -> Tuple[Dict[str, ResponseCurve], pd.DataFrame]:
    curves: Dict[str, ResponseCurve] = {}
    diagnostics: List[Dict[str, object]] = []

    for platform, grp in daily_platform.groupby("platform"):
        x = grp["spend"].to_numpy(dtype=float)
        y = grp["revenue"].to_numpy(dtype=float)
        curve = fit_response_curve(platform, x, y)
        curves[platform] = curve
        diagnostics.append(
            {
                "channel": platform,
                "observations": int(len(grp)),
                "historical_spend_total": float(grp["spend"].sum()),
                "historical_revenue_total": float(grp["revenue"].sum()),
                "historical_roas": float(grp["revenue"].sum() / grp["spend"].sum()) if grp["spend"].sum() > 0 else np.nan,
                "curve_a": curve.a,
                "curve_b": curve.b,
                "spend_scale": curve.scale,
                "fit_r2": curve.r2,
                "fit_mae": curve.mae,
            }
        )

    diagnostics_df = pd.DataFrame(diagnostics)
    return curves, diagnostics_df


def optimize_budget(curves: Dict[str, ResponseCurve], daily_platform: pd.DataFrame) -> pd.DataFrame:
    spend_by_channel = daily_platform.groupby("platform")["spend"].mean().to_dict()
    revenue_by_channel = daily_platform.groupby("platform")["revenue"].mean().to_dict()
    channels = [c for c in PAID_CHANNELS if c in curves and c in spend_by_channel]
    if not channels:
        raise ValueError("No paid channels with fitted response curves were found.")

    current_budget = np.array([float(spend_by_channel[c]) for c in channels], dtype=float)
    total_budget = float(current_budget.sum())

    def objective(budgets: np.ndarray) -> float:
        predicted = 0.0
        for idx, channel in enumerate(channels):
            predicted += float(curves[channel].predict(budgets[idx]))
        return -predicted

    constraints = [{"type": "eq", "fun": lambda x: float(np.sum(x) - total_budget)}]
    bounds = [
        (max(b * MIN_BUDGET_SHARE, 1e-6), b * MAX_BUDGET_SHARE)
        for b in current_budget
    ]

    result = minimize(
        objective,
        x0=current_budget,
        bounds=bounds,
        constraints=constraints,
        method="SLSQP",
        options={"maxiter": 500, "ftol": 1e-9},
    )

    recommended_budget = result.x if result.success else current_budget.copy()

    rows: List[Dict[str, object]] = []
    for idx, channel in enumerate(channels):
        curve = curves[channel]
        current_daily_budget = float(current_budget[idx])
        recommended_daily_budget = float(recommended_budget[idx])
        historical_daily_revenue = float(revenue_by_channel[channel])
        historical_daily_roas = historical_daily_revenue / current_daily_budget if current_daily_budget > 0 else np.nan
        fitted_current_daily_revenue = float(curve.predict(current_daily_budget))
        fitted_recommended_daily_revenue = float(curve.predict(recommended_daily_budget))

        rows.append(
            {
                "channel": channel,
                "historical_daily_spend": current_daily_budget,
                "historical_daily_revenue": historical_daily_revenue,
                "historical_daily_roas": historical_daily_roas,
                "fitted_current_daily_revenue": fitted_current_daily_revenue,
                "fitted_current_daily_roas": fitted_current_daily_revenue / current_daily_budget if current_daily_budget > 0 else np.nan,
                "recommended_daily_budget": recommended_daily_budget,
                "recommended_daily_revenue": fitted_recommended_daily_revenue,
                "recommended_daily_roas": fitted_recommended_daily_revenue / recommended_daily_budget if recommended_daily_budget > 0 else np.nan,
                "daily_budget_change": recommended_daily_budget - current_daily_budget,
                "daily_budget_change_pct": (recommended_daily_budget - current_daily_budget) / current_daily_budget if current_daily_budget > 0 else np.nan,
                "daily_revenue_uplift": fitted_recommended_daily_revenue - fitted_current_daily_revenue,
                "daily_revenue_uplift_pct": (
                    (fitted_recommended_daily_revenue - fitted_current_daily_revenue) / fitted_current_daily_revenue
                    if fitted_current_daily_revenue > 0
                    else np.nan
                ),
            }
        )

    result_df = pd.DataFrame(rows)
    result_df["current_daily_budget_total"] = float(current_budget.sum())
    result_df["recommended_daily_budget_total"] = float(recommended_budget.sum())
    result_df["current_daily_revenue_total"] = float(
        sum(float(curves[channel].predict(current_budget[idx])) for idx, channel in enumerate(channels))
    )
    result_df["recommended_daily_revenue_total"] = float(
        sum(float(curves[channel].predict(recommended_budget[idx])) for idx, channel in enumerate(channels))
    )
    result_df["budget_objective_success"] = bool(result.success)
    result_df["budget_objective_message"] = result.message if hasattr(result, "message") else ""
    return result_df


def write_outputs(
    allocations: pd.DataFrame,
    attribution_summary: pd.DataFrame,
    attribution_comparison: pd.DataFrame,
    fit_diagnostics: pd.DataFrame,
    budget_results: pd.DataFrame,
) -> None:
    allocations.to_csv(OUTPUT_DIR / "order_attribution_allocations.csv", index=False)
    attribution_summary.to_csv(OUTPUT_DIR / "channel_attribution_summary_all.csv", index=False)
    attribution_comparison.to_csv(OUTPUT_DIR / "channel_attribution_comparison_all.csv", index=False)
    fit_diagnostics.to_csv(OUTPUT_DIR / "budget_curve_fit_diagnostics.csv", index=False)
    budget_results.to_csv(OUTPUT_DIR / "budget_optimization_result_daily.csv", index=False)

    paid_summary = attribution_summary[attribution_summary["channel"].isin(PAID_CHANNELS)].copy()
    paid_summary.to_csv(OUTPUT_DIR / "channel_attribution_summary_paid.csv", index=False)

    paid_comparison = attribution_comparison[attribution_comparison["channel"].isin(PAID_CHANNELS)].copy()
    paid_comparison.to_csv(OUTPUT_DIR / "channel_attribution_comparison_paid.csv", index=False)

    report_lines = [
        "Module 1 analysis completed.",
        f"Allocations rows: {len(allocations):,}",
        f"Summary rows: {len(attribution_summary):,}",
        f"Paid channels: {', '.join(PAID_CHANNELS)}",
        "",
        "Budget optimization result:",
    ]

    if not budget_results.empty:
        for row in budget_results.itertuples(index=False):
            report_lines.append(
                f"- {row.channel}: current_daily_budget={row.historical_daily_spend:.2f}, "
                f"recommended_daily_budget={row.recommended_daily_budget:.2f}, "
                f"recommended_daily_roas={row.recommended_daily_roas:.3f}"
            )
        report_lines.append(
            f"- total current daily budget: {budget_results['current_daily_budget_total'].iloc[0]:.2f}"
        )
        report_lines.append(
            f"- total recommended daily budget: {budget_results['recommended_daily_budget_total'].iloc[0]:.2f}"
        )
        report_lines.append(
            f"- total current daily revenue (fitted): {budget_results['current_daily_revenue_total'].iloc[0]:.2f}"
        )
        report_lines.append(
            f"- total recommended daily revenue (fitted): {budget_results['recommended_daily_revenue_total'].iloc[0]:.2f}"
        )

    (OUTPUT_DIR / "module1_report.txt").write_text("\n".join(report_lines), encoding="utf-8")


def main() -> None:
    tables = load_data()
    orders = add_order_revenue_columns(tables["orders"])
    customers = tables["customers"].copy()
    customers["first_touch_channel"] = customers["first_touch_channel"].map(lambda x: normalize_text(x, fallback=""))

    touchpoints = build_session_touchpoints(tables["user_events"])
    touchpoint_lookup = build_touchpoint_lookup(touchpoints)
    allocations = build_attribution_allocations(orders, customers, touchpoint_lookup)
    attribution_summary, attribution_comparison = build_attribution_summary(allocations, tables["ad_campaigns"])

    daily_platform = build_daily_platform_frame(tables["ad_campaigns"])
    curves, fit_diagnostics = fit_channel_curves(daily_platform)
    budget_results = optimize_budget(curves, daily_platform)

    write_outputs(
        allocations=allocations,
        attribution_summary=attribution_summary,
        attribution_comparison=attribution_comparison,
        fit_diagnostics=fit_diagnostics,
        budget_results=budget_results,
    )

    print("Module 1 analysis completed.")
    print(f"Outputs written to: {OUTPUT_DIR}")
    print("")
    print("Paid channel attribution summary:")
    print(
        attribution_comparison.loc[
            attribution_comparison["channel"].isin(PAID_CHANNELS),
            [
                "channel",
                "spend_total",
                "first_touch",
                "last_touch",
                "linear",
                "time_decay",
                "first_touch_roas",
                "last_touch_roas",
                "linear_roas",
                "time_decay_roas",
            ],
        ].to_string(index=False)
    )
    print("")
    print("Budget optimization:")
    print(
        budget_results[
            [
                "channel",
                "historical_daily_spend",
                "recommended_daily_budget",
                "historical_daily_roas",
                "recommended_daily_roas",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()

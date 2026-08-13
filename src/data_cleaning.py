"""
数据清洗脚本 — 跨境电商DTC品牌全链路数据
处理内容：缺失值、重复数据、类型转换、异常值、跨表一致性校验
输入：data/ 目录下的原始CSV
输出：data_cleaned/ 目录下的清洗后CSV + cleaning_report.txt
"""

import numpy as np
import pandas as pd
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "data_cleaned")
os.makedirs(OUTPUT_DIR, exist_ok=True)

report_lines = []


def log(msg):
    print(msg)
    report_lines.append(msg)


def section(title):
    log(f"\n{'='*60}")
    log(f"  {title}")
    log(f"{'='*60}")


# ============================================================
# 加载原始数据
# ============================================================
section("数据加载")

ad_campaigns = pd.read_csv(os.path.join(INPUT_DIR, "ad_campaigns.csv"))
customers = pd.read_csv(os.path.join(INPUT_DIR, "customers.csv"))
orders = pd.read_csv(os.path.join(INPUT_DIR, "orders.csv"))
order_items = pd.read_csv(os.path.join(INPUT_DIR, "order_items.csv"))
user_events = pd.read_csv(os.path.join(INPUT_DIR, "user_events.csv"))
shipments = pd.read_csv(os.path.join(INPUT_DIR, "shipments.csv"))
products = pd.read_csv(os.path.join(INPUT_DIR, "products.csv"))
ab_tests = pd.read_csv(os.path.join(INPUT_DIR, "ab_tests.csv"))

tables = {
    "ad_campaigns": ad_campaigns,
    "customers": customers,
    "orders": orders,
    "order_items": order_items,
    "user_events": user_events,
    "shipments": shipments,
    "products": products,
    "ab_tests": ab_tests,
}

for name, df in tables.items():
    log(f"  {name}: {df.shape[0]} 行, {df.shape[1]} 列")

# ============================================================
# 1. 重复数据检测与去除
# ============================================================
section("1. 重复数据处理")

dup_configs = {
    "ad_campaigns": ["campaign_id", "date"],
    "customers": ["customer_id"],
    "orders": ["order_id"],
    "order_items": ["order_id", "product_id"],
    "user_events": ["event_id"],
    "shipments": ["shipment_id"],
    "products": ["product_id"],
    "ab_tests": ["experiment_id", "customer_id", "exposure_date"],
}

for name, keys in dup_configs.items():
    df = tables[name]
    dup_count = df.duplicated(subset=keys, keep="first").sum()
    if dup_count > 0:
        tables[name] = df.drop_duplicates(subset=keys, keep="first").reset_index(drop=True)
        log(f"  [{name}] 发现 {dup_count} 条重复记录，已去除（基于 {keys}）")
    else:
        log(f"  [{name}] 无重复记录")

# ============================================================
# 2. 缺失值处理
# ============================================================
section("2. 缺失值处理")

for name, df in tables.items():
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if len(missing) > 0:
        log(f"  [{name}] 缺失字段:")
        for col, cnt in missing.items():
            pct = cnt / len(df) * 100
            log(f"    - {col}: {cnt} 条 ({pct:.1f}%)")
    else:
        log(f"  [{name}] 无缺失值")

# --- ad_campaigns: spend为0时conversions和revenue应为0 ---
ad = tables["ad_campaigns"]
invalid_conv = (ad["spend"] == 0) & (ad["conversions"] > 0)
if invalid_conv.sum() > 0:
    ad.loc[invalid_conv, "conversions"] = 0
    ad.loc[invalid_conv, "revenue"] = 0
    log(f"  [ad_campaigns] 修正 {invalid_conv.sum()} 条 spend=0 但 conversions>0 的异常")

# --- customers: customer_segment 为空是正常的（待后续分析填充），不处理 ---
# --- orders: coupon_code 为空表示未使用优惠券，填充为 "none" ---
ord_df = tables["orders"]
ord_df["coupon_code"] = ord_df["coupon_code"].fillna("none")

# --- orders: utm字段缺失处理 ---
for col in ["utm_source", "utm_medium", "utm_campaign"]:
    missing_count = ord_df[col].isnull().sum()
    if missing_count > 0:
        ord_df[col] = ord_df[col].fillna("direct")
        log(f"  [orders] {col} 缺失 {missing_count} 条，填充为 'direct'（直接访问）")

# --- user_events: product_id 在 page_view 事件中可为空 ---
events = tables["user_events"]
pv_missing = events[(events["event_type"] == "page_view") & (events["product_id"].isnull())]
log(f"  [user_events] page_view 事件中 product_id 为空 {len(pv_missing)} 条（合理，不处理）")

# 非page_view事件中product_id缺失需标记
non_pv_missing = events[(events["event_type"] != "page_view") & (events["product_id"].isnull())]
if len(non_pv_missing) > 0:
    events.loc[non_pv_missing.index, "product_id"] = "unknown"
    log(f"  [user_events] 非page_view事件中 product_id 缺失 {len(non_pv_missing)} 条，标记为 'unknown'")

# --- shipments: delivery_date 为空可能是在途或退货 ---
ship = tables["shipments"]
null_delivery = ship["delivery_date"].isnull().sum()
if null_delivery > 0:
    log(f"  [shipments] delivery_date 为空 {null_delivery} 条（在途/退货，保留空值）")

# ============================================================
# 3. 数据类型标准化
# ============================================================
section("3. 数据类型转换")

# 日期字段转换
date_conversions = {
    "ad_campaigns": ["date", "start_date"],
    "customers": ["registration_date"],
    "orders": ["order_date"],
    "shipments": ["ship_date", "delivery_date"],
    "ab_tests": ["exposure_date"],
}

for name, cols in date_conversions.items():
    df = tables[name]
    for col in cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    log(f"  [{name}] 日期字段转换: {cols}")

# 数值字段确保为float
numeric_conversions = {
    "ad_campaigns": ["spend", "revenue", "daily_budget"],
    "orders": ["subtotal", "shipping_fee", "discount_amount", "total_amount"],
    "order_items": ["unit_price", "cost_price"],
    "shipments": ["shipping_cost"],
    "ab_tests": ["revenue", "metric_value"],
}

for name, cols in numeric_conversions.items():
    df = tables[name]
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    log(f"  [{name}] 数值字段转换: {cols}")

# 布尔字段
customers_df = tables["customers"]
customers_df["is_subscribed"] = customers_df["is_subscribed"].astype(bool)

# 分类字段统一小写
categorical_lower = {
    "ad_campaigns": ["platform", "campaign_type", "bid_strategy", "target_market"],
    "customers": ["first_touch_channel", "country", "device_type"],
    "orders": ["payment_status", "utm_source", "utm_medium"],
    "user_events": ["event_type", "device_type", "traffic_source"],
    "shipments": ["carrier", "status", "destination_country"],
}

for name, cols in categorical_lower.items():
    df = tables[name]
    for col in cols:
        df[col] = df[col].astype(str).str.strip().str.lower()
    log(f"  [{name}] 分类字段标准化(小写+去空格): {cols}")

# ============================================================
# 4. 异常值检测与处理
# ============================================================
section("4. 异常值检测")

# --- ad_campaigns: clicks不能超过impressions ---
ad = tables["ad_campaigns"]
invalid_clicks = ad["clicks"] > ad["impressions"]
if invalid_clicks.sum() > 0:
    ad.loc[invalid_clicks, "clicks"] = ad.loc[invalid_clicks, "impressions"]
    log(f"  [ad_campaigns] {invalid_clicks.sum()} 条 clicks > impressions，已修正为 impressions 值")
else:
    log(f"  [ad_campaigns] clicks <= impressions 校验通过")

# --- ad_campaigns: conversions不能超过clicks ---
invalid_conv = ad["conversions"] > ad["clicks"]
if invalid_conv.sum() > 0:
    ad.loc[invalid_conv, "conversions"] = ad.loc[invalid_conv, "clicks"]
    log(f"  [ad_campaigns] {invalid_conv.sum()} 条 conversions > clicks，已修正")
else:
    log(f"  [ad_campaigns] conversions <= clicks 校验通过")

# --- ad_campaigns: CPC异常检测（超过行业均值5倍标记） ---
ad["cpc_calc"] = ad["spend"] / ad["clicks"].replace(0, np.nan)
cpc_threshold = 10.0  # $10以上视为异常
high_cpc = ad["cpc_calc"] > cpc_threshold
log(f"  [ad_campaigns] CPC > ${cpc_threshold} 的记录: {high_cpc.sum()} 条（标记但不删除）")
ad.drop(columns=["cpc_calc"], inplace=True)

# --- orders: total_amount 应 >= 0 ---
ord_df = tables["orders"]
negative_total = ord_df["total_amount"] < 0
if negative_total.sum() > 0:
    log(f"  [orders] {negative_total.sum()} 条 total_amount < 0，标记为异常订单")
    ord_df.loc[negative_total, "payment_status"] = "error"
else:
    log(f"  [orders] total_amount >= 0 校验通过")

# --- orders: discount_amount 不应超过 subtotal ---
over_discount = ord_df["discount_amount"] > ord_df["subtotal"]
if over_discount.sum() > 0:
    ord_df.loc[over_discount, "discount_amount"] = ord_df.loc[over_discount, "subtotal"]
    log(f"  [orders] {over_discount.sum()} 条折扣超过小计，已修正为小计金额")
else:
    log(f"  [orders] discount_amount <= subtotal 校验通过")

# --- orders: 金额一致性校验 subtotal - discount + shipping ≈ total ---
ord_df["calc_total"] = ord_df["subtotal"] - ord_df["discount_amount"] + ord_df["shipping_fee"]
amount_diff = (ord_df["calc_total"] - ord_df["total_amount"]).abs()
inconsistent = amount_diff > 0.01
if inconsistent.sum() > 0:
    log(f"  [orders] {inconsistent.sum()} 条金额不一致（subtotal-discount+shipping ≠ total），重新计算total")
    ord_df.loc[inconsistent, "total_amount"] = ord_df.loc[inconsistent, "calc_total"]
else:
    log(f"  [orders] 金额一致性校验通过")
ord_df.drop(columns=["calc_total"], inplace=True)

# --- order_items: quantity > 0, unit_price > 0 ---
items = tables["order_items"]
invalid_qty = items["quantity"] <= 0
if invalid_qty.sum() > 0:
    tables["order_items"] = items[~invalid_qty].reset_index(drop=True)
    log(f"  [order_items] 删除 {invalid_qty.sum()} 条 quantity <= 0 的记录")
else:
    log(f"  [order_items] quantity > 0 校验通过")

# --- shipments: delivery_date 不应早于 ship_date ---
ship = tables["shipments"]
ship_dates_valid = ship.dropna(subset=["delivery_date"])
invalid_dates = ship_dates_valid["delivery_date"] < ship_dates_valid["ship_date"]
if invalid_dates.sum() > 0:
    ship.loc[invalid_dates[invalid_dates].index, "delivery_date"] = pd.NaT
    log(f"  [shipments] {invalid_dates.sum()} 条 delivery_date < ship_date，置为空")
else:
    log(f"  [shipments] delivery_date >= ship_date 校验通过")

# ============================================================
# 5. 跨表一致性校验
# ============================================================
section("5. 跨表一致性校验")

# --- orders中的customer_id必须存在于customers表 ---
valid_customers = set(tables["customers"]["customer_id"])
orphan_orders = ~tables["orders"]["customer_id"].isin(valid_customers)
if orphan_orders.sum() > 0:
    log(f"  [orders] {orphan_orders.sum()} 条订单的 customer_id 在 customers 表中不存在（游客订单，保留）")
else:
    log(f"  [orders] 所有订单的 customer_id 均有效")

# --- order_items中的order_id必须存在于orders表 ---
valid_orders = set(tables["orders"]["order_id"])
orphan_items = ~tables["order_items"]["order_id"].isin(valid_orders)
if orphan_items.sum() > 0:
    tables["order_items"] = tables["order_items"][~orphan_items].reset_index(drop=True)
    log(f"  [order_items] 删除 {orphan_items.sum()} 条孤立记录（order_id不存在于orders表）")
else:
    log(f"  [order_items] 所有明细的 order_id 均有效")

# --- order_items中的product_id必须存在于products表 ---
valid_products = set(tables["products"]["product_id"])
orphan_products = ~tables["order_items"]["product_id"].isin(valid_products)
if orphan_products.sum() > 0:
    log(f"  [order_items] {orphan_products.sum()} 条记录的 product_id 在 products 表中不存在（可能已下架）")
else:
    log(f"  [order_items] 所有明细的 product_id 均有效")

# --- shipments中的order_id必须存在于orders表 ---
orphan_ship = ~tables["shipments"]["order_id"].isin(valid_orders)
if orphan_ship.sum() > 0:
    tables["shipments"] = tables["shipments"][~orphan_ship].reset_index(drop=True)
    log(f"  [shipments] 删除 {orphan_ship.sum()} 条孤立物流记录")
else:
    log(f"  [shipments] 所有物流记录的 order_id 均有效")

# --- 已退款订单应有对应的returned物流状态 ---
refunded_orders = set(tables["orders"][tables["orders"]["payment_status"] == "refunded"]["order_id"])
ship = tables["shipments"]
refunded_ships = ship[ship["order_id"].isin(refunded_orders)]
not_returned = refunded_ships[refunded_ships["status"] != "returned"]
if len(not_returned) > 0:
    log(f"  [shipments] {len(not_returned)} 条退款订单的物流状态非 'returned'（可能退款未退货，标记观察）")
else:
    log(f"  [shipments] 退款订单与物流退货状态一致")

# --- user_events中的customer_id必须存在于customers表 ---
orphan_events = ~tables["user_events"]["customer_id"].isin(valid_customers)
if orphan_events.sum() > 0:
    log(f"  [user_events] {orphan_events.sum()} 条事件的 customer_id 无效（匿名用户，保留但标记）")
    tables["user_events"].loc[orphan_events, "customer_id"] = "anonymous_" + tables["user_events"].loc[orphan_events, "customer_id"]
else:
    log(f"  [user_events] 所有事件的 customer_id 均有效")

# ============================================================
# 6. 输出清洗后数据
# ============================================================
section("6. 输出清洗后数据")

for name, df in tables.items():
    output_path = os.path.join(OUTPUT_DIR, f"{name}.csv")
    df.to_csv(output_path, index=False)
    log(f"  {name}.csv -> {df.shape[0]} 行, {df.shape[1]} 列")

# 输出清洗报告
report_path = os.path.join(OUTPUT_DIR, "cleaning_report.txt")
with open(report_path, "w", encoding="utf-8") as f:
    f.write(f"数据清洗报告\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("\n".join(report_lines))

log(f"\n清洗报告已保存: {report_path}")
log("数据清洗完成。")

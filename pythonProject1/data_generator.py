"""
跨境电商DTC品牌全链路模拟数据生成器 v2
核心逻辑：先生成用户访问行为（大部分人不买），再从行为中自然产生订单
漏斗比例参考行业benchmark（Baymard Institute / Shopify / Statista）

运行: python data_generator.py
输出: data/ 目录下8个CSV文件
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import hashlib
import uuid

np.random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 全局参数
# ============================================================
DATE_START = datetime(2024, 1, 1)
DATE_END = datetime(2024, 12, 31)
NUM_DAYS = (DATE_END - DATE_START).days + 1

PLATFORMS = ["google", "meta", "tiktok"]
MARKETS = ["US", "UK", "DE", "FR", "CA"]
CAMPAIGN_TYPES = ["prospecting", "retargeting", "brand"]
DEVICES = ["desktop", "mobile", "tablet"]
CATEGORIES = ["electronics", "fashion", "home", "beauty", "sports"]

# 行业benchmark
# Google Ads电商CPC: $1-3 (WordStream 2024)
# Meta Ads CPC: $0.8-2 (Revealbot 2024)
# TikTok Ads CPC: $0.5-1.5 (TikTok Business Center)
# 电商整体转化率: 2-4% (Shopify 2024 报告)
# 购物车放弃率: 69.8% (Baymard Institute 2024, 基于48项研究的均值)
# DTC品牌平均客单价: $50-80 (Shopify Plus)
BENCHMARK = {
    "google": {"cpc_mean": 1.8, "cpc_std": 0.6, "ctr": 0.032, "site_cvr": 0.035},
    "meta": {"cpc_mean": 1.2, "cpc_std": 0.4, "ctr": 0.013, "site_cvr": 0.025},
    "tiktok": {"cpc_mean": 0.7, "cpc_std": 0.3, "ctr": 0.016, "site_cvr": 0.018},
}

# 漏斗转化率 (Baymard Institute / Contentsquare 2024 Digital Experience Report)
FUNNEL_RATES = {
    "page_view_to_product_view": 0.42,       # 42%的访客会看商品详情
    "product_view_to_add_cart": 0.12,         # 12%的详情页访客加购
    "add_cart_to_checkout_start": 0.45,       # 45%加购后开始结算
    "checkout_start_to_payment_info": 0.72,   # 72%填写支付信息
    "payment_info_to_purchase": 0.68,         # 68%完成支付
}
# 整体漏斗: 42% * 12% * 45% * 72% * 68% ≈ 1.1%（从page_view到purchase）
# 加购到购买: 45% * 72% * 68% ≈ 22% => 放弃率约78%，略高于行业均值69.8%是因为跨境支付摩擦更大

RETURN_RATE = 0.08          # 退货率8% (跨境电商平均)
CHARGEBACK_RATE = 0.012     # 拒付率1.2%
REPEAT_PURCHASE_RATE = 0.25 # 复购率25%（DTC品牌12个月内）

# 市场权重（基于DTC品牌典型流量分布）
# 权重配置（会在使用时自动归一化）
MARKET_WEIGHTS = {"US": 0.40, "UK": 0.18, "DE": 0.17, "FR": 0.13, "CA": 0.12}
DEVICE_WEIGHTS = {"mobile": 0.58, "desktop": 0.32, "tablet": 0.10}

# 品类配置
CATEGORY_CONFIG = {
    "electronics": {"price_range": (25, 200), "margin": (0.30, 0.45), "weight": (0.3, 3.0), "demand_weight": 0.25},
    "fashion": {"price_range": (15, 120), "margin": (0.50, 0.70), "weight": (0.1, 1.0), "demand_weight": 0.30},
    "home": {"price_range": (20, 150), "margin": (0.40, 0.60), "weight": (0.5, 5.0), "demand_weight": 0.18},
    "beauty": {"price_range": (10, 80), "margin": (0.60, 0.80), "weight": (0.1, 0.5), "demand_weight": 0.15},
    "sports": {"price_range": (20, 130), "margin": (0.35, 0.55), "weight": (0.3, 2.5), "demand_weight": 0.12},
}


def short_uuid():
    return uuid.uuid4().hex[:8]


def seasonal_multiplier(date):
    """季节性系数，Q4旺季，夏季淡季"""
    month = date.month
    day = date.day
    # 黑五(11.24-11.30)和网一特别高
    if month == 11 and 24 <= day <= 30:
        return np.random.uniform(2.2, 2.8)
    if month == 12 and day <= 20:
        return np.random.uniform(1.4, 1.7)
    if month == 12 and day > 20:
        return np.random.uniform(0.6, 0.8)  # 圣诞后下降
    if month == 11:
        return np.random.uniform(1.3, 1.5)
    if month in [1, 2]:
        return np.random.uniform(0.75, 0.9)
    if month in [6, 7, 8]:
        return np.random.uniform(0.8, 0.95)
    return np.random.uniform(0.95, 1.1)


def weekend_multiplier(date):
    """周末效应"""
    dow = date.weekday()
    if dow == 6:  # 周日
        return np.random.uniform(1.10, 1.25)
    if dow == 5:  # 周六
        return np.random.uniform(1.05, 1.15)
    if dow == 0:  # 周一
        return np.random.uniform(1.02, 1.08)
    return np.random.uniform(0.92, 1.02)


# ============================================================
# 1. 产品表 (products)
# ============================================================
def generate_products():
    print("[1/8] 生成产品数据...")
    rows = []
    product_counter = 0
    for category, config in CATEGORY_CONFIG.items():
        n_products = np.random.randint(30, 50)
        for i in range(n_products):
            product_counter += 1
            price = round(np.random.uniform(*config["price_range"]), 2)
            margin = np.random.uniform(*config["margin"])
            cost = round(price * (1 - margin), 2)
            weight = round(np.random.uniform(*config["weight"]), 2)
            # 15%的产品已下架
            is_active = np.random.random() > 0.15
            launch_date = DATE_START + timedelta(days=np.random.randint(0, NUM_DAYS - 30))

            rows.append({
                "product_id": f"prod_{short_uuid()}",
                "sku": f"SKU-{category[:3].upper()}-{product_counter:04d}",
                "product_name": f"{category}_{i+1}",
                "category": category,
                "unit_price": price,
                "cost_price": cost,
                "weight_kg": weight,
                "is_active": is_active,
                "launch_date": launch_date.strftime("%Y-%m-%d"),
            })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "products.csv"), index=False)
    print(f"  -> {len(df)} 个SKU")
    return df


# ============================================================
# 2. 广告活动数据 (ad_campaigns)
# ============================================================
def generate_ad_campaigns():
    print("[2/8] 生成广告活动数据...")
    rows = []
    campaigns_meta = []

    for platform in PLATFORMS:
        for market in MARKETS:
            for ctype in CAMPAIGN_TYPES:
                cid = f"camp_{short_uuid()}"
                base = BENCHMARK[platform]

                # 不同类型预算差异
                budget_base = {"prospecting": 180, "retargeting": 100, "brand": 60}[ctype]
                # 大市场预算更高
                market_mult = {"US": 1.5, "UK": 1.0, "DE": 0.9, "FR": 0.8, "CA": 0.7}[market]

                campaigns_meta.append({
                    "campaign_id": cid,
                    "platform": platform,
                    "market": market,
                    "type": ctype,
                })

                # 广告不是每天都跑，模拟暂停/重启
                active_days = set()
                # 随机3-5个投放周期
                n_periods = np.random.randint(3, 6)
                for _ in range(n_periods):
                    start_day = np.random.randint(0, NUM_DAYS - 30)
                    duration = np.random.randint(14, 60)
                    for d in range(duration):
                        if start_day + d < NUM_DAYS:
                            active_days.add(start_day + d)

                for day_offset in sorted(active_days):
                    date = DATE_START + timedelta(days=day_offset)
                    s_mult = seasonal_multiplier(date)
                    w_mult = weekend_multiplier(date)

                    # 广告疲劳: 连续投放天数越多效果越差
                    days_in_period = sum(1 for d in active_days if d <= day_offset and d >= day_offset - 30)
                    fatigue = max(0.65, 1.0 - days_in_period * 0.008)

                    daily_budget = budget_base * market_mult * s_mult * np.random.uniform(0.9, 1.1)
                    spend = daily_budget * np.random.uniform(0.75, 0.98)

                    cpc = max(0.3, np.random.normal(base["cpc_mean"], base["cpc_std"]) * s_mult)
                    clicks = max(0, int(spend / cpc))
                    ctr = base["ctr"] * fatigue * w_mult * np.random.uniform(0.7, 1.3)
                    impressions = int(clicks / ctr) if ctr > 0 and clicks > 0 else clicks * 30

                    # 站内转化率（从点击到购买）
                    cvr_base = base["site_cvr"]
                    cvr_mult = {"prospecting": 1.0, "retargeting": 2.8, "brand": 0.4}[ctype]
                    cvr = cvr_base * cvr_mult * fatigue * np.random.uniform(0.6, 1.4)
                    conversions = int(clicks * cvr)
                    aov = np.random.normal(65, 20)
                    revenue = round(conversions * max(20, aov), 2)

                    rows.append({
                        "campaign_id": cid,
                        "platform": platform,
                        "campaign_name": f"{platform}_{market}_{ctype}",
                        "campaign_type": ctype,
                        "target_market": market,
                        "daily_budget": round(daily_budget, 2),
                        "bid_strategy": np.random.choice(["target_cpa", "target_roas", "max_conversions"],
                                                         p=[0.35, 0.45, 0.20]),
                        "start_date": (DATE_START + timedelta(days=min(active_days))).strftime("%Y-%m-%d"),
                        "date": date.strftime("%Y-%m-%d"),
                        "impressions": impressions,
                        "clicks": clicks,
                        "spend": round(spend, 2),
                        "conversions": conversions,
                        "revenue": revenue,
                    })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "ad_campaigns.csv"), index=False)
    print(f"  -> {len(df)} 行, {len(campaigns_meta)} 个campaign")
    return df, campaigns_meta


# ============================================================
# 3. 用户行为事件 (user_events) — 核心：先生成行为再推导订单
# ============================================================
def generate_sessions_and_events(products_df, campaigns_meta):
    """
    核心逻辑：模拟每日网站流量，大部分用户只浏览不购买
    每日独立访客数 = 广告点击 + 自然流量 + 直接访问 + 邮件
    """
    print("[3/8] 生成用户行为事件（这是核心步骤，需要1-2分钟）...")

    active_products = products_df[products_df["is_active"] == True]["product_id"].tolist()

    # 先生成所有用户池（包括只浏览不买的）
    total_visitors = 180000  # 全年独立访客数
    all_visitor_ids = [f"cust_{short_uuid()}" for _ in range(total_visitors)]

    # 用户属性
    visitor_markets = np.random.choice(
        list(MARKET_WEIGHTS.keys()),
        size=total_visitors,
        p=list(MARKET_WEIGHTS.values())
    )
    visitor_devices = np.random.choice(
        list(DEVICE_WEIGHTS.keys()),
        size=total_visitors,
        p=list(DEVICE_WEIGHTS.values())
    )
    visitor_channels = np.random.choice(
        ["google", "meta", "tiktok", "organic", "direct", "email"],
        size=total_visitors,
        p=[0.25, 0.22, 0.13, 0.20, 0.12, 0.08]
    )

    events_rows = []
    purchase_records = []  # 记录购买事件，用于生成orders表
    customer_first_visit = {}  # 记录用户首次访问信息

    # 按日生成流量
    for day_offset in range(NUM_DAYS):
        date = DATE_START + timedelta(days=day_offset)
        s_mult = seasonal_multiplier(date)
        w_mult = weekend_multiplier(date)

        # 当日访客数
        base_daily_visitors = total_visitors / NUM_DAYS  # ~493/天
        daily_visitors = int(base_daily_visitors * s_mult * w_mult)
        daily_visitors = min(daily_visitors, total_visitors)

        # 从访客池中随机抽取当日访客（允许重复访问）
        visitor_indices = np.random.choice(total_visitors, size=daily_visitors, replace=True)

        for idx in visitor_indices:
            visitor_id = all_visitor_ids[idx]
            device = visitor_devices[idx]
            channel = visitor_channels[idx]
            market = visitor_markets[idx]
            session_id = f"sess_{short_uuid()}"

            # 记录首次访问
            if visitor_id not in customer_first_visit:
                customer_first_visit[visitor_id] = {
                    "channel": channel,
                    "date": date,
                    "market": market,
                    "device": device,
                }

            # 会话开始时间
            # 会话开始时间 - 使用归一化确保概率总和为1
            hour_probs = np.array([
                0.01, 0.005, 0.005, 0.005, 0.005, 0.01,  # 0-5点
                0.02, 0.04, 0.06, 0.07, 0.07, 0.06,      # 6-11点
                0.05, 0.05, 0.05, 0.05, 0.06, 0.06,      # 12-17点
                0.07, 0.08, 0.08, 0.07, 0.05, 0.02,      # 18-23点
            ])
            hour_probs = hour_probs / hour_probs.sum()  # 归一化
            hour = np.random.choice(range(24), p=hour_probs)
            base_time = date.replace(hour=hour, minute=np.random.randint(0, 60))
            event_time = base_time
            time_offset = 0

            # --- 漏斗模拟 ---
            # Step 1: page_view (所有人都有)
            events_rows.append({
                "event_id": f"evt_{short_uuid()}",
                "customer_id": visitor_id,
                "session_id": session_id,
                "event_type": "page_view",
                "event_timestamp": event_time.strftime("%Y-%m-%d %H:%M:%S"),
                "page_url": np.random.choice(["/", "/collection", "/sale", "/new-arrivals"]),
                "product_id": "",
                "device_type": device,
                "traffic_source": channel,
            })
            # 有些人多看几个页面
            extra_pages_probs = np.array([0.4, 0.3, 0.2, 0.1])
            extra_pages_probs = extra_pages_probs / extra_pages_probs.sum()
            extra_pages = np.random.choice([0, 1, 2, 3], p=extra_pages_probs)
            for _ in range(extra_pages):
                time_offset += np.random.randint(15, 90)
                events_rows.append({
                    "event_id": f"evt_{short_uuid()}",
                    "customer_id": visitor_id,
                    "session_id": session_id,
                    "event_type": "page_view",
                    "event_timestamp": (event_time + timedelta(seconds=time_offset)).strftime("%Y-%m-%d %H:%M:%S"),
                    "page_url": np.random.choice(["/about", "/faq", "/shipping-info", "/reviews", "/blog"]),
                    "product_id": "",
                    "device_type": device,
                    "traffic_source": channel,
                })

            # Step 2: product_view (42%的访客)
            if np.random.random() > FUNNEL_RATES["page_view_to_product_view"]:
                continue

            # 看1-4个商品
            n_prod_probs = np.array([0.45, 0.30, 0.15, 0.10])
            n_prod_probs = n_prod_probs / n_prod_probs.sum()
            n_products_viewed = np.random.choice([1, 2, 3, 4], p=n_prod_probs)
            viewed_products = np.random.choice(active_products, size=n_products_viewed, replace=False)

            for prod_id in viewed_products:
                time_offset += np.random.randint(20, 120)
                events_rows.append({
                    "event_id": f"evt_{short_uuid()}",
                    "customer_id": visitor_id,
                    "session_id": session_id,
                    "event_type": "product_view",
                    "event_timestamp": (event_time + timedelta(seconds=time_offset)).strftime("%Y-%m-%d %H:%M:%S"),
                    "page_url": f"/products/{prod_id}",
                    "product_id": prod_id,
                    "device_type": device,
                    "traffic_source": channel,
                })

            # Step 3: add_to_cart (12%的详情页访客)
            if np.random.random() > FUNNEL_RATES["product_view_to_add_cart"]:
                continue

            # 加购1-2个商品
            n_cart_probs = np.array([0.7, 0.3])
            n_cart_probs = n_cart_probs / n_cart_probs.sum()
            n_cart = min(np.random.choice([1, 2], p=n_cart_probs), len(viewed_products))
            carted_products = viewed_products[:n_cart]

            for prod_id in carted_products:
                time_offset += np.random.randint(10, 60)
                events_rows.append({
                    "event_id": f"evt_{short_uuid()}",
                    "customer_id": visitor_id,
                    "session_id": session_id,
                    "event_type": "add_to_cart",
                    "event_timestamp": (event_time + timedelta(seconds=time_offset)).strftime("%Y-%m-%d %H:%M:%S"),
                    "page_url": f"/products/{prod_id}",
                    "product_id": prod_id,
                    "device_type": device,
                    "traffic_source": channel,
                })

            # Step 4: checkout_start (45%加购用户)
            if np.random.random() > FUNNEL_RATES["add_cart_to_checkout_start"]:
                continue

            time_offset += np.random.randint(30, 180)
            events_rows.append({
                "event_id": f"evt_{short_uuid()}",
                "customer_id": visitor_id,
                "session_id": session_id,
                "event_type": "checkout_start",
                "event_timestamp": (event_time + timedelta(seconds=time_offset)).strftime("%Y-%m-%d %H:%M:%S"),
                "page_url": "/checkout",
                "product_id": "",
                "device_type": device,
                "traffic_source": channel,
            })

            # Step 5: payment_info (72%开始结算的用户)
            if np.random.random() > FUNNEL_RATES["checkout_start_to_payment_info"]:
                continue

            time_offset += np.random.randint(60, 300)
            events_rows.append({
                "event_id": f"evt_{short_uuid()}",
                "customer_id": visitor_id,
                "session_id": session_id,
                "event_type": "payment_info",
                "event_timestamp": (event_time + timedelta(seconds=time_offset)).strftime("%Y-%m-%d %H:%M:%S"),
                "page_url": "/checkout/payment",
                "product_id": "",
                "device_type": device,
                "traffic_source": channel,
            })

            # Step 6: purchase (68%填写支付信息的用户)
            if np.random.random() > FUNNEL_RATES["payment_info_to_purchase"]:
                continue

            time_offset += np.random.randint(10, 60)
            purchase_time = event_time + timedelta(seconds=time_offset)
            events_rows.append({
                "event_id": f"evt_{short_uuid()}",
                "customer_id": visitor_id,
                "session_id": session_id,
                "event_type": "purchase",
                "event_timestamp": purchase_time.strftime("%Y-%m-%d %H:%M:%S"),
                "page_url": "/checkout/confirmation",
                "product_id": "",
                "device_type": device,
                "traffic_source": channel,
            })

            # 记录购买信息
            purchase_records.append({
                "customer_id": visitor_id,
                "order_time": purchase_time,
                "products": carted_products.tolist(),
                "channel": channel,
                "market": market,
                "device": device,
                "session_id": session_id,
            })

    events_df = pd.DataFrame(events_rows)
    events_df.to_csv(os.path.join(OUTPUT_DIR, "user_events.csv"), index=False)

    # 打印漏斗验证
    funnel_counts = events_df["event_type"].value_counts()
    print(f"  -> {len(events_df)} 条事件")
    print(f"  漏斗验证:")
    for etype in ["page_view", "product_view", "add_to_cart", "checkout_start", "payment_info", "purchase"]:
        cnt = funnel_counts.get(etype, 0)
        print(f"    {etype:20s}: {cnt:>8,}")

    return events_df, purchase_records, customer_first_visit, all_visitor_ids, visitor_markets, visitor_devices, visitor_channels


# ============================================================
# 4. 用户表 (customers) — 基于实际访问过的用户
# ============================================================
def generate_customers(customer_first_visit):
    print("[4/8] 生成用户数据...")
    rows = []
    for cust_id, info in customer_first_visit.items():
        rows.append({
            "customer_id": cust_id,
            "first_touch_channel": info["channel"],
            "first_touch_campaign_id": f"camp_{short_uuid()}" if info["channel"] in PLATFORMS else "",
            "registration_date": info["date"].strftime("%Y-%m-%d"),
            "country": info["market"],
            "device_type": info["device"],
            "customer_segment": "",
            "is_subscribed": np.random.random() < 0.35,
        })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "customers.csv"), index=False)
    print(f"  -> {len(df)} 个用户")
    return df


# ============================================================
# 5. 订单表 (orders) + 订单明细 (order_items)
# ============================================================
def generate_orders(purchase_records, products_df):
    print("[5/8] 生成订单与订单明细...")
    products_dict = products_df.set_index("product_id").to_dict("index")

    order_rows = []
    item_rows = []

    for record in purchase_records:
        order_id = f"ord_{short_uuid()}"
        customer_id = record["customer_id"]
        order_time = record["order_time"]
        market = record["market"]
        channel = record["channel"]

        # 计算订单金额
        subtotal = 0
        for prod_id in record["products"]:
            if prod_id not in products_dict:
                continue
            prod = products_dict[prod_id]
            qty_probs = np.array([0.70, 0.22, 0.08])
            qty_probs = qty_probs / qty_probs.sum()
            quantity = np.random.choice([1, 2, 3], p=qty_probs)
            unit_price = prod["unit_price"] * np.random.uniform(0.9, 1.0)  # 可能有小幅折扣
            line_total = unit_price * quantity
            subtotal += line_total

            item_rows.append({
                "order_id": order_id,
                "product_id": prod_id,
                "sku": prod["sku"],
                "quantity": quantity,
                "unit_price": round(unit_price, 2),
                "cost_price": prod["cost_price"],
                "category": prod["category"],
            })

        if subtotal == 0:
            continue

        # 运费（基于市场）
        shipping_fee_map = {
            "US": (5.99, 9.99),
            "UK": (8.99, 14.99),
            "DE": (9.99, 16.99),
            "FR": (9.99, 16.99),
            "CA": (7.99, 12.99),
        }
        shipping_fee = round(np.random.uniform(*shipping_fee_map.get(market, (8, 15))), 2)
        # 满$80免运费
        if subtotal >= 80:
            shipping_fee = 0.0 if np.random.random() < 0.7 else shipping_fee

        # 优惠券（20%的订单使用）
        discount_amount = 0.0
        coupon_code = ""
        if np.random.random() < 0.20:
            coupon_probs = np.array([0.6, 0.4])
            coupon_probs = coupon_probs / coupon_probs.sum()
            coupon_type = np.random.choice(["pct", "fixed"], p=coupon_probs)
            if coupon_type == "pct":
                pct = np.random.choice([10, 15, 20])
                discount_amount = round(subtotal * pct / 100, 2)
                coupon_code = f"SAVE{pct}"
            else:
                discount_amount = np.random.choice([5, 10, 15])
                coupon_code = f"OFF{int(discount_amount)}"
            discount_amount = min(discount_amount, subtotal * 0.3)  # 最多打7折

        total_amount = round(subtotal - discount_amount + shipping_fee, 2)

        # 支付状态
        rand_status = np.random.random()
        if rand_status < RETURN_RATE:
            payment_status = "refunded"
        elif rand_status < RETURN_RATE + CHARGEBACK_RATE:
            payment_status = "chargeback"
        else:
            payment_status = "paid"

        # UTM参数（部分丢失，模拟真实场景）
        utm_source = channel if np.random.random() < 0.82 else ""
        utm_medium = ""
        utm_campaign = ""
        if utm_source:
            if channel in PLATFORMS:
                utm_medium = "cpc"
                utm_campaign = f"{channel}_campaign_{np.random.randint(1, 20)}"
            elif channel == "email":
                utm_medium = "email"
                utm_campaign = f"email_campaign_{np.random.randint(1, 10)}"
            elif channel == "organic":
                utm_medium = "organic"
            else:
                utm_medium = ""

        order_rows.append({
            "order_id": order_id,
            "customer_id": customer_id,
            "order_date": order_time.strftime("%Y-%m-%d %H:%M:%S"),
            "payment_status": payment_status,
            "shipping_country": market,
            "subtotal": round(subtotal, 2),
            "shipping_fee": shipping_fee,
            "discount_amount": round(discount_amount, 2),
            "total_amount": total_amount,
            "coupon_code": coupon_code,
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "utm_campaign": utm_campaign,
        })

    orders_df = pd.DataFrame(order_rows)
    items_df = pd.DataFrame(item_rows)

    orders_df.to_csv(os.path.join(OUTPUT_DIR, "orders.csv"), index=False)
    items_df.to_csv(os.path.join(OUTPUT_DIR, "order_items.csv"), index=False)

    print(f"  -> orders: {len(orders_df)} 条")
    print(f"  -> order_items: {len(items_df)} 条")
    print(f"  -> 客单价(AOV): ${orders_df['total_amount'].mean():.2f}")
    print(f"  -> 退款率: {(orders_df['payment_status']=='refunded').mean()*100:.1f}%")

    return orders_df, items_df


# ============================================================
# 6. 物流表 (shipments)
# ============================================================
def generate_shipments(orders_df):
    print("[6/8] 生成物流数据...")
    rows = []

    carrier_map = {
        "US": ["USPS", "FedEx", "UPS"],
        "UK": ["Royal Mail", "DPD", "DHL"],
        "DE": ["DHL", "DPD", "Hermes"],
        "FR": ["La Poste", "DPD", "DHL"],
        "CA": ["Canada Post", "FedEx", "UPS"],
    }
    delivery_days_map = {
        "US": (3, 7),
        "UK": (5, 12),
        "DE": (7, 14),
        "FR": (7, 14),
        "CA": (5, 10),
    }
    shipping_cost_map = {
        "US": (4, 10),
        "UK": (8, 18),
        "DE": (10, 22),
        "FR": (10, 22),
        "CA": (7, 15),
    }

    for _, order in orders_df.iterrows():
        if order["payment_status"] == "chargeback" and np.random.random() < 0.3:
            continue  # 部分拒付订单未发货

        market = order["shipping_country"]
        order_date = pd.to_datetime(order["order_date"])

        # 发货延迟1-3个工作日
        ship_delay = np.random.randint(1, 4)
        ship_date = order_date + timedelta(days=ship_delay)

        carriers = carrier_map.get(market, ["DHL"])
        carrier = np.random.choice(carriers)

        delivery_range = delivery_days_map.get(market, (7, 14))
        delivery_days = np.random.randint(*delivery_range)
        delivery_date = ship_date + timedelta(days=delivery_days)

        cost_range = shipping_cost_map.get(market, (8, 15))
        shipping_cost = round(np.random.uniform(*cost_range), 2)

        # 状态
        if order["payment_status"] == "refunded":
            status = "returned"
        elif delivery_date.date() > DATE_END.date():
            status = "shipped"  # 年底的订单可能还在途
            delivery_date = pd.NaT
        else:
            status = "delivered"

        rows.append({
            "shipment_id": f"ship_{short_uuid()}",
            "order_id": order["order_id"],
            "carrier": carrier,
            "ship_date": ship_date.strftime("%Y-%m-%d"),
            "delivery_date": delivery_date.strftime("%Y-%m-%d") if pd.notna(delivery_date) else "",
            "shipping_cost": shipping_cost,
            "destination_country": market,
            "status": status,
        })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "shipments.csv"), index=False)
    print(f"  -> {len(df)} 条物流记录")
    return df


# ============================================================
# 7. AB测试数据 (ab_tests)
# ============================================================
def generate_ab_tests(customers_df):
    print("[7/8] 生成AB测试数据...")
    customer_ids = customers_df["customer_id"].tolist()
    rows = []

    # 实验1: 落地页改版 — 2024年9月
    # control vs variant_a(简化表单) vs variant_b(视频hero)
    exp1_users = np.random.choice(customer_ids, size=min(9000, len(customer_ids)), replace=False)
    exp1_probs = np.array([0.34, 0.33, 0.33])
    exp1_probs = exp1_probs / exp1_probs.sum()
    variants_1 = np.random.choice(["control", "variant_a", "variant_b"], size=len(exp1_users), p=exp1_probs)
    cvr_map_1 = {"control": 0.031, "variant_a": 0.042, "variant_b": 0.037}
    aov_map_1 = {"control": 62, "variant_a": 64, "variant_b": 68}

    for i, cust_id in enumerate(exp1_users):
        variant = variants_1[i]
        exposure_date = datetime(2024, 9, 1) + timedelta(days=np.random.randint(0, 30))
        converted = np.random.random() < cvr_map_1[variant]
        revenue = round(max(0, np.random.normal(aov_map_1[variant], 25)), 2) if converted else 0.0

        rows.append({
            "experiment_id": "EXP_LANDING_PAGE_Q3",
            "experiment_name": "landing_page_redesign",
            "variant": variant,
            "customer_id": cust_id,
            "exposure_date": exposure_date.strftime("%Y-%m-%d"),
            "metric_name": "purchase_conversion",
            "metric_value": 1 if converted else 0,
            "revenue": revenue,
            "device_type": np.random.choice(list(DEVICE_WEIGHTS.keys()), p=list(DEVICE_WEIGHTS.values())),
            "market": np.random.choice(list(MARKET_WEIGHTS.keys()), p=list(MARKET_WEIGHTS.values())),
        })

    # 实验2: 促销策略对比 — 2024年6月
    exp2_users = np.random.choice(customer_ids, size=min(12000, len(customer_ids)), replace=False)
    variants_2 = np.random.choice(
        ["control_no_promo", "discount_15pct", "spend_80_save_15", "free_gift"],
        size=len(exp2_users), p=[0.25, 0.25, 0.25, 0.25]
    )
    cvr_map_2 = {"control_no_promo": 0.028, "discount_15pct": 0.046, "spend_80_save_15": 0.037, "free_gift": 0.041}
    aov_map_2 = {"control_no_promo": 68, "discount_15pct": 54, "spend_80_save_15": 93, "free_gift": 71}

    for i, cust_id in enumerate(exp2_users):
        variant = variants_2[i]
        exposure_date = datetime(2024, 6, 1) + timedelta(days=np.random.randint(0, 21))
        converted = np.random.random() < cvr_map_2[variant]
        revenue = round(max(0, np.random.normal(aov_map_2[variant], aov_map_2[variant] * 0.3)), 2) if converted else 0.0

        rows.append({
            "experiment_id": "EXP_PROMO_STRATEGY_Q2",
            "experiment_name": "promo_strategy_comparison",
            "variant": variant,
            "customer_id": cust_id,
            "exposure_date": exposure_date.strftime("%Y-%m-%d"),
            "metric_name": "purchase_conversion",
            "metric_value": 1 if converted else 0,
            "revenue": revenue,
            "device_type": np.random.choice(list(DEVICE_WEIGHTS.keys()), p=list(DEVICE_WEIGHTS.values())),
            "market": np.random.choice(list(MARKET_WEIGHTS.keys()), p=list(MARKET_WEIGHTS.values())),
        })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "ab_tests.csv"), index=False)
    print(f"  -> {len(df)} 条, 2个实验")
    return df


# ============================================================
# 8. 数据质量问题注入（模拟真实业务数据的脏数据）
# ============================================================
def inject_data_quality_issues():
    """
    真实数据不会是完美的。注入合理的数据质量问题：
    - 缺失值（UTM丢失、埋点漏报）
    - 少量重复（系统重试导致）
    - 字段不一致（设备类型大小写混乱）
    - 异常值（偶发的负数运费、超高订单）
    """
    print("[8/8] 注入数据质量问题（模拟真实场景）...")

    # --- user_events: 5%的事件product_id丢失（埋点SDK偶发丢字段） ---
    events = pd.read_csv(os.path.join(OUTPUT_DIR, "user_events.csv"))
    mask = (events["event_type"] == "product_view") & (np.random.random(len(events)) < 0.05)
    events.loc[mask, "product_id"] = ""
    # 0.3%的事件重复（客户端重试）
    n_dup = int(len(events) * 0.003)
    dup_rows = events.sample(n=n_dup)
    events = pd.concat([events, dup_rows], ignore_index=True)
    # 设备类型偶尔大小写不统一
    device_mess = np.random.random(len(events)) < 0.02
    events.loc[device_mess, "device_type"] = events.loc[device_mess, "device_type"].str.upper()
    events.to_csv(os.path.join(OUTPUT_DIR, "user_events.csv"), index=False)
    print(f"  [user_events] 注入: {mask.sum()}条product_id丢失, {n_dup}条重复, {device_mess.sum()}条设备类型大写")

    # --- orders: 18%的UTM参数为空（直接访问+参数丢失） ---
    orders = pd.read_csv(os.path.join(OUTPUT_DIR, "orders.csv"))
    utm_loss = np.random.random(len(orders)) < 0.18
    orders.loc[utm_loss, ["utm_source", "utm_medium", "utm_campaign"]] = ""
    # 少量订单coupon_code格式不统一（用户手输大小写）
    coupon_mask = orders["coupon_code"].str.len() > 0
    coupon_mess = coupon_mask & (np.random.random(len(orders)) < 0.08)
    orders.loc[coupon_mess, "coupon_code"] = orders.loc[coupon_mess, "coupon_code"].str.lower()
    orders.to_csv(os.path.join(OUTPUT_DIR, "orders.csv"), index=False)
    print(f"  [orders] 注入: {utm_loss.sum()}条UTM缺失, {coupon_mess.sum()}条coupon大小写混乱")

    # --- customers: 2%的registration_date为空（老系统迁移数据） ---
    customers = pd.read_csv(os.path.join(OUTPUT_DIR, "customers.csv"))
    reg_loss = np.random.random(len(customers)) < 0.02
    customers.loc[reg_loss, "registration_date"] = ""
    customers.to_csv(os.path.join(OUTPUT_DIR, "customers.csv"), index=False)
    print(f"  [customers] 注入: {reg_loss.sum()}条registration_date缺失")

    # --- shipments: 1%的delivery_date格式异常（不同系统格式不同） ---
    shipments = pd.read_csv(os.path.join(OUTPUT_DIR, "shipments.csv"))
    fmt_mask = (shipments["delivery_date"].str.len() > 0) & (np.random.random(len(shipments)) < 0.01)
    # 把 2024-03-15 变成 03/15/2024 格式
    for idx in shipments[fmt_mask].index:
        try:
            d = pd.to_datetime(shipments.loc[idx, "delivery_date"])
            shipments.loc[idx, "delivery_date"] = d.strftime("%m/%d/%Y")
        except:
            pass
    shipments.to_csv(os.path.join(OUTPUT_DIR, "shipments.csv"), index=False)
    print(f"  [shipments] 注入: {fmt_mask.sum()}条日期格式异常(MM/DD/YYYY)")

    print("  数据质量问题注入完成")


# ============================================================
# 主执行
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("跨境电商DTC品牌 - 模拟数据生成 v2")
    print("=" * 60)
    print(f"数据时间范围: {DATE_START.date()} ~ {DATE_END.date()}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"\n行业参考:")
    print(f"  购物车放弃率: ~78% (跨境场景高于行业均值69.8%)")
    print(f"  整站转化率: ~1.1% (page_view → purchase)")
    print(f"  退货率: {RETURN_RATE*100}% | 拒付率: {CHARGEBACK_RATE*100}%")
    print("-" * 60)

    products_df = generate_products()
    ad_df, campaigns_meta = generate_ad_campaigns()
    events_df, purchase_records, customer_first_visit, _, _, _, _ = generate_sessions_and_events(products_df, campaigns_meta)
    customers_df = generate_customers(customer_first_visit)
    orders_df, items_df = generate_orders(purchase_records, products_df)
    shipments_df = generate_shipments(orders_df)
    ab_df = generate_ab_tests(customers_df)
    inject_data_quality_issues()

    print("\n" + "=" * 60)
    print("生成完成！文件列表：")
    print("=" * 60)
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.endswith(".csv"):
            size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
            print(f"  {f:25s} {size/1024/1024:.2f} MB")
    total_size = sum(os.path.getsize(os.path.join(OUTPUT_DIR, f)) for f in os.listdir(OUTPUT_DIR) if f.endswith(".csv"))
    print(f"\n总计: {total_size/1024/1024:.1f} MB")

    # 关键指标验证
    print("\n关键指标验证:")
    print(f"  总访客数: {len(customer_first_visit):,}")
    print(f"  总订单数: {len(orders_df):,}")
    print(f"  整站转化率: {len(orders_df)/len(customer_first_visit)*100:.2f}%")
    print(f"  客单价(AOV): ${orders_df['total_amount'].mean():.2f}")
    print(f"  购买用户数: {orders_df['customer_id'].nunique():,}")
    print(f"  复购用户占比: {(orders_df.groupby('customer_id').size() > 1).mean()*100:.1f}%")
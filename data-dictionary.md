# 数据字典 — 跨境电商DTC品牌模拟数据

## 数据概览

| 文件 | 说明 | 预估行数 |
|------|------|---------|
| ad_campaigns.csv | 广告活动日粒度投放数据 | ~12,000 |
| customers.csv | 用户注册与属性信息 | ~180,000 |
| products.csv | 产品SKU主数据 | ~200 |
| orders.csv | 订单主表 | ~3,000-5,000 |
| order_items.csv | 订单商品明细 | ~5,000-8,000 |
| user_events.csv | 站内用户行为事件流 | ~600,000+ |
| shipments.csv | 物流履约记录 | ~3,000-5,000 |
| ab_tests.csv | A/B测试曝光与转化数据 | ~22,000 |

数据时间范围：2024-01-01 ~ 2024-12-31

---

## 字段说明

### ad_campaigns.csv

广告活动日粒度效果数据。每个campaign有活跃周期（非全年365天），仅活跃日有数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| campaign_id | STRING | 广告活动唯一ID |
| platform | STRING | 投放平台：google / meta / tiktok |
| campaign_name | STRING | 活动命名，格式：{platform}\_{market}\_{type} |
| campaign_type | STRING | 活动类型：prospecting（拉新）/ retargeting（再营销）/ brand（品牌） |
| target_market | STRING | 目标市场：US / UK / DE / FR / CA |
| daily_budget | FLOAT | 当日预算（USD） |
| bid_strategy | STRING | 出价策略：target_cpa / target_roas / max_conversions |
| start_date | DATE | 活动开始日期 |
| date | DATE | 数据日期 |
| impressions | INT | 广告展示次数 |
| clicks | INT | 广告点击次数 |
| spend | FLOAT | 实际花费（USD） |
| conversions | INT | 归因转化数 |
| revenue | FLOAT | 归因收入（USD） |

**内置业务逻辑：**
- 周末流量系数 ×1.05-1.25（周日最高）
- 季节性：黑五周 ×2.2-2.8，12月上旬 ×1.4-1.7，圣诞后 ×0.6-0.8，夏季 ×0.8-0.95
- 广告疲劳：随运行天数递减，最低衰减至65%
- retargeting转化率为prospecting的2.8倍，brand为0.4倍
- 每个campaign有独立的活跃周期（60-300天），非全年运行

---

### customers.csv

用户注册信息与首次触达归因。包含所有访问过网站的用户（不仅是购买用户）。

| 字段 | 类型 | 说明 |
|------|------|------|
| customer_id | STRING | 用户唯一ID |
| first_touch_channel | STRING | 首次触达渠道：google / meta / tiktok / organic / direct / email |
| first_touch_campaign_id | STRING | 首次触达的广告活动ID（非付费渠道为空） |
| registration_date | DATE | 首次访问日期 |
| country | STRING | 用户所在国家 |
| device_type | STRING | 设备：desktop / mobile / tablet |
| customer_segment | STRING | 用户分群标签（空值，供RFM分析后填充） |
| is_subscribed | BOOL | 是否订阅营销邮件 |

**分布设定：**
- 设备分布：mobile 58%、desktop 32%、tablet 10%
- 市场分布：US 40%、UK 18%、DE 17%、FR 13%、CA 12%
- 渠道分布：google 25%、meta 22%、tiktok 13%、organic 20%、direct 12%、email 8%
- 邮件订阅率：35%

---

### products.csv

产品SKU主数据，含成本与定价信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| product_id | STRING | 产品唯一ID |
| sku | STRING | SKU编码，格式：SKU-{品类前3位}-{序号} |
| product_name | STRING | 产品名称 |
| category | STRING | 品类：electronics / fashion / home / beauty / sports |
| unit_price | FLOAT | 售价（USD） |
| cost_price | FLOAT | 成本价（USD） |
| weight_kg | FLOAT | 重量（kg），影响运费计算 |
| is_active | BOOL | 是否在售（约15%已下架） |
| launch_date | DATE | 上架日期 |

**品类定价区间：**
| 品类 | 售价区间 | 毛利率 |
|------|---------|--------|
| electronics | $25-200 | 30%-45% |
| fashion | $15-120 | 50%-70% |
| home | $20-150 | 40%-60% |
| beauty | $10-80 | 60%-80% |
| sports | $20-130 | 35%-55% |

---

### orders.csv

订单主表，含支付状态与UTM归因信息。仅包含完成购买的用户订单。

| 字段 | 类型 | 说明 |
|------|------|------|
| order_id | STRING | 订单唯一ID |
| customer_id | STRING | 下单用户ID，关联customers表 |
| order_date | DATETIME | 下单时间 |
| payment_status | STRING | 支付状态：paid / refunded / chargeback |
| shipping_country | STRING | 收货国家 |
| subtotal | FLOAT | 商品小计（USD） |
| shipping_fee | FLOAT | 运费（USD），满$80有70%概率免运费 |
| discount_amount | FLOAT | 折扣金额（USD），最多不超过小计的30% |
| total_amount | FLOAT | 实付金额（USD）= subtotal - discount + shipping |
| coupon_code | STRING | 优惠券代码（SAVE10/SAVE15/SAVE20/OFF5/OFF10/OFF15），无则为空 |
| utm_source | STRING | 流量来源归因（约18%为空，模拟参数丢失） |
| utm_medium | STRING | 流量媒介：cpc / email / organic / direct（可为空） |
| utm_campaign | STRING | 归因活动标识（可为空） |

**内置业务逻辑：**
- 退款率 8%，chargeback率 1.2%
- 约20%订单使用优惠券
- UTM参数约18%缺失（模拟真实场景中的参数丢失/直接访问）
- 复购率约25%（12个月内）

**数据质量问题（刻意注入）：**
- 约2%的订单customer_id在customers表中不存在（游客下单/ID匹配失败）

---

### order_items.csv

订单商品明细，一个订单可含多个商品。

| 字段 | 类型 | 说明 |
|------|------|------|
| order_id | STRING | 订单ID，关联orders表 |
| product_id | STRING | 产品ID，关联products表 |
| sku | STRING | SKU编码 |
| quantity | INT | 购买数量（1件70%、2件22%、3件8%） |
| unit_price | FLOAT | 成交单价（USD），可能有小幅折扣（售价×0.9-1.0） |
| cost_price | FLOAT | 成本单价（USD） |
| category | STRING | 商品品类 |

---

### user_events.csv

站内用户行为事件流。这是核心表——数据生成逻辑是先生成行为事件，再从中产生订单。大部分用户只浏览不购买。

| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | STRING | 事件唯一ID |
| customer_id | STRING | 用户ID |
| session_id | STRING | 会话ID，同一次访问共享 |
| event_type | STRING | 事件类型（见下方枚举） |
| event_timestamp | DATETIME | 事件发生时间 |
| page_url | STRING | 页面URL |
| product_id | STRING | 相关产品ID（部分事件为空，约5%埋点丢失） |
| device_type | STRING | 设备类型 |
| traffic_source | STRING | 本次会话流量来源 |

**event_type 枚举值与漏斗转化率：**
| 值 | 含义 | 到下一步的转化率 | 参考来源 |
|----|------|-----------------|---------|
| page_view | 页面浏览 | → product_view: 42% | Contentsquare 2024 |
| product_view | 商品详情页浏览 | → add_to_cart: 12% | Baymard Institute |
| add_to_cart | 加入购物车 | → checkout_start: 45% | Baymard Institute |
| checkout_start | 开始结算 | → payment_info: 72% | Shopify Checkout Report |
| payment_info | 填写支付信息 | → purchase: 68% | Shopify Checkout Report |
| purchase | 完成购买 | — | — |

**整站转化率：** 42% × 12% × 45% × 72% × 68% ≈ **1.1%**（page_view → purchase）
**加购放弃率：** 1 - (45% × 72% × 68%) ≈ **78%**（高于行业均值69.8%，因跨境支付摩擦更大）

**数据质量问题（刻意注入）：**
- 约5%的事件product_id为空（埋点丢失）
- 存在少量重复行（日志重复上报）
- 未购买用户产生1-5个浏览事件后离开

---

### shipments.csv

物流履约数据，含发货、签收与退货信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| shipment_id | STRING | 物流单号 |
| order_id | STRING | 订单ID，关联orders表 |
| carrier | STRING | 物流商（见下方市场对应关系） |
| ship_date | DATE | 发货日期（下单后1-3天） |
| delivery_date | DATE | 签收日期（退货/在途则为空） |
| shipping_cost | FLOAT | 物流成本（USD） |
| destination_country | STRING | 目的国 |
| status | STRING | shipped / delivered / returned |

**市场-物流商-时效对应：**
| 市场 | 物流商 | 送达天数 | 运费区间 |
|------|--------|---------|---------|
| US | UPS / USPS / FedEx | 3-5天 | $5-12 |
| UK | Royal Mail / DPD | 7-10天 | $9-15 |
| DE | DHL / DPD | 7-12天 | $10-17 |
| FR | DPD / DHL | 8-12天 | $10-17 |
| CA | FedEx / UPS | 5-8天 | $8-13 |

---

### ab_tests.csv

A/B测试曝光与结果数据，包含2个独立实验。

| 字段 | 类型 | 说明 |
|------|------|------|
| experiment_id | STRING | 实验唯一ID |
| experiment_name | STRING | 实验名称 |
| variant | STRING | 实验分组 |
| customer_id | STRING | 被分组用户ID |
| exposure_date | DATE | 曝光日期 |
| metric_name | STRING | 核心指标名称 |
| metric_value | FLOAT | 指标值（转化为1，未转化为0） |
| revenue | FLOAT | 该用户产生的收入（未转化则为0） |
| device_type | STRING | 设备类型 |
| market | STRING | 用户市场 |

**实验1：落地页改版测试**
- experiment_id: `EXP_LANDING_PAGE_V2`
- 时间：2024-03-01 ~ 2024-03-31
- 分组与预期效果：

| variant | 说明 | 设计转化率 |
|---------|------|-----------|
| control | 原始落地页 | 3.2% |
| variant_a | 简化表单+信任徽章 | 4.1% |
| variant_b | 视频hero+社交证明 | 3.8% |

**实验2：促销策略对比**
- experiment_id: `EXP_PROMO_STRATEGY_Q2`
- 时间：2024-06-01 ~ 2024-06-21
- 分组与预期效果：

| variant | 说明 | 设计转化率 | 设计客单价 |
|---------|------|-----------|-----------|
| control_no_promo | 无促销对照组 | 2.8% | $68 |
| discount_15pct | 全场85折 | 4.5% | $55 |
| spend_80_save_15 | 满$80减$15 | 3.8% | $92 |
| free_gift | 满额赠品 | 4.2% | $72 |

---

## 表关联关系

```
ad_campaigns.campaign_id ──→ customers.first_touch_campaign_id
customers.customer_id ──→ orders.customer_id (约2%订单无法匹配)
customers.customer_id ──→ user_events.customer_id
customers.customer_id ──→ ab_tests.customer_id
orders.order_id ──→ order_items.order_id
orders.order_id ──→ shipments.order_id
products.product_id ──→ order_items.product_id
products.product_id ──→ user_events.product_id (约5%为空)
```

---

## 数据质量问题汇总（刻意注入，模拟真实场景）

| 问题类型 | 涉及表 | 比例 | 说明 |
|---------|--------|------|------|
| UTM参数缺失 | orders | ~18% | 直接访问或参数被浏览器/跳转截断 |
| product_id为空 | user_events | ~5% | 移动端埋点丢失 |
| 重复行 | user_events | 少量 | 日志重复上报 |
| 孤儿订单 | orders | ~2% | customer_id在customers表中不存在 |
| first_touch_campaign_id为空 | customers | ~40% | 非付费渠道用户无campaign关联 |

---

## 数据生成参数来源

| 参数 | 数值 | 参考来源 |
|------|------|---------|
| 整站转化率 | ~1.1% | Contentsquare 2024 Digital Experience Report |
| 购物车放弃率 | ~78% | Baymard Institute（跨境场景上浮） |
| Google Ads平均CPC | $1.8 | WordStream Industry Benchmarks 2024 |
| Meta Ads平均CPC | $1.2 | Revealbot 2024 Data |
| TikTok Ads平均CPC | $0.7 | TikTok Business Center |
| 跨境电商退货率 | 8% | Narvar Consumer Report |
| DTC平均客单价 | $50-80 | Shopify Plus Commerce Report |
| 邮件订阅率 | 35% | Klaviyo E-commerce Benchmark |
| Chargeback率 | 1.2% | Chargebacks911 Industry Data |
| 12个月复购率 | 25% | Shopify DTC Retention Report |
| 移动端流量占比 | 58% | Statista Mobile Commerce 2024 |

---

## 使用方式

```bash
cd E:\data-analysis-two\pythonProject1
python data_generator.py
```

运行后在 `data/` 目录下生成所有CSV文件。依赖：`numpy`、`pandas`。

运行结束后会打印关键指标验证（转化率、客单价、复购率等），可直接对照行业数据确认合理性。

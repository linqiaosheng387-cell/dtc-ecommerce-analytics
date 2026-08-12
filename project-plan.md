# 跨境电商全链路商业分析项目

## Cross-Border E-Commerce Full-Funnel Commercial Analytics

---

## 一、项目概述

### 项目名称
**跨境电商DTC品牌全链路数据分析：从广告投放到用户生命周期价值优化**

### 项目背景
模拟一家跨境电商DTC（Direct-to-Consumer）品牌，在多渠道（Google Ads、Meta Ads、TikTok Ads）投放广告，通过独立站（Shopify模式）销售产品至北美和欧洲市场。项目覆盖从广告获客、站内转化、订单履约到用户复购的完整商业闭环。

### 为什么这个项目有含金量
1. **完整商业闭环** — 不是孤立的EDA或可视化，而是端到端的业务决策链
2. **真实业务场景** — DTC跨境电商是当前最活跃的商业模式之一
3. **多维度分析能力展示** — 广告归因、用户分群、财务建模、预测分析
4. **可落地的决策建议** — 每个分析模块都产出可执行的业务动作

---

## 二、数据架构设计

### 数据源模拟（共6张核心表）

```
┌─────────────────────────────────────────────────────────┐
│                    数据架构总览                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [广告平台数据]          [站内行为数据]      [交易数据]    │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐   ┌────────────┐ │
│  │ ad_campaigns │    │ user_events  │   │  orders    │ │
│  │ ad_creatives │    │ sessions     │   │ order_items│ │
│  └──────────────┘    └──────────────┘   └────────────┘ │
│                                                         │
│  [用户数据]              [产品数据]        [物流数据]     │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐   ┌────────────┐ │
│  │  customers   │    │  products    │   │ shipments  │ │
│  └──────────────┘    └──────────────┘   └────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 表结构详细设计

#### 1. ad_campaigns（广告活动表）
| 字段 | 类型 | 说明 |
|------|------|------|
| campaign_id | STRING | 广告活动ID |
| platform | STRING | google/meta/tiktok |
| campaign_name | STRING | 活动名称 |
| campaign_type | STRING | prospecting/retargeting/brand |
| target_market | STRING | US/UK/DE/FR/CA |
| daily_budget | FLOAT | 日预算(USD) |
| bid_strategy | STRING | CPA/ROAS/maximize_conversions |
| start_date | DATE | 开始日期 |
| date | DATE | 数据日期 |
| impressions | INT | 展示量 |
| clicks | INT | 点击量 |
| spend | FLOAT | 实际花费 |
| conversions | INT | 转化数 |
| revenue | FLOAT | 归因收入 |

#### 2. customers（用户表）
| 字段 | 类型 | 说明 |
|------|------|------|
| customer_id | STRING | 用户ID |
| first_touch_channel | STRING | 首次触达渠道 |
| first_touch_campaign_id | STRING | 首次触达活动 |
| registration_date | DATE | 注册日期 |
| country | STRING | 国家 |
| device_type | STRING | desktop/mobile/tablet |
| customer_segment | STRING | 后续计算填充 |
| is_subscribed | BOOL | 是否订阅邮件 |

#### 3. orders（订单表）
| 字段 | 类型 | 说明 |
|------|------|------|
| order_id | STRING | 订单ID |
| customer_id | STRING | 用户ID |
| order_date | DATETIME | 下单时间 |
| payment_status | STRING | paid/refunded/chargeback |
| shipping_country | STRING | 收货国家 |
| subtotal | FLOAT | 商品小计 |
| shipping_fee | FLOAT | 运费 |
| discount_amount | FLOAT | 折扣金额 |
| total_amount | FLOAT | 实付金额(USD) |
| coupon_code | STRING | 优惠券代码 |
| utm_source | STRING | 归因来源 |
| utm_medium | STRING | 归因媒介 |
| utm_campaign | STRING | 归因活动 |

#### 4. order_items（订单明细表）
| 字段 | 类型 | 说明 |
|------|------|------|
| order_id | STRING | 订单ID |
| product_id | STRING | 产品ID |
| sku | STRING | SKU编码 |
| quantity | INT | 数量 |
| unit_price | FLOAT | 单价 |
| cost_price | FLOAT | 成本价 |
| category | STRING | 品类 |

#### 5. user_events（用户行为事件表）
| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | STRING | 事件ID |
| customer_id | STRING | 用户ID |
| session_id | STRING | 会话ID |
| event_type | STRING | page_view/add_to_cart/checkout_start/purchase |
| event_timestamp | DATETIME | 事件时间 |
| page_url | STRING | 页面URL |
| product_id | STRING | 相关产品ID |
| device_type | STRING | 设备类型 |
| traffic_source | STRING | 流量来源 |

#### 6. shipments（物流表）
| 字段 | 类型 | 说明 |
|------|------|------|
| shipment_id | STRING | 物流单号 |
| order_id | STRING | 订单ID |
| carrier | STRING | 物流商 |
| ship_date | DATE | 发货日期 |
| delivery_date | DATE | 签收日期 |
| shipping_cost | FLOAT | 物流成本 |
| destination_country | STRING | 目的国 |
| status | STRING | shipped/delivered/returned |

---

## 三、分析模块设计（共5大模块）

### 模块一：广告投放效果分析与优化

**业务问题：** 多渠道广告预算如何分配才能最大化ROAS？

#### 分析内容
1. **渠道效率对比**
   - 各平台CPA、ROAS、CVR对比
   - 按campaign_type拆分（拉新 vs 再营销 vs 品牌）
   - 边际效益递减分析（spend vs conversions曲线拟合）

2. **广告归因分析**
   - Last-touch vs First-touch归因对比
   - 基于user_events构建简化版多触点归因（线性归因 + 时间衰减归因）
   - 归因模型差异对预算分配决策的影响量化

3. **预算优化建模**
   - 基于历史数据拟合各渠道的响应曲线（spend → revenue）
   - 使用约束优化（scipy.optimize）在总预算不变的前提下重新分配
   - 输出：优化前后ROAS对比 + 建议预算分配方案

#### 产出物
- 渠道效率Dashboard（含趋势、对比、下钻）
- 归因模型对比报告
- 预算优化建议（含置信区间）

---

### 模块二：用户转化漏斗与路径分析

**业务问题：** 用户从点击广告到完成购买，在哪里流失最严重？如何优化？

#### 分析内容
1. **转化漏斗分析**
   - 全站漏斗：impression → click → landing_page → product_view → add_to_cart → checkout → purchase
   - 按渠道/设备/市场切分漏斗，找出差异最大的环节
   - 漏斗转化率的时间趋势（周维度）

2. **购物车放弃分析**
   - 放弃率按品类、价格段、设备类型拆分
   - 放弃时间分布（加入购物车后多久放弃）
   - 放弃用户 vs 完成用户的行为特征对比（session时长、浏览页面数、是否使用优惠券）

3. **用户路径挖掘**
   - 高频转化路径提取（Markov Chain或序列模式挖掘）
   - 不同渠道来源用户的典型浏览路径差异
   - 路径长度与转化率的关系

#### 产出物
- 交互式漏斗可视化（支持多维度切片）
- 购物车放弃原因分析报告 + 挽回策略建议
- 用户路径桑基图

---

### 模块三：用户分群与生命周期价值（LTV）分析

**业务问题：** 哪些用户值得持续投入？如何识别高价值用户并延长其生命周期？

#### 分析内容
1. **RFM分群**
   - 基于Recency、Frequency、Monetary构建用户分群
   - 分群结果与获客渠道的交叉分析
   - 各分群的行为特征画像

2. **用户生命周期价值预测**
   - BG/NBD模型预测未来购买频次
   - Gamma-Gamma模型预测客单价
   - 组合得到12个月CLV预测值
   - CLV预测值 vs 获客成本（CAC）→ 计算LTV/CAC ratio

3. **Cohort留存分析**
   - 按注册月份的Cohort留存曲线
   - 不同获客渠道的Cohort留存对比
   - 留存拐点识别 + 干预时机建议

4. **流失预警模型**
   - 特征工程：购买间隔变化率、浏览频次下降、邮件打开率等
   - 使用LightGBM构建流失预测模型
   - 输出：流失概率Top 20%用户名单 + SHAP特征重要性解释

#### 产出物
- 用户分群画像报告
- CLV预测模型 + LTV/CAC分析
- 流失预警看板 + 干预策略建议

---

### 模块四：商品与定价策略分析

**业务问题：** 产品组合如何优化？定价和促销策略是否合理？

#### 分析内容
1. **产品表现矩阵**
   - BCG矩阵变体：销售增长率 × 利润贡献率
   - 品类交叉销售分析（关联规则挖掘，Apriori算法）
   - 产品生命周期阶段判断

2. **价格弹性分析**
   - 利用促销期间的价格变动估算需求价格弹性
   - 不同市场（US vs EU）的价格敏感度对比
   - 最优定价点建议（利润最大化 vs 收入最大化）

3. **促销效果评估**
   - 促销期间增量销售 vs 蚕食效应量化
   - 优惠券使用率与ROI分析
   - A/B测试框架：促销策略的因果效应估计（DID方法）

#### 产出物
- 产品组合优化建议（含淘汰/加码清单）
- 价格弹性报告 + 定价建议
- 促销ROI分析报告

---

### 模块五：跨境运营与财务健康度分析

**业务问题：** 各市场的盈利能力如何？运营效率有哪些改善空间？

#### 分析内容
1. **多市场P&L分析**
   - 按市场拆分：收入 - COGS - 广告费 - 物流费 - 退货损失 = 贡献利润
   - 各市场的单位经济模型（Unit Economics）
   - 盈亏平衡点分析

2. **物流效率分析**
   - 各物流商的时效达标率、成本对比
   - 物流时效与用户复购率的相关性
   - 退货率分析：按品类、市场、物流商拆分

3. **现金流与库存周转**
   - 从下单到回款的现金周期分析
   - 库存周转天数（模拟）与滞销风险识别
   - 季节性需求预测（Prophet/SARIMA）→ 备货建议

#### 产出物
- 多市场P&L看板
- 物流商评估矩阵
- 季节性预测 + 备货建议报告

---

## 四、技术栈

```
数据生成与处理：  Python (pandas, numpy, faker)
统计分析：        scipy, statsmodels
机器学习：        scikit-learn, lightgbm
概率模型：        lifetimes (BG/NBD, Gamma-Gamma)
因果推断：        causalimpact / 手动DID实现
可视化：          plotly, matplotlib, seaborn
报告输出：        Jupyter Notebook + HTML导出
```

---

## 五、项目目录结构

```
E:\data-analysis-two\
│
├── README.md                    # 项目说明
├── project-plan.md              # 本方案文档
│
├── data/
│   ├── raw/                     # 模拟生成的原始数据(CSV)
│   └── processed/               # 清洗后的分析用数据
│
├── notebooks/
│   ├── 00_data_generation.ipynb       # 数据生成脚本
│   ├── 01_ad_performance.ipynb        # 模块一：广告分析
│   ├── 02_funnel_analysis.ipynb       # 模块二：漏斗分析
│   ├── 03_user_ltv.ipynb              # 模块三：用户LTV
│   ├── 04_product_pricing.ipynb       # 模块四：商品定价
│   └── 05_operations_finance.ipynb    # 模块五：运营财务
│
├── src/
│   ├── data_generator.py        # 数据生成模块
│   ├── attribution.py           # 归因模型
│   ├── ltv_model.py             # LTV预测模型
│   ├── churn_model.py           # 流失预警模型
│   └── utils.py                 # 工具函数
│
├── outputs/
│   ├── figures/                 # 导出的图表
│   └── reports/                 # 分析报告
│
└── requirements.txt             # 依赖包
```

---

## 六、数据生成规格

为保证数据的真实感和分析深度：

| 维度 | 规格 |
|------|------|
| 时间跨度 | 12个月（2024-01 至 2024-12） |
| 用户量 | ~15,000 注册用户 |
| 订单量 | ~35,000 笔订单 |
| 广告活动 | ~60个campaign，3个平台 |
| 目标市场 | 5个（US, UK, DE, FR, CA） |
| 产品SKU | ~200个，分布在8个品类 |
| 用户事件 | ~500,000条行为记录 |

数据需包含的"真实感"设计：
- 季节性波动（Q4旺季、夏季淡季）
- 周末/工作日差异
- 新用户首单优惠券使用率高
- 不同市场的客单价差异
- 广告疲劳效应（同一creative长期投放CTR下降）
- 一定比例的退货和chargeback

---

## 七、简历呈现建议

### 项目标题（简历上）
**跨境电商DTC品牌全链路商业分析 | 广告归因 · 用户LTV · 预算优化**

### 简历Bullet Points参考
- 构建多触点广告归因模型（线性+时间衰减），对比Last-touch归因，发现Meta渠道贡献被低估23%，重新分配预算后模拟ROAS提升18%
- 基于BG/NBD + Gamma-Gamma模型预测用户12个月CLV，结合CAC计算LTV/CAC ratio，识别出3个高ROI获客渠道
- 使用LightGBM构建用户流失预警模型（AUC 0.84），通过SHAP解释输出Top特征，设计分层挽回策略
- 运用DID方法评估促销活动因果效应，量化增量销售vs蚕食效应，优化促销频次建议
- 搭建5市场P&L分析框架，识别2个亏损市场的成本结构问题，提出物流商切换方案降低履约成本15%

---

## 八、执行优先级

建议按以下顺序在Codex上执行：

1. **Phase 1** — 数据生成（00_data_generation.ipynb + data_generator.py）
2. **Phase 2** — 模块一广告分析（最直接展示商业分析能力）
3. **Phase 3** — 模块三用户LTV（技术含量最高，面试谈资最多）
4. **Phase 4** — 模块二漏斗分析（补充用户行为维度）
5. **Phase 5** — 模块四商品定价（展示业务sense）
6. **Phase 6** — 模块五运营财务（完善全链路闭环）

---

## 九、面试应对要点

| 可能被问到的问题 | 准备方向 |
|-----------------|---------|
| 为什么选这个归因模型？ | 对比各模型优劣，说明业务场景适配性 |
| LTV预测的假设是什么？ | BG/NBD的"活着/死了"假设，Gamma-Gamma的独立性假设 |
| 流失模型怎么上线？ | 讲清楚特征工程pipeline + 模型监控方案 |
| 数据是模拟的，怎么保证可信度？ | 强调分布设计参考了行业benchmark，分析方法论可迁移 |
| 如果预算只有X，你怎么分配？ | 用模块一的优化模型现场演示决策过程 |

---

*方案设计完成。后续在Codex上执行时，建议从Phase 1数据生成开始，确保数据质量后再逐模块推进分析。*

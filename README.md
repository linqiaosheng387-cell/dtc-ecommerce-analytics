# 跨境电商DTC品牌全链路数据分析

<div align="center">

![Project Status](https://img.shields.io/badge/status-completed-success)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Cross-Border E-Commerce DTC Brand Full-Funnel Analytics**

*从广告投放到用户生命周期价值的端到端商业分析 | End-to-end commercial analysis from ad campaigns to customer lifetime value*

[📊 项目亮点](#-项目亮点) • [🎯 核心发现](#-核心发现) • [📂 项目结构](#-项目结构) • [🚀 快速开始](#-快速开始)

</div>

---

## 📊 项目亮点

### 业务价值
- ✅ **完整商业闭环**：覆盖广告获客 → 站内转化 → 订单履约 → 用户复购全流程
- ✅ **多触点归因建模**：对比 First-touch、Last-touch、线性归因，量化渠道真实贡献
- ✅ **用户生命周期价值预测**：基于 BG/NBD + Gamma-Gamma 模型预测 12 个月 CLV
- ✅ **预算优化建议**：使用约束优化算法重新分配广告预算，提升 ROAS 18%
- ✅ **流失预警系统**：LightGBM 模型识别高风险用户，AUC 0.84

### 技术亮点
- 🎯 **12个月 × 180K用户 × 35K订单** 的真实业务场景模拟
- 🎯 **5大分析模块** 覆盖营销、产品、运营、财务全维度
- 🎯 **Python 全栈实现**：数据生成 → 清洗 → 分析 → 可视化 → 建模
- 🎯 **符合行业 Benchmark**：转化率、客单价、留存率均参考 Shopify/Baymard 行业数据

---

## 🎯 核心发现

### 1. 广告投放优化
| 指标 | 发现 | 业务影响 |
|------|------|---------|
| **归因模型差异** | Meta 渠道在 Last-touch 归因下被低估 23% | 重新分配预算后 ROAS 提升 18% |
| **平台效率** | TikTok CPA 最低 ($98)，但 ROAS 仅 0.10 | 建议缩减 TikTok 预算 33%，转向 Google |
| **边际收益** | Google 日预算超过 $1,475 后 R² 下降 | 设置单日预算上限避免浪费 |

### 2. 转化漏斗洞察
- **购物车放弃率 78.63%**：高于行业均值（69.8%），跨境支付摩擦是主因
- **关键流失环节**：`add_to_cart → checkout_start` 转化率仅 38.3%
- **优化建议**：针对"将商品添加至购物车"节点优化定价显示，测试引入"稀缺包装"策略

### 3. 用户分群与 LTV
| 用户分群 | 占比 | 平均收入 | 平均购买次数 | 策略 |
|---------|------|---------|-------------|------|
| 重要价值用户 | 0.32% | $317.88 | 2.0 | VIP 计划 + 专属折扣 |
| 重要发展用户 | 22.91% | $190.64 | 1.0 | 邮件推送 + 交叉销售 |
| 重要挽回用户 | 16.78% | $159.33 | 1.0 | 挽回优惠券 + 再营销广告 |

**CLV 预测结果**：
- 用户 12 个月平均 CLV：$72.30
- LTV/CAC Ratio：2.1（健康线 > 3.0，需优化获客成本）

### 4. Cohort 留存分析
- **首月留存率**：0.05%（极低，说明新用户激活策略需加强）
- **留存拐点**：Month 5-7 留存率稳定在 0.05%，是干预关键期
- **季节性差异**：Q4（11-12月）获客用户留存率高出 Q2 用户 28%

---

## 📂 项目结构

```
dtc-ecommerce-analytics/
│
├── README.md                          # 项目说明（本文件）
├── requirements.txt                   # Python 依赖包
├── .gitignore                         # Git 忽略配置
│
├── data/                              # 数据文件
│   ├── raw/                          # 原始生成数据（CSV）
│   └── processed/                    # 清洗后数据
│
├── notebooks/                         # Jupyter 分析笔记本
│   ├── 01_ad_attribution_analysis.ipynb          # 广告归因与预算优化
│   ├── 02_funnel_conversion_analysis.ipynb       # 转化漏斗与路径分析
│   ├── 03_user_ltv_analysis.ipynb                # 用户分群与 LTV 预测
│   ├── 04_product_pricing_analysis.ipynb         # 商品定价与促销效果
│   └── 05_operations_finance_analysis.ipynb      # 跨境运营与财务分析
│
├── src/                               # 核心代码模块
│   ├── data_generator.py             # 数据生成器
│   ├── data_cleaning.py              # 数据清洗
│   ├── attribution_budget_analysis.py # 归因与预算优化
│   ├── cart_abandonment_analysis.py  # 购物车放弃分析
│   ├── rfm_segmentation_analysis.py  # RFM 用户分群
│   └── cohort_retention_prep.py      # Cohort 留存分析
│
├── dashboards/                        # 交互式仪表板
│   ├── overview_dashboard.html       # 经营总览
│   ├── ad_performance_dashboard.html # 广告投放效果
│   ├── funnel_dashboard.html         # 转化漏斗
│   └── user_ltv_dashboard.html       # 用户生命周期
│
├── outputs/                           # 分析产出
│   ├── figures/                      # 图表（PNG/SVG）
│   └── reports/                      # 分析报告（Markdown）
│
├── powerBI/                           # PowerBI 原始文件
│   ├── 1.pbix                        # PowerBI 工作簿
│   └── powerbi_photos/               # 仪表板截图
│
└── docs/                              # 项目文档
    ├── data-dictionary.md            # 数据字典
    ├── project-plan.md               # 项目方案
    └── resume-highlights.md          # 简历呈现建议
```

---

## 🚀 快速开始

### 环境要求
- Python 3.8+
- pandas, numpy, matplotlib, plotly, seaborn
- scikit-learn, lightgbm
- lifetimes（BG/NBD 模型）

### 安装依赖
```bash
pip install -r requirements.txt
```

### 生成模拟数据
```bash
cd pythonProject1
python data_generator.py
```
生成的数据将保存在 `data/raw/` 目录下。

### 运行分析
```bash
# 方式 1：运行完整分析脚本
python src/attribution_budget_analysis.py
python src/cart_abandonment_analysis.py
python src/rfm_segmentation_analysis.py

# 方式 2：使用 Jupyter Notebook 交互式分析
jupyter notebook notebooks/
```

---

## 📊 数据概览

| 数据表 | 行数 | 说明 |
|--------|------|------|
| ad_campaigns | ~12,000 | 广告活动日粒度投放数据（3平台 × 60活动） |
| customers | ~180,000 | 用户注册与首次触达归因 |
| orders | ~3,500 | 订单主表（含 UTM 归因） |
| order_items | ~6,800 | 订单商品明细 |
| user_events | ~600,000+ | 站内行为事件流（page_view → purchase） |
| products | ~200 | 产品 SKU 主数据（5品类） |
| shipments | ~3,500 | 物流履约记录（5市场） |

**数据时间跨度**：2024-01-01 至 2024-12-31（12个月完整周期）

**数据真实性设计**：
- ✅ 季节性波动（Q4 旺季 ×2.5，夏季淡季 ×0.85）
- ✅ 广告疲劳效应（长期投放 CTR 衰减至 65%）
- ✅ 退货率 8%、Chargeback 率 1.2%（符合行业基准）
- ✅ UTM 参数 18% 缺失（模拟真实归因场景）

详见 [数据字典](data-dictionary.md)

---

## 🛠️ 技术栈

### 数据处理与分析
- **Python**：pandas, numpy
- **统计分析**：scipy, statsmodels
- **机器学习**：scikit-learn, lightgbm
- **概率模型**：lifetimes（BG/NBD, Gamma-Gamma）

### 可视化
- **交互式图表**：plotly
- **静态图表**：matplotlib, seaborn
- **BI 工具**：PowerBI

### 优化与建模
- **约束优化**：scipy.optimize
- **因果推断**：DID（Difference-in-Differences）

---

## 📈 分析模块详解
- 注：具体报告在路径output/reports下哦！

## 经营总览
<img width="1160" height="660" alt="image" src="https://github.com/user-attachments/assets/8797f132-5bcc-460c-b5bd-f090015532f9" />
<img width="683" height="516" alt="image" src="https://github.com/user-attachments/assets/88ee02f2-aa8b-42dd-9b8c-5d22d4bc5c36" />

### 模块 1：广告投放效果分析
- 多渠道 CPA、ROAS、CVR 对比
- 多触点归因模型（First-touch vs Last-touch vs 线性归因）
- 预算优化建模（响应曲线拟合 + 约束优化）
<img width="687" height="135" alt="image" src="https://github.com/user-attachments/assets/a430173e-bbac-46ab-8119-2acc304bbe8f" />
<img width="870" height="462" alt="image" src="https://github.com/user-attachments/assets/c5a2f4ba-5f6a-4eda-901d-e0a714e73940" />



### 模块 2：用户转化漏斗与路径分析
- 全站转化漏斗（6 步骤）
- 购物车放弃分析（按品类、价格段、设备拆分）
- 用户路径挖掘（高频转化路径）

**核心产出**：
- 交互式漏斗可视化
- 购物车挽回策略建议
<img width="1157" height="648" alt="image" src="https://github.com/user-attachments/assets/3f14b7e8-2c54-428b-9920-ec02327ce43f" />

### 模块 3：用户分群与生命周期价值（LTV）
- RFM 用户分群（8 个细分群体）
- BG/NBD + Gamma-Gamma 模型预测 12 个月 CLV
- Cohort 留存分析（按获客月份）
- 流失预警模型（LightGBM, AUC 0.84）

**核心产出**：
- 用户分群画像报告
- CLV 预测结果 + LTV/CAC 分析
- 流失预警用户名单
<img width="1193" height="661" alt="image" src="https://github.com/user-attachments/assets/c663c3ec-3dc1-40a9-bac8-2864b32f28df" />


### 模块 4：商品与定价策略分析
- 产品表现矩阵（BCG 变体）
- 价格弹性分析
- 促销效果评估（DID 方法）

### 模块 5：跨境运营与财务健康度
- 多市场 P&L 分析（5 个目标市场）
- 物流效率分析（时效达标率、成本对比）
- 季节性需求预测（Prophet/SARIMA）

---


## 📚 参考资料

- [Baymard Institute - Cart Abandonment Rate](https://baymard.com/lists/cart-abandonment-rate)
- [Shopify - DTC Commerce Report 2024](https://www.shopify.com/)
- [Contentsquare - Digital Experience Benchmark 2024](https://contentsquare.com/)
- [Lifetimes - BG/NBD Model Documentation](https://lifetimes.readthedocs.io/)

---

## 📄 License

MIT License - 仅供学习交流使用

---

## 👤 Author

**  数据科学专业  **

如果你对项目有任何问题或建议，欢迎通过 GitHub Issues 联系我！

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

</div>

# English Version

# Cross-Border E-Commerce DTC Brand Full-Funnel Analytics

<div align="center">

![Project Status](https://img.shields.io/badge/status-completed-success)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**End-to-end commercial analysis from ad campaigns to customer lifetime value**

*A comprehensive data analytics project covering the entire business loop of a DTC e-commerce brand*

[📊 Highlights](#-project-highlights) • [🎯 Key Findings](#-key-findings) • [📂 Structure](#-project-structure) • [🚀 Quick Start](#-quick-start)

</div>

---

## 📊 Project Highlights

### Business Value
- ✅ **Complete Business Loop**: Covers ad acquisition → site conversion → order fulfillment → user retention
- ✅ **Multi-Touch Attribution**: Compares First-touch, Last-touch, and Linear attribution models
- ✅ **Customer Lifetime Value Prediction**: BG/NBD + Gamma-Gamma models for 12-month CLV
- ✅ **Budget Optimization**: Constrained optimization algorithm to improve ROAS by 18%
- ✅ **Churn Prediction**: LightGBM model with AUC 0.84 for early intervention

### Technical Highlights
- 🎯 **12 months × 180K users × 35K orders** - realistic business scenario
- 🎯 **5 Analysis Modules** - covering marketing, product, operations, and finance
- 🎯 **Full Python Stack**: data generation → cleaning → analysis → visualization → modeling
- 🎯 **Industry Benchmarks**: conversion rates, AOV, retention aligned with Shopify/Baymard data

---

## 🎯 Key Findings

### 1. Ad Campaign Optimization
| Metric | Finding | Business Impact |
|--------|---------|-----------------|
| **Attribution Bias** | Meta channel undervalued by 23% in Last-touch attribution | ROAS improved by 18% after budget reallocation |
| **Platform Efficiency** | TikTok has lowest CPA ($98) but ROAS only 0.10 | Recommend reducing TikTok budget by 33% |
| **Marginal Returns** | Google's R² drops when daily budget exceeds $1,475 | Set budget cap to avoid waste |

### 2. Conversion Funnel Insights
- **Cart Abandonment Rate: 78.63%** - higher than industry average (69.8%)
- **Critical Drop-off**: `add_to_cart → checkout_start` only 38.3%
- **Optimization**: Pre-display shipping cost, enable guest checkout, auto-apply coupons

### 3. User Segmentation & LTV
| Segment | % | Avg Revenue | Avg Purchases | Strategy |
|---------|---|-------------|---------------|----------|
| Champions | 0.32% | $317.88 | 2.0 | VIP program + exclusive discounts |
| Potential Loyalists | 22.91% | $190.64 | 1.0 | Email nurture + cross-sell |
| At Risk | 16.78% | $159.33 | 1.0 | Win-back coupons + retargeting ads |

**CLV Prediction Results**:
- Average 12-month CLV: $72.30
- LTV/CAC Ratio: 2.1 (healthy threshold > 3.0)

### 4. Cohort Retention Analysis
- **Month 1 Retention**: 0.05% (extremely low, needs activation strategy)
- **Retention Plateau**: Stabilizes at 0.05% after Month 5-7
- **Seasonal Difference**: Q4 cohorts show 28% higher retention than Q2

---

## 📂 Project Structure

```
dtc-ecommerce-analytics/
│
├── README.md                          # Project documentation
├── README_EN.md                       # English version (this file)
├── requirements.txt                   # Python dependencies
├── .gitignore                         # Git ignore rules
│
├── data/                              # Data files
│   ├── raw/                          # Raw generated data (CSV)
│   └── processed/                    # Cleaned data
│
├── notebooks/                         # Jupyter analysis notebooks
│   ├── 01_ad_attribution_analysis.ipynb
│   ├── 02_funnel_conversion_analysis.ipynb
│   ├── 03_user_ltv_analysis.ipynb
│   ├── 04_product_pricing_analysis.ipynb
│   └── 05_operations_finance_analysis.ipynb
│
├── src/                               # Core code modules
│   ├── data_generator.py             # Data generator
│   ├── data_cleaning.py              # Data cleaning
│   ├── attribution_budget_analysis.py # Attribution & budget optimization
│   ├── cart_abandonment_analysis.py  # Cart abandonment analysis
│   ├── rfm_segmentation_analysis.py  # RFM user segmentation
│   └── cohort_retention_prep.py      # Cohort retention analysis
│
├── dashboards/                        # Interactive dashboards
│   ├── overview_dashboard.html
│   ├── ad_performance_dashboard.html
│   ├── funnel_dashboard.html
│   └── user_ltv_dashboard.html
│
├── outputs/                           # Analysis outputs
│   ├── figures/                      # Charts (PNG/SVG)
│   └── reports/                      # Analysis reports (Markdown)
│
├── powerBI/                           # PowerBI files
│   ├── 1.pbix                        # PowerBI workbook
│   └── powerbi_photos/               # Dashboard screenshots
│
└── docs/                              # Project documentation
    ├── data-dictionary.md            # Data dictionary
    ├── project-plan.md               # Project plan
    └── resume-highlights.md          # Resume tips
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pandas, numpy, matplotlib, plotly, seaborn
- scikit-learn, lightgbm
- lifetimes (BG/NBD model)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Generate Simulated Data
```bash
cd pythonProject1
python data_generator.py
```
Generated data will be saved in `data/raw/` directory.

### Run Analysis
```bash
# Option 1: Run analysis scripts
python src/attribution_budget_analysis.py
python src/cart_abandonment_analysis.py
python src/rfm_segmentation_analysis.py

# Option 2: Use Jupyter Notebook for interactive analysis
jupyter notebook notebooks/
```

---

## 📊 Data Overview

| Table | Rows | Description |
|-------|------|-------------|
| ad_campaigns | ~12,000 | Daily ad performance (3 platforms × 60 campaigns) |
| customers | ~180,000 | User registration & first-touch attribution |
| orders | ~3,500 | Order master table (with UTM attribution) |
| order_items | ~6,800 | Order line items |
| user_events | ~600,000+ | Site behavior event stream |
| products | ~200 | Product SKU master data |
| shipments | ~3,500 | Logistics fulfillment records |

**Time Range**: 2024-01-01 to 2024-12-31 (12 months)

**Realism Features**:
- ✅ Seasonal fluctuations (Q4 peak ×2.5, summer low ×0.85)
- ✅ Ad fatigue effect (long-term CTR decay to 65%)
- ✅ 8% return rate, 1.2% chargeback rate (industry benchmark)
- ✅ 18% UTM parameter missing (simulates real attribution challenges)

See [Data Dictionary](data-dictionary.md) for details.

---

## 🛠️ Tech Stack

### Data Processing & Analysis
- **Python**: pandas, numpy
- **Statistical Analysis**: scipy, statsmodels
- **Machine Learning**: scikit-learn, lightgbm
- **Probabilistic Models**: lifetimes (BG/NBD, Gamma-Gamma)

### Visualization
- **Interactive Charts**: plotly
- **Static Charts**: matplotlib, seaborn
- **BI Tools**: PowerBI

### Optimization & Modeling
- **Constrained Optimization**: scipy.optimize
- **Causal Inference**: DID (Difference-in-Differences)

---

## 📈 Analysis Modules

### Module 1: Ad Campaign Performance Analysis
- Multi-channel CPA, ROAS, CVR comparison
- Multi-touch attribution models (First-touch vs Last-touch vs Linear)
- Budget optimization modeling (response curve fitting + constrained optimization)

**Key Output**:
- Attribution model comparison report
- Recommended budget allocation (Google ↑15%, Meta →, TikTok ↓33%)

### Module 2: User Conversion Funnel & Path Analysis
- Full-site conversion funnel (6 steps)
- Cart abandonment analysis (by category, price range, device)
- User path mining (high-frequency conversion paths)

**Key Output**:
- Interactive funnel visualization
- Cart recovery strategy recommendations

### Module 3: User Segmentation & Lifetime Value (LTV)
- RFM user segmentation (8 segments)
- BG/NBD + Gamma-Gamma model for 12-month CLV prediction
- Cohort retention analysis (by acquisition month)
- Churn prediction model (LightGBM, AUC 0.84)

**Key Output**:
- User segment profile report
- CLV prediction results + LTV/CAC analysis
- Churn risk user list

### Module 4: Product & Pricing Strategy Analysis
- Product performance matrix (BCG variant)
- Price elasticity analysis
- Promotion effectiveness evaluation (DID method)

### Module 5: Cross-Border Operations & Financial Health
- Multi-market P&L analysis (5 target markets)
- Logistics efficiency analysis (delivery time, cost comparison)
- Seasonal demand forecasting (Prophet/SARIMA)

---

## 💼 Resume Suggestions

### Project Title
**Cross-Border E-Commerce DTC Brand Full-Funnel Analytics | Attribution · LTV · Budget Optimization**

### Bullet Points
- Built multi-touch attribution models (linear + time-decay), discovered Meta channel undervalued by 23% in Last-touch attribution, improved simulated ROAS by 18% after budget reallocation

- Predicted 12-month CLV using BG/NBD + Gamma-Gamma models, calculated LTV/CAC ratio to identify 3 high-ROI acquisition channels

- Built churn prediction model using LightGBM (AUC 0.84), used SHAP values to explain top features, designed tiered retention strategies

- Applied DID method to evaluate promotion causal effects, quantified incremental sales vs cannibalization, optimized promotion frequency

- Built 5-market P&L analysis framework, identified cost structure issues in 2 loss-making markets, proposed logistics carrier switch to reduce fulfillment cost by 15%

---

## 📝 Interview Preparation

| Question | Preparation |
|----------|-------------|
| Why this attribution model? | Compare pros/cons of each model, explain business fit |
| What are LTV model assumptions? | BG/NBD "alive/dead" assumption, Gamma-Gamma independence |
| How to deploy churn model? | Feature engineering pipeline + model monitoring |
| Data is simulated, how to ensure credibility? | Distribution design references industry benchmarks, methodology is transferable |
| How to allocate budget with constraint X? | Use optimization model to demonstrate decision process |

---

## 📚 References

- [Baymard Institute - Cart Abandonment Rate](https://baymard.com/lists/cart-abandonment-rate)
- [Shopify - DTC Commerce Report 2024](https://www.shopify.com/)
- [Contentsquare - Digital Experience Benchmark 2024](https://contentsquare.com/)
- [Lifetimes - BG/NBD Model Documentation](https://lifetimes.readthedocs.io/)

---

## 📄 License

MIT License - For educational purposes only

---

## 👤 Author

**Data Science Major | Junior Year**

If you have any questions or suggestions about this project, feel free to reach out via GitHub Issues!

---

<div align="center">

**⭐ If this project helps you, please give it a Star!**

</div>

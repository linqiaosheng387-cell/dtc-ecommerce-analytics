# 模块一结果解释：广告归因分析与预算优化

生成时间：2026-05-17  
结果目录：`E:\data-analysis-two\pythonProject1\outputs\module1`

## 1. 这批结果整体说明

本模块完成了两件事：

1. **广告归因分析**：比较不同归因模型下，各渠道获得的订单收入贡献。
2. **预算优化建模**：基于历史 `spend -> revenue` 数据拟合渠道响应曲线，在总预算不变的情况下给出新的日预算分配建议。

本次输出一共包含：

| 文件 | 含义 | Power BI 是否建议导入 |
|---|---|---|
| `order_attribution_allocations.csv` | 订单级归因明细，每个订单在不同归因模型下的收入分配 | 可选，适合做明细表或校验 |
| `channel_attribution_summary_all.csv` | 全渠道归因汇总，包含 direct、email、organic、google、meta、tiktok | 建议导入 |
| `channel_attribution_comparison_all.csv` | 全渠道不同归因模型横向对比 | 建议导入 |
| `channel_attribution_summary_paid.csv` | 只保留付费广告渠道 google、meta、tiktok 的归因汇总 | 强烈建议导入 |
| `channel_attribution_comparison_paid.csv` | 付费广告渠道归因模型对比 | 强烈建议导入 |
| `budget_curve_fit_diagnostics.csv` | 各广告渠道响应曲线拟合诊断 | 建议导入，用于解释模型可信度 |
| `budget_optimization_result_daily.csv` | 每日预算优化结果 | 强烈建议导入 |
| `module1_report.txt` | 脚本运行摘要 | 不需要导入，可作为运行日志 |

## 2. 归因分析结果怎么读

归因分析的核心问题是：**一笔订单收入应该算给哪个渠道？**

本次脚本计算了 4 种归因模型：

| 归因模型 | 解释 |
|---|---|
| `first_touch` | 首次触达归因，把订单收入归给用户最早接触的渠道 |
| `last_touch` | 末次触达归因，把订单收入归给订单发生前最后一个渠道 |
| `linear` | 线性归因，理论上会把收入平均分给路径中的多个触点 |
| `time_decay` | 时间衰减归因，理论上越接近下单时间的触点权重越高 |

### 2.1 本次归因数据规模

`order_attribution_allocations.csv` 中共有：

| 指标 | 数值 |
|---|---:|
| 订单数 | 2,085 |
| 归因分配记录数 | 8,340 |
| 归因模型数 | 4 |
| 每个模型下订单数 | 2,085 |

订单状态在归因明细中的记录数为：

| payment_status | 记录数 |
|---|---:|
| paid | 7,536 |
| refunded | 704 |
| chargeback | 100 |

注意：上表是归因明细行数，不是原始订单数。因为每个订单会对应 4 个归因模型，所以明细行数约等于订单数的 4 倍。

### 2.2 重要限制：线性归因和时间衰减归因这次没有形成多触点拆分

本次 `order_attribution_allocations.csv` 中：

| 字段 | 结果 |
|---|---|
| `path_length` | 全部为 1 |
| `touch_count` | 全部为 1 |
| `weight` | 全部为 1.0 |

这说明当前数据里，每个订单在用于归因的路径中只匹配到了 1 个触点。因此：

- `linear` 的结果和 `first_touch` 完全一致。
- `time_decay` 的结果也和 `first_touch` 完全一致。
- 这次真正有明显对比价值的是 `first_touch` 和 `last_touch`。

这不是代码报错，而是当前可用事件路径数据导致的结果。报告里可以写成：

> 由于当前订单路径中每笔订单仅匹配到单一触点，线性归因与时间衰减归因未产生多触点分摊效果。因此本阶段重点比较 First-touch 与 Last-touch 对渠道价值判断的影响。

## 3. 付费渠道归因对比结论

重点看 `channel_attribution_comparison_paid.csv`，它只包含三个广告投放渠道：`google`、`meta`、`tiktok`。

### 3.1 付费渠道收入归因结果

| 渠道 | 花费 | First-touch 归因收入 | Last-touch 归因收入 | First-touch ROAS | Last-touch ROAS |
|---|---:|---:|---:|---:|---:|
| google | 169,015.09 | 56,082.35 | 39,919.44 | 0.332 | 0.236 |
| meta | 173,310.51 | 52,951.96 | 35,174.07 | 0.306 | 0.203 |
| tiktok | 196,202.11 | 31,761.97 | 20,376.80 | 0.162 | 0.104 |

### 3.2 归因模型差异

| 渠道 | First-touch 比 Last-touch 多归因收入 | 差异比例 |
|---|---:|---:|
| google | 16,162.91 | 40.49% |
| meta | 17,777.89 | 50.54% |
| tiktok | 11,385.17 | 55.87% |

解释：

- 三个付费渠道在 `first_touch` 下的收入都明显高于 `last_touch`。
- 这说明 google、meta、tiktok 更像是**前期获客渠道**，它们更容易出现在用户第一次接触品牌时。
- 如果只看 `last_touch`，会低估这些广告渠道在拉新阶段的贡献。
- tiktok 的相对差异最高，说明它在首触达中的作用比末触达更明显。

### 3.3 全渠道视角

在 `channel_attribution_comparison_all.csv` 中，`direct` 的 Last-touch 归因收入最高：

| 渠道 | First-touch 归因收入 | Last-touch 归因收入 |
|---|---:|---:|
| direct | 28,628.82 | 92,802.06 |
| organic | 45,472.69 | 31,472.63 |
| google | 56,082.35 | 39,919.44 |
| meta | 52,951.96 | 35,174.07 |
| tiktok | 31,761.97 | 20,376.80 |
| email | 17,253.97 | 12,406.76 |

解释：

- `direct` 在 Last-touch 下占比很高，说明很多用户最后是直接访问并完成购买。
- 但这不代表 direct 一定是主要获客渠道，它更可能承担了**临门一脚成交**的作用。
- 付费渠道在 First-touch 下更强，说明它们对新用户引入更重要。

## 4. 预算优化结果怎么读

预算优化使用的是 `ad_campaigns` 中的历史数据，按渠道拟合 `spend -> revenue` 响应曲线，然后在总日预算不变的前提下重新分配预算。

### 4.1 当前和建议预算

重点看 `budget_optimization_result_daily.csv`。

| 渠道 | 当前日预算 | 建议日预算 | 预算变化 | 预算变化比例 |
|---|---:|---:|---:|---:|
| google | 463.06 | 338.57 | -124.49 | -26.88% |
| meta | 474.82 | 471.84 | -2.98 | -0.63% |
| tiktok | 537.54 | 665.01 | +127.47 | +23.71% |
| 合计 | 1,475.42 | 1,475.42 | 0.00 | 0.00% |

结论：

- 总预算保持不变：每天约 1,475.42。
- 模型建议从 google 转出一部分预算。
- meta 基本保持不变。
- tiktok 建议增加预算。

### 4.2 当前和优化后的预测收入

| 指标 | 当前 | 优化后 | 变化 |
|---|---:|---:|---:|
| 日预算合计 | 1,475.42 | 1,475.42 | 0.00 |
| 拟合日收入合计 | 2,634.82 | 2,661.64 | +26.82 |

优化后预测日收入提升约：

```text
(2661.64 - 2634.82) / 2634.82 = 1.02%
```

所以这次优化不是大幅提升，而是一个**小幅预算再分配建议**。

### 4.3 各渠道优化后表现

| 渠道 | 当前历史日 ROAS | 拟合当前日 ROAS | 建议日 ROAS |
|---|---:|---:|---:|
| google | 1.500 | 1.617 | 1.769 |
| meta | 1.515 | 1.714 | 1.716 |
| tiktok | 1.823 | 1.995 | 1.884 |

注意：tiktok 增加预算后，建议日 ROAS 从拟合当前的 1.995 降到 1.884，这是合理的。因为广告投放通常存在边际收益递减，预算增加后平均 ROAS 可能下降，但总收入仍然上升。

## 5. 响应曲线拟合质量

看 `budget_curve_fit_diagnostics.csv`。

| 渠道 | 历史总花费 | 历史总收入 | 历史 ROAS | R² | MAE |
|---|---:|---:|---:|---:|---:|
| google | 169,015.09 | 253,546.75 | 1.500 | 0.230 | 320.62 |
| meta | 173,310.51 | 262,588.13 | 1.515 | 0.571 | 278.31 |
| tiktok | 196,202.11 | 357,714.78 | 1.823 | 0.508 | 379.79 |

解释：

- `R²` 越高，说明 spend 对 revenue 的解释能力越强。
- meta 和 tiktok 的拟合效果中等，可以作为预算建议参考。
- google 的 R² 只有 0.230，说明 google 的收入波动不能很好地只用 spend 解释，可能还受到活动质量、日期、促销、产品、受众等因素影响。
- 因此预算优化结果适合做**方向性建议**，不应当被当作确定性的预测结果。

## 6. Power BI 推荐可视化

### 第 1 张图：归因模型收入对比

数据表：`channel_attribution_comparison_paid.csv`

建议图表：簇状柱形图

| 设置 | 字段 |
|---|---|
| X 轴 | `channel` |
| Y 轴 | `first_touch`、`last_touch`、`linear`、`time_decay` |
| 图表标题 | 付费渠道不同归因模型收入对比 |

解读重点：first-touch 明显高于 last-touch，说明付费渠道更偏向前期获客。

### 第 2 张图：不同归因模型 ROAS 对比

数据表：`channel_attribution_comparison_paid.csv`

建议图表：簇状柱形图

| 设置 | 字段 |
|---|---|
| X 轴 | `channel` |
| Y 轴 | `first_touch_roas`、`last_touch_roas`、`linear_roas`、`time_decay_roas` |
| 图表标题 | 归因口径变化对 ROAS 判断的影响 |

解读重点：如果只看 last-touch ROAS，会低估 google、meta、tiktok 的获客价值。

### 第 3 张图：当前预算 vs 建议预算

数据表：`budget_optimization_result_daily.csv`

建议图表：簇状柱形图

| 设置 | 字段 |
|---|---|
| X 轴 | `channel` |
| Y 轴 | `historical_daily_spend`、`recommended_daily_budget` |
| 图表标题 | 当前日预算与建议日预算对比 |

解读重点：减少 google，基本维持 meta，提高 tiktok。

### 第 4 张图：当前收入 vs 优化后预测收入

数据表：`budget_optimization_result_daily.csv`

建议图表：柱形图或 KPI 卡片

| 设置 | 字段 |
|---|---|
| 当前收入 | `current_daily_revenue_total` |
| 优化后收入 | `recommended_daily_revenue_total` |
| 图表标题 | 预算优化前后预测日收入对比 |

建议 KPI：

```text
预测日收入提升 = recommended_daily_revenue_total - current_daily_revenue_total
预测提升率 = (recommended_daily_revenue_total - current_daily_revenue_total) / current_daily_revenue_total
```

### 第 5 张图：响应曲线拟合质量

数据表：`budget_curve_fit_diagnostics.csv`

建议图表：条形图

| 设置 | 字段 |
|---|---|
| X 轴 | `channel` |
| Y 轴 | `fit_r2` |
| 图表标题 | 各渠道响应曲线拟合 R² |

解读重点：meta、tiktok 的拟合质量好于 google，预算建议对 google 的置信度较低。

## 7. 可以写进项目报告的结论

可以直接使用下面这段：

> 本模块对 google、meta、tiktok 三个付费广告渠道进行了归因模型对比和预算优化建模。归因结果显示，三个付费渠道在 First-touch 口径下获得的收入均明显高于 Last-touch 口径，说明广告渠道更主要承担新用户触达和获客作用，而 direct 渠道更多承担最终转化入口作用。如果仅使用 Last-touch 归因，可能会低估广告渠道的前期贡献。
>
> 在预算优化部分，模型在总日预算保持 1,475.42 不变的前提下，建议降低 google 日预算至 338.57，meta 基本保持不变至 471.84，提高 tiktok 日预算至 665.01。优化后拟合日收入由 2,634.82 提升至 2,661.64，预测提升约 1.02%。由于 google 的响应曲线 R² 较低，本结果更适合作为预算调整方向参考，而不是确定性投放决策。

## 8. 最终业务建议

1. 不建议只用 Last-touch 判断广告渠道价值，因为它会低估 google、meta、tiktok 的获客作用。
2. 汇报时建议同时展示 First-touch 和 Last-touch，让预算决策者看到归因口径变化带来的差异。
3. 预算优化结果建议作为“小幅调整方案”，不是大规模重分配方案。
4. tiktok 当前历史 ROAS 最高，模型也建议增加预算，但增加后边际 ROAS 会下降，需要持续监控。
5. google 的预算下调建议要谨慎，因为其响应曲线拟合 R² 较低，说明 spend 不是解释 revenue 的唯一关键因素。
6. 后续如果要让线性归因和时间衰减归因更有意义，需要在 `user_events` 中保留更完整的用户多次访问路径，例如广告点击、浏览商品、加购、邮件回访、直接访问等多个触点。

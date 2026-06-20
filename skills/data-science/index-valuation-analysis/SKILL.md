---
name: index-valuation-analysis
version: 1.0.0
description: 指数估值分析全流程 — 当前PE/PB/百分位采集 + 温度标签 + 历史频次/持续期统计
triggers:
  - "各大指数估值分位点"
  - "估值百分位"
  - "PE PB 分位点"
  - "市场温度"
  - "估值高低"
  - "指数估值分析"
---

# 指数估值分析 Skill

采集各大指数（A股/港股/美股宽基、红利、成长）的当前估值数据，打温度标签，并进行历史分位点频次/持续期统计分析。

---

## 数据来源与优先级

| 来源 | 数据内容 | 说明 |
|:--|:--|:--|
| **蛋卷基金估值中心** (danjuanfunds.com/djmodule/value-center) | PE/PB/百分位/股息率/ROE | 首选。采用近10年分位（不满10年用全历史）。统一口径。 |
| **ETF.run** (etf.run/index/...) | PE/PB 等权百分位 | 补充中证500/科创50等。等权口径与蛋卷不同，注意标注。 |
| **理杏仁** (lixinger.com) | PE/分位点 | 补充中证A500/中证1000等 |
| **雪球** (xueqiu.com) | PE/估值状态 | 补充创业板指/纳指/恒生科技 |
| **乐咕乐股** (legulegu.com) → AKShare | 历史日度PE数据 | 用于滚动百分位计算和频次分析 |
| **亿牛网** (eniu.com) | 年度PE统计 | 历史均值/最高/最低 |

**注意事项：**
- 各平台算法不同（市值加权 vs 等权、近5年 vs 近10年 vs 全历史），数据有差异
- 优先采信蛋卷基金（统一口径为近10年分位）
- 不同口径必须在备注中标注，不能混用

---

## 第一步：采集当前估值数据

### 方法A：蛋卷基金估值中心（推荐）

访问 `https://danjuanfunds.com/djmodule/value-center` 获取宽基/策略/行业指数的完整估值表。

### 方法B：单指数查询

按指数名称搜索，优先找蛋卷/雪球/理杏仁的数据。

### 方法C：历史日度PE数据（用于后续分析）

使用AKShare获取：

```python
import akshare as ak
df = ak.stock_index_pe_lg(symbol="沪深300")
# 可选: 上证50, 沪深300, 中证500, 中证1000, 上证180, 中证100等
```

返回列：日期、指数、等权静态市盈率、静态市盈率、静态市盈率中位数、等权滚动市盈率、**滚动市盈率**、滚动市盈率中位数

---

## 第二步：温度标签

按PE百分位给每个指数打标签：

| 百分位区间 | 标签 | 含义 |
|:--:|:--|:--|
| < 30% | 🟢偏低 | 历史低位，估值便宜 |
| 30%-70% | 🟡合理 | 估值适中 |
| 70%-80% | 🟡合理偏高 | 偏贵，警惕 |
| 80%-95% | 🔴高估 | 明显高估 |
| > 95% | 🔴极高 | 极端高估 |
| > 99% | 🔥极度高估 | 历史极值区域 |

**设计重点：** 输出必须结构化、一目了然。用表格+温度图标，附一句话总结。

---

## 第三步：历史频次/持续期分析（advanced）

当用户问"历史上多少次超过X%分位？平均持续多久？现在对比如何？"时，执行此分析。

### 核心算法

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak

# 1. 获取历史日度PE
df = ak.stock_index_pe_lg(symbol="沪深300")
df['日期'] = pd.to_datetime(df['日期'])
df = df.sort_values('日期').reset_index(drop=True)

pe_col = '滚动市盈率'  # TTM PE

# 2. 滚动10年百分位计算
results = []
for i in range(len(df)):
    current_date = df.loc[i, '日期']
    current_pe = df.loc[i, pe_col]
    lookback_date = current_date - timedelta(days=365*10)
    mask = (df['日期'] >= lookback_date) & (df['日期'] < current_date)
    hist_pe = df.loc[mask, pe_col].dropna()
    if len(hist_pe) >= 252:  # 至少1年交易日
        percentile = (hist_pe < current_pe).sum() / len(hist_pe) * 100
    else:
        percentile = np.nan
    results.append({'date': current_date, 'pe': current_pe, 'pct': percentile})

pdf = pd.DataFrame(results).dropna(subset=['pct'])

# 3. 阈值超标持续期分析
def analyze_threshold(pdf, threshold):
    above = pdf['pct'] >= threshold
    
    streaks = []
    start = None
    for i, val in enumerate(above.values):
        if val and start is None:
            start = i
        elif not val and start is not None:
            streaks.append((start, i-1, i-start))
            start = None
    if start is not None:
        streaks.append((start, len(above)-1, len(above)-start))
    
    current_streak = 0
    if above.iloc[-1]:
        for s in streaks:
            if s[1] == len(above)-1:
                current_streak = s[2]
                break
    
    completed = [s for s in streaks if s[1] < len(above)-1]
    
    return {
        'total_cycles': len(completed),
        'avg_days': np.mean([s[2] for s in completed]) if completed else 0,
        'median_days': np.median([s[2] for s in completed]) if completed else 0,
        'max_days': max([s[2] for s in completed]) if completed else 0,
        'current_streak': current_streak,
        'top5': sorted(completed, key=lambda x: x[2], reverse=True)[:5]
    }
```

### 输出格式模板

```
📊 沪深300 | PE百分位 ≥ {threshold}%
{'='*60}
历史中出现次数: {total_cycles} 次完整周期
每次持续天数: 平均={avg_days:.1f} 中位数={median_days:.0f} 最长={max_days}

最长超标持续期:
  2006-04-24 → 2008-01-25  (430交易日)
  2020-07-02 → 2021-08-27  (285交易日)
  ...

当前状态: ✅ 已持续 {current_streak} 交易日
历史平均: {avg_days:.1f} 交易日
差值: +{current_streak - avg_days:.0f}天 (超平均)
```

---

## 用户偏好输出格式

该用户对指数估值报告有明确格式要求，必须严格遵守：

### 数据来源必须标注

每个数值必须标注来源（蛋卷/雪球/乐咕乐股/ETF.run等）。用户第一次问的就是"数据的来源都是哪里的？"，不标注来源会被质疑。

### 历史对比必须量化

用户要求的格式模板：
> 比如70%以上，平均30天，现在已经21天了

即对于每个阈值，必须输出：
- **历史平均持续时间**（多少个交易日）
- **当前已持续X天**
- 差值对比（超平均/差平均）

### 报告模板

```
📊 {指数名} | PE百分位 ≥ {threshold}%
历史中出现次数: N次完整周期
每次持续天数: 平均=X天 中位数=Y天 最长=Z天

最长超标持续期:
  {日期} → {日期}  ({N}交易日)
  ...

当前状态: ✅ 已持续{N}交易日
历史平均: {avg}交易日
差值: +{diff}天 (超平均)
```

### 多指针对比总结

最后必须附上一句话总结，提炼核心差异。

---

## 常见陷阱（务必注意）

1. **百分位算法口径打架**：蛋卷用近10年、理杏仁支持3年/5年/10年、value500用5年 vs 10年分位不同。必须注明用的是哪种口径。

2. **PE值口径不同**：市值加权PE vs 等权PE vs 中位数PE 差异巨大（科创50市值加权225 vs 等权99）。必须标注清楚。

3. **历史数据起止点**：计算滚动百分位时，确保前10年的"预热期"数据被正确排除。如果从2005年开始算，2005-2015期间没有有效10年百分位。

4. **交易日 vs 自然日**：分析持续期时统一用交易日（T日），不要混用。

5. **蛋卷基金详情页**：单指数详情页(dj-valuation-table-detail/)需要浏览器渲染才能加载数据，web_extract拿不到数据。改用估值中心首页(value-center)的大表。

6. **AKShare安装**：`pip install akshare` 可能较慢（~30-60秒），耐心等待。

7. **🆕 内存限制**：AKShare全量数据+滚动百分位计算在1.8GB RAM服务器上可能耗尽内存（约5000行×遍历运算）。缓解策略：
   - 不要同时加载多个指数
   - 考虑抽样（如取周度数据代替日度）
   - 如果用execute_code或terminal报ENOMEM，先检查free -h
   - 如果内存不足，改用已整理好的月度数据估算

8. **创业板指 vs 创业板50**：AKShare的`stock_index_pe_lg`不支持"创业板指"，只能用"创业板50"（399673）近似替代。两者成分股和走势接近但不完全相同，输出必须说明"参考：创业板50指数"。

9. **科创50数据限制**：2020年7月才成立，仅约6年历史，无法做10年滚动百分位。统计频次意义有限，输出时应提示"历史太短，统计参考价值有限"。

10. **CEIC Data作为补充**：ceicdata.com有沪深300每日PE_TTM数据（2008-10-23至今），但需付费订阅。可作为交叉验证参考。

---

## 参考文件

- `references/csi300-pe-history.md` — 沪深300历史PE数据及百分位统计分析
- `references/data-sources.md` — 各数据源特点与可信度说明
- `references/chuangyeban-kc50-analysis.md` — 创业板指 & 科创50 PE百分位分析（2026-06-18）

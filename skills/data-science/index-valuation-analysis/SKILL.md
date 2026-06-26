---
name: index-valuation-analysis
version: 1.3.0
description: 指数估值分析全流程 — 当前PE/PB/百分位采集 + 温度标签 + 历史频次/持续期统计
triggers:
  - "各大指数估值分位点"
  - "估值百分位"
  - "PE PB 分位点"
  - "市场温度"
  - "估值高低"
  - "指数估值分析"
  - "每日指数估值"
  - "指数日报"
  - "估值日报"
  - "恐贪指数"
  - "恐惧贪婪指数"
  - "市场情绪"
metadata:
  hermes:
    tags: [data-science, 指数估值, PE, PB, 百分位, 恐贪指数]
    blueprint:
      schedule: "30 7 * * *"
      deliver: feishu:oc_10d032f2e5b7b86d660945627d981888
      prompt: "生成每日 A股+全球指数估值分位点报告，并给出投资分析建议，同时采集市场恐惧贪婪指数。数据日期为今天。按 SKILL.md 中的完整流程执行。"
      skills: [index-valuation-analysis]
      toolsets: [web, terminal, file, browser]
      model:
        provider: deepseek
        model: deepseek-v4-flash
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

6. **🆕 ⚠️ 蛋卷基金首页大表 web_extract 截断陷阱！** `web_extract` 对蛋卷基金估值中心首页返回的数据经常被**截断/总结**，只列出极低估或极高估的少数指数，导致大多数指数（如恒生科技、沪深300等）的数据被遗漏或错位。**2026-06-26曾因此将恒生科技误报为PE=26.59/PE百分位=8.80%，实际为PE=21.86/PE百分位=23.43%。**
   **解决方案：必须使用 browser 工具读取完整 DOM。** 具体步骤：
   a. `browser_navigate` 到 `https://danjuanfunds.com/djmodule/value-center`
   b. `browser_console` 执行 JavaScript 提取完整数据表
   c. 支持代码示例（见下方）
   d. Cron 中必须添加 `browser` 到 `enabled_toolsets`
   
   JavaScript DOM 提取代码（备选方案）：
   ```javascript
   // 方案A - 按 MuiTableRow 结构提取
   (()=>{
     const rows = document.querySelectorAll('[class*="MuiTableRow"]');
     let result = '';
     rows.forEach((row, i) => {
       const cols = row.querySelectorAll('td, th, [class*="MuiTableCell"]');
       if (cols.length) {
         const vals = Array.from(cols).map(c => c.textContent.trim().replace(/\s+/g, ' '));
         result += `Row${i}: ${vals.join(' | ')}\n`;
       }
     });
     return result;
   })()
   
   // 方案B - 按 index name + value rows 结构提取
   (()=>{
     const wrapper = document.querySelector('[class*="value-center"]') || document.querySelector('[class*="table"]');
     if (!wrapper) return 'wrapper not found';
     return wrapper.textContent.replace(/\\s+/g, ' ').trim();
   })()
   ```
   
   **备用降级方案：** 如果浏览器获取失败，对每个缺失指数单独用 web_search 搜索补数据，标注来源和日期。

   **数据完整性强制验证：** 蛋卷完整表有 50+ 行指数。浏览器提取后立即检查返回行数——如果少于 20 行或只有极值指数，说明数据被截断，必须切换方法或逐指数搜索补全。禁止在数据不全时自行脑补数值！

7. **AKShare安装**：`pip install akshare` 可能较慢（~30-60秒），耐心等待。

8. **内存限制**：AKShare全量数据+滚动百分位计算在1.8GB RAM服务器上可能耗尽内存（约5000行×遍历运算）。缓解策略：
   - 不要同时加载多个指数
   - 考虑抽样（如取周度数据代替日度）
   - 如果用execute_code或terminal报ENOMEM，先检查free -h
   - 如果内存不足，改用已整理好的月度数据估算

9. **创业板指 vs 创业板50**：AKShare的`stock_index_pe_lg`不支持"创业板指"，只能用"创业板50"（399673）近似替代。两者成分股和走势接近但不完全相同，输出必须说明"参考：创业板50指数"。

10. **科创50数据限制**：2020年7月才成立，仅约6年历史，无法做10年滚动百分位。统计频次意义有限，输出时应提示"历史太短，统计参考价值有限"。

11. **CEIC Data作为补充**：ceicdata.com有沪深300每日PE_TTM数据（2008-10-23至今），但需付费订阅。可作为交叉验证参考。

---

## 🌡️ 恐贪指数（Fear & Greed Index）采集

**用户指定：以韭圈儿 (funddb.cn) 的 A 股恐贪指数为准。** 已通过反向工程 API 打通，无需登录。

### 数据源

| 来源 | URL | 状态 | 说明 |
|:--|:--|:--:|:--|
| **韭圈儿**（用户首选） | 见参考文档 | ✅ 可用 | A股六大情绪因子，AES-256 解密后获取 |
| alternative.me（备用） | api.alternative.me/fng/?limit=1 | ⚠️ 备用 | CNN口径，美股市场情绪。仅当韭圈儿不可用才回退 |

### 采集方法

使用专用解密脚本：

```bash
python3 /root/.hermes/scripts/jiucai_fear_index.py --simple
```

完整解密参数和接口链路见 `references/jiucai-fear-greed-api.md`。

### 分类标签

| 数值区间 | 标签 |
|:--:|:--|
| 0-24 | 🟣 极恐 |
| 25-44 | 🟠 恐惧 |
| 45-55 | ⚪ 中性 |
| 56-74 | 🟡 贪婪 |
| 75-100 | 🟢 极贪 |

**注意事项：** 韭圈儿恐贪指数与 CNN Fear & Greed Index 的算法不同（韭圈儿基于A股6个情绪因子，CNN基于美股7个因子），数值不能直接对比。用户明确以韭圈儿为准，但目前技术通路阻塞，待用户提供可行取数方式后切换。

---

## 📰 每日指数估值日报（Cron 自动模式）

当收到 "每日指数估值" 或作为晨间 cron 任务运行时，使用此工作流。

### 数据采集

**⚠️ 必须使用 browser 工具，不能仅依赖 web_extract！**
web_extract 对蛋卷首页大表经常截断/总结，导致数据缺失或错位。

1. 使用 `browser_navigate` 访问 `https://danjuanfunds.com/djmodule/value-center`
2. 使用 `browser_console` 执行 JavaScript 提取完整 DOM 数据表
3. 逐行解析，按索引名称匹配 PE/百分位数值

备用降级：若浏览器获取失败，对每个缺失指数单独用 `web_search` 搜索补数据，标注来源和日期。

### 采集恐贪指数

**数据源：韭圈儿恐贪指数（funddb.cn）**

使用脚本 `/root/.hermes/scripts/jiucai_fear_index.py` 采集：

```bash
# 简洁输出
python3 /root/.hermes/scripts/jiucai_fear_index.py --simple
# → "72 贪婪"

# 完整 JSON 输出
python3 /root/.hermes/scripts/jiucai_fear_index.py
```

**接口链路：**
1. `https://funddb.cn/meta_info/toolfear.json` — SEO 元数据（连通性验证）
2. `https://api.jiucaishuo.com/v2/kjtl/getbasedata` — AES-256-CBC 加密的实时数据
3. 解密参数：Key=`K_B+"ll1"`, IV=`K_A+"ll1"`, AES-256-CBC/PKCS7
   - `K_A = "bvroqevdjqibsdkq"`
   - `K_B = "eveqocftukbotqjcequcnkrqlw1oi"`
4. 恐贪指数分类：0-24 极恐 | 25-44 恐惧 | 45-55 中性 | 56-74 贪婪 | 75-100 极贪

### 追踪指数列表

| 类别 | 指数 | 说明 |
|:---|:---|:---|
| A股宽基 | 沪深300、上证50、中证500、中证1000、科创50、创业板 | 代表A股大中小盘 |
| 港股 | 恒生指数、恒生科技、国企指数 | 港股三大核心 |
| 全球 | 标普500、纳指100、德国DAX、MSCI印度 | 美股+欧股+新兴 |
| 行业 | 中证红利、中证银行、中证白酒、中证医疗 | 红利+金融+消费+医药 |

### 报告格式模板

```
📊 全球指数估值日报 · YYYY-MM-DD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
数据来源：蛋卷基金估值中心（基于近10年PE数据）

━━━ A股宽基 ━━━
沪深300 | PE=XX | PE百分位=XX% | 🟢🟡🔴标签
上证50  | PE=XX | PE百分位=XX% | 🟢🟡🔴标签
...

━━━ 港股 ━━━
恒生指数 | PE=XX | PE百分位=XX% | 🟢🟡🔴标签
...

━━━ 全球 ━━━
标普500 | PE=XX | PE百分位=XX% | 🟢🟡🔴标签
...

━━━ 重点行业 ━━━
中证红利 | PE=XX | PE百分位=XX% | 🟢🟡🔴标签
...

━━━ 元宝投资分析 ━━━
总体判断：(高屋建瓴)
A股方面：(结构性机会)
港股方面：(估值与资金面)
全球方面：(美股与其他市场对比)
操作建议：(具体可执行)

⚠️ 免责声明：以上为AI基于公开估值数据的分析参考，不构成投资建议。
```

### 温度标签（用于日报）

| PE百分位 | 标签 | 建议 |
|:--:|:--|:--|
| < 30% | 🟢偏低 | 估值便宜，可关注加仓机会 |
| 30%-70% | 🟡合理 | 估值适中，持有为主 |
| 70%-80% | 🟡合理偏高 | 偏贵，谨慎追高 |
| 80%-95% | 🔴高估 | 明显高估，考虑分批止盈 |
| > 95% | 🔴极高 | 极端高估，注意回调风险 |

### 投资分析撰写要点

以 **元宝（资深运营顾问 / AI合伙人）** 身份撰写分析：
1. **结论先行** — 每段第一句给出判断
2. **数据说话** — 引用PE百分位数值支撑观点
3. **多市场对比** — 横向对比A股/港股/全球的估值温差，找出结构性机会
4. **操作建议要具体** — 如"沪深300在8%分位已进入历史低估区间，有仓位的可以定投加仓"
5. **免责声明必须附带** — 每份报告末尾都需标注

### 定时任务

cron 表达式：`30 7 * * *`（每天07:30，A股开盘前2小时）
toolsets：`['web', 'terminal', 'file', 'browser']`
deliver：飞书私聊

---

## 参考文件

- `references/csi300-pe-history.md` — 沪深300历史PE数据及百分位统计分析
- `references/data-sources.md` — 各数据源特点与可信度说明
- `references/chuangyeban-kc50-analysis.md` — 创业板指 & 科创50 PE百分位分析（2026-06-18）
- `references/jiucai-fear-greed-api.md` — 韭圈儿恐贪指数API反向工程记录（含SPA API通用方法论）

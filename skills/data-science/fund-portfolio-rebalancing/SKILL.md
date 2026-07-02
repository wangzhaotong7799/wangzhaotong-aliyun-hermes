---
name: fund-portfolio-rebalancing
description: 个人基金持仓穿透分析与调仓建议 — 读取持仓数据、查询基金季报、穿透计算实际股债比、诊断风格重叠、生成结构化调仓方案
tags:
  - fund
  - portfolio
  - rebalancing
  - investment
  - analysis
---

# 基金持仓分析与调仓建议

## 触发条件

用户要求：
- "看看我的持仓" / "调仓建议" / "再平衡"
- "分析一下这个基金怎么样" / "看看它跟其他持仓有没有重叠"
- "帮我看看应该换什么基金"

## 工作流程

### 第一步：读取/整理持仓数据

获取当前持仓的来源（按优先级）：
1. **SQLite数据库**：`~/.hermes/fund_portfolio.db` 的 `holdings` 表（如果已建）
2. **Excel文件**：用户上传的 xlsx，用 `openpyxl` 读取
3. **用户手动提供**：从消息中提取基金名称+金额

```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/fund_portfolio.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT * FROM holdings ORDER BY amount DESC')
holdings = [dict(r) for r in c.fetchall()]
```

### 第二步：查询基金最新持仓（穿透分析）

**目的**：知道每只基金底层到底买了什么，才能算真实股债比。

**核心数据源**：
- **天天基金** `fundf10.eastmoney.com/ccmx_<code>.html` — 前十大重仓+资产配置
- **新浪财经** `stock.finance.sina.com.cn/fundInfo/view/FundInfo_CGMX.php?symbol=<code>` — 全部持股明细
- **同花顺** `basic.10jqka.com.cn/<code>/asset.html` — 资产配置

**查询命令**：
```
web_extract(urls=["https://fundf10.eastmoney.com/ccmx_270002.html"])
# 或
web_extract(urls=["https://stock.finance.sina.com.cn/fundInfo/view/FundInfo_CGMX.php?symbol=270002"])
```

**关键字段**（截至最新季报日期）：
- `资产配置`：股票%、债券%、现金%
- `前十大重仓股`：股票名称、占净值比、行业
- 记录 `as_of_date`（季报日期）

**注意**：新浪和同花顺可能滞后（显示年报而非最新季报），优先用天天基金的数据。

### 第三步：穿透计算实际股债比

将每只基金拆解为"权益部分 + 债券部分 + 现金部分"：

```
分类规则：
- 纯指数ETF联接/LOF（创业板、科创50、沪深300、A500等）：权益 ≈ 100%
- 纯债指数（中债7-10年、中债新综合等）：债券 ≈ 100%
- 被动策略指数（红利、红利低波等）：权益 ≈ 100%
- 主动混合型（偏股混合）：查季报取实际股票%
- 平衡混合型：查季报取实际股票%+债券%
- 偏债混合/二级债基：查季报或者按 股票~16% + 债券~80% 估算
```

计算公式：
```
实际权益 = Σ (基金金额 × 权益百分比)
实际债券 = Σ (基金金额 × 债券百分比)
实际现金 = 总金额 - 实际权益 - 实际债券
```

### 第四步：诊断问题

检查以下维度并记录到报告：

| 检查项 | 说明 |
|--------|------|
| **产品重叠** | 同一家基金公司产品过多（如易方达4只以上）→ 建议分散 |
| **风格重叠** | 两只主动混合基金对比前十大持仓，真有重叠还是伪重叠 |
| **单一股票穿透暴露** | 紫金矿业同时被多只基金持有时的总暴露比例 |
| **仓位集中度** | 某只基金占比 > 20% 是否合理 |
| **科创/创业板比例** | 单市场暴露是否过大 |
| **债券内部结构** | 同类型利率债过多（如同时持有中债7-10年+中债新综合） |

**主动基金风格对比方法**：
- 列出两只基金的行业偏好（南方优选成长=制造业69%+新能源；广发稳健增长=有色/黄金+消费+平衡）
- 对比前十大中重叠的个股（如久立特材、紫金矿业同时持有）
- 结论：是"互补"还是"重复" — 互补则保留，重复则合并

### 第五步：检查市场环境

查询当前市场情绪：
```
cd ~/.hermes/scripts && python3 jiucai_fear_index.py --simple
```

结合近期行情（搜索 "A股 市场 近期走势"）判断股票仓位的合理性。

### 第六步：生成调仓建议报告

报告结构：

```
## 一、当前持仓总览
表格：基金名 | 金额 | 占比 | 类型

## 二、穿透后实际资产配置
权益 XX% | 债券 XX% | 现金 XX%

## 三、诊断发现
- 发现问题1：...
- 发现问题2：...

## 四、调仓方案（2-3个选项）
### 方案A：精简版（推荐）
操作1：卖XX → 买XX，理由
操作2：合并XX → XX，理由

### 方案B：进攻型（提高权益）
### 方案C：保守型（降低权益）

## 五、我的建议
选择一个方案，说明理由。
```

### 第七步：更新数据库

调仓执行后，更新 `fund_portfolio.db` 中的 `holdings` 表：
```
DELETE FROM holdings;  -- 重新写入
INSERT INTO holdings (fund_name, amount, percentage, notes) VALUES (...)
```

## 基金池管理

用户的基金选择池存储在 `fund_portfolio.db.funds` 表中，结构：

```
category TEXT       -- 宽基/行业主题/策略/债券
sub_category TEXT   -- 细分
fund_name TEXT      -- 基金名称
company TEXT        -- 基金公司
etf_code TEXT       -- 场内ETF代码
otc_code TEXT       -- 场外申购代码
notes TEXT          -- 备注
```

规则：
- **未来买基金只能从池中选**（池外现持的保留不动）
- 池子需要建 `CREATE TABLE` + 批量 INSERT
- 也存入内存和 OpenViking 做备份

## 常见坑

### 假重叠 vs 真重叠
- 只看"都是混合型"就判断重叠 → ❌ 错
- 要对比前十大持仓的行业分布才准确 → ✅ 对
- 例子：南方优选成长(制造业+新能源) vs 广发稳健增长(有色+消费+平衡) → 实际互补

### 穿透遗漏
- 不查季报就直接按基金类型估算 → ❌ 可能偏差大
- 至少查最新季报的股票仓位比例 → ✅

### 基金季报日期
- 不同来源的数据可能不同：新浪可能是2025年报，天天基金可能是2026Q1
- 一定要确认 `as_of_date` 字段
- Q1报告约4月底发布，Q2约7月底发布

### 费率不可忽略
- 主动基金管理费 1.20% vs 指数基金 0.15%
- 长期持有差异巨大，调仓时需考虑

## 参考
- 基金池数据库：`~/.hermes/fund_portfolio.db`
- 恐贪指数脚本：`~/.hermes/scripts/jiucai_fear_index.py`
- 基金季报发布时间：Q1(4月底)、Q2(7月底)、Q3(10月底)、年报(3月底)

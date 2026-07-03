---
name: investment-research
description: 投资研究编排技能 — 股票/基金/指数的分析工具链决策框架。整合 Daisy Financial Research（深度股票研究）、Stocks（快速查价）、index-valuation-analysis（指数估值）、fund-portfolio-rebalancing（持仓管理）等工具，根据用户需求选择最合适的分析路径。
tags: [finance, investment, stocks, funds, research, orchestration]
category: research
related_skills: [daisy-financial-research, stocks, index-valuation-analysis, fund-portfolio-rebalancing]
version: 1.0.0
---

# Investment Research 投资研究编排

投资分析工具的**决策框架**。不是替代具体技能，而是告诉我面对一个投资问题时，走哪条分析路径。

---

## 工具链一览

| 工具 | 类型 | 适用场景 | 数据源 | 是否需要 Token |
|------|------|----------|--------|:---:|
| **Daisy Financial Research** | 深度股票研究 | A股/港股/美股基本面、估值、筛选、财报分析 | Tushare Pro + AKShare + Yahoo Finance | ✅ TUSHARE_TOKEN |
| **Stocks（官方）** | 快速行情 | 查股价、历史走势、多股对比、加密货币 | Yahoo Finance | ❌ 无需 Key |
| **index-valuation-analysis** | 指数估值 | PE/PB百分位、温度标签、历史频次统计 | 蛋卷基金 + AKShare | ❌ 无需 Key |
| **fund-portfolio-rebalancing** | 持仓管理 | 基金持仓穿透、股债比、调仓建议 | 用户持仓数据 | ❌ 无需 Key |
| **web_search / web_extract** | 通用搜索 | 市场新闻、行业动态、宏观政策 | Web | ❌ 无需 Key |

---

## 决策树

用户问投资相关问题 → 按以下优先级判断：

### ① 快速查价 / 行情快照

> "茅台多少钱"、"看一眼腾讯"、"比特币多少了"

→ 用 **Stocks** skill（快速，零配置）

```bash
# 调 stocks_client.py
python ~/.hermes/skills/finance/stocks/scripts/stocks_client.py quote 600519.SH
python ~/.hermes/skills/finance/stocks/scripts/stocks_client.py crypto BTC ETH
python ~/.hermes/skills/finance/stocks/scripts/stocks_client.py compare AAPL MSFT GOOGL
```

### ② 指数估值 / 温度判断

> "沪深300估值高不高"、"创业板PE多少"、"恐贪指数"

→ 用 **index-valuation-analysis**（已有完善的 cron 日报 + 脚本）

- 蛋卷基金估值中心：`https://danjuanfunds.com/djmodule/value-center`
- 韭圈儿恐贪指数：`~/.hermes/scripts/jiucai_fear_index.py --simple`

### ③ 基金持仓分析与调仓

> "持仓穿透分析"、"股债比多少"、"调仓建议"

→ 用 **fund-portfolio-rebalancing**（已有数据库 + 分析流程）

- 基金池数据库：`~/.hermes/fund_portfolio.db`（24只精选基金）
- 当前持仓 9 只共约 39.4 万
- 调仓时参考 `index-valuation-analysis` 的估值判断

### ④ 个股深度研究 / DCF / 筛选

> "深度分析茅台"、"筛一批高股息A股"、"给腾讯做DCF估值"

→ 用 **Daisy Financial Research**（完整分析师工作流）

- 包含计划→数据采集→验证→报告输出
- 支持 A 股 / 港股 / 美股
- TUSHARE_TOKEN 必须配置才能在 Tushare 回源时正常工作

### ⑤ 市场宏观 / 行业动态 / 新闻

> "今天大盘为什么跌"、"光伏板块怎么看"

→ 用 **web_search**（通用搜索），不局限于股票工具

---

## Hermes 环境配置

### Daisy 安装路径

```
~/.hermes/skills/research/daisy-financial-research/
```

Hermes 自动识别（`research/` 子目录中的 SKILL.md 被自动发现）。

### Stocks 安装路径

```
~/.hermes/skills/finance/stocks/
```

通过 `hermes skills install official/finance/stocks` 安装。

### Python 环境

Hermes 的 Python 位于：
```
/root/.hermes/hermes-agent/venv/bin/python3
```

已安装依赖：tushare==1.4.29, akshare==1.18.64, yfinance==1.5.1, pandas, requests, stockstats

### Tushare Token

Daisy 的核心数据源。配置方式：
```
# 在 .env 中加入
TUSHARE_TOKEN=你的Token
```

免费注册：https://tushare.pro → 个人主页获取 Token。

若未配置，Daisy 仍可用 web_search / Yahoo 做有限分析，但 A 股深度数据不可用。

---

## 参考文件

- `references/stock-tools-setup.md` — Daisy + Stocks 的安装路径、依赖、Token 配置等操作细节
- `references/hermes-extend-options.md` — Profile vs Skill vs Multi-Gateway 的架构决策框架

---

## 注意事项

1. **不开投资建议** — 所有分析结果必须附带 "数据分析仅供参考，不构成投资建议"
2. **不绕路** — 简单查价不调 Daisy（太重），深度分析不用 Stocks（太浅）
3. **基金 vs 股票** — 用户提基金走 index-valuation-analysis / fund-portfolio-rebalancing，提股票走 Daisy / Stocks
4. **混合场景** — 比如"基金持仓里的股票最近怎么样" → 先用 fund-portfolio-rebalancing 查持仓，再用 Daisy / web 分析具体个股

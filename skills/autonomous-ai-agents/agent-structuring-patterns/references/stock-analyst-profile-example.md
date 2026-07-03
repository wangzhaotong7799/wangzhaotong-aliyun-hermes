# Stock Analyst Profile — Concrete Example

This reference documents the pattern for creating a dedicated Hermes profile for stock/fund analysis work — isolated from the user's daily operations profile.

## When to use this

- User wants ongoing stock/fund analysis (daily/weekly reports, tracking)
- Memory contamination would be a problem (stock market observations mixing with daily work)
- Analysis benefits from different model/provider than daily operations (cheaper Flash for daily scans, Pro for deep analysis)
- Will have its own cron schedule separate from existing report cron

## Profile Creation

```bash
hermes profile create stock-analyst
hermes -p stock-analyst
```

## Suggested SOUL.md

```
你是专业 A 股分析师，专注技术面+基本面分析。
- 每日开盘前扫描市场情绪和技术指标
- 收盘后做复盘和明日预判
- 所有分析结论附数据来源和逻辑推导
- 不编造信息，不确定的说"不确认"
- 每次分析标注数据时间戳
```

## Model Strategy

| Task | Model | Rationale |
|------|-------|-----------|
| Daily market scan | DeepSeek v4 Flash | Cheap, fast, sufficient for data aggregation |
| Deep analysis / report | DeepSeek v4 Pro | Stronger reasoning for complex judgments |
| Multi-model verification | MoA preset (optional) | When confidence matters — costs more tokens |

Configure:
```bash
hermes config set model.default deepseek-v4-flash
```

## Cron Jobs (Examples)

```bash
# Pre-market scan (09:00, before A股 open)
hermes cron create "0 9 * * 1-5" \
  --name "pre-market-scan" \
  --skill agent-structuring-patterns \
  --prompt "扫描今日A股盘前情绪：外盘走势、重要新闻、板块热点。输出结构化的盘前分析简报。" \
  --deliver feishu:oc_xxxxx

# Post-market review (15:30, 30min after close)
hermes cron create "30 15 * * 1-5" \
  --name "post-market-review" \
  --skill agent-structuring-patterns \
  --prompt "复盘今日A股：主要指数涨跌、成交量变化、北向资金、板块轮动、涨停跌停情况。输出明日预判。"
```

## Integration with Existing Fund Portfolio

If the user already has fund tracking (e.g., `fund_portfolio.db`, index valuation skills), the stock analyst profile can:

1. **Share skills** — Install the same `index-valuation-analysis` skill into the stock profile
2. **Cross-reference** — When stock analysis impacts fund positions (e.g., sector rotation), mention it in reports
3. **Keep memory separate** — Individual stock tracking doesn't pollute fund rebalancing decisions in the main profile

## Security Notes

- Stock analysis at scale can consume significant tokens (multiple data fetches per report)
- All external API calls for market data go through the user's configured providers
- Profile has its own `.env` — if stock market data requires additional API keys, this keeps them isolated from production keys

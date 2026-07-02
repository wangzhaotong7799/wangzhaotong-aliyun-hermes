# Fund Portfolio Rebalancing Methodology

A systematic approach for analyzing personal fund holdings and generating rebalancing advice.

## Workflow

### 1. Parse Holdings

User sends holdings file (typically xlsx/csv). Extract with openpyxl:

```python
import openpyxl
wb = openpyxl.load_workbook('file.xlsx')
ws = wb.active
for row in ws.iter_rows(values_only=True):
    print(row)
```

Common xlsx structure: col B = fund name, col C = amount (yuan), col E = ratio formula.

### 2. Calculate Effective Asset Allocation

Funds are not pure stock/bond — hybrid/mixed funds need decomposition:

| Fund Type | Typical Stock % | Typical Bond % |
|---|---|---|
| Pure equity index ETF | 100% | 0% |
| Dividend / low-vol index | 100% | 0% |
| Active balanced fund (优选成长混合) | ~60-80% | ~20-40% |
| Conservative balanced (稳健增长) | ~30-50% | ~50-70% |
| Hybrid bond fund (宝元债券) | ~10-20% | ~80-90% |
| Pure bond index (国开行/新综合) | 0% | 100% |

Sum weighted portions to get stock/bond ratio.

### 3. Check Market Context

Always check two data points before giving advice:

**a) Fear & Greed Index:**
```bash
python3 /root/.hermes/scripts/jiucai_fear_index.py --simple
# Output: "42 中立"
```
- <30 = fearful (oversold opportunity)
- 30-70 = neutral
- >70 = greedy (caution on chasing)

**b) Recent market performance by index:**
Search for recent month's returns for major indices (沪深300, 创业板, 科创50, 恒生). Check A-share market narrative (中报季, AI/tech themes, economic data).

### 4. Identify Issues

Common problems in fund portfolios:

- **Product overlap** — Multiple funds tracking the same or similar benchmark (e.g., two active balanced funds with same role)
- **Company concentration** — Too many funds from one fund house (e.g., 4+ from 易方达)
- **Role redundancy** — Two funds with identical purpose (e.g., two pure bond indices)
- **No core/satellite structure** — Missing clear distinction between core holdings (压舱石) and satellite positions (弹性仓)
- **Overweight in volatile sector** — Single theme (e.g., 科创50) too large after a big run-up

### 5. Generate Options

Present at least 2-3 options with different risk profiles:

| Profile | Stock % | Best for |
|---|---|---|
| **Conservative** | 50-55% | Expecting pullback, capital preservation |
| **Balanced (推荐)** | 60-65% | Neutral market view, consolidation |
| **Aggressive** | 70-75% | Bullish on AI/tech, can stomach volatility |

Each option should specify:
- Which funds to SELL/MERGE (reducing overlap)
- Which funds to BUY/INCREASE
- Target amounts (not just percentages — user has concrete yuan amounts)
- Rationale tied to market context

### 6. Fund Selection (New Addition)

When user wants to add a specific fund type (e.g., A500):

**a) Identify available options** — From user's reference sheet or by searching.

**b) Compare candidates on:**
- Fund house reputation and existing relationship
- Fund size and liquidity (especially for ETFs)
- Fee structure (management fee 管理费 + custody fee 托管费)
- Tracking error and index methodology

**c) Give a clear recommendation** with reasoning, not an open-ended choice.

### 7. Output Format

Structure the response as:

```
## Holdings Summary
[Table with fund name, amount, %]

## Current Allocation
[Stock/bond split, key observations]

## Issues Found
[Bullet list of problems]

## Recommendation: [Option Name]
[Specific trades with amounts]
[Rationale tied to market data]
```

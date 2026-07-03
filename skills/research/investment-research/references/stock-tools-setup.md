# Daisy Financial Research + Stocks 技能安装记录

## 安装时间
2026-07-03（v0.18.0 升级后）

## Daisy 安装

```bash
cd ~/.hermes/skills/research
git clone https://github.com/Agents365-ai/daisy-financial-research.git daisy-financial-research
```

Hermes 自动发现（`research/` 子目录下有 SKILL.md）。
Daisy 版本：v2.6.0（SKILL.md metadata.version）

### Python 依赖

```bash
# 使用 Hermes 的 venv 安装
/root/.hermes/hermes-agent/venv/bin/pip install tushare pandas requests
/root/.hermes/hermes-agent/venv/bin/pip install akshare yfinance stockstats
```

### Tushare Token（未配置）

Daisy 的 Tushare 数据源需要 Token。配置方式：
```
# 在 ~/.hermes/.env 中添加
TUSHARE_TOKEN=你的Token
```

免费注册：https://tushare.pro → 个人主页获取 Token。
未配置时，Daisy 仍可用 web_search / Yahoo 做有限分析，但 Tushare 回源的 A 股深度数据不可用。

### Daisy 数据路由

A 股 → Tushare Pro（需 Token）
港股 → Tushare HK 接口 → AKShare fallback（stock_hk_valuation_comparison_em）
美股 → Yahoo Finance（yfinance 库）
通用 → web_search / Brave MCP

## Stocks（官方）安装

```bash
hermes skills install official/finance/stocks
```

安装路径：`~/.hermes/skills/finance/stocks/`
零配置，纯 Python 标准库 + Yahoo Finance，无需 API Key。

## 验证技能已被识别

```bash
hermes skills list | grep -E "daisy|stock"
```

预期输出显示 `daisy-financial-rese…` 和 `stocks` 均为 enabled。

## 快速测试 Stocks

```bash
python ~/.hermes/skills/finance/stocks/scripts/stocks_client.py quote AAPL
```

## 已知问题

- TUSHARE_TOKEN 未配置（截至 2026-07-03）
- Daisy 的 `pro.hk_daily_basic` 接口返回"请指定正确的接口名"，已通过 AKShare fallback 解决

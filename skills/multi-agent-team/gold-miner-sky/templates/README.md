# 📡 天网 — 输出模板库

> 数据采集报告、榜单数据、政策公告的输出格式模板

## 已有报告（Cron 周报产出）

| 报告 | 采集内容 | 文件大小 |
|------|---------|:-------:|
| 电商周报 | 电商赛道排行榜 + 平台政策 | ~25-41KB |
| 自媒体周报 | 自媒体赛道趋势 + 平台动态 | ~28-34KB |
| CPS联盟营销周报 | 联盟营销趋势 + 赛道分析 | ~25-41KB |

报告存储在：`/root/.hermes/cron/output/`

## 采集输出字段标准

每条数据必须包含：
- `collected_at`: ISO 时间戳
- `source_publish_date`: 原始发布日期
- `data_year`: 发布年份
- `source_url`: 来源链接
- `content`: 采集内容
- `platform`: 数据来源平台
- `采集方法`: web_search / agent-reach / union-search / exa-api

## 新增规范
- 每个模板独立文件
- 文件名格式：`{模板名}_template.md`

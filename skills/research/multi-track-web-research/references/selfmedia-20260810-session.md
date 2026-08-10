# 2026-08-10 自媒体域 8赛道 — Worked Session Reference

Concrete numbers and recipes from a real multi-track Exa collection run (cron job, no interaction). Use as calibration for future runs.

## Setup
- Domain: 自媒体 (self-media), 8 tracks: 短剧/本地生活/教育知识/美妆/美食/母婴/数码/健身
- Platforms: 抖音、小红书、B站、视频号、快手、TikTok
- Method: Exa API via standalone python script, truncate=1200, `publishedDate` captured
- Year target: ≥2026 only (2025 and earlier banned per data-quality mandate)

## Round 1 — full coverage (20 searches)
- 140 raw records → 96 year-valid (68.6%)
- Year-source distribution of valid: publishedDate 85 (88.5%), title 7, text 4
- Per-track valid counts were ALL ≥6 → year gate alone declared "all tracks sufficient"

### The trap
Per-track year-valid counts looked fine (母婴 6, 美食 6, 美妆 9...), but **relevance was broken**:
- 美食 track contained: 药明康德业绩交流会 (stock news), OpenAI/Anthropic 云厂商分析, 沈小婷solo单曲 (celebrity), 商圈咖啡节
- 母婴 track contained: AI IMO 满分金牌, 北京积分落户复盘, 赵露思潮牌, 冷静2024x10kex312 (junk translation page)
- 数码 track contained: 軽井沢マリオットホテル press releases (Japanese hotel PR), 60秒广告报价25.8万 (AI avatar story — marginally related)
- 健身 track contained: 功夫女足票房20亿, 北京积分落户

Lesson: never trust per-track year-valid counts alone. Always do a title relevance scan per track.

## Round 2 — focused re-search for weak tracks (6 searches)
Targets: 母婴 + 美食 only. Disambiguating keyword recipes that worked:
- `2026年 母婴博主 育儿 内容 小红书 变现 带货 奶粉 纸尿裤`
- `2026年 母婴行业 报告 母婴消费 市场 趋势 婴童`
- `2026年 母婴 KOL 达人 种草 母婴品牌 投放 小红书`
- `2026年 美食博主 探店 餐饮 变现 抖音 小红书 团购`
- `2026年 美食内容 创作者 菜谱 美食账号 涨粉 变现`
- `2026年 餐饮 探店达人 佣金 收入 乱象 商家 合作`

Result: 48 raw → 17 year-valid (35.4%) — LOWER than round 1, as expected for focused queries (they surface evergreen 2023-2025 tutorials). Some hits still noisy (2022/2023 探店 articles), but relevant 2026 hits appeared (小红书2026母婴月报, 2026母婴行业报告, 橙学/中式白人饭, 律师转行料理网红, 抖音探店网红好日子到头).

## Merged result
- 188 total records → 113 year-valid → after de-dup + relevance scan: **per-track relevant counts**: 短剧9, 本地生活8, 教育知识8, 数码8, 健身8, 美妆7, 美食7, 母婴7 (policy 12, failure-cases 10 as auxiliary)
- All 8 scoring tracks ≥5 relevant → pass
- Tracks with 7 → flagged "数据置信度中等" in quality gate report

## Quality gate report structure (used, worked well)
1. 采集概况 (totals + pass rate + reject reasons)
2. 年份来源分布 (publishedDate dominance)
3. 赛道覆盖情况 table (relevant count + coverage assessment + 相关性复核 note)
4. 违规记录检查 (tamper check: collected_at vs publishedDate)
5. 通过标准判定 (per-track ≥5 threshold)
6. 数据局限说明 (low-confidence tracks)

## Downstream calibration
- Scoring weights (自媒体域): 变现效率0.35 + 竞争强度0.25(逆) + 供给饱和度0.25(逆) + 生命周期0.15
- 逆分 convention is critical: 竞争/供给 low score = red ocean (negative for attractiveness)
- Report size: ~227 lines / 15KB for full version (within 250-350 expected band for manual mode)
- Delivery: cron DELIVERY marker → full report to file, summary as final response; do NOT call send_message/feishu scripts when DELIVERY is present

## Reusable facts from this run's data
- 抖音真人短剧 IAP 分成 70%→80% (2026-08-08) — latest policy signal, boosts 短剧 track
- 抖音本地生活 2025 GMV 8500亿, +59%, 2026 target +50%
- 抖音线上卖课改定向邀约制 (2026-07) — restructures 教育知识 track
- 小红书处置涉未成年人违规账号 3571 个 (2026-08) — 母婴 compliance red line
- Exa `publishedDate` availability remains high for 自媒体域 (88.5% of valid records)

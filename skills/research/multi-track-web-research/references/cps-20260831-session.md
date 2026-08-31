# CPS 联盟营销域 6-track run — 2026-08-31 (cron, 手动联合模式)

> Worked-session record for the generalizable multi-track pipeline. Team SOP lives in user-owned `wealth-analyst`; this file captures the reusable technique + numbers only.

## Run summary
- Single Exa script, 18 searches (6 tracks × 2 + 平台政策×2 + 失败案例×2 + 补充×2), truncate=1200, absolute output path `/root/data/tianwang_cps_20260831.md` (+ parallel `.json` twin)
- **120 raw → 103 valid = 85.8% pass rate — CPS-domain historical best** (previous best 81.5% on 08-10; 73.1% on 07-06). All 6 tracks ≥10 valid (电商/跨境 14, 本地生活 13, 短视频 13, 外卖 11, 社交 10).
- Rejected 17: 2025×11, 2024-or-earlier×5, no-date×1. No tampering.
- Year-source distribution: publishedDate 47 (39%), text 25, title 15, platform_docs 16, URL 2, web_verified 1, rejected-unknown 9.

## Key learning #1 — publishedDate is now dominant in CPS (reverses old guidance)
The 2026-06/07 CPS runs concluded "publishedDate 不活跃 in CPS (tutorial/forum content, low metadata quality); rely on URL+title". **This run: Exa `publishedDate` was the top year source (47/120 = 39%)** and the pass rate hit 85.8%. The template script's `r.get('publishedDate','')` capture must stay; do NOT strip it for CPS. platform_current/official-doc domain matching remains the fallback (16 records: developer.open-douyin.com, partner.open-douyin.com, developers.weixin.qq.com, store.weixin.qq.com, school.jinritemai.com, seller.tiktokglobalshop.com, veapi.cn, kancloud.cn, csjplatform.com).

## Key learning #2 — web_verified recovery technique (new, zero-API)
Undated "每日热点/跨境早报" roundups (`ikj168.com/46062` 跨境精选热点) had no URL date and no publishedDate, but body cited "千岸科技成功上市" — web_search confirmed 千岸科技 IPO'd 北交所 2026-07-29 → `data_year=2026`, `year_source=web_verified`. Rule: the internal fact must be concretely checkable (IPO date / policy effective date / launch date); vague narrative → reject. This is cheaper than web_extract (no page fetch) and slots in before final reject.

## Key learning #3 — 本地生活CPS track is polluted with old SEO tutorials
The 本地生活 track's unknown pool was dominated by dated old posts that neither URL nor title revealed:
- `jiutoushe.net/wen/256341` — body date 2022-09-16 → reject
- `130vip.com/tuiguang/52560` — body date 2024-01-24 → reject
- `taokeshow.com/4023` — body date 2018-11-28 → reject
- `news.ixbk.net/douban-maizu/3760568` — no date anywhere → reject
- `blog.csdn.net/bojuncheng/.../129773415` — CSDN ID ≈ 2023 → reject
- `nctoro.com/a132028` — body date 2025-05-16 → reject
- `mxy-ai.com/...` — 服务条款 生效 2025-08-01 → reject
- `jjsoho.com/wxtuike/` — body date 2025-09-09 → reject
- `jiemian.com/article/12155312` — ID heuristic ≈2024/25 + content references 2024 internal letter → reject
Lesson: for tutorial/forum/aggregator URLs, do NOT pass them on domain intuition — read the `text_snippet` body date tag and reject on that (this extends Pitfall #6's body-text scan to the REJECT direction as well as the ingestion-time-bias direction).

## Scoring ranking (CPS weights: 佣金率0.25 / LTV0.25 / 政策稳定0.20 / 容量0.20 / 竞争0.10)
本地生活CPS **7.85** > 社交裂变CPS 7.28 > 电商CPS 6.80 > 短视频带货CPS 6.45 > 外卖CPS 6.28 > 跨境CPS 5.08 (vs 08-24: 7.73 / 7.38 / 6.90 / 6.45 / 6.28 / 4.95).
- 本地生活 +0.12 蝉联: 豆包/抖音AI渠道 8-10 独立计费 (酒店综合费率 12% = 11.4% 软件服务费 + 0.6% 支付手续费, 主站 8%; 生活服务最高 18%) — 国内首个 AI 对话入口明码抽佣; "AI渠道佣金红利" first time factored into CPS scoring (佣金率 8.5, domain-high).
- 社交裂变 -0.10: 微信小店推客分销 API 开放 8-23 (利好) vs 微信封杀分销 8-21 + 封禁自家元宝 10亿现金裂变 (利空对冲).
- 电商 -0.10: 京东联盟紧急通知电商达人补税 (合规风暴).
- 跨境 +0.13: TikTok Shop 欧洲跨境POP "领航计划" 8-21 (10亿资源, 新商佣金 9-15%→2-8%, 单商年返佣至高500万) — 唯一亮点; 政策稳定性仍 3.0 垫底.

## New policy signals (feed next week's searches)
- 抖音/字节: 豆包独立交易渠道计费 8-10; 穿山甲 CPS 接口替代原抖客精选联盟; 精选联盟门槛 5% (4-01 分批)
- 微信: 推客分销 API 开放 8-23 (2025 推客 GMV +225%, 超50万带货者); 封杀分销 8-21; 涉诈工具人封禁 8-20
- 京东: Q3 上调 297 类目 / 下调 118 类目 (7-01); 超级18 额外佣金; 全员渠道额外佣提最高 10% (8-27~29); 达人补税通知
- 淘宝联盟: "安心补" 补贴升级可叠加 (8-07); 佣金翻倍活动 8-26
- 美团: 美团返返 (原试吃官) CPA 10元/单 + CPS 8% (7-24~8-31, 日均3000+单, 复购39%+); 外卖平台新规征求意见; Q2 份额 美团43%/淘宝闪购42%/京东15%
- TikTok Shop: 欧洲 POP 领航计划 8-21; 三紧箍咒 (8-27 新越 PPS 评分 / 8-31 样品置换商业标 / 9-4 东南亚正品标签收归); 联盟削佣迫使 DTC 重建达人模型
- 亚马逊: 联盟 "10%→1%" 洗牌; 2026 佣金物流费变更 (官方)
- Shopee: 8-1 联盟佣金开票新规 (企业达人须按卖家开具 NFS-e 发票); 巴西站网红佣金税务申报转嫁
- eBay / CJ: Partner Network 佣金清除; Dropshipping 佣金 clawback

## Artifacts (all in /root/data/)
`tianwang_cps_20260831.md/.json` (collection) + `quality_gate_report_cps_20260831.md` (gate) + `abacus_scoring_cps_20260831.md` + `strategist_cps_20260831.md` + `report_cps_20260831.md` (241行/17KB, box-drawing 核心结论框 + 5维×6赛道加权矩阵 + 12平台政策对比 + 30条编号来源附录). Final response = 50-80行精简摘要 (评分排行 + Top3 核心数据 + 一句话总结); DELIVERY marker present → no manual Feishu send.

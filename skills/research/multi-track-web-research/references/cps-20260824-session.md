# CPS联盟营销域 2026-08-24 会话记录

> 6-track CPS run, wealth-analyst 金脉小队 cron (联合手动模式). Companion to `cps-20260817-session.md`.

## Run mechanics
- **Single Exa script, 22 searches** (6赛道×3 + 2平台政策 + 2失败案例), truncate=1200, numResults 6-7 → `/root/data/tianwang_cps_20260824.md` (absolute path).
- The 6-track single-script pattern keeps working (also 2026-08-10/07-20); no need for 3-group parallel splitting at this size.

## Year gate
- 145 raw → **118 valid (81.4%)**, 27 rejected (8 old <2026 + 19 no-date after multi-strategy recovery).
- **platform_current recovered 23 records** — re-confirms it is the PRIMARY recovery lever in the CPS/vendor-doc domain (抖音开放平台 developer/partner docs, Amazon Associates Central, Shopee Seller Education/help center, 有赞 help center, union/联盟 homepages).
- All 6 tracks ≥13 valid (historical best CPS coverage): 社交裂变17 / 短视频带货17 / 电商16 / 本地生活16 / 跨境14 / 外卖13.

## Pitfall #6 re-confirmed in CPS domain (publishedDate = ingestion time)
- 3 36kr old-ID articles sailed through the gate with `publishedDate=2026` but body content is 2019-2020 (e.g. `m.36kr.com/p/1723665399809` 裂变增长时代终结, `36kr.com/p/875369626928391` 抖音直播切断外链 with visible "2020年09月10日" body date).
- Action: body-text year contradiction scan on auxiliary/failure-case records; excluded the 3 from report citations; noted in the report's data-limitations section (not treated as tampering — Exa metadata semantics).
- **36kr old-ID URLs are the recurring source of this bias** — prioritize them in the contradiction scan.

## Tooling notes
- `read_file` reported "Binary file - cannot display as text" for a perfectly valid UTF-8 `quality_gate_report_20260824.md` (box-drawing + emoji). `file` + python3 read it fine — re-confirms the Pitfall #3 note; verify gate artifacts with python3, not read_file.
- Score-arithmetic check (Pitfall #4 mitigation) passed: weighted totals recomputed, no error this run.

## Scoring (CPS weights: 佣金率0.25 / LTV0.25 / 政策稳定性0.20 / 市场容量0.20 / 竞争强度0.10)
| Rank | Track | Total | vs 2026-08-10 |
|:---:|:---|:---:|:---:|
| 🥇 | 本地生活CPS | 7.73 | +1.03 (首次登顶) |
| 🥈 | 社交裂变CPS | 7.38 | +0.03 |
| 🥉 | 电商CPS | 6.90 | +0.20 |
| 4 | 短视频带货CPS | 6.45 | +1.45 |
| 5 | 外卖CPS | 6.28 | +0.98 |
| 6 | 跨境CPS | 4.95 | -0.25 (垫底, 政策稳定性3.0) |

## Policy signal list (2026, for future CPS runs)
- 抖音精选联盟佣金门槛 1%→5%（2026-04-01 生效，特殊类目保留1%）；外链带货收20%服务费；九大扶持"千川·乘方"全类目免佣。
- 京东联盟 Q3 上调297个三级类目佣金（7-01）+ 春晓计划 350 亿投入 + 新商0扣点/至高返120万广告金。
- 淘宝联盟"安心补"随单补贴升级（8-07）+ 联盟API链接合规改造（5-20起）+ 新增园艺/智能教育/珍玩类目团长侧（3-27）。
- 美团：试吃官CPS 5%→10% + 新客CPA 10元/单（投放期7-24~8-31）；外卖私域拉新首关3→2元/人。
- 微信小店优选联盟计佣结算规则 2026-06-26 生效；私域裂变9大合规红线（诱导分享/强制关注/多级分销）。
- 跨境：TikTok Shop 美国联盟佣金 6 月无预警削减 + Q4 卖家费用改革 + 联盟准入前移（VoC/店铺分双端体检）；Amazon 4-14 同类商品不再计佣 + 佣金最高降幅50% + Promo Codes 下线（7-06）；eBay Partner Network 静默佣金重置；Shopee AMS 佣金规则持续更新。
- 失败案例：1688 停发"分销客"即时零售返佣（4-01起）、直播间"霸王契约"（马孔多投225万净亏82万）、探店一哥白冰偷税 4000万粉账号禁言。

## Deliverables (descriptive naming per Pitfall #2)
`tianwang_cps_20260824.md` + `quality_gate_report_20260824.md` + `abacus_scoring_cps_20260824.md` + `report_cps_20260824.md` (report_202608.md was taken by the 自媒体域 run).

# Selfmedia 8-track run — 2026-08-24 (自媒体域, cron)

Documents Pitfall #6 (Exa `publishedDate` = ingestion time on old articles) and the first fully
validated parallel DIRECT-terminal collection for an 8-track run (previous runs used a single
manual script or delegated subagents).

## Pipeline shape
- Parallel direct-terminal mode: 3 group scripts written with `write_file`
  (`/root/data/exa_selfmedia_g{1,2,3}_20260824.py`), each launched as
  `terminal(background=true)` then `process(action='wait')`. No delegation, no Tirith block.
- Group split: g1 = 短剧/本地生活/教育知识/平台政策 (8 searches), g2 = 美妆/美食/母婴/失败案例
  (8 searches), g3 = 数码/健身/补充搜索 (6 searches). 22 Exa searches total, truncate=1200.
- Outputs to absolute paths `/root/data/tianwang_group{1,2,3}_selfmedia_20260824.md`.
- Results: 148 raw → 136 year-valid (91.9%). Per-track valid: 短剧13 / 本地11 / 教育12 /
  美妆13 / 美食14 / 母婴12 / 数码13 / 健身12; auxiliary 平台政策12 / 失败案例12 / 补充12.
- Recovery detail: 42 records recovered (title 25 + url 7 + platform_current 6 + text 3 + url_date 1).
- Reuse pattern: copy the previous week's group scripts and swap TRACKS + output filename — fastest
  reliable path; the collection script shape has been stable since 2026-08-10.

## Incident: publishedDate = ingestion time on old articles (Pitfall #6)
Year gate passed 136/148, but a body-text scan of the 失败案例 auxiliary set revealed records whose
text_snippet explicitly said 2020/2025 while `publishedDate` said 2026 — Exa had re-stamped old
36kr articles (old p/IDs like 782836058058886, 980368199249672, 3432452472114568) with
collection-time metadata. These are NOT tampering (collected_at and publishedDate agree); it's an
Exa metadata semantics quirk that the year gate cannot catch because the metadata is present and
plausible.

**Detection script pattern** (run after the gate, on auxiliary/historical content only):
```python
import json, re
recs = json.load(open('/root/data/valid_selfmedia_20260824.json'))['records']
for r in recs:
    if r['track'] in ('失败案例', '平台政策', '补充搜索'):
        years = sorted({y for y in re.findall(r'(20[12]\d)', r.get('text_snippet',''))
                        if 2019 <= int(y) <= 2027})
        if years and min(map(int, years)) < 2026 and r['data_year'] == 2026:
            print('REJECT?', r['title'][:60], '| body years:', years)
```
Verdict: 3 失败案例 records rejected (2020/2025 body years) — excluded from report citations;
the report's failure-case section only cited cases whose body text confirmed 2026
(MCN存量竞争 2026-07-29, 三只羊 2026-02-10, 顾茜茜, 蓝月亮达播 2026-04, 网红带货穷途末路).

## Scoring & report outcomes
- Ranking: 短剧6.60 > 教育知识6.43 > 健身6.38 > 本地生活6.30 > 数码6.23 > 母婴6.10 > 美食5.88 > 美妆5.10.
- 美妆 was the only mover (−0.18): 85% brands cut 达播 spend (抖音美妆 TOP20, 17 of 20 shrank
  creator-promo share), 618 international brands back to top ranks → 变现效率 7.0→6.5.
- Report: `report_selfmedia_20260824.md` (240 lines / 20KB), 36 numbered sources in appendix,
  quality-gate report embedded (91.9% pass). Domain-specific filename avoided collision with the
  05:00 电商域 run's `report_ecommerce_20260824.md` (Pitfall #2).
- Experience sedimentation (阶段八) updated all four team MEMORY.md files the same session.

## Reuse notes
- Body-text contradiction scan costs zero API calls and is the only defense against ingestion-time
  publishedDate; run it whenever the report will CITE auxiliary/historical records (失败案例/案例库).
- Keep the scan scoped to auxiliary content — for scoring tracks, publishedDate remains the best
  year source (this run: 8 tracks all ≥11 valid, no contradictions flagged).

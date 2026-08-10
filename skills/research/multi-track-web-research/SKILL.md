---
name: multi-track-web-research
description: Use when collecting multi-track web data for domain reports.
version: 1.0.0
tags: [research, web-search, exa, quality-gate, market-research, data-collection]
category: research
---

# Multi-Track Web Research Pipeline

> Class-level workflow for collecting and quality-gating web data across multiple tracks (赛道/segments) for a market/domain report. The user's team-orchestration skill `wealth-analyst` (金脉小队, user-owned) contains the full SOP for its weekly cron reports; THIS skill captures the generalizable collection + quality-gate technique that applies to any multi-track research task, including ones outside that team setup.

## When to use
- Weekly/monthly domain reports with multiple tracks (自媒体 8赛道, 电商 10赛道, CPS 6赛道, AI工具对比, 硬件选型…)
- Any research task where collected data must be (a) filtered to a specific year range and (b) verified topically relevant per track
- Cron jobs / no-interaction runs: data must pass automated quality gates before scoring

## Core pipeline
1. **Define tracks + disambiguating keywords** (track name alone is NOT enough — see Pitfall #1)
2. **Exa multi-track collection**: one standalone `.py` script, truncate=1200, capture `publishedDate`, multi-strategy year detection
3. **Year validation gate**: keep records ≥ target year; log rejects with reasons
4. **Relevance review gate** ← the step that is almost always missed
5. **Focused re-search** for weak tracks (disambiguating keywords)
6. **Quality gate report** (counts, per-track coverage, tamper check, limitation notes)
7. Hand off clean dataset to scoring/reporting

## ⚠️ Pitfall #1: year-valid ≠ relevant (validated 2026-08-10, 自媒体域)
Exa semantic search passes the YEAR gate but returns topically irrelevant records — worst for generic/ambiguous track names. Observed noise carrying `publishedDate=2026` and passing year validation:
- celebrity/gossip articles
- unrelated company stock/earnings reports (e.g. 药明康德业绩交流会 in a 美食 track)
- adjacent-domain tech news (AI IMO medal in a 母婴 track)
- sports/entertainment (票房, 明星签约) mixed into 健身/美妆 tracks

**Mitigation (mandatory steps):**
1. After the year gate, run a per-track **title relevance scan** (read titles per track; drop cross-domain noise). Count RELEVANT records per track, never year-valid records.
2. If a track has <5 relevant records, run a **focused second search** with disambiguating keywords: append qualifiers like `博主 / 变现 / 带货 / 平台 / 行业报告 / 趋势` to the track name. Example: `2026年 母婴博主 育儿 小红书 变现 带货 奶粉` instead of `2026年 母婴 报告`.
3. **Expected focused-round pass rate is LOWER than round 1** (observed 35.4% vs 68.6%) because focused queries surface evergreen tutorials and old how-to content. Do not treat this as failure — relevance of hits matters more than pass rate. (This is the OPPOSITE of the year-recovery case, where focused search with `2026` prefixes RAISES pass rate.)
4. Merge both rounds, de-duplicate by title, re-count relevance per track.
5. Note low-confidence tracks (relevant count 5-7) in the quality gate report so scoring marks them "数据置信度中等".

## ⚠️ Pitfall #2: sibling cron jobs share the data directory (2026-08-10)
Multiple domain cron jobs (电商/自媒体/CPS) may run at staggered times into the SAME `data/` directory. Files from another domain's run look like yours (e.g. `exa_group1_20260810.py`, `quality_gate_report_202608.md` existed from a 05:00 电商域 run while the 自媒体域 job started 05:30).
- Before collecting, `ls -la --time-style=full-iso` the data dir and check file mtimes to distinguish your run's artifacts from siblings.
- Use DOMAIN-SPECIFIC filenames (e.g. `tianwang_selfmedia_20260810.md`, `quality_gate_report_selfmedia_20260810.md`) — never bare `quality_gate_report_202608.md`.
- When writing the final report, a sibling subagent warning ("file was modified by sibling subagent") may fire; verify your content with read_file/wc after write — it is usually a false positive from concurrent runs, not data loss.

## Exa collection specifics
- **truncate=1200 minimum** (250-500 loses date lines → pass rate collapses to 20-30%)
- **Capture `publishedDate` explicitly** — best year source when present (`r.get('publishedDate','')`, check first 4 chars)
- Year detection fallback chain: publishedDate > URL date pattern `/(20[12]\d)[/\-]` > title year > body `2026年` text (first ~600 chars)
- Expected first-round pass rates by track type: specific tracks (短剧/数码) 70-90%; generic tracks (母婴/美食/美妆) 40-70% with higher noise
- Write the search script with write_file and run `python3 /tmp/script.py`; never inline curl|python pipes (quoting breaks). Output to an ABSOLUTE path (subagent working dirs differ from parent).

## Quality gate report contents
- Total collected / passed / rejected, with reject reason distribution (old year vs no date)
- Per-track: valid count + coverage assessment (✅充分 ≥8 / ⚠️偏少 5-7 / ❌严重不足 <5)
- Tamper check: `collected_at` vs source `publishedDate` consistency
- Data limitation notes for low-confidence tracks
- Pass/fail decision vs threshold: every scoring track needs ≥5 relevant records; if >half of tracks <3, stop and report data insufficiency

## Handoff to downstream stages
Pass the quality gate report + filtered dataset to scoring with: per-track relevant counts, the year range covered (e.g. "2026年1-8月公开信息"), and confidence flags. Never let noise records reach the scoring matrix — one irrelevant "valid" record can swing a track's score by 0.5+.

## Reference: worked session
`references/selfmedia-20260810-session.md` — concrete numbers, noise examples, and the disambiguating keyword recipes that recovered 母婴/美食 (2026-08-10 自媒体域 8-track run).

## Relationship to other skills
- `wealth-analyst` (user-owned, multi-agent-team): full orchestration SOP for the user's weekly domain reports. Its year-validation documentation is extensive; the RELEVANCE gate (this skill's Pitfall #1) is the gap it does not cover. Recommend adding the relevance review step to that SOP.
- `grounded-citations`: use for source/URL hygiene when publishing findings.

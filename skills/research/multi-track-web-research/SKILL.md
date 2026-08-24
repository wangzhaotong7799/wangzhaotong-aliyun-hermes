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
- **The FINAL report file name collides too** (validated 2026-08-17, CPS域): `report_YYYYMM.md` is a shared name across domains in the same month — 自媒体域 had already written `report_202608.md` before the CPS域 run finished, and overwriting it would destroy the other domain's deliverable. Use `report_<domain>_YYYYMMDD.md` (e.g. `report_cps_20260817.md`) for the final report as well. Unique descriptive names beat the uniform naming convention whenever domains share a `data/` directory.

## Exa collection specifics
- **truncate=1200 minimum** (250-500 loses date lines → pass rate collapses to 20-30%)
- **Capture `publishedDate` explicitly** — best year source when present (`r.get('publishedDate','')`, check first 4 chars)
- Year detection fallback chain: publishedDate > URL date pattern `/(20[12]\d)[/\-]` > title year > body `2026年` text (first ~600 chars)
- **Platform-homepage rule**: URLs on official platform domains with current operating info (规则中心/创作激励/帮助中心, e.g. `douyin.com/rule/`, `bilibili.com/read/cv*` rules pages, `tiktok.com/creator-academy`) → mark `data_year=current year`, `year_source=platform_current`. Cheap zero-API recovery (3 records recovered this way on 2026-08-17). **In English/vendor-documentation-heavy domains (跨境CPS/联盟营销: Shopee Seller Education `seller.shopee.sg`/`help.shopee.com.my`, Amazon Associates Central `affiliate-program.amazon.com`) platform_current is the PRIMARY recovery lever, not a minor assist** — 14 records recovered via domain match in the 2026-08-17 CPS run, lifting 跨境CPS from 4 to 12 valid records (publishedDate is rare on such pages; the 36kr-ID heuristic is useless there). Re-confirmed 2026-08-24 CPS run: 23 records recovered via platform_current (抖音开放平台 developer/partner docs, Amazon Central, Shopee education/help, 有赞 help, union homepages); all 6 tracks finished ≥13 valid — best-ever CPS coverage.
- **web_extract manual verification — final fallback** (validated 2026-08-17): when all heuristics fail on a few remaining unknown URLs, fetch each page with `web_extract` and read the real publish date. Resolves BOTH ways: recovers (课堂街 page showed "时间：2026年01月26日" → 2026; QuestMobile snippet text contained "2026本地生活消费洞察报告" → 2026) and definitively rejects (新抖 "新抖服务2021-12-09", 晰数塔 2021-11-22 / 2022-03-10, 新红 "新红数据2025-10-09", Keep×新榜 report → all <2026). Cost: a few page fetches, zero API calls.
- **⚠️ Report-download-site trap**: on aggregator sites (sgpjbg.com, scribd.com, report-warehouse pages), the displayed date is often the report's DATA vintage, not the upload date (Keep×新榜 健身报告 showed "数据来源：Keep，2021年12月" → the report IS 2021, not 2026). Judge by the data references inside, not the page timestamp. Pages with NO visible date (e.g. 鸟哥笔记 article) must be rejected, never guessed.
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

## ⚠️ Pitfall #3: Exa text corrupts markdown fenced JSON blocks (validated 2026-08-17, 电商域 group2)
Exa `text`/`textSnippet` content routinely contains markdown code-fence markers (```) and newlines. When the collection script embeds raw `text_snippet` inside a ` ```json_data_block ``` ` fenced block in the .md output, the inner ``` terminates the fence EARLY → the JSON string is truncated mid-value → output file unparseable. Deceptive part: the script exits 0 and prints "✅ 已保存", so nothing looks wrong until you try to parse.

**Mitigation (mandatory for every Exa → markdown pipeline):**
1. Sanitize before writing to the file: `text_snippet = text[:300].replace("\n", " ").replace("```", "'")` — do the same for `title`. (`json.dumps` already escapes quotes/newlines correctly; the fence backticks are the only thing that breaks the markdown CONTAINER.)
2. After any run, ALWAYS validate the artifact with python3: regex-extract the `json_data_block` fenced block and `json.loads` it. Exit code 0 does NOT mean the output is parseable. (Note: `read_file` may misreport such .md as "binary" — use python3 instead.)
3. When parsing stats, use the generator's ACTUAL field names — don't guess. This pipeline uses `data_year` with values `"2026"`/`"unknown"` (valid = `!= "unknown" and int(...) >= 2026`), NOT `date`/`year`/`publishedDate`. Reading the wrong field yields 0 valid records and a false 0.0% pass rate.
4. Cross-check parsed totals against the script's own printed stats (e.g. `=== 第2组统计: 54/61 = 88.5%`) — they must match exactly. The script prints these; the parse is verification, not discovery.

## ⚠️ Pitfall #4: verify weighted-score arithmetic before ranking (validated 2026-08-17, 电商域)
Even after a clean quality gate, the downstream scoring matrix can carry plain arithmetic errors. Observed: 社交电商 written as 6.25 but true weighted sum `7×0.30+6×0.25+5×0.20+6×0.15+7×0.10 = 6.20` — a 0.05 error that flipped its rank from #3 to #2 vs the adjacent track. Wrong totals silently propagate into the report's ranking table and the final summary.
**Mitigation (mandatory before handoff to report writing):**
1. Recompute every weighted total programmatically or by hand: `Σ(维度分 × 权重)` per track, using the declared weights (e.g. 电商域: 0.30/0.25/0.20/0.15/0.10).
2. Sort by the RECOMPUTED total — do not trust the order in which rows were typed into the matrix.
3. If any total changed, update rank order AND the vs-previous-month comparison table together (they were inconsistent in the observed run).
4. Echo the recomputed totals into the report's ranking table as the single source of truth.

## ⚠️ Pitfall #5: rewrite scripts DROP the JSON fence entirely (validated 2026-08-17, 自媒体域)
Pitfall #3 covers Exa text corrupting the fence from inside. A SECOND, distinct failure: recovery/gate scripts that rewrite the collected .md via `content[:match.start()] + new_json + content[match.end():]` **delete the ` ```json_data_block ``` ` fence markers themselves** (the regex match includes the fences), so downstream code that parses via `re.search(r'```json_data_block\n(.*?)\n```')` gets `AttributeError: 'NoneType'`. Symptom is silent: the rewrite "succeeds", the file just no longer parses.

**Mitigation:**
1. Parse robustly, never depend on fence regex when the file may have been rewritten: `idx = content.index('## 详细数据')` → `jstart = content.index('{', idx)` → `jend = content.rindex('}') + 1` → `json.loads(content[jstart:jend])`.
2. When rewriting, rebuild the container explicitly: `"## 详细数据（JSON数据块）\n\n```json_data_block\n" + new_json + "\n```\n"`.
3. Combine with Pitfall #3's validation step: always `json.loads` the final artifact after ANY transformation pass (merge, recovery, focus-补采), not just after collection.

## ⚠️ Pitfall #6: Exa `publishedDate` can be INGESTION time, not publish date (validated 2026-08-24, 自媒体域; re-confirmed 2026-08-24, CPS域)
The year-detection chain treats `publishedDate` as the most reliable source — and usually it is. But Exa re-stamps OLD articles with collection-time metadata: records whose body text clearly says 2020/2025 (36kr old-ID articles, historical MCN/案例 retrospectives) came back with `publishedDate=2026` and sailed through the year gate as "valid". This is the OPPOSITE failure of Pitfall #1 — the metadata is present but WRONG (too recent), so the normal "unknown year" reject path never fires. Harm: stale failure-case/anecdote data gets cited in reports as current evidence.

**Symptom**: track stats look great (all records pass), but a spot-check of body text shows old years in 失败案例/历史复盘/教程 content.

**Mitigation (mandatory for auxiliary/historical content — 失败案例, case studies, retrospectives):**
1. After the year gate, run a **body-text year contradiction scan** on auxiliary records: regex `text_snippet` for `20[12]\d年` / `20[12]\d-\d`; if min(body year) < target year while `publishedDate` says target year → mark "疑似收录时间偏差" (ingestion-time bias), manually eyeball the title/URL, and REJECT.
2. Records rejected this way are NOT tampering — it's Exa metadata semantics. Do not abort the pipeline; just exclude them from report citations.
3. In the report's failure-case section, only cite cases whose body text confirms the current year. (2026-08-24 自媒体域: 3 old 失败案例 records rejected out of 12 — 2020/2025 body years with 2026 publishedDate. 2026-08-24 CPS域: same bias on 3 36kr old-ID articles — 2019/2020 body content with publishedDate=2026, excluded from citations. **36kr old-ID URLs are the recurring source — prioritize them in the contradiction scan.**)

**Parallel direct-terminal collection is validated for 8-track runs** (2026-08-24 自媒体域): write 3 group scripts with `write_file` (absolute output paths `/root/data/tianwang_group{1,2,3}_selfmedia_YYYYMMDD.md`), launch all 3 as `terminal(background=true)` processes, then `process(wait)` each. No delegation needed, no Tirith block observed. 22 Exa searches → 148 raw → 136 valid (91.9%). Reuse the previous week's group script as the template (copy + swap TRACKS and output filename) — fastest reliable path.

## Reference: worked sessions
`references/selfmedia-20260810-session.md` — concrete numbers, noise examples, and the disambiguating keyword recipes that recovered 母婴/美食 (2026-08-10 自媒体域 8-track run).
`references/exa-md-json-corruption-20260817.md` — the code-fence corruption symptom→diagnosis→fix transcript and the parse/verify recipe (2026-08-17 电商域 group2 run).
`references/selfmedia-20260817-session.md` — fence-loss-on-rewrite incident, web_extract date-verification verdicts, and the focused-search rescue of a weak track (2026-08-17 自媒体域 8-track run).
`references/cps-20260817-session.md` — CPS 6-track run: platform_current as the dominant recovery lever in cross-border/vendor-doc domains (跨境CPS 4→12), re-confirmed fence-loss-on-rewrite, final-report filename collision (`report_202608.md` taken by 自媒体域), and CPS policy signal list (2026-08-17).
`references/selfmedia-20260824-session.md` — Pitfall #6 (publishedDate=ingestion-time on old 36kr articles, body-text contradiction scan recipe) and the validated parallel direct-terminal 3-script collection pattern for 8-track runs (2026-08-24 自媒体域).
`references/cps-20260824-session.md` — CPS 6-track run: single-script 22-search pattern re-validated, platform_current dominant recovery (23 records), Pitfall #6 re-confirmed on 36kr old-ID articles in the CPS domain, ranking results + CPS policy signal list (2026-08-24).

## Relationship to other skills
- `wealth-analyst` (user-owned, multi-agent-team): full orchestration SOP for the user's weekly domain reports. Its year-validation documentation is extensive; the RELEVANCE gate (this skill's Pitfall #1) is the gap it does not cover. Recommend adding the relevance review step to that SOP.
- `grounded-citations`: use for source/URL hygiene when publishing findings.

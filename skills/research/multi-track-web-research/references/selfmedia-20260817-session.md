# Selfmedia 8-track run — 2026-08-17 (自媒体域, cron)

Concrete numbers and incidents from a manual single-script Exa collection + quality gate. Complements
`exa-md-json-corruption-20260817.md` (Pitfall #3) — this one documents Pitfall #5 (fence loss on rewrite)
and the web_extract date-verification fallback (year-detection section).

## Pipeline shape
- Manual mode, one standalone Exa script (write_file → `python3 /tmp/...`), truncate=1200, 20 searches
  (8 tracks × 2 + 2 platform policy + 2 failure cases) → 140 raw records, 123 year-valid (87.9%).
- 美食 track was weak: only 6/14 valid (42.9%) — most hits were 2021/2022 evergreen 探店 articles.
  Focused second pass (2 searches, precise keywords `探店 现状 收入 下滑 内卷` + `美食 自媒体 增长 趋势 报告`)
  returned 14 records, 9 valid → 美食 15/23. Matches Pitfall #1's focused-search recipe.
- Final after merge + manual verdicts: 149 raw / 137 valid (91.9%). All 8 tracks ≥12 valid.

## Incident: fence loss on rewrite (Pitfall #5)
Recovery script rewrote `tianwang_selfmedia_20260817.md` with
`content[:match.start()] + new_json + content[match.end():]`; the regex match spanned the
` ```json_data_block ` ```  fences, so they were deleted. Downstream parse via
`re.search(r'```json_data_block\n(.*?)\n```')` → `AttributeError: 'NoneType'`.
Fix used in-session: `content.index('## 详细数据')` → `content.index('{', idx)` → `content.rindex('}')+1`,
then rebuild the file with explicit fences. Verified working on the merge/finalize pass.

## web_extract manual verdicts (fallback beyond heuristics)
Leftover unknown-year entries (12) after publishedDate/URL/title/text heuristics; 3 recovered by the
platform-homepage rule (douyin.com/rule/, bilibili.com rules page, tiktok.com/creator-academy).
Remaining 9 resolved by fetching pages:

| URL fragment | Page evidence | Verdict |
|:---|:---|:---|
| ketangjie.com/yyjq/14101.html | "时间：2026年01月26日" | ✅ 2026 (text_2026) |
| questmobile.com.cn/research/report/2056581155403087874/ | snippet "QuestMobile **2026**本地生活消费洞察报告" | ✅ 2026 |
| newrank.cn/article/detail/32803 | "新红数据2025-10-09" | ❌ 2025 |
| xd.newrank.cn/help/z/... | "新抖服务2021-12-09" | ❌ 2021 |
| xishuta.cn/newsview54267.html | "时间：2021年11月22日" | ❌ 2021 |
| m.xishuta.cn/newsview60240.html | "2022-03-10" | ❌ 2022 |
| niaogebiji.com/article-695192-1.html | no publish date anywhere in page | ❌ unknown → reject |
| sgpjbg.com/bgdown/57599.html | report body cites "数据来源：Keep，2021年12月"; upload image path 2021-12/20 | ❌ 2021 (DATA vintage, not upload) |
| scribd.com/document/991992322 | same Keep×新榜 report | ❌ 2021 |

## Reuse notes
- The index-based JSON locate (`content.index('{', idx)`) is the robust parse for any collected-data md
  that has been through a transformation pass.
- web_extract fallback is worth ~9 resolutions for ~4 page fetches; prioritize it when unknown count is
  small (<15) and per-track coverage is borderline.
- 电商域 ran 05:00 same day into the same `data/` dir; 自媒体域 started 05:30. Domain-specific
  filenames (`tianwang_selfmedia_*`, `quality_gate_report_selfmedia_*`) avoided clobbering (Pitfall #2).

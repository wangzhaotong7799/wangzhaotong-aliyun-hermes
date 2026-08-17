# Exa → markdown fenced-JSON corruption (2026-08-17, 电商域 group2 run)

## Symptom
- Collection script (`exa_group2_20260817.py`, 9 Exa searches) exits 0, prints `✅ 已保存: ...tianwang_group2_20260817.md`.
- Parsing the ` ```json_data_block ``` ` fenced block with python fails:
  `json.JSONDecodeError: Unterminated string starting at: line 403 column 23 (char 23913)`.
- `read_file` misreports the .md as `Binary file - cannot display as text` even though `file` says `UTF-8 Unicode text` — read it with python3, not read_file.

## Root cause
Exa's `text`/`textSnippet` field contains arbitrary page text, which frequently includes markdown code fences (```) and internal quotes. The script embedded the raw snippet into a markdown fenced block:

```python
f.write("## 详细数据\n\n```json_data_block\n")
f.write(json.dumps(output, ensure_ascii=False, indent=2))
f.write("\n```\n")
```

An inner ``` inside `text_snippet` terminated the fence early → the remainder of the JSON string stayed unclosed → truncated JSON. `json.dumps` escapes quotes/newlines fine; only the fence backticks break the markdown CONTAINER.

## Fix (script side)
Sanitize before embedding (and do the same for title):

```python
"text_snippet": text[:300].replace("\n", " ").replace("```", "'"),
"title": title[:120].replace("```", "'"),
```

## Verify (always, after every run)
Exit code 0 ≠ parseable artifact. Validate with python3:

```python
import json, re
text = open("/root/data/tianwang_group2_20260817.md", encoding="utf-8").read()
blocks = re.findall(r"```json_data_block\s*\n(.*?)```", text, re.S)
data = json.loads(blocks[0].strip())
records = data["results"] if isinstance(data, dict) else data
```

## Parse stats using the generator's ACTUAL fields
The generator writes `data_year` (values `"2026"`, `"2025"`, `"unknown"`), NOT `date`/`year`/`publishedDate`.
- valid = `r["data_year"] != "unknown" and int(r["data_year"]) >= 2026`
- Group by `r["track"]` for per-track totals.
- First attempt used guessed field names → 61 total / 0 valid / 0.0% pass rate. Correct field → 54/61 = 88.5%.
- Cross-check against the script's own printed stats line (`=== 第2组统计: 54/61 = 88.5%`) — they must match; the parse is verification, not discovery.

## Result of the verified run
| track | total | valid(≥2026) |
|---|---:|---:|
| 快手电商 | 7 | 7 (100%) |
| 直播电商(抖音) | 14 | 14 (100%) |
| 社交电商(小红书/微信私域) | 14 | 12 (85.7%) |
| 视频号电商 | 14 | 10 (71.4%) |
| 失败案例 | 12 | 11 (91.7%) |
| **合计** | **61** | **54 (88.5%)** |

`data_year` distribution: 2026×54, 2025×5, unknown×2.

## Same-run overall context (merged 3 groups, 2026-08-17 电商域 10赛道)
The full run merged groups 1-3: **163 raw → 152 valid (93.3%)**, all 10 scoring tracks ≥7 valid (✅充分). Multi-strategy year recovery on the merged set: url 15, title 13, text 9, url_date 6, platform_current 3 (46 recovered total; publishedDate was the primary source for most). Track-aliasing note: auxiliary categories arrive with bare names (`平台政策`, `失败案例`, `补充搜索`) — the year-gate must map them to "(辅助)" labels before scoring so they don't count as tracks. No tamper flags (collected_at 2026-08-17 consistent with source publishedDate).

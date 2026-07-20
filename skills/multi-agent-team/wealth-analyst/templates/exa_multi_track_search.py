#!/usr/bin/env python3
"""
Exa 多赛道搜索模板
====================
用途：一键搜索多个赛道/关键词，输出 Markdown（人工阅读）+ JSON 数据块（程序化年份验证）
用法：修改下方的 TRACKS 列表即可复用

⚠️ truncate=1200 是避免年份被误剔除的关键参数
✅ 包含 publishedDate 字段捕获 + 多策略年份检测
✅ 输出含 year_distribution + track_stats 用于年份验证闸门
"""

import json, os, urllib.request, time, sys, re

# ===== 修改点：在此添加搜索词和赛道名 =====
TRACKS = [
    # (搜索词, 赛道/备注名, 结果数量)
    ("2026年 短剧 行业 报告 市场规模", "短剧赛道", 7),
    ("2026年 本地生活 探店 自媒体 变现", "本地生活赛道", 7),
    # 按需添加更多赛道...
]
# ========================================

# 读取 API Key
api_key = os.environ.get("EXA_API_KEY", "")
if not api_key:
    try:
        with open(os.path.expanduser("~/.hermes/.env")) as f:
            for line in f:
                line = line.strip()
                if line.startswith("EXA_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip("'\"")
                    break
    except FileNotFoundError:
        print("ERROR: ~/.hermes/.env 不存在，且 EXA_API_KEY 未设置")
        sys.exit(1)

if not api_key:
    print("ERROR: 无法读取 EXA_API_KEY")
    sys.exit(1)

all_results = []
total_results = 0

for query, note, num in TRACKS:
    print(f"搜索中: [{note}] {query[:50]}...")
    time.sleep(0.3)

    payload = json.dumps({
        "query": query,
        "type": "auto",
        "numResults": num,
        "contents": {"text": True, "truncate": 1200}
    }).encode()

    try:
        req = urllib.request.Request(
            "https://api.exa.ai/search", data=payload,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        results = data.get("results", [])

        for r in results:
            url = r.get("url", "")
            title = r.get("title", "")
            text = r.get("text", "") or ""
            pd = r.get("publishedDate", "") or ""

            # 多策略年份检测
            year = "unknown"
            source = "none"

            # 策略1: publishedDate 字段
            if pd and pd[:4].isdigit():
                y = int(pd[:4])
                if 2020 <= y <= 2026:
                    year, source = str(y), "publishedDate"

            # 策略2: URL 路径
            if year == "unknown":
                m = re.findall(r'/(20[12]\d)[/\-]', url)
                if m:
                    y = int(m[0])
                    if 2020 <= y <= 2026:
                        year, source = str(y), "url"

            # 策略3: 标题
            if year == "unknown":
                m = re.search(r'(20[12]\d)', title)
                if m:
                    y = int(m.group(1))
                    if 2020 <= y <= 2026:
                        year, source = str(y), "title"

            # 策略4: 正文前600字
            if year == "unknown":
                m = re.search(r'2026[年/\-\.]', text[:600])
                if m:
                    year, source = "2026", "text"

            record = {
                "track": note,
                "title": title[:120],
                "url": url[:200],
                "text_snippet": text[:300].replace("\n", " "),
                "data_year": year,
                "year_source": source,
                "publishedDate": pd,
                "collected_at": time.strftime("%Y-%m-%d")
            }
            all_results.append(record)
            total_results += 1

            mark = "✅" if (year != "unknown" and int(year) >= 2026) else \
                   ("❌" if (year != "unknown" and int(year) < 2026) else "❓")
            print(f"  {mark} [{year}/{source}] {title[:60]}")

    except Exception as e:
        print(f"  ERROR [{note}]: {e}")

# 统计
pass_rate_data = {}
for r in all_results:
    t = r["track"]
    if t not in pass_rate_data:
        pass_rate_data[t] = {"total": 0, "valid": 0}
    pass_rate_data[t]["total"] += 1
    if r["data_year"] != "unknown" and int(r["data_year"]) >= 2026:
        pass_rate_data[t]["valid"] += 1

valid_total = sum(d["valid"] for d in pass_rate_data.values())

print(f"\n=== 采集统计 ===")
print(f"总记录数: {total_results}")
print(f"有效(≥2026): {valid_total}/{total_results} = {valid_total/total_results*100:.1f}%")
for t, d in sorted(pass_rate_data.items()):
    pct = d["valid"]/d["total"]*100 if d["total"] else 0
    print(f"  {t}: {d['valid']}/{d['total']} ({pct:.1f}%)")

# 保存
output = {
    "total": total_results,
    "valid": valid_total,
    "pass_rate": f"{valid_total/total_results*100:.1f}%",
    "track_stats": pass_rate_data,
    "results": all_results
}

output_path = f"data/tianwang_{time.strftime('%Y%m%d')}.md"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(f"# 天网数据采集 — {time.strftime('%Y-%m-%d')}\n\n")
    f.write(f"> 赛道数: {len(TRACKS)} | truncate=1200 | 引擎: Exa API\n\n")
    f.write("## 采集统计\n\n")
    f.write("| 赛道 | 总记录 | 有效(≥2026) | 通过率 |\n")
    f.write("|:---|---:|:---:|:---:|\n")
    for t, d in sorted(pass_rate_data.items()):
        pct = d["valid"]/d["total"]*100 if d["total"] else 0
        f.write(f"| {t} | {d['total']} | {d['valid']} | {pct:.1f}% |\n")
    f.write(f"| **合计** | {total_results} | {valid_total} | {valid_total/total_results*100:.1f}% |\n\n")
    f.write("## 详细数据（JSON数据块）\n\n")
    f.write("```json_data_block\n")
    f.write(json.dumps(output, ensure_ascii=False, indent=2))
    f.write("\n```\n")

print(f"\n✅ 结果已保存: {output_path}")

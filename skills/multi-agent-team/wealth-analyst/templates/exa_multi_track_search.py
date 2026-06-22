#!/usr/bin/env python3
"""
Exa 多赛道搜索模板
====================
用途：一键搜索多个赛道/关键词，输出 Markdown 表格（人工阅读）+ 年份标注
用法：修改下方的 TRACKS 列表即可复用，无需修改其他代码

⚠️ truncate=1200 是避免年份被误剔除的关键参数（低于800会导致大量条目"无日期"）
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

output_lines = []
output_lines.append("# 天网数据采集 — 多赛道搜索\n")
output_lines.append(f"> 采集日期: {time.strftime('%Y-%m-%d')} | 引擎: Exa API\n")
output_lines.append(f"> 赛道数: {len(TRACKS)} | truncate=1200\n\n")

total_results = 0

for query, note, num in TRACKS:
    print(f"搜索中: [{note}] {query[:50]}...")
    time.sleep(0.3)  # 限速

    payload = json.dumps({
        "query": query,
        "type": "auto",
        "numResults": num,
        "contents": {"text": True, "truncate": 1200}
    }).encode()

    try:
        req = urllib.request.Request(
            "https://api.exa.ai/search", data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        results = data.get("results", [])

        output_lines.append(f"\n## [{note}] - {query}\n")
        output_lines.append("| # | 标题 | URL | 摘要(前100字) | 年份判定 | 判定依据 |\n")
        output_lines.append("|---|------|-----|---------------|---------|---------|\n")

        for idx, r in enumerate(results, 1):
            title = r.get('title', '?').replace('|', '\\|')
            url = r.get('url', '?')
            text = r.get('text', '')[:200].replace('\n', ' ').replace('|', '/')
            full_for_check = title + ' ' + (r.get('text', '')[:500])

            # 多策略年份判定
            # (1) URL路径
            url_2026 = bool(re.search(r'/2026/', url))
            url_2025 = bool(re.search(r'/2025/', url))
            # (2) 标题显式
            title_2026 = bool(re.search(r'2026', title))
            title_2025 = bool(re.search(r'2025', title))
            # (3) 正文日期
            text_2026 = bool(re.search(r'2026[年./\-]', full_for_check[:300]))

            # 综合判定 - 优先信任URL > 标题 > 正文
            if url_2026:
                year_info, reason = "2026 ✅", "URL含/2026/"
            elif title_2026 and not title_2025:
                year_info, reason = "2026 ✅", "标题含2026"
            elif text_2026 and not title_2025:
                year_info, reason = "2026 ✅", "正文含2026年"
            elif url_2025:
                year_info, reason = "2025 ❌", "URL含/2025/"
            elif title_2025:
                year_info, reason = "2025 ❌", "标题含2025"
            else:
                year_info, reason = "? ⚠️", "无明确年份标记"

            output_lines.append(f"| {idx} | {title} | {url} | {text[:100]}... | {year_info} | {reason} |\n")
            total_results += 1

        output_lines.append(f"\n--- {note} 采集到 {len(results)} 条结果 ---\n")

    except Exception as e:
        output_lines.append(f"\n## [{note}] - ERROR: {e}\n\n")
        print(f"  ERROR: {e}")

output_lines.append(f"\n\n---\n## 采集统计\n")
output_lines.append(f"- 总搜索次数: {len(TRACKS)}\n")
output_lines.append(f"- 总结果条数: {total_results}\n")
output_lines.append(f"- 采集时间: {time.strftime('%Y-%m-%d')}\n")

output = ''.join(output_lines)
output_path = f"data/tianwang_{time.strftime('%Y%m%d')}.md"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"\n完成！{total_results} 条结果写入 {output_path}")

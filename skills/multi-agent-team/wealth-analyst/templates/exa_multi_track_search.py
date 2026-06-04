#!/usr/bin/env python3
"""
Exa 多赛道数据采集脚本模板
============================
用途：为金脉小队（wealth-analyst）数据采集阶段提供可复用的 Exa API 搜索脚本。
输出：一个 Markdown 文件，同时包含 Human-readable 表格 和 Machine-readable JSON，
      便于算盘阶段直接解析年份分布和进行质量门审核。

使用方式：
  1. 复制本模板到 /tmp/exa_search.py
  2. 修改 TRACKS 列表中的赛道和搜索词
  3. 通过 delegate_task(leaf, terminal+file) 执行
  4. 从输出文件中读取结果

输出文件结构：
  - 采集概况元数据
  - 每个赛道的 Markdown 表格（标题+来源+年份+URL）
  - 每个赛道的文本摘要（供人工阅读评分依据）
  - 完整 JSON 数据块（供程序化年份验证闸门使用）

必改项：
  - TRACKS 列表：更换赛道名、搜索词、搜索数量
  - OUTPUT 路径：指向 data/ 目录

作者：金脉小队
日期：2026-05-25
"""

import json, os, urllib.request, sys, re, time

# ===== 配置区 — 请按需修改 =====

OUTPUT = "/root/data/tianwang_data.md"

TRACKS = [
    # (搜索关键词, 赛道名称, 搜索结果数量)
    # 每个赛道给出 2-3 个不同角度的搜索词
    ("2026年 [赛道] 市场 趋势 报告 增速", "赛道名称1", 5),
    ("2026年 [赛道] 竞争 格局 头部 玩家", "赛道名称1", 5),
    ("2026年 [赛道2] 趋势 规模 报告", "赛道名称2", 5),
    # ... 添加更多赛道
]

# 额外的全局搜索（平台政策、失败案例等）
EXTRA_SEARCHES = [
    ("2026年 平台 政策 佣金 规则 调整", "平台政策", 5),
    ("2026年 失败 案例 倒闭 亏损 翻车", "失败案例", 5),
]

# ===== 下面一般不需要改 =====

def get_api_key():
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("EXA_API_KEY="):
                    return line.strip().split("=", 1)[1]
    return None

def search_exa(api_key, query, note, num=5):
    payload = json.dumps({
        "query": query, "type": "auto", "numResults": num,
        "contents": {"text": True, "truncate": 300}
    }).encode()
    req = urllib.request.Request(
        "https://api.exa.ai/search", data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        items = results_from_response(data, note)
        print(f"  ✅ [{note}] got {len(items)} results")
        return items
    except Exception as e:
        print(f"  ❌ [{note}] error: {e}")
        return []

def results_from_response(data, track_name):
    items = []
    for r in data.get("results", []):
        title = r.get("title", "?").strip()
        url = r.get("url", "?")
        text = r.get("text", "")[:500].replace("\n", " ").strip()
        pub_date = r.get("publishedDate", "")
        data_year = 0
        if pub_date:
            m = re.search(r'(\d{4})', pub_date)
            if m:
                data_year = int(m.group(1))
        elif text:
            years = re.findall(r'\b(202[4-6])\b', text[:200])
            if years:
                data_year = max(int(y) for y in years)
        items.append({
            "track": track_name,
            "title": title,
            "url": url,
            "text": text[:300],
            "source_publish_date": pub_date,
            "data_year": data_year,
            "collected_at": time.strftime("%Y-%m-%d"),
            "source": "exa"
        })
    return items

def write_markdown(all_results, tracks_order):
    lines = [f"# 天网数据采集 — {tracks_order[0] if tracks_order else ''}域 — {time.strftime('%Y年%m月%d日')}",
             f"## 采集概况\n- 总结果数: {len(all_results)}\n- 采集时间: {time.strftime('%Y-%m-%d')}\n"]
    for track in tracks_order:
        tr = [r for r in all_results if r["track"] == track]
        if not tr:
            continue
        lines.append(f"\n## 赛道：{track}\n")
        lines.append("| # | 标题 | 来源 | 发布日期 | data_year | URL |")
        lines.append("|---|------|------|---------|:---------:|-----|")
        for i, r in enumerate(tr, 1):
            lines.append(f"| {i} | {r['title'].replace('|','\\\\|')[:50]} | Exa | {r['source_publish_date'][:10] if r['source_publish_date'] else 'N/A'} | {r['data_year'] or '?'} | {r['url'][:60]} |")
        lines.append(f"\n**文本摘要：**\n")
        for i, r in enumerate(tr, 1):
            lines.append(f"> **{i}. {r['title']}**")
            lines.append(f"> {r['text']}")
            lines.append(f"> 来源: {r['url']} | 发布: {r['source_publish_date'][:10] if r['source_publish_date'] else 'N/A'} | data_year: {r['data_year']}\n")
    lines.append("\n---\n## JSON 数据（结构化）\n```json\n")
    lines.append(json.dumps(all_results, ensure_ascii=False, indent=2))
    lines.append("\n```\n")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n✅ 写入 {OUTPUT}，共 {len(all_results)} 条记录")

def main():
    api_key = get_api_key()
    if not api_key:
        print("ERROR: EXA_API_KEY not found")
        sys.exit(1)
    all_results = []
    searches = [(q, n, num) for q, n, num in TRACKS] + EXTRA_SEARCHES
    print(f"开始 Exa 采集，共 {len(searches)} 次搜索")
    for query, note, num in searches:
        print(f"  搜索: {query[:60]}")
        all_results.extend(search_exa(api_key, query, note, num))
        time.sleep(0.3)
    tracks_order = []
    seen = set()
    for _, note, _ in TRACKS:
        if note not in seen:
            tracks_order.append(note)
            seen.add(note)
    for _, note, _ in EXTRA_SEARCHES:
        if note not in seen:
            tracks_order.append(note)
            seen.add(note)
    write_markdown(all_results, tracks_order)
    print(f"✅ 完成！共 {len(all_results)} 条记录")

if __name__ == "__main__":
    main()

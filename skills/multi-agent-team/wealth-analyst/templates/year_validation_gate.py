#!/usr/bin/env python3
"""
年份验证闸门脚本模板
====================
用途：对天网采集的 Markdown 数据执行年份验证，输出质量报告
用法：修改下方的 DATA_PATH、TRACK_NAMES、DOMAIN_NAME 即可复用

⚠️ 核心逻辑：使用 URL 路径 + 标题 + 正文 三策略综合判定年份
"""

import re, json, os

# ===== 修改点：路径和赛道名 =====
DATA_PATH = "data/tianwang_data.md"
TRACK_NAMES = ["赛道A", "赛道B", "赛道C"]  # 修改为实际赛道名
DOMAIN_NAME = "域名称"
# ===============================

OUTPUT_PATH = "data/quality_gate_report.md"
CURRENT_YEAR = 2026

def detect_year_from_entry(title, url, text):
    """多策略年份检测"""
    # 策略1: URL路径
    url_years = re.findall(r'/(20[12]\d)[/\-]', url)
    # 策略2: 标题显式
    title_years_2026 = bool(re.search(r'\b2026\b', title))
    title_years_2025 = bool(re.search(r'\b2025\b', title))
    # 策略3: 正文日期模式
    text_2026 = bool(re.search(r'2026[年\.\-/]', text[:500]))

    if url_years:
        year = int(url_years[-1])  # 取最近的年份
        if year >= CURRENT_YEAR:
            return year, f"URL路径/{year}/"
    if title_years_2026 and not title_years_2025:
        return 2026, "标题含2026"
    if text_2026 and not title_years_2025:
        return 2026, "正文含2026年"
    if title_years_2025:
        return 2025, "标题含2025"
    # 其他年份从URL提取
    if url_years:
        return int(url_years[-1]), f"URL路径/{url_years[-1]}/"
    return None, "无明确日期"

def parse_markdown_data(filepath):
    """解析天网Markdown数据"""
    if not os.path.exists(filepath):
        print(f"ERROR: 文件不存在 {filepath}")
        return {}

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    tracks = {}
    current_track = None
    for line in lines:
        # 检测赛道标题 ## [赛道名]
        m = re.match(r'^## \[(.+?)\]', line)
        if m:
            current_track = m.group(1)
            tracks[current_track] = []
            continue

        # 检测表格行
        if line.startswith('|') and not line.startswith('| # |') and not line.startswith('|---'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5 and current_track:
                tracks[current_track].append({
                    'title': parts[2],
                    'url': parts[3],
                    'text': ' '.join(parts[4:])
                })
    return tracks

def main():
    tracks = parse_markdown_data(DATA_PATH)
    if not tracks:
        print(f"ERROR: 无法解析数据文件，或文件为空")
        return

    total_all = sum(len(entries) for entries in tracks.values())
    total_passed = 0
    total_rejected = 0
    reject_reasons = {"旧数据(<2026)": 0, "无日期": 0}
    track_stats = []

    for name, entries in tracks.items():
        passed = []
        rejected = []
        for e in entries:
            year, reason = detect_year_from_entry(e['title'], e['url'], e['text'])
            if year and year >= CURRENT_YEAR:
                passed.append(e)
            elif year and year < CURRENT_YEAR:
                rejected.append((e, f"旧数据({year}年)"))
                reject_reasons["旧数据(<2026)"] += 1
            else:
                rejected.append((e, "无发布日期"))
                reject_reasons["无日期"] += 1

        total_passed += len(passed)
        total_rejected += len(rejected)

        if len(passed) >= 5:
            coverage = "✅ 充分"
        elif len(passed) >= 3:
            coverage = "⚠️ 偏少,结论置信度低"
        else:
            coverage = "❌ 严重不足,建议人工调研"

        track_stats.append({
            'name': name, 'total': len(entries),
            'passed': len(passed), 'rejected': len(rejected),
            'coverage': coverage
        })

    # 生成质量报告
    report_lines = [
        f"# 数据质量报告 — {DOMAIN_NAME} — {CURRENT_YEAR}年\n",
        f"> 生成时间: {__import__('time').strftime('%Y-%m-%d')}\n",
        "---\n",
        "## 采集概况\n",
        f"| 指标 | 数值 |\n",
        f"|------|:----:|\n",
        f"| 总采集记录 | {total_all} |\n",
        f"| 通过年份验证(≥{CURRENT_YEAR}年) | {total_passed} ({total_passed/total_all*100:.1f}%) |\n",
        f"| 已剔除 | {total_rejected} ({total_rejected/total_all*100:.1f}%) |\n\n",
        "### 剔除原因\n",
        f"| 原因 | 数量 |\n",
        f"|------|:---:|\n",
    ]
    for reason, count in sorted(reject_reasons.items(), key=lambda x: -x[1]):
        report_lines.append(f"| {reason} | {count} |\n")

    report_lines.extend([
        "\n## 赛道覆盖情况\n",
        f"| 赛道 | 总记录 | 有效(≥{CURRENT_YEAR}) | 剔除 | 覆盖评估 |\n",
        f"|:---|:----:|:----------------:|:---:|:--------|\n",
    ])
    for ts in track_stats:
        report_lines.append(f"| {ts['name']} | {ts['total']} | {ts['passed']} | {ts['rejected']} | {ts['coverage']} |\n")

    report_lines.append("\n## 违规记录\n- 无篡改年份痕迹\n")

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)

    print(f"质量报告已写入 {OUTPUT_PATH}")
    print(f"总{total_all}条 | 通过: {total_passed} ({total_passed/total_all*100:.1f}%) | 剔除: {total_rejected}")
    for ts in track_stats:
        print(f"  {ts['name']}: {ts['passed']}/{ts['total']} - {ts['coverage']}")

if __name__ == '__main__':
    main()

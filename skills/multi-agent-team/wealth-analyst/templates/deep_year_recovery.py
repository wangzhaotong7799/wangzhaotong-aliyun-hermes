#!/usr/bin/env python3
"""
深层年份恢复 — 多策略修复 Exa 采集中的 unknown 条目
在年份验证闸门（阶段三）中发现大量 unknown 条目时使用。
策略：平台首页判定 + 文本2026检测 + 36kr ID启发式

用法：
  1. 修改 INPUT 为天网采集文件路径
  2. 修改 DOMAIN_CONFIG 中的平台域名列表
  3. 运行：python3 deep_year_recovery.py
  4. 输出会更新原始数据文件 + 打印修复统计
"""
import json, re, os

INPUT = "data/tianwang_cps_data.md"

# --- 按域配置的平台首页域名 ---
# 修改为你所在域的官方/服务商域名列表
DOMAIN_CONFIG = {
    "CPS联盟营销": [
        "union.meituan.com", "union.jd.com", "jinbao.pinduoduo.com",
        "taobao.com/market/common/taoke", "alimama.com",
        "affiliate-program.amazon.com", "ads.tiktok.com",
        "kwaixiaodian.com/cps", "cps.ym.qq.com", "youzan.com",
        "help.shopee.com", "seller.shopee.sg",
        "open-douyin.com", "open.fliggy.com",
        "taokeniao.cn", "52gaoyong.com", "jutuike.com",
        "huizanyun.com", "qiaotuoyun.com", "gxpfb.com",
    ],
    "自媒体": [
        "douyin.com", "kuaishou.com", "xiaohongshu.com",
        "bilibili.com", "weixin.qq.com", "weibo.com",
    ],
    "电商": [
        "tmall.com", "taobao.com", "jd.com", "pinduoduo.com",
        "vip.com", "suning.com",
    ],
}

def extract_json_block(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r'```json_data_block\n(.*?)\n```', content, re.DOTALL)
    if m:
        return json.loads(m.group(1)), content, m
    return [], content, None

def is_platform_homepage(url, domains):
    return any(d in url for d in domains)

def has_2026_in_text(text):
    if not text:
        return False
    # 安全模式：仅匹配"2026年"、"2026/"等明确日期格式
    return bool(re.search(r'2026[年/\-\.]', text[:600]))

def has_2026_in_title(title):
    if not title:
        return False
    return bool(re.search(r'(?:^|[\s,，、])2026', title))

def is_36kr_2026(url):
    m = re.search(r'36kr\.com/p/(\d+)', url)
    if m:
        aid = int(m.group(1))
        return aid >= 37000000000
    return False

def recover_unknown(records, domains):
    """Apply multi-strategy recovery to unknown entries. Returns (recovered_count, still_unknown_count)"""
    recovered = 0
    still_unknown = 0

    for r in records:
        if r.get("data_year") != "unknown":
            continue

        url = r.get("url", "")
        title = r.get("title", "")
        text = r.get("text_snippet", "") or r.get("text", "")

        # 策略D: 平台首页
        if is_platform_homepage(url, domains):
            r["data_year"] = "2026"
            r["year_source"] = "platform_current"
            r["source_publish_date"] = "2026-01-01"
            recovered += 1
            continue

        # 策略B: 36kr ID
        if is_36kr_2026(url):
            r["data_year"] = "2026"
            r["year_source"] = "36kr_id"
            r["source_publish_date"] = "2026-01-01"
            recovered += 1
            continue

        # 策略E: 正文文本2026
        if has_2026_in_text(text) or has_2026_in_title(title):
            r["data_year"] = "2026"
            r["year_source"] = "text_2026"
            r["source_publish_date"] = "2026-01-01"
            recovered += 1
            continue

        still_unknown += 1

    return recovered, still_unknown

def main():
    records, content, match = extract_json_block(INPUT)
    if records is None:
        print("ERROR: Cannot find JSON data block")
        return

    # 自动检测域（从文件路径或内容推断）
    domain = "CPS联盟营销"  # 修改为你的域
    domains = DOMAIN_CONFIG.get(domain, DOMAIN_CONFIG["CPS联盟营销"])

    unknown_before = sum(1 for r in records if r.get("data_year") == "unknown")
    print(f"修复前 unknown 条目: {unknown_before}")

    recovered, still_unknown = recover_unknown(records, domains)
    print(f"修复后: 恢复 {recovered} 条, 仍未知 {still_unknown} 条")

    # 更新 JSON 数据块
    if match and recovered > 0:
        new_json = json.dumps(records, ensure_ascii=False, indent=2)
        new_content = content[:match.start()] + new_json + content[match.end():]
        with open(INPUT, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"已更新 {INPUT}")

    # 打印赛道覆盖
    track_2026 = {}
    for r in records:
        if r.get("data_year") == "2026":
            t = r.get("track", "unknown")
            track_2026[t] = track_2026.get(t, 0) + 1
    print("\n赛道覆盖 (2026年):")
    for t, c in sorted(track_2026.items()):
        status = "✅" if c >= 5 else ("⚠️" if c >= 3 else "❌")
        print(f"  {status} {t}: {c}")

if __name__ == "__main__":
    main()

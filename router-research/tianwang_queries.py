#!/usr/bin/env python3
"""天网 - 企业路由器市场调研 Exa API 搜索脚本"""
import json, os, urllib.request

# 从 .env 读取 API Key
env_path = os.path.expanduser("~/.hermes/.env")
api_key = None
if os.path.exists(env_path):
    for line in open(env_path):
        if line.startswith("EXA_API_KEY="):
            api_key = line.strip().split("=", 1)[1]
            break

if not api_key:
    print("ERROR: EXA_API_KEY not found")
    exit(1)

queries = [
    # === 品牌/方案赛道搜索 ===
    ("企业级路由器 性价比 推荐 300台 终端 2025 2026", "赛道总览"),
    ("华为 AR651 AR161 企业路由器 价格 参数 性价比", "华为"),
    ("H3C MSR3610 ER系列 企业路由器 价格 带机量", "H3C"),
    ("锐捷 RG-EG3210 企业路由器 价格 参数 评测", "锐捷"),
    ("TP-LINK 企业路由器 ER6520G 500台 带机量 性价比", "TP-LINK"),
    ("爱快 iKuai 软路由 企业 300台 工控机 N100 方案", "爱快软路由"),
    ("高恪 软路由 企业 性价比 评测", "高恪"),

    # === 价格与对比 ===
    ("2026 企业路由器 品牌对比 价格 排行榜 中小企业", "价格对比"),
    ("企业路由器 300终端 预算 推荐 5000以内", "预算推荐"),

    # === 用户真实评价/负面 ===
    ("企业路由器 翻车 问题 踩坑 体验差", "失败案例"),
    ("锐捷 路由器 故障 问题 负面 评价", "锐捷负面"),
    ("爱快 软路由 不稳定 问题 吐槽", "爱快负面"),
    ("H3C 企业路由器 吐槽 售后 问题", "H3C负面"),
    ("华为 企业路由器 问题 不好用 贵", "华为负面"),
]

results_dir = os.path.expanduser("/root/wangzhaotong-hermes/router-research")

for query, note in queries:
    print(f"\n{'='*60}")
    print(f"=== [{note}] {query}")
    print(f"{'='*60}")
    
    payload = json.dumps({
        "query": query,
        "type": "auto",
        "numResults": 5,
        "contents": {"text": True, "truncate": 500}
    }).encode()
    
    try:
        req = urllib.request.Request(
            "https://api.exa.ai/search", data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        
        results = data.get("results", [])
        print(f"  返回 {len(results)} 条结果")
        
        for i, r in enumerate(results, 1):
            title = r.get('title', '?')
            url = r.get('url', '?')
            text = r.get('text', '')[:300].replace('\n', ' ')
            print(f"\n  [{i}] {title}")
            print(f"      URL: {url}")
            print(f"      TEXT: {text[:200]}")
            
            # 保存完整结果
            result_file = os.path.join(results_dir, f"exa_{note}.jsonl")
            with open(result_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "note": note,
                    "query": query,
                    "title": title,
                    "url": url,
                    "text": text[:500]
                }, ensure_ascii=False) + "\n")
                
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n\n=== 采集完成 ===")

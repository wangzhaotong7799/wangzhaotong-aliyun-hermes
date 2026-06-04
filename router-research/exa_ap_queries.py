#!/usr/bin/env python3
"""
Exa API search script for enterprise PoE ceiling APs.
Searches 6 queries, saves results to JSONL files.
"""

import os
import json
import requests
import time
from datetime import datetime

# Read Exa API key from env file
env_path = os.path.expanduser("~/.hermes/.env")
exa_api_key = None
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith("EXA_API_KEY="):
            exa_api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if not exa_api_key:
    raise ValueError("EXA_API_KEY not found in ~/.hermes/.env")

print(f"Exa API Key: {exa_api_key[:8]}...{exa_api_key[-4:]}")

BASE_DIR = "/root/wangzhaotong-hermes/router-research"

# Define queries - 5 results each
QUERIES = [
    {
        "id": 1,
        "query": "锐捷 吸顶AP RG-RAP 1200M WiFi6 价格 企业",
        "filename": "exa_AP_01_ruijie.jsonl"
    },
    {
        "id": 2,
        "query": "爱快 iKuai 吸顶AP 价格 企业级 WiFi6",
        "filename": "exa_AP_02_ikuai.jsonl"
    },
    {
        "id": 3,
        "query": "H3C Mini 吸顶AP 价格 WiFi6 企业 管理",
        "filename": "exa_AP_03_h3c.jsonl"
    },
    {
        "id": 4,
        "query": "TP-LINK 企业AP 吸顶 WiFi6 价格 AC管理",
        "filename": "exa_AP_04_tplink.jsonl"
    },
    {
        "id": 5,
        "query": "企业级AP 推荐 300终端 部署方案 2026",
        "filename": "exa_AP_05_deployment.jsonl"
    },
    {
        "id": 6,
        "query": "锐捷EG3210 管理AP AC功能 评测",
        "filename": "exa_AP_06_eg3210.jsonl"
    }
]

def search_exa(query_text, max_results=5):
    """Call Exa API search endpoint."""
    url = "https://api.exa.ai/search"
    headers = {
        "Authorization": f"Bearer {exa_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": query_text,
        "numResults": max_results,
        "type": "auto",
        "useAutoprompt": True,
        "contents": {
            "text": True,
            "highlights": True,
            "summary": True
        }
    }
    
    print(f"  Requesting: {query_text}")
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"  Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"  Error response: {resp.text[:500]}")
        resp.raise_for_status()
    
    data = resp.json()
    results = data.get("results", [])
    print(f"  Got {len(results)} results")
    return results, data.get("autopromptString", "")


def save_jsonl(filename, results, query_info):
    """Save results as JSONL with query metadata."""
    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        for r in results:
            record = {
                "query_id": query_info["id"],
                "query_text": query_info["query"],
                "timestamp": datetime.now().isoformat(),
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "published_date": r.get("publishedDate", ""),
                "text": r.get("text", "")[:2000],  # Truncate long text
                "highlights": r.get("highlights", []),
                "summary": r.get("summary", ""),
                "source_type": "exa_api",
                "autoprompt": query_info.get("autoprompt", "")
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  Saved {len(results)} records to {filepath}")


def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    
    for q in QUERIES:
        print(f"\n{'='*60}")
        print(f"Query {q['id']}: {q['query']}")
        print(f"{'='*60}")
        
        try:
            results, autoprompt = search_exa(q["query"], max_results=5)
            q["autoprompt"] = autoprompt
            save_jsonl(q["filename"], results, q)
        except Exception as e:
            print(f"  FAILED: {e}")
        
        # Rate limiting - be polite to the API
        if q != QUERIES[-1]:
            time.sleep(1.5)
    
    print(f"\n{'='*60}")
    print("All queries complete!")
    print(f"Output directory: {BASE_DIR}")


if __name__ == "__main__":
    main()

# Exa 搜索策略模式 — 手动执行版

> 创建：2026-06-01 | 基于CPS联盟营销6赛道手动执行经验

---

## 背景：两种搜索策略的实际效果对比

| 指标 | 多引擎混合搜索 (2026-05-25) | Exa专注搜索 (2026-06-01) |
|:----|:--------------------------:|:-----------------------:|
| 域 | CPS联盟营销6赛道 | CPS联盟营销6赛道 |
| 搜索工具 | Exa+web_search | 仅Exa |
| 总记录 | 175条 | 96条 |
| 通过(≥2026) | 108条 | 77条 |
| 通过率 | **61.7%** | **80.2%** |
| 搜索次数 | 29+ | 15 |
| 执行耗时 | ~6min | ~3min |

**核心发现**：Exa专注搜索 + 精准关键词 + 小范围numResults(6-8)，比多引擎混合搜索的通过率高出近20个百分点，耗时减半。

---

## 推荐搜索模式（手动模式）

### 标准化搜索脚本模板

```python
#!/usr/bin/env python3
"""Exa多赛道搜索模板 — 修改TRACKS列表即可复用"""
import json, os, urllib.request, time

api_key = os.environ.get("EXA_API_KEY") or \
    [l.split("=",1)[1] for l in open(os.path.expanduser("~/.hermes/.env")) if l.startswith("EXA_API_KEY=")][0]

def exa_search(query, num=8, note=""):
    print(f"\n=== [{note}] ===")
    payload = json.dumps({
        "query": query, "type": "auto", "numResults": num,
        "contents": {"text": True, "truncate": 400}
    }).encode()
    req = urllib.request.Request(
        "https://api.exa.ai/search", data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        print(f"结果数: {len(data.get('results',[]))}")
        for r in data.get("results", []):
            print(f"  TITLE: {r.get('title','?')[:80]}")
            print(f"  URL: {r.get('url','?')}")
            print(f"  DATE: {r.get('publishedDate','no date')}")
        return data.get("results", [])
    except Exception as e:
        print(f"  ERROR: {e}")
        return []

# ── 修改此处 ──
TRACKS = [
    ("赛道A 描述", "2026年 搜索词1 搜索词2"),
    ("赛道B 描述", "2026年 搜索词3 搜索词4"),
]
# ── /修改 ──

all_results = {}
for name, query in TRACKS:
    all_results[name] = exa_search(query, num=8, note=name)
    time.sleep(0.5)

total = sum(len(v) for v in all_results.values())
print(f"\n总计: {total}条记录")
```

### 搜索词构造规则

| 要素 | 要求 | 示例 |
|:----|:-----|:-----|
| 年份 | 必须包含「2026年」 | `2026年 外卖CPS 美团联盟` |
| 赛道名 | 精确名词 | `电商CPS` 而非 `CPS电商` |
| 平台名 | 2-3个平台 | `美团 饿了么` |
| 主题词 | 2-3个维度词 | `佣金 返利 趋势` |

**有效搜索词模式**：`2026年 [赛道] [平台1] [平台2] [维度1] [维度2]`

### 搜索维度覆盖

每场比赛搜索应覆盖3个维度：

```
维度A：赛道本身数据        → 6次 × 8条
维度B：平台政策/变化        → 5次 × 6条
维度C：失败案例/负面        → 3次 × 6条
```

对于6赛道域：6+5+3 = **14-15次搜索**，~80-100条原始数据足够。

---

## 避坑

1. **numResults=8 是推荐值** — 多了(15+)会引入大量低质量结果(旧文/SEO垃圾)，少了(<4)覆盖不足
2. **Exa 对失败案例的召回远好于 web_search** — 英文/混合关键词场景优先用Exa
3. **不要用管道命令组合 curl+Python** — 引号嵌套导致 SyntaxError。始终用独立 .py 脚本文件
4. **API key 读取方式** — `source ~/.hermes/.env` 只在当前shell有效。推荐用 `grep EXA_API_KEY ~/.hermes/.env | cut -d= -f2` 或 Python 逐行解析
5. **写文件用 write_file 而非 echo/cat heredoc** — write_file 自动创建目录，无安全扫描问题

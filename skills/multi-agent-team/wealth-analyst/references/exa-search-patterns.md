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

## 产出文件结构（关键设计决策）

Exa 搜索脚本的输出文件结构直接决定了后续年份验证闸门的可靠性和效率。此模式已验证两个版本：

### ❌ 仅 Markdown + 嵌入式 JSON 块（v1，已弃用）

```python
# 错误做法：将JSON块嵌入Markdown文件中
with open("data/tianwang_raw.md", "w") as f:
    for track, results in groups.items():
        f.write(f"## {track}\n\n")
        for r in results:
            f.write("```json\n")
            f.write(json.dumps(r))  # text_preview可能包含"## "标题
            f.write("\n```\n")
```

**问题**：`text_preview` 字段中可能包含 `## ` 开头的 Markdown 标题行（如 `## API文档中心`、`## 查找文档`）。年份验证闸门脚本通过扫描 `## ` 行定位赛道时，会被这些假标题误导，导致大量结果被归入"其他"类别，年通过率计算失真。

**真实案例（2026-06-15）**：CPS联盟营销6赛道，74条记录中仅42条被正确分配赛道标签，通过率从实际60.8%被误算为27%。修复后恢复正常。

### ✅ Markdown + 独立 JSON 双输出（v2，推荐）

```python
# 正确做法：
# 1. 搜索时直接在每条结果的dict中嵌入"track"字段
# 2. 保存两个文件：human_readable.md + machine_readable.json

all_data = []  # 全局结果列表

def exa_search(query, num, track="", note=""):
    ...
    for r in results:
        r["track"] = track      # 关键：在JSON中嵌入赛道字段
        r["note"] = note
    all_data.extend(results)

# 输出A：机器可读的JSON（年份验证用）
json.dump(all_data, open("data/raw.json", "w"), ensure_ascii=False)

# 输出B：人类可读的Markdown（人工复查用）
# 含 track + publishedDate 标注，但年份验证闸门读JSON而非Markdown
```

**关键设计原则**：
- JSON 文件中的每条记录必须包含 `track` 字段（赛道/分组归属）
- 年份验证闸门从 JSON 文件读取（`json.load()`），而非从 Markdown 解析
- Markdown 文件仅用于人工复查和报告引用
- 两个文件同时保存，互不依赖

### 推荐脚本模板（双输出版）

```python
#!/usr/bin/env python3
"""Exa多赛道搜索模板 — 双输出版（JSON + Markdown）"""
import json, os, urllib.request, time

api_key = os.environ.get("EXA_API_KEY") or \
    [l.split("=",1)[1] for l in open(os.path.expanduser("~/.hermes/.env")) if l.startswith("EXA_API_KEY=")][0]

all_data = []  # ← 收集所有结果

def exa_search(query, num=7, track=""):
    """搜索并返回结果，每条结果嵌入track字段"""
    payload = json.dumps({
        "query": query, "type": "auto", "numResults": num,
        "contents": {"text": True, "truncate": 1200}
    }).encode()
    req = urllib.request.Request(
        "https://api.exa.ai/search", data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=60)
    results = json.loads(resp.read()).get("results", [])
    for r in results:
        r["track"] = track    # ← 赛道归属写入JSON内部
    all_data.extend(results)
    return results

# ── 搜索定义 ──
SEARCHES = [
    ("2026年 搜索词A", 7, "赛道A", "备注"),
    ("2026年 搜索词B", 7, "赛道B", "备注"),
]

for query, num, track, note in SEARCHES:
    exa_search(query, num=num, track=track)
    time.sleep(0.3)

# ── 输出A: JSON（年份验证用） ──
json.dump(all_data, open("data/raw.json", "w"), ensure_ascii=False, indent=2)

# ── 输出B: Markdown（人工读） ──
with open("data/raw.md", "w") as f:
    f.write(f"# 采集数据 — {time.strftime('%Y-%m-%d')}\n总记录: {len(all_data)}\n\n")
    groups = {}
    for r in all_data:
        groups.setdefault(r["track"], []).append(r)
    for track, results in groups.items():
        f.write(f"## {track}\n共{len(results)}条\n\n")
        for r in results:
            f.write(f"### {r.get('title','?')[:80]}\n")
            f.write(f"- URL: {r.get('url','?')}\n")
            f.write(f"- publishedDate: {r.get('publishedDate','no-date')}\n")
            f.write(f"- track: {r.get('track')}\n\n")
```

---

## 避坑

1. **numResults=8 是推荐值** — 多了(15+)会引入大量低质量结果(旧文/SEO垃圾)，少了(<4)覆盖不足
2. **Exa 对失败案例的召回远好于 web_search** — 英文/混合关键词场景优先用Exa
3. **不要用管道命令组合 curl+Python** — 引号嵌套导致 SyntaxError。始终用独立 .py 脚本文件
4. **API key 读取方式** — `source ~/.hermes/.env` 只在当前shell有效。推荐用 `grep EXA_API_KEY ~/.hermes/.env | cut -d= -f2` 或 Python 逐行解析
5. **写文件用 write_file 而非 echo/cat heredoc** — write_file 自动创建目录，无安全扫描问题
6. **年份验证闸门必须读 JSON 而非 Markdown** — JSON 文件中的 `track` 字段是可靠的赛道归属标识。Markdown 文件中的 `## ` 标题行可能被文本预览中的假标题污染。年份验证脚本统一用 `json.load(open("data/raw.json"))` 读取，不要用 `re.split("## ", markdown_text)` 解析赛道归属。

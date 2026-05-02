# Hermes Web Search 后端参考手册

> 供天网及各子智能体参考，了解可用的搜索引擎及其能力边界

---

## 引擎优先级（自动选择）

Hermes 的 `web_search` 工具按以下优先级自动选择可用后端：

```
Firecrawl > Parallel > Tavily > Exa
```

配置多个 Key 时，只会激活优先级最高的那个。**要切换后端需在 config 中手动指定**。

---

## 各引擎对比

### 🔥 Firecrawl（默认主引擎）

| 属性 | 说明 |
|------|------|
| API Key | `FIRECRAWL_API_KEY` |
| 能力 | search + extract + crawl |
| 核心优势 | 深度页面爬取，能提取完整正文（支持 markdown）、结构化网页数据 |
| 适用场景 | 平台榜单详情页、政策公告全文、行业报告类内容 |
| 免费额度 | 有免费套餐可注册 |
| 注意 | 免费版有速率限制（一般足够） |

### 🔍 Exa

| 属性 | 说明 |
|------|------|
| API Key | `EXA_API_KEY` |
| SDK | `exa-py`（Hermes 内建依赖，无需额外安装） |
| 能力 | search + extract（语义搜索、知识图谱） |
| 核心优势 | 语义化搜索精度高，适合精确匹配政策关键词、技术概念 |
| 适用场景 | 平台政策搜索、特定话题深度调研、知识发现 |
| 免费额度 | 注册送免费额度 |
| 配置验证 | `python3 -c "from exa_py import Exa; c = Exa(api_key='...'); print(c.search('test', num_results=1))"` |

### 🌐 Tavily

| 属性 | 说明 |
|------|------|
| API Key | `TAVILY_API_KEY` |
| SDK | `tavily-python`（需手动安装） |
| 能力 | search + extract + crawl |
| 核心优势 | AI 优化的搜索结果、实时性强、搜索结果经过摘要优化 |
| 适用场景 | 实时热点追踪、最新行业动态、竞品动态 |
| 安装 | `pip3 install tavily-python` |
| 免费额度 | 注册送免费额度（约 1000 次/月） |

### ⚡ Parallel（备用）

| 属性 | 说明 |
|------|------|
| API Key | `PARALLEL_API_KEY` |
| 能力 | search |
| 核心优势 | 极速、专注搜索 |
| 适用场景 | 需要快速获取搜索摘要的场景 |
| 备注 | 本团队未使用此引擎 |

---

## 实际使用策略（天网推荐）

1. **日常榜单采集** → 默认 Firecrawl（正文页深度爬取效果好）
2. **政策精确搜索** → Exa（语义匹配准，能找到 Firecrawl 搜不到的）
3. **实时热点追踪** → Tavily（实时性最强，适合突发新闻）
4. **数据不足补采** → 切换引擎重试

---

## 环境配置

所有 Key 写在 `~/.hermes/.env`：

```
FIRECRAWL_API_KEY=xxx
EXA_API_KEY=xxx
TAVILY_API_KEY=xxx
```

调用 `web_search` 前需确保 Key 已 export 到当前 shell 环境：
```bash
source ~/.hermes/.env
```

Web backend 自动检测逻辑见 `web_tools.py:_auto_detect_web_backend()`。

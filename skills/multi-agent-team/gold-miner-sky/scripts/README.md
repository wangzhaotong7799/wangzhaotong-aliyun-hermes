# 📡 天网 — 脚本工具库

> 全网数据采集脚本工具栈。Union Search 多引擎聚合（30+引擎）+ Agent-Reach 社交平台通道。

## 已安装工具

| 工具 | 版本 | 路径 | 用途 |
|------|:----:|------|------|
| **Union Search CLI** | latest | `/root/.hermes/tools/union-search-skill/` | 30+ 搜索引擎聚合，含百度/搜狗/360/头条等免费引擎 |
| **Agent-Reach** | v1.4.0 | Hermes venv (`agent-reach`) | 16 个社交平台数据通道，含微博/微信/B站/V2EX/雪球/YouTube/GitHub |
| **web_search** | 内置 | Hermes 工具 | Firecrawl + Exa + Tavily 三引擎并行 |
| **Exa API** | 直调 | curl/Python | 语义搜索，适合行业报告/政策类内容 |
| **B站 API** | 直调 | `api.bilibili.com` | B站热门视频、UP主信息 |

## 已有脚本（在 Union Search 中）

| 脚本 | 说明 |
|------|------|
| `union_search.py` (65KB) | 多平台统一搜索入口 |
| `agents.py` (907KB) | 各搜索引擎代理实现（百度/搜狗/360等30+引擎） |
| `github_search.py` | GitHub 仓库/代码搜索 |
| `youtube_search.py` | YouTube 视频/频道搜索 |
| `rss_search.py` | RSS/Atom 订阅源检索 |
| `url_to_markdown.py` | 网页内容 Markdown 提取 |
| `volcengine_search.py` | 火山引擎搜索 |
| `multi_platform_image_search.py` | 多平台图片搜索 |
| `search_wechat.js` | 微信公众号文章搜索（Node.js） |

## 新增脚本规范
- 文件名格式：`{功能}_{版本}.py`
- 开头注明用途、输入、输出、依赖
- 天网独立开发的采集脚本放在此目录（不放在 Union Search 目录下，避免混乱）

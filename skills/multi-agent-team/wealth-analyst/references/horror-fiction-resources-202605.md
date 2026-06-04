# 恐怖小说免费资源知识库

> 采集日期：2026-05-17 | 来源：Exa AI 搜索 + 各平台实测

## 可爬取性实测结果

| 来源 | 可爬取性 | 技术细节 |
|:---|:---:|:---|
| **知乎规则怪谈** | ✅ 直接爬 | 纯 HTML SSR，`curl -A` 即可获取全文内容 |
| **鬼话连篇网** | ✅ 大概率可爬 | 纯 HTML 网站（未实测） |
| **话本小说** | ⚠️ 需测试 | 动态页面可能性大 |
| **番茄小说** | ❌ 防爬混淆 | 自定义字体编码，正文内容被打散为乱码字符 |
| **七猫/书旗** | ❌ App为主 | 需登录 |

## 已验证可爬取的优质资源

### 知乎规则怪谈（最佳来源）
- URL: `https://www.zhihu.com/question/501651078`（28,534关注，5889万浏览）
- 爬取方法：`curl -s -L -A "Mozilla/5.0 ..." URL | python3 -c "提取 <p> 标签文本"`
- 代表作：《汤泉粮子洗浴中心规则怪谈》（~2500字，三段视角）
- 知乎专栏：`https://zhuanlan.zhihu.com/c_1743223805387083776`

### 番茄小说（防爬，仅可拿目录）
- URL: `https://fanqienovel.com/page/7449644855736683545`
- 前10章免费（`isChapterLock: false`），后续需登录
- 正文有自定义字体混淆，无法直接获取纯文本

### 鬼话连篇网
- URL: `https://www.guihualianpian.cn/`
- 原创鬼故事分享站，含张震讲故事资源

## 爬取工具（Exa API 兜底）

当 Firecrawl/web_search 配额用完时，使用 Exa API：

```python
import json, os, urllib.request

api_key = os.environ.get("EXA_API_KEY")
if not api_key:
    with open(os.path.expanduser("~/.hermes/.env")) as f:
        for line in f:
            if line.startswith("EXA_API_KEY="):
                api_key = line.strip().split("=", 1)[1]
                break

payload = json.dumps({"query": "搜索词", "type": "auto", "numResults": 5, 
                      "contents": {"text": True, "truncate": 300}}).encode()
req = urllib.request.Request(
    "https://api.exa.ai/search", data=payload,
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
)
data = json.loads(urllib.request.urlopen(req).read())
for r in data.get("results", []):
    print(r.get("title"), r.get("url"))
```

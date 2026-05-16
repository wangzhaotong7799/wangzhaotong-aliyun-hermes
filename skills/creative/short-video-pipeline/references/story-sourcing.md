# 📚 恐怖故事素材源 & 内容库

> 本文档记录夜半低语品牌可用的素材来源、提取方法及已有内容资产。
> 更新日期: 2026-05-15

---

## 一、已确认的素材源

### 1. meiriyuedu.cn（每日阅读网）✅ 已验证

**链接:** https://www.meiriyuedu.cn/yuedu/10401.html
**内容:** 鬼故事短篇超吓人（精选40篇）
**提取方法:** curl 直接抓取 HTML → 解析 `<p>` 标签 → 按标题拆分 → 保存单个文件
**风险:** 普通静态网页，无反爬（目前），但可能随时变动

**提取命令:**
```bash
# 1. 下载页面
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://www.meiriyuedu.cn/yuedu/10401.html" -o /tmp/horror_stories.html

# 2. Python 提取（核心逻辑）
python3 -c "
import re, html as html_lib
from pathlib import Path

html = open('/tmp/horror_stories.html').read()
paragraphs = re.findall(r'<p>(.*?)</p>', html, re.DOTALL)

# 清洗 + 按标题拆分
cleaned = []
for p in paragraphs:
    text = re.sub(r'<[^>]+>', '', p).strip()
    text = html_lib.unescape(text)
    if len(text) > 10 and 'script' not in text and '广告' not in text:
        cleaned.append(text)

# 按「鬼故事短篇超吓人（X）：」拆分
stories = {}
cn_map = {'一':1,'二':2, ...}  # 中文数字转整数
for text in cleaned:
    header_match = re.match(r'鬼故事短篇超吓人（([一二三四五六七八九十百]+)）', text)
    if header_match:
        # 保存上一个故事，开始新故事
        ...
"
```

### 2. 番茄小说（fanqienovel.com）⚠️ 有反爬

**链接:** https://fanqienovel.com/reader/7547951686266913304
**问题:** 客户端渲染 SPA + 自定义字体加密（CSS Font-face 混淆文字），curl 无法直接提取内容
**解决方案:** 需要登录态 + API 抓取，或换个网站找同一篇故事
**建议:** 优先使用 meiriyuedu.cn 等静态网站，番茄小说作为后备

### 3. 其他潜在来源（待验证）

| 来源 | 类型 | 反爬 | 优先级 |
|:---|:---|:---:|:---:|
| **知乎「恐怖短篇」话题** | UGC 故事 | 正常 | ⭐⭐⭐ |
| **豆瓣「短篇恐怖故事」小组** | UGC 故事 | 正常 | ⭐⭐⭐ |
| **鬼大爷鬼故事网** | 专业鬼故事站 | 未知 | ⭐⭐ |
| **抖音恐怖故事文案** | 短视频文案 | 需 cookies | ⭐⭐ |
| **小红书灵异笔记** | 用户投稿 | 需登录 | ⭐ |

---

## 二、现有关键提示词库（40篇）

**位置:** `stories/` 目录
**总量:** 40 篇恐怖短篇（每篇180-1560字不等）

### 最佳视频候选篇（500-1200字，适合30-60秒视频）

| 编号 | 故事 | 字数 | 适合度 | 说明 |
|:---:|:---|---:|:---:|---|
| 01 | 坟地管理员 | 1027 | ⭐⭐⭐ | 传统恐怖，氛围感强 |
| 03 | 停尸房的声音 | 867 | ⭐⭐⭐ | 医院场景，悬念层层递进 |
| 04 | 天花板里的秘密 | 950 | ⭐⭐⭐ | 都市灵异，反转不错 |
| 05 | 饿死鬼的年夜饭 | 1020 | ⭐⭐⭐ | 民俗恐怖，年味+恐惧 |
| 10 | 鬼搭车 | 1150 | ⭐⭐⭐ | 公路恐怖，故事完整 |
| 19 | 出租车司机 | 624 | ⭐⭐ | 经典套路，适合快速验证 |
| 20 | 血衣 | 537 | ⭐⭐⭐ | 反转结局（雕牌洗衣粉） |
| 31 | 守夜人 | 1560 | ⭐⭐⭐ | 殡仪馆场景，最长篇 |
| 37 | 女生宿舍的脸 | 1051 | ⭐⭐⭐ | 学生恐怖片即视感 |
| 39 | 电梯里的母女 | 969 | ⭐⭐⭐ | 电梯恐怖，悬疑强 |

### 使用方式

```bash
# 用 --story 指定故事文件
cd /root/wangzhaotong-hermes/horror-pipeline
python scripts/generate_horror_video_v7.py \
  --story stories/story_19_出租车司机.txt \
  --title "出租车司机" \
  -o yeban_v7_taxi_driver.mp4
```

**⚠️ 重要：`--title` 只决定视频中显示的故事名文字，内容由 `--story` 文件决定。**
用错 `--story` 会导致封面标题对但配音内容不对的问题（如用 `--title "老镜子" --story sample_horror.txt` 则标题写老镜子但配音是镜中人）。

---

## 三、素材入库流程

当用户发送新链接时：

1. **尝试 `web_extract`** — 如果是静态网页可能直接拿到
2. **如果失败 → curl 抓取 HTML** — 保存到临时文件
3. **解析 `<p>` 标签提取正文** — 用正则 `r'<p>(.*?)</p>'`
4. **HTML实体解码** — `html.unescape()`
5. **按标题拆分多篇** — 处理类似「鬼故事X」的批量页面
6. **保存单篇文件** — `stories/story_XX_标题.txt`（限30字符以内文件名）
7. **更新此文档** — 在「已有故事库」部分增加新条目

### 目录结构规范

```
stories/
├── story_01_坟地管理员.txt     # 已入库（40篇）
├── story_02_末班车.txt
├── ...
├── story_40_红衣女子.txt
└── story_41_新入库故事.txt     # 新入库
```

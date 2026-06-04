---
name: video-inverse
description: 影墨小队总指挥 - 视频提示词逆向工程：视频预处理→逐帧分析→结构化提示词生成→Word文档交付
version: 1.2.0
author: wangzhaotong7799
tags: [video, prompt-engineering, reverse-engineering, multi-agent]
toolsets_required: ['terminal', 'file', 'vision']
category: multi-agent-team
metadata:
  agent_type: team_orchestrator
  team_role: 影墨小队总指挥
  team: 影墨小队
  priority: high
  memory_enabled: false
  permission_level: read-write
  concurrency_limit: 1
links:
  team_members:
    - frame-catcher: 帧捕手 - 视频预处理，ffmpeg关键帧抽取
    - visual-analyst: 画师 - 逐帧视觉分析，构图/色调/风格描述
    - prompt-scribe: 执笔 - 结构化提示词模板生成（v1.2 新增摄像机百科/钩子框架/灯光库/平台优化）
  references:
    - frame-extraction-guide: references/frame-extraction-guide.md
    - prompt-template: references/prompt-template.md
    - camera-encyclopedia: references/camera-encyclopedia.md
  external_skills:
    - higgsfield-seedance2-jineng: 15个种子技能集 https://github.com/beshuaxian/higgsfield-seedance2-jineng
    - awesome-video-prompts: 多平台提示词合集 https://github.com/songguoxs/awesome-video-prompts
    - seedance-api: Seedance Python客户端 https://github.com/seedance-api/seedance-api
  references:
    - frame-extraction-guide: references/frame-extraction-guide.md
    - prompt-template: references/prompt-template.md
    - camera-encyclopedia: references/camera-encyclopedia.md
    - 2-second-hooks: references/2-second-hooks.md
    - lighting-library: references/lighting-library.md
    - platform-optimization: references/platform-optimization.md
    - wan-video-generation: references/wan-video-generation.md
    - video-gen-api-comparison: references/video-gen-api-comparison.md
    - kling-remake-workflow: references/kling-remake-workflow.md

---
# 🎬 影墨小队 — 视频提示词逆向工程 v1.1

> **角色**: 影墨小队总指挥 | **座右铭**: "帧帧入微，墨尽风华"
> **团队**: 🎯帧捕手 + 🎨画师 + ✍️执笔
> **三大件**: 每个成员独立 SKILL(含铁律) + SOUL + MEMORY + 技能库(scripts/refs/templates)
> **建队标准**: 按 `team-architect` 元技能搭建，同金脉/星光小队一致

---

## 🧭 关联技能速查

| 技能 | 用途 | 路径 |
|------|------|------|
| **team-architect** | 团队组建元技能（建新队/扩编用） | `multi-agent-team/team-architect/` |
| **video-inverse-roster** | 影墨小队名册+召唤示例 | `multi-agent-team/video-inverse-roster/` |
| **Kling翻拍完整SOP** | 选片→拆解→Prompt→Kling→质检全流程 | `/root/wangzhaotong-hermes/videos/kling_remake_workflow_v1.md` |
| **Kling翻拍模板** | 6种场景直接复制改 | `/root/wangzhaotong-hermes/videos/kling_remake_template_v1.md` |
| **Kling翻拍速查卡** | 跑的过程随时翻 | `/root/wangzhaotong-hermes/videos/kling_remake_cheatsheet_v1.md` |
| **GitHub调研报告** | 前沿技术参考 | `/root/wangzhaotong-hermes/videos/github_video_research_report_20260512.md` |

---

## 📋 SOP — 全自动调度流程

### 阶段一：视频预处理 → 委托帧捕手

收到视频文件或链接后：

1. **如果是链接**：用 `terminal` 下载（`wget` 或 `curl -O`）
2. **如果是本地文件**：确认文件路径
3. **必备步骤 —— 获取视频元数据**：使用以下方式之一获取时长、分辨率、帧率
   ```bash
   # 方式 A：ffprobe（推荐）
   ffprobe -v quiet -print_format json -show_format -show_streams video.mp4

   # 方式 B：Python OpenCV
   python3 -c "
   import cv2
   cap = cv2.VideoCapture('video.mp4')
   fps = cap.get(cv2.CAP_PROP_FPS)
   frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
   w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
   h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
   print(f'时长:{frames/fps:.1f}s 分辨率:{w}x{h} 帧率:{fps:.1f}fps')
   cap.release()
   "

   # 方式 C：Python file size + PIL
   python3 -c "import os; print(f'大小:{os.path.getsize(\"video.mp4\")/1024/1024:.1f}MB')"
   ```
4. **委托帧捕手进行预处理**（或直接在总指挥手动模式下执行）：
   ```yaml
   delegate_task(
     goal="对视频进行预处理，提取关键帧和元数据",
     context="视频路径: {path}，视频链接: {url}",
     toolsets=['terminal', 'file'],
     skills=['frame-catcher']
   )
   ```

帧捕手产出：
- 关键帧图片集（每3-5秒1帧，场景切换处额外抽取）
- 视频元数据（时长、分辨率、帧率、编码信息）
- 场景分段标注

### 阶段二：画面分析 → 委托画师

```yaml
delegate_task(
  goal="对所有关键帧进行逐帧视觉分析，输出结构化画面描述",
  context="关键帧路径列表: {frames}，产品图片: {product_image}",
  toolsets=['vision', 'file'],
  skills=['visual-analyst']
)
```

画师产出：
- 每帧画面描述（构图、色调、照明、物体、运动）
- 产品图在产品图中的表现分析
- 视觉风格总结

### 阶段三：提示词生成 → 委托执笔

```yaml
delegate_task(
  goal="综合所有分析结果，生成多版本结构化视频提示词模板",
  context="帧捕手场景分段 + 画师逐帧描述 + 产品分析",
  toolsets=['file'],
  skills=['prompt-scribe']
)
```

执笔产出：
- 核心创意描述
- 视觉风格定义（色调板、构图模式、光效）
- 镜头序列（逐镜头的起承转合）
- 产品替换适配说明

### 阶段三·五：质量门（必须）— 不可跳过

执笔产出后，总指挥必须执行以下质量检查：

**检查项目**（所有项目都必须通过）：

| # | 检查项 | 标准 | 失败处理 |
|:-:|-------|------|---------|
| 1 | 每镜光线描述 | 包含方向+类型+色温 | 退回执笔重写 |
| 2 | 每镜运镜描述 | 包含景别+镜头运动 | 退回执笔重写 |
| 3 | 每镜情绪标签 | 复合标签，不止一个词 | 退回执笔重写 |
| 4 | 时间粒度 | ≤5秒区间，关键段≤3秒 | 退回执笔细化 |
| 5 | 产品细节 | 包含光线与材质的相互作用描述 | 退回执笔补充 |
| 6 | 平台提示词 | 至少一个平台的完整可复制提示词 | 补充平台版本 |
| 7 | 产品替换说明 | 标注可改和不可改的部分 | 补充适配指南 |

**通过标准**：全部7项为绿色。任何一项红色则退回执笔修改，**不允许跳过质量门直接交付**。

### 阶段四（新增）：视频生成 — 通义万相 Wan2.7

当用户要求"生成视频"时，通过通义万相图生视频 API 直接生成。

**前提**：用户提供了产品图片作为首帧参考

**步骤**：
1. 加载 `references/wan-video-generation.md` 获取API参数
2. 从画师分析中提取产品实际色调/材质信息
3. 从执笔提示词中提取第一个分镜的描述，转为 Wan2.7 图生视频 prompt
4. 异步提交 → 轮询（15秒间隔）→ 下载视频到 `videos/segments/`
5. 如需多段，逐段生成后告知用户自行剪辑拼接

**推荐模型**：`wan2.7-i2v-2026-04-25`（¥0.6/秒，720P）
**避坑**：端点用连字符 `video-synthesis`，必须传 `X-DashScope-Async: enable`

### 阶段四：最终质检（质量门 — 不可跳过）

在飞书交付前，按以下清单逐项检查：

- [ ] **4个强制维度**：每个分镜是否包含光线/运镜/色调/情绪？
- [ ] **时间精度**：关键段是否 ≤3秒，普通段 ≤5秒？
- [ ] **光材交互**：产品描述是否体现了「光在材质表面的相互作用」？
- [ ] **多场景编号**：多场景是否独立编号+节点标注？
- [ ] **分镜板 HTML**：是否已生成？内容完整？
- [ ] **平台提示词**：是否直接可复制粘贴，无需调整？
- [ ] **替换说明**：是否标注了换产品时改什么不改什么？
- [ ] **飞书摘要**：是否在群消息中呈现了关键信息（不是长文分段发）？

**任何一项不通过，不得交付，修正后再发。**

### 阶段五：飞书交付（升级版）

最终交付包含三步：

**Step A — 创建 Markdown 报告文件：**
写入 `/root/wangzhaotong-hermes/videos/prompt_report_{YYYYMMDD}.md`

**⚠️ 文件写入后必须验证：**
```python
# write_file 可能静默失败，必须验证文件实际存在
import os
path = '/root/wangzhaotong-hermes/videos/prompt_report_20260512.md'
if not os.path.exists(path):
    print(f'[FAIL] 文件未创建: {path}')
else:
    print(f'[OK] 文件已创建 ({os.path.getsize(path)/1024:.1f}KB)')
```

如果文件不在预期路径，用 `ls` 查一下实际路径，然后用 `find` 找到再发。

**Step B — 生成 Word 文档（.docx）：**
```python
# python-docx 通常已安装，如没有则 pip install python-docx
from docx import Document
doc = Document()
# 设置默认字体
from docx.shared import Pt
from docx.oxml.ns import qn
style = doc.styles['Normal']
style.font.name = '微软雅黑'
style.font.size = Pt(10.5)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

# 读取 .md 转成 .docx
with open('/path/to/report.md', 'r') as f:
    lines = f.readlines()
# ... 逐行解析 headers/tables/lists ...
doc.save('/path/to/report.docx')
```

**Step C — 发到指定飞书群：**

先确认目标群，用 `send_message(target="feishu:群名")` 发送。

**Step D — 创建可视化分镜板 HTML（必备）：**

分镜板必须与实际视频帧相结合，按分镜逐个嵌入帧截图。

**HTML 结构要求**：
- 每个分镜一张卡片，含实际帧（base64内嵌）、镜头号、时间、构图、动作、机位、描述
- 色调板：主色/辅色/背景色 swatch 展示
- 视觉参数统计条：构图占比/景深占比/色温分布
- 色温趋势图：18帧暖冷色带可视化

脚本示例：
```python
import base64
panels = [
    {"frame": "frame_0001.jpg", "shot": 1, "time": "0-3s", "type": "开场抓眼",
     "comp": "极近景微距", "action": "手从阴影伸出，钻石爆闪",
     "camera": "慢推入画，f/1.4", "desc": "暗调反差，单束聚光灯"},
    ...
]
for p in panels:
    with open(os.path.join(frames_dir, p["frame"]), "rb") as f:
        p["b64"] = base64.b64encode(f.read()).decode("utf-8")
# 生成含每个分镜卡片的完整 HTML 页面
```

路径：`/root/wangzhaotong-hermes/videos/storyboard_{YYYYMMDD}.html`

**验证**：文件大小应 > 100KB（含base64图像），用 `ls -la` 确认。

由于飞书不支持 MEDIA 附件，分镜板HTML文件存于服务器路径，在群消息中告知用户路径即可。

---

由于飞书 send_message 不支持 MEDIA 附件嵌入，采取**文本消息替代方案**：
- 将报告核心内容拆分为两条消息发送
- 消息 1：基本信息 + 视觉风格 + 镜头序列
- 消息 2：平台提示词 + 适配指南

消息格式模板（实际使用过的已验证格式）：

```
📹 **{产品名} — 视频提示词逆向报告**

━━━━━━━━━━━━━━━━━━━

**🎬 基本信息**
• 时长 ~{X}s | {宽}x{高} | {帧率}fps
• 内容：{主题描述}
• 分析方式：逐帧采样 + 视觉AI ({帧数}帧)

**🎯 核心创意**
{叙事主线箭头拼接}

**🎨 视觉风格**
• 色调：主色 `#HEX` + 辅色 `#HEX` + 背景色 `#HEX`
• 构图：浅景深前景后景 {X}% + 中心主图 {Y}%
• 照明：{照明描述}
• 风格：纪实感 {X}% + 商业感 {Y}%

━━━━━━━━━━━━━━━━━━━

**📋 六镜头逐帧拆解**

① **{镜头名} ~{X}s** 🎬
{一句画面描述}

② **{镜头名} ~{X}s** 🎬
{一句画面描述}

③ **{镜头名} ~{X}s** 🎬
{一句画面描述}

④ **{镜头名} ~{X}s** 🎬
{一句画面描述}

⑤ **{镜头名} ~{X}s** 🎬
{一句画面描述}

⑥ **{镜头名} ~{X}s** 🎬
{一句画面描述}
```

第二条消息格式（平台提示词）：

```
━━━━━━━━━━━━━━━━━━━

**🤖 三平台 AI 视频提示词**

**Kling（可灵）：**
{中文提示词}

**Runway Gen-3：**
{英文提示词，+ style/color/camera info}

**Seedance：**
{[SCENE START] [CUT] [SCENE END] 格式}

━━━━━━━━━━━━━━━━━━━

**🔄 产品替换适配**
• 改：{改什么}
• 留：{留什么}
• 适用：{产品类型范围}
```

---

## 🔧 手动执行模式（当 delegate_task 不可用时）

如果 `delegate_task` 工具不可用，由总指挥直接执行：

| 阶段 | 手动替代方案 |
|------|-------------|
| 视频预处理 | 直接用 terminal 调用 ffmpeg 抽帧 + Python 获取元数据 |
| 画面分析 | 用 vision_analyze 逐图分析关键帧 |
| 提示词生成 | 用 write_file 直接生成结构化提示词文档 |
| Word文档 | 用 python-docx 从 .md 转换 |
| 群交付 | 用 send_message 发送（MEDIA 附件不支持飞书） |

---

## 📁 文件结构（v1.2 — 每个成员独立三大件+技能库）

```
~/.hermes/skills/multi-agent-team/
├── video-inverse/             # 影墨总指挥
│   ├── SKILL.md
│   └── references/            # 11份参考文件
│
├── frame-catcher/             # 🎯 帧捕手
│   ├── SKILL.md  (含铁律5条)
│   ├── SOUL.md   (人格档案)
│   ├── MEMORY.md (工作记忆)
│   ├── scripts/               # CV智能帧选择脚本
│   ├── references/            # 抽帧参数参考
│   └── templates/             # 场景报告模板
│
├── visual-analyst/            # 🎨 画师
│   ├── SKILL.md  (含铁律5条)
│   ├── SOUL.md   (人格档案)
│   ├── MEMORY.md (工作记忆)
│   ├── scripts/               # batch_analyze.py
│   ├── references/            # 材质光效描述库
│   └── templates/             # 帧分析报告模板
│
└── prompt-scribe/             # ✍️ 执笔
    ├── SKILL.md  (含铁律5条 + v1.2模式库)
    ├── SOUL.md   (人格档案)
    ├── MEMORY.md (工作记忆)
    ├── scripts/               # docx/HTML生成脚本
    ├── references/            # Seedance质检+翻拍案例库
    └── templates/             # 报告/分镜板模板

团队名册：video-inverse-roster/SKILL.md
```

## 📸 输入来源

视频文件存放目录：`/root/wangzhaotong-hermes/videos/`

---

## ⚠️ 已知坑点与故障排查

### ⛔ 1. vision_analyze 依赖辅助视觉模型

画师阶段的 `vision_analyze` 并不使用当前主模型（如 deepseek），而是使用配置中的 `auxiliary.vision` 设置：

```yaml
# config.yaml
auxiliary:
  vision:
    provider: auto
    model: ''
    api_key: ''
```

**常见失败原因（按顺序排查）：**

| 症状 | 原因 | 修复 |
|------|------|------|
| `unknown variant "image_url"` | 主模型不支持图片 | 配置 auxiliary.vision 指向视觉模型 |
| `401 Invalid API key` | auxiliary.vision.api_key 为空 | 显式设置 api_key |
| `401` 但 provider 能正常聊天 | api_key 只在 provider 级别配置了 | auxiliary 需要独立设置 |

**正确配置步骤：**
```bash
source ~/.hermes/.env 2>/dev/null
hermes config set auxiliary.vision.provider <provider_name>
hermes config set auxiliary.vision.model <vision_model_name>
hermes config set auxiliary.vision.api_key "$ALIYUN_BAILIAN_API_KEY"
# ${ENV_VAR} 语法在 auxiliary 中可能不生效，用实际值
```

### ⛔ 2. 视觉模型推荐（阿里云百炼）

| 模型 | 特点 | 推荐场景 |
|------|------|---------|
| `qwen-vl-max-2025-08-13` ← 当前在用 | 最强视觉理解 | **关键帧**（场景切换帧/产品帧/高光帧） |\n| `qwen3-vl-plus-2025-09-23` | 性价比高 | 常规帧分析 |
| `qwen3-vl-flash-2025-10-15` | 快速廉价 | 批量分析 |

### ⛔ 3. 视觉分析失败时的备选方案

如果 vision_analyze 不可用，使用画师的 `scripts/batch_analyze.py` 脚本：

```bash
source ~/.hermes/.env 2>/dev/null
python3 ~/.hermes/skills/multi-agent-team/visual-analyst/scripts/batch_analyze.py
```

已验证 18 帧全量测试通过。

### ⛔ 4. 帧捕手无法使用 ffmpeg 时的备选方案

Alibaba Cloud Linux / 部分 Docker 镜像无 ffmpeg。使用 Python `av` 包（Hermes venv 预装）：

```python
import av
container = av.open('video.mp4')
for frame in container.decode(video=0):
    img = frame.to_image()  # PIL Image
```

### ⛔ 5. write_file 可能静默失败 — 必须验证

**症状**：回复中说"已保存到 /path/to/file"但用户说"目录下没看到文件呀"

**原因**：`write_file` 在某些沙箱环境下返回成功但实际未写入

**预防**：每次写文件后立即验证：
```python
import os
if not os.path.exists(path):
    print(f"[WARN] 文件未创建: {path}")
    # 用 ls 查实际路径，或用 find 搜索
```

或：
```bash
ls -la /output/directory/  # 确认文件列表
```

### ⛔ 6. 飞书 send_message 不支持 MEDIA 附件

**症状**：消息中嵌入 `MEDIA:/path/to/file.docx` 后，飞书群只显示文字，附件被忽略

**原因**：该 tool 的 MEDIA 附件仅支持 telegram/discord/matrix/weixin/signal/yuanbao 平台

**替代方案**：
- 将文件内容转化为格式化文本消息发送
- 如需传递文件附件，需通过 Feishu API（`/open-apis/im/v1/files`）直接上传
- 当前已验证的最佳实践：文本内容分2条消息发送（见阶段四 Step C 模板）

### ⛔ 7. 镜头时长计算

从视频分析中提取镜头时长时，确保总时长 ≈ 各镜头时长之和。通常 6 镜头结构的常见时长模式：
```
开箱 6s → 展示 12s → 细节 6s → 演示 12s → 实景 12s → 收尾 4s = 52s
```
如果各镜头时长加起来不接近视频总时长，则镜头划分有误，需要重新分析场景切换点。

---

## 🧠 模型选择指南（翻拍质量关键）

### 核心认知

| 阶段 | 模型 | 能力 | 说明 |
|:----:|:----:|:----:|------|
| **拆帧/看画面** | 视觉模型（Qwen-VL-Max / qwen3-vl-plus） | ✅ 直接理解图像 | 能直接「看见」构图/光线/材质/运动，零失真 |
| **写翻拍Prompt** | DeepSeek V4（当前主模型） | ✅ 深度思考+语言组织 | 基于结构化帧描述做模式匹配和语言润色 |
| **流程调度** | DeepSeek V4 | ✅ 规划判断 | 整体流程编排和决策 |

### ⚠️ 关键陷阱

**DeepSeek V4 是纯文本模型，看不了图片。**

如果你用 DeepSeek V4 去拆帧，它只能靠「你写给它看的文字描述」来分析——但这层描述本身已经损失了画面信息（颜色偏差、光线描述不准、构图定位模糊）。

正确流程：
```
原视频帧 → 视觉模型（Qwen-VL-Max）直接看图 → 输出结构化帧描述（光线/构图/材质/色调） → DeepSeek V4基于描述写翻拍prompt
```

### 视觉模型推荐

| 模型 | 质量 | 成本 | 推荐场景 |
|------|:----:|:----:|---------|
| **qwen-vl-max-2025-08-13** | ⭐⭐⭐⭐⭐ | 较高 | **关键帧**（场景切换帧/产品帧/高光帧） |
| qwen3-vl-plus-2025-09-23 | ⭐⭐⭐⭐ | 中等 | 常规帧分析 |
| qwen3-vl-flash-2025-10-15 | ⭐⭐⭐ | 低 | 批量快速预览 |

### 分工策略

```
关键帧（场景切换帧/产品特写帧/高光帧） → qwen-vl-max（最精准）
普通帧（过渡帧/背景帧）               → qwen3-vl-plus（够用+省钱）
```

当前 `auxiliary.vision` 配置在 `~/.hermes/config.yaml`：
```yaml
auxiliary:
  vision:
    provider: aliyun-bailian
    model: qwen3-vl-plus-2025-09-23
    api_key: ''  # ⚠️ 必须显式设置，不继承 provider 的 api_key
```

### 扩展阅读

Kling翻拍完整工作流见 `references/kling-remake-workflow.md`，含选片评分矩阵、场景分解6步法、6种翻拍模板、光材交互描述库、质检清单。

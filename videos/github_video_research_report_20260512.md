# GitHub 视频生成前沿调研报告

**调研时间**: 2026-05-12 21:30
**调研目标**: 为「对标爆款视频 → 换产品翻拍」工作流寻找前沿技术和最佳实践
**当前项目**: 五合一婴儿水杯套装 — 通义万相 Wan2.7 图生视频

---

## 一、背景

今天下午我们跑了**五合一婴儿水杯套装**的图生视频流程：
- 影墨小队（帧捕手→画师→执笔）进行视频逆向分析
- 通义万相 Wan2.7 i2v 生成视频片段
- 已生成第一段 10 秒开箱镜头

现在需要升级这整个流程，实现 **「找到爆款视频 → 智能拆解 → 一套提示词直接换产品翻拍」**。

---

## 二、GitHub 调研发现（按价值排序）

### 🏆 Top 1：Prompt-Detective（⭐ 新星）

**仓库**: `okaditya84/Prompt-Detective`
**价值**: ⭐⭐⭐⭐⭐
**定位**: AI视频/图像逆向工程系统

| 技术点 | 我们的现状 | 它可以带来 |
|--------|-----------|-----------|
| 帧选择 | 固定间隔（每3-5秒抽帧） | **CV智能帧选择**（SSIM结构相似度 + 光流法 + LBP） |
| 场景检测 | ffmpeg阈值法（scene>0.3） | **直方图分析 + 运动向量**的场景边界检测 |
| 画面质量 | 无增强处理 | **CLAHE自适应直方图均衡 + 双边滤波** |
| 分析方式 | 单次视觉AI分析 | **多轮多专家分析**（技术pass + 创意pass + prompt pass） |
| 运动分析 | 无 | 光流计算用于动态内容理解 |

**核心差异**: 我们当前用时间间隔抽帧（每3秒1张），它是**根据画面变化智能选择关键帧**——对爆款视频拆解来说，这能精准捕捉到每段最核心的视觉帧，而不是均匀分布。

Tech stack：OpenCV + Streamlit + 多模型推理，可以直接借鉴算法思路。

---

### 🏆 Top 2：Video Prompt Engineering Patterns

**仓库**: `duyuanchao/video-prompt-engineering-patterns`
**价值**: ⭐⭐⭐⭐⭐
**定位**: 多平台视频提示词模板库 + 场景分解指南

**精华内容**（直接可用）：

**运镜模式库**：
| 模式 | 说明 | 最佳平台 |
|------|------|---------|
| Dolly Zoom | 眩晕效果，背景推移 | Sora |
| Time Lapse | 加速时间进程 | Sora, Veo |
| Parallax Scroll | 分层景深运动 | Midjourney |
| Slow Motion | 时间减速 | Veo |

**构图模式库**：
| 模式 | 说明 |
|------|------|
| Rule of Thirds | 主体在交点 |
| Leading Lines | 引导线构图 |
| Frame Within Frame | 嵌套画框 |
| Symmetry | 对称构图 |

**灯光模式库**：
| 模式 | 说明 | 效果 |
|------|------|------|
| Golden Hour | 暖低角度光 | 电影感暖意 |
| Blue Hour | 冷黄昏照明 | 氛围感 |
| Rembrandt | 单光源三角高光 | 戏剧性肖像 |
| High Key | 均匀明亮 | 干净商业感 |

**场景分解指南（6步法）**：
1. 帧选择 — 定位场景切换关键帧
2. 主体分析 — 主客体的属性编目
3. 环境映射 — 场景/天气/时间
4. 运镜追踪 — 运动类型/速度/方向
5. 灯光评估 — 光源/质量/色温
6. 运动分析 — 主体运动与互动

**负面提示词参考**：
- 通用：No flickering, no morphing, no lighting inconsistency
- 平台特定：Sora（no temporal jumping）, Midjourney（no color banding）, Veo（no physics violations）

> 这个仓库直接可以补充进我们的「执笔」技能，作为分镜模式库。

---

### 🏆 Top 3：Awesome Grok Imagine Prompts（⭐ 10）

**仓库**: `YouMind-OpenLab/awesome-grok-imagine-prompts`
**价值**: ⭐⭐⭐⭐
**定位**: Grok Imagine 视频生成提示词合集，含产品风格

- 包含 **product commercial** 类别的提示词模板
- 多语言支持（中英日韩等13语言）
- 可直接提取产品广告视频的提示词模式
- 可学习其「风格标签系统」来规范我们的输出

---

### 🏆 Top 4：Ultimate Image & Video Prompt Generator（⭐ 7）

**仓库**: `DareDev256/Ultimate-Image-Video-Prompt-Generator`
**价值**: ⭐⭐⭐
**定位**: 结构化提示词构建器（13个分类 × 7000+提示）

- Next.js + TypeScript 的提示词构建器
- 支持 Nano Banana, DALL-E, Kling 三种模型
- 13个引导分类的提示生成
- 适合作为前端参考，但非核心算法

---

### 🏆 Top 5：Awesome Prompt Optimization（⭐ 16）

**仓库**: `malteos/awesome-prompt-optimization`
**价值**: ⭐⭐⭐
**定位**: 提示词工程资源大全（文本/图像/视频/多模态）

- 涵盖手动优化、自动优化、多模态提示
- 含提示词评测基准和数据集
- 作为资源索引，可定期查阅更新

---

### 🏆 Top 6：Alibaba Wan2.7 官方特性（官方）

**仓库**: `AlibabaCloud-Official/awsome-Wan2.7-video`
**价值**: ⭐⭐⭐⭐⭐（对当前项目）
**定位**: 通义万相 Wan2.7 官方特性文档

**对我们最有用的三大特性**：

| 特性 | 说明 | 对我们项目的价值 |
|------|------|----------------|
| **Creative Video Transfer** | 一键复制动态，从复杂角色动作到运镜 | ⭐⭐⭐⭐⭐ 这正是「换产品翻拍」需要的！ |
| **Instructional Video Editing** | 用文本提示+多图指导重绘场景/情节 | ⭐⭐⭐⭐ 可用文本直接指导产品替换 |
| **Motion Control** | 精确控制运动轨迹 | ⭐⭐⭐ 运镜保持 |
| **Precise Color Control** | 像素级色彩对齐 | ⭐⭐⭐⭐ 确保色调一致性 |

**结论：Wan2.7本身就支持我们要做的事**，只是我们还没用对方向——之前只用了 i2v 基础模式，应该尝试 Creative Video Transfer 的「视频→视频」模式来保留原始运镜和动态，只换产品。

---

## 三、现状 vs 目标 — 差距分析

### 我们的流程（当前）

```
爆款视频 → ffmpeg时间抽帧 → vision_analyze逐帧分析 
→ 人工撰写提示词 → Wan2.7 i2v 单图生视频 → 人工比对
```

### 目标流程（理想）

```
爆款视频 → CV智能帧选择(SSIM+光流+历史直方图) 
→ 场景分割+主体追踪 → 多轮多专家视觉分析 
→ 结构化子提示词模式库匹配 
→ Wan2.7 Creative Video Transfer 视频→视频风格迁移 
→ 只换产品，保持运镜/光线/构图一致
```

### 具体差距点

| 环节 | 当前能力 | 差距 | 优先级 |
|------|---------|------|:----:|
| 帧选择 | 时间均匀抽帧（每N秒） | 无CV智能选择 | 🔴高 |
| 场景检测 | ffmpeg阈值法 | 无直方图+光流分析 | 🔴高 |
| 运动分析 | 无 | 无法分析动态内容 | 🟡中 |
| 提示词模式库 | 零散参考文件 | 无结构化模式系统 | 🟡中 |
| 负面提示词 | 无 | 缺少质量控制 | 🟡中 |
| 视频风格迁移 | 仅用i2v基础模式 | 未用Creative Video Transfer | 🔴高 |
| 多专家分析 | 单轮视觉分析 | 无多轮多角色交叉验证 | 🟢低 |

---

## 四、行动建议

### 立即可行的（不需改代码）

1. **升级提示词模板** — 把 video-prompt-engineering-patterns 的6步分解法、运镜/灯光/构图模式库整合进执笔的参考文件
2. **在 Wan2.7 调用中加入负面提示词** — 减少画面闪烁/变形
3. **利用 Creative Video Transfer** — 先研究 Alibaba 文档中「视频→视频」的参数格式

### 需要开发的

4. **升级帧捕手** — 加入 OpenCV 的 SSIM 智能帧选择 + 直方图场景检测
5. **建立模式库** — 整理一个结构化参考文件，存 6 大运镜类型 × 6 大灯光方案 × 6 大构图模式

### 资料源

- `okaditya84/Prompt-Detective` — CV智能帧算法参考
- `duyuanchao/video-prompt-engineering-patterns` — 模式库（可直接复制使用）
- `YouMind-OpenLab/awesome-grok-imagine-prompts` — 产品提示词风格标签参考
- `AlibabaCloud-Official/awsome-Wan2.7-video` — Wan2.7高级特性文档
- `DareDev256/Ultimate-Image-Video-Prompt-Generator` — 13分类×7000+提示词模板

---

## 五、结论

**核心发现：** 我们的影墨小队流程骨架是对的，但两处关键短板：

1. **帧选择太粗糙** — 时间均匀抽帧 ≈ 盲人摸象。用 Prompt-Detective 的 CV 算法做智能帧选择，能精准抓到爆款视频的每个「高光帧」
2. **Wan2.7 我们只用了一成功力** — 它自带的 Creative Video Transfer 就是「保留原有运镜/动态/构图→只换产品」的天然工具，比 i2v 模式更适合当前需求
3. **缺少结构化模式库** — video-prompt-engineering-patterns 提供了一个很完整的6类模式×平台适配模板，可以直接拿来用

现在的差距是「知道用什么工具」但需要把工具集成到流程中。

---
*报告完*

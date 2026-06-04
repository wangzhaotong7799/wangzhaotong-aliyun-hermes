# Seedance 2.0 提示词质量标准基准

> 基于 ZeroLu/awesome-seedance + beshuaxian/higgsfield-seedance2-jineng 的实践

## 专业分镜级提示词结构

### 15秒时间线分段模板

参考 ZeroLu/awesome-seedance 的电影提示词格式（好莱坞赛车/维伦纽瓦沙漠等）：

```
Duration: 15s.

[00-05s] Shot 1: Name (景别/环境).
场景描述。光线和气氛。
Dialogue Cue: 对话或音效提示（可选）。

[05-10s] Shot 2: Name (景别/变化).
切换描述。动作和运镜变化。

[10-15s] Shot 3: Name (景别/高潮).
关键时刻。"引号动作提示"（Subtitle: 字幕内容）。
```

### 2秒钩子框架（来自 higgsfield 技能集）

开场前2秒必须抓住注意力。12种钩子模式（电商版）：

| # | 钩子 | 适用 | 手法 |
|---|------|------|------|
| 1 | Product Drop | 奢侈品 | 暗调背景，产品下降入画，运动模糊+灯光突变 |
| 2 | Texture ASMR | 美妆/面料 | 微距拍摄材质纹理，手指滑过表面 |
| 3 | Before/After | 功能型产品 | 分屏或快速转场展示改变 |
| 4 | Unboxing Reveal | 美妆/电子 | 手打开包装，产品入光 |
| 5 | Color Cascade | 多色系产品 | 产品列队旋转展示颜色变体 |
| 6 | Ingredient Explosion | 食品/护肤品 | 成分向外炸出—视觉动感 |
| 7 | Problem-Solution Snap | 功能性 | "问题"→切→"解决方案"+产品 |
| 8 | Lifestyle Aspiration | 生活方式 | 快速切到理想生活场景+产品 |

### 产品360°黄金法则

每个产品360°展示应包含：

1. **英雄角度选择** — 目标角度（如珠宝35°倾斜展示切面深度）
2. **材质叙事** — 每种材质有不同的光影语言
   - 金属：反射 = 精密/工艺
   - 玻璃/水晶：透明/折射 = 纯净/奢华
   - 皮革：纹理和光泽 = 传承/触感
3. **环境控制** — 背景/照明/反射的精确描述

## 不同平台提示词特征

| 平台 | 语言 | 风格偏好 | 特色参数 |
|------|------|---------|---------|
| Seedance 2.0 | 英文+场景标记 | 长段描述，[00-05s] 时间线格式 | 支持 `@image1` `@video1` 素材引用 |
| Kling（可灵） | 中文自然语言 | 简练，中长段 | 支持的图和开始/结束帧 |
| Runway Gen-3 | 英文 | 自然语言，强调镜头语言 | 支持 camera_shot 参数 |

## Jewelry / Diamond 专用提示词词汇

**光线词汇**：
- "Single cold spotlight from upper left 45°"
- "Chiaroscuro contrast ratio"
- "Subsurface scattering on diamonds"
- "Crushed ice effect"
- "Blue-white fire from each facet"
- "Specular highlight fidelity"

**机位词汇**：
- "Extreme close-up macro shot"
- "Ultra slow push-in"
- "Slow rotation turntable"
- "Micro push with focus pull"

**产品描述词汇**：
- "Pave setting craftsmanship"
- "Claw/prong details"
- "Diamond dispersion with rainbow flashes"
- "Multi-faceted surface catching light in sequence"
- "Brilliant refracted light with intense scintillation"

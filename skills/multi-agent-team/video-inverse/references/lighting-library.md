# 💡 灯光方案库 — 视频提示词用

## 5种基本灯光设置

| 编号 | 方案 | 英文表述 | 效果 |
|:----:|------|---------|------|
| L1 | **单束冷调聚光** | `single cold spotlight from upper left at 45°` | 戏剧性、高反差、高级感 |
| L2 | **双灯平光** | `dual softbox lighting from both sides, even illumination` | 产品展示、无阴影、清晰 |
| L3 | **窗口自然光** | `soft window light from the right, warm morning sun` | 自然、温馨、生活感 |
| L4 | **底光+顶光** | `rim light from above + fill light from below` | 立体感、神秘感 |
| L5 | **纯黑背景单光** | `single light source in complete darkness, product isolated` | 极致聚焦、高级黑 |

## 场景光源组合

### 珠宝/钻石场景
| 光源 | 方向 | 色温 | 效果 | 提示词写法 |
|------|------|:----:|------|-----------|
| 聚光灯 | 左上45° | 冷6000K | 钻石爆闪 | `single cold directional spotlight 45° upper left` |
| 补光 | 右侧柔光箱 | 中性5000K | 填充暗部 | `soft fill light from right` |
| 轮廓光 | 后方斜上 | 冷5500K | 勾勒边缘 | `cool rim light from behind creating edge definition` |

### 场景1：暗调高反差（御姐/轻奢/高级）
```
Primary: hard cold spotlight 45° upper left, creates dramatic shadow
Fill: none or minimal bounce fill from white card right
Rim: cold rim light from back-right at 30°
Result: high contrast ratio, deep shadows, product caught in single beam
Color temperature: 5500-6500K cold
```

### 场景2：柔和日光（自然/生活/温馨）
```
Primary: large soft window light from right side
Fill: natural bounce from white walls
Rim: none, rely on natural edge definition
Result: soft shadows, even skin tone, natural feel
Color temperature: 4500-5500K neutral warm
```

### 场景3：水晶灯效（奢华/晚宴/派对）
```
Primary: multiple small warm point lights (chandelier simulation)
Fill: ambient candlelight from below
Rim: cool blue from distant window
Result: multiple sparkle sources, complex refraction patterns
Color temperature: mixed - warm 3200K + cool 6500K
```

### 场景4：车内夜景（都市/时尚/冷感）
```
Primary: passing street lights from outside car (intermittent)
Fill: cool dashboard ambient blue-green
Rim: none
Result: dynamic changing light, city bokeh circles in background
Color temperature: cool blue-green 7000K + amber street lights 3000K
```

### 场景5：咖啡馆暖光（休闲/生活/质感）
```
Primary: warm desk lamp directional from left
Fill: ambient café lighting from behind
Rim: none
Result: warm skin tones, soft shadows, intimate feel
Color temperature: warm 3200K
```

## 灯光可写关键词表

| 中文 | 英文提示词 | 效果 |
|------|-----------|------|
| 硬光 | `hard light` | 明暗分界清晰，戏剧化 |
| 柔光 | `soft light / diffused light` | 阴影柔和，过渡自然 |
| 侧光 | `side lighting` | 强调轮廓和纹理 |
| 逆光 | `backlight / rim light` | 勾勒边缘，分离背景 |
| 顶光 | `top light` | 神秘感，强调立体感 |
| 底光 | `underlight` | 恐怖/未来感（慎用） |
| 混合光 | `mixed lighting` | 复杂场景，真实感 |
| 高反差 | `high contrast lighting / chiaroscuro` | 戏剧性，高级感 |
| 低反差 | `low contrast / soft even lighting` | 温柔，柔和 |
| 冷调 | `cool tone / cold white light / 6000K` | 清冷，高级 |
| 暖调 | `warm tone / golden light / 3200K` | 温馨，亲密 |
| 斑驳光 | `dappled light` | 透过树叶的光影 |
| 聚光 | `spotlight / focused beam` | 聚焦主体，戏剧性 |
| 扩散光 | `diffused light` | 大面积柔和照明 |
| 伦勃朗 | `Rembrandt lighting` | 经典人像布光 |
| 蝴蝶光 | `butterfly lighting` | 好莱坞女星质感 |
| 环形光 | `loop lighting` | 自然立体感 |
| 分割光 | `split lighting` | 一半亮一半暗，强烈戏剧感 |

## 情绪与灯光匹配

| 情绪 | 推荐灯光方案 |
|------|-------------|
| 清冷高贵 | 单束冷调聚光L1 + 高反差 |
| 温暖亲切 | 窗口自然光L3 + 低反差 |
| 奢华闪耀 | 水晶灯效L1+L4混合 + 多折射 |
| 都市时尚 | 车内夜景方案 + 冷调 |
| 生活日常 | 咖啡馆暖光方案 |
| 神秘暗黑 | 纯黑背景单光L5 + 底光 |
| 高级极简 | 双灯平光L2 + 中性色温 |

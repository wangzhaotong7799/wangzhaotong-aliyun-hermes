# Seedance 2.0 提示词质量基准

> 本文件记录用户实际确认的高质量标准，作为执笔交付的参照基准。
> 来源：2026-05-12 钻石戒指冷调御姐风故事板

## 每条提示词的必须元素

| 元素 | 必须在提示词中出现 | 检查方式 |
|------|:-----------------:|:---------:|
| 光线(方向/类型/色温) | ✅ | 搜索方向词+色温词 |
| 运镜(景别/运动) | ✅ | 搜索"push/pull/zoom/track/cut" |
| 产品细节(材质/光相互作用) | ✅ | 搜索"facet/sparkle/refract/scatter" |
| 情绪/氛围标签 | ✅ | 参见注释行 |
| 色彩描述(HEX或颜色词) | ✅ | 搜索"#HEX"或颜色名 |
| Negative prompt(可选) | ⚠️ | 特殊风格需要 |

## 合格示例 vs 不合格示例

### ❌ 不合格（我原来出的）
```
暖色调，浅景深，手举着戒指展示
```
**问题**：
- 无光线方向/色温
- 无运镜描述
- 无产品与光线相互作用
- 无情绪标签
- 太笼统，换任何产品都能用

### ✅ 合格标准（用户给的参照）
```
暗调光影反差特写，一只手从阴影里缓缓伸出，
冷调聚光灯突然打在戒指上，碎钻瞬间爆闪，
镜头聚焦戒指的满钻切面，光影在钻石上流动
```
**达标原因**：
- 光线：暗调反差 + 冷调聚光灯 + 瞬间爆闪
- 运镜：特写 + 镜头聚焦
- 产品细节：满钻切面 + 光影在钻石上流动
- 情绪：冷调、御姐气场
- 时间：0-3秒精确

### 🎯 优秀级（我重写的）
```
Dark ambient room, extreme close-up macro shot of elegant hand slowly emerging
from deep shadow, single cold spotlight hits diamond ring — diamonds EXPLODE with
brilliant refracted light. Slow motion, light traces across multi-faceted diamond
surface. Dark background 80% black, cold spotlight upper left 45°. Chiaroscuro
contrast. Ultra realistic texture on diamond surface.
Style: High-end jewelry commercial, cold luxury aesthetic, editorial fashion
Camera: Macro extreme close-up, slow push in, shallow depth of field (f/1.4)
Lighting: Single cold directional spotlight, high contrast, dark shadows
Mood: Mysterious, elegant, powerful, captivating
Color: Cool white (#E8E8F0) silver (#C0C0D0), deep black background
```

## 常见问题自查表

提交前逐项检查：

- [ ] 每段都写清**光线方向**（左上45°/顶光/侧光/逆光/底光）了吗？
- [ ] 每段都写清**光源类型**（聚光灯/柔光箱/自然光/烛光/路灯）了吗？
- [ ] 每段都写清**色温**（冷调/暖调/中性）了吗？
- [ ] 每段都写清**镜头运动**（推/拉/摇/移/跟/固定/闪切）了吗？
- [ ] 每段都写清**景别**（极近景微距/近景/中近景/中景/全景）了吗？
- [ ] 产品描述包含**光线在材质表面**的相互作用描述吗？（折射/散射/反射/爆闪/火光/流动）
- [ ] 情绪描述不在一个词打住，而是有**复合标签**吗？（如"温暖、亲切、精致、生活化"）
- [ ] 时间粒度不超过**5秒**，关键段**3秒**精度吗？
- [ ] 如有多场景，每个场景有独立的**切换节点标注**吗？

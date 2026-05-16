# Pillow 封面图片编辑参考

> 用户提供参考图（如可灵AI生成的封面）时，用Pillow进行编辑处理的工作流

## 核心原则

**Pillow画的封面永远不如用户提供的AI生成图。** 用户说"太丑了"之后，改用可灵AI 3.0生成的封面直接做背景，通过验收。

## 完整编辑流程（最终验收版）

```python
from PIL import Image, ImageDraw

img = Image.open('kelin_cover.jpg')

# 1. RGBA → RGB（可灵AI图常见）
if img.mode == 'RGBA':
    bg = Image.new('RGB', img.size, (0, 0, 0))
    bg.paste(img, mask=img.split()[3])
    img = bg

W, H = img.size
draw = ImageDraw.Draw(img)

# 2. 删除右下角水印（位置：80-98%, 96-99%）
draw.rectangle((int(W*0.78), int(H*0.94), W, H), fill=(0, 0, 0))

# 3. 裁剪核心区域（夜伴低语+白色边框）
# 范围：左25% 上14% 右75% 下82%
crop = img.crop((int(W*0.25), int(H*0.14), int(W*0.75), int(H*0.82)))
cw, ch = crop.size

# 4. 缩放到50%（用户说"再缩"→从67%→50%通过）
new_w = int(cw * 0.50)
new_h = int(ch * 0.50)
crop_resized = crop.resize((new_w, new_h), Image.LANCZOS)

# 5. 合成到纯黑背景，位置15%高度（居中→8%→"太靠上"→20%→"好"→最终15%）
result = Image.new('RGB', (W, H), (0, 0, 0))
paste_x = (W - new_w) // 2
paste_y = int(H * 0.15)
result.paste(crop_resized, (paste_x, paste_y))

result.save('output.jpg', quality=95)
```

## 缩放适应视频尺寸（1080×1920）

```python
target_w, target_h = 1080, 1920
scale = target_h / src_h
new_w = int(src_w * scale)
img_resized = img.resize((new_w, new_h), Image.LANCZOS)
if new_w > target_w:
    left = (new_w - target_w) // 2
    img_cropped = img_resized.crop((left, 0, left + target_w, target_h))
else:
    img_cropped = Image.new('RGB', (target_w, target_h), (0, 0, 0))
    left = (target_w - new_w) // 2
    img_cropped.paste(img_resized, (left, 0))
img_cropped.save('1080x1920.jpg', quality=95)
```

## 经验参数速查

| 操作 | 参数 | 说明 |
|:---|:---:|:---|
| 水印区域 | 左下80%/96% 到右下角 | 可灵AI水印典型位置 |
| 核心区域裁剪 | 25%-14%-75%-82% | 夜伴低语+白色边框范围 |
| 缩放比例 | **50%** | 从100%→67%→"再缩"→50%→通过 |
| 纵向位置 | **15%** 高度 | 居中→8%→"太靠上"→20%→"好"→最终15% |
| 缩放到视频 | 填高度→居中裁宽 | 1472x2944 → 1080x1920 |

## Pillow避坑

1. `Image.fromarray()` 需要 numpy 数组，不能传 list → 用 `Image.new('L', size).putdata(list)` 替代
2. 暗角遮罩不要用 `Image.fromarray`：
   ```python
   v_data = list(vignette.getdata())
   max_v = max(max(rgb) for rgb in v_data) or 255
   mask_data = [int(255 - max(rgb) * 0.5 / max_v * 255) for rgb in v_data]
   mask_img = Image.new('L', (width, height))
   mask_img.putdata(mask_data)
   ```
3. `getdata()` 在 Pillow 14 (2027-10) 将移除，届时用 `get_flattened_data()`
4. RGBA→RGB转换要带mask参数：`background.paste(img, mask=img.split()[3])`
5. LANCZOS 缩放滤镜效果最好

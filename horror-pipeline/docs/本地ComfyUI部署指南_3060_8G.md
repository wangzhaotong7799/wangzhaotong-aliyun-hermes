# 🎬 夜伴低语 — 本地 ComfyUI + AnimateDiff 部署指南

> **适用硬件：** RTX 3060 8G + 32GB 内存 + Windows
> **目标：** 用 AI 让静态场景图动起来——人走进门、拿手机、走路、转头的连贯动画

---

## 📦 需要下载的东西（全免费）

| # | 名称 | 大小 | 用途 | 下载地址 |
|:--|:-----|:----:|:-----|:---------|
| 1 | **ComfyUI 整合包** | ~2GB | 主程序，解压即用 | [点此下载](https://github.com/comfyanonymous/ComfyUI/releases) → 找 `ComfyUI_windows_portable_nvidia.7z` |
| 2 | **Git** | ~50MB | 装插件用 | [点此下载](https://git-scm.com/download/win) → 一路默认安装 |
| 3 | **SD1.5 基座模型** | ~2GB | 图片生成基础 | [Realistic Vision V5.1](https://civitai.com/models/4201/realistic-vision-v51) → 下 `realisticVisionV51_v51VAE.safetensors` |
| 4 | **AnimateDiff 运动模块** | ~800MB | 让图动起来 | [点此下载](https://huggingface.co/guoyww/animatediff/blob/main/mm_sd_v15_v2.ckpt) |
| 5 | **ControlNet OpenPose**（选装） | ~1.5GB | 精确控制人物姿势 | [点此下载](https://huggingface.co/lllyasviel/ControlNet-v1-1/blob/main/control_v11p_sd15_openpose.pth) |

---

## 🚀 安装步骤

### Step 1 — 解压 ComfyUI

1. 把下载的 `ComfyUI_windows_portable_nvidia.7z` 解压到 `D:\ComfyUI\`
   > ⚠️ **千万别放 C 盘**，模型文件很大
2. 双击 `D:\ComfyUI\run_nvidia_gpu.bat`
   - 第一次启动会下载 Python 和依赖包，等它跑完（约 3-5 分钟）
   - 浏览器自动打开 `http://127.0.0.1:8188`
   - 看到灰色的节点界面 = 成功 ✅

### Step 2 — 安装 ComfyUI Manager（插件管理器）

打开终端（CMD 或 PowerShell，右键「以管理员运行」）：

```cmd
cd /d D:\ComfyUI\custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
```

关掉 ComfyUI 窗口，重新双击 `run_nvidia_gpu.bat` 启动。
浏览器右下角多出 **Manager** 按钮 = 安装成功 ✅

### Step 3 — 安装 AnimateDiff 插件

1. 浏览器点右下角 **Manager** 按钮
2. 点 **Install Custom Nodes**
3. 搜索框输入 `AnimateDiff`
4. 找到 **ComfyUI-AnimateDiff-Evolved** → 点 Install
5. 关掉 ComfyUI，重启

### Step 4 — 放模型文件

把下载的模型文件放到对应目录：

```
D:\ComfyUI\
├── models\
│   ├── checkpoints\
│   │   └── realisticVisionV51_v51VAE.safetensors    ← SD1.5 基座模型
│   ├── animatediff_models\
│   │   └── mm_sd_v15_v2.ckpt                        ← 运动模块
│   └── controlnet\
│       └── control_v11p_sd15_openpose.pth            ← OpenPose（选装）
```

> 💡 没有的文件夹就自己新建

### Step 5 — 验证安装

重启 ComfyUI，看左下角是否显示：
- ✅ `ComfyUI-AnimateDiff-Evolved: 已加载`
- ✅ `ComfyUI-Manager: 已加载`

都显示 = 部署完成 🎉

---

## 🎬 跑第一个动画视频

### 方法一：导入我的工作流（推荐）

复制下面的 JSON，保存为 `workflow.json`，然后拖进 ComfyUI 窗口：

> ⚠️ 由于 JSON 太长，我会在确认你装好后单独生成发给你的飞书

### 方法二：手动搭建（5 个节点）

拖一个最简单的测试工作流：

```
1.  Load Checkpoint → 选 realisticVisionV51
        ↓
2.  AnimateDiff Loader → 选 mm_sd_v15_v2.ckpt
        ↓
3.  KSampler → steps=20, CFG=7, sampler=euler, scheduler=normal
        ↓
4.  Empty Latent Image → width=768, height=1152, batch_size=16
        ↓
5.  VAEDecode → 连接输出
        ↓
6.  Video Combine → format=mp4, fps=8
```

### 测试 Prompt（复制粘贴）

正面词：
```text
(masterpiece, best quality, photorealistic:1.2), 1man, chinese doctor,
white coat, sitting at desk, holding a pen, looking at medical record,
dim hospital office lighting, moody atmosphere
```

负面词：
```text
(worst quality, low quality:1.4), badhand, extra fingers, distorted face,
blurry, jpeg artifacts, swimming, jittery, oversaturated
```

### 输出设置

- **帧数：** 16 帧（约 2 秒，测试用）
- 正式做每张图建议 **32 帧 × 8fps = 4 秒**
- **CFG：** 7~8（太高会闪）
- **步数：** 20~25

---

## ⏱ 生成速度参考（RTX 3060 8G）

| 分辨率 | 帧数 | 时长 | 耗时 |
|:-----|:---:|:----:|:---:|
| 768×1152 | 16帧 | 2秒 | ~2分钟 |
| 768×1152 | 32帧 | 4秒 | ~4分钟 |
| 768×1152 | 48帧 | 6秒 | ~6分钟 |

> 💡 8G 显存 ≈ 6 分钟出 1 张 4 秒动画，9 张全出约 **50 分钟**

---

## 📤 上传到服务器 + 我合成完整视频

你在本地跑完每张图的动画 MP4 后，按这个命名：

```
scene_01_anim.mp4
scene_02_anim.mp4
...
scene_09_anim.mp4
```

**上传到这台服务器：**

```cmd
scp D:\ComfyUI\output\scene_*.mp4 root<服务器IP>:/root/wangzhaotong-hermes/horror-pipeline/images/
```

我收到后自动合成：动画片段 + 配音 + BGM + 字幕 + 封面片头 → 飞书发给你

---

## ❓ 常见问题

**Q: ComfyUI 打不开 / 报错？**
→ 打开 `D:\ComfyUI\run_nvidia_gpu.bat` 看错误信息，截图发我

**Q: 生成的人脸崩了？**
→ 加负面词 `bad hand, extra fingers, distorted face`
→ 或用 [ADetailer 插件](https://github.com/Bing-su/adetailer) 修复人脸

**Q: 闪屏严重 / 画面一跳一跳？**
→ 降低 CFG 到 7
→ 加 AnimateDiff 的 **Motion Scale** 节点，设为 1.0~1.5
→ 帧数越多越平滑（32 帧起步）

**Q: 显存不够？**
→ 降低分辨率到 640×960
→ batch_size 设为 8 而不是 16
→ 关掉其他程序

---

> 📍 文档路径（服务器）：`/root/wangzhaotong-hermes/horror-pipeline/docs/本地ComfyUI部署指南_3060_8G.md`
> 
> 有任何问题截图发我，远程帮你看

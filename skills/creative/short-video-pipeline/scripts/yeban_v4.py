#!/usr/bin/env python3
"""
夜半低语 - 恐怖故事短视频生成器 v4
===============================
仿张震讲故事风格:
  1. edge-tts整段配音 + FFmpeg音高下移沙哑处理
  2. 四段式动态BGM (铺垫→紧张→高潮→收尾)
  3. 暗黑辐射渐变背景
  4. drawtext逐句字幕 (56px, 白字黑边)
  5. 3秒封面片头 (大字标题+品牌水印)

用法:
  python3 yeban_v4.py --story stories/xxx.txt --title "标题"
  
依赖:
  pip3 install edge-tts pillow numpy
  dnf install ffmpeg wqy-microhei-fonts
"""
# (完整源码见 /root/wangzhaotong-hermes/horror-pipeline/scripts/yeban_v4.py)

#!/usr/bin/env python3
"""
通义万相 文生图工具 — 给画师用
=====================
调用阿里云百炼API生成暗黑漫画风图片

用法:
  python wanx_image_gen.py --prompt "深夜坟场, 孤零零的木屋"
  python wanx_image_gen.py --prompt "鬼魂掐脖子" --output scene_01.jpg
  python wanx_image_gen.py --batch prompts.txt  # 批量生成

输出: 1080x1920 竖版PNG/JPG
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

# ─── 配置 ───────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = PROJECT_DIR / "images"

# 固定风格前缀（所有图片统一）
STYLE_PREFIX = (
    "黑白漫画, 粗线条勾边, 高对比光影, 电影构图, "
    "暗黑恐怖风格, 少量红色血迹点缀, "
    "黑白为主红色为辅"
)

# 阿里云百炼API
API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
POLL_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{}"


def get_api_key() -> str:
    """从 .hermes/.env 读取 API Key"""
    env_paths = [
        Path("/root/.hermes/.env"),
        Path.home() / ".hermes" / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.startswith("ALIYUN_BAILIAN_API_KEY"):
                        return line.split("=", 1)[1].strip().strip("'\"")
    # fallback: 环境变量
    key = os.environ.get("ALIYUN_BAILIAN_API_KEY", "")
    if key:
        return key
    print("❌ 未找到 ALIYUN_BAILIAN_API_KEY")
    sys.exit(1)


def build_prompt(scene_desc: str) -> str:
    """组装最终提示词 = 固定风格 + 场景描述"""
    if scene_desc.startswith(STYLE_PREFIX):
        return scene_desc  # 已经包含风格前缀
    return f"{STYLE_PREFIX}, {scene_desc}"


def generate_one(prompt: str, output_path: Path = None,
                 max_polls: int = 60, poll_interval: int = 5) -> str:
    """单次文生图
    返回: 图片文件路径
    """
    api_key = get_api_key()
    final_prompt = build_prompt(prompt)

    if output_path is None:
        output_path = IMAGES_DIR / f"scene_{int(time.time())}.jpg"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"  🎨 通义万相生成中...")
    print(f"     提示词: {final_prompt[:80]}...")

    # 1. 异步提交
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    payload = {
        "model": "wanx-v1",
        "input": {"prompt": final_prompt},
        "parameters": {"size": "768*1152", "n": 1},  # 3:4竖版，后处理缩放到1080x1920
    }

    resp = requests.post(API_URL, headers=headers, json=payload, timeout=10)
    data = resp.json()

    # 检查直接结果（同步模式有时会直接返回）
    results = data.get("output", {}).get("results", [])
    if results:
        img_url = results[0]["url"]
        _download(img_url, output_path)
        print(f"  ✅ {output_path.name} ({output_path.stat().st_size // 1024}KB)")
        return str(output_path)

    # 异步模式：轮询
    task_id = data.get("output", {}).get("task_id", "")
    if not task_id:
        print(f"  ❌ 提交失败: {json.dumps(data, ensure_ascii=False)[:200]}")
        return ""

    for i in range(max_polls):
        time.sleep(poll_interval)
        poll_resp = requests.get(
            POLL_URL.format(task_id),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        poll_data = poll_resp.json()
        status = poll_data.get("output", {}).get("task_status", "")

        if i % 3 == 0 or status in ("SUCCEEDED", "FAILED"):
            dots = "." * ((i % 6) + 1)
            print(f"     等待{dots} {status} ({i * poll_interval}s)")

        if status == "SUCCEEDED":
            results = poll_data.get("output", {}).get("results", [])
            if results:
                img_url = results[0]["url"]
                _download(img_url, output_path)
                print(f"  ✅ {output_path.name} ({output_path.stat().st_size // 1024}KB)")
                return str(output_path)
            else:
                print(f"  ⚠️ 成功但无结果: {json.dumps(poll_data, ensure_ascii=False)[:200]}")
                return ""
        elif status == "FAILED":
            msg = poll_data.get("output", {}).get("message", "未知错误")
            print(f"  ❌ 生成失败: {msg}")
            return ""

    print(f"  ⏰ 超时（{max_polls * poll_interval}s）")
    return ""


def generate_batch(prompts: list, output_dir: Path = None,
                   prefix: str = "scene") -> list:
    """批量生成多张图
    prompts: [(prompt, filename_or_None), ...] 或 [prompt, ...]
    返回: [(input_prompt, output_path_or_empty), ...]
    """
    if output_dir is None:
        output_dir = IMAGES_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, item in enumerate(prompts, 1):
        if isinstance(item, str):
            prompt = item
            filename = f"{prefix}_{i:02d}.jpg"
        else:
            prompt, filename = item
            if filename is None:
                filename = f"{prefix}_{i:02d}.jpg"

        output_path = output_dir / filename
        print(f"\n[{i}/{len(prompts)}] {filename}")

        result = generate_one(prompt, output_path)
        results.append((prompt, result))

    return results


def _download(url: str, save_path: Path):
    """下载图片到本地"""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    save_path.write_bytes(resp.content)


def main():
    parser = argparse.ArgumentParser(description="通义万相文生图工具")
    parser.add_argument("--prompt", "-p", help="场景描述（不加风格前缀）")
    parser.add_argument("--output", "-o", help="输出文件名（默认 scene_时间戳.jpg）")
    parser.add_argument("--batch", "-b", help="批量提示词文件（每行一个prompt）")
    args = parser.parse_args()

    if args.batch:
        # 批量模式
        with open(args.batch) as f:
            prompts = [line.strip() for line in f if line.strip()]
        print(f"📦 批量生成 {len(prompts)} 张图...")
        results = generate_batch(prompts)
        success = sum(1 for _, r in results if r)
        print(f"\n✅ 完成: {success}/{len(prompts)} 张成功")
        return

    if args.prompt:
        output = None
        if args.output:
            output = IMAGES_DIR / args.output
        result = generate_one(args.prompt, output)
        if result:
            print(f"\n✅ 图片: {result}")
        else:
            print(f"\n❌ 生成失败")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

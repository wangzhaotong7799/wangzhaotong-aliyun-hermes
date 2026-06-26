#!/usr/bin/env python3
"""韭圈儿恐贪指数采集脚本

从 funddb.cn/meta_info/toolfear.json 获取 SEO 信息（验证连通性）
从 api.jiucaishuo.com/v2/kjtl/getbasedata 获取加密的恐贪指数数据并解密

用法:
  python3 jiucai_fear_index.py           # 输出完整 JSON
  python3 jiucai_fear_index.py --simple  # 只输出 "72 贪婪"

依赖: pip install pycryptodome requests
"""

import base64
import json
import sys
import requests
from Crypto.Cipher import AES

# ===== 解密参数（从 JS 源码逆向） =====
K_A = "bvroqevdjqibsdkq"      # 也是 IV 的组成部分
K_B = "eveqocftukbotqjcequcnkrqlw1oi"  # 也是 Key 的组成部分


def decrypt_response(encrypted_b64: str) -> dict:
    """
    解密 api.jiucaishuo.com 返回的 AES-256-CBC 加密数据
    
    JS 端 monkey-patch 链:
      1. Utf8.parse 对输入追加 "1"
      2. AES.decrypt 对 key 追加 "ll", 对 iv 追加 "ll"
      所以实际使用的 key = K_B + "ll1", iv = K_A + "ll1"
    """
    key_material = (K_B + "ll1").encode("utf-8")   # 32 bytes
    iv_material = (K_A + "ll1").encode("utf-8")     # 19 bytes
    
    # AES-256 需要 32 字节 key, 16 字节 iv
    key = key_material[:32]
    iv = iv_material[:16]
    
    # 修复 base64 填充
    padding = 4 - len(encrypted_b64) % 4
    if padding != 4:
        encrypted_b64 += "=" * padding
    
    decoded = base64.b64decode(encrypted_b64)
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(decoded)
    
    # PKCS7 去填充
    pad_len = decrypted[-1]
    if 1 <= pad_len <= 16:
        decrypted = decrypted[:-pad_len]
    
    return json.loads(decrypted.decode("utf-8"))


def fetch_fear_index() -> dict:
    """获取并解密韭圈儿恐贪指数"""
    
    # 先调 SEO 接口（验证连通性）
    seo_resp = requests.get(
        "https://funddb.cn/meta_info/toolfear.json",
        headers={
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://funddb.cn/",
        },
        timeout=10,
    )
    seo_resp.raise_for_status()
    
    # 调加密数据接口
    data_resp = requests.get(
        "https://api.jiucaishuo.com/v2/kjtl/getbasedata",
        headers={
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://funddb.cn/",
            "Origin": "https://funddb.cn",
        },
        timeout=10,
    )
    data_resp.raise_for_status()
    
    # 解析响应（是个 JSON 字符串，包含 base64 数据）
    encrypted_b64 = data_resp.json()
    
    return decrypt_response(encrypted_b64)


def main():
    result = fetch_fear_index()
    
    if "--simple" in sys.argv:
        # 简洁输出: "72 贪婪"
        data = result.get("data", {})
        num = data.get("num", "?")
        status = data.get("status_str", "?")
        print(f"{num} {status}")
    else:
        # 完整输出
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

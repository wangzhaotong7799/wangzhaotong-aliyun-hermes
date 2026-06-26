# 韭圈儿恐贪指数 API 反向工程记录

> 记录日期：2026-06-26 | 最后验证：2026-06-26 | 状态：已可用

## 总览

| 项目 | 值 |
|:--|:--|
| 数据源 | 韭圈儿 (funddb.cn) -- 基于A股六大情绪因子 |
| 接口 | GET https://api.jiucaishuo.com/v2/kjtl/getbasedata |
| 认证 | need_login: false -- 无需登录 |
| 加密 | AES-256-CBC/PKCS7, 响应体是 JSON 字符串内含 base64 密文 |
| 采集脚本 | ~/.hermes/scripts/jiucai_fear_index.py |
| 用户偏好 | 以此数据源为准, 替代 alternative.me 的 CNN Fear & Greed Index |

## 接口链路

步骤1 -- 连通性验证:
  GET https://funddb.cn/meta_info/toolfear.json -> SEO JSON (title/desc/keywords)
  状态: 200, Content-Type: application/json

步骤2 -- 加密数据获取:
  GET https://api.jiucaishuo.com/v2/kjtl/getbasedata
  Headers: Accept: application/json, Referer: https://funddb.cn/, Origin: https://funddb.cn
  -> 返回 JSON 字符串: "SYLnjmR3umL/..." (base64 密文)
  状态: 200, is_jm: true (需解密)

步骤3 -- AES-256-CBC 解密(见下方)

## 解密参数

来自 funddb.cn/static/js/app.*.js (webpack 打包主 JS)

两个魔数常量:
  K_A = "bvroqevdjqibsdkq"  (即 k.a)
  K_B = "eveqocftukbotqjcequcnkrqlw1oi"  (即 k.b)

### CryptoJS monkey-patch 链

补丁1 -- AES.decrypt 对 key 和 iv 追加 "ll":
  e = Utf8.parse(key + "ll")
  n.iv = Utf8.parse(iv + "ll")

补丁2 -- Utf8.parse 对输入追加 "1":
  Utf8.parse(t) -> orig_Utf8.parse(t + "1")

实际效应: key = K_B + "ll1" (32 bytes), iv = K_A + "ll1" (取前16 bytes)

### 简化参数

Key  = K_B + "ll1" = "eveqocftukbotqjcequcnkrqlw1oill1"[:32]
IV   = K_A + "ll1" = "bvroqevdjqibsdkqll1"[:16]
算法 = AES-256-CBC/PKCS7

### Python 解密核心

```python
key = (K_B + "ll1").encode("utf-8")[:32]
iv = (K_A + "ll1").encode("utf-8")[:16]
# base64 decode -> AES decrypt -> PKCS7 unpadding -> json.loads
# result["data"]["num"] -> 72 (数值)
# result["data"]["status_str"] -> "贪婪" (标签)
```

## API 响应格式

```json
{
  "code": 0,
  "message": "请求成功",
  "data": {
    "current_time": "2026-06-25",
    "num": 72,
    "status_str": "贪婪",
    "list": [
      {"name": "1日前", "status_str": "中立", "data": {"series": [{"data": 0.41}]}},
      {"name": "1周前", "status_str": "贪婪", "data": {"series": [{"data": 0.74}]}},
      {"name": "1月前", "status_str": "贪婪", "data": {"series": [{"data": 0.71}]}},
      {"name": "1年前", "status_str": "中立", "data": {"series": [{"data": 0.68}]}}
    ],
    "target_details": {
      "target_list": [
        {"name": "指数波动", "is_complete": 1},
        {"name": "总成交量", "is_complete": 1},
        {"name": "股价强度", "is_complete": 1},
        {"name": "升贴水率", "is_complete": 1},
        {"name": "避险天堂", "is_complete": 1},
        {"name": "杠杆水平", "is_complete": 1}
      ]
    }
  }
}
```

## 分类阈值

0-24 极恐 | 25-44 恐惧 | 45-55 中性 | 56-74 贪婪 | 75-100 极贪

## 方法论要点

反向工程 SPA 加密 API 的可行路径:
1. 下载页面 JS 包 -> grep API 域名 (api.jiucaishuo.com)
2. 找到 H5 子域名 -> 分析页面路由 (h5.jiucaishuo.com)
3. 用户在已登录浏览器 F12 Network 截图 -> OCR 提取请求名和 URL
4. 从 JS grep is_jm -> 发现加密机制
5. 在 JS 中搜索 AES.decrypt -> 追踪 monkey-patch + key/IV 来源
6. 还原出完整的解密链路

工具链: curl -> grep -oP -> pytesseract -> CryptoJS monkey-patch 逆向

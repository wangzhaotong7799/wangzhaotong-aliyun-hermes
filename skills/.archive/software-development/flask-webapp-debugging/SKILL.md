---
name: flask-webapp-debugging
description: "Systematic debugging workflow for Flask web applications showing wrong data or missing results"
aliases:
  - flask-app-debugging
  - web-application-troubleshooting
tags:
  - debugging
  - flask
  - troubleshooting
---

# Flask 应用系统性调试指南

## 概述
当 Flask 应用出现显示异常、数据错误或功能失效时，按此流程进行系统性排查。本方法强调**先验证数据流再修改代码**，避免盲目猜测。

## 适用场景
- 数据显示异常（如"没有找到数据"但实际有数据）
- 前后端数据不一致
- 筛选条件导致的数据丢失
- 页面功能失效但 API 正常

## 调试流程

### 1. 验证后端 API 数据流

直接调用 API 端点验证数据是否正常返回：

```bash
# 保存响应到文件
curl -s "API_ENDPOINT" > /tmp/test.json

# 检查文件大小和格式
wc -c /tmp/test.json
head -c 500 /tmp/test.json
```

**关键点**：先用 API 工具验证数据，排除数据库或后端逻辑问题。

### 2. 使用 Python 分析数据结构

```python
import json

with open('/tmp/test.json', 'r') as f:
    data = json.load(f)

print(f"总记录数：{len(data)}")

# 统计关键状态
status_count = {}
for p in data[:100]:
    status = p.get('key_field', '')
    status_count[status] = status_count.get(status, 0) + 1

print("状态统计:", status_count)
```

**关键点**：用脚本验证数据是否符合预期，确认是数据问题还是展示问题。

### 3. 定位前端错误提示来源

```bash
# 搜索错误提示信息在哪个文件
grep -r "error message" /path/to/project/ --include="*.html" --include="*.js"

# 定位相关代码行
grep -n "elementId\|error text" index.html | head -30
```

**关键点**：从用户看到的错误信息反向追踪代码位置。

### 4. 追踪数据筛选逻辑

```bash
# 查找相关的 JavaScript 函数
grep -n "loadFunctionName\|filter-param" index.html

# 查看默认值设置
grep -A10 "formElement.value" index.html
```

**常见问题点**：
- 页面加载时自动设置的默认筛选值
- 隐藏的计算逻辑影响数据过滤
- 时间戳格式不匹配

### 5. 识别隐蔽的逻辑错误

**典型案例**：页面初始化代码自动设置错误的筛选范围

```javascript
// ❌ 错误示例
const today = new Date();
threeDaysLater.setDate(today.getDate() + 3);
startDate.value = today.toISOString().split('T')[0];
endDate.value = threeDaysLater.toISOString().split('T')[0];

// 结果：只显示最近 3 天的数据，而非所有需要的数据
```

**排查技巧**：
- 检查 `DOMContentLoaded` 或 `window.onload` 事件
- 查找页面初始化时设置的任何表单默认值
- 验证默认值是否与应用逻辑一致

### 6. 修复与同步

```bash
# 如果项目有多个静态文件副本，需要同步修改
find . -name "index.html" -type f
ls path/to/project/static/*.html

# 逐文件 patch 或使用 sed 批量修改
```

### 7. 验证修复效果

用浏览器访问页面，清除缓存后重新加载测试。

## 经验总结

### 常见陷阱
1. **默认值误导**：表单默认值可能导致看似正常的筛选条件实际上排除了大部分数据
2. **多文件副本**：静态文件可能在多个位置存在副本，需全部更新
3. **浏览器缓存**：HTML/CSS/JS 修改后需要强制刷新 (Ctrl+F5)
4. **时间计算错误**：前端时间和后端时间的解析可能不一致
5. **Gunicorn 进程缓存静态文件**：修改 `static/js/` 或 `static/css/` 后，Flask 开发服务器自动刷新，但 **gunicorn 需要 restart** 才能加载新文件。修改完后 `systemctl restart your-service`，否则 curl 看到的是旧内容。测试时不要只看本地文件，要用 `curl SERVER_URL/static/js/xxx.js` 确认线上版本。
6. **双层登录门控（搜索控件被禁 + 搜索参数被锁）**：这是一个常见但容易漏掉的模式。表单控件可能在 HTML/JS 中被 `disabled`，同时 JS 的搜索参数也被 `if (isLoggedIn)` 包裹。修复时必须同时解除两把锁：\n   - **第一层（DOM 禁用）**：`pageLoaders` 或 `DOMContentLoaded` 里的 `el.disabled = !isLoggedIn` 循环\n   - **第二层（参数封锁）**：`loadPrescriptions()` 或搜索函数里的 `if (isLoggedIn) { ... 读取搜索参数 ... }`\n   - **注意：不要一刀切全放开**。把全部搜索参数移出 `if (isLoggedIn)` 可能导致未登录用户看到异常数据（如日期范围过滤错误）。应当**选择性开放**：仅把需要的参数（如 `assistant`）移出，其余参数保持原样。即登录用户走完整逻辑，未登录用户只走精简分支。\n   - 排查步骤：\n     1. 检查页面加载器（`pageLoaders['xxx']` 或 `DOMContentLoaded`）里是否有禁用控件的代码\n     2. 检查搜索/筛选函数里搜索参数是否被 `isLoggedIn` 包裹\n     3. 用 `curl 'API_URL?assistant=xxx'` 单独验证后端 API 是否支持未登录请求\n     4. 如需选择性开放（如仅开放医助搜索），从禁用列表里移除该控件 ID + 在 else 分支加对应参数

### 调试口诀
- 先看 API 再看页
- 搜错文找源头
- 追逻辑查默认
- 修多处要同步
- 清缓存再验证
- 改静态需重启
- 双锁控要两端解

## 参考案例

**复诊管理页面显示空的问题**（2026-04-24）
- 症状：显示"没有找到符合条件的患者"
- 真相：API 返回 3146 条数据，但前端默认筛选最近 3 天取药的记录
- 根因：页面初始化代码错误地设置了 start_date=today, end_date=today+3
- 解决：清空默认值，让用户自主选择或查询全部
- 教训：检查所有初始化代码中的默认值设置

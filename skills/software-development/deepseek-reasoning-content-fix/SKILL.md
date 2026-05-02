---
name: deepseek-reasoning-content-fix
description: Fix DeepSeek v4-flash reasoning_content API compatibility issue
aliases:
  - deepseek-thinking-mode-fix
  - openrouter-reasoning-content-handling
related_skills: []
tags:
  - flask
  - deepseek
  - openrouter
  - api-compatibility
---

# DeepSeek V4-Flash `reasoning_content` Bug 修复指南

## 问题概述

使用 **DeepSeek v4-flash** 模型时遇到 HTTP 400 错误：

```json
{
  "error": {
    "message": "The `reasoning_content` in the thinking mode must be passed back to the API.",
    "type": "invalid_request_error"
  }
}
```

即使配置了 `reasoning_config.enabled: false`，API 服务端仍强制返回 `reasoning_content` 字段。

## 根本原因分析

### 技术细节

1. **服务端强制开启思考模式**  
   DeepSeek v4-flash 在服务器端强制启用 thinking 模式，返回包含特殊格式/加密数据的 `reasoning_content` 字段。

2. **签名/元数据需要原样传回**  
   该字段可能包含：
   - 加密的思考摘要
   - 数字签名（用于验证完整性）
   - Provider 特有的 opaque metadata
   
   这些内容必须**逐字节不变地**在下一次 API 请求中传回，否则 API 拒绝后续请求。

3. **Hermes Agent 原有逻辑缺陷**  
   ```python
   # ❌ 旧代码：只提取文本并传回
   if reasoning_text:
       api_msg["reasoning_content"] = reasoning_text  # 丢失原始格式
   ```
   
   提取后的纯文本丢失了签名/元数据，导致 API 校验失败。

## 解决方案

### 核心思路

保存 API 返回的**原始 `reasoning_content`**，下次请求时优先传回原始字段而非提取后的文本。

### 修改位置（run_agent.py）

#### 1. 构建助手消息时保存原始字段

**文件：** `hermes-agent/run_agent.py`  
**方法：** `_build_assistant_message()`  
**行号：** ~7150 行后

```python
if hasattr(assistant_message, 'reasoning_details') and assistant_message.reasoning_details:
    # ... existing reasoning_details handling ...
    if preserved:
        msg["reasoning_details"] = preserved

# ✅ 新增：保存原始 reasoning_content 字段
if hasattr(assistant_message, 'reasoning_content') and assistant_message.reasoning_content:
    msg["_raw_reasoning_content"] = assistant_message.reasoning_content
```

**原理：** 将 API 返回的完整字段原样存储在内侧字典中（前缀 `_raw_` 标记为内部字段）。

---

#### 2. 主对话循环优先传回原始字段

**位置：** 主 API 调用循环中的消息构建部分（~9061 行）

```python
# For ALL assistant messages, pass reasoning back to the API
if msg.get("role") == "assistant":
    # ✅ DeepSeek v4-flash: prioritize raw content (may contain signatures)
    raw_rc = msg.get("_raw_reasoning_content")
    reasoning_text = msg.get("reasoning")
    
    if raw_rc is not None:
        api_msg["reasoning_content"] = raw_rc  # Pass RAW exactly as returned
    elif reasoning_text:
        api_msg["reasoning_content"] = reasoning_text

# Remove internal fields - not accepted by APIs
if "reasoning" in api_msg:
    api_msg.pop("reasoning")
api_msg.pop("_thinking_prefill", None)
api_msg.pop("_raw_reasoning_content", None)  # Clean up after use
```

**关键点：**
- 优先检查 `_raw_reasoning_content` 是否存在
- 如果存在，直接赋值给 `api_msg["reasoning_content"]`
- 之后清理掉内部字段，避免传给 API

---

#### 3. 记忆刷新时的处理

**方法：** `_flush_memory_to_llm()`  
**行号：** ~7302 行

```python
for msg in messages:
    api_msg = msg.copy()
    if msg.get("role") == "assistant":
        reasoning = msg.get("reasoning")
        if reasoning:
            api_msg["reasoning_content"] = reasoning
        
        # ✅ DeepSeek v4-flash: pass back the RAW reasoning_content
        raw_rc = msg.get("_raw_reasoning_content")
        if raw_rc is not None:
            api_msg["reasoning_content"] = raw_rc
    
    api_msg.pop("reasoning", None)
    api_msg.pop("finish_reason", None)
    api_msg.pop("_thinking_prefill", None)
    api_msg.pop("_raw_reasoning_content", None)  # Clean up internal field
```

---

#### 4. 最大迭代次数处理

**方法：** `_handle_max_iterations()`  
**行号：** ~8400 行

```python
for msg in messages:
    api_msg = msg.copy()
    
    # Handle reasoning content properly for DeepSeek v4-flash
    if msg.get("role") == "assistant":
        raw_rc = msg.get("_raw_reasoning_content")
        reasoning = msg.get("reasoning")
        
        if raw_rc is not None:
            api_msg["reasoning_content"] = raw_rc  # Pass back RAW exactly
        elif reasoning:
            api_msg["reasoning_content"] = reasoning
    
    for internal_field in ("reasoning", "finish_reason", "_thinking_prefill", 
                           "_raw_reasoning_content"):
        api_msg.pop(internal_field, None)
```

## 修改总结

| 文件 | 方法 | 修改类型 | 目的 |
|------|------|---------|------|
| run_agent.py | _build_assistant_message | 新增代码块 | 保存原始 reasoning_content |
| run_agent.py | 主对话循环 (~9061 行) | 修改逻辑 | 优先传回原始字段 |
| run_agent.py | _flush_memory_to_llm | 修改逻辑 | 记忆刷新时使用原始字段 |
| run_agent.py | _handle_max_iterations | 修改逻辑 | Max iterations 时使用原始字段 |

## 测试验证

### 方式 1：通过飞书发送复杂问题

```text
请计算：(25x8 - 16x3) / 4 + sqrt(144)，展示逐步思考过程。
```

**预期结果：**
- 正常接收 DeepSeek 响应
- 多轮对话不会中断
- 不再出现 HTTP 400 错误

### 方式 2：监控日志

```bash
tail -f ~/.hermes/logs/errors.log | grep -i "reasoning_content\|HTTP 400"
```

**预期结果：** 无新的 reasoning_content 相关错误。

### 方式 3：检查 Gateway 状态

```bash
cat ~/.hermes/gateway_state.json | python3 -m json.tool | grep gateway_state
# → "gateway_state": "running"
```

## 适用场景

这个修复适用于所有类似情况：

1. **DeepSeek v4/v3 系列** — deepseek-v4-flash, deepseek-chat 等 thinking 模型
2. **Moonshot AI (Kimi)** — 同样使用 reasoning_content 字段
3. **OpenRouter 路由的 thinking 模型** — 经过 OpenRouter 的 DeepSeek/Qwen 等
4. **其他 Provider** — 任何要求严格保持 reasoning 字段格式的 API

## 坑点与注意事项

### 不要手动构造 reasoning_content

```python
# 错误：重新格式化或修改内容
api_msg["reasoning_content"] = f"thought{reasoning}endthought"
api_msg["reasoning_content"] = json.loads(raw_rc).get("summary")
```

必须原样传回，连空格都不能改。

### 清理内部字段

```python
# 正确：使用前弹出内部字段
api_msg.pop("_raw_reasoning_content", None)
```

避免传给 API（API 不接受未知字段）。

### 优先级顺序

```python
# 优先级：
# 1. _raw_reasoning_content (原始字段) ← 最高优先级
# 2. reasoning (提取后的文本) ← 备用
# 3. 不传 (如果都没有)

if raw_rc:
    api_msg["reasoning_content"] = raw_rc
elif reasoning:
    api_msg["reasoning_content"] = reasoning
```

### 持久化考虑

如果需要长期保存会话历史（SQLite/session DB），建议：
- 同时保存 _raw_reasoning_content 和 reasoning
- reasoning 用于 UI 显示
- _raw_reasoning_content 用于续传

## Gateway 重启

修改 Python 代码后需要重启 Hermes Gateway：

```bash
# 找到 Gateway 进程
ps aux | grep "gateway run" | grep -v grep

# 优雅终止
kill <PID>

# 或者直接替换
pkill -f "gateway run" && hermes gateway run --replace
```

---

**更新记录：**
- 2026-04-26 — 创建技能，修复 DeepSeek v4-flash reasoning_content bug
- 影响版本：Hermes Agent >= 0.10.0
- 修改文件：hermes-agent/run_agent.py (4 处关键位置)
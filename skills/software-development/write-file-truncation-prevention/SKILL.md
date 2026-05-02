---
name: write-file-truncation-prevention
description: 避免 write_file 截断文件 — 整文件重写时先 read_file 完整内容，或改用 patch 做靶向编辑
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [file-management, write-file, patch, best-practice]
    related_skills: []
---

# write_file 截断预防指南

## When to Use

**适用场景：**
- 使用 `write_file` 重写长 JS/HTML/Python 文件（50+ 行）
- 函数/方法替换后文件末尾内容丢失
- 语法检查报错显示函数/变量未定义，但明明写入了
- 需要决定使用 `patch` 还是 `write_file`

## Problem

`write_file(path, content)` **完全覆盖**整个文件 — 如果你传入的内容只包含文件前 90 行（比如你只想替换 `loadUsers` 函数），那么文件从 91 行以后的所有代码都会永久丢失。

**这不是工具的限制**，而是使用上的错误。工具忠实地写入你提供的内容。

## Prevention Rules

### Rule 1: 小改动（< 20 行）→ 用 `patch`

```python
# ✅ 替代 write_file 的靶向替换
patch("file.js",
    old_string="旧的完整函数体...",
    new_string="新的完整函数体..."
)
```

- 只替换匹配的文本段
- 文件其余部分不变
- 适合：修改函数体、修复 bug、更新配置

### Rule 2: 替换整个函数 → 用 `patch` 匹配函数范围

```python
# 读取目标函数的起止行
from hermes_tools import search_files
matches = search_files("file.js", "function loadUsers")
# 然后用 patch 匹配该函数的完整定义
```

### Rule 3: 只有当你要重写整个文件时才用 `write_file`

```python
# ✅ 先读后写
from hermes_tools import read_file
result = read_file("file.js", limit=2000)
# result.content 包含完整文件内容
# 基于完整内容构造新的完整内容
new_content = result.content + "\n// 新增代码"
write_file("file.js", new_content)
```

### Rule 4: 意外截断后的恢复步骤

1. **别慌** — 文件还在服务器上，只是被截断了
2. **搜索历史记录** — 用 `session_search` 查找之前读取/写入过该文件内容的会话
3. **提取原内容** — 如果找到之前 `read_file` 的结果，从那里恢复
4. **重建完整文件** — 根据已知的接口（函数名、参数、导出符号）补全缺失部分
5. **写回** — `write_file` 完整的新文件

## Example: 正确的函数替换流程

```python
# Step 1: 读取当前文件
from hermes_tools import read_file, patch

# Step 2: 用小段 context 做靶向替换
patch("file.js",
    old_string="function loadUsers() {\n" +
               "    var tableBody = document.getElementById('users-table-body');\n" +
               "    var loadingElement = document.getElementById('loading-users');",
    new_string="function loadUsers() {\n" +
               "    var tableBody = document.getElementById('users-table-body');\n" +
               "    var loadingElement = document.getElementById('loading-users');\n" +
               "    // NEW: added error handling\n" +
               "    if (!tableBody || !loadingElement) return;\n"
)
```

## Pitfalls

1. **`write_file` 没有追加模式** — 每次调用都是覆盖写入
2. **`patch` 需要唯一匹配** — 确保 `old_string` 在文件中只出现一次
3. **语法检查不总是立即触发** — 文件写入后记得做语法验证
4. **大文件的 context 要足够长** — `patch` 的模糊匹配需要至少 5-10 行 context 才能精确定位

## Pitfall: JS 多行字符串续行符 (\\n\\) 导致 patch 后语法错误

**场景**: 修改 JS 文件中使用反斜杠换行续写的多行字符串（常见于老旧 Vanilla JS 代码）：

```javascript
return '\\n\\\n      <div class=\"card\" data-id=\"' + id + '\">\\n\\\n        <div class=\"card-title\">' + name + '</div>\\n\\\n        <div class=\"card-row\">\\n\\\
```

**问题**: `patch` 工具将此视为普通字符串文本。如果 `new_string` 末尾不小心丢失了 `\\n\\`（续行符 + 换行），JS 语法就断了——下一行代码变成孤立的语句，导致 `SyntaxError: Unexpected token`。

**修复步骤**：

1. 遇到 `SyntaxError` 后检查行末：patch 写入的内容末尾是否保留了完整的 `\\n\\`
2. 用 `read_file` 查看受影响行，确认续行符是否丢失
3. 用第二次 `patch` 补回丢失的续行符：
   ```
   old_string: '">\''          ← 丢失续行符的写入结果
   new_string: '">\\n\\'       ← 正确的续行符
   ```
4. 重新验证：`node -c file.js` 确认语法通过

**预防**: 在 `new_string` 中始终保留与 `old_string` 相同的行末续行符模式。将多行字符串当作**精确的字节序列**对待，不要随意增减末尾的反斜杠或换行。

# Flask 应用系统性调试工作流

> 吸收自 `flask-webapp-debugging`（2026-05 合并）
> 本节补充 flask-api-troubleshooting 主文档未详细展开的通用调试方法论。

## 调试流程

### 1. 验证后端 API 数据流

```bash
# 保存响应到文件
curl -s "API_ENDPOINT" > /tmp/test.json
# 检查文件大小和格式
wc -c /tmp/test.json
head -c 500 /tmp/test.json
```

### 2. 使用 Python 分析数据结构

```python
import json
with open('/tmp/test.json', 'r') as f:
    data = json.load(f)
print(f"总记录数：{len(data)}")
status_count = {p.get('key_field', ''): 1 for p in data[:100]}
```

### 3. 定位前端错误提示来源

```bash
grep -r "error message" /path/to/project/ --include="*.html" --include="*.js"
```

### 4. 追踪数据筛选逻辑

```bash
grep -n "loadFunctionName\|filter-param" index.html
grep -A10 "formElement.value" index.html
```

## 双层登录门控（常见陷阱）

当搜索控件被禁用 + 搜索参数被登录检查双重封锁时：

- **第一层（DOM 禁用）**：`pageLoaders` 里的 `el.disabled = !isLoggedIn`
- **第二层（参数封锁）**：搜索函数里的 `if (isLoggedIn) { ... }`
- 修复时必须解除两把锁，但**选择性开放**（仅把需要的参数移出，其余保持原样）

排查步骤：
1. 检查页面加载器里是否有禁用控件的代码
2. 检查搜索函数里参数是否被 `isLoggedIn` 包裹
3. 用 `curl 'API_URL?param=xxx'` 单独验证后端 API 是否支持未登录请求

## 调试口诀

> 先看 API 再看页，搜错文本找源头
> 追逻辑查默认值，修多处要同步
> 清缓存再验证，改静态需重启
> 双锁控要两端解

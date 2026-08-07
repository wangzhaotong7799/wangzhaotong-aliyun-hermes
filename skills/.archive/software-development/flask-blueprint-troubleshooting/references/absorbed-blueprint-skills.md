# 已吸收的 Blueprint 相关技能摘要

以下技能的独特内容已合并到 `flask-blueprint-troubleshooting` 主 SKILL.md：

## flask-blueprint-api-debugging
- Blueprint 组织最佳实践（目录结构、标准定义）
- 前端字段缺失排查流程
- 复诊时间计算（基于取药日期的动态推算）
- 数据格式不一致（日期范围 vs 单个日期）

## flask-blueprint-api-troubleshooting
- 路由路径不匹配（/api/users vs /api/auth/users）
- API 返回类型错误（数组 vs 对象）
- 前端默认筛选条件限制
- 蓝图别名模式示例

## flask-blueprint-auth-isolation-fix
- 装饰器作用域隔离的完整调试步骤
- 多版本 auth.py 文件冲突诊断
- `from auth import auth_required` 加载旧模块的排查
- 验证装饰器实际来源：`inspect.getfile()`

## flask-blueprint-isolation-troubleshooting
- 补充：sys.path 优先级检查
- `importlib.reload()` 强制验证实际加载模块
- 快速决策树：API 500 → traceback 文件路径检查
- 方案 B (统一装饰器源文件) 和方案 C (清理旧文件)

## flask-blueprint-url-conflict-fix
- 多重蓝图别名方案（4 个不同前缀的同功能蓝图）
- 别名蓝图 Pitfall 详解（name 重复、method 限制、尾部斜杠）
- 实战案例：膏方 V2 的 5 种路径兼容

## flask-blueprint-url-prefix-conflict
- url_prefix 覆盖行为的最小复現
- 方案 A vs 方案 B 的对比
- 路由表验证命令

## flask-new-api-endpoint-debugging
- 新 API 端点开发标准流程（4 步）
- 重复模块文件导致的路径冲突
- SQLAlchemy 模型导入路径错误（from database vs from models）
- JWT Secret 不一致导致认证失败
- Blueprint URL Prefix 导致的路径变化 (assistants 示例)
